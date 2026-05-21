"""
Direct script to send a thank you email for limit increase approval.
"""
import os
import resend
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv("backend/.env")

# Get Resend API key from environment variables
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", "hello@notetubeai.in")
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://notetubeai.in")

def send_thank_you_email():
    """Send a thank you email for limit increase approval."""
    # List of recipients with their details
    recipients = [
        {"email": "shrutild67@gmail.com", "name": "Shruti"}
    ]
    new_limit = 100
    
    if not RESEND_API_KEY:
        print("❌ Error: RESEND_API_KEY not found in environment variables")
        return False
        
    resend.api_key = RESEND_API_KEY
    success_count = 0
    
    for recipient in recipients:
        user_email = recipient["email"]
        user_name = recipient["name"]
        first_name = user_name.split()[0] if user_name else "there"
        
        print(f"Sending thank you email to {user_email}...")
        
        try:
            html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #111827; color: #e5e7eb;">
            <div style="max-width: 600px; margin: 0 auto; padding: 40px 20px;">
                <!-- Header -->
                <div style="text-align: center; margin-bottom: 32px;">
                    <h1 style="font-size: 28px; font-weight: bold; margin: 0;">
                        <span style="background: linear-gradient(to right, #3b82f6, #06b6d4); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;">NoteTube AI</span>
                    </h1>
                </div>

                <!-- Main Content -->
                <div style="background-color: #1f2937; border-radius: 12px; padding: 32px; border: 1px solid #374151;">
                    <p style="font-size: 18px; color: #f3f4f6; margin: 0 0 16px 0;">
                        Hey {first_name},
                    </p>

                    <p style="color: #9ca3af; line-height: 1.6; margin: 0 0 20px 0;">
                        Thank you for your feedback and for using NoteTube AI! We've reviewed your request and are happy to let you know that we've increased your video limit to <strong style="color: #10b981;">{new_limit} videos</strong>.
                    </p>

                    <p style="color: #9ca3af; line-height: 1.6; margin: 0 0 20px 0;">
                        We're thrilled to hear that you're finding NoteTube AI helpful for your CompTIA Security+ certification preparation. Your success is our success, and we're here to support your learning journey.
                    </p>

                    <p style="color: #9ca3af; line-height: 1.6; margin: 0 0 20px 0;">
                        If you have any questions, need assistance, or have suggestions for how we can improve NoteTube AI, please don't hesitate to reach out. We'd love to hear your thoughts!
                    </p>

                    <!-- CTA Button -->
                    <div style="text-align: center; margin: 32px 0;">
                        <a href="{FRONTEND_URL}/dashboard"
                           style="display: inline-block; background: linear-gradient(to right, #3b82f6, #06b6d4); color: white; font-weight: 600; padding: 14px 32px; border-radius: 8px; text-decoration: none; font-size: 16px;">
                            Continue Learning
                        </a>
                    </div>

                    <p style="color: #9ca3af; line-height: 1.6; margin: 24px 0 0 0;">
                        Best of luck with your certification!<br>
                        <strong style="color: #f3f4f6;">Ayush</strong><br>
                        <span style="font-size: 14px;">Creator, NoteTube AI</span>
                    </p>
                </div>

                <!-- Footer -->
                <div style="text-align: center; margin-top: 32px; color: #6b7280; font-size: 12px;">
                    <p style="margin: 0 0 8px 0;">
                        Made with care in India
                    </p>
                    <p style="margin: 0;">
                        <a href="{FRONTEND_URL}" style="color: #3b82f6; text-decoration: none;">notetubeai.in</a>
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

            params = {
                "from": f"Ayush from NoteTube AI <{RESEND_FROM_EMAIL}>",
                "to": [user_email],
                "subject": f"Your NoteTube AI Limit Has Been Increased to {new_limit} Videos!",
                "html": html_content,
                "reply_to": "ayush@notetubeai.in"
            }

            email = resend.Emails.send(params)
            print(f"✅ Successfully sent thank you email to {user_email}")
            success_count += 1
            
        except Exception as e:
            print(f"❌ Failed to send email to {user_email}: {str(e)}")
    
    return success_count > 0

if __name__ == "__main__":
    send_thank_you_email()
