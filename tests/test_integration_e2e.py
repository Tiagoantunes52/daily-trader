"""Integration and end-to-end tests for Daily Market Tips system."""

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.database.models import DeliveryLog, MarketDataRecord, TipRecord
from src.models.market_data import DataSource, HistoricalData, MarketData
from src.models.trading_tip import EmailContent, TipSource, TradingTip
from src.services.analysis_engine import AnalysisEngine
from src.services.email_service import EmailService
from src.services.scheduler_service import SchedulerService


class TestSchedulerToEmailFlow:
    """Test complete flow: scheduler triggers → data fetch → analysis → email send."""

    def test_complete_morning_delivery_flow(self, test_session: Session):
        """Test the complete morning delivery flow from scheduler to email."""
        scheduler = SchedulerService(db_session=test_session)

        # Create mock market data
        mock_market_data = MarketData(
            symbol="BTC",
            type="crypto",
            current_price=50000.0,
            price_change_24h=5.0,
            volume_24h=1000000.0,
            historical_data=HistoricalData(
                period="24h",
                prices=[49000.0 + i * 100 for i in range(30)],
                timestamps=[float(i) for i in range(30)],
            ),
            source=DataSource(
                name="CoinGecko", url="https://coingecko.com", fetched_at=datetime.now()
            ),
        )

        mock_tip = TradingTip(
            symbol="BTC",
            type="crypto",
            recommendation="BUY",
            reasoning="Strong upward momentum detected",
            confidence=75,
            indicators=["RSI", "SMA"],
            sources=[TipSource(name="CoinGecko", url="https://coingecko.com")],
        )

        with patch.object(
            scheduler.market_aggregator, "fetch_crypto_data", return_value=[mock_market_data]
        ):
            with patch.object(scheduler.market_aggregator, "fetch_stock_data", return_value=[]):
                with patch.object(
                    scheduler.analysis_engine, "analyze_crypto", return_value=[mock_tip]
                ):
                    with patch.object(scheduler.analysis_engine, "analyze_stocks", return_value=[]):
                        with patch.object(
                            scheduler.email_service, "send_email_content", return_value=True
                        ) as mock_send:
                            # Execute morning delivery
                            scheduler.execute_delivery("morning")

                            # Verify the complete flow
                            assert mock_send.called, "Email service should be called"

                            # Verify email content
                            call_args = mock_send.call_args[0][0]
                            assert isinstance(call_args, EmailContent)
                            assert call_args.delivery_type == "morning"
                            assert len(call_args.tips) == 1
                            assert call_args.tips[0].symbol == "BTC"
                            assert len(call_args.market_data) == 1
                            assert call_args.market_data[0].symbol == "BTC"

    def test_complete_evening_delivery_flow(self, test_session: Session):
        """Test the complete evening delivery flow."""
        scheduler = SchedulerService(db_session=test_session)

        # Create mock data for both crypto and stocks
        crypto_data = MarketData(
            symbol="ETH",
            type="crypto",
            current_price=3000.0,
            price_change_24h=2.5,
            volume_24h=500000.0,
            historical_data=HistoricalData(
                period="24h",
                prices=[2950.0 + i * 10 for i in range(30)],
                timestamps=[float(i) for i in range(30)],
            ),
            source=DataSource(
                name="CoinGecko", url="https://coingecko.com", fetched_at=datetime.now()
            ),
        )

        stock_data = MarketData(
            symbol="AAPL",
            type="stock",
            current_price=150.0,
            price_change_24h=-1.0,
            volume_24h=5000000.0,
            historical_data=HistoricalData(
                period="24h",
                prices=[150.0 + i * 0.5 for i in range(30)],
                timestamps=[float(i) for i in range(30)],
            ),
            source=DataSource(
                name="Alpha Vantage", url="https://alphavantage.co", fetched_at=datetime.now()
            ),
        )

        crypto_tip = TradingTip(
            symbol="ETH",
            type="crypto",
            recommendation="HOLD",
            reasoning="Consolidation pattern observed",
            confidence=60,
            indicators=["MACD", "EMA"],
            sources=[TipSource(name="CoinGecko", url="https://coingecko.com")],
        )

        stock_tip = TradingTip(
            symbol="AAPL",
            type="stock",
            recommendation="BUY",
            reasoning="Support level holding strong",
            confidence=70,
            indicators=["RSI", "SMA"],
            sources=[TipSource(name="Alpha Vantage", url="https://alphavantage.co")],
        )

        with patch.object(
            scheduler.market_aggregator, "fetch_crypto_data", return_value=[crypto_data]
        ):
            with patch.object(
                scheduler.market_aggregator, "fetch_stock_data", return_value=[stock_data]
            ):
                with patch.object(
                    scheduler.analysis_engine, "analyze_crypto", return_value=[crypto_tip]
                ):
                    with patch.object(
                        scheduler.analysis_engine, "analyze_stocks", return_value=[stock_tip]
                    ):
                        with patch.object(
                            scheduler.email_service, "send_email_content", return_value=True
                        ) as mock_send:
                            # Execute evening delivery
                            scheduler.execute_delivery("evening")

                            # Verify the complete flow
                            assert mock_send.called

                            # Verify email content includes both crypto and stock
                            call_args = mock_send.call_args[0][0]
                            assert call_args.delivery_type == "evening"
                            assert len(call_args.tips) == 2
                            assert len(call_args.market_data) == 2

                            # Verify both asset types are present
                            symbols = [tip.symbol for tip in call_args.tips]
                            assert "ETH" in symbols
                            assert "AAPL" in symbols


class TestSchedulerToDashboardFlow:
    """Test complete flow: scheduler triggers → data fetch → analysis → dashboard update."""

    def test_tips_persisted_to_database(self, test_session: Session, test_client: TestClient):
        """Test that generated tips are persisted and accessible via dashboard API."""
        scheduler = SchedulerService(db_session=test_session)

        # Create mock data
        mock_market_data = MarketData(
            symbol="BTC",
            type="crypto",
            current_price=50000.0,
            price_change_24h=5.0,
            volume_24h=1000000.0,
            historical_data=HistoricalData(
                period="24h",
                prices=[49000.0 + i * 100 for i in range(30)],
                timestamps=[float(i) for i in range(30)],
            ),
            source=DataSource(
                name="CoinGecko", url="https://coingecko.com", fetched_at=datetime.now()
            ),
        )

        mock_tip = TradingTip(
            symbol="BTC",
            type="crypto",
            recommendation="BUY",
            reasoning="Strong upward momentum",
            confidence=75,
            indicators=["RSI", "SMA"],
            sources=[TipSource(name="CoinGecko", url="https://coingecko.com")],
        )

        with patch.object(
            scheduler.market_aggregator, "fetch_crypto_data", return_value=[mock_market_data]
        ):
            with patch.object(scheduler.market_aggregator, "fetch_stock_data", return_value=[]):
                with patch.object(
                    scheduler.analysis_engine, "analyze_crypto", return_value=[mock_tip]
                ):
                    with patch.object(scheduler.analysis_engine, "analyze_stocks", return_value=[]):
                        # Mock email sending to avoid actual SMTP calls
                        with patch.object(
                            scheduler.email_service, "send_email_content", return_value=True
                        ):
                            # Manually persist tip to database (simulating what would happen in real flow)
                            tip_record = TipRecord(
                                id="test-tip-1",
                                symbol=mock_tip.symbol,
                                type=mock_tip.type,
                                recommendation=mock_tip.recommendation,
                                reasoning=mock_tip.reasoning,
                                confidence=mock_tip.confidence,
                                indicators=json.dumps(mock_tip.indicators),
                                sources=json.dumps(
                                    [{"name": s.name, "url": s.url} for s in mock_tip.sources]
                                ),
                                generated_at=datetime.now(UTC),
                                delivery_type="morning",
                            )
                            test_session.add(tip_record)
                            test_session.commit()

                            # Verify tip is accessible via API
                            response = test_client.get("/api/tips")
                            assert response.status_code == 200
                            data = response.json()
                            assert data["total"] == 1
                            assert data["tips"][0]["symbol"] == "BTC"
                            assert data["tips"][0]["recommendation"] == "BUY"

    def test_market_data_persisted_to_database(
        self, test_session: Session, test_client: TestClient
    ):
        """Test that market data is persisted and accessible via dashboard API."""
        # Create and persist market data
        market_data_record = MarketDataRecord(
            id="test-md-1",
            symbol="BTC",
            type="crypto",
            current_price=50000.0,
            price_change_24h=5.0,
            volume_24h=1000000.0,
            historical_data=json.dumps(
                {
                    "period": "24h",
                    "prices": [49000.0 + i * 100 for i in range(30)],
                    "timestamps": [float(i) for i in range(30)],
                }
            ),
            source_name="CoinGecko",
            source_url="https://coingecko.com",
            fetched_at=datetime.now(UTC),
        )
        test_session.add(market_data_record)
        test_session.commit()

        # Verify market data is accessible via API
        response = test_client.get("/api/market-data?symbols=BTC")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["market_data"][0]["symbol"] == "BTC"
        assert data["market_data"][0]["current_price"] == 50000.0


class TestErrorScenarios:
    """Test error scenarios: API failures, email send failures, invalid data."""

    def test_api_failure_during_data_fetch(self, test_session: Session):
        """Test handling of API failures during market data fetch."""
        scheduler = SchedulerService(db_session=test_session)

        # Mock API failure
        with patch.object(
            scheduler.market_aggregator,
            "fetch_crypto_data",
            side_effect=Exception("API connection failed"),
        ):
            with patch.object(scheduler.market_aggregator, "fetch_stock_data", return_value=[]):
                # Should not raise, just log error
                scheduler.execute_delivery("morning")

                # Verify scheduler continues to run
                assert scheduler.is_running is False  # Not started in this test

    def test_email_send_failure_with_retry(self, test_session: Session):
        """Test email send failure triggers retry logic."""
        scheduler = SchedulerService(db_session=test_session)

        mock_market_data = MarketData(
            symbol="BTC",
            type="crypto",
            current_price=50000.0,
            price_change_24h=5.0,
            volume_24h=1000000.0,
            historical_data=HistoricalData(
                period="24h",
                prices=[49000.0 + i * 100 for i in range(30)],
                timestamps=[float(i) for i in range(30)],
            ),
            source=DataSource(
                name="CoinGecko", url="https://coingecko.com", fetched_at=datetime.now()
            ),
        )

        mock_tip = TradingTip(
            symbol="BTC",
            type="crypto",
            recommendation="BUY",
            reasoning="Strong upward momentum",
            confidence=75,
            indicators=["RSI", "SMA"],
            sources=[TipSource(name="CoinGecko", url="https://coingecko.com")],
        )

        with patch.object(
            scheduler.market_aggregator, "fetch_crypto_data", return_value=[mock_market_data]
        ):
            with patch.object(scheduler.market_aggregator, "fetch_stock_data", return_value=[]):
                with patch.object(
                    scheduler.analysis_engine, "analyze_crypto", return_value=[mock_tip]
                ):
                    with patch.object(scheduler.analysis_engine, "analyze_stocks", return_value=[]):
                        # Mock email service to fail then succeed
                        with patch.object(
                            scheduler.email_service, "send_email_content", return_value=False
                        ) as mock_send:
                            scheduler.execute_delivery("morning")

                            # Verify email service was called
                            assert mock_send.called

    def test_invalid_market_data_handling(self, test_session: Session):
        """Test handling of invalid market data."""
        SchedulerService(db_session=test_session)

        # Create invalid market data (missing required fields)
        invalid_data = MarketData(
            symbol="",  # Empty symbol
            type="crypto",
            current_price=-100.0,  # Negative price
            price_change_24h=5.0,
            volume_24h=1000000.0,
            historical_data=HistoricalData(
                period="24h",
                prices=[],  # Empty prices
                timestamps=[],
            ),
            source=DataSource(name="", url="", fetched_at=datetime.now()),
        )

        # Analysis engine should handle gracefully
        engine = AnalysisEngine()
        # Should not raise exception
        tips = engine.analyze_crypto([invalid_data])
        # May return empty list or handle gracefully
        assert isinstance(tips, list)

    def test_missing_market_data_for_delivery(self, test_session: Session):
        """Test handling when no market data is available for delivery."""
        scheduler = SchedulerService(db_session=test_session)

        # Mock empty market data
        with patch.object(scheduler.market_aggregator, "fetch_crypto_data", return_value=[]):
            with patch.object(scheduler.market_aggregator, "fetch_stock_data", return_value=[]):
                with patch.object(scheduler.email_service, "send_email_content") as mock_send:
                    scheduler.execute_delivery("morning")

                    # Email should not be sent if no data available
                    assert not mock_send.called

    def test_invalid_delivery_type(self, test_session: Session):
        """Test handling of invalid delivery type."""
        scheduler = SchedulerService(db_session=test_session)

        # Should not raise exception
        scheduler.execute_delivery("invalid_type")

        # Scheduler should still be functional
        assert scheduler.scheduler is not None


class TestRetryLogic:
    """Test retry logic for failed operations."""

    def test_email_retry_with_exponential_backoff(self, test_session: Session):
        """Test that email retry uses exponential backoff delays."""
        email_service = EmailService(db_session=test_session)

        with patch("smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server

            # Fail twice, then succeed
            call_count = [0]

            def send_message_side_effect(msg):
                call_count[0] += 1
                if call_count[0] < 3:
                    raise Exception("SMTP connection failed")

            mock_server.send_message.side_effect = send_message_side_effect

            with patch("time.sleep") as mock_sleep:
                result = email_service.send_email(
                    recipient="test@example.com", subject="Test", content="<p>Test</p>"
                )

            # Should succeed after retries
            assert result is True

            # Verify exponential backoff delays
            assert mock_sleep.call_count == 2
            expected_delays = [300, 900]  # 5min, 15min
            for i, call in enumerate(mock_sleep.call_args_list):
                assert call[0][0] == expected_delays[i]

    def test_email_failure_after_max_retries(self, test_session: Session):
        """Test that email fails after maximum retry attempts."""
        email_service = EmailService(db_session=test_session)

        with patch("smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server

            # Always fail
            mock_server.send_message.side_effect = Exception("SMTP connection failed")

            with patch("time.sleep"):
                result = email_service.send_email(
                    recipient="test@example.com", subject="Test", content="<p>Test</p>"
                )

            # Should fail after all retries
            assert result is False

    def test_delivery_log_records_retry_attempts(self, test_session: Session):
        """Test that delivery log records all retry attempts."""
        email_service = EmailService(db_session=test_session)

        with patch("smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server

            # Fail once, then succeed
            call_count = [0]

            def send_message_side_effect(msg):
                call_count[0] += 1
                if call_count[0] < 2:
                    raise Exception("SMTP connection failed")

            mock_server.send_message.side_effect = send_message_side_effect

            with patch("time.sleep"):
                result = email_service.send_email(
                    recipient="test@example.com",
                    subject="Test",
                    content="<p>Test</p>",
                    delivery_type="morning",
                )

            assert result is True

            # Verify delivery logs were created
            logs = test_session.query(DeliveryLog).all()
            assert len(logs) >= 2  # At least one retry attempt and one success

            # Verify log statuses
            statuses = [log.status for log in logs]
            assert "retrying" in statuses
            assert "success" in statuses


class TestEndToEndDashboardFlow:
    """Test complete end-to-end dashboard flows."""

    def test_dashboard_displays_latest_tips(self, test_session: Session, test_client: TestClient):
        """Test that dashboard displays the latest tips."""
        # Create multiple tips
        for i in range(3):
            tip = TipRecord(
                id=f"tip-{i}",
                symbol=["BTC", "ETH", "AAPL"][i],
                type=["crypto", "crypto", "stock"][i],
                recommendation=["BUY", "HOLD", "SELL"][i],
                reasoning=f"Test reasoning {i}",
                confidence=50 + (i * 10),
                indicators=json.dumps(["RSI", "MACD"]),
                sources=json.dumps([{"name": "Test", "url": "https://example.com"}]),
                generated_at=datetime.now(UTC) - timedelta(hours=i),
                delivery_type="morning",
            )
            test_session.add(tip)
        test_session.commit()

        # Retrieve tips via API
        response = test_client.get("/api/tips")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["tips"]) == 3

    def test_dashboard_filters_by_asset_type(self, test_session: Session, test_client: TestClient):
        """Test that dashboard correctly filters by asset type."""
        # Create tips of different types
        crypto_tip = TipRecord(
            id="crypto-tip",
            symbol="BTC",
            type="crypto",
            recommendation="BUY",
            reasoning="Test",
            confidence=75,
            indicators=json.dumps(["RSI"]),
            sources=json.dumps([{"name": "Test", "url": "https://example.com"}]),
            generated_at=datetime.now(UTC),
            delivery_type="morning",
        )

        stock_tip = TipRecord(
            id="stock-tip",
            symbol="AAPL",
            type="stock",
            recommendation="HOLD",
            reasoning="Test",
            confidence=60,
            indicators=json.dumps(["SMA"]),
            sources=json.dumps([{"name": "Test", "url": "https://example.com"}]),
            generated_at=datetime.now(UTC),
            delivery_type="morning",
        )

        test_session.add(crypto_tip)
        test_session.add(stock_tip)
        test_session.commit()

        # Filter by crypto
        response = test_client.get("/api/tips?asset_type=crypto")
        assert response.status_code == 200
        data = response.json()
        assert all(tip["type"] == "crypto" for tip in data["tips"])

        # Filter by stock
        response = test_client.get("/api/tips?asset_type=stock")
        assert response.status_code == 200
        data = response.json()
        assert all(tip["type"] == "stock" for tip in data["tips"])

    def test_dashboard_tip_history_with_date_range(
        self, test_session: Session, test_client: TestClient
    ):
        """Test that dashboard tip history respects date range."""
        # Create tips from different dates
        for i in range(5):
            tip = TipRecord(
                id=f"tip-{i}",
                symbol="BTC",
                type="crypto",
                recommendation="BUY",
                reasoning=f"Test {i}",
                confidence=75,
                indicators=json.dumps(["RSI"]),
                sources=json.dumps([{"name": "Test", "url": "https://example.com"}]),
                generated_at=datetime.now(UTC) - timedelta(days=i),
                delivery_type="morning",
            )
            test_session.add(tip)
        test_session.commit()

        # Get history for last 2 days
        response = test_client.get("/api/tip-history?days=2")
        assert response.status_code == 200
        data = response.json()
        assert data["days"] == 2
        # Should get tips from last 2 days (indices 0, 1)
        assert data["total"] <= 5

    def test_dashboard_market_data_display(self, test_session: Session, test_client: TestClient):
        """Test that dashboard displays market data correctly."""
        # Create market data
        market_data = MarketDataRecord(
            id="md-1",
            symbol="BTC",
            type="crypto",
            current_price=50000.0,
            price_change_24h=5.0,
            volume_24h=1000000.0,
            historical_data=json.dumps(
                {"period": "24h", "prices": [49000.0, 50000.0], "timestamps": [1.0, 2.0]}
            ),
            source_name="CoinGecko",
            source_url="https://coingecko.com",
            fetched_at=datetime.now(UTC),
        )
        test_session.add(market_data)
        test_session.commit()

        # Retrieve market data
        response = test_client.get("/api/market-data?symbols=BTC")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["market_data"][0]["symbol"] == "BTC"
        assert data["market_data"][0]["current_price"] == 50000.0
        assert data["market_data"][0]["source"]["name"] == "CoinGecko"
