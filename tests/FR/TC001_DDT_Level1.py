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
