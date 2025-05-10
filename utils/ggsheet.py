import gspread.urls
import gspread.utils
from oauth2client.service_account import ServiceAccountCredentials
import gspread


class GSheet:
    client: gspread.client.Client

    def __init__(self, keypath="key.json"):
        self.client = self.__get_gspread(keypath)

    def __get_gspread(self, keypath="key.json"):
        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_name(keypath, scope)  # type: ignore
        client = gspread.auth.authorize(creds)  # type: ignore
        return client

    def get_sheet(
            self,
            sheet_id,
    ) -> gspread.spreadsheet.Spreadsheet:
        return self.client.open_by_key(sheet_id)

    def read_sheet_data(self, sheet_id):
        sheet = self.get_sheet(sheet_id)
        return sheet.sheet1.get_all_values()

    def load_cell_value(self,
                        spreadsheet_id: str,
                        sheet_name: str,
                        cell: str,
                        ) -> float:
        spreadsheet = self.client.open_by_key(spreadsheet_id)

        worksheet = spreadsheet.worksheet(sheet_name)
        value = worksheet.acell(cell).value
        return float(value)


class Sheet:
    gsheet: GSheet
    sheet_id: str
    sheet: gspread.spreadsheet.Spreadsheet

    def __init__(
            self,
            gsheet: GSheet,
            sheet_id: str,
    ) -> None:
        self.gsheet = gsheet
        self.sheet_id = sheet_id
        self.sheet = self.gsheet.get_sheet(self.sheet_id)

    def open_worksheet(
            self,
            worksheet_name: str,
    ) -> gspread.worksheet.Worksheet:
        return self.sheet.worksheet(worksheet_name)

    def __call__(self) -> gspread.spreadsheet.Spreadsheet:
        return self.sheet

    @staticmethod
    def extract_sheet_id_from_url(url: str):
        return gspread.utils.extract_id_from_url(url)

    @staticmethod
    def from_url(
            gsheet: GSheet,
            url: str,
    ) -> "Sheet":
        sheet_id = Sheet.extract_sheet_id_from_url(url)
        return Sheet(gsheet, sheet_id)

    @staticmethod
    def from_sheet_id(
            gsheet: GSheet,
            sheet_id: str,
    ) -> "Sheet":
        return Sheet(gsheet, sheet_id)
