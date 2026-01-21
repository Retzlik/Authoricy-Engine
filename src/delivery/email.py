"""
Email Delivery Module

Sends reports via Resend email service.
"""

import os
import logging
import base64
from typing import Optional
from dataclasses import dataclass
from datetime import datetime

import resend

logger = logging.getLogger(__name__)


@dataclass
class EmailResult:
    """Result of email delivery."""
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None


class EmailDelivery:
    """
    Email delivery service using Resend.

    Handles:
    - Report delivery emails
    - Follow-up sequences
    - Error notifications
    """

    DEFAULT_FROM_EMAIL = "reports@authoricy.com"
    DEFAULT_FROM_NAME = "Authoricy Intelligence"

    def __init__(
        self,
        api_key: Optional[str] = None,
        from_email: Optional[str] = None,
    ):
        """
        Initialize email delivery.

        Args:
            api_key: Resend API key (defaults to env var)
            from_email: Sender email address
        """
        self.api_key = api_key or os.getenv("RESEND_API_KEY")
        if not self.api_key:
            logger.warning("RESEND_API_KEY not set - email delivery disabled")

        self.from_email = from_email or os.getenv("FROM_EMAIL", self.DEFAULT_FROM_EMAIL)

        if self.api_key:
            resend.api_key = self.api_key

    async def send_report(
        self,
        to_email: str,
        domain: str,
        company_name: str,
        pdf_bytes: bytes,
        pdf_filename: str,
    ) -> EmailResult:
        """
        Send report delivery email with PDF attachment.

        Args:
            to_email: Recipient email
            domain: Analyzed domain
            company_name: Company name
            pdf_bytes: PDF report as bytes
            pdf_filename: Filename for attachment

        Returns:
            EmailResult indicating success/failure
        """
        if not self.api_key:
            return EmailResult(
                success=False,
                error="Email delivery not configured (missing API key)"
            )

        subject = f"Your SEO Analysis for {domain} is Ready"

        html_content = self._get_report_email_html(domain, company_name)

        # Encode PDF for attachment
        pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")

        try:
            params = {
                "from": f"{self.DEFAULT_FROM_NAME} <{self.from_email}>",
                "to": [to_email],
                "subject": subject,
                "html": html_content,
                "attachments": [
                    {
                        "filename": pdf_filename,
                        "content": pdf_base64,
                    }
                ],
            }

            response = resend.Emails.send(params)

            logger.info(f"Email sent to {to_email}: {response.get('id', 'unknown')}")

            return EmailResult(
                success=True,
                message_id=response.get("id"),
            )

        except Exception as e:
            logger.error(f"Email delivery failed: {e}")
            return EmailResult(
                success=False,
                error=str(e),
            )

    async def send_error_notification(
        self,
        to_email: str,
        domain: str,
        error_message: str,
    ) -> EmailResult:
        """
        Send error notification email.

        Args:
            to_email: Recipient email
            domain: Domain that failed
            error_message: Error description

        Returns:
            EmailResult
        """
        if not self.api_key:
            return EmailResult(success=False, error="Email not configured")

        subject = f"Issue with your SEO analysis for {domain}"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #f72585; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 30px 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Analysis Issue</h1>
                </div>
                <div class="content">
                    <p>Hi,</p>
                    <p>We encountered an issue while analyzing <strong>{domain}</strong>.</p>
                    <p>Our team has been notified and is looking into this. We'll reach out once the analysis is complete.</p>
                    <p>If you have questions, please reply to this email.</p>
                    <p>Best regards,<br>The Authoricy Team</p>
                </div>
            </div>
        </body>
        </html>
        """

        try:
            params = {
                "from": f"{self.DEFAULT_FROM_NAME} <{self.from_email}>",
                "to": [to_email],
                "subject": subject,
                "html": html_content,
            }

            response = resend.Emails.send(params)
            return EmailResult(success=True, message_id=response.get("id"))

        except Exception as e:
            logger.error(f"Error notification failed: {e}")
            return EmailResult(success=False, error=str(e))

    def _get_report_email_html(self, domain: str, company_name: str) -> str:
        """Generate HTML for report delivery email."""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }}
                .container {{ max-width: 600px; margin: 0 auto; }}
                .header {{ background: linear-gradient(135deg, #4361ee, #3f37c9); color: white; padding: 40px 20px; text-align: center; }}
                .header h1 {{ margin: 0; font-size: 24px; }}
                .content {{ padding: 40px 30px; }}
                .highlight {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; }}
                .cta {{ display: inline-block; background: #4361ee; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .footer {{ background: #f5f5f5; padding: 30px; text-align: center; font-size: 12px; color: #666; }}
                .metric {{ display: inline-block; text-align: center; margin: 0 20px; }}
                .metric-value {{ font-size: 28px; font-weight: bold; color: #4361ee; }}
                .metric-label {{ font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Your SEO Analysis is Ready</h1>
                    <p style="margin: 10px 0 0; opacity: 0.9;">{domain}</p>
                </div>

                <div class="content">
                    <p>Hi{f' {company_name}' if company_name else ''},</p>

                    <p>Great news! Your comprehensive SEO analysis for <strong>{domain}</strong> is complete.</p>

                    <div class="highlight">
                        <h3 style="margin-top: 0;">What's Inside Your Report:</h3>
                        <ul>
                            <li><strong>Current Position:</strong> Where you stand in organic search</li>
                            <li><strong>Competitive Analysis:</strong> How you compare to competitors</li>
                            <li><strong>Opportunity Map:</strong> Keywords and content gaps</li>
                            <li><strong>90-Day Roadmap:</strong> Prioritized action plan</li>
                        </ul>
                    </div>

                    <p>Your full report is attached to this email as a PDF.</p>

                    <p><strong>What's Next?</strong></p>
                    <p>After reviewing your report, we'd love to discuss how we can help you implement these recommendations. Schedule a free strategy call to dive deeper into the findings.</p>

                    <p>Questions about your report? Simply reply to this email.</p>

                    <p>Best regards,<br>
                    <strong>The Authoricy Team</strong></p>
                </div>

                <div class="footer">
                    <p>© {datetime.now().year} Authoricy. All rights reserved.</p>
                    <p>This report was generated automatically using AI-powered analysis.</p>
                </div>
            </div>
        </body>
        </html>
        """
