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
