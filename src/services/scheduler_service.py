"""Scheduler service for managing timed email deliveries."""

import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session
from src.services.email_service import EmailService
from src.services.market_data_aggregator import MarketDataAggregator
from src.services.analysis_engine import AnalysisEngine
from src.models.trading_tip import EmailContent
from src.database.db import SessionLocal

logger = logging.getLogger(__name__)


class SchedulerService:
    """Manages scheduled email deliveries at configured times."""

    def __init__(self, db_session: Session = None):
        """
        Initialize scheduler service.
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.scheduler = BackgroundScheduler()
        self.db_session = db_session
        self.email_service = EmailService(db_session)
        self.market_aggregator = MarketDataAggregator()
        self.analysis_engine = AnalysisEngine()
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
        if delivery_type not in ["morning", "evening"]:
            logger.error(f"Invalid delivery type: {delivery_type}")
            return
        
        try:
            logger.info(f"Starting {delivery_type} delivery execution")
            
            # Fetch market data
            logger.debug("Fetching market data...")
            crypto_data = self.market_aggregator.fetch_crypto_data(["bitcoin", "ethereum"])
            stock_data = self.market_aggregator.fetch_stock_data(["AAPL", "GOOGL"])
            all_market_data = crypto_data + stock_data
            
            if not all_market_data:
                logger.warning(f"No market data available for {delivery_type} delivery")
                return
            
            # Analyze market data
            logger.debug("Analyzing market data...")
            crypto_tips = self.analysis_engine.analyze_crypto(crypto_data)
            stock_tips = self.analysis_engine.analyze_stocks(stock_data)
            all_tips = crypto_tips + stock_tips
            
            if not all_tips:
                logger.warning(f"No tips generated for {delivery_type} delivery")
                return
            
            # Format email content
            logger.debug("Formatting email content...")
            email_content = EmailContent(
                recipient="user@example.com",  # This should come from user config
                subject=f"{delivery_type.capitalize()} Market Tips - {datetime.now().strftime('%Y-%m-%d')}",
                delivery_type=delivery_type,
                tips=all_tips,
                market_data=all_market_data,
                generated_at=datetime.now()
            )
            
            # Send email
            logger.debug("Sending email...")
            success = self.email_service.send_email_content(email_content)
            
            if success:
                logger.info(f"{delivery_type.capitalize()} delivery completed successfully")
            else:
                logger.error(f"{delivery_type.capitalize()} delivery failed after retries")
                
        except Exception as e:
            logger.error(f"Error during {delivery_type} delivery: {str(e)}", exc_info=True)

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
