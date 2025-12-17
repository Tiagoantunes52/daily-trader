"""Email service for sending market tips to users."""

import smtplib
import time
import uuid
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from src.models.trading_tip import EmailContent, TradingTip
from src.models.market_data import MarketData
from src.utils.config import config
from src.database.models import DeliveryLog
from src.utils.logger import StructuredLogger
from src.utils.trace_context import get_current_trace
from src.utils.event_store import EventStore


class EmailService:
    """Handles email sending with retry logic and delivery logging."""

    def __init__(self, db_session: Session = None, event_store: EventStore = None):
        """
        Initialize email service.
        
        Args:
            db_session: SQLAlchemy database session for logging
            event_store: EventStore instance for tracking operations
        """
        self.db_session = db_session
        self.event_store = event_store
        self.logger = StructuredLogger("email_service")
        self.smtp_server = config.email.smtp_server
        self.smtp_port = config.email.smtp_port
        self.sender_email = config.email.sender_email
        self.sender_password = config.email.sender_password
        self.retry_delays = config.email.retry_delays

    def send_email(self, recipient: str, subject: str, content: str, delivery_type: str = "manual") -> bool:
        """
        Send an email with retry logic.
        
        Args:
            recipient: Email address to send to
            subject: Email subject line
            content: Email body content
            delivery_type: Type of delivery (morning, evening, manual)
            
        Returns:
            True if sent successfully, False otherwise
        """
        trace_id = get_current_trace()
        max_attempts = len(self.retry_delays) + 1
        
        # Log email send start
        self.logger.info(
            "Starting email send operation",
            context={
                "recipient": recipient,
                "subject": subject,
                "delivery_type": delivery_type,
                "trace_id": trace_id
            }
        )
        
        if self.event_store and trace_id:
            self.event_store.add_event(
                trace_id=trace_id,
                event_type="email_send_start",
                component="email_service",
                message=f"Starting email send to {recipient}",
                context={
                    "recipient": recipient,
                    "subject": subject,
                    "delivery_type": delivery_type
                }
            )
        
        for attempt in range(1, max_attempts + 1):
            try:
                # Create message
                message = MIMEMultipart("alternative")
                message["Subject"] = subject
                message["From"] = self.sender_email
                message["To"] = recipient
                
                # Attach plain text and HTML versions
                text_part = MIMEText(self._strip_html(content), "plain")
                html_part = MIMEText(content, "html")
                message.attach(text_part)
                message.attach(html_part)
                
                # Send email
                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                    server.starttls()
                    server.login(self.sender_email, self.sender_password)
                    server.send_message(message)
                
                # Log successful delivery
                self.logger.info(
                    "Email sent successfully",
                    context={
                        "recipient": recipient,
                        "subject": subject,
                        "delivery_type": delivery_type,
                        "attempt": attempt,
                        "trace_id": trace_id
                    }
                )
                
                if self.event_store and trace_id:
                    self.event_store.add_event(
                        trace_id=trace_id,
                        event_type="email_send_complete",
                        component="email_service",
                        message=f"Email sent successfully to {recipient}",
                        context={
                            "recipient": recipient,
                            "subject": subject,
                            "delivery_type": delivery_type,
                            "status": "success",
                            "attempt": attempt
                        }
                    )
                
                self.log_delivery("success", recipient, datetime.now(timezone.utc), delivery_type, attempt)
                return True
                
            except Exception as e:
                error_message = str(e)
                
                if attempt < max_attempts:
                    # Log retry attempt
                    delay = self.retry_delays[attempt - 1]
                    self.logger.warning(
                        f"Email send failed, retrying in {delay}s",
                        context={
                            "recipient": recipient,
                            "subject": subject,
                            "delivery_type": delivery_type,
                            "attempt": attempt,
                            "error": error_message,
                            "retry_delay_seconds": delay,
                            "trace_id": trace_id
                        }
                    )
                    
                    if self.event_store and trace_id:
                        self.event_store.add_event(
                            trace_id=trace_id,
                            event_type="email_send_retry",
                            component="email_service",
                            message=f"Email send failed, retrying in {delay}s",
                            context={
                                "recipient": recipient,
                                "subject": subject,
                                "delivery_type": delivery_type,
                                "attempt": attempt,
                                "error": error_message,
                                "retry_delay_seconds": delay
                            }
                        )
                    
                    self.log_delivery("retrying", recipient, datetime.now(timezone.utc), delivery_type, attempt, error_message)
                    
                    # Wait before retrying with exponential backoff
                    time.sleep(delay)
                else:
                    # Log final failure
                    self.logger.error(
                        "Email send failed after all retry attempts",
                        context={
                            "recipient": recipient,
                            "subject": subject,
                            "delivery_type": delivery_type,
                            "attempts": max_attempts,
                            "error": error_message,
                            "trace_id": trace_id
                        },
                        exception=e
                    )
                    
                    if self.event_store and trace_id:
                        self.event_store.add_event(
                            trace_id=trace_id,
                            event_type="email_send_failed",
                            component="email_service",
                            message=f"Email send failed after {max_attempts} attempts",
                            context={
                                "recipient": recipient,
                                "subject": subject,
                                "delivery_type": delivery_type,
                                "attempts": max_attempts,
                                "error": error_message
                            }
                        )
                    
                    self.log_delivery("failed", recipient, datetime.now(timezone.utc), delivery_type, attempt, error_message)
                    return False
        
        return False

    def send_email_content(self, email_content: EmailContent) -> bool:
        """
        Send formatted email content with tips and market data.
        
        Args:
            email_content: EmailContent object with tips and market data
            
        Returns:
            True if sent successfully, False otherwise
        """
        html_content = self._format_email_html(email_content)
        
        return self.send_email(
            recipient=email_content.recipient,
            subject=email_content.subject,
            content=html_content,
            delivery_type=email_content.delivery_type
        )

    def log_delivery(
        self,
        status: str,
        recipient: str,
        timestamp: datetime,
        delivery_type: str = "manual",
        attempt_number: int = 1,
        error_message: str = None
    ) -> None:
        """
        Log email delivery attempt.
        
        Args:
            status: Delivery status (success, failed, retrying)
            recipient: Recipient email address
            timestamp: When the delivery was attempted
            delivery_type: Type of delivery (morning, evening, manual)
            attempt_number: Which attempt this is
            error_message: Error message if delivery failed
        """
        if self.db_session is None:
            return
        
        # Ensure timestamp is timezone-aware
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        
        log_entry = DeliveryLog(
            id=str(uuid.uuid4()),
            recipient=recipient,
            status=status,
            delivery_type=delivery_type,
            attempt_number=attempt_number,
            error_message=error_message,
            attempted_at=timestamp
        )
        
        self.db_session.add(log_entry)
        self.db_session.commit()

    def _format_email_html(self, email_content: EmailContent) -> str:
        """
        Format email content as HTML with tips and market data.
        
        Args:
            email_content: EmailContent object
            
        Returns:
            HTML formatted email content
        """
        delivery_label = "Morning" if email_content.delivery_type == "morning" else "Evening"
        
        html = f"""
        <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background-color: #2c3e50; color: white; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
                    .tip {{ background-color: #f8f9fa; border-left: 4px solid #007bff; padding: 15px; margin-bottom: 15px; border-radius: 3px; }}
                    .tip-header {{ font-weight: bold; font-size: 16px; margin-bottom: 8px; }}
                    .recommendation {{ font-weight: bold; padding: 5px 10px; border-radius: 3px; display: inline-block; margin-bottom: 8px; }}
                    .buy {{ background-color: #d4edda; color: #155724; }}
                    .sell {{ background-color: #f8d7da; color: #721c24; }}
                    .hold {{ background-color: #fff3cd; color: #856404; }}
                    .reasoning {{ margin: 10px 0; font-style: italic; }}
                    .indicators {{ margin: 10px 0; font-size: 14px; }}
                    .source {{ font-size: 12px; color: #666; margin-top: 8px; }}
                    .market-data {{ background-color: #f8f9fa; padding: 15px; margin-bottom: 15px; border-radius: 3px; }}
                    .footer {{ text-align: center; font-size: 12px; color: #666; margin-top: 30px; border-top: 1px solid #ddd; padding-top: 20px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>{delivery_label} Market Tips</h1>
                        <p>Expert-analyzed trading recommendations for your portfolio</p>
                    </div>
        """
        
        # Add tips
        if email_content.tips:
            html += "<h2>Trading Tips</h2>"
            for tip in email_content.tips:
                html += self._format_tip_html(tip)
        
        # Add market data
        if email_content.market_data:
            html += "<h2>Market Data</h2>"
            for market_data in email_content.market_data:
                html += self._format_market_data_html(market_data)
        
        html += """
                    <div class="footer">
                        <p>This is an automated message from Daily Market Tips.</p>
                        <p>Generated at """ + email_content.generated_at.strftime("%Y-%m-%d %H:%M:%S") + """ UTC</p>
                    </div>
                </div>
            </body>
        </html>
        """
        
        return html

    def _format_tip_html(self, tip: TradingTip) -> str:
        """Format a single trading tip as HTML."""
        rec_class = tip.recommendation.lower()
        
        html = f"""
        <div class="tip">
            <div class="tip-header">{tip.symbol} ({tip.type.upper()})</div>
            <div class="recommendation {rec_class}">{tip.recommendation}</div>
            <div class="reasoning"><strong>Analysis:</strong> {tip.reasoning}</div>
            <div class="indicators"><strong>Indicators:</strong> {", ".join(tip.indicators)}</div>
            <div class="source">
                <strong>Sources:</strong>
        """
        
        for source in tip.sources:
            html += f'<br><a href="{source.url}">{source.name}</a>'
        
        html += f"""
                <br><strong>Confidence:</strong> {tip.confidence}%
            </div>
        </div>
        """
        
        return html

    def _format_market_data_html(self, market_data: MarketData) -> str:
        """Format market data as HTML."""
        html = f"""
        <div class="market-data">
            <strong>{market_data.symbol} ({market_data.type.upper()})</strong><br>
            <strong>Current Price:</strong> ${market_data.current_price:.2f}<br>
            <strong>24h Change:</strong> {market_data.price_change_24h:+.2f}%<br>
            <strong>24h Volume:</strong> ${market_data.volume_24h:,.0f}<br>
            <strong>Source:</strong> <a href="{market_data.source.url}">{market_data.source.name}</a>
        </div>
        """
        
        return html

    def _strip_html(self, html: str) -> str:
        """Strip HTML tags for plain text version."""
        import re
        # Remove HTML tags
        text = re.sub('<[^<]+?>', '', html)
        # Decode HTML entities
        text = text.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
        return text
