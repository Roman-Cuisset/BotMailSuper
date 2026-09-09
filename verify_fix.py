import logging
import sys
from utils.gmail_api import authenticate_gmail

logging.basicConfig(level=logging.INFO)

print("Attempting authentication (interactive=False)...")
service = authenticate_gmail()
if service is None:
    print("SUCCESS: Authentication failed cleanly (did not hang)")
else:
    print("UNEXPECTED: Authentication succeeded (did you leave the token?)")
