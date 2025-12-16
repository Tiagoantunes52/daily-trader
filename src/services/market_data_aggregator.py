"""Market data aggregator service for fetching data from multiple sources."""

from typing import Optional
from src.models.market_data import MarketData, HistoricalData, DataSource
from datetime import datetime
import requests


class MarketDataAggregator:
    """Aggregates market data from multiple sources."""

    def __init__(self):
        """Initialize the aggregator with API endpoints."""
        self.coingecko_base_url = "https://api.coingecko.com/api/v3"
        self.alphavantage_base_url = "https://www.alphavantage.co/query"
        self.alphavantage_api_key = None  # Can be set via config

    def fetch_crypto_data(self, symbols: list[str]) -> list[MarketData]:
        """
        Fetch cryptocurrency data from available sources.
        
        Args:
            symbols: List of crypto symbols to fetch (e.g., ["bitcoin", "ethereum"])
            
        Returns:
            List of MarketData objects with source attribution
        """
        market_data_list = []
        
        for symbol in symbols:
            try:
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
            except Exception as e:
                # Log error and continue with next symbol
                print(f"Error fetching crypto data for {symbol}: {e}")
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
        
        for symbol in symbols:
            try:
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
            except Exception as e:
                # Log error and continue with next symbol
                print(f"Error fetching stock data for {symbol}: {e}")
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
