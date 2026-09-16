# FenixHost Auto Renew

FenixHost 免费 Minecraft 服务器自动续期脚本（GitHub Actions 版）。

## 功能

- 每天北京时间 08:30 自动检查剩余时间
- 剩余时间 ≤ 2 天（`RENEW_THRESHOLD_DAYS` 可调）时自动点击 `Renovar` 并确认
- 兼容英语 / 西班牙语界面（Renew / Renovar）
- Telegram 通知：检查结果 / 续期成功 / 失败异常
- 支持可选 `NODE_LINK` 固定出口 IP（VMess / VLESS）

## GitHub Secrets

`Settings -> Secrets and variables -> Actions` 添加：

| Name | 说明 |
|------|------|
| `FENIX_SERVER_URL` | 服务详情页地址，如 `https://fenixhost.net/services/xxxxxxxx`（必填） |
| `FENIX_LOGIN` | FenixHost 登录邮箱（必填） |
| `FENIX_PASSWORD` | 登录密码（必填） |
| `TG_BOT_TOKEN` | Telegram Bot Token（必填） |
| `TG_CHAT_ID` | 接收通知的 Chat ID（必填） |
| `NODE_LINK` | `vmess://...` / `vless://...` 分享链接（可选） |
| `RENEW_THRESHOLD_DAYS` | 剩余多少天内才续期，默认 2（可选） |

## 使用

- **手动测试**：`Actions -> FenixHost 自动续期 -> Run workflow`，手动运行会发送一条 Telegram 检查消息
- **自动运行**：每天北京时间 08:30 自动检查续期

## 说明

- 所有敏感信息只存放在 Repository secrets，不要写入代码或 README
- Actions 定时任务可能有几分钟延迟，属正常现象
- 登录页含 Cloudflare Turnstile 验证，脚本会等待其自动通过；登录失败截图保存为 `fenix_*.png`，可在 Actions artifacts 下载查看
- FenixHost 页面结构变化后可能需要更新脚本选择器
