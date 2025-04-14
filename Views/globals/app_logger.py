import logging
import os

# Create a global logger
app_logger = logging.getLogger("app_logger")
app_logger.setLevel(logging.DEBUG)

# Create a file handler
# log_file = os.path.join(os.path.dirname(__file__), 'app.log')
log_file = os.path.join("app.log")
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.DEBUG)

# Create a console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Create a formatter and set it for both handlers
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Define a filter to exclude sync_CT_cycles logs


class SyncCTCyclesFilter(logging.Filter):
    def filter(self, record):
        if "sync_CT_cycles" in record.getMessage():
            return False
        return True


# Add filter to both handlers
filter = SyncCTCyclesFilter()
file_handler.addFilter(filter)
console_handler.addFilter(filter)

# Add handlers to the logger
app_logger.addHandler(file_handler)
app_logger.addHandler(console_handler)

# Example usage
if __name__ == "__main__":
    app_logger.debug("This is a debug message")
    app_logger.info("This is an info message")
    app_logger.warning("This is a warning message")
    app_logger.error("This is an error message")
    app_logger.critical("This is a critical message")
