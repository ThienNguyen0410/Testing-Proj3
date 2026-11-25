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

        if data["authentication"]:
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
