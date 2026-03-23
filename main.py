from playwright.sync_api import sync_playwright

URL_LOGIN = "https://hr.selise.biz/login"
URL_ATTENDANCE = "https://hr.selise.biz/hrd/attendance"

USERNAME = "username"
PASSWORD = "password"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()

    # 1. Go to login page
    page.goto(URL_LOGIN)

    # 2. Fill username & password
    page.wait_for_selector("input[name='email']", state="visible")
    page.fill("input[name='email']", USERNAME)
    page.wait_for_selector("input[name='password']", state="visible")
    page.fill("input[name='password']", PASSWORD)

    # 3. Click login button (wait for it to become enabled after form is filled)
    page.wait_for_selector("button[type='submit']:not([disabled])", state="visible")
    page.click("button[type='submit']")

    # 4. Wait for login to complete (important)
    page.wait_for_load_state("networkidle")

    # 5. Go to attendance page
    page.goto(URL_ATTENDANCE)

    # 6. Wait for button and click "Filter"
    page.wait_for_selector("button.primary-btn:has-text('Filter')")
    page.click("button.primary-btn:has-text('Filter')")

    # Keep browser open for a while (for debugging)
    # page.wait_for_timeout(10000)

    browser.close()