import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.data_reader import read_test_data

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env", override=True)

def validate_data(data_path):
    rows = read_test_data(data_path)
    print(f"CSV OK: {len(rows)} test cases")
    for row in rows:
        print(f"  {row['test_id']}: {row['title']}")
    return 0


def _assert_case(page, driver, row, config):
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait

    page.open_create_form(config["base_url"])
    page.fill_form(row)

    if row["expected"] == "cancelled":
        page.cancel()
        create_form_url = (
            f"{config['base_url'].rstrip('/')}{config['urls']['create_user']}"
        ).rstrip("/")
        WebDriverWait(driver, page.timeout).until(
            lambda browser: browser.current_url.rstrip("/") != create_form_url
        )
        WebDriverWait(driver, page.timeout).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, page.selectors["users_table"])
            )
        )
        if row["username"] and row["username"] in driver.find_element(
            By.TAG_NAME, "body"
        ).text:
            raise AssertionError("Cancelled username appears on the user list")
        return "Cancel returned to the user list; username was not created"

    page.submit()
    if row["expected"] in {"success", "duplicate"}:
        WebDriverWait(driver, page.timeout).until(
            lambda browser: row["expected_text"]
            in browser.find_element(By.TAG_NAME, "body").text
        )
        return f"Found expected text: {row['expected_text']}"

    WebDriverWait(driver, page.timeout).until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, page.selectors["validation_feedback"])
        )
    )
    return "Validation feedback element is present"


def run_suite(config, data_path, base_url=None, headless=True, validate_only=False):
    rows = read_test_data(data_path)
    if validate_only:
        return validate_data(data_path)

    effective_base_url = (
        base_url or os.environ.get("MOODLE_BASE_URL") or config.get("base_url", "")
    ).strip()
    if not effective_base_url:
        raise ValueError(
            "Set MOODLE_BASE_URL, configure base_url, or pass --base-url."
        )
    config = dict(config)
    config["base_url"] = effective_base_url.rstrip("/")

    username = os.environ.get("MOODLE_USERNAME", "")
    password = os.environ.get("MOODLE_PASSWORD", "")
    if not username or not password:
        raise ValueError(
            "Set MOODLE_USERNAME and MOODLE_PASSWORD in environment variables."
        )

    from selenium import webdriver

    from pages.add_user_page import AddUserPage

    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1440,1000")
    options.add_argument("--disable-notifications")

    driver = webdriver.Chrome(options=options)
    passed = 0
    failed = 0
    try:
        page = AddUserPage(driver, config)
        page.login(config["base_url"], username, password)

        for row in rows:
            try:
                detail = _assert_case(page, driver, row, config)
                passed += 1
                print(f"PASS {row['test_id']} - {row['title']}: {detail}")
            except Exception as error:
                failed += 1
                print(f"FAIL {row['test_id']} - {row['title']}: {error}")
    finally:
        driver.quit()

    print(f"\nResult: {passed} passed, {failed} failed, {len(rows)} total")
    return 0 if failed == 0 else 1
