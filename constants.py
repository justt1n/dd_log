import os

KEY_PATH = "key.json"
DATA_PATH = "storage/output.json"
RETRIES_TIME = 20
DEFAULT_URL = "https://www.bijiaqi.com/"

SHEET_NAME = "Sheet1"
BLACKLIST_SHEET_NAME = "Blacklist"
DESTINATION_RANGE = "G{n}:Q{n}"
INFORMATION_RANGE = "G{n}:H{n}"
TIMEOUT = 15
REFRESH_TIME = 10
LOG_FILE = "function_calls.log"
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(message)s"

TEMPLATE_FOLDER = os.path.join(os.path.dirname(__file__), "storage", "pa_template")
