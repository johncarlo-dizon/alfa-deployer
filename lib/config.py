import sys
import os

# NOTE: sys.argv[0] is used (not __file__) so this still resolves to the
# folder the .exe lives in, even when frozen by PyInstaller with --onefile.
BASE_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))

STORES_FILE = os.path.join(BASE_DIR, "stores.txt")
LOGS_FILE = os.path.join(BASE_DIR, "deployment_logs.txt")

# Default remote folder suggested in the "Remote Directory" field
DEFAULT_REMOTE_DIR = r"C:\Reminder_v2"

# Max parallel SSH/SFTP workers when deploying to many stores at once
MAX_WORKERS = 10

# How many times to retry a single file upload before marking it failed
UPLOAD_MAX_ATTEMPTS = 3
UPLOAD_RETRY_DELAY_SEC = 1.5
