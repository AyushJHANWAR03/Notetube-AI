"""
Script to send a thank you email for limit increase approval.
"""
import asyncio
import sys
import os
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = str(Path(__file__).parent.parent / "backend")
sys.path.insert(0, backend_dir)

# Import after path setup
from app.core.config import settings
from app.services.email_service import email_service

async def send_thank_you_email():
    """Send a thank you email for limit increase approval."""
    user_email = "kenishkumar007@gmail.com"
    user_name = "Kenish R"
    new_limit = 100
    
    print(f"Sending thank you email to {user_email}...")
    
    success = await email_service.send_limit_increase_approval(
        to_email=user_email,
        user_name=user_name,
        new_limit=new_limit
    )
    
    if success:
        print(f"✅ Successfully sent thank you email to {user_email}")
    else:
        print(f"❌ Failed to send email to {user_email}")
        print("Please check the logs for more details.")

if __name__ == "__main__":
    asyncio.run(send_thank_you_email())
