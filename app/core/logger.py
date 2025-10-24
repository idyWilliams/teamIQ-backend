import logging
import sys

# Create a shared logger for the entire app (especially invitations)
logger = logging.getLogger("teamiq")
logger.setLevel(logging.INFO)

# Stream to console
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)

# Format logs with timestamps
formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")
console_handler.setFormatter(formatter)

# Avoid multiple handler duplications
if not logger.handlers:
    logger.addHandler(console_handler)
