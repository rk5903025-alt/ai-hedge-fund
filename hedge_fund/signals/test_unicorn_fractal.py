from dataclasses import dataclass

from hedge_fund.data.models import Price
from hedge_fund.signals.unicorn_fractal import UnicornFractalModel


@dataclass
class FakeDataClient:
    prices: list[Price]

    def get_prices(self, ticker: str, start_date: str, end_date: str, **kwargs):
        return [p for p in self.prices if start_date <= p.time[:10] <= end_date]


def _bar(day: int, high: float, low: float, close: float) -> Price:
    return Price(
        open=close,
        high=high,
        low=low,
        close=close,
        volume=100,
        time=f"2026-01-{day:02d}T00:00:00Z",
    )


def test_bullish_fractal_breakout_produces_positive_signal():
    prices = [
        _bar(1, 100, 95, 98),
        _bar(2, 101, 96, 99),
        _bar(3, 102, 97, 100),
        _bar(4, 101, 96, 99),
        _bar(5, 103, 98, 102),
        _bar(6, 110, 101, 108),
        _bar(7, 105, 100, 103),
        _bar(8, 104, 99, 102),
        _bar(9, 109, 102, 108),
        _bar(10, 111, 105, 110),
        _bar(11, 116, 108, 115),
    ]

    signal = UnicornFractalModel(lookback_bars=20).predict(
        "NQ", "2026-01-11", FakeDataClient(prices)
    )

    assert signal.value > 0
    assert signal.metadata["structure"] == "bullish_breakout"


def test_no_breakout_returns_neutral_signal():
    prices = [
        _bar(1, 100, 95, 98),
        _bar(2, 101, 96, 99),
        _bar(3, 102, 97, 100),
        _bar(4, 101, 96, 99),
        _bar(5, 103, 98, 102),
        _bar(6, 110, 101, 108),
        _bar(7, 105, 100, 103),
        _bar(8, 104, 99, 102),
        _bar(9, 106, 102, 104),
        _bar(10, 107, 103, 105),
        _bar(11, 108, 104, 106),
    ]

    signal = UnicornFractalModel(lookback_bars=20).predict(
        "NQ", "2026-01-11", FakeDataClient(prices)
    )

    assert signal.value == 0.0
