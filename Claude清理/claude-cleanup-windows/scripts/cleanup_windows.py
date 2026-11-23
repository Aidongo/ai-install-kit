#!/usr/bin/env python3
"""Windows-only interactive Claude maintenance; audit never writes."""
from __future__ import annotations
import argparse
import copy
import csv
import datetime as dt
import hashlib
import io
import json
import os
from pathlib import Path
import secrets
import shutil
import stat
import subprocess
import sys
import tempfile

def native_path(value):
    return Path(os.path.abspath(os.path.expandvars(str(value))))

def is_windows():
    return os.name == 'nt'

TELEMETRY = ('DISABLE_TELEMETRY', 'DISABLE_ERROR_REPORTING', 'CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC')
CLI_CACHE = ('cache', 'stats-cache.json', 'telemetry', 'usage-data', 'usage.jsonl', 'usage.with-fix.jsonl')
DESKTOP_CACHE = ('Cache', 'Code Cache', 'GPUCache', 'DawnCache', 'logs', 'Crashpad/reports')
ACCOUNT_CACHE = {'oauthAccount', 'anonymousId', 'cachedDynamicConfigs', 'cachedExperimentData', 'cachedStatsigGates', 'clientDataCache', 'clientDataCacheSlots', 'feedbackSurveyState', 'modelAccessCache', 'orgModelDefaultCache'}

class Layout:
    def __init__(self, home, appdata, localappdata, config=None, storage=None):
        self.home = native_path(home)
        self.appdata, self.local = native_path(appdata), native_path(localappdata)
        self.config = native_path(config) if config else self.home / '.claude'
        self.storage = native_path(storage) if storage else self.config
        self.settings = self.config / 'settings.json'
        self.identities = list(dict.fromkeys([self.home / '.claude.json', self.config / '.claude.json']))
        self.batches = self.home / 'ClaudeCleanupBackups' / 'Windows'
        for p in [self.appdata, self.local, self.config, self.storage]:
            guard(p, self.home)
        if self.config in [self.home, self.appdata, self.local] or self.storage == self.home:
            raise ValueError('配置目录指向过大的用户目录，拒绝操作')

    @classmethod
    def current(cls):
        home = Path.home()
        return cls(home, os.environ.get('APPDATA', str(home/'AppData/Roaming')), os.environ.get('LOCALAPPDATA', str(home/'AppData/Local')),
                   os.environ.get('CLAUDE_CONFIG_DIR'), os.environ.get('CLAUDE_SECURESTORAGE_CONFIG_DIR'))

    def desktops(self):
        roots = [self.appdata/'Claude', self.local/'Claude-Data', self.local/'Claude']
        packages = self.local/'Packages'
        guard(packages, self.home)
        if packages.exists():
            for item in packages.iterdir():
                if item.name.lower().startswith('claude_'):
                    roots.append(item/'LocalCache/Roaming/Claude')
        return list(dict.fromkeys(roots))

    def candidates(self):
        result = {'cli:'+name: self.config/name for name in CLI_CACHE}
        result['cli-node-cache'] = self.local/'claude-cli-nodejs/Cache'
        for i, root in enumerate(self.desktops()):
            for name in DESKTOP_CACHE:
                root_id = hashlib.sha256(str(root).encode()).hexdigest()[:16]
                result[f'desktop-{root_id}:{name}'] = root/name
        result['cli-credentials'] = self.storage/'.credentials.json'
        for p in result.values():
            guard(p, self.home)
        return result

    def json_targets(self):
        values = [self.settings] + self.identities
        backups = self.config/'backups'
        guard(backups, self.home)
        if backups.exists():
            values += sorted(backups.glob('.claude.json.backup.*'))
        return list(dict.fromkeys(values))


def linked(path):
    st = path.lstat()
    return stat.S_ISLNK(st.st_mode) or bool(getattr(st, 'st_file_attributes', 0) & 0x400)


def guard(path, home):
    path, home = native_path(path), native_path(home)
    if path != home and home not in path.parents:
        raise ValueError('发现用户目录外路径，需单独审计，脚本停止')
    current = path
    while True:
        if (current.exists() or current.is_symlink()) and linked(current):
            raise ValueError('发现符号链接或 Windows junction/reparse point，脚本停止')
        if current == home:
            break
        current = current.parent
    return path


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1024*1024), b''):
            h.update(b)
    return h.hexdigest()


def snapshot(path):
    path = Path(path)
    if not path.exists():
        return None
    if linked(path):
        raise ValueError('备份树包含链接，拒绝跟随')
    if path.is_file():
        return {'file': digest(path)}
    result = {'.': 'dir'}
    for base, dirs, files in os.walk(path, followlinks=False):
        for name in dirs+files:
            p = Path(base)/name
            if linked(p):
                raise ValueError('备份树包含 junction/链接，停止')
            if not (p.is_file() or p.is_dir()):
                raise ValueError('遇到非常规文件，停止')
            result[p.relative_to(path).as_posix()] = 'dir' if p.is_dir() else digest(p)
    return result


def read_json(path, default=None):
    path = Path(path)
    if not path.exists():
        return copy.deepcopy(default)
    value = json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(value, dict):
        raise ValueError('JSON 顶层不是对象，停止')
    return value


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.claude-cleanup-', dir=path.parent)
    tmp = Path(name)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(value, f, ensure_ascii=False, indent=2)
            f.write('\n'); f.flush(); os.fsync(f.fileno())
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def telemetry(value):
    env = value.get('env', {})
    if not isinstance(env, dict):
        raise ValueError('settings.env 不是对象，停止')
    return {k: {'present': k in env, 'value': env.get(k)} for k in TELEMETRY}


def prepare_changes(layout, rotate=False, simple=0):
    changes = {}
    if rotate:
        ids = {'userID': secrets.token_hex(32), 'machineID': secrets.token_hex(32)}
        identities = [p for p in layout.identities if p.exists()]
        backups = layout.config/'backups'
        if backups.exists():
            identities += list(backups.glob('.claude.json.backup.*'))
        for p in dict.fromkeys(identities):
            guard(p, layout.home)
            value = read_json(p)
            # Don't invent unsupported fields in installations without these identifiers.
            updated = copy.deepcopy(value)
            for k in ids:
                if k in updated:
                    updated[k] = ids[k]
            for k in ACCOUNT_CACHE:
                updated.pop(k, None)
            if updated != value:
                changes[p] = updated
    if simple:
        value = read_json(layout.settings, {})
        before = telemetry(value)
        if simple == 2 and 'CLAUDE_CODE_SIMPLE' not in value.get('env', {}):
            return changes
        updated = copy.deepcopy(value)
        env = updated.setdefault('env', {})
        if simple == 1:
            env['CLAUDE_CODE_SIMPLE'] = '1'
        elif simple == 2:
            env.pop('CLAUDE_CODE_SIMPLE', None)
        else:
            raise ValueError('精简模式选择无效')
        if telemetry(updated) != before:
            raise ValueError('遥测设置变化，停止')
        if updated != value:
            changes[layout.settings] = updated
    return changes


def powershell(code):
    r = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', '[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new();'+code], capture_output=True, encoding='utf-8', errors='strict')
    if r.returncode:
        raise RuntimeError('Windows 只读进程检查失败，未执行清理')
    return r.stdout.strip()


def process_state():
    raw = powershell('Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,Name,ExecutablePath,CommandLine | ConvertTo-Json -Compress')
    rows = json.loads(raw or '[]')
    rows = [rows] if isinstance(rows, dict) else rows
    def is_claude(p):
        name = (p.get('Name') or '').lower()
        args = (p.get('CommandLine') or '').lower().replace('\\','/')
        exe = (p.get('ExecutablePath') or '').lower().replace('\\','/')
        return name in ('claude.exe','claude-code.exe','claudedesktop.exe') or any(x in exe for x in ('/claude/versions/','/windowsapps/claude_','/anthropicclaude/')) or bool(__import__('re').search(r'(?:@anthropic-ai/claude-code/|/claude-code/)cli\.js', args))
    index = {int(p['ProcessId']):p for p in rows}
    current = os.getppid(); under = os.environ.get('CLAUDECODE') == '1'
    for _ in range(32):
        p=index.get(current)
        if not p:break
        under = under or is_claude(p)
        parent=int(p.get('ParentProcessId') or 0)
        if parent==current:break
        current=parent
    active=[{'pid':int(p['ProcessId']),'name':p.get('Name')} for p in rows if is_claude(p)]
    return under, active


def timezone():
    r=subprocess.run(['tzutil.exe','/g'],capture_output=True,text=True)
    if r.returncode:raise RuntimeError('无法读取 Windows 时区')
    return r.stdout.strip()


def secure_directory(path):
    path.mkdir(parents=True, exist_ok=False)
    if os.name=='nt':
        r=subprocess.run(['whoami.exe','/user','/fo','csv','/nh'],capture_output=True,text=True)
        rows=list(csv.reader(io.StringIO(r.stdout)))
        if r.returncode or not rows or len(rows[0])<2 or not rows[0][1].startswith('S-1-'):
            raise RuntimeError('无法识别当前用户 SID，停止备份')
        sid=rows[0][1]
        r=subprocess.run(['icacls.exe',str(path),'/inheritance:r','/grant:r','*'+sid+':(OI)(CI)F'],capture_output=True)
        if r.returncode:raise RuntimeError('备份目录 ACL 设置失败，停止')
    else:
        path.chmod(0o700)  # Used only for isolated portable tests.


def create_backup(layout, targets, changes, old_timezone):
    # Complete hash verification happens before any target is changed/moved.
    sources={'config':layout.config}
    sources.update({'identity-'+str(i):p for i,p in enumerate(layout.identities) if p.exists()})
    for i,p in enumerate(list(targets.values())+list(changes)):
        if layout.config not in p.parents and p != layout.config and p.exists():sources['extra-'+str(i)]=p
    sources={k:p for k,p in sources.items() if p.exists()}
    if not sources:raise ValueError('没有可备份的 Claude 数据，不执行空清理')
    inventories={k:snapshot(p) for k,p in sources.items()}
    size=sum(p.stat().st_size for src in sources.values() for p in ([src] if src.is_file() else src.rglob('*')) if p.is_file())
    if shutil.disk_usage(layout.home).free < size + max(size//10,1024*1024):
        raise RuntimeError('备份空间不足，未清理')
    batch=layout.batches/('batch-'+dt.datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    guard(batch,layout.home)
    secure_directory(batch)
    try:
        for key,src in sources.items():
            dest=batch/'backup'/key;dest.parent.mkdir(parents=True,exist_ok=True)
            if src.is_dir():shutil.copytree(src,dest)
            else:shutil.copy2(src,dest)
            if inventories[key] != snapshot(src) or inventories[key] != snapshot(dest):
                raise RuntimeError('备份内容校验不一致，未清理')
        manifest={'version':1,'state':'backed-up','timezone_before':old_timezone,'timezone_changed':False,'moves':[],'changes':[]}
        for i,(key,p) in enumerate(targets.items()):
            manifest['moves'].append({'id':key,'original':str(p),'stored':f'quarantine/{i:03d}','before':snapshot(p),'status':'planned'})
        for i,(p,value) in enumerate(changes.items()):
            guard(p,layout.home)
            backup=batch/'json-before'/f'{i:03d}'
            if p.exists():backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,backup)
            manifest['changes'].append({'target':str(p),'backup':f'json-before/{i:03d}','before':digest(p) if p.exists() else None,'after':None})
        manifest['backup_inventory']=inventories
        write_json(batch/'manifest.json',manifest)
        return batch,manifest
    except BaseException:
        # Preserve partial backup for diagnosis; no cleanup has occurred.
        raise RuntimeError('备份未完成；已停止，未清理。保留备份目录：'+str(batch))


def protected_snapshot(layout, excluded):
    value=snapshot(layout.config) or {}
    if 'file' in value:raise ValueError('配置根目录不是目录')
    prefixes=[]
    for p in excluded:
        if layout.config in p.parents:prefixes.append(p.relative_to(layout.config).as_posix())
    return {k:v for k,v in value.items() if k != '.' and not any(k==x or k.startswith(x+'/') for x in prefixes)}


def execute(layout, targets, changes, set_taipei, old_timezone):
    allowed=layout.candidates()
    if any(k not in allowed or p != allowed[k] for k,p in targets.items()):raise ValueError('目标不在窄白名单')
    if any(p not in layout.json_targets() for p in changes):raise ValueError('JSON 修改目标不在白名单')
    settings_before=telemetry(read_json(layout.settings,{}))
    config_existed = layout.config.exists()
    protected_before=protected_snapshot(layout,list(targets.values())+list(changes))
    batch,manifest=create_backup(layout,targets,changes,old_timezone)
    try:
        for move in manifest['moves']:
            p=targets[move['id']];guard(p,layout.home)
            if snapshot(p)!=move['before']:raise RuntimeError('目标在确认后发生变化，停止')
            dest=batch/move['stored'];dest.parent.mkdir(parents=True,exist_ok=True)
            os.replace(p,dest)
            move['status']='moved';write_json(batch/'manifest.json',manifest)
        for item in manifest['changes']:
            p=Path(item['target']);guard(p,layout.home)
            if (digest(p) if p.exists() else None)!=item['before']:raise RuntimeError('JSON 在备份后变化，停止')
            write_json(p,changes[p]);item['after']=digest(p);write_json(batch/'manifest.json',manifest)
        if set_taipei:
            manifest['timezone_change_requested']=True;write_json(batch/'manifest.json',manifest)
            r=subprocess.run(['tzutil.exe','/s','Taipei Standard Time'],capture_output=True)
            if r.returncode or timezone()!='Taipei Standard Time':raise RuntimeError('时区修改失败，可能缺少系统权限；不自动提权')
            manifest['timezone_changed']=True
        if telemetry(read_json(layout.settings,{}))!=settings_before:raise RuntimeError('遥测设置变化，停止')
        if config_existed and not layout.config.is_dir():raise RuntimeError('受保护配置根目录丢失，停止')
        if protected_snapshot(layout,list(targets.values())+list(changes))!=protected_before:raise RuntimeError('受保护数据变化，停止')
        manifest['state']='complete';write_json(batch/'manifest.json',manifest)
    except BaseException:
        manifest['state']='partial';write_json(batch/'manifest.json',manifest)
        raise RuntimeError('部分完成，停止后续操作；备份/恢复清单：'+str(batch))
    return batch


def restore(layout,batch):
    batch=native_path(batch);guard(batch,layout.home)
    if batch.parent != layout.batches or not batch.name.startswith('batch-'):raise ValueError('不是本脚本的备份批次')
    manifest=read_json(batch/'manifest.json');allowed=layout.candidates();json_allowed=layout.json_targets()
    planned=[]
    for item in manifest.get('moves',[]):
        p=allowed.get(item['id'])
        stored=Path(item['stored'])
        if p is None or str(p)!=item['original'] or stored.parent!=Path('quarantine') or not stored.name.isdigit():raise ValueError('恢复清单路径不合法')
        guard(p,layout.home);src=batch/stored;guard(src,layout.home)
        if src.exists():
            if p.exists() or p.is_symlink():raise ValueError('原路径已有新数据，拒绝覆盖；请人工对比')
            if snapshot(src)!=item['before']:raise ValueError('隔离数据已变化，停止恢复')
            planned.append((src,p))
    json_restore=[]
    for item in manifest.get('changes',[]):
        p=Path(item['target']);guard(p,layout.home)
        if p not in json_allowed:raise ValueError('JSON 恢复目标不在白名单')
        expected=item.get('after')
        if expected is None:
            if (digest(p) if p.exists() else None)!=item['before']:raise ValueError('变更中断在未记录阶段，请按完整备份人工恢复')
            continue
        if not p.exists() or digest(p)!=expected:raise ValueError('JSON 出现新变更，拒绝覆盖')
        rel=Path(item['backup'])
        if rel.parent!=Path('json-before') or not rel.name.isdigit():raise ValueError('JSON 备份路径不合法')
        src=batch/rel;guard(src,layout.home)
        if item['before'] is not None and (not src.is_file() or digest(src)!=item['before']):raise ValueError('JSON 备份校验失败')
        json_restore.append((src,p,item['before']))
    if manifest.get('timezone_changed') and timezone()!='Taipei Standard Time':raise ValueError('时区已有新变化，拒绝覆盖')
    for src,p in planned:p.parent.mkdir(parents=True,exist_ok=True);os.replace(src,p)
    for src,p,before in json_restore:
        if before is None:
            dest=batch/'restore-created-settings.json';os.replace(p,dest)
        else:
            # Quarantine the modified file rather than permanently delete it.
            dest=batch/('restore-modified-'+str(len(list(batch.glob('restore-modified-*')))))
            os.replace(p,dest);shutil.copy2(src,p)
    if manifest.get('timezone_changed'):
        r=subprocess.run(['tzutil.exe','/s',manifest['timezone_before']],capture_output=True)
        if r.returncode or timezone()!=manifest['timezone_before']:raise RuntimeError('数据已恢复，但时区恢复失败，请手动设置')
    manifest['state']='restored';write_json(batch/'manifest.json',manifest)
    return len(planned)+len(json_restore)


def ask_choice(text,values):
    value=input(text).strip() or '0'
    if value not in values:raise ValueError('选择无效，取消且未写盘')
    return value


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--audit',action='store_true');ap.add_argument('--restore',metavar='BATCH')
    args=ap.parse_args(argv)
    if not is_windows():print('仅支持 Windows 原生 Python；WSL/macOS 不可代替目标 Windows。',file=sys.stderr);return 2
    if args.audit and args.restore:print('audit 与 restore 不可同时使用',file=sys.stderr);return 2
    try:
        layout=Layout.current();under,active=process_state();old=timezone();settings=read_json(layout.settings,{})
        candidates=layout.candidates();existing={k:p for k,p in candidates.items() if p.exists()}
        print('只读审计：配置目录：'+str(layout.config))
        print('缓存/日志：'+str(sum(k!='cli-credentials' for k in existing))+' 项；CLI 凭据文件：'+('存在' if 'cli-credentials' in existing else '未找到'))
        print('运行中的 Claude 进程：'+str(len(active))+'；时区：'+old)
        print('遥测键保持原值；未知文件、聊天/项目/技能/MCP/Cowork 数据不在清理白名单。')
        for k,p in existing.items():print('  '+k+' -> '+str(p))
        telemetry(settings)
        if args.audit:return 0
        if under:raise ValueError('Claude Code 本身只能审计；请切换 Codex 或普通终端')
        if not sys.stdin.isatty():raise ValueError('需要真实终端交互；禁止管道代答')
        if active:raise ValueError('请正常退出所有 Claude Code/Desktop 后重试；脚本不终止进程')
        if args.restore:
            print('恢复批次：'+str(args.restore)+'；冲突时拒绝覆盖。')
            if input('输入 CONFIRM 恢复；其他输入取消：').strip()!='CONFIRM':return 1
            if process_state()[1]:raise ValueError('Claude 重新启动，停止恢复')
            print('已恢复项目数：'+str(restore(layout,args.restore)));return 0
        rotate=ask_choice('轮换已有本地 userID/machineID、清已知账号缓存？0 保持 / 1 执行 [0]：',{'0','1'})=='1'
        auth=ask_choice('移走 CLI 凭据文件（可能退出 CLI 登录）？0 保持 / 1 执行 [0]：',{'0','1'})=='1'
        simple=int(ask_choice('精简模式：0 保持 / 1 启用 / 2 移除 [0]：',{'0','1','2'}))
        tz=old!='Taipei Standard Time' and ask_choice('时区改为 Taipei Standard Time？0 保持 / 1 执行 [0]：',{'0','1'})=='1'
        targets={k:p for k,p in existing.items() if k!='cli-credentials' or auth}
        changes=prepare_changes(layout,rotate,simple)
        print('最终清单：先完整备份并 SHA-256 校验 CLI 配置/身份文件及本次额外目标，再移入本批次隔离目录（不是永久删除）。')
        for p in targets.values():print('  移入隔离：'+str(p))
        for p in changes:print('  结构化修改：'+str(p))
        print('时区：'+('修改' if tz else '保持')+'；不操作浏览器、系统凭据库或卸载程序。')
        if input('输入 CONFIRM 开始；其他输入取消：').strip()!='CONFIRM':print('已取消，未写盘');return 1
        under,active=process_state()
        if under or active:raise ValueError('进程状态改变，取消且未写盘')
        batch=execute(layout,targets,changes,tz,old)
        print('完成。备份/隔离/恢复清单：'+str(batch));return 0
    except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as e:
        # Never print malformed JSON, command arguments or credential contents.
        print('停止：'+(str(e) if type(e) in (ValueError,RuntimeError) else type(e).__name__),file=sys.stderr);return 2
    except (EOFError,KeyboardInterrupt):
        print('用户中断；若已产生备份批次，请检查 manifest.json 的状态。',file=sys.stderr);return 2

if __name__=='__main__':sys.exit(main())
