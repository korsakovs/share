import os
from datetime import datetime

from updateme.core import dao
from updateme.email.client import obtain_token_info, get_labels, credentials_filename, TEST_EMAIL_FROM, \
    generate_test_message, send_message, TEST_EMAIL_TO
from updateme.email.composer import compose_message

if __name__ == "__main__":
    obtain_token_info()
    get_labels()
    if not os.path.exists(credentials_filename):
        raise RuntimeError("Please, obtain \"credentials.json\" file and put in in the \"email\" folder")
    if not TEST_EMAIL_FROM:
        raise ValueError("Please, set TEST_EMAIL_FROM environment variable in order to test this module")
    message = compose_message(
        dao.read_status_updates()
    )
    message["To"] = TEST_EMAIL_TO
    message["From"] = f"Share!<{TEST_EMAIL_FROM}>"
    message["Subject"] = f"Share! digest from {datetime.utcnow().strftime('%A, %B %-d')}"
    send_message(message)
