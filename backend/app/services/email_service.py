"""
Email service using Resend for transactional emails.
"""
import resend
from typing import Optional
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails via Resend."""

    def __init__(self):
        if settings.RESEND_API_KEY:
            resend.api_key = settings.RESEND_API_KEY
            self.enabled = True
        else:
            self.enabled = False
            logger.warning("RESEND_API_KEY not configured - emails disabled")

    def _get_welcome_email_html(self, user_name: str) -> str:
        """Generate welcome email HTML template."""
        first_name = user_name.split()[0] if user_name else "there"

        return f"""
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
                I'm Ayush, the creator of NoteTube AI. I just wanted to say thanks for signing up!
            </p>

            <p style="color: #9ca3af; line-height: 1.6; margin: 0 0 20px 0;">
                I built NoteTube AI to help people like you learn from YouTube videos 10x faster - with AI-powered notes, smart chapters, flashcards, and the ability to jump to any topic instantly.
            </p>

            <p style="color: #9ca3af; line-height: 1.6; margin: 0 0 20px 0;">
                If you have a moment, I'd love to hear:
            </p>

            <ul style="color: #9ca3af; line-height: 1.8; margin: 0 0 20px 0; padding-left: 20px;">
                <li>What are you using NoteTube AI for?</li>
                <li>What's your favorite feature?</li>
                <li>Any suggestions or feedback?</li>
            </ul>

            <p style="color: #9ca3af; line-height: 1.6; margin: 0 0 20px 0;">
                Just hit reply - I read every email and would love to help!
            </p>

            <!-- CTA Button -->
            <div style="text-align: center; margin: 32px 0;">
                <a href="{settings.FRONTEND_URL}/dashboard"
                   style="display: inline-block; background: linear-gradient(to right, #3b82f6, #06b6d4); color: white; font-weight: 600; padding: 14px 32px; border-radius: 8px; text-decoration: none; font-size: 16px;">
                    Start Analyzing Videos
                </a>
            </div>

            <!-- Quick Tips - All 6 Features -->
            <div style="background-color: #111827; border-radius: 8px; padding: 20px; margin-top: 24px;">
                <p style="color: #f3f4f6; font-weight: 600; margin: 0 0 12px 0; font-size: 14px;">
                    What you can do with NoteTube AI:
                </p>
                <ul style="color: #9ca3af; line-height: 1.8; margin: 0; padding-left: 20px; font-size: 14px;">
                    <li><strong style="color: #3b82f6;">Take Me There</strong> - AI semantic search to find any moment in the video</li>
                    <li><strong style="color: #06b6d4;">Transcript</strong> - Full searchable transcript with timestamps and auto-scroll</li>
                    <li><strong style="color: #eab308;">User Notes</strong> - Save selections from transcript and rewrite with AI</li>
                    <li><strong style="color: #a855f7;">Chat</strong> - Chat with AI about video content and get instant answers</li>
                    <li><strong style="color: #f97316;">Breakdown</strong> - AI-generated chapters with summaries for easy navigation</li>
                    <li><strong style="color: #22c55e;">Flashcards</strong> - Auto-generated flashcards to test your knowledge</li>
                </ul>
            </div>

            <p style="color: #9ca3af; line-height: 1.6; margin: 24px 0 0 0;">
                Best,<br>
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
                <a href="{settings.FRONTEND_URL}" style="color: #3b82f6; text-decoration: none;">notetubeai.in</a>
            </p>
        </div>
    </div>
</body>
</html>
"""

    async def send_welcome_email(self, to_email: str, user_name: str) -> bool:
        """
        Send welcome email to new user.

        Args:
            to_email: User's email address
            user_name: User's display name

        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.enabled:
            logger.info(f"Email disabled - would send welcome email to {to_email}")
            return False

        try:
            first_name = user_name.split()[0] if user_name else "there"

            params = {
                "from": f"Ayush from NoteTube AI <hello@{settings.RESEND_FROM_DOMAIN}>",
                "to": [to_email],
                "subject": f"Welcome to NoteTube AI, {first_name}!",
                "html": self._get_welcome_email_html(user_name),
                "reply_to": "ayush@notetubeai.in"
            }

            email = resend.Emails.send(params)
            logger.info(f"Welcome email sent to {to_email}: {email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send welcome email to {to_email}: {e}")
            return False


    def _get_limit_increase_email_html(
        self,
        user_email: str,
        user_name: str,
        feedback: str,
        videos_analyzed: int,
        video_limit: int
    ) -> str:
        """Generate limit increase request email HTML template."""
        return f"""
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
            <h1 style="font-size: 24px; font-weight: bold; margin: 0; color: #f59e0b;">
                Limit Increase Request
            </h1>
        </div>

        <!-- Main Content -->
        <div style="background-color: #1f2937; border-radius: 12px; padding: 32px; border: 1px solid #374151;">
            <h2 style="font-size: 18px; color: #f3f4f6; margin: 0 0 20px 0;">
                User Details
            </h2>

            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px 0; color: #9ca3af;">Name:</td>
                    <td style="padding: 8px 0; color: #f3f4f6; font-weight: 600;">{user_name}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #9ca3af;">Email:</td>
                    <td style="padding: 8px 0; color: #3b82f6;">{user_email}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #9ca3af;">Videos Analyzed:</td>
                    <td style="padding: 8px 0; color: #f3f4f6;">{videos_analyzed} / {video_limit}</td>
                </tr>
            </table>

            <hr style="border: none; border-top: 1px solid #374151; margin: 24px 0;">

            <h2 style="font-size: 18px; color: #f3f4f6; margin: 0 0 16px 0;">
                User Feedback
            </h2>

            <div style="background-color: #111827; border-radius: 8px; padding: 16px; border-left: 4px solid #3b82f6;">
                <p style="color: #d1d5db; line-height: 1.6; margin: 0; white-space: pre-wrap;">{feedback}</p>
            </div>

            <div style="margin-top: 24px; text-align: center;">
                <p style="color: #9ca3af; font-size: 14px; margin: 0;">
                    To increase the user's limit, run this SQL:
                </p>
                <code style="display: block; background-color: #111827; padding: 12px; border-radius: 6px; color: #10b981; font-size: 12px; margin-top: 8px; word-break: break-all;">
                    UPDATE users SET video_limit = 10 WHERE email = '{user_email}';
                </code>
            </div>
        </div>
    </div>
</body>
</html>
"""

    async def send_limit_increase_request(
        self,
        user_email: str,
        user_name: str,
        feedback: str,
        videos_analyzed: int,
        video_limit: int
    ) -> bool:
        """
        Send limit increase request email to admin.

        Args:
            user_email: User's email address
            user_name: User's display name
            feedback: User's feedback/reason for request
            videos_analyzed: Current videos analyzed count
            video_limit: Current video limit

        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.enabled:
            logger.info(f"Email disabled - would send limit increase request for {user_email}")
            return False

        try:
            params = {
                "from": f"NoteTube AI <hello@{settings.RESEND_FROM_DOMAIN}>",
                "to": ["ayush@notetubeai.in"],
                "subject": f"Limit Increase Request: {user_name} ({user_email})",
                "html": self._get_limit_increase_email_html(
                    user_email, user_name, feedback, videos_analyzed, video_limit
                ),
                "reply_to": user_email
            }

            email = resend.Emails.send(params)
            logger.info(f"Limit increase request email sent for {user_email}: {email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send limit increase email for {user_email}: {e}")
            return False

    def _get_feature_update_email_html(self, user_name: str) -> str:
        """Generate feature update announcement email HTML template."""
        first_name = user_name.split()[0] if user_name else "there"

        return f"""
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
                Hey {first_name}!
            </p>

            <p style="color: #9ca3af; line-height: 1.6; margin: 0 0 20px 0;">
                I've been working hard on NoteTube AI and wanted to share some exciting updates with you!
            </p>

            <p style="color: #f3f4f6; font-weight: 600; margin: 0 0 16px 0; font-size: 16px;">
                Here's what's new:
            </p>

            <!-- Feature Updates -->
            <div style="background-color: #111827; border-radius: 8px; padding: 20px; margin-bottom: 24px;">
                <div style="margin-bottom: 16px;">
                    <span style="color: #3b82f6; font-size: 18px;">&#128269;</span>
                    <strong style="color: #3b82f6; margin-left: 8px;">Take Me There 2.0</strong>
                    <p style="color: #9ca3af; margin: 4px 0 0 28px; font-size: 14px;">Semantic search now uses AI embeddings for instant, accurate results</p>
                </div>

                <div style="margin-bottom: 16px;">
                    <span style="color: #a855f7; font-size: 18px;">&#128172;</span>
                    <strong style="color: #a855f7; margin-left: 8px;">Smarter Chat</strong>
                    <p style="color: #9ca3af; margin: 4px 0 0 28px; font-size: 14px;">Have deeper conversations about video content with improved AI responses</p>
                </div>

                <div style="margin-bottom: 16px;">
                    <span style="color: #f97316; font-size: 18px;">&#128209;</span>
                    <strong style="color: #f97316; margin-left: 8px;">Perfect Chapters</strong>
                    <p style="color: #9ca3af; margin: 4px 0 0 28px; font-size: 14px;">AI-generated breakdowns are now more accurate with better summaries</p>
                </div>

                <div style="margin-bottom: 16px;">
                    <span style="color: #22c55e; font-size: 18px;">&#127183;</span>
                    <strong style="color: #22c55e; margin-left: 8px;">Dynamic Flashcards</strong>
                    <p style="color: #9ca3af; margin: 4px 0 0 28px; font-size: 14px;">Flashcards now flip with smooth animations - perfect for learning</p>
                </div>

                <div>
                    <span style="color: #06b6d4; font-size: 18px;">&#10024;</span>
                    <strong style="color: #06b6d4; margin-left: 8px;">Fresh New UI</strong>
                    <p style="color: #9ca3af; margin: 4px 0 0 28px; font-size: 14px;">Cleaner interface that's easier to navigate</p>
                </div>
            </div>

            <!-- New: Try without Sign In -->
            <div style="background: linear-gradient(to right, #3b82f620, #06b6d420); border-radius: 8px; padding: 16px; margin-bottom: 24px; border: 1px solid #3b82f640;">
                <p style="color: #f3f4f6; margin: 0; font-size: 14px;">
                    <strong>New:</strong> Your friends can now try NoteTube AI without signing in! Share the love &#128640;
                </p>
            </div>

            <p style="color: #9ca3af; line-height: 1.6; margin: 0 0 20px 0;">
                I'd love to hear what you think! Just hit reply with any feedback.
            </p>

            <!-- CTA Button -->
            <div style="text-align: center; margin: 32px 0;">
                <a href="{settings.FRONTEND_URL}/dashboard"
                   style="display: inline-block; background: linear-gradient(to right, #3b82f6, #06b6d4); color: white; font-weight: 600; padding: 14px 32px; border-radius: 8px; text-decoration: none; font-size: 16px;">
                    Try the New Features
                </a>
            </div>

            <p style="color: #9ca3af; line-height: 1.6; margin: 24px 0 0 0;">
                Best,<br>
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
                <a href="{settings.FRONTEND_URL}" style="color: #3b82f6; text-decoration: none;">notetubeai.in</a>
            </p>
        </div>
    </div>
</body>
</html>
"""

    def send_feature_update_email(self, to_email: str, user_name: str) -> bool:
        """
        Send feature update announcement email to a user.

        Args:
            to_email: User's email address
            user_name: User's display name

        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.enabled:
            logger.info(f"Email disabled - would send feature update to {to_email}")
            return False

        try:
            first_name = user_name.split()[0] if user_name else "there"

            params = {
                "from": f"Ayush from NoteTube AI <hello@{settings.RESEND_FROM_DOMAIN}>",
                "to": [to_email],
                "subject": f"{first_name}, NoteTube AI just got a major upgrade!",
                "html": self._get_feature_update_email_html(user_name),
                "reply_to": "ayush@notetubeai.in"
            }

            email = resend.Emails.send(params)
            logger.info(f"Feature update email sent to {to_email}: {email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send feature update email to {to_email}: {e}")
            return False


# Singleton instance
email_service = EmailService()
