from typing import Any

import gspread


def get_row_run_index(
        worksheet: gspread.worksheet.Worksheet,
        col_check_index: int = 2,
        value_check: Any = "1",
) -> list[int]:
    row_indexes: list[int] = []
    for i, row_value in enumerate(worksheet.col_values(col_check_index), start=1):
        if row_value == value_check:
            row_indexes.append(i)

    return row_indexes


