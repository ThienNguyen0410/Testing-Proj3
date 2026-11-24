# TC-001: Selenium Data-Driven Testing

## 1. Project structure and implementation

The project separates recorded scenarios, page interactions, test data, functional
tests, and reusable utilities. This implementation keeps that structure and adds:

| File | Purpose |
|---|---|
| `pages/add_user_page.py` | Selenium page object for Moodle login and user creation |
| `utils/data_reader.py` | Reads and validates the data CSV |
| `utils/ddt_runner.py` | Shared Selenium runner, assertions, and result summary |
| `tests/FR/TC001_DDT_Level1.py` | Level 1: test data in CSV; URLs/selectors in Python |
| `tests/FR/TC001_DDT_Level2.py` | Level 2: test data in CSV; URLs/selectors in JSON |
| `test_data/add_user_test_data.csv` | The ten requested TC-001 cases and their expected outcomes |
| `test_data/tc001_ddt_config.json` | Level 2 site URL paths and element selectors |

The selectors and relative paths are based on
[`katalon/TC001-AddUser.krecorder`](./katalon/TC001-AddUser.krecorder). The recorder
does not specify a host name, so set the Moodle base URL before running.

## 2. TC-001-031 clarification

The recorder labels this case **“Mobile phone length 18”**, enters 18 digits, checks
that the value is present, and then checks for `.form-control-feedback.invalid-feedback`.
That assertion indicates validation feedback is expected. The CSV therefore currently
expects `validation`, following the recorder's assertion rather than guessing from the
title. Confirm the intended product rule (whether 18 digits should be valid) with the
test owner; if it should be valid, change the row's `expected` value to `success` and
set the expected success text accordingly.

## 3. Requirements

- Python 3.9 or newer.
- Selenium 4.6 or newer (Selenium Manager can resolve the Chrome driver).
- Google Chrome installed.
- A reachable Moodle site and an account permitted to create users.
- The test account must be able to create Manual accounts.

No Selenium test can be fully verified without the target Moodle site and credentials.
Use a test instance: successful rows create user accounts.

## 4. Configure and run (Windows PowerShell)

Run commands from the project root:

```powershell
cd C:\Users\Thien\Documents\HCMUT\261\Testing\Proj3
```

Set credentials in the current PowerShell session. These are environment variables,
not source-code values:

```powershell
$env:MOODLE_USERNAME = "your-admin-username"
$env:MOODLE_PASSWORD = "your-admin-password"
$env:MOODLE_BASE_URL = "http://localhost/moodle"
```

Replace the URL with the actual Moodle installation URL, for example
`http://localhost` if Moodle is installed at the web root. The URL must not end with
`/login/index.php`; that path is appended by the test.

The runner also loads `.env` from the project root and gives its values precedence
over variables already set in the shell. Keep that file local and do not commit it.

### Level 1

Test values come from the CSV. Base URL is provided by the environment or CLI;
relative page paths and selectors are embedded in the Python script.

```powershell
python -m tests.FR.TC001_DDT_Level1 --validate-only
python -m tests.FR.TC001_DDT_Level1
```

To display Chrome while the tests run:

```powershell
python -m tests.FR.TC001_DDT_Level1 --headed
```

Or provide the site URL directly:

```powershell
python -m tests.FR.TC001_DDT_Level1 --base-url "http://localhost/moodle"
```

### Level 2

Test values come from the CSV. Base URL, relative paths, and element selectors are
loaded from `test_data/tc001_ddt_config.json`. Update its `base_url` and, if the
installation differs, the `urls` or `selectors` values.

```powershell
python -m tests.FR.TC001_DDT_Level2 --validate-only
python -m tests.FR.TC001_DDT_Level2
```

To display Chrome or override the configured URL:

```powershell
python -m tests.FR.TC001_DDT_Level2 --headed
python -m tests.FR.TC001_DDT_Level2 --base-url "http://localhost/moodle"
```

`--validate-only` checks CSV headers, row IDs, and expected outcome values without
starting Chrome or connecting to Moodle. A full run prints PASS/FAIL per case and
returns exit code 1 if any case fails. The browser runs headless by default.

If login fails, the runner now reports the visible Moodle login error when available;
otherwise it reports the current URL, page title, and whether the login form remains
visible. Confirm the credentials and target URL, then compare the Level 2
`logged_in_marker` and `login_error` selectors with the actual page if using a custom
Moodle theme.

If Selenium is not available in the active Python environment, install it there:

```powershell
python -m pip install "selenium>=4.6"
```

The test data has unique usernames for most cases. Before rerunning, remove any users
created by earlier successful runs or change those usernames in the CSV. The
duplicate-user scenario intentionally uses the existing `admin` username.

## 5. Source code

### `utils/data_reader.py`

```python
import csv
from itertools import chain
from pathlib import Path


REQUIRED_COLUMNS = {
    "test_id",
    "title",
    "username",
    "password",
    "firstname",
    "lastname",
    "email",
    "phone",
    "mobile_phone",
    "expected",
    "expected_text",
}


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
            test_id = (row.get("test_id") or "").strip()
            if not test_id:
                raise ValueError(f"{path}:{line_number}: test_id must not be empty")
            if test_id in seen_ids:
                raise ValueError(f"{path}:{line_number}: duplicate test_id {test_id}")
            seen_ids.add(test_id)

            cleaned = {
                key: (value or "").strip()
                for key, value in row.items()
                if key is not None
            }
            if cleaned["expected"] not in {"success", "validation", "duplicate", "cancelled"}:
                raise ValueError(
                    f"{path}:{line_number}: unsupported expected value "
                    f"{cleaned['expected']!r}"
                )
            if cleaned["expected"] in {"success", "duplicate"} and not cleaned["expected_text"]:
                raise ValueError(
                    f"{path}:{line_number}: expected_text is required for "
                    f"{cleaned['expected']} cases"
                )
            rows.append(cleaned)

    if not rows:
        raise ValueError(f"{path} contains no test rows")
    return rows
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

    def _wait_visible(self, selector):
        return WebDriverWait(self.driver, self.timeout).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, selector))
        )

    def _wait_clickable(self, selector):
        return WebDriverWait(self.driver, self.timeout).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
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
        def populate_field(driver):
            try:
                element = driver.find_element(By.CSS_SELECTOR, selector)
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
        self.driver.get(f"{base_url.rstrip('/')}{self.urls['login']}")
        self._type_and_wait(self.selectors["login_username"], username)
        self._type_and_wait(self.selectors["login_password"], password)
        self._click(self.selectors["login_button"])
        try:
            outcome = WebDriverWait(self.driver, self.timeout).until(
                self._login_outcome
            )
        except TimeoutException as error:
            login_form_visible = any(
                element.is_displayed()
                for element in self.driver.find_elements(
                    By.CSS_SELECTOR, self.selectors["login_username"]
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

        status, message = outcome
        if status == "error":
            raise RuntimeError(
                f"Moodle rejected the login: {message}. Check "
                "MOODLE_USERNAME and MOODLE_PASSWORD."
            )

    def _login_outcome(self, driver):
        error_selector = self.selectors.get("login_error")
        if error_selector:
            for element in driver.find_elements(By.CSS_SELECTOR, error_selector):
                message = element.text.strip()
                if element.is_displayed() and message:
                    return "error", message

        login_form_visible = any(
            element.is_displayed()
            for element in driver.find_elements(
                By.CSS_SELECTOR, self.selectors["login_username"]
            )
        )
        for element in driver.find_elements(
            By.CSS_SELECTOR, self.selectors["logged_in_marker"]
        ):
            if element.is_displayed() and not login_form_visible:
                return "success", ""
        return False

    def open_create_form(self, base_url):
        self.driver.get(f"{base_url.rstrip('/')}{self.urls['create_user']}")
        self._wait_visible(self.selectors["username"])

    def fill_form(self, data):
        self._replace_text(self.selectors["username"], data["username"])

        auth = Select(self._wait_visible(self.selectors["auth_method"]))
        auth.select_by_visible_text(self.config["manual_auth_label"])

        self._click(self.selectors["password_toggle"])
        if data["password"]:
            self._replace_text(self.selectors["new_password"], data["password"])

        for field in ("firstname", "lastname", "email"):
            self._replace_text(self.selectors[field], data[field])

        if data["phone"] or data["mobile_phone"]:
            self._click(self.selectors["optional_section_toggle"])
            self._wait_visible(self.selectors["optional_section_open"])
            if data["phone"]:
                self._replace_text(self.selectors["phone"], data["phone"])
            if data["mobile_phone"]:
                self._replace_text(self.selectors["mobile_phone"], data["mobile_phone"])

    def submit(self):
        self._click(self.selectors["submit_button"])

    def cancel(self):
        self._click(self.selectors["cancel_button"])

    def _replace_text(self, selector, value):
        element = self._wait_visible(selector)
        element.clear()
        if value:
            element.send_keys(value)
```

### `utils/ddt_runner.py`

```python
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pages.add_user_page import AddUserPage
from utils.data_reader import read_test_data


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
        "create_user": "/user/editadvanced.php?id=-1",
        "users": "/admin/user.php",
    },
    "manual_auth_label": "Manual accounts",
    "timeout_seconds": 10,
    "selectors": {
        "login_username": "#username",
        "login_password": "#password",
        "login_button": "#loginbtn",
        "logged_in_marker": ".navbar, #usernavigation, .usermenu, [data-region='usermenu']",
        "login_error": "#loginerrormessage, .loginerrors, .alert-danger, [role='alert']",
        "username": "#id_username",
        "auth_method": "#id_auth",
        "password_toggle": "#fitem_id_newpassword [data-passwordunmask='edit']",
        "new_password": "#id_newpassword",
        "firstname": "#id_firstname",
        "lastname": "#id_lastname",
        "email": "#id_email",
        "optional_section_toggle": "a[data-bs-toggle='collapse'][href='#id_moodle_optionalcontainer']",
        "optional_section_open": "#id_moodle_optionalcontainer.show",
        "phone": "#id_phone1",
        "mobile_phone": "#id_phone2",
        "submit_button": "#id_submitbutton",
        "cancel_button": "#id_cancel",
        "validation_feedback": ".form-control-feedback.invalid-feedback, .invalid-feedback, [role='alert']",
        "users_table": "table",
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
    "create_user": "/user/editadvanced.php?id=-1",
    "users": "/admin/user.php"
  },
  "manual_auth_label": "Manual accounts",
  "timeout_seconds": 10,
  "selectors": {
    "login_username": "#username",
    "login_password": "#password",
    "login_button": "#loginbtn",
    "logged_in_marker": ".navbar, #usernavigation, .usermenu, [data-region='usermenu']",
    "login_error": "#loginerrormessage, .loginerrors, .alert-danger, [role='alert']",
    "username": "#id_username",
    "auth_method": "#id_auth",
    "password_toggle": "#fitem_id_newpassword [data-passwordunmask='edit']",
    "new_password": "#id_newpassword",
    "firstname": "#id_firstname",
    "lastname": "#id_lastname",
    "email": "#id_email",
    "optional_section_toggle": "a[data-bs-toggle='collapse'][href='#id_moodle_optionalcontainer']",
    "optional_section_open": "#id_moodle_optionalcontainer.show",
    "phone": "#id_phone1",
    "mobile_phone": "#id_phone2",
    "submit_button": "#id_submitbutton",
    "cancel_button": "#id_cancel",
    "validation_feedback": ".form-control-feedback.invalid-feedback, .invalid-feedback, [role='alert']",
    "users_table": "table"
  }
}
```

### `test_data/add_user_test_data.csv`

```csv
test_id,title,username,password,firstname,lastname,email,phone,mobile_phone,expected,expected_text
TC-001-001,Create user with valid required fields,tc001_ddt_valid,ValidPass123!,Test,User,tc001_valid@example.com,,,success,Changes saved
TC-001-002,Username is empty,,ValidPass123!,Test,User,tc001_empty_username@example.com,,,validation,
TC-001-005,Username contains unsupported special character,test#user,ValidPass123!,Test,User,tc001_special_char@example.com,,,validation,
TC-001-007,Duplicate username,admin,ValidPass123!,Test,User,tc001_duplicate@example.com,,,duplicate,"This username already exists, choose another"
TC-001-008,Password is empty with Manual accounts,tc001_empty_password,,Test,User,tc001_empty_password@example.com,,,validation,
TC-001-015,Email has invalid format,tc001_invalid_email,ValidPass123!,Test,User,invalid@,,,validation,
TC-001-017,Optional profile fields are empty,tc001_optional_empty,ValidPass123!,Test,User,tc001_optional_empty@example.com,,,success,Changes saved
TC-001-025,Phone length 20,tc001_phone_20,ValidPass123!,Test,User,tc001_phone20@example.com,11111111111111111111,,success,Changes saved
TC-001-031,Mobile phone length 18 (recorder expects validation),tc001_mobile_18,ValidPass123!,Test,User,tc001_mobile18@example.com,,111111111111111111,validation,
TC-001-045,Cancel user creation,tc001_cancel,ValidPass123!,Test,User,tc001_cancel@example.com,,,cancelled,
```
