# Windows 布局、边界与验证

## 支持路径

- Claude Code：默认 %USERPROFILE%\.claude；CLAUDE_CONFIG_DIR 非空时使用实际目录。
- 身份文件：%USERPROFILE%\.claude.json，以及存在时配置目录内的 .claude.json。内部 .claude.json.backup.* 只在明确选择本地标识轮换时同步。
- 已存储 CLI 登录：默认配置目录内 .credentials.json；CLAUDE_SECURESTORAGE_CONFIG_DIR 若存在也纳入显式审计。后者的版本行为可能变化，因此只处理真实存在、位于用户目录内的同名文件，不能推断其他凭据库位置。
- CLI 缓存：cache、stats-cache.json、telemetry、usage-data、usage.jsonl、usage.with-fix.jsonl；%LOCALAPPDATA%\claude-cli-nodejs\Cache。
- Desktop 候选布局：%APPDATA%\Claude；%LOCALAPPDATA%\Claude-Data；%LOCALAPPDATA%\Claude；以及 %LOCALAPPDATA%\Packages\Claude_*\LocalCache\Roaming\Claude。安装方式和版本会改变布局，候选路径不是存在保证，也不是清理整个根目录的许可。
- Desktop 只清实际存在的明确缓存/日志子路径：Cache、Code Cache、GPUCache、DawnCache、logs、Crashpad\reports。不会移走整个 Packages 容器、LocalCache、Desktop 用户数据或 Cowork 会话。

用户目录外配置、UNC/重定向路径、junction/reparse point 一律停止，需另行审计；本版本不跨用户、不用管理员身份扫全盘。审计也不跟随这些链接。

## 备份/隔离

%USERPROFILE%\ClaudeCleanupBackups\Windows\batch-时间戳 下：

- backup：完整 CLI 配置与身份文件、本次 CLI 根目录外目标副本；SHA-256 校验。
- json-before：本次结构化变更的原始文件。
- quarantine：移入的缓存/日志/可选凭据；不是系统回收站。
- manifest.json：原始位置、哈希、操作状态和原时区。备份及清单可能含敏感数据，Windows ACL 仅给当前用户继承权限，不上传或转发。

确认前不写盘；确认后如磁盘不足、复制/哈希/ACL/文件占用失败，立即停止。脚本不会自动结束 Claude 进程。恢复有冲突时不覆盖，避免删除重新登录或新产生的会话。

## 与 macOS 版本的差异

Windows 没有删除 macOS Keychain 的对应步骤；本版本只隔离明确的 CLI 凭据文件。Desktop 正常退出登录或卸载需要走应用/Windows 设置。MSIX 卸载可能删除包内持久数据，因此不能把 Remove-AppxPackage 当作等同于移动 macOS .app 的操作；若用户明确要求卸载，先单独识别安装包、备份相关持久数据，再使用系统流程，不直接改 WindowsApps。

时区使用 tzutil /g 与 tzutil /s "Taipei Standard Time"。本地标识重置不能保证账号、设备关联或平台判断发生变化。CLAUDE_CODE_SIMPLE 的实际产品行为以所安装版本为准，本脚本只控制该配置键。

## 权威来源（制作时核对）

- [Claude Code 设置路径](https://code.claude.com/docs/en/settings)：Windows .claude、CLAUDE_CONFIG_DIR、独立 .claude.json。
- [Claude Code 凭据](https://code.claude.com/docs/en/authentication)：Windows .credentials.json、配置目录和登录/退出管理。
- [Microsoft 时区表](https://learn.microsoft.com/en-us/windows-hardware/manufacture/desktop/default-time-zones)：Taipei Standard Time。
- [Remove-AppxPackage](https://learn.microsoft.com/en-us/powershell/module/appx/remove-appxpackage)：Windows 包卸载与数据保留参数，不套用 macOS 应用路径。

## 验证范围

隔离目录测试覆盖备份哈希、保护文件、可恢复隔离、取消不写盘、遥测继承、凭据可选、进程/TTY 限制、符号链接拒绝和冲突恢复。当前制作环境为 macOS；没有在 Windows 实机测试 CIM、ACL、junction 原生属性和 tzutil，实际清理前必须在目标 Windows 先运行只读审计。本版本没有宣称 Windows 端到端清理已验证。
