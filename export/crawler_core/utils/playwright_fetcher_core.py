from __future__ import annotations

from typing import Optional
import random
import time

BLOCK_PATTERNS = (
    ".*doubleclick\.net.*",
    ".*googletagmanager\.com.*",
    ".*google-analytics\.com.*",
    ".*adservice\.google\.com.*",
    ".*analytics.*",
    ".*\.mp4$",
    ".*video.*",
)


def fetch_rendered_html_sync(url: str, timeout_ms: int = 30000, human_simulation: bool = False, proxy_server: Optional[str] = None) -> Optional[str]:
    """使用 Playwright 同步渲染页面并返回 HTML。

    - 若 Playwright 未安装或失败，返回 None。
    - 会阻断常见广告/分析请求，等待主体选择器和网络空闲，并做轻量滚动。
    """
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return None

    try:
        with sync_playwright() as p:
            # 随机化 UA 与视口，尽量避免完全一致的指纹
            ua_pool = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            ]
            ua = random.choice(ua_pool)
            vw = random.randint(1200, 1920)
            vh = random.randint(720, 1080)

            # 通过禁用 AutomationControlled 降低 webdriver 识别概率
            launch_kwargs = {
                "headless": True,
                "args": ["--disable-blink-features=AutomationControlled"],
            }
            if proxy_server:
                launch_kwargs["proxy"] = {"server": proxy_server}
            browser = p.chromium.launch(**launch_kwargs)
            context = browser.new_context(
                user_agent=ua,
                viewport={"width": vw, "height": vh},
                locale=random.choice(["zh-CN", "en-US", "zh-TW"]),
                timezone_id=random.choice(["Asia/Shanghai", "UTC", "Etc/GMT-8"]),
            )
            page = context.new_page()

            # 低成本 stealth：去除 navigator.webdriver、补齐常用属性
            if human_simulation:
                try:
                    context.add_init_script(
                        """
                        // webdriver 标记
                        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                        // 补齐 chrome 对象
                        window.chrome = { runtime: {} };
                        // 语言与插件
                        Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN','zh','en-US','en'] });
                        Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3,4,5] });
                        """
                    )
                except Exception:
                    pass

            # 阻断不必要资源
            def _route(route, request):
                req_url = request.url
                if any(__import__('re').match(pat, req_url) for pat in BLOCK_PATTERNS):
                    return route.abort()
                return route.continue_()

            page.route("**/*", _route)
            page.set_default_timeout(timeout_ms)
            page.goto(url, wait_until="domcontentloaded")

            # 等待主体选择器或网络空闲
            main_selectors = ['article', 'main', '#content', '.post', '.article', '.content']
            for sel in main_selectors:
                try:
                    page.wait_for_selector(sel, timeout=2000)
                    break
                except Exception:
                    continue

            try:
                page.wait_for_load_state('networkidle', timeout=4000)
            except Exception:
                pass

            # 轻量滚动触发懒加载 + 人类行为模拟（随机步长/停顿/鼠标移动）
            try:
                step = random.randint(500, 1000)
                delay_ms = random.randint(120, 220)
                page.evaluate(
                    f"""
                    () => {{
                      return new Promise((resolve) => {{
                        let y = 0; let step = {step}; let max = document.body.scrollHeight;
                        function sc() {{ y += step; window.scrollTo(0, y); if (y < max) {{ setTimeout(sc, {delay_ms}); }} else {{ resolve(true); }} }}
                        sc();
                      }});
                    }}
                    """
                )
            except Exception:
                pass

            if human_simulation:
                # 鼠标随机移动 + 停留时间 >= 7s（可通过环境变量调整）
                try:
                    # 随机移动几次鼠标
                    for _ in range(random.randint(3, 6)):
                        x = random.randint(10, max(11, vw - 10))
                        y = random.randint(10, max(11, vh - 10))
                        page.mouse.move(x, y, steps=random.randint(2, 5))
                        time.sleep(random.uniform(0.2, 0.8))
                except Exception:
                    pass

                try:
                    min_dwell = float(__import__('os').getenv('HUMAN_SIM_MIN_DWELL_SEC', '7'))
                    max_dwell = float(__import__('os').getenv('HUMAN_SIM_MAX_DWELL_SEC', '12'))
                    dwell = max(min_dwell, random.uniform(min_dwell, max_dwell))
                    time.sleep(dwell)
                except Exception:
                    pass

            html = page.content()
            context.close()
            browser.close()
            return html
    except Exception:
        return None