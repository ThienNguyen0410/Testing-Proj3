import os
import re
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.data_reader import EXPECTED_SLOTS, read_test_data


def _load_environment_file(path):
    if not path.is_file():
        return

    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8-sig").splitlines(), start=1
    ):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        key, separator, value = line.partition("=")
        key = key.strip()
        if not separator or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            raise ValueError(f"{path}:{line_number}: invalid environment entry")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        else:
            value = value.split(" #", maxsplit=1)[0].rstrip()
        os.environ[key] = value


_load_environment_file(PROJECT_ROOT / ".env")


def validate_data(data_path):
    rows = read_test_data(data_path)
    print(f"CSV OK: {len(rows)} test cases")
    for row in rows:
        print(f"  {row['test_id']}: {row['title']} [{row['scenario']}]")
    return 0


def _assert_expected(page, driver, row, config, stage):
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import Select, WebDriverWait

    for result_column, check_column, target_column, stage_column in EXPECTED_SLOTS:
        if row[stage_column] != stage:
            continue

        expected = row[result_column]
        check = row[check_column]
        target = row[target_column]
        if check == "text":
            WebDriverWait(driver, page.timeout).until(
                lambda browser: expected
                in browser.find_element(By.TAG_NAME, "body").text,
                message=f"Expected page text was not found: {expected}",
            )
        elif check == "element_present":
            selector = config["selectors"][target]
            WebDriverWait(driver, page.timeout).until(
                EC.presence_of_element_located(page._parse_locator(selector))
            )
        elif check == "value":
            selector = config["selectors"][target]
            locator = page._parse_locator(selector)
            WebDriverWait(driver, page.timeout).until(
                lambda browser: browser.find_element(*locator).get_attribute("value")
                == expected,
                message=f"Expected value {expected!r} in {target!r}",
            )
        elif check == "selected_value":
            selector = config["selectors"][target]
            locator = page._parse_locator(selector)
            WebDriverWait(driver, page.timeout).until(
                lambda browser: Select(browser.find_element(*locator))
                .first_selected_option.get_attribute("value")
                == expected,
                message=f"Expected selected value {expected!r} in {target!r}",
            )
        elif check == "not_created":
            selector = config["selectors"]["users_table"]
            table = WebDriverWait(driver, page.timeout).until(
                EC.presence_of_element_located(page._parse_locator(selector))
            )
            if target in table.text:
                raise AssertionError(
                    f"Cancelled user {target!r} appears in the users table"
                )
        else:
            raise ValueError(f"Unsupported expected-result check: {check}")


def _run_case(page, driver, row, config):
    page.open_create_form(config["base_url"])

    if row["scenario"] == "auth_options":
        page._click(page.selectors["auth_method"])
        _assert_expected(page, driver, row, config, "before_submit")
        return

    page.fill_form(row)
    _assert_expected(page, driver, row, config, "before_submit")

    pictures = [
        row["profile_picture"],
        row["profile_picture_2"],
    ]
    for index, picture in enumerate((value for value in pictures if value), start=1):
        page.upload_profile_picture(picture)
        _assert_expected(page, driver, row, config, f"after_upload_{index}")

    if row["scenario"] == "upload_invalid":
        return
    if row["scenario"] == "cancel":
        page.cancel()
        _assert_expected(page, driver, row, config, "after_cancel")
        return

    page.submit()
    _assert_expected(page, driver, row, config, "after_submit")

    if row["scenario"] in {
        "suspended_login",
        "no_login",
        "force_password_change",
    }:
        page.logout_current(config["base_url"])
        page.submit_login(
            config["base_url"], row["username"], row["password"]
        )
        _assert_expected(page, driver, row, config, "after_login")


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

    class DataDrivenMoodleTest(unittest.TestCase):
        def __init__(self, row):
            super().__init__("test_case")
            self.row = row

        @classmethod
        def setUpClass(cls):
            options = webdriver.ChromeOptions()
            if headless:
                options.add_argument("--headless=new")
            options.add_argument("--window-size=1440,1000")
            options.add_argument("--disable-notifications")

            cls.driver = webdriver.Chrome(options=options)
            cls.page = AddUserPage(cls.driver, config)
            try:
                cls.page.login(config["base_url"], username, password)
            except Exception:
                cls.driver.quit()
                raise

        @classmethod
        def tearDownClass(cls):
            cls.driver.quit()

        def test_case(self):
            _run_case(self.page, self.driver, self.row, config)

        def tearDown(self):
            if self.row["scenario"] in {
                "suspended_login",
                "no_login",
                "force_password_change",
            }:
                self.page.restore_admin_session(
                    config["base_url"], username, password
                )

        def __str__(self):
            return f"{self.row['test_id']} - {self.row['title']}"

    suite = unittest.TestSuite(DataDrivenMoodleTest(row) for row in rows)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1
