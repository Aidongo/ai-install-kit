---
name: claude-cleanup-windows
description: 在 Windows 原生环境审计、完整备份并可恢复地清理 Claude Code/Desktop 缓存日志，按需处理 CLI 登录、本地标识、精简模式和时区。保护会话、项目、Skills、MCP 和 Cowork 数据；不用于规避平台风控。
---

# Claude Windows 本机清理

使用随附 Python 3.10+ 标准库脚本；不套用 macOS 的 Library、钥匙串或 Asia/Taipei 命令。WSL 和远程 Linux 不是 Windows 宿主。此 Skill 独立分发，不依赖 macOS Skill。

## 执行

1. 先在实际 Windows 用户终端识别 Python：`py -3 --version`，不可用时试 `python --version`。缺少 Python 则说明依赖并按用户意愿从官方来源安装；不要用执行策略绕过或临时拼接删除命令。
2. 只读审计：
   ```powershell
   py -3 scripts/cleanup_windows.py --audit
   ```
   也可使用 PowerShell 入口 `scripts/cleanup-windows.ps1 -Audit`；它选择已安装的 Python，不下载软件、不绕过执行策略。Windows 阻止未签名脚本时直接运行上面的 Python 命令。
   审计列出实际配置目录、缓存/日志目标、凭据文件是否存在、进程数量与时区，不输出身份文件或令牌内容。尊重 CLAUDE_CONFIG_DIR / CLAUDE_SECURESTORAGE_CONFIG_DIR；用户目录外路径、符号链接/junction/reparse point 停止并报告，不猜测迁移位置。
3. 向用户展示审计结果与操作范围。只有用户要求实际清理后，运行交互脚本：
   ```powershell
   py -3 scripts/cleanup_windows.py
   ```
   缓存日志统一列入；本地标识轮换、CLI 凭据移走、精简模式与台北时区由用户分别选择。终端显示完整最终清单，用户输入一次 `CONFIRM` 后才写盘；不要管道代答，不增加跳过确认参数。若当前执行者为 Claude Code，仅允许审计，切换到 Codex/普通终端执行写操作。
4. 写操作前必须正常退出所有 Claude Code/Desktop；不自动杀进程，不自动提权。首次写操作是创建用户私有备份批次，完整复制 CLI 配置、身份文件及本次额外目标，逐文件 SHA-256 校验。备份失败不清理。文件仅移入批次内 quarantine；**这是脚本的可恢复隔离目录，不是 Windows 回收站**，不永久删除或清空回收站。
5. 报告完成/部分完成、备份批次、隔离清单、实际修改和恢复命令。中途失败停止后续操作，保留日志清单，不能笼统声称成功。

## 默认与可选范围

- 默认：CLI 明确缓存/统计/日志及 Desktop 的 Cache、Code Cache、GPUCache、DawnCache、logs、Crashpad/reports。只处理实际存在且通过路径检查的窄白名单。
- CLI 登录：可选把 `.credentials.json` 备份后移入隔离目录，可能退出已存储登录；不会清理系统 Credential Manager、环境变量 API key、第三方云凭据或服务端登录会话。
- 本地标识：只轮换已存在的 userID/machineID，清除已知账号缓存字段，同步内部身份备份；不创建未知标识字段，不宣称能改变平台关联或风控。
- 精简模式：只改 settings.json 的 env.CLAUDE_CODE_SIMPLE，其他键、MCP、权限和秘密保持原样。DISABLE_TELEMETRY、DISABLE_ERROR_REPORTING、CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC 按存在性和原值保持，不额外关闭遥测。
- 时区：用户单选时才用 Windows 原生 tzutil 设置 Taipei Standard Time，记录原值便于恢复；权限不足报告失败，不自动提权。

## 保护与 Windows 特有边界

保护 CLI 的 projects、sessions、history.jsonl、file-history、debug、skills、plugins、hooks、commands、agents、MCP、backups、CLAUDE.md、项目和 Codex 数据。settings.json 仅允许上述明确选择的单键变更，身份备份仅在明确选择轮换时变更。Desktop 的 claude_desktop_config.json、Cookies、Local Storage、IndexedDB、会话与 Cowork/VM 数据不在清理范围。

桌面端登录重置和卸载不能照搬“移动整个应用数据目录”：使用应用正常退出登录/Windows 设置的卸载入口，且按 [Windows 布局与限制](references/windows.md) 先单独列出可能删除的持久数据并备份。脚本本身不实现这些操作，不碰 WindowsApps、注册表、浏览器或系统凭据库。不把清缓存说成重置了 Desktop 登录。

## 恢复

```powershell
py -3 scripts/cleanup_windows.py --restore "C:\Users\用户名\ClaudeCleanupBackups\Windows\batch-时间戳"
```

同样需要真实终端、Claude 已退出、用户 `CONFIRM`。恢复前核对清单、哈希和原路径；存在新数据/新设置就拒绝覆盖。完整 CLI 备份始终保留，部分事务不能安全自动恢复时按清单人工比对。不删除备份或隔离批次。

详细路径、来源和测试范围见 [Windows 布局与限制](references/windows.md)。本 Skill 只用于本机维护与排障。
