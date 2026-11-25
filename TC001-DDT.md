# TC-001 Selenium Data-Driven Testing

## Scope

This suite contains the 52 TC-001 scenarios from `katalon/TC001-AddUser.krecorder`.
The CSV stores each test case as a row with separate input columns and explicit expected-result columns. The Selenium implementation uses Python `unittest`; it creates one unittest case per CSV row.

## Level 1 and Level 2

| Level | Where test items are configured |
|---|---|
| Level 1 | `tests/FR/TC001_DDT_Level1.py`: site routes and element selectors are defined in the Python `CONFIG`. Test values and expected results are in the CSV. |
| Level 2 | `test_data/tc001_ddt_config.json`: site routes and element selectors are loaded from JSON. Test values and expected results are in the same CSV. |

Both levels share the same page object and `unittest` runner. The difference is the source of URLs and selectors, not separate test logic.

## CSV layout

The CSV has one row per test case. Common fields include username, authentication method, password, names, email, profile fields, phones, tags, checkbox settings, and upload fixture paths. `scenario` selects the small number of different flows (for example cancellation, failed login, or image upload).

`Expected Result`, `Expected Result 2`, and `Expected Result 3` hold the expected outcomes. The matching `Expected Check`, `Expected Target`, and `Expected Stage` columns say how and when to verify each outcome. Supported checks are text, element presence, input value, selected value, and cancelled-user absence. This retains recorder assertions such as invalid-feedback presence without inventing validation messages.

Example rows (only the most relevant columns shown):

| Test ID | Scenario | Username | Expected Result | Expected Check | Expected Stage |
|---|---|---|---|---|---|
| TC-001-001 | create_user | tc001_full_001 | Changes saved | text | after_submit |
| TC-001-008 | create_user | tc001_full_008 | present | element_present | after_submit |
| TC-001-026 | create_user | tc001_full_026 | 1111111111 | value | after_submit |
| TC-001-046 | suspended_login | tc001_full_046 | User created successfully | text | after_submit |
| TC-001-051 | upload_multiple | tc001_full_051 | maximum number of files: 1 | text | after_upload_1 |

The complete dataset is `test_data/add_user_test_data.csv`; upload fixtures are under `test_data/assets/`.

## Configure and run

Set `MOODLE_BASE_URL`, `MOODLE_USERNAME`, and `MOODLE_PASSWORD` in the environment or project-root `.env`. The runner supports simple `KEY=VALUE` entries in `.env`; credentials are not stored in the CSV or source code. Use a disposable Moodle instance: successful cases create accounts.

From the project root on Windows:

```powershell
python -m tests.FR.TC001_DDT_Level1 --validate-only
python -m tests.FR.TC001_DDT_Level1 --headed
python -m tests.FR.TC001_DDT_Level2 --validate-only
python -m tests.FR.TC001_DDT_Level2 --headed
```

From WSL/Linux:

```bash
python3 -m tests.FR.TC001_DDT_Level1 --validate-only
python3 -m tests.FR.TC001_DDT_Level1 --headed
python3 -m tests.FR.TC001_DDT_Level2 --validate-only
python3 -m tests.FR.TC001_DDT_Level2 --headed
```

`--validate-only` checks the CSV schema and all 52 rows without opening Chrome. Full runs use `unittest` and Selenium; Selenium and Chrome must be installed in the selected Python environment. Level 2's configured base URL can be overridden with `--base-url` or `MOODLE_BASE_URL`.

## Source code

The following listings are embedded from the current source files. The CSV itself is maintained separately so its rows remain easy to edit in a spreadsheet.

### `utils/data_reader.py`

```python
import csv
from itertools import chain
from pathlib import Path


REQUIRED_COLUMNS = {
    "test_id",
    "title",
    "scenario",
    "username",
    "authentication",
    "password",
    "firstname",
    "lastname",
    "email",
    "city",
    "moodlenet_profile",
    "country",
    "timezone",
    "firstname_phonetic",
    "lastname_phonetic",
    "middle_name",
    "alternate_name",
    "id_number",
    "institution",
    "department",
    "phone",
    "mobile_phone",
    "address",
    "interests",
    "email_visibility",
    "language",
    "create_password",
    "force_password_change",
    "suspended",
    "profile_picture",
    "profile_picture_2",
    "Expected Result",
    "Expected Check",
    "Expected Target",
    "Expected Stage",
    "Expected Result 2",
    "Expected Check 2",
    "Expected Target 2",
    "Expected Stage 2",
    "Expected Result 3",
    "Expected Check 3",
    "Expected Target 3",
    "Expected Stage 3",
}
SCENARIOS = {
    "create_user",
    "auth_options",
    "cancel",
    "suspended_login",
    "no_login",
    "force_password_change",
    "upload_valid",
    "upload_invalid",
    "upload_multiple",
}
EXPECTED_CHECKS = {
    "text",
    "element_present",
    "value",
    "selected_value",
    "not_created",
}
EXPECTED_STAGES = {
    "before_submit",
    "after_upload_1",
    "after_upload_2",
    "after_submit",
    "after_login",
    "after_cancel",
}
EXPECTED_SLOTS = (
    ("Expected Result", "Expected Check", "Expected Target", "Expected Stage"),
    ("Expected Result 2", "Expected Check 2", "Expected Target 2", "Expected Stage 2"),
    ("Expected Result 3", "Expected Check 3", "Expected Target 3", "Expected Stage 3"),
)


def read_test_data(file_path):
    path = Path(file_path)
    with path.open(mode="r", encoding="utf-8-sig", newline="") as file:
        header_line = file.readline()
        while header_line and not header_line.strip():
            header_line = file.readline()
        if not header_line:
            raise ValueError(f"{path} contains no CSV header")

        reader = csv.DictReader(chain((header_line,), file))
        missing_columns = REQUIRED_COLUMNS.difference(reader.fieldnames or [])
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(f"{path} is missing required CSV columns: {missing}")

        rows = []
        seen_ids = set()
        for line_number, row in enumerate(reader, start=2):
            cleaned = {
                key: (value or "").strip()
                for key, value in row.items()
                if key is not None
            }
            test_id = cleaned.get("test_id", "")
            if not test_id:
                raise ValueError(f"{path}:{line_number}: test_id must not be empty")
            if test_id in seen_ids:
                raise ValueError(f"{path}:{line_number}: duplicate test_id {test_id}")
            seen_ids.add(test_id)

            if cleaned.get("scenario") not in SCENARIOS:
                raise ValueError(
                    f"{path}:{line_number}: unsupported scenario "
                    f"{cleaned.get('scenario')!r}"
                )
            if not any(cleaned[result] for result, _, _, _ in EXPECTED_SLOTS):
                raise ValueError(
                    f"{path}:{line_number}: at least one Expected Result is required"
                )
            for result_column, check_column, target_column, stage_column in EXPECTED_SLOTS:
                result = cleaned[result_column]
                check = cleaned[check_column]
                target = cleaned[target_column]
                stage = cleaned[stage_column]
                if not result and not (check or target or stage):
                    continue
                if (
                    not result
                    or check not in EXPECTED_CHECKS
                    or stage not in EXPECTED_STAGES
                ):
                    raise ValueError(
                        f"{path}:{line_number}: invalid expectation in "
                        f"{result_column}"
                    )
                if check in {
                    "element_present",
                    "value",
                    "selected_value",
                    "not_created",
                } and not target:
                    raise ValueError(
                        f"{path}:{line_number}: target required for {result_column}"
                    )
            rows.append(cleaned)

    if not rows:
        raise ValueError(f"{path} contains no test rows")
    return rows
```

### `utils/ddt_runner.py`

```python
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
```

### `pages/add_user_page.py`

```python
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait


class AddUserPage:
    def __init__(self, driver, config):
        self.driver = driver
        self.config = config
        self.timeout = int(config.get("timeout_seconds", 10))
        self.selectors = config["selectors"]
        self.urls = config["urls"]

    @staticmethod
    def _parse_locator(locator):
        if locator.startswith("css="):
            return By.CSS_SELECTOR, locator[4:]
        if locator.startswith("xpath="):
            return By.XPATH, locator[6:]
        if locator.startswith("id="):
            return By.ID, locator[3:]
        if locator.startswith("id_"):
            return By.ID, locator
        return By.CSS_SELECTOR, locator

    def _wait_visible(self, selector):
        return WebDriverWait(self.driver, self.timeout).until(
            EC.visibility_of_element_located(self._parse_locator(selector))
        )

    def _wait_clickable(self, selector):
        return WebDriverWait(self.driver, self.timeout).until(
            EC.element_to_be_clickable(self._parse_locator(selector))
        )

    def _click(self, selector):
        element = self._wait_clickable(selector)
        self.driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center', inline: 'center', behavior: 'instant'});",
            element,
        )
        WebDriverWait(self.driver, self.timeout).until(
            lambda driver: driver.execute_script(
                """
                const rect = arguments[0].getBoundingClientRect();
                const x = rect.left + rect.width / 2;
                const y = rect.top + rect.height / 2;
                return rect.width > 0 && rect.height > 0
                    && x >= 0 && x < window.innerWidth
                    && y >= 0 && y < window.innerHeight;
                """,
                element,
            ),
            message=f"Click target {selector!r} did not enter the viewport.",
        )
        element = self._wait_clickable(selector)
        try:
            element.click()
        except ElementClickInterceptedException as error:
            blocker = self.driver.execute_script(
                """
                const rect = arguments[0].getBoundingClientRect();
                const x = rect.left + rect.width / 2;
                const y = rect.top + rect.height / 2;
                const element = document.elementFromPoint(x, y);
                const blocker = element
                    ? element.tagName.toLowerCase()
                    + (element.id ? "#" + element.id : "")
                    + (element.className && typeof element.className === "string"
                        ? "." + element.className.trim().replace(/\\s+/g, ".")
                        : "")
                    : "no element at click point";
                return JSON.stringify({
                    viewport: [window.innerWidth, window.innerHeight],
                    target: [rect.left, rect.top, rect.width, rect.height],
                    blocker: blocker
                });
                """,
                element,
            )
            raise ElementClickInterceptedException(
                f"Click on {selector!r} failed; diagnostics: {blocker}. {error}"
            ) from error

    def _type_and_wait(self, selector, value):
        locator = self._parse_locator(selector)

        def populate_field(driver):
            try:
                element = driver.find_element(*locator)
                if not element.is_displayed():
                    return False
                if element.get_attribute("value") == value:
                    return True
                element.clear()
                if value:
                    element.send_keys(value)
                return element.get_attribute("value") == value
            except StaleElementReferenceException:
                return False

        WebDriverWait(self.driver, self.timeout).until(
            populate_field,
            message=f"Could not enter data into {selector!r}; the page kept replacing it.",
        )

    def login(self, base_url, username, password):
        status, message = self.attempt_login(base_url, username, password)
        if status == "error":
            raise RuntimeError(
                f"Moodle rejected the login: {message}. Check "
                "MOODLE_USERNAME and MOODLE_PASSWORD."
            )
        if status != "success":
            raise RuntimeError(f"Moodle login returned an unknown status: {status}")

    def submit_login(self, base_url, username, password):
        self.driver.get(f"{base_url.rstrip('/')}{self.urls['login']}")
        self._type_and_wait(self.selectors["login_username"], username)
        self._type_and_wait(self.selectors["login_password"], password)
        self._click(self.selectors["login_button"])

    def attempt_login(self, base_url, username, password):
        self.submit_login(base_url, username, password)
        try:
            outcome = WebDriverWait(self.driver, self.timeout).until(
                self._login_outcome
            )
        except TimeoutException as error:
            login_form_visible = any(
                element.is_displayed()
                for element in self.driver.find_elements(
                    *self._parse_locator(self.selectors["login_username"])
                )
            )
            raise RuntimeError(
                "Login did not complete: no authenticated-page marker or visible "
                "login error appeared within "
                f"{self.timeout}s. Current URL: {self.driver.current_url}; "
                f"title: {self.driver.title!r}; "
                f"login form still present: {login_form_visible}. Check the "
                "Moodle credentials, base URL, and configured login selectors."
            ) from error

        return outcome

    def _login_outcome(self, driver):
        error_selector = self.selectors.get("login_error")
        if error_selector:
            for element in driver.find_elements(*self._parse_locator(error_selector)):
                message = element.text.strip()
                if element.is_displayed() and message:
                    return "error", message

        login_form_visible = any(
            element.is_displayed()
            for element in driver.find_elements(
                *self._parse_locator(self.selectors["login_username"])
            )
        )
        for element in driver.find_elements(
            *self._parse_locator(self.selectors["logged_in_marker"])
        ):
            if element.is_displayed() and not login_form_visible:
                return "success", ""
        return False

    def open_create_form(self, base_url):
        self.driver.get(f"{base_url.rstrip('/')}{self.urls['create_user']}")
        self._wait_visible(self.selectors["username"])

    def restore_admin_session(self, base_url, username, password):
        self.logout_current(base_url)
        self.login(base_url, username, password)

    def logout_current(self, base_url):
        self.driver.get(
            f"{base_url.rstrip('/')}{self.urls.get('logout', '/login/logout.php')}"
        )
        confirm_selector = self.selectors.get("logout_confirm")
        if confirm_selector:
            login_locator = self._parse_locator(self.selectors["login_username"])

            def logout_state(driver):
                if any(
                    button.is_displayed()
                    for button in driver.find_elements(
                        *self._parse_locator(confirm_selector)
                    )
                ):
                    return "confirm"
                if any(
                    field.is_displayed()
                    for field in driver.find_elements(*login_locator)
                ):
                    return "logged_out"
                return False

            state = WebDriverWait(self.driver, self.timeout).until(logout_state)
            if state == "confirm":
                self._click(confirm_selector)

    def fill_form(self, data):
        self._replace_text(self.selectors["username"], data["username"])

        auth = Select(self._wait_visible(self.selectors["auth_method"]))
        auth.select_by_visible_text(data["authentication"])

        if data["authentication"] == self.config["manual_auth_label"]:
            self._click(self.selectors["password_toggle"])
            self._replace_text(self.selectors["new_password"], data["password"])

        for field in ("firstname", "lastname", "email"):
            self._replace_text(self.selectors[field], data[field])

        for field in ("city", "moodlenet_profile"):
            if data[field]:
                self._replace_text(self.selectors[field], data[field])

        if any(data[field] for field in (
            "firstname_phonetic",
            "lastname_phonetic",
            "middle_name",
            "alternate_name",
        )):
            self._click(self.selectors["names_section_toggle"])
            self._wait_visible(self.selectors["names_section_open"])
            for field in (
                "firstname_phonetic",
                "lastname_phonetic",
                "middle_name",
                "alternate_name",
            ):
                if data[field]:
                    self._replace_text(self.selectors[field], data[field])

        if any(
            data[field]
            for field in (
                "id_number",
                "institution",
                "department",
                "phone",
                "mobile_phone",
                "address",
            )
        ):
            self._click(self.selectors["optional_section_toggle"])
            self._wait_visible(self.selectors["optional_section_open"])
            for field in (
                "id_number",
                "institution",
                "department",
                "phone",
                "mobile_phone",
                "address",
            ):
                if data[field]:
                    self._replace_text(self.selectors[field], data[field])

        for field in ("country", "timezone", "email_visibility"):
            if data[field]:
                select = Select(self._wait_visible(self.selectors[field]))
                value = data[field]
                if value.startswith("label="):
                    value = value[len("label="):]
                select.select_by_visible_text(value)

        if data["interests"]:
            self._click(self.selectors["interests_section_toggle"])
            self._wait_visible(self.selectors["interests_section_open"])
            from selenium.webdriver.common.keys import Keys

            for interest in data["interests"].split("|"):
                if interest:
                    input_element = self._wait_visible(
                        self.selectors["interests_input"]
                    )
                    input_element.send_keys(interest)
                    input_element.send_keys(Keys.ENTER)

        for field, selector_key in (
            ("create_password", "create_password"),
            ("force_password_change", "force_password_change"),
            ("suspended", "suspended"),
        ):
            if data[field]:
                expected = data[field].strip().lower() in {"1", "true", "yes"}
                checkbox = self._wait_visible(self.selectors[selector_key])
                if checkbox.is_selected() != expected:
                    self._click(self.selectors[selector_key])

    def upload_profile_picture(self, file_path):
        from pathlib import Path

        self._click(self.selectors["image_add"])
        self._click(self.selectors["upload_file_menu"])
        file_input = WebDriverWait(self.driver, self.timeout).until(
            EC.presence_of_element_located(
                self._parse_locator(self.selectors["profile_upload_input"])
            )
        )
        path = Path(file_path)
        if not path.is_absolute():
            path = Path(__file__).resolve().parents[1] / path
        if not path.is_file():
            raise FileNotFoundError(f"Upload file does not exist: {path}")
        file_input.send_keys(str(path.resolve()))
        self._click(self.selectors["upload_button"])

    def submit(self):
        self._click(self.selectors["submit_button"])

    def cancel(self):
        self._click(self.selectors["cancel_button"])

    def _replace_text(self, selector, value):
        self._type_and_wait(selector, value)
```

### `tests/FR/TC001_DDT_Level1.py`

```python
import argparse
from pathlib import Path

from utils.ddt_runner import PROJECT_ROOT, run_suite


CONFIG = {
    "base_url": "",
    "urls": {
        "login": "/login/index.php",
        "logout": "/login/logout.php",
        "create_user": "/user/editadvanced.php?id=-1",
        "users": "/admin/user.php",
    },
    "manual_auth_label": "Manual accounts",
    "timeout_seconds": 10,
    "selectors": {
        "login_username": "#username",
        "login_password": "#password",
        "login_button": "#loginbtn",
        "logout_confirm": "css=[role='alertdialog'] button.btn-primary",
        "logged_in_marker": ".navbar, #usernavigation, .usermenu, [data-region='usermenu']",
        "login_error": "#loginerrormessage, .loginerrors, .alert-danger, [role='alert']",
        "username": "#id_username",
        "auth_method": "#id_auth",
        "auth_options": "#id_auth option",
        "password_toggle": "#fitem_id_newpassword [data-passwordunmask='edit']",
        "new_password": "#id_newpassword",
        "firstname": "#id_firstname",
        "lastname": "#id_lastname",
        "email": "#id_email",
        "city": "#id_city",
        "moodlenet_profile": "#id_moodlenetprofile",
        "country": "#id_country",
        "timezone": "#id_timezone",
        "firstname_phonetic": "#id_firstnamephonetic",
        "lastname_phonetic": "#id_lastnamephonetic",
        "middle_name": "#id_middlename",
        "alternate_name": "#id_alternatename",
        "id_number": "#id_idnumber",
        "institution": "#id_institution",
        "department": "#id_department",
        "address": "#id_address",
        "email_visibility": "#id_maildisplay",
        "language": "#id_lang",
        "create_password": "#id_createpassword",
        "force_password_change": "#id_preference_auth_forcepasswordchange",
        "suspended": "#id_suspended",
        "optional_section_toggle": "a[data-bs-toggle='collapse'][href='#id_moodle_optionalcontainer']",
        "optional_section_open": "#id_moodle_optionalcontainer.show",
        "names_section_toggle": "a[data-bs-toggle='collapse'][href='#id_moodle_additional_namescontainer']",
        "names_section_open": "#id_moodle_additional_namescontainer.show",
        "interests_section_toggle": "a[data-bs-toggle='collapse'][href='#id_moodle_interestscontainer']",
        "interests_section_open": "#id_moodle_interestscontainer.show",
        "interests_input": "#fitem_id_interests input[role='textbox']",
        "phone": "#id_phone1",
        "mobile_phone": "#id_phone2",
        "submit_button": "#id_submitbutton",
        "cancel_button": "#id_cancel",
        "validation_feedback": ".form-control-feedback.invalid-feedback, .invalid-feedback, [role='alert']",
        "validation_feedback_simple": ".form-control-feedback.invalid-feedback",
        "users_table": "table",
        "image_add": "#id_imagefile_fieldset a[title='Add...']",
        "upload_file_menu": "xpath=//a[.//span[normalize-space()='Upload a file']]",
        "upload_button": "button.fp-upload-btn",
        "profile_upload_input": "input[type='file'][name='repo_upload_file']",
    },
}


def main():
    parser = argparse.ArgumentParser(description="Run TC001 Level 1 Selenium DDT")
    parser.add_argument(
        "--data",
        default=str(PROJECT_ROOT / "test_data" / "add_user_test_data.csv"),
        help="Path to the test data CSV",
    )
    parser.add_argument("--base-url", help="Moodle base URL; overrides MOODLE_BASE_URL")
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Show the Chrome browser instead of running headless",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate and list CSV cases without opening a browser",
    )
    args = parser.parse_args()
    return run_suite(
        CONFIG,
        Path(args.data),
        base_url=args.base_url,
        headless=not args.headed,
        validate_only=args.validate_only,
    )


if __name__ == "__main__":
    raise SystemExit(main())
```

### `tests/FR/TC001_DDT_Level2.py`

```python
import argparse
import json
from pathlib import Path

from utils.ddt_runner import PROJECT_ROOT, run_suite


def main():
    parser = argparse.ArgumentParser(description="Run TC001 Level 2 Selenium DDT")
    parser.add_argument(
        "--config",
        default=str(PROJECT_ROOT / "test_data" / "tc001_ddt_config.json"),
        help="JSON file containing site URLs and element selectors",
    )
    parser.add_argument(
        "--data",
        default=str(PROJECT_ROOT / "test_data" / "add_user_test_data.csv"),
        help="Path to the test data CSV",
    )
    parser.add_argument("--base-url", help="Overrides base_url from JSON or MOODLE_BASE_URL")
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Show the Chrome browser instead of running headless",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate and list CSV cases without opening a browser",
    )
    args = parser.parse_args()

    with Path(args.config).open(encoding="utf-8") as file:
        config = json.load(file)
    return run_suite(
        config,
        Path(args.data),
        base_url=args.base_url,
        headless=not args.headed,
        validate_only=args.validate_only,
    )


if __name__ == "__main__":
    raise SystemExit(main())
```

### `test_data/tc001_ddt_config.json`

```json
{
  "base_url": "http://localhost/moodle",
  "urls": {
    "login": "/login/index.php",
    "logout": "/login/logout.php",
    "create_user": "/user/editadvanced.php?id=-1",
    "users": "/admin/user.php"
  },
  "manual_auth_label": "Manual accounts",
  "timeout_seconds": 10,
  "selectors": {
    "login_username": "#username",
    "login_password": "#password",
    "login_button": "#loginbtn",
    "logout_confirm": "css=[role='alertdialog'] button.btn-primary",
    "logged_in_marker": ".navbar, #usernavigation, .usermenu, [data-region='usermenu']",
    "login_error": "#loginerrormessage, .loginerrors, .alert-danger, [role='alert']",
    "username": "#id_username",
    "auth_method": "#id_auth",
    "auth_options": "#id_auth option",
    "password_toggle": "#fitem_id_newpassword [data-passwordunmask='edit']",
    "new_password": "#id_newpassword",
    "firstname": "#id_firstname",
    "lastname": "#id_lastname",
    "email": "#id_email",
    "city": "#id_city",
    "moodlenet_profile": "#id_moodlenetprofile",
    "country": "#id_country",
    "timezone": "#id_timezone",
    "firstname_phonetic": "#id_firstnamephonetic",
    "lastname_phonetic": "#id_lastnamephonetic",
    "middle_name": "#id_middlename",
    "alternate_name": "#id_alternatename",
    "id_number": "#id_idnumber",
    "institution": "#id_institution",
    "department": "#id_department",
    "address": "#id_address",
    "email_visibility": "#id_maildisplay",
    "language": "#id_lang",
    "create_password": "#id_createpassword",
    "force_password_change": "#id_preference_auth_forcepasswordchange",
    "suspended": "#id_suspended",
    "optional_section_toggle": "a[data-bs-toggle='collapse'][href='#id_moodle_optionalcontainer']",
    "optional_section_open": "#id_moodle_optionalcontainer.show",
    "names_section_toggle": "a[data-bs-toggle='collapse'][href='#id_moodle_additional_namescontainer']",
    "names_section_open": "#id_moodle_additional_namescontainer.show",
    "interests_section_toggle": "a[data-bs-toggle='collapse'][href='#id_moodle_interestscontainer']",
    "interests_section_open": "#id_moodle_interestscontainer.show",
    "interests_input": "#fitem_id_interests input[role='textbox']",
    "phone": "#id_phone1",
    "mobile_phone": "#id_phone2",
    "submit_button": "#id_submitbutton",
    "cancel_button": "#id_cancel",
    "validation_feedback": ".form-control-feedback.invalid-feedback, .invalid-feedback, [role='alert']",
    "validation_feedback_simple": ".form-control-feedback.invalid-feedback",
    "users_table": "table",
    "image_add": "#id_imagefile_fieldset a[title='Add...']",
    "upload_file_menu": "xpath=//a[.//span[normalize-space()='Upload a file']]",
    "upload_button": "button.fp-upload-btn",
    "profile_upload_input": "input[type='file'][name='repo_upload_file']"
  }
}
```

