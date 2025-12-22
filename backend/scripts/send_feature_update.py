#!/usr/bin/env python3
"""
One-time script to send feature update emails to all users.
Run from backend directory: python scripts/send_feature_update.py
"""
import sys
import os
import time

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from app.core.config import settings
from app.services.email_service import email_service


def get_all_users():
    """Fetch all users from the database."""
    # Use sync engine for simple script
    db_url = settings.DATABASE_URL.replace("+psycopg", "")  # Use psycopg2
    engine = create_engine(db_url)

    with engine.connect() as conn:
        result = conn.execute(text("SELECT email, name FROM users ORDER BY created_at"))
        users = [{"email": row[0], "name": row[1]} for row in result]

    return users


def send_to_all_users(dry_run=True):
    """Send feature update email to all users."""
    users = get_all_users()

    print(f"\n{'='*50}")
    print(f"Feature Update Email Campaign")
    print(f"{'='*50}")
    print(f"Total users: {len(users)}")
    print(f"Mode: {'DRY RUN (no emails sent)' if dry_run else 'LIVE - SENDING EMAILS'}")
    print(f"{'='*50}\n")

    if dry_run:
        print("Users who would receive emails:\n")
        for i, user in enumerate(users, 1):
            print(f"  {i}. {user['name']} <{user['email']}>")
        print(f"\nTo send for real, run: python scripts/send_feature_update.py --send")
        return

    # Confirm before sending
    confirm = input(f"\nAre you sure you want to send {len(users)} emails? (yes/no): ")
    if confirm.lower() != 'yes':
        print("Aborted.")
        return

    success = 0
    failed = 0

    for i, user in enumerate(users, 1):
        email = user['email']
        name = user['name']

        print(f"[{i}/{len(users)}] Sending to {name} <{email}>...", end=" ")

        try:
            result = email_service.send_feature_update_email(email, name)
            if result:
                print("✓")
                success += 1
            else:
                print("✗ (disabled or failed)")
                failed += 1
        except Exception as e:
            print(f"✗ Error: {e}")
            failed += 1

        # Small delay to avoid rate limits (Resend allows 10/sec)
        time.sleep(0.2)

    print(f"\n{'='*50}")
    print(f"Campaign Complete!")
    print(f"{'='*50}")
    print(f"Sent: {success}")
    print(f"Failed: {failed}")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    dry_run = "--send" not in sys.argv
    send_to_all_users(dry_run=dry_run)
