from dotenv import load_dotenv
import logging
import os
from datetime import datetime

import constants


def setup_logging():
    # Load environment variables at the beginning of the script
    load_dotenv('settings.env')

    # Configure logging from environment variables
    log_level = constants.LOG_LEVEL
    log_format = constants.LOG_FORMAT

    # Create log file based on the current date in the logs/ directory
    log_dir = 'logs'
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"{datetime.now().strftime('%Y-%m-%d')}_function_calls.log")

    logging.basicConfig(filename=log_file, level=log_level, format=log_format)