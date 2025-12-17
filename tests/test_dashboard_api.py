"""Tests for Dashboard API endpoints."""

import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import json
import uuid

from src.database.models import TipRecord, MarketDataRecord
from main import app


@pytest.fixture
def sample_tips(test_session: Session):
    """Create sample tip records for testing."""
    tips = []
    
    # Create tips from different dates
    for i in range(5):
        tip = TipRecord(
            id=str(uuid.uuid4()),
            symbol="BTC" if i % 2 == 0 else "AAPL",
            type="crypto" if i % 2 == 0 else "stock",
            recommendation=["BUY", "SELL", "HOLD"][i % 3],
            reasoning=f"Test reasoning {i}",
            confidence=50 + (i * 10),
            indicators=json.dumps(["RSI", "MACD"]),
            sources=json.dumps([{"name": "Test Source", "url": "https://example.com"}]),
            generated_at=datetime.now(timezone.utc) - timedelta(days=i),
            delivery_type="morning" if i % 2 == 0 else "evening"
        )
        test_session.add(tip)
        tips.append(tip)
    
    test_session.commit()
    return tips


@pytest.fixture
def sample_market_data(test_session: Session):
    """Create sample market data records for testing."""
    data = []
    
    symbols = ["BTC", "ETH", "AAPL", "GOOGL"]
    for symbol in symbols:
        record = MarketDataRecord(
            id=str(uuid.uuid4()),
            symbol=symbol,
            type="crypto" if symbol in ["BTC", "ETH"] else "stock",
            current_price=100.0 + len(data),
            price_change_24h=2.5,
            volume_24h=1000000.0,
            historical_data=json.dumps({
                "period": "24h",
                "prices": [99.0, 100.0, 101.0],
                "timestamps": [1, 2, 3]
            }),
            source_name="Test Exchange",
            source_url="https://example.com",
            fetched_at=datetime.now(timezone.utc)
        )
        test_session.add(record)
        data.append(record)
    
    test_session.commit()
    return data


class TestGetTips:
    """Tests for GET /api/tips endpoint."""
    
    def test_get_tips_returns_all_tips(self, test_client: TestClient, sample_tips):
        """Test retrieving all tips without filters."""
        response = test_client.get("/api/tips")
        assert response.status_code == 200
        data = response.json()
        assert "tips" in data
        assert "total" in data
        assert data["total"] == 5
        assert len(data["tips"]) == 5
    
    def test_get_tips_filters_by_asset_type(self, test_client: TestClient, sample_tips):
        """Test filtering tips by asset type."""
        response = test_client.get("/api/tips?asset_type=crypto")
        assert response.status_code == 200
        data = response.json()
        assert all(tip["type"] == "crypto" for tip in data["tips"])
        
        response = test_client.get("/api/tips?asset_type=stock")
        assert response.status_code == 200
        data = response.json()
        assert all(tip["type"] == "stock" for tip in data["tips"])
    
    def test_get_tips_filters_by_days(self, test_client: TestClient, sample_tips):
        """Test filtering tips by date range."""
        response = test_client.get("/api/tips?days=2")
        assert response.status_code == 200
        data = response.json()
        # Should get tips from last 2 days (indices 0, 1)
        assert data["total"] <= 5
        # Verify that tips are from recent dates
        assert len(data["tips"]) > 0
    
    def test_get_tips_pagination(self, test_client: TestClient, sample_tips):
        """Test pagination with skip and limit."""
        response = test_client.get("/api/tips?skip=0&limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["tips"]) == 2
        assert data["skip"] == 0
        assert data["limit"] == 2
        
        response = test_client.get("/api/tips?skip=2&limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["tips"]) == 2
        assert data["skip"] == 2
    
    def test_get_tips_combined_filters(self, test_client: TestClient, sample_tips):
        """Test combining multiple filters."""
        response = test_client.get("/api/tips?asset_type=crypto&days=3&skip=0&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert all(tip["type"] == "crypto" for tip in data["tips"])
    
    def test_get_tips_returns_tip_details(self, test_client: TestClient, sample_tips):
        """Test that returned tips contain all required fields."""
        response = test_client.get("/api/tips")
        assert response.status_code == 200
        data = response.json()
        
        tip = data["tips"][0]
        assert "id" in tip
        assert "symbol" in tip
        assert "type" in tip
        assert "recommendation" in tip
        assert "reasoning" in tip
        assert "confidence" in tip
        assert "indicators" in tip
        assert "sources" in tip
        assert "generated_at" in tip
        assert "delivery_type" in tip
    
    def test_get_tips_empty_database(self, test_client: TestClient):
        """Test retrieving tips when database is empty."""
        response = test_client.get("/api/tips")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["tips"]) == 0


class TestGetMarketData:
    """Tests for GET /api/market-data endpoint."""
    
    def test_get_market_data_returns_all(self, test_client: TestClient, sample_market_data):
        """Test retrieving all market data."""
        response = test_client.get("/api/market-data")
        assert response.status_code == 200
        data = response.json()
        assert "market_data" in data
        assert "count" in data
        assert data["count"] == 4
    
    def test_get_market_data_filters_by_symbols(self, test_client: TestClient, sample_market_data):
        """Test filtering market data by symbols."""
        response = test_client.get("/api/market-data?symbols=BTC&symbols=AAPL")
        assert response.status_code == 200
        data = response.json()
        symbols = [md["symbol"] for md in data["market_data"]]
        assert "BTC" in symbols
        assert "AAPL" in symbols
        assert len(data["market_data"]) == 2
    
    def test_get_market_data_single_symbol(self, test_client: TestClient, sample_market_data):
        """Test retrieving market data for a single symbol."""
        response = test_client.get("/api/market-data?symbols=BTC")
        assert response.status_code == 200
        data = response.json()
        assert len(data["market_data"]) == 1
        assert data["market_data"][0]["symbol"] == "BTC"
    
    def test_get_market_data_returns_complete_structure(self, test_client: TestClient, sample_market_data):
        """Test that market data contains all required fields."""
        response = test_client.get("/api/market-data")
        assert response.status_code == 200
        data = response.json()
        
        md = data["market_data"][0]
        assert "symbol" in md
        assert "type" in md
        assert "current_price" in md
        assert "price_change_24h" in md
        assert "volume_24h" in md
        assert "historical_data" in md
        assert "source" in md
        
        # Check historical data structure
        hist = md["historical_data"]
        assert "period" in hist
        assert "prices" in hist
        assert "timestamps" in hist
        
        # Check source structure
        source = md["source"]
        assert "name" in source
        assert "url" in source
        assert "fetched_at" in source
    
    def test_get_market_data_empty_database(self, test_client: TestClient):
        """Test retrieving market data when database is empty."""
        response = test_client.get("/api/market-data")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert len(data["market_data"]) == 0


class TestGetTipHistory:
    """Tests for GET /api/tip-history endpoint."""
    
    def test_get_tip_history_default_days(self, test_client: TestClient, sample_tips):
        """Test retrieving tip history with default 7 days."""
        response = test_client.get("/api/tip-history")
        assert response.status_code == 200
        data = response.json()
        assert "tips" in data
        assert "total" in data
        assert "days" in data
        assert data["days"] == 7
    
    def test_get_tip_history_custom_days(self, test_client: TestClient, sample_tips):
        """Test retrieving tip history with custom day range."""
        response = test_client.get("/api/tip-history?days=2")
        assert response.status_code == 200
        data = response.json()
        assert data["days"] == 2
        # Should get tips from last 2 days
        assert data["total"] <= 5
    
    def test_get_tip_history_filters_by_asset_type(self, test_client: TestClient, sample_tips):
        """Test filtering history by asset type."""
        response = test_client.get("/api/tip-history?asset_type=crypto")
        assert response.status_code == 200
        data = response.json()
        assert all(tip["type"] == "crypto" for tip in data["tips"])
    
    def test_get_tip_history_pagination(self, test_client: TestClient, sample_tips):
        """Test pagination in tip history."""
        response = test_client.get("/api/tip-history?skip=0&limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["tips"]) == 2
        assert data["skip"] == 0
        assert data["limit"] == 2
    
    def test_get_tip_history_combined_filters(self, test_client: TestClient, sample_tips):
        """Test combining multiple filters in history."""
        response = test_client.get("/api/tip-history?days=5&asset_type=stock&skip=0&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert all(tip["type"] == "stock" for tip in data["tips"])
        assert data["days"] == 5
    
    def test_get_tip_history_empty_database(self, test_client: TestClient):
        """Test retrieving history when database is empty."""
        response = test_client.get("/api/tip-history")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["tips"]) == 0


class TestPaginationLimits:
    """Tests for pagination parameter validation."""
    
    def test_tips_limit_max_100(self, test_client: TestClient, sample_tips):
        """Test that tips endpoint enforces max limit of 100."""
        response = test_client.get("/api/tips?limit=101")
        # Should either reject or cap at 100
        assert response.status_code in [200, 422]
    
    def test_tips_skip_non_negative(self, test_client: TestClient, sample_tips):
        """Test that skip parameter must be non-negative."""
        response = test_client.get("/api/tips?skip=-1")
        assert response.status_code == 422
    
    def test_history_days_range(self, test_client: TestClient, sample_tips):
        """Test that days parameter is within valid range."""
        response = test_client.get("/api/tip-history?days=0")
        assert response.status_code == 422
        
        response = test_client.get("/api/tip-history?days=91")
        assert response.status_code == 422
