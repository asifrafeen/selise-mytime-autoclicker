"""Playwright automation: log in to mytime.selise.biz and submit timesheet."""

import logging
import threading

from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)

URL_LOGIN = "https://mytime.selise.biz/"

# Threading event so the job can be cancelled cleanly on app exit
_cancel_event = threading.Event()


def cancel() -> None:
    """Signal a running job to abort at the next checkpoint."""
    _cancel_event.set()


def _check_cancelled() -> None:
    if _cancel_event.is_set():
        raise InterruptedError("Job was cancelled.")


def run_timesheet(username: str, password: str, headless: bool = True) -> None:
    """
    Full automation flow:
      1. Log in
      2. Create Timesheet for Today
      3. Click Edit
      4. Fill General Admin column with 9 hours
      5. Save
    """
    _cancel_event.clear()
    logger.info("Starting timesheet automation (headless=%s)", headless)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context()
        page = context.new_page()

        try:
            # 1. Login
            logger.info("Navigating to login page")
            page.goto(URL_LOGIN)

            page.wait_for_selector("input[name='email']", state="visible")
            page.fill("input[name='email']", username)
            _check_cancelled()

            page.wait_for_selector("input[name='password']", state="visible")
            page.fill("input[name='password']", password)
            _check_cancelled()

            page.wait_for_selector(
                "button[type='submit']:not([disabled])", state="visible"
            )
            page.click("button[type='submit']")
            logger.info("Login submitted, waiting for page load")

            # 2. Wait for login, then create today's timesheet
            page.wait_for_load_state("networkidle")
            _check_cancelled()

            logger.info("Clicking 'Create Timesheet for Today'")
            page.wait_for_selector(
                "button:has-text('Create Timesheet for Today')", state="visible"
            )
            page.click("button:has-text('Create Timesheet for Today')")

            # 3. Click Edit after redirect
            page.wait_for_load_state("networkidle")
            _check_cancelled()

            logger.info("Clicking 'Edit'")
            page.wait_for_selector("button:has-text('Edit')", state="visible")
            page.click("button:has-text('Edit')")

            # 4. Fill General Admin column (locate dynamically — BVID IDs change)
            logger.info("Waiting for table to render")
            page.wait_for_selector(
                "table[data-test-id='table-record-list'] tbody tr", state="visible"
            )
            _check_cancelled()

            col_index = page.evaluate(
                """
                () => {
                    const headers = Array.from(document.querySelectorAll(
                        'table[data-test-id="table-record-list"] thead th'
                    ));
                    return headers.findIndex(
                        th => th.textContent.includes('General Admin')
                    );
                }
            """
            )

            if col_index == -1:
                raise RuntimeError("Could not find 'General Admin' column in table.")

            logger.info("Filling General Admin (column %d) with 9 hours", col_index)
            general_admin_input = page.locator(
                f"table[data-test-id='table-record-list'] tbody tr:first-child "
                f"td:nth-child({col_index + 1}) input[type='number']"
            )
            general_admin_input.fill("9")
            _check_cancelled()

            # 5. Save
            logger.info("Clicking Save")
            page.wait_for_selector(
                "button[data-test-id='button-save']", state="visible"
            )
            page.click("button[data-test-id='button-save']")

            page.wait_for_timeout(2000)
            logger.info("Timesheet submitted successfully")

        except InterruptedError:
            logger.warning("Automation was cancelled mid-run")
        except Exception:
            logger.exception("Automation failed")
            raise
        finally:
            browser.close()
