"""Analysis engine for generating trading recommendations."""

import time
from typing import Literal

from src.models.market_data import MarketData
from src.models.trading_tip import TipSource, TradingTip
from src.utils.event_store import EventStore
from src.utils.logger import StructuredLogger
from src.utils.trace_context import get_current_trace


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
        """Simple moving average."""
        if len(prices) < period:
            return None
        return sum(prices[-period:]) / period

    def _calculate_rsi(self, prices: list[float], period: int = 14) -> float | None:
        """
        Wilder RSI. Accepts short periods (e.g. 5) for small datasets.
        Requires period + 1 prices minimum.
        """
        if len(prices) < period + 1:
            return None
        deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
        relevant = deltas[-period:]
        gains = [d if d > 0 else 0.0 for d in relevant]
        losses = [-d if d < 0 else 0.0 for d in relevant]
        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period
        if avg_loss == 0:
            return 100.0 if avg_gain > 0 else 50.0
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    def _calculate_ema(self, prices: list[float], period: int) -> float | None:
        """Exponential moving average."""
        if len(prices) < period:
            return None
        multiplier = 2.0 / (period + 1)
        ema = sum(prices[:period]) / period
        for price in prices[period:]:
            ema = price * multiplier + ema * (1.0 - multiplier)
        return ema

    def _calculate_volume_signal(
        self,
        volume_24h: float | None,
        historical_volumes: list[float] | None,
        price_change_24h: float,
    ) -> tuple[str | None, float | None]:
        """
        Compare today's volume against the 7-day average.
        Returns (direction, ratio) where direction is 'bullish', 'bearish', or 'neutral'.
        Bullish: elevated volume on an up day (ratio >= 1.2, price_change > 0).
        Bearish: elevated volume on a down day (ratio >= 1.2, price_change < 0).
        """
        if volume_24h is None or not historical_volumes or len(historical_volumes) < 2:
            return None, None
        avg_volume = sum(historical_volumes) / len(historical_volumes)
        if avg_volume == 0:
            return None, None
        ratio = volume_24h / avg_volume
        if ratio >= 1.2 and price_change_24h > 0:
            return "bullish", ratio
        if ratio >= 1.2 and price_change_24h < 0:
            return "bearish", ratio
        return "neutral", ratio

    def _build_indicators(
        self,
        prices: list[float],
        volume_24h: float | None,
        price_change_24h: float,
        historical_volumes: list[float] | None = None,
    ) -> dict:
        """
        Build the indicators dict consumed by _generate_recommendation.

        RSI period: 5 when < 15 prices, 14 otherwise (RSI-14 needs 15+ prices).
        SMA periods: 3 (short) and 7 (long) — fit within an 8-point history.
        MACD removed — requires 26+ prices; always returned None with real data.
        """
        n = len(prices)

        if n >= 15:
            rsi_period = 14
        elif n >= 6:
            rsi_period = 5
        else:
            rsi_period = None

        rsi = self._calculate_rsi(prices, rsi_period) if rsi_period else None

        sma_short_period = 3
        sma_long_period = 7
        sma_short = self._calculate_sma(prices, sma_short_period)
        sma_long = self._calculate_sma(prices, sma_long_period)

        vol_direction, vol_ratio = self._calculate_volume_signal(
            volume_24h, historical_volumes, price_change_24h
        )

        return {
            "rsi": rsi,
            "rsi_period": rsi_period,
            "sma_short": sma_short,
            "sma_short_period": sma_short_period,
            "sma_long": sma_long,
            "sma_long_period": sma_long_period,
            "volume_direction": vol_direction,
            "volume_ratio": vol_ratio,
        }

    def _generate_recommendation(
        self,
        market_data: MarketData,
        indicators: dict,
        asset_type: Literal["crypto", "stock"],
        sentiment_score: float | None = None,
    ) -> tuple[Literal["BUY", "SELL", "HOLD"], int, str]:
        """
        Weighted signal aggregation that degrades gracefully when data is scarce.

        Signal weights (when all fire): RSI 35%, SMA crossover 30%, momentum 20%, volume 15%.
        A scarcity penalty (up to 25 pts) reduces confidence when fewer than 15 prices exist.
        RSI in the neutral zone is recorded but does not consume weight.
        """
        prices = market_data.historical_data.prices if market_data.historical_data else []
        n = len(prices)

        if n < 2:
            return "HOLD", 20, "Insufficient historical data — no actionable signal"

        # Asset-type thresholds
        if asset_type == "crypto":
            rsi_oversold, rsi_overbought, momentum_threshold = 35, 65, 3.0
        else:
            rsi_oversold, rsi_overbought, momentum_threshold = 30, 70, 5.0

        rsi = indicators.get("rsi")
        rsi_period = indicators.get("rsi_period", 14)
        sma_short = indicators.get("sma_short")
        sma_long = indicators.get("sma_long")
        price_change = market_data.price_change_24h
        vol_direction = indicators.get("volume_direction")
        vol_ratio = indicators.get("volume_ratio")

        WEIGHT_RSI = 0.35
        WEIGHT_SMA = 0.30
        WEIGHT_MOMENTUM = 0.20
        WEIGHT_VOLUME = 0.15

        buy_weight = 0.0
        sell_weight = 0.0
        active_weight = 0.0
        reasoning_parts: list[str] = []

        # RSI signal — neutral zone noted but does not consume weight
        if rsi is not None:
            rsi_tag = f"RSI({rsi_period})={rsi:.1f}"
            if rsi < rsi_oversold:
                buy_weight += WEIGHT_RSI
                active_weight += WEIGHT_RSI
                reasoning_parts.append(f"{rsi_tag} oversold")
            elif rsi > rsi_overbought:
                sell_weight += WEIGHT_RSI
                active_weight += WEIGHT_RSI
                reasoning_parts.append(f"{rsi_tag} overbought")
            else:
                reasoning_parts.append(f"{rsi_tag} neutral")
        else:
            reasoning_parts.append("RSI unavailable")

        # SMA crossover signal
        if sma_short is not None and sma_long is not None:
            short_p = indicators.get("sma_short_period", "S")
            long_p = indicators.get("sma_long_period", "L")
            direction = ">" if sma_short > sma_long else "<"
            sma_tag = f"SMA{short_p}({direction})SMA{long_p}"
            if sma_short > sma_long:
                buy_weight += WEIGHT_SMA
                active_weight += WEIGHT_SMA
                reasoning_parts.append(f"{sma_tag} short-term uptrend")
            else:
                sell_weight += WEIGHT_SMA
                active_weight += WEIGHT_SMA
                reasoning_parts.append(f"{sma_tag} short-term downtrend")
        elif sma_short is not None:
            # Single SMA: price vs average at half-weight
            short_p = indicators.get("sma_short_period", "S")
            current = prices[-1]
            if current > sma_short:
                buy_weight += WEIGHT_SMA * 0.5
                active_weight += WEIGHT_SMA * 0.5
                reasoning_parts.append(f"price above SMA{short_p}")
            else:
                sell_weight += WEIGHT_SMA * 0.5
                active_weight += WEIGHT_SMA * 0.5
                reasoning_parts.append(f"price below SMA{short_p}")
        else:
            reasoning_parts.append("SMA unavailable")

        # Price momentum signal
        if abs(price_change) >= momentum_threshold:
            momentum_tag = f"24h {price_change:+.2f}%"
            if price_change > 0:
                buy_weight += WEIGHT_MOMENTUM
                active_weight += WEIGHT_MOMENTUM
                reasoning_parts.append(f"{momentum_tag} bullish momentum")
            else:
                sell_weight += WEIGHT_MOMENTUM
                active_weight += WEIGHT_MOMENTUM
                reasoning_parts.append(f"{momentum_tag} bearish momentum")
        else:
            reasoning_parts.append(f"24h {price_change:+.2f}% (below threshold)")

        # Volume confirmation signal
        if vol_direction in ("bullish", "bearish") and vol_ratio is not None:
            vol_tag = f"volume {vol_ratio:.1f}× 7d avg"
            if vol_direction == "bullish":
                buy_weight += WEIGHT_VOLUME
                active_weight += WEIGHT_VOLUME
                reasoning_parts.append(f"{vol_tag} confirms up-move")
            else:
                sell_weight += WEIGHT_VOLUME
                active_weight += WEIGHT_VOLUME
                reasoning_parts.append(f"{vol_tag} confirms down-move")
        elif vol_ratio is not None:
            reasoning_parts.append(f"volume {vol_ratio:.1f}× 7d avg (neutral)")

        if active_weight == 0:
            return "HOLD", 20, "No indicators fired — hold and monitor"

        net = buy_weight - sell_weight
        dominant_weight = max(buy_weight, sell_weight)
        raw_confidence = (dominant_weight / active_weight) * 100.0

        # Scarcity penalty: up to 25 pts when fewer than 15 prices available
        MIN_RELIABLE = 15
        if n < MIN_RELIABLE:
            scarcity_factor = (n - 2) / (MIN_RELIABLE - 2)
            penalty = (1.0 - scarcity_factor) * 25.0
        else:
            penalty = 0.0

        confidence = max(15, min(95, int(raw_confidence - penalty)))

        # Deadband: require minimum net weight advantage to issue a directional call
        MIN_NET = 0.10
        if net > MIN_NET:
            action: Literal["BUY", "SELL", "HOLD"] = "BUY"
        elif net < -MIN_NET:
            action = "SELL"
        else:
            action = "HOLD"

        # Sentiment adjustment: blends news signal with technical confidence.
        # Agreement boosts by up to +10; contradiction penalises by up to -15.
        if sentiment_score is not None:
            sentiment_direction = (
                "bullish" if sentiment_score > 0.1
                else "bearish" if sentiment_score < -0.1
                else "neutral"
            )
            if sentiment_direction != "neutral":
                tech_bullish = action == "BUY"
                agrees = (sentiment_direction == "bullish") == tech_bullish
                magnitude = abs(sentiment_score)
                if action != "HOLD":
                    if agrees:
                        confidence = min(95, confidence + int(magnitude * 10))
                    else:
                        confidence = max(15, confidence - int(magnitude * 15))
                label_str = f"news sentiment {sentiment_direction} ({sentiment_score:+.2f})"
                if not agrees and action != "HOLD":
                    label_str += " [contra-signal]"
                reasoning_parts.append(label_str)

        reasoning = "; ".join(reasoning_parts)
        return action, confidence, reasoning

    def analyze_crypto(self, market_data: list[MarketData], sentiment: dict | None = None) -> list[TradingTip]:
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
                },
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

                indicators = self._build_indicators(
                    prices=prices,
                    volume_24h=data.volume_24h,
                    price_change_24h=data.price_change_24h,
                )

                # Generate recommendation
                sentiment_score = None
                if sentiment:
                    rec = sentiment.get(data.symbol.upper()) or sentiment.get(data.symbol)
                    if rec:
                        sentiment_score = rec.score if hasattr(rec, "score") else rec.get("score")
                recommendation, confidence, reasoning = self._generate_recommendation(
                    data, indicators, "crypto", sentiment_score=sentiment_score
                )

                # Collect used indicators
                used_indicators = []
                if indicators["rsi"] is not None:
                    used_indicators.append(f"RSI({indicators['rsi_period']})")
                if indicators["sma_short"] is not None:
                    used_indicators.append(f"SMA{indicators['sma_short_period']}")
                if indicators["sma_long"] is not None:
                    used_indicators.append(f"SMA{indicators['sma_long_period']}")
                if indicators.get("volume_direction") in ("bullish", "bearish"):
                    used_indicators.append("Volume")

                # Log analysis result
                self.logger.info(
                    f"Cryptocurrency analysis completed for {data.symbol}",
                    context={
                        "trace_id": trace_id,
                        "symbol": data.symbol,
                        "recommendation": recommendation,
                        "confidence": confidence,
                        "indicators": used_indicators,
                    },
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
                    sources=[TipSource(name=data.source.name, url=data.source.url)],
                )
                tips.append(tip)

            duration_ms = (time.time() - start_time) * 1000
            self.logger.info(
                "Cryptocurrency analysis completed",
                context={
                    "trace_id": trace_id,
                    "tips_generated": len(tips),
                    "duration_ms": duration_ms,
                },
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

    def analyze_stocks(self, market_data: list[MarketData], sentiment: dict | None = None) -> list[TradingTip]:
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
                },
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

                indicators = self._build_indicators(
                    prices=prices,
                    volume_24h=data.volume_24h,
                    price_change_24h=data.price_change_24h,
                )

                # Generate recommendation
                sentiment_score = None
                if sentiment:
                    rec = sentiment.get(data.symbol.upper()) or sentiment.get(data.symbol)
                    if rec:
                        sentiment_score = rec.score if hasattr(rec, "score") else rec.get("score")
                recommendation, confidence, reasoning = self._generate_recommendation(
                    data, indicators, "stock", sentiment_score=sentiment_score
                )

                # Collect used indicators
                used_indicators = []
                if indicators["rsi"] is not None:
                    used_indicators.append(f"RSI({indicators['rsi_period']})")
                if indicators["sma_short"] is not None:
                    used_indicators.append(f"SMA{indicators['sma_short_period']}")
                if indicators["sma_long"] is not None:
                    used_indicators.append(f"SMA{indicators['sma_long_period']}")
                if indicators.get("volume_direction") in ("bullish", "bearish"):
                    used_indicators.append("Volume")

                # Log analysis result
                self.logger.info(
                    f"Stock analysis completed for {data.symbol}",
                    context={
                        "trace_id": trace_id,
                        "symbol": data.symbol,
                        "recommendation": recommendation,
                        "confidence": confidence,
                        "indicators": used_indicators,
                    },
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
                    sources=[TipSource(name=data.source.name, url=data.source.url)],
                )
                tips.append(tip)

            duration_ms = (time.time() - start_time) * 1000
            self.logger.info(
                "Stock analysis completed",
                context={
                    "trace_id": trace_id,
                    "tips_generated": len(tips),
                    "duration_ms": duration_ms,
                },
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
