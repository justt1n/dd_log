import time

from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

from decorator.time_execution import time_execution


class StockManager:
    def __init__(self, spreadsheet_id: str):
        self.credentials_file = "key.json"
        self.spreadsheet_id = spreadsheet_id
        time.sleep(1)
        self.service = self._initialize_service()

    def _initialize_service(self):
        credentials = Credentials.from_service_account_file(
            self.credentials_file,
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
        return build('sheets', 'v4', credentials=credentials)

    def get_cell_float_value(self, range_name: str) -> float:
        try:
            result = (
                self.service.spreadsheets()
                .values()
                .get(spreadsheetId=self.spreadsheet_id, range=range_name)
                .execute()
            )
            cell_value = result.get('values', [[]])[0][0]
            # Convert to integer after handling float-like values
            stock_value = float(cell_value)
            return stock_value
        except ValueError as ve:
            print(f"ValueError for range {range_name}: {cell_value} is not a valid integer.")
            raise Exception(f"Invalid stock value: {cell_value}")
        except Exception as e:
            print(f"Error retrieving stock from range {range_name}: {e}")
            raise Exception(f"Error getting stock from {range_name}")

    def get_cell_stock(self, range_name: str) -> float:
        try:
            result = (
                self.service.spreadsheets()
                .values()
                .get(spreadsheetId=self.spreadsheet_id, range=range_name)
                .execute()
            )
            cell_value = result.get('values', [[]])[0][0]
            # Convert to integer after handling float-like values
            stock_value = float(cell_value)
            return stock_value
        except Exception as e:
            print(f"Error retrieving stock from range {range_name}: {e}")
            return -1

    def get_multiple_cells(self, ranges: list[str]) -> list[int]:
        try:
            # Make a batch request for multiple ranges
            result = (
                self.service.spreadsheets()
                .values()
                .batchGet(spreadsheetId=self.spreadsheet_id, ranges=ranges)
                .execute()
            )
            values = result.get("valueRanges", [])
            # Extract values from the response, convert to integers if possible
            cell_values = []
            for value_range in values:
                cell = value_range.get("values", [[]])[0][0]
                cell_values.append(int(float(cell)))  # Handle float-like strings like '0.'
            return cell_values
        except ValueError as ve:
            raise Exception(f"Invalid stock value in ranges {ranges}\n{ve}")
        except Exception as e:
            raise Exception(f"Error getting values from ranges {ranges}{e}")

    def get_multiple_str_cells(self, range_str: str) -> list[str]:
        try:
            # Make a request for the single range
            result = (
                self.service.spreadsheets()
                .values()
                .get(spreadsheetId=self.spreadsheet_id, range=range_str)
                .execute()
            )
            values = result.get("values", [])
            # Extract values from the response as strings
            cell_values = [str(cell[0]) for cell in values if cell]
            return cell_values
        except Exception as e:
            print(f"Error retrieving values from range {range_str}: {e}")
            raise Exception(f"Error getting values from range {range_str}")


if __name__ == "__main__":
    spreadsheet_id = "1vS6X10z8LoTI_NL6F-SnBPFKdExeDYLt2PL0C1Qux54"  # Replace with your spreadsheet ID
    stock_manager = StockManager(spreadsheet_id)
    stock1, stock2 = stock_manager.get_multiple_cells(["'Tool.SoD'!U53", "'Tool.SoD'!T53"])

    # stock1 = stock_manager.get_stock("'Tool.SoD'!U53")  # Replace with your specific range
    print(f"Stock 1: {stock1}")

    # stock2 = stock_manager.get_stock("'Tool.SoD'!T53")  # Replace with your specific range
    print(f"Stock 2: {stock2}")
