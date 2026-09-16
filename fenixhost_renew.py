#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import sys
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests
from playwright.sync_api import sync_playwright


SERVER_URL = os.getenv("FENIX_SERVER_URL", "").strip()
FENIX_LOGIN = os.getenv("FENIX_LOGIN", "").strip()
FENIX_PASSWORD = os.getenv("FENIX_PASSWORD", "").strip()
FENIX_COOKIE = os.getenv("FENIX_COOKIE", "").strip()

TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "").strip()
TG_CHAT_ID = os.getenv("TG_CHAT_ID", "").strip()

IS_PROXY = os.getenv("IS_PROXY", "false").lower() == "true"
PROXY_SERVER = os.getenv(
    "PROXY_SERVER",
    "socks5://127.0.0.1:1080"
).strip()

MANUAL_RUN = os.getenv(
    "MANUAL_RUN",
    "false"
).lower() == "true"

HEADLESS = os.getenv(
    "HEADLESS",
    "false"
).lower() == "true"

RENEW_THRESHOLD_DAYS = float(
    os.getenv(
        "RENEW_THRESHOLD_DAYS",
        "2"
    )
)

BJ_TZ = ZoneInfo("Asia/Shanghai")


def log(msg):
    print(
        f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}",
        flush=True
    )


def server_id():
    if not SERVER_URL:
        return "未知"

    return SERVER_URL.rstrip("/").split("/")[-1]


def node_status():
    if IS_PROXY:
        return "✅ 已启用"

    return "⚪ 未启用（直连）"


def beijing_now():
    return datetime.now(BJ_TZ)


def parse_remaining(text):
    """Parse '9d 12h 51m 30s' style countdown text."""
    if not text:
        return None

    match = re.search(
        r"(\d+)\s*d[^0-9a-z]*(\d+)\s*h(?:[^0-9a-z]*(\d+)\s*m)?(?:[^0-9a-z]*(\d+)\s*s)?",
        text,
        re.I,
    )

    if match:
        days = int(match.group(1))
        hours = int(match.group(2))
        minutes = int(match.group(3)) if match.group(3) else 0
        seconds = int(match.group(4)) if match.group(4) else 0

        return {
            "days": days,
            "hours": hours,
            "minutes": minutes,
            "seconds": seconds,
            "total": (
                days * 86400
                + hours * 3600
                + minutes * 60
                + seconds
            ),
            "text": f"{days}d {hours}h {minutes}m",
        }

    return None


def get_remaining(page):
    text = page.locator(
        "body"
    ).inner_text()

    return parse_remaining(text)


def remaining_expired(page):
    """Expired services may show 0d or an expired notice."""
    text = page.locator(
        "body"
    ).inner_text().lower()

    expired_words = [
        "expired",
        "suspendido",
        "suspended",
    ]

    return any(
        word in text
        for word in expired_words
    )


def tg(text):
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        log("⚠️ Telegram 未配置，跳过通知")
        return False

    try:
        proxies = None

        if IS_PROXY:
            proxies = {
                "http": PROXY_SERVER,
                "https": PROXY_SERVER,
            }

        response = requests.post(
            (
                "https://api.telegram.org/"
                f"bot{TG_BOT_TOKEN}/sendMessage"
            ),
            json={
                "chat_id": TG_CHAT_ID,
                "text": text,
            },
            timeout=20,
            proxies=proxies,
        )

        if response.ok:
            log("✅ Telegram 通知发送成功")
            return True

        log(
            "❌ Telegram 通知失败: "
            + response.text
        )

        return False

    except Exception as exc:
        log(
            f"❌ Telegram 通知异常: {exc}"
        )
        return False


def current_ip():
    try:
        proxies = None

        if IS_PROXY:
            proxies = {
                "http": PROXY_SERVER,
                "https": PROXY_SERVER,
            }

        response = requests.get(
            "https://api.ipify.org",
            timeout=15,
            proxies=proxies,
        )

        if response.ok:
            return response.text.strip()

        return "获取失败"

    except Exception:
        return "获取失败"


def build_check_message(remaining, ip):
    now = beijing_now()

    lines = [
        "⏳ FenixHost 检查完成",
        "",
        f"🖥️ 服务器：#{server_id()}",
        f"🌐 节点状态：{node_status()}",
        f"📍 出口IP：{ip}",
        f"🕗 检查时间：{now.strftime('%Y/%m/%d %H:%M')}",
        "",
        "🔒 当前状态：未到续期时间",
    ]

    if remaining is not None:
        lines.append(
            f"⏱️ 剩余时间：{remaining['text']}"
        )

        expire = (
            now
            + timedelta(seconds=remaining["total"])
        )

        lines.append(
            "📆 预计到期："
            + expire.strftime("%Y/%m/%d %H:%M")
        )

    lines.append(
        "⏰ 自动检查：每天 08:30（北京时间）"
    )

    return "\n".join(lines)


def build_success_message(before, after, ip):
    now = beijing_now()

    before_text = (
        before["text"]
        if before
        else "未知"
    )

    after_text = (
        after["text"]
        if after
        else "未知"
    )

    return (
        "🎉 FenixHost 续期成功\n\n"
        f"🖥️ 服务器：#{server_id()}\n"
        f"🌐 节点状态：{node_status()}\n"
        f"📍 出口IP：{ip}\n"
        f"🕗 续期时间：{now.strftime('%Y/%m/%d %H:%M')}\n\n"
        f"📅 续期前：{before_text}\n"
        f"✅ 续期后：{after_text}\n\n"
        "⏰ 自动检查：每天 08:30（北京时间）"
    )


def build_error_message(title, reason, ip):
    now = beijing_now()

    return (
        f"{title}\n\n"
        f"🖥️ 服务器：#{server_id()}\n"
        f"🌐 节点状态：{node_status()}\n"
        f"📍 出口IP：{ip}\n"
        f"🕗 检查时间：{now.strftime('%Y/%m/%d %H:%M')}\n\n"
        f"⚠️ 原因：{reason}"
    )


def first_visible(page, selectors):
    for selector in selectors:
        locator = page.locator(
            selector
        ).first

        try:
            if (
                locator.count()
                and locator.is_visible()
            ):
                return locator

        except Exception:
            pass

    return None


def turnstile_solved(page):
    try:
        return page.evaluate(
            "() => {"
            " const el = document.querySelector("
            "'input[name=\"cf-turnstile-response\"]'"
            ");"
            " return !!(el && el.value"
            " && el.value.length > 10);"
            "}"
        )

    except Exception:
        return False


def try_click_turnstile(page):
    selectors = [
        "input[type='checkbox']",
        "input",
        "label",
        "body",
    ]

    try:
        frame = page.frame_locator(
            "iframe[src*='challenges.cloudflare.com']"
        )

        for sel in selectors:
            try:
                frame.locator(
                    sel
                ).first.click(
                    timeout=2000
                )

                return True

            except Exception:
                pass

    except Exception:
        pass

    try:
        for frame in page.frames:
            if (
                "challenges.cloudflare.com"
                in (frame.url or "")
            ):
                for sel in selectors:
                    try:
                        loc = frame.locator(
                            sel
                        ).first

                        if loc.count():
                            loc.click(
                                timeout=2000
                            )

                            return True

                    except Exception:
                        pass

    except Exception:
        pass

    return False


def wait_turnstile(page, timeout):
    log(
        "⏳ 等待 Cloudflare Turnstile "
        "校验..."
    )

    start = time.time()
    attempts = 0

    while time.time() - start < timeout:
        if turnstile_solved(page):
            log(
                "✅ Turnstile 校验已通过"
            )

            return True

        if (
            time.time() - start > 5
            and attempts < 10
        ):
            if try_click_turnstile(page):
                attempts += 1

                log(
                    "🖱️ 已尝试点击 "
                    f"Turnstile 验证框"
                    f"（第 {attempts} 次）"
                )

        page.wait_for_timeout(3000)

    log(
        "⚠️ Turnstile 未在限时内通过，"
        "仍尝试提交"
    )

    return False



def parse_cookies(cookie_str):
    cookies = []

    for pair in cookie_str.split(";"):
        pair = pair.strip()

        if "=" in pair:
            name, value = pair.split(
                "=",
                1,
            )

            cookies.append({
                "name": name.strip(),
                "value": value.strip(),
                "domain": "fenixhost.net",
                "path": "/",
            })

    return cookies


def inject_login(page):
    cookies = parse_cookies(FENIX_COOKIE)

    if not cookies:
        log("❌ FENIX_COOKIE 解析为空")
        return False

    page.context.add_cookies(cookies)

    page.goto(
        SERVER_URL,
        wait_until="domcontentloaded",
        timeout=60000,
    )

    page.wait_for_timeout(3000)

    if (
        "/login" in page.url
        or "/services/" not in page.url
    ):
        log(
            "❌ Cookie 已过期或无效，"
            "请重新导出 FENIX_COOKIE"
        )

        return False

    log("✅ Cookie 注入成功，已进入服务页")

    return True


def login_if_needed(page):
    page.goto(
        SERVER_URL,
        wait_until="domcontentloaded",
        timeout=60000,
    )

    page.wait_for_timeout(3000)

    if (
        "/login" not in page.url
        and "/services/" in page.url
    ):
        return True

    email = first_visible(
        page,
        [
            "input#email",
            'input[name="email"]',
            'input[type="email"]',
        ],
    )

    password = first_visible(
        page,
        [
            "input#password",
            'input[name="password"]',
            'input[type="password"]',
        ],
    )

    if not email or not password:
        page.goto(
            "https://fenixhost.net/login",
            wait_until="domcontentloaded",
            timeout=60000,
        )

        page.wait_for_timeout(3000)

        email = first_visible(
            page,
            [
                "input#email",
                'input[name="email"]',
                'input[type="email"]',
            ],
        )

        password = first_visible(
            page,
            [
                "input#password",
                'input[name="password"]',
                'input[type="password"]',
            ],
        )

    if not FENIX_LOGIN or not FENIX_PASSWORD:
        log(
            "❌ 缺少 FENIX_LOGIN "
            "/ FENIX_PASSWORD"
        )
        return False

    for attempt in range(2):
        if attempt > 0:
            log(
                "🔄 第 "
                f"{attempt + 1}"
                " 次重试登录..."
            )

            page.goto(
                "https://fenixhost.net/login",
                wait_until="domcontentloaded",
                timeout=60000,
            )

            page.wait_for_timeout(3000)

            email = first_visible(
                page,
                [
                    "input#email",
                    'input[name="email"]',
                    'input[type="email"]',
                ],
            )

            password = first_visible(
                page,
                [
                    "input#password",
                    'input[name="password"]',
                    'input[type="password"]',
                ],
            )

            if not email or not password:
                break

        log("🔐 正在登录 FenixHost...")

        email.fill(FENIX_LOGIN)
        password.fill(FENIX_PASSWORD)

        wait_turnstile(page, 60)

        submit = first_visible(
            page,
            [
                'button[type="submit"]',
                'button:has-text("Sign in")',
                'button:has-text("Iniciar sesión")',
            ],
        )

        if not submit:
            log("❌ 没找到登录按钮")
            continue

        submit.click()

        for _ in range(10):
            page.wait_for_timeout(2000)

            if "/login" not in page.url:
                break

        if "/login" not in page.url:
            break

        log(
            "⚠️ 登录后仍停留在登录页"
        )

    if "/login" in page.url:
        body = page.locator(
            "body"
        ).inner_text().lower()

        if "credential" in body or (
            "incorrect" in body
        ):
            log(
                "❌ 账号或密码错误"
            )

        return False

    page.goto(
        SERVER_URL,
        wait_until="domcontentloaded",
        timeout=60000,
    )

    page.wait_for_timeout(2000)

    return (
        "/login" not in page.url
        and "/services/" in page.url
    )


def find_renew_button(page):
    candidates = [
        page.get_by_role(
            "button",
            name=re.compile(
                r"^(?:Renovar|Renew)(?:\s+(?:now|ahora))?$",
                re.I,
            ),
        ),
        page.get_by_role(
            "link",
            name=re.compile(
                r"^(?:Renovar|Renew)(?:\s+(?:now|ahora))?$",
                re.I,
            ),
        ),
        page.locator(
            'button:has-text("Renovar")'
        ),
        page.locator(
            'button:has-text("Renew")'
        ),
        page.locator(
            'a:has-text("Renovar")'
        ),
        page.locator(
            'a:has-text("Renew")'
        ),
    ]

    for group in candidates:
        try:
            count = group.count()

            for i in range(count):
                item = group.nth(i)

                label = (
                    item.inner_text()
                    or ""
                ).strip()

                if re.search(
                    r"cancel|cancelar|plan",
                    label,
                    re.I,
                ):
                    continue

                if item.is_visible():
                    return item

        except Exception:
            pass

    return None


def confirm_renewal(page):
    """Wait for the Alpine confirmation modal and click confirm."""
    page.wait_for_timeout(1500)

    modal = page.locator(
        "div.fixed.inset-0"
    ).last

    try:
        if (
            modal.count()
            and modal.is_visible()
        ):
            buttons = modal.locator(
                "button:visible"
            )

            for i in range(buttons.count()):
                button = buttons.nth(i)

                label = (
                    button.inner_text()
                    or ""
                ).strip()

                if re.search(
                    r"cancel|cancelar|close|cerrar",
                    label,
                    re.I,
                ):
                    continue

                if (
                    label
                    and button.is_enabled()
                    and "loading" not in label.lower()
                ):
                    log(
                        "✅ 确认弹窗已打开，"
                        f"点击确认按钮: {label}"
                    )

                    button.click()

                    return True

    except Exception:
        pass

    log("❌ 未找到续期确认弹窗")
    return False


def renewal_succeeded(before, after):
    if before is None or after is None:
        return False

    return (
        after["total"]
        > before["total"] + 3600
    )


def wait_for_renewal_result(page, before):
    after = get_remaining(page)

    for attempt in range(5):
        after = get_remaining(page)

        if renewal_succeeded(
            before,
            after,
        ):
            return True, after

        page.wait_for_timeout(2000)

        if attempt == 1:
            page.reload(
                wait_until="domcontentloaded",
                timeout=60000,
            )
            page.wait_for_timeout(2000)

    return False, after


def main():
    if not SERVER_URL.startswith(
        "https://fenixhost.net/services/"
    ):
        log("❌ FENIX_SERVER_URL 不正确")

        tg(
            "❌ FenixHost 配置错误\n"
            "FENIX_SERVER_URL 不是服务详情页地址"
        )

        return 1

    log("======================================")
    log(" FenixHost Free Auto Renew")
    log("======================================")

    log(
        f"🌐 节点状态：{node_status()}"
    )

    ip = current_ip()

    log(
        f"📍 当前出口IP：{ip}"
    )

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=HEADLESS,
            proxy={
                "server": PROXY_SERVER
            }
            if IS_PROXY
            else None,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
            ],
        )

        context = browser.new_context(
            viewport={
                "width": 1440,
                "height": 1000,
            },
            user_agent=(
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/128.0.0.0 Safari/537.36"
            ),
        )

        page = context.new_page()

        try:
            if FENIX_COOKIE:
                logged_in = inject_login(page)
                fail_reason = (
                    "Cookie 已过期，"
                    "请重新导出 FENIX_COOKIE"
                )
            else:
                logged_in = login_if_needed(page)
                fail_reason = (
                    "登录失败或遇到安全验证"
                )

            if not logged_in:
                page.screenshot(
                    path="fenix_login_fail.png",
                    full_page=True,
                )

                tg(
                    build_error_message(
                        "❌ FenixHost 登录失败",
                        fail_reason,
                        ip,
                    )
                )

                return 1

            log("✅ 登录成功")

            before = get_remaining(page)

            if before is not None:
                log(
                    f"📅 当前剩余时间：{before['text']}"
                )

            else:
                log(
                    "⚠️ 未识别到倒计时"
                )

            threshold = (
                RENEW_THRESHOLD_DAYS * 86400
            )

            if (
                remaining_expired(page)
                or (
                    before is not None
                    and before["total"] > threshold
                )
            ):
                log(
                    "⏳ 目前未到续期窗口，"
                    "不进行操作"
                )

                if MANUAL_RUN:
                    tg(
                        build_check_message(
                            before,
                            ip,
                        )
                    )

                return 0

            button = find_renew_button(page)

            if not button:
                page.screenshot(
                    path="fenix_no_renew_button.png",
                    full_page=True,
                )

                tg(
                    build_error_message(
                        "⚠️ FenixHost 需要检查",
                        "没有找到可用的 Renovar 按钮",
                        ip,
                    )
                )

                return 1

            try:
                disabled = button.is_disabled()

            except Exception:
                disabled = False

            if disabled:
                log(
                    "⏳ Renovar 按钮当前不可点击"
                )

                if MANUAL_RUN:
                    tg(
                        build_check_message(
                            before,
                            ip,
                        )
                    )

                return 0

            log(
                "🔄 已到续期窗口，"
                "点击 Renovar..."
            )

            button.click()

            if not confirm_renewal(page):
                page.screenshot(
                    path="fenix_confirm_fail.png",
                    full_page=True,
                )

                tg(
                    build_error_message(
                        "❌ FenixHost 续期确认失败",
                        "点击 Renovar 后未出现确认弹窗"
                        "或未能点击确认按钮",
                        ip,
                    )
                )

                return 1

            success, after = wait_for_renewal_result(
                page,
                before,
            )

            if success:
                log(
                    "✅ 续期成功："
                    f"{before['text']} -> {after['text']}"
                )

                tg(
                    build_success_message(
                        before,
                        after,
                        ip,
                    )
                )

                return 0

            page.screenshot(
                path="fenix_renew_fail.png",
                full_page=True,
            )

            after_text = (
                after["text"]
                if after
                else "未识别"
            )

            log(
                "❌ 续期失败："
                f"{before['text']} -> {after_text}"
            )

            tg(
                build_error_message(
                    "❌ FenixHost 续期失败",
                    (
                        f"倒计时未变化："
                        f"{before['text']} -> {after_text}"
                    ),
                    ip,
                )
            )

            return 1

        except Exception as exc:
            log(f"❌ 运行异常: {exc}")

            try:
                page.screenshot(
                    path="fenix_error.png",
                    full_page=True,
                )

            except Exception:
                pass

            tg(
                build_error_message(
                    "❌ FenixHost 运行异常",
                    str(exc)[:300],
                    ip,
                )
            )

            return 1

        finally:
            browser.close()


if __name__ == "__main__":
    sys.exit(main())