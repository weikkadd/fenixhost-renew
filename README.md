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
| `FENIX_COOKIE` | 登录后的 Cookie 字符串（必填，见下方导出方法） |
| `TG_BOT_TOKEN` | Telegram Bot Token（必填） |
| `TG_CHAT_ID` | 接收通知的 Chat ID（必填） |
| `FENIX_LOGIN` / `FENIX_PASSWORD` | 账号密码（仅 Cookie 失效回退时用，Turnstile 多半会拦，建议优先用 Cookie） |
| `NODE_LINK` | `vmess://...` / `vless://...` 分享链接（可选） |
| `RENEW_THRESHOLD_DAYS` | 剩余多少天内才续期，默认 2（可选） |

## 导出 FENIX_COOKIE

脚本通过注入 Cookie 跳过登录页（避开 Cloudflare Turnstile）。Cookie 过期后需重新导出：

1. 浏览器登录 `https://fenixhost.net`（勾选 Remember me 可延长有效期）
2. 按 `F12` → `Network` 标签 → 刷新页面 → 点任意一个请求 → `Request Headers` 里找 `Cookie:` 行
3. 复制 `Cookie:` 后面整串（形如 `laravel_session=xxx; XSRF-TOKEN=yyy; remember_web_...=zzz`）
4. 粘贴到 Secret `FENIX_COOKIE`

或用 `Application` 标签 → `Cookies` → `https://fenixhost.net`，把 `laravel_session`、`XSRF-TOKEN`、`remember_web_*` 拼成 `name=value; name=value`。

## 使用

- **手动测试**：`Actions -> FenixHost 自动续期 -> Run workflow`，手动运行会发送一条 Telegram 检查消息
- **自动运行**：每天北京时间 08:30 自动检查续期
- **Cookie 过期**：脚本会发 Telegram 通知"Cookie 已过期"，按上面步骤重新导出 `FENIX_COOKIE` 即可

## 说明

- 所有敏感信息只存放在 Repository secrets，不要写入代码或 README
- Actions 定时任务可能有几分钟延迟，属正常现象
- 登录失败截图保存为 `fenix_*.png`，可在 Actions artifacts 下载查看
- FenixHost 页面结构变化后可能需要更新脚本选择器
