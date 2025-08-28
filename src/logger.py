import datetime
import logging
import subprocess
import sys
from logging.handlers import TimedRotatingFileHandler

from pytz import timezone

MEDICONY_LOG_PATH = "log/medicony.log"  # Default path, will be overridden by config


def read_n_log_lines_from_file(file_path: str = MEDICONY_LOG_PATH, num_lines: int = 30) -> str:
    try:
        result = subprocess.run(["tail", f"-n{num_lines}", file_path], check=True, capture_output=True, text=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Running tail failed: {e}")
        return ""


class Logger:
    def __init__(self, log_file: str = MEDICONY_LOG_PATH):
        self.logger = logging.getLogger("MediConyLogger")
        self.logger.setLevel(logging.DEBUG)
        self.formatter = logging.Formatter(self._log_format())
        self.formatter.converter = lambda *args: datetime.datetime.now(tz=timezone("Europe/Warsaw")).timetuple()
        self.log_file = log_file

        # File handler with daily rotation
        self.file_handler = TimedRotatingFileHandler(
            log_file, when="midnight", interval=1, backupCount=7, encoding="utf-8"
        )
        self.file_handler.setFormatter(self.formatter)
        self.file_handler.setLevel(logging.DEBUG)

        # Console handler
        self.console_handler = logging.StreamHandler(sys.stdout)
        self.console_handler.setFormatter(self.formatter)
        self.console_handler.setLevel(logging.DEBUG)

        self.logger.addHandler(self.file_handler)
        self.logger.addHandler(self.console_handler)
        self.console_only = False

    def _log_format(self):
        return "[%(asctime)s] [%(levelname)8s] | %(message)s"

    def info(self, message: str):
        self.logger.info(message)

    def error(self, message: str):
        self.logger.error(message)

    def warning(self, message: str):
        self.logger.warning(message)

    def debug(self, message: str):
        self.logger.debug(message)

    def log_to_file(self, level: str, message: str):
        self.logger.removeHandler(self.console_handler)
        self.log(level, message)
        self.logger.addHandler(self.console_handler)

    def setup_console_only(self):
        # If app is launched in console-only mode (one-shot), remove the file handler and log only to console
        if self.console_only:
            return
        self.logger.removeHandler(self.file_handler)
        self.console_only = True

    def log(self, level: str, message: str):
        match level.upper():
            case "INFO":
                self.logger.info(message)
            case "ERROR":
                self.logger.error(message)
            case "WARN", "WARNING":
                self.logger.warning(message)
            case _:
                self.logger.debug(message)

    def set_log_path(self, log_path: str):
        """Update the log file path and recreate the file handler."""
        if log_path == self.log_file:
            return  # No change needed

        # Remove old file handler
        if self.file_handler in self.logger.handlers:
            self.logger.removeHandler(self.file_handler)

        # Create new file handler with updated path
        self.log_file = log_path
        self.file_handler = TimedRotatingFileHandler(
            log_path, when="midnight", interval=1, backupCount=7, encoding="utf-8"
        )
        self.file_handler.setFormatter(self.formatter)
        self.file_handler.setLevel(logging.DEBUG)
        self.logger.addHandler(self.file_handler)


log = Logger()
