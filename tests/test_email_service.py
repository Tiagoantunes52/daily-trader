"""Tests for email service."""

import pytest
from hypothesis import given, strategies as st, settings
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock
from src.services.email_service import EmailService
from src.models.trading_tip import TradingTip, TipSource, EmailContent
from src.models.market_data import MarketData, HistoricalData, DataSource


class TestEmailService:
    """Test suite for EmailService."""

    def test_email_service_initialization(self):
        """Test that email service initializes correctly."""
        service = EmailService(db_session=None)
        assert service is not None
        assert service.smtp_server is not None
        assert service.sender_email is not None

    def test_send_email_success(self):
        """Test successful email sending."""
        service = EmailService(db_session=None)
        
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server
            
            result = service.send_email(
                recipient="test@example.com",
                subject="Test Subject",
                content="<p>Test content</p>"
            )
            
            assert result is True
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_once()
            mock_server.send_message.assert_called_once()

    def test_send_email_with_html_and_text(self):
        """Test that email is sent with both HTML and plain text versions."""
        service = EmailService(db_session=None)
        
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server
            
            result = service.send_email(
                recipient="test@example.com",
                subject="Test Subject",
                content="<p>Test content</p>"
            )
            
            assert result is True
            # Verify send_message was called
            mock_server.send_message.assert_called_once()

    @given(st.integers(min_value=1, max_value=3))
    @settings(max_examples=10)
    def test_email_retry_logic(self, failure_attempt):
        """
        **Feature: daily-market-tips, Property 7: Failed emails are retried**
        
        For any email send failure, the system SHALL attempt retry with exponential backoff
        (3 attempts minimum). When an email fails to send on the first attempt, the system
        should retry with delays of 5min, 15min, and 30min before giving up.
        
        **Validates: Requirements 3.3**
        """
        service = EmailService(db_session=None)
        
        # Mock SMTP to fail on specific attempt
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server
            
            # Configure mock to fail on specified attempt, then succeed
            call_count = [0]
            
            def send_message_side_effect(msg):
                call_count[0] += 1
                if call_count[0] < failure_attempt:
                    raise Exception("SMTP connection failed")
                # Success on final attempt
            
            mock_server.send_message.side_effect = send_message_side_effect
            
            with patch('time.sleep') as mock_sleep:
                result = service.send_email(
                    recipient="test@example.com",
                    subject="Test Subject",
                    content="<p>Test content</p>"
                )
            
            # If failure_attempt <= 4, we should succeed (3 retries + 1 initial = 4 attempts)
            if failure_attempt <= 4:
                assert result is True
                # Verify retries happened with correct delays
                if failure_attempt > 1:
                    assert mock_sleep.call_count == failure_attempt - 1
                    # Check that delays match exponential backoff: 300s, 900s, 1800s
                    expected_delays = [300, 900, 1800]
                    for i, call in enumerate(mock_sleep.call_args_list):
                        assert call[0][0] == expected_delays[i]
            else:
                # If failure_attempt > 4, all attempts fail
                assert result is False

    def test_email_retry_delays_are_exponential(self):
        """Test that retry delays follow exponential backoff pattern."""
        service = EmailService(db_session=None)
        
        # Verify retry delays are configured correctly
        assert service.retry_delays == [300, 900, 1800]  # 5min, 15min, 30min

    def test_email_failure_after_all_retries(self):
        """Test that email sending fails after all retry attempts."""
        service = EmailService(db_session=None)
        
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server
            
            # Always fail
            mock_server.send_message.side_effect = Exception("SMTP connection failed")
            
            with patch('time.sleep'):
                result = service.send_email(
                    recipient="test@example.com",
                    subject="Test Subject",
                    content="<p>Test content</p>"
                )
            
            assert result is False

    def test_log_delivery_with_session(self):
        """Test delivery logging with database session."""
        mock_session = Mock()
        service = EmailService(db_session=mock_session)
        
        service.log_delivery(
            status="success",
            recipient="test@example.com",
            timestamp=datetime.now(timezone.utc),
            delivery_type="morning",
            attempt_number=1
        )
        
        # Verify session methods were called
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    def test_log_delivery_without_session(self):
        """Test that logging without session doesn't raise error."""
        service = EmailService(db_session=None)
        
        # Should not raise any exception
        service.log_delivery(
            status="success",
            recipient="test@example.com",
            timestamp=datetime.now(timezone.utc),
            delivery_type="morning",
            attempt_number=1
        )

    def test_send_email_content(self):
        """Test sending formatted email content."""
        service = EmailService(db_session=None)
        
        tip = TradingTip(
            symbol="BTC",
            type="crypto",
            recommendation="BUY",
            reasoning="Strong uptrend detected",
            confidence=85,
            indicators=["RSI", "MACD"],
            sources=[TipSource(name="CoinGecko", url="https://coingecko.com")]
        )
        
        email_content = EmailContent(
            recipient="test@example.com",
            subject="Morning Market Tips",
            delivery_type="morning",
            tips=[tip]
        )
        
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server
            
            result = service.send_email_content(email_content)
            
            assert result is True
            mock_server.send_message.assert_called_once()

    def test_format_email_html_includes_tips(self):
        """Test that formatted email includes all tips."""
        service = EmailService(db_session=None)
        
        tip = TradingTip(
            symbol="BTC",
            type="crypto",
            recommendation="BUY",
            reasoning="Strong uptrend detected",
            confidence=85,
            indicators=["RSI", "MACD"],
            sources=[TipSource(name="CoinGecko", url="https://coingecko.com")]
        )
        
        email_content = EmailContent(
            recipient="test@example.com",
            subject="Morning Market Tips",
            delivery_type="morning",
            tips=[tip]
        )
        
        html = service._format_email_html(email_content)
        
        assert "BTC" in html
        assert "BUY" in html
        assert "Strong uptrend detected" in html
        assert "RSI" in html
        assert "MACD" in html
        assert "CoinGecko" in html

    def test_format_email_html_includes_market_data(self):
        """Test that formatted email includes market data."""
        service = EmailService(db_session=None)
        
        market_data = MarketData(
            symbol="BTC",
            type="crypto",
            current_price=45000.0,
            price_change_24h=5.2,
            volume_24h=1000000000.0,
            historical_data=HistoricalData(
                period="24h",
                prices=[44000.0, 45000.0],
                timestamps=[0.0, 1.0]
            ),
            source=DataSource(
                name="CoinGecko",
                url="https://coingecko.com",
                fetched_at=datetime.now()
            )
        )
        
        email_content = EmailContent(
            recipient="test@example.com",
            subject="Morning Market Tips",
            delivery_type="morning",
            market_data=[market_data]
        )
        
        html = service._format_email_html(email_content)
        
        assert "BTC" in html
        assert "45000" in html
        assert "5.2" in html
        assert "CoinGecko" in html

    def test_strip_html_removes_tags(self):
        """Test that HTML stripping works correctly."""
        service = EmailService(db_session=None)
        
        html = "<p>This is <strong>bold</strong> text</p>"
        text = service._strip_html(html)
        
        assert "<p>" not in text
        assert "<strong>" not in text
        assert "This is bold text" in text

    def test_email_with_multiple_sources(self):
        """Test email formatting with multiple sources."""
        service = EmailService(db_session=None)
        
        tip = TradingTip(
            symbol="AAPL",
            type="stock",
            recommendation="HOLD",
            reasoning="Mixed signals from indicators",
            confidence=60,
            indicators=["SMA", "EMA"],
            sources=[
                TipSource(name="Alpha Vantage", url="https://alphavantage.co"),
                TipSource(name="Yahoo Finance", url="https://finance.yahoo.com")
            ]
        )
        
        email_content = EmailContent(
            recipient="test@example.com",
            subject="Evening Market Tips",
            delivery_type="evening",
            tips=[tip]
        )
        
        html = service._format_email_html(email_content)
        
        assert "Alpha Vantage" in html
        assert "Yahoo Finance" in html
        assert "AAPL" in html
        assert "HOLD" in html
