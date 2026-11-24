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
