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
