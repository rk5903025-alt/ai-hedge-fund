"""Unicorn + Fractal alpha model.

This first implementation provides the deterministic fractal market-structure
layer. The exact Unicorn/ICT rules can be plugged into this model later when
the user's Pine Script is added; until then, the model deliberately avoids
claiming that generic fractal structure is an exact reproduction of that
indicator.
"""

from __future__ import annotations

from datetime import date as Date
from datetime import datetime, timedelta

from hedge_fund.data.protocol import DataClient
from hedge_fund.models import Signal
from hedge_fund.signals.base import QuantModel


class UnicornFractalModel(QuantModel):
    """Generate a point-in-time signal from confirmed fractal breakouts.

    A bullish signal occurs when the latest close breaks the most recently
    confirmed swing-high fractal. A bearish signal occurs when it breaks the
    most recently confirmed swing-low fractal. Fractals require two bars on
    each side, so the current bar can never be used to confirm the fractal.
    """

    def __init__(self, *, lookback_bars: int = 100) -> None:
        if lookback_bars < 5:
            raise ValueError("lookback_bars must be at least 5")
        self._lookback_bars = lookback_bars

    @property
    def name(self) -> str:
        return "unicorn_fractal"

    def predict(self, ticker: str, date: str, data_client: DataClient) -> Signal:
        as_of = _parse_date(date)
        start = as_of - timedelta(days=self._lookback_bars * 3)
        prices = data_client.get_prices(
            ticker,
            start.isoformat(),
            as_of.isoformat(),
        )
        prices = sorted(
            (p for p in prices if _parse_date(p.time) <= as_of),
            key=lambda p: p.time,
        )[-self._lookback_bars :]

        if len(prices) < 5:
            return self._neutral(ticker, date, "insufficient_history")

        swing_highs, swing_lows = _confirmed_fractals(prices)
        current_close = float(prices[-1].close)

        latest_high = swing_highs[-1] if swing_highs else None
        latest_low = swing_lows[-1] if swing_lows else None

        if latest_high is not None and current_close > latest_high[1]:
            return Signal(
                model_name=self.name,
                ticker=ticker,
                date=date,
                value=0.8,
                reasoning=(
                    f"Close {current_close:.4f} broke confirmed swing high "
                    f"{latest_high[1]:.4f}."
                ),
                components={"fractal_breakout": 1.0},
                metadata={
                    "structure": "bullish_breakout",
                    "fractal_time": latest_high[0],
                    "fractal_level": latest_high[1],
                },
            )

        if latest_low is not None and current_close < latest_low[1]:
            return Signal(
                model_name=self.name,
                ticker=ticker,
                date=date,
                value=-0.8,
                reasoning=(
                    f"Close {current_close:.4f} broke confirmed swing low "
                    f"{latest_low[1]:.4f}."
                ),
                components={"fractal_breakout": -1.0},
                metadata={
                    "structure": "bearish_breakout",
                    "fractal_time": latest_low[0],
                    "fractal_level": latest_low[1],
                },
            )

        return self._neutral(ticker, date, "no_confirmed_breakout")

    def _neutral(self, ticker: str, date: str, reason: str) -> Signal:
        return Signal(
            model_name=self.name,
            ticker=ticker,
            date=date,
            value=0.0,
            reasoning="No confirmed fractal breakout.",
            metadata={"structure": "neutral", "reason": reason},
        )


def _confirmed_fractals(prices):
    """Return confirmed swing highs and lows as (time, level) pairs."""
    highs = []
    lows = []

    for i in range(2, len(prices) - 2):
        center = prices[i]
        left = prices[i - 2 : i]
        right = prices[i + 1 : i + 3]

        if center.high > max(p.high for p in left + right):
            highs.append((center.time, float(center.high)))

        if center.low < min(p.low for p in left + right):
            lows.append((center.time, float(center.low)))

    return highs, lows


def _parse_date(value: str) -> Date:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
