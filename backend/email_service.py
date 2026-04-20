"""
Email Service for ChatMaster Password Authentication
Feature: chatmaster-password-auth

Sends password reset emails via SMTP with MC ChatMaster branding.
Gracefully degrades when SMTP env vars are missing — logs a warning
at startup and returns False from send_reset_email().

Uses smtplib run in a thread executor for async compatibility.
"""

import asyncio
import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending password reset emails via SMTP"""

    EMAIL_SUBJECT = "MC ChatMaster - Password Reset"

    def __init__(self):
        """
        Initialize email service from environment variables.

        Required env vars for email to be enabled:
        - EMAIL_SMTP_HOST
        - EMAIL_FROM_ADDRESS
        - EMAIL_SMTP_PASSWORD

        Optional:
        - EMAIL_SMTP_PORT (default 587)
        - FRONTEND_URL (default http://localhost:3000)
        """
        self.smtp_host = os.getenv("EMAIL_SMTP_HOST")
        self.smtp_port = int(os.getenv("EMAIL_SMTP_PORT", "587"))
        self.from_address = os.getenv("EMAIL_FROM_ADDRESS")
        self.smtp_password = os.getenv("EMAIL_SMTP_PASSWORD")
        self.frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip("/")

        self.enabled = all([self.smtp_host, self.from_address, self.smtp_password])

        if not self.enabled:
            missing = []
            if not self.smtp_host:
                missing.append("EMAIL_SMTP_HOST")
            if not self.from_address:
                missing.append("EMAIL_FROM_ADDRESS")
            if not self.smtp_password:
                missing.append("EMAIL_SMTP_PASSWORD")
            logger.warning(
                "⚠️  Email service disabled — missing environment variables: %s. "
                "Forgot-password feature will be unavailable.",
                ", ".join(missing),
            )

    async def send_reset_email(self, email: str, token: str) -> bool:
        """
        Send a password reset email.

        Args:
            email: Recipient email address
            token: Password reset token

        Returns:
            True on success, False on failure or when service is disabled
        """
        if not self.enabled:
            logger.warning("Email service is disabled — cannot send reset email to %s", email)
            return False

        try:
            reset_url = self._build_reset_url(token)
            html_body = self._build_email_html(reset_url)

            msg = MIMEMultipart("alternative")
            msg["Subject"] = self.EMAIL_SUBJECT
            msg["From"] = self.from_address
            msg["To"] = email

            # Plain-text fallback
            plain_text = (
                f"MC ChatMaster - Password Reset\n\n"
                f"You requested a password reset for your MC ChatMaster account.\n\n"
                f"Click the link below to reset your password:\n{reset_url}\n\n"
                f"This link expires in 1 hour.\n\n"
                f"If you didn't request this, you can safely ignore this email."
            )
            msg.attach(MIMEText(plain_text, "plain"))
            msg.attach(MIMEText(html_body, "html"))

            # Run blocking SMTP in a thread executor
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._send_smtp, msg)

            logger.info("✅ Password reset email sent to %s", email)
            return True

        except Exception as e:
            logger.error("❌ Failed to send reset email to %s: %s", email, str(e))
            return False

    def _send_smtp(self, msg: MIMEMultipart) -> None:
        """Send email via SMTP (blocking — intended for thread executor)."""
        with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            # SendGrid requires username "apikey" (literal); other SMTP providers use the from address
            smtp_username = os.getenv("EMAIL_SMTP_USERNAME", "apikey")
            server.login(smtp_username, self.smtp_password)
            server.send_message(msg)

    def _build_reset_url(self, token: str) -> str:
        """
        Build the password reset URL.

        Args:
            token: Reset token

        Returns:
            Full reset URL in format {FRONTEND_URL}/reset-password?token={token}
        """
        return f"{self.frontend_url}/reset-password?token={token}"

    def _build_email_html(self, reset_url: str) -> str:
        """
        Build MC ChatMaster branded HTML email template.

        Args:
            reset_url: The password reset URL

        Returns:
            HTML string for the email body
        """
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{self.EMAIL_SUBJECT}</title>
</head>
<body style="margin:0;padding:0;background-color:#f0f4f8;font-family:Arial,Helvetica,sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f0f4f8;padding:40px 0;">
    <tr>
      <td align="center">
        <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="background-color:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.1);">
          <!-- Header -->
          <tr>
            <td style="background:linear-gradient(135deg,#1e3a5f 0%,#2563eb 100%);padding:32px 40px;text-align:center;">
              <h1 style="margin:0;color:#ffffff;font-size:28px;font-weight:700;letter-spacing:0.5px;">
                MC ChatMaster
              </h1>
              <p style="margin:8px 0 0;color:#93c5fd;font-size:14px;">
                AI-Powered Technical Documentation Assistant
              </p>
            </td>
          </tr>
          <!-- Body -->
          <tr>
            <td style="padding:40px;">
              <h2 style="margin:0 0 16px;color:#1e3a5f;font-size:22px;">Password Reset Request</h2>
              <p style="margin:0 0 24px;color:#4b5563;font-size:16px;line-height:1.6;">
                We received a request to reset the password for your MC ChatMaster account.
                Click the button below to set a new password.
              </p>
              <!-- CTA Button -->
              <table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 auto 24px;">
                <tr>
                  <td style="border-radius:6px;background-color:#2563eb;">
                    <a href="{reset_url}"
                       target="_blank"
                       style="display:inline-block;padding:14px 32px;color:#ffffff;font-size:16px;font-weight:600;text-decoration:none;border-radius:6px;">
                      Reset My Password
                    </a>
                  </td>
                </tr>
              </table>
              <!-- Expiry notice -->
              <p style="margin:0 0 16px;color:#6b7280;font-size:14px;line-height:1.5;">
                ⏰ This link will expire in <strong>1 hour</strong>. After that you'll need to request a new reset.
              </p>
              <!-- Fallback link -->
              <p style="margin:0 0 24px;color:#6b7280;font-size:13px;line-height:1.5;">
                If the button doesn't work, copy and paste this URL into your browser:<br>
                <a href="{reset_url}" style="color:#2563eb;word-break:break-all;">{reset_url}</a>
              </p>
              <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0;">
              <!-- Disclaimer -->
              <p style="margin:0;color:#9ca3af;font-size:13px;line-height:1.5;">
                If you didn't request a password reset, you can safely ignore this email.
                Your password will remain unchanged.
              </p>
            </td>
          </tr>
          <!-- Footer -->
          <tr>
            <td style="background-color:#f9fafb;padding:24px 40px;text-align:center;border-top:1px solid #e5e7eb;">
              <p style="margin:0;color:#9ca3af;font-size:12px;">
                &copy; MC ChatMaster &mdash; MC Press Online
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""
