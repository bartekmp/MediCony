#!/usr/bin/env python3
"""
Simple script to retrieve the current device_id and decrypted refresh_token
from your MediCony database. This is explicitly useful when populating
Jenkins testing variables or rotating compromised credentials.
"""

import os
import sys

# Ensure imports work regardless of execution folder
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.database.medicover_db import MedicoverDbLogic
from src.config import parse_medicover_accounts


def main():
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        print("python-dotenv not installed, proceeding with current env.")

    db = MedicoverDbLogic()

    userdata = os.environ.get("MEDICOVER_USERDATA")
    if not userdata:
        print("❌ MEDICOVER_USERDATA is missing in the environment.")
        sys.exit(1)

    try:
        _, alias = parse_medicover_accounts(userdata)
    except Exception as e:
        print(f"❌ Error parsing MEDICOVER_USERDATA: {e}")
        sys.exit(1)

    print(f"🔍 Fetching active session for account alias: '{alias}'...")

    session = db.get_account_session(alias)
    if not session:
        print(f"❌ No active session found in the database for '{alias}'.")
        print("Run the bot interactively first to complete MFA and save a session!")
        sys.exit(1)

    device_id, refresh_token = session

    print("\n✅ Session successfully retrieved and decrypted!\n")
    print("=" * 60)
    print("Export these into Jenkins or your CI environment:\n")
    print(f'MEDICONY_TEST_DEVICE_ID="{device_id}"')
    print(f'MEDICONY_TEST_REFRESH_TOKEN="{refresh_token}"')
    print("=" * 60)


if __name__ == "__main__":
    main()
