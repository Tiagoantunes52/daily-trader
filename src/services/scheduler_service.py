"""Scheduler service for managing timed email deliveries."""

import logging
import time
from datetime import datetime, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session
from src.services.email_service import EmailService
from src.services.market_data_aggregator import MarketDataAggregator
from src.services.analysis_engine import AnalysisEngine
from src.models.trading_tip import EmailContent
from src.database.models import TipRecord, MarketDataRecord
from src.utils.logger import StructuredLogger
from src.utils.trace_context import create_trace, clear_trace
from src.utils.event_store import EventStore
import uuid
import json

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

    def _get_symbols_needing_update(self, symbols: list[str], asset_type: str, cache_hours: int = 1) -> list[str]:
        """
        Check which symbols need updating based on cache age.
        
        Args:
            symbols: List of symbols to check
            asset_type: Type of asset ("crypto" or "stock")
            cache_hours: How many hours to consider as cached
            
        Returns:
            List of symbols that need updating
        """
        if not self.db_session:
            return symbols
        
        from datetime import timedelta
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=cache_hours)
        
        try:
            # Find symbols with recent tips
            recent_tips = self.db_session.query(TipRecord).filter(
                TipRecord.type == asset_type,
                TipRecord.symbol.in_(symbols),
                TipRecord.generated_at >= cutoff_time
            ).all()
            
            recent_symbols = {tip.symbol for tip in recent_tips}
            symbols_to_fetch = [s for s in symbols if s not in recent_symbols]
            
            if symbols_to_fetch:
                structured_logger.debug(
                    f"Cache check: {len(symbols)} symbols checked, {len(symbols_to_fetch)} need updating",
                    context={
                        "asset_type": asset_type,
                        "cached_symbols": list(recent_symbols),
                        "symbols_to_fetch": symbols_to_fetch
                    }
                )
            else:
                structured_logger.debug(
                    f"All {len(symbols)} symbols have recent tips, skipping fetch",
                    context={"asset_type": asset_type}
                )
            
            return symbols_to_fetch
        except Exception as e:
            structured_logger.warning(
                f"Error checking cache, fetching all symbols: {str(e)}",
                context={"asset_type": asset_type}
            )
            return symbols

    def execute_delivery(self, delivery_type: str) -> None:
        """
        Execute the email sending process.
        
        Args:
            delivery_type: Either "morning", "evening", or "dashboard" (for on-demand generation)
        """
        # Create a new trace for this delivery operation
        trace_id = create_trace()
        start_time = time.time()
        
        if delivery_type not in ["morning", "evening", "dashboard"]:
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
            
            # Check cache and only fetch symbols that need updating
            crypto_symbols = ["bitcoin", "ethereum", "near", "solana", "tron"]
            stock_symbols = ["AAPL", "GOOGL"]
            
            crypto_to_fetch = self._get_symbols_needing_update(crypto_symbols, "crypto")
            stock_to_fetch = self._get_symbols_needing_update(stock_symbols, "stock")
            
            # Fetch market data
            structured_logger.debug(
                "Fetching market data...",
                context={
                    "trace_id": trace_id,
                    "delivery_type": delivery_type,
                    "crypto_to_fetch": crypto_to_fetch,
                    "stock_to_fetch": stock_to_fetch
                }
            )
            
            crypto_data = self.market_aggregator.fetch_crypto_data(crypto_to_fetch) if crypto_to_fetch else []
            stock_data = self.market_aggregator.fetch_stock_data(stock_to_fetch) if stock_to_fetch else []
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
            
            # Store tips and market data in database
            self._store_tips(all_tips, delivery_type)
            self._store_market_data(all_market_data)
            
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
            
            # Send email (skip for dashboard requests)
            if delivery_type != "dashboard":
                structured_logger.debug(
                    "Sending email...",
                    context={
                        "trace_id": trace_id,
                        "delivery_type": delivery_type,
                        "recipient": email_content.recipient
                    }
                )
                
                success = self.email_service.send_email_content(email_content)
            else:
                structured_logger.debug(
                    "Skipping email send for dashboard request",
                    context={
                        "trace_id": trace_id,
                        "delivery_type": delivery_type
                    }
                )
                success = True
            
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

    def _store_tips(self, tips: list, delivery_type: str) -> None:
        """
        Store generated tips in the database.
        
        Args:
            tips: List of TradingTip objects
            delivery_type: Type of delivery (morning, evening, dashboard)
        """
        if not self.db_session or not tips:
            return
        
        try:
            for tip in tips:
                tip_record = TipRecord(
                    id=str(uuid.uuid4()),
                    symbol=tip.symbol,
                    type=tip.type,
                    recommendation=tip.recommendation,
                    reasoning=tip.reasoning,
                    confidence=tip.confidence,
                    indicators=json.dumps(tip.indicators),
                    sources=json.dumps([{"name": s.name, "url": s.url} for s in tip.sources]),
                    delivery_type=delivery_type
                )
                self.db_session.add(tip_record)
            
            self.db_session.commit()
            structured_logger.debug(
                f"Stored {len(tips)} tips in database",
                context={"delivery_type": delivery_type, "tips_count": len(tips)}
            )
        except Exception as e:
            structured_logger.error(
                f"Error storing tips in database: {str(e)}",
                exception=e
            )
            self.db_session.rollback()

    def _store_market_data(self, market_data: list) -> None:
        """
        Store market data in the database.
        
        Args:
            market_data: List of MarketData objects
        """
        if not self.db_session or not market_data:
            return
        
        try:
            for data in market_data:
                market_record = MarketDataRecord(
                    id=str(uuid.uuid4()),
                    symbol=data.symbol,
                    type=data.type,
                    current_price=data.current_price,
                    price_change_24h=data.price_change_24h,
                    volume_24h=data.volume_24h,
                    historical_data=json.dumps({
                        "period": data.historical_data.period,
                        "prices": data.historical_data.prices,
                        "timestamps": data.historical_data.timestamps
                    }),
                    source_name=data.source.name,
                    source_url=data.source.url
                )
                self.db_session.add(market_record)
            
            self.db_session.commit()
            structured_logger.debug(
                f"Stored {len(market_data)} market data records in database",
                context={"market_data_count": len(market_data)}
            )
        except Exception as e:
            structured_logger.error(
                f"Error storing market data in database: {str(e)}",
                exception=e
            )
            self.db_session.rollback()

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
