import os
import time
from datetime import datetime

from dotenv import load_dotenv
from gspread.exceptions import APIError
from gspread.utils import a1_to_rowcol
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.webdriver import WebDriver
from webdriver_manager.chrome import ChromeDriverManager

import constants
from app.process import get_row_run_index
from decorator.retry import retry
from decorator.time_execution import time_execution
from model.payload import Row
from utils.dd_utils import get_dd_min_price
from utils.exceptions import PACrawlerError
from utils.ggsheet import GSheet, Sheet
from utils.logger import setup_logging

### SETUP ###
load_dotenv("settings.env")

setup_logging()
gs = GSheet()


### FUNCTIONS ###


@time_execution
@retry(5, delay=15, exception=PACrawlerError)
def process(
    gsheet: GSheet,
    driver: WebDriver
):
    print("process")
    try:
        sheet = Sheet.from_sheet_id(
            gsheet=gsheet,
            sheet_id=os.getenv("SPREADSHEET_ID"),  # type: ignore
        )
    except Exception as e:
        print(f"Error getting sheet: {e}")
        return
    try:
        worksheet = sheet.open_worksheet(os.getenv("SHEET_NAME"))  # type: ignore
    except APIError as e:
        print("Quota exceeded, sleeping for 60 seconds")
        time.sleep(60)
        return
    except Exception as e:
        print(f"Error getting worksheet: {e}")
        return
    row_indexes = get_row_run_index(worksheet=worksheet)

    for index in row_indexes:
        status = "NOT FOUND"
        print(f"Row: {index}")
        try:
            row = Row.from_row_index(worksheet, index)
        except Exception as e:
            print(f"Error getting row: {e}")
            _current_time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            write_to_log_cell(worksheet, index, "Error: " + _current_time, log_type="time")
            continue
        if not isinstance(row, Row):
            continue
        try:
            min_price = get_dd_min_price(row.dd, driver)
            if min_price is None:
                print("No item info")
            else:
                print(f"Min price: {min_price[0]}")
                print(f"Title: {min_price[1]}")
                status = "FOUND"
                write_to_log_cell(worksheet, index, min_price[0], log_type="price")
                write_to_log_cell(worksheet, index, min_price[1], log_type="title")
                write_to_log_cell(worksheet, index, min_price[2], log_type="stock")
            try:
                _row_time_sleep = float(os.getenv("ROW_TIME_SLEEP"))
                print(f"Sleeping for {_row_time_sleep} seconds")
                time.sleep(_row_time_sleep)
            except Exception as e:
                print("No row time sleep, sleeping for 3 seconds by default")
                time.sleep(3)

        except Exception as e:
            print(f"Error calculating price change: {e}")
            continue
        write_to_log_cell(worksheet, index, status, log_type="status")
        _current_time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        write_to_log_cell(worksheet, index, _current_time, log_type="time")
        print("Next row...")


def write_to_log_cell(
    worksheet,
    row_index,
    log_str,
    log_type="log"
):
    try:
        r, c = None, None
        if log_type == "status":
            r, c = a1_to_rowcol(f"E{row_index}")
        if log_type == "time":
            r, c = a1_to_rowcol(f"F{row_index}")
        if log_type == "price":
            r, c = a1_to_rowcol(f"I{row_index}")
        if log_type == "title":
            r, c = a1_to_rowcol(f"J{row_index}")
        if log_type == "stock":
            r, c = a1_to_rowcol(f"K{row_index}")
        worksheet.update_cell(r, c, log_str)
    except Exception as e:
        print(f"Error writing to log cell: {e}")


def create_selenium_driver():
    options = Options()
    prefs = {"profile.default_content_setting_values.popups": 2}  # 2 = Block, 1 = Allow
    options.add_experimental_option("prefs", prefs)
    options.add_argument("--disable-notifications")  # Disables browser notification prompts
    options.add_experimental_option("excludeSwitches", ["enable-automation"])  # Hides "Chrome is being controlled" bar
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    print("Driver created")
    return driver


### MAIN ###

if __name__ == "__main__":
    print("Starting...")
    gsheet = GSheet(constants.KEY_PATH)
    sd = create_selenium_driver()
    while True:
        try:
            process(gsheet, sd)
            try:
                _time_sleep = float(os.getenv("TIME_SLEEP"))
            except Exception:
                _time_sleep = 0
            print(f"Sleeping for {_time_sleep} seconds")
            time.sleep(_time_sleep)
        except Exception as e:
            _str_error = f"Error: {e}"
            print(_str_error)
            time.sleep(60)  # Wait for 60 seconds before retrying
        print("Done")
