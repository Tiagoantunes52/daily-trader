"""Scheduler service for managing timed email deliveries."""

import logging
import time
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session
from src.services.email_service import EmailService
from src.services.market_data_aggregator import MarketDataAggregator
from src.services.analysis_engine import AnalysisEngine
from src.models.trading_tip import EmailContent
from src.database.db import SessionLocal
from src.utils.logger import StructuredLogger
from src.utils.trace_context import create_trace, clear_trace, get_current_trace
from src.utils.event_store import EventStore

logger = logging.getLogger(__name__)
structured_logger = StructuredLogger("SchedulerService")


class SchedulerService:
    """Manages scheduled email deliveries at configured times."""

    def __init__(self, db_session: Session = None, event_store: EventStore = None):
        """
        Initialize scheduler service.
        
        Args:
            db_session: SQLAlchemy database session
            event_store: EventStore instance for tracking operations
        """
        self.scheduler = BackgroundScheduler()
        self.db_session = db_session
        self.event_store = event_store
        self.email_service = EmailService(db_session, event_store)
        self.market_aggregator = MarketDataAggregator()
        self.analysis_engine = AnalysisEngine(event_store)
        self.is_running = False

    def schedule_deliveries(self, morning_time: str, evening_time: str) -> None:
        """
        Set up recurring delivery schedule.
        
        Args:
            morning_time: Time for morning delivery (HH:MM format)
            evening_time: Time for evening delivery (HH:MM format)
            
        Raises:
            ValueError: If time format is invalid
        """
        # Validate time format
        self._validate_time_format(morning_time)
        self._validate_time_format(evening_time)
        
        # Parse times
        morning_hour, morning_minute = map(int, morning_time.split(":"))
        evening_hour, evening_minute = map(int, evening_time.split(":"))
        
        # Schedule morning delivery
        self.scheduler.add_job(
            self.execute_delivery,
            CronTrigger(hour=morning_hour, minute=morning_minute),
            args=["morning"],
            id="morning_delivery",
            name="Morning Market Tips Delivery",
            replace_existing=True
        )
        logger.info(f"Scheduled morning delivery at {morning_time}")
        
        # Schedule evening delivery
        self.scheduler.add_job(
            self.execute_delivery,
            CronTrigger(hour=evening_hour, minute=evening_minute),
            args=["evening"],
            id="evening_delivery",
            name="Evening Market Tips Delivery",
            replace_existing=True
        )
        logger.info(f"Scheduled evening delivery at {evening_time}")
        
        # Start scheduler if not already running
        if not self.is_running:
            self.scheduler.start()
            self.is_running = True
            logger.info("Scheduler started")

    def execute_delivery(self, delivery_type: str) -> None:
        """
        Execute the email sending process.
        
        Args:
            delivery_type: Either "morning" or "evening"
        """
        # Create a new trace for this delivery operation
        trace_id = create_trace()
        start_time = time.time()
        
        if delivery_type not in ["morning", "evening"]:
            structured_logger.error(
                f"Invalid delivery type: {delivery_type}",
                context={"trace_id": trace_id, "delivery_type": delivery_type}
            )
            clear_trace()
            return
        
        try:
            # Log delivery start
            structured_logger.info(
                f"Starting {delivery_type} delivery execution",
                context={
                    "trace_id": trace_id,
                    "delivery_type": delivery_type
                }
            )
            
            if self.event_store:
                self.event_store.add_event(
                    trace_id=trace_id,
                    event_type="delivery_start",
                    component="SchedulerService",
                    message=f"Starting {delivery_type} delivery",
                    context={"delivery_type": delivery_type}
                )
            
            # Fetch market data
            structured_logger.debug(
                "Fetching market data...",
                context={"trace_id": trace_id, "delivery_type": delivery_type}
            )
            
            crypto_data = self.market_aggregator.fetch_crypto_data(["bitcoin", "ethereum"])
            stock_data = self.market_aggregator.fetch_stock_data(["AAPL", "GOOGL"])
            all_market_data = crypto_data + stock_data
            
            if not all_market_data:
                structured_logger.warning(
                    f"No market data available for {delivery_type} delivery",
                    context={"trace_id": trace_id, "delivery_type": delivery_type}
                )
                if self.event_store:
                    self.event_store.add_event(
                        trace_id=trace_id,
                        event_type="delivery_failed",
                        component="SchedulerService",
                        message=f"No market data available for {delivery_type} delivery",
                        context={"delivery_type": delivery_type, "reason": "no_market_data"}
                    )
                clear_trace()
                return
            
            # Analyze market data
            structured_logger.debug(
                "Analyzing market data...",
                context={
                    "trace_id": trace_id,
                    "delivery_type": delivery_type,
                    "market_data_count": len(all_market_data)
                }
            )
            
            crypto_tips = self.analysis_engine.analyze_crypto(crypto_data)
            stock_tips = self.analysis_engine.analyze_stocks(stock_data)
            all_tips = crypto_tips + stock_tips
            
            if not all_tips:
                structured_logger.warning(
                    f"No tips generated for {delivery_type} delivery",
                    context={"trace_id": trace_id, "delivery_type": delivery_type}
                )
                if self.event_store:
                    self.event_store.add_event(
                        trace_id=trace_id,
                        event_type="delivery_failed",
                        component="SchedulerService",
                        message=f"No tips generated for {delivery_type} delivery",
                        context={"delivery_type": delivery_type, "reason": "no_tips_generated"}
                    )
                clear_trace()
                return
            
            # Format email content
            structured_logger.debug(
                "Formatting email content...",
                context={
                    "trace_id": trace_id,
                    "delivery_type": delivery_type,
                    "tips_count": len(all_tips)
                }
            )
            
            email_content = EmailContent(
                recipient="user@example.com",  # This should come from user config
                subject=f"{delivery_type.capitalize()} Market Tips - {datetime.now().strftime('%Y-%m-%d')}",
                delivery_type=delivery_type,
                tips=all_tips,
                market_data=all_market_data,
                generated_at=datetime.now()
            )
            
            # Send email
            structured_logger.debug(
                "Sending email...",
                context={
                    "trace_id": trace_id,
                    "delivery_type": delivery_type,
                    "recipient": email_content.recipient
                }
            )
            
            success = self.email_service.send_email_content(email_content)
            
            duration_ms = (time.time() - start_time) * 1000
            
            if success:
                structured_logger.info(
                    f"{delivery_type.capitalize()} delivery completed successfully",
                    context={
                        "trace_id": trace_id,
                        "delivery_type": delivery_type,
                        "tips_sent": len(all_tips),
                        "duration_ms": duration_ms
                    }
                )
                
                if self.event_store:
                    self.event_store.add_event(
                        trace_id=trace_id,
                        event_type="delivery_complete",
                        component="SchedulerService",
                        message=f"{delivery_type.capitalize()} delivery completed successfully",
                        context={
                            "delivery_type": delivery_type,
                            "tips_sent": len(all_tips),
                            "status": "success"
                        },
                        duration_ms=duration_ms
                    )
            else:
                structured_logger.error(
                    f"{delivery_type.capitalize()} delivery failed after retries",
                    context={
                        "trace_id": trace_id,
                        "delivery_type": delivery_type,
                        "duration_ms": duration_ms
                    }
                )
                
                if self.event_store:
                    self.event_store.add_event(
                        trace_id=trace_id,
                        event_type="delivery_failed",
                        component="SchedulerService",
                        message=f"{delivery_type.capitalize()} delivery failed after retries",
                        context={
                            "delivery_type": delivery_type,
                            "status": "failed"
                        },
                        duration_ms=duration_ms
                    )
                
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            structured_logger.error(
                f"Error during {delivery_type} delivery: {str(e)}",
                context={
                    "trace_id": trace_id,
                    "delivery_type": delivery_type,
                    "duration_ms": duration_ms
                },
                exception=e
            )
            
            if self.event_store:
                self.event_store.add_event(
                    trace_id=trace_id,
                    event_type="delivery_error",
                    component="SchedulerService",
                    message=f"Error during {delivery_type} delivery",
                    context={
                        "delivery_type": delivery_type,
                        "error_type": type(e).__name__,
                        "error_message": str(e)
                    },
                    duration_ms=duration_ms
                )
        
        finally:
            # Clear trace context
            clear_trace()

    def stop(self) -> None:
        """Stop the scheduler."""
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("Scheduler stopped")

    def _validate_time_format(self, time_str: str) -> None:
        """
        Validate time format (HH:MM).
        
        Args:
            time_str: Time string to validate
            
        Raises:
            ValueError: If format is invalid
        """
        try:
            parts = time_str.split(":")
            if len(parts) != 2:
                raise ValueError(f"Invalid time format: {time_str}. Use HH:MM")
            hour, minute = int(parts[0]), int(parts[1])
            if not (0 <= hour < 24 and 0 <= minute < 60):
                raise ValueError(f"Invalid time values: {time_str}")
        except (ValueError, AttributeError) as e:
            raise ValueError(f"Invalid time format: {e}")
