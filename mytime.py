from playwright.sync_api import sync_playwright

URL_LOGIN = "https://mytime.selise.biz/"
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

    # 4. Wait for login to complete
    page.wait_for_load_state("networkidle")

    # 5. Click "Create Timesheet for Today"
    page.wait_for_selector("button:has-text('Create Timesheet for Today')", state="visible")
    page.click("button:has-text('Create Timesheet for Today')")

    # 6. Wait for redirect, then click "Edit"
    page.wait_for_load_state("networkidle")
    page.wait_for_selector("button:has-text('Edit')", state="visible")
    page.click("button:has-text('Edit')")

    # 7. Wait for the table to render, then fill "General Admin" column input with 9
    page.wait_for_selector("table[data-test-id='table-record-list'] tbody tr", state="visible")
    col_index = page.evaluate("""
        () => {
            const headers = Array.from(document.querySelectorAll(
                'table[data-test-id="table-record-list"] thead th'
            ));
            return headers.findIndex(th => th.textContent.includes('General Admin'));
        }
    """)
    general_admin_input = page.locator(
        f'table[data-test-id="table-record-list"] tbody tr:first-child '
        f'td:nth-child({col_index + 1}) input[type="number"]'
    )
    general_admin_input.fill("9")

    # 8. Click Save
    page.wait_for_selector("button[data-test-id='button-save']", state="visible")
    page.click("button[data-test-id='button-save']")

    # 9. Wait 50 seconds
    page.wait_for_timeout(50000)

    browser.close()