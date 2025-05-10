import os

from utils.google_api import StockManager


def getCNYRate() -> float:
    try:
        sheet_manager = StockManager(os.getenv("CNY_RATE_SPREADSHEET_ID"))
        cell_value = sheet_manager.get_cell_float_value(f"'{os.getenv('CNY_RATE_SHEET_NAME')}'!{os.getenv('CNY_RATE_CELL')}")
        # _rate_sheet = os.getenv("CNY_RATE_SPREADSHEET_ID")
        # _rate_worksheet = os.getenv("CNY_RATE_SHEET_NAME")
        # _cell = os.getenv("CNY_RATE_CELL")
        # return gs.load_cell_value(_rate_sheet, _rate_worksheet, _cell)
        return cell_value
    except Exception as e:
        print(f"Error reading CNY rate: {e}")
        return 1
