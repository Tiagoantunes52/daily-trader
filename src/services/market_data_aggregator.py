"""Market data aggregator service for fetching data from multiple sources."""

from typing import Optional
from src.models.market_data import MarketData, HistoricalData, DataSource
from datetime import datetime
import requests
from src.utils.logger import StructuredLogger
from src.utils.trace_context import get_current_trace


class MarketDataAggregator:
    """Aggregates market data from multiple sources."""

    def __init__(self):
        """Initialize the aggregator with API endpoints."""
        self.coingecko_base_url = "https://api.coingecko.com/api/v3"
        self.alphavantage_base_url = "https://www.alphavantage.co/query"
        self.alphavantage_api_key = None  # Can be set via config
        self.logger = StructuredLogger("MarketDataAggregator")

    def fetch_crypto_data(self, symbols: list[str]) -> list[MarketData]:
        """
        Fetch cryptocurrency data from available sources.
        
        Args:
            symbols: List of crypto symbols to fetch (e.g., ["bitcoin", "ethereum"])
            
        Returns:
            List of MarketData objects with source attribution
        """
        market_data_list = []
        trace_id = get_current_trace()
        
        for symbol in symbols:
            try:
                # Log fetch start
                self.logger.info(
                    "Starting cryptocurrency data fetch",
                    context={
                        "trace_id": trace_id,
                        "source": "CoinGecko",
                        "symbol": symbol,
                        "type": "crypto"
                    }
                )
                
                # Fetch current data from CoinGecko
                url = f"{self.coingecko_base_url}/simple/price"
                params = {
                    "ids": symbol.lower(),
                    "vs_currencies": "usd",
                    "include_market_cap": "true",
                    "include_24hr_vol": "true",
                    "include_24hr_change": "true"
                }
                
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                if symbol.lower() not in data:
                    self.logger.warning(
                        "Cryptocurrency symbol not found in response",
                        context={
                            "trace_id": trace_id,
                            "source": "CoinGecko",
                            "symbol": symbol,
                            "result": "not_found"
                        }
                    )
                    continue
                
                crypto_data = data[symbol.lower()]
                
                # Fetch historical data
                historical_data = self._fetch_crypto_historical(symbol)
                
                market_data = MarketData(
                    symbol=symbol,
                    type="crypto",
                    current_price=crypto_data.get("usd", 0),
                    price_change_24h=crypto_data.get("usd_24h_change", 0),
                    volume_24h=crypto_data.get("usd_24h_vol", 0),
                    historical_data=historical_data,
                    source=DataSource(
                        name="CoinGecko",
                        url="https://www.coingecko.com",
                        fetched_at=datetime.now()
                    )
                )
                market_data_list.append(market_data)
                
                # Log successful fetch
                self.logger.info(
                    "Successfully fetched cryptocurrency data",
                    context={
                        "trace_id": trace_id,
                        "source": "CoinGecko",
                        "symbol": symbol,
                        "result": "success",
                        "current_price": market_data.current_price,
                        "price_change_24h": market_data.price_change_24h
                    }
                )
            except Exception as e:
                # Log error with full context
                self.logger.error(
                    f"Error fetching cryptocurrency data for {symbol}",
                    context={
                        "trace_id": trace_id,
                        "source": "CoinGecko",
                        "symbol": symbol,
                        "result": "failed"
                    },
                    exception=e
                )
                continue
        
        return market_data_list

    def fetch_stock_data(self, symbols: list[str]) -> list[MarketData]:
        """
        Fetch stock data from available sources.
        
        Args:
            symbols: List of stock symbols to fetch (e.g., ["AAPL", "GOOGL"])
            
        Returns:
            List of MarketData objects with source attribution
        """
        market_data_list = []
        trace_id = get_current_trace()
        
        for symbol in symbols:
            try:
                # Log fetch start
                self.logger.info(
                    "Starting stock data fetch",
                    context={
                        "trace_id": trace_id,
                        "source": "Alpha Vantage",
                        "symbol": symbol,
                        "type": "stock"
                    }
                )
                
                # Fetch current data from Alpha Vantage
                params = {
                    "function": "GLOBAL_QUOTE",
                    "symbol": symbol,
                    "apikey": self.alphavantage_api_key or "demo"
                }
                
                response = requests.get(self.alphavantage_base_url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                if "Global Quote" not in data or not data["Global Quote"]:
                    self.logger.warning(
                        "Stock symbol not found in response",
                        context={
                            "trace_id": trace_id,
                            "source": "Alpha Vantage",
                            "symbol": symbol,
                            "result": "not_found"
                        }
                    )
                    continue
                
                quote = data["Global Quote"]
                
                # Fetch historical data
                historical_data = self._fetch_stock_historical(symbol)
                
                market_data = MarketData(
                    symbol=symbol,
                    type="stock",
                    current_price=float(quote.get("05. price", 0)),
                    price_change_24h=float(quote.get("09. change", 0)),
                    volume_24h=float(quote.get("06. volume", 0)),
                    historical_data=historical_data,
                    source=DataSource(
                        name="Alpha Vantage",
                        url="https://www.alphavantage.co",
                        fetched_at=datetime.now()
                    )
                )
                market_data_list.append(market_data)
                
                # Log successful fetch
                self.logger.info(
                    "Successfully fetched stock data",
                    context={
                        "trace_id": trace_id,
                        "source": "Alpha Vantage",
                        "symbol": symbol,
                        "result": "success",
                        "current_price": market_data.current_price,
                        "price_change_24h": market_data.price_change_24h
                    }
                )
            except Exception as e:
                # Log error with full context
                self.logger.error(
                    f"Error fetching stock data for {symbol}",
                    context={
                        "trace_id": trace_id,
                        "source": "Alpha Vantage",
                        "symbol": symbol,
                        "result": "failed"
                    },
                    exception=e
                )
                continue
        
        return market_data_list

    def get_historical_data(self, symbol: str, period: str) -> Optional[HistoricalData]:
        """
        Retrieve historical price data for a symbol.
        
        Args:
            symbol: The symbol to fetch history for
            period: Time period ("24h", "7d", or "30d")
            
        Returns:
            HistoricalData object or None if not available
        """
        if period not in ["24h", "7d", "30d"]:
            return None
        
        try:
            # Try crypto first
            historical = self._fetch_crypto_historical(symbol, period)
            if historical and historical.prices:
                return historical
            
            # Try stock
            historical = self._fetch_stock_historical(symbol, period)
            if historical and historical.prices:
                return historical
            
            return None
        except Exception as e:
            print(f"Error fetching historical data for {symbol}: {e}")
            return None

    def _fetch_crypto_historical(self, symbol: str, period: str = "7d") -> HistoricalData:
        """
        Fetch historical crypto data from CoinGecko.
        
        Args:
            symbol: Crypto symbol
            period: Time period ("24h", "7d", or "30d")
            
        Returns:
            HistoricalData object
        """
        try:
            # Map period to days for API
            days_map = {"24h": 1, "7d": 7, "30d": 30}
            days = days_map.get(period, 7)
            
            url = f"{self.coingecko_base_url}/coins/{symbol.lower()}/market_chart"
            params = {
                "vs_currency": "usd",
                "days": days,
                "interval": "daily"
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            prices = [price[1] for price in data.get("prices", [])]
            timestamps = [price[0] / 1000 for price in data.get("prices", [])]  # Convert to seconds
            
            return HistoricalData(
                period=period,
                prices=prices,
                timestamps=timestamps
            )
        except Exception as e:
            print(f"Error fetching crypto historical data for {symbol}: {e}")
            return HistoricalData(period=period, prices=[], timestamps=[])

    def _fetch_stock_historical(self, symbol: str, period: str = "7d") -> HistoricalData:
        """
        Fetch historical stock data from Alpha Vantage.
        
        Args:
            symbol: Stock symbol
            period: Time period ("24h", "7d", or "30d")
            
        Returns:
            HistoricalData object
        """
        try:
            # Use TIME_SERIES_DAILY for stock data
            params = {
                "function": "TIME_SERIES_DAILY",
                "symbol": symbol,
                "apikey": self.alphavantage_api_key or "demo"
            }
            
            response = requests.get(self.alphavantage_base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            time_series_key = "Time Series (Daily)"
            if time_series_key not in data:
                return HistoricalData(period=period, prices=[], timestamps=[])
            
            time_series = data[time_series_key]
            
            # Get the appropriate number of days
            days_map = {"24h": 1, "7d": 7, "30d": 30}
            days = days_map.get(period, 7)
            
            prices = []
            timestamps = []
            
            for i, (date_str, day_data) in enumerate(time_series.items()):
                if i >= days:
                    break
                prices.append(float(day_data.get("4. close", 0)))
                # Convert date string to timestamp
                from datetime import datetime as dt
                timestamp = dt.strptime(date_str, "%Y-%m-%d").timestamp()
                timestamps.append(timestamp)
            
            return HistoricalData(
                period=period,
                prices=prices,
                timestamps=timestamps
            )
        except Exception as e:
            print(f"Error fetching stock historical data for {symbol}: {e}")
            return HistoricalData(period=period, prices=[], timestamps=[])
