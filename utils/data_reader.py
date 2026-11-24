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