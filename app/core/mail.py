import httpx
import logging
import base64
from datetime import datetime
from typing import Any, Dict, Callable
from core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Email Templates ---

def _base_template(content: str) -> str:
    year = datetime.now().year
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                background-color: #f4f4f5;
                margin: 0;
                padding: 0;
            }}
            .container {{
                max-width: 600px;
                margin: 40px auto;
                background: #ffffff;
                border-radius: 12px;
                overflow: hidden;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            }}
            .header {{
                background-color: #18181b;
                padding: 32px;
                text-align: center;
            }}
            .header h1 {{
                color: #ffffff;
                margin: 0;
                font-size: 24px;
                font-weight: 600;
                letter-spacing: -0.025em;
            }}
            .content {{
                padding: 32px;
                text-align: center;
            }}
            .code-box {{
                background-color: #f4f4f5;
                border: 2px dashed #d4d4d8;
                border-radius: 8px;
                padding: 24px;
                margin: 24px 0;
            }}
            .code {{
                font-family: 'Monaco', 'Consolas', monospace;
                font-size: 32px;
                font-weight: 700;
                color: #18181b;
                letter-spacing: 2px;
            }}
            .cta-button {{
                display: inline-block;
                background-color: #18181b;
                color: #ffffff;
                text-decoration: none;
                padding: 12px 32px;
                border-radius: 6px;
                font-weight: 500;
                margin-top: 24px;
                transition: background-color 0.2s;
            }}
            .cta-button:hover {{
                background-color: #27272a;
            }}
            .footer {{
                background-color: #fafafa;
                padding: 24px;
                text-align: center;
                font-size: 14px;
                color: #a1a1aa;
                border-top: 1px solid #e4e4e7;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Welcome to huzlr.</h1>
            </div>
            <div class="content">
                {content}
            </div>
            <div class="footer">
                <p>&copy; {year} Huzlr. All rights reserved.</p>
                <p>If you didn't request this, please ignore this email.</p>
            </div>
        </div>
    </body>
    </html>
    """

def template_access_code(context: Dict[str, Any]) -> str:
    code = context.get("code", "")
    frontend_url = context.get("frontend_url", settings.FRONTEND_BASE_URL)
    
    content = f"""
        <p class="welcome-text" style="font-size: 18px; color: #52525b; margin-bottom: 24px;">
            You've been invited to join the inner circle.
        </p>
        <p>Here is your exclusive access code to unlock the platform:</p>
        
        <div class="code-box">
            <div class="code">{code}</div>
        </div>
        
        <p>Enter this code on the onboarding screen to get started.</p>
        
        <a href="{frontend_url}" class="cta-button">Go to Huzlr</a>
    """
    return _base_template(content)

def template_welcome(context: Dict[str, Any]) -> str:
    username = context.get("username", "there")
    frontend_url = context.get("frontend_url", settings.FRONTEND_BASE_URL)
    
    content = f"""
        <p class="welcome-text" style="font-size: 18px; color: #52525b; margin-bottom: 24px;">
            Welcome to the team, {username}.
        </p>
        <p>We're thrilled to have you on board. Huzlr is designed to help you streamline your standups and boost productivity.</p>
        
        <p>You can now access your dashboard and start managing your projects.</p>
        
        <a href="{frontend_url}/dashboard" class="cta-button">Go to Dashboard</a>
    """
    return _base_template(content)

# Registry mapping template names to functions
TEMPLATES: Dict[str, Callable[[Dict[str, Any]], str]] = {
    "access_code": template_access_code,
    "welcome": template_welcome,
}

# --- Async Sender Function ---

async def send_email(to_email: str, subject: str, template_name: str, context: Dict[str, Any] = {}) -> bool:
    """
    Sends an email using a specified template via Mailjet Send API (Async).
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        template_name: Name of the template to use (must be in TEMPLATES)
        context: Dictionary of data to pass to the template
    """
    if not settings.MAILJET_API_KEY or not settings.MAILJET_SECRET_KEY:
        logger.warning("Mailjet credentials not found. Skipping email send.")
        return False

    template_func = TEMPLATES.get(template_name)
    if not template_func:
        logger.error(f"Template '{template_name}' not found.")
        return False

    try:
        html_content = template_func(context)
        text_content = f"Please view this email in HTML. Subject: {subject}"
        
        sender_email = settings.MAILJET_SENDER_EMAIL
        logger.info(f"Attempting to send email FROM: {sender_email} TO: {to_email}")
        
        data = {
          'Messages': [
            {
              "From": {
                "Email": sender_email,
                "Name": "Huzlr Team"
              },
              "To": [
                {
                  "Email": to_email,
                  "Name": "User"
                }
              ],
              "Subject": subject,
              "HTMLPart": html_content,
              "TextPart": text_content
            }
          ]
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.mailjet.com/v3.1/send",
                json=data,
                auth=(settings.MAILJET_API_KEY, settings.MAILJET_SECRET_KEY),
                timeout=10.0
            )

        logger.info(f"Mailjet Response: {response.status_code} - {response.text}")
        
        if response.status_code == 200:
            logger.info(f"Email sent successfully to {to_email}")
            return True
        else:
            logger.error(f"Failed to send email: {response.status_code} {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        return False
