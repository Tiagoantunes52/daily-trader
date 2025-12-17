"""Analysis engine for generating trading recommendations."""

from src.models.market_data import MarketData
from src.models.trading_tip import TradingTip, TipSource
from src.utils.logger import StructuredLogger
from src.utils.trace_context import get_current_trace
from src.utils.event_store import EventStore
from typing import Literal
import time


class AnalysisEngine:
    """Generates trading recommendations based on market data."""

    def __init__(self, event_store: EventStore | None = None):
        """
        Initialize the analysis engine.

        Args:
            event_store: Optional event store for logging events
        """
        self.logger = StructuredLogger("AnalysisEngine")
        self.event_store = event_store

    def _calculate_sma(self, prices: list[float], period: int) -> float | None:
        """Calculate Simple Moving Average."""
        if len(prices) < period:
            return None
        return sum(prices[-period:]) / period

    def _calculate_rsi(self, prices: list[float], period: int = 14) -> float | None:
        """Calculate Relative Strength Index."""
        if len(prices) < period + 1:
            return None
        
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100.0 if avg_gain > 0 else 50.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def _calculate_macd(self, prices: list[float]) -> tuple[float | None, float | None]:
        """Calculate MACD (Moving Average Convergence Divergence)."""
        if len(prices) < 26:
            return None, None
        
        ema_12 = self._calculate_ema(prices, 12)
        ema_26 = self._calculate_ema(prices, 26)
        
        if ema_12 is None or ema_26 is None:
            return None, None
        
        macd = ema_12 - ema_26
        signal = self._calculate_ema([macd], 9) if macd else None
        
        return macd, signal

    def _calculate_ema(self, prices: list[float], period: int) -> float | None:
        """Calculate Exponential Moving Average."""
        if len(prices) < period:
            return None
        
        multiplier = 2 / (period + 1)
        ema = sum(prices[:period]) / period
        
        for price in prices[period:]:
            ema = price * multiplier + ema * (1 - multiplier)
        
        return ema

    def _generate_recommendation(
        self,
        market_data: MarketData,
        indicators: dict,
        asset_type: Literal["crypto", "stock"]
    ) -> tuple[Literal["BUY", "SELL", "HOLD"], int, str]:
        """
        Generate a trading recommendation based on technical indicators.
        
        Returns:
            Tuple of (recommendation, confidence, reasoning)
        """
        prices = market_data.historical_data.prices
        if not prices or len(prices) < 2:
            return "HOLD", 30, "Insufficient historical data for analysis"
        
        rsi = indicators.get("rsi")
        sma_short = indicators.get("sma_short")
        sma_long = indicators.get("sma_long")
        macd = indicators.get("macd")
        price_change = market_data.price_change_24h
        
        buy_signals = 0
        sell_signals = 0
        total_signals = 0
        
        # RSI signals
        if rsi is not None:
            total_signals += 1
            if rsi < 30:
                buy_signals += 1
            elif rsi > 70:
                sell_signals += 1
        
        # SMA signals
        if sma_short is not None and sma_long is not None:
            total_signals += 1
            if sma_short > sma_long:
                buy_signals += 1
            else:
                sell_signals += 1
        
        # MACD signals
        if macd is not None:
            total_signals += 1
            if macd > 0:
                buy_signals += 1
            else:
                sell_signals += 1
        
        # Price change signal
        if price_change > 5:
            buy_signals += 1
            total_signals += 1
        elif price_change < -5:
            sell_signals += 1
            total_signals += 1
        
        # Determine recommendation
        if total_signals == 0:
            return "HOLD", 30, "Insufficient indicator data"
        
        confidence = int((max(buy_signals, sell_signals) / total_signals) * 100)
        
        if buy_signals > sell_signals:
            reasoning = f"Technical indicators suggest upward momentum ({buy_signals}/{total_signals} signals positive)"
            return "BUY", confidence, reasoning
        elif sell_signals > buy_signals:
            reasoning = f"Technical indicators suggest downward pressure ({sell_signals}/{total_signals} signals negative)"
            return "SELL", confidence, reasoning
        else:
            reasoning = "Mixed signals from technical indicators"
            return "HOLD", confidence, reasoning

    def analyze_crypto(self, market_data: list[MarketData]) -> list[TradingTip]:
        """
        Generate cryptocurrency trading tips.
        
        Args:
            market_data: List of crypto market data
            
        Returns:
            List of trading tips with reasoning and indicators
        """
        trace_id = get_current_trace()
        start_time = time.time()
        tips = []
        
        try:
            self.logger.info(
                "Starting cryptocurrency analysis",
                context={
                    "trace_id": trace_id,
                    "data_count": len(market_data),
                }
            )
            
            if self.event_store and trace_id:
                self.event_store.add_event(
                    trace_id=trace_id,
                    event_type="analysis_start",
                    component="AnalysisEngine",
                    message="Starting cryptocurrency analysis",
                    context={"asset_type": "crypto", "data_count": len(market_data)},
                )
            
            for data in market_data:
                if data.type != "crypto":
                    continue
                
                prices = data.historical_data.prices
                
                # Calculate indicators
                indicators = {
                    "rsi": self._calculate_rsi(prices),
                    "sma_short": self._calculate_sma(prices, 5),
                    "sma_long": self._calculate_sma(prices, 20),
                    "macd": self._calculate_macd(prices)[0],
                }
                
                # Generate recommendation
                recommendation, confidence, reasoning = self._generate_recommendation(
                    data, indicators, "crypto"
                )
                
                # Collect used indicators
                used_indicators = []
                if indicators["rsi"] is not None:
                    used_indicators.append("RSI")
                if indicators["sma_short"] is not None and indicators["sma_long"] is not None:
                    used_indicators.append("SMA")
                if indicators["macd"] is not None:
                    used_indicators.append("MACD")
                
                # Log analysis result
                self.logger.info(
                    f"Cryptocurrency analysis completed for {data.symbol}",
                    context={
                        "trace_id": trace_id,
                        "symbol": data.symbol,
                        "recommendation": recommendation,
                        "confidence": confidence,
                        "indicators": used_indicators,
                    }
                )
                
                if self.event_store and trace_id:
                    self.event_store.add_event(
                        trace_id=trace_id,
                        event_type="analysis_complete",
                        component="AnalysisEngine",
                        message=f"Analysis completed for {data.symbol}",
                        context={
                            "symbol": data.symbol,
                            "recommendation": recommendation,
                            "confidence": confidence,
                            "indicators": used_indicators,
                        },
                    )
                
                tip = TradingTip(
                    symbol=data.symbol,
                    type="crypto",
                    recommendation=recommendation,
                    reasoning=reasoning,
                    confidence=confidence,
                    indicators=used_indicators,
                    sources=[TipSource(name=data.source.name, url=data.source.url)]
                )
                tips.append(tip)
            
            duration_ms = (time.time() - start_time) * 1000
            self.logger.info(
                "Cryptocurrency analysis completed",
                context={
                    "trace_id": trace_id,
                    "tips_generated": len(tips),
                    "duration_ms": duration_ms,
                }
            )
            
            if self.event_store and trace_id:
                self.event_store.add_event(
                    trace_id=trace_id,
                    event_type="analysis_complete",
                    component="AnalysisEngine",
                    message="Cryptocurrency analysis completed",
                    context={"asset_type": "crypto", "tips_generated": len(tips)},
                    duration_ms=duration_ms,
                )
        
        except Exception as e:
            self.logger.error(
                "Error during cryptocurrency analysis",
                context={
                    "trace_id": trace_id,
                    "error_type": type(e).__name__,
                },
                exception=e,
            )
            raise
        
        return tips

    def analyze_stocks(self, market_data: list[MarketData]) -> list[TradingTip]:
        """
        Generate stock trading tips.
        
        Args:
            market_data: List of stock market data
            
        Returns:
            List of trading tips with reasoning and indicators
        """
        trace_id = get_current_trace()
        start_time = time.time()
        tips = []
        
        try:
            self.logger.info(
                "Starting stock analysis",
                context={
                    "trace_id": trace_id,
                    "data_count": len(market_data),
                }
            )
            
            if self.event_store and trace_id:
                self.event_store.add_event(
                    trace_id=trace_id,
                    event_type="analysis_start",
                    component="AnalysisEngine",
                    message="Starting stock analysis",
                    context={"asset_type": "stock", "data_count": len(market_data)},
                )
            
            for data in market_data:
                if data.type != "stock":
                    continue
                
                prices = data.historical_data.prices
                
                # Calculate indicators
                indicators = {
                    "rsi": self._calculate_rsi(prices),
                    "sma_short": self._calculate_sma(prices, 5),
                    "sma_long": self._calculate_sma(prices, 20),
                    "macd": self._calculate_macd(prices)[0],
                }
                
                # Generate recommendation
                recommendation, confidence, reasoning = self._generate_recommendation(
                    data, indicators, "stock"
                )
                
                # Collect used indicators
                used_indicators = []
                if indicators["rsi"] is not None:
                    used_indicators.append("RSI")
                if indicators["sma_short"] is not None and indicators["sma_long"] is not None:
                    used_indicators.append("SMA")
                if indicators["macd"] is not None:
                    used_indicators.append("MACD")
                
                # Log analysis result
                self.logger.info(
                    f"Stock analysis completed for {data.symbol}",
                    context={
                        "trace_id": trace_id,
                        "symbol": data.symbol,
                        "recommendation": recommendation,
                        "confidence": confidence,
                        "indicators": used_indicators,
                    }
                )
                
                if self.event_store and trace_id:
                    self.event_store.add_event(
                        trace_id=trace_id,
                        event_type="analysis_complete",
                        component="AnalysisEngine",
                        message=f"Analysis completed for {data.symbol}",
                        context={
                            "symbol": data.symbol,
                            "recommendation": recommendation,
                            "confidence": confidence,
                            "indicators": used_indicators,
                        },
                    )
                
                tip = TradingTip(
                    symbol=data.symbol,
                    type="stock",
                    recommendation=recommendation,
                    reasoning=reasoning,
                    confidence=confidence,
                    indicators=used_indicators,
                    sources=[TipSource(name=data.source.name, url=data.source.url)]
                )
                tips.append(tip)
            
            duration_ms = (time.time() - start_time) * 1000
            self.logger.info(
                "Stock analysis completed",
                context={
                    "trace_id": trace_id,
                    "tips_generated": len(tips),
                    "duration_ms": duration_ms,
                }
            )
            
            if self.event_store and trace_id:
                self.event_store.add_event(
                    trace_id=trace_id,
                    event_type="analysis_complete",
                    component="AnalysisEngine",
                    message="Stock analysis completed",
                    context={"asset_type": "stock", "tips_generated": len(tips)},
                    duration_ms=duration_ms,
                )
        
        except Exception as e:
            self.logger.error(
                "Error during stock analysis",
                context={
                    "trace_id": trace_id,
                    "error_type": type(e).__name__,
                },
                exception=e,
            )
            raise
        
        return tips
