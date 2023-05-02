"""
This sets up global test configs when pytest starts
"""

# Standard
import os

# First Party
import alog

# Configure logging from the environment
alog.configure(
    default_level=os.environ.get("LOG_LEVEL", "off"),
    filters=os.environ.get("LOG_FILTERS", "urllib3:off"),
    thread_id=os.environ.get("LOG_THREAD_ID", "") == "true",
)
