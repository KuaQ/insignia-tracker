from playwright.sync_api import sync_playwright

class BrowserFetchError(RuntimeError):
    pass

def browser_fetch(url: str, timeout_ms: int = 30000):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            locale="pl-PL",
            timezone_id="Europe/Warsaw",
            viewport={"width": 1440, "height": 1000},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/140.0.0.0 Safari/537.36"
            ),
            extra_http_headers={
                "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
                "Upgrade-Insecure-Requests": "1",
            },
        )
        page = context.new_page()
        try:
            response = page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            page.wait_for_timeout(2500)
            status = response.status if response else None
            html = page.content()
            final_url = page.url
            title = page.title()
            return {
                "status": status,
                "html": html,
                "url": final_url,
                "title": title,
            }
        except Exception as e:
            raise BrowserFetchError(str(e))
        finally:
            context.close()
            browser.close()
