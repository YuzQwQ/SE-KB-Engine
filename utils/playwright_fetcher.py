#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Playwright 抓取辅助模块（同步 API）
用于在静态抓取不足时获取渲染后的 HTML。

说明：
- 该模块使用 Playwright 的同步 API，避免与现有异步事件循环冲突。
- 若环境未安装 Playwright，则返回 None 并在日志中提示。
"""

from typing import Optional, List
import random
import time

import logging

logger = logging.getLogger(__name__)

BLOCK_PATTERNS: List[str] = [
    "**/*googletagmanager.com/**",
    "**/*google-analytics.com/**",
    "**/*doubleclick.net/**",
    "**/*facebook.net/**",
    "**/*adsbygoogle.js**",
    "**/*.mp4",
    "**/*.webm",
    "**/*.mpeg",
]


def fetch_rendered_html_sync(
    url: str,
    timeout_ms: int = 30000,
    human_simulation: bool = False,
    proxy_server: Optional[str] = None,
) -> Optional[str]:
    """使用 Playwright 同步 API 获取渲染后的 HTML。

    Args:
        url: 目标网址
        timeout_ms: 页面加载或选择器等待的超时时间（毫秒）

    Returns:
        渲染后的 HTML 字符串，若 Playwright 不可用或失败则返回 None
    """
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        logger.warning(f"Playwright 未安装或导入失败，跳过动态渲染：{e}")
        return None

    try:
        with sync_playwright() as p:
            # 随机 UA 与视口，减少固定指纹
            ua_pool = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            ]
            ua = random.choice(ua_pool)
            vw = random.randint(1200, 1920)
            vh = random.randint(720, 1080)

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

            # 低成本 stealth：去除 webdriver 与补齐属性
            if human_simulation:
                try:
                    context.add_init_script(
                        """
                        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                        window.chrome = { runtime: {} };
                        Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN','zh','en-US','en'] });
                        Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3,4,5] });
                        """
                    )
                except Exception:
                    pass

            # 屏蔽常见广告/追踪/大视频资源，降低带宽与渲染压力
            def route_handler(route):
                req = route.request
                url_lc = req.url.lower()
                for pattern in BLOCK_PATTERNS:
                    # 简化匹配：直接用字符串包含判断，避免过度复杂化通配处理
                    token = pattern.strip("*")
                    if token and token in url_lc:
                        try:
                            route.abort()
                        except Exception:
                            pass
                        return
                try:
                    route.continue_()
                except Exception:
                    pass

            try:
                page.route("**/*", route_handler)
            except Exception:
                # 某些环境可能不支持 route，忽略
                pass

            page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")

            # 优先等待主体选择器，其次等待网络空闲
            selectors = "article, main, #content, .post, .article, .content, [role='main']"
            try:
                page.wait_for_selector(selectors, timeout=timeout_ms)
            except Exception:
                try:
                    page.wait_for_load_state("networkidle", timeout=timeout_ms)
                except Exception:
                    # 不可用则忽略，直接尝试取内容
                    pass

            # 轻量滚动 + 人类行为模拟（随机步长/停顿/鼠标移动、随机停留>7s）
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
                try:
                    for _ in range(random.randint(3, 6)):
                        x = random.randint(10, max(11, vw - 10))
                        y = random.randint(10, max(11, vh - 10))
                        page.mouse.move(x, y, steps=random.randint(2, 5))
                        time.sleep(random.uniform(0.2, 0.8))
                except Exception:
                    pass

                try:
                    import os

                    min_dwell = float(os.getenv("HUMAN_SIM_MIN_DWELL_SEC", "7"))
                    max_dwell = float(os.getenv("HUMAN_SIM_MAX_DWELL_SEC", "12"))
                    dwell = max(min_dwell, random.uniform(min_dwell, max_dwell))
                    time.sleep(dwell)
                except Exception:
                    pass

            html = page.content()
            try:
                context.close()
                browser.close()
            except Exception:
                pass
            return html
    except Exception as e:
        logger.warning(f"Playwright 渲染失败：{e}")
        return None
