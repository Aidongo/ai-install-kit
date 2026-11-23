# AI 软件安装工具包

Clash Verge 网络配置与 Claude 本机清理的安装流程和配套文件。

本仓库不包含任何账号、密码、订阅链接或节点信息；订阅链接由安装人员单独私下提供。

## 下载

最新版本（链接固定不变）：

| 文件 | 用途 |
| --- | --- |
| [ai-install-kit.zip](https://github.com/Aidongo/ai-install-kit/releases/latest/download/ai-install-kit.zip) | 完整教程包：安装流程 + 白名单脚本 + Claude 清理 Skill |
| [clash-whitelist.js](https://github.com/Aidongo/ai-install-kit/releases/latest/download/clash-whitelist.js) | 白名单脚本（第 3 步） |
| [claude-cleanup.zip](https://github.com/Aidongo/ai-install-kit/releases/latest/download/claude-cleanup.zip) | Claude 清理 Skill，Mac（第 6 步） |
| [claude-cleanup-windows.zip](https://github.com/Aidongo/ai-install-kit/releases/latest/download/claude-cleanup-windows.zip) | Claude 清理 Skill，Windows（第 6 步） |

历史版本见 [Releases](https://github.com/Aidongo/ai-install-kit/releases)，每个版本附 `SHA256SUMS.txt`。

## 安装流程

按顺序一步步做。遇到和下面描述不一样的情况，先停下来联系安装人员。

### 1. 安装 Clash Verge

先确认电脑类型，点对应链接下载（官方 GitHub，v2.5.10）：

| 电脑 | 怎么确认 | 下载 |
| --- | --- | --- |
| Mac Apple 芯片 | 苹果菜单 → 关于本机，显示「Apple M…」 | [Apple 芯片版](https://github.com/clash-verge-rev/clash-verge-rev/releases/download/v2.5.10/Clash.Verge_2.5.10_aarch64.dmg) |
| Mac Intel 芯片 | 苹果菜单 → 关于本机，显示「Intel」 | [Intel 芯片版](https://github.com/clash-verge-rev/clash-verge-rev/releases/download/v2.5.10/Clash.Verge_2.5.10_x64.dmg) |
| Windows 10 / 11 | — | [Windows 版](https://github.com/clash-verge-rev/clash-verge-rev/releases/download/v2.5.10/Clash.Verge_2.5.10_x64-setup.exe) |

- **Mac**：打开 DMG，把 Clash Verge 拖进「应用程序」，然后打开。提示无法验证开发者时，到「系统设置 → 隐私与安全性」点「仍要打开」。
- **Windows**：运行安装程序，装在默认目录。提示「Windows 已保护你的电脑」时点「更多信息 → 仍要运行」。
- 弹出授权请求一律允许。

### 2. 导入订阅链接

「订阅」页粘贴订阅链接 → 导入 → 点选该订阅。

### 3. 导入白名单规则

1. 打开 [`网络配置/公网白名单-追加补丁.js`](网络配置/公网白名单-追加补丁.js)（或下载 `clash-whitelist.js`），全选复制。
2. Clash「订阅」页右键订阅卡片 → 「扩展脚本」。
3. 保留原有内容，在最后一个 `}` 后面另起一行粘贴。
4. 保存 → 右键订阅卡片 → 重新激活订阅。

### 4. 开启代理

「代理」页选「规则」模式和节点 → 「设置」打开「系统代理」。

### 5. 测试

| # | 测试 | 打开 | 通过标准 |
| --- | --- | --- | --- |
| 1 | 出口 IP | [ippure.com](https://ippure.com)、[ipok.io](https://ipok.io)、[ping0.cc](https://ping0.cc) | 3 个网站中至少 2 个显示风险值 ≤ 5%，且不是机房 IP |
| 2 | 国内直连 | [www.163.com](https://www.163.com) | Clash「连接」页筛选 `163.com`，显示 `DIRECT` |
| 3 | DNS 泄漏 | [browserleaks.com/dns](https://browserleaks.com/dns) | 没有本地运营商或国内的 DNS 服务器 |
| 4 | WebRTC 泄漏 | [browserleaks.com/webrtc](https://browserleaks.com/webrtc) | 显示的公网 IP 不是本地宽带 IP |

- 第 2 项只用白名单内的网站测，例如 163.com、alipay.com、feishu.cn。
- 第 4 项不通过时，到「设置」打开 TUN 模式后重测。

### 6. 清理 Claude 本机数据（装 Claude 前，由 Codex 执行）

电脑从没装过 Claude Code / Claude Desktop 时跳过。

1. 退出 Claude Code 和 Claude Desktop。
2. 下载对应的 Skill zip（Mac `claude-cleanup.zip`，Windows `claude-cleanup-windows.zip`），拖进 Codex 对话框，发送：

> 解压这个 skill，按里面的 SKILL.md 清理本机的 Claude 数据。先只读审计，说明会清什么、不清什么，等我确认再执行。

3. Codex 审计后会列出清理范围。不确定的选项一律选否（只清缓存和日志）。
4. 最终确认需要在真实终端里输入 `CONFIRM`：Codex 给出命令后，在「终端」/ PowerShell 里运行，看完清单再输入。
5. 记下结束时显示的备份路径。

- 清理前会先完整备份；移走的文件进废纸篓或隔离目录，不会永久删除。会话、项目、Skills、MCP 和设置不动。
- Codex 提示缺少 Python 时：Mac 按弹窗安装「命令行开发者工具」；Windows 从 [python.org](https://www.python.org/downloads/) 安装 3.10 及以上版本。

### 撤销白名单

「扩展脚本」中删除 `CODEX_PUBLIC_WHITELIST_SYNC_BEGIN` 到 `CODEX_PUBLIC_WHITELIST_SYNC_END` 整段，保存并重新激活订阅。

## 仓库结构

```
网络配置/公网白名单-追加补丁.js     Clash 扩展脚本补丁（20261109 版）
Claude清理/claude-cleanup/          Claude 本机清理 Skill（macOS）
Claude清理/claude-cleanup-windows/  Claude 本机清理 Skill（Windows）
```

Clash Verge Rev 不在本仓库重新分发，请从其[官方 Release](https://github.com/clash-verge-rev/clash-verge-rev/releases) 下载。
