# Unicorn + Fractal Trading Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a point-in-time Unicorn + Fractal quantitative alpha model, feature layer, risk-aware paper execution, and backtestable trading flow to the user's fork without replacing the existing v2 architecture.

**Architecture:** The existing `AlphaModel` contract remains the model boundary. A new `UnicornFractalModel` consumes the existing `DataClient` price history and emits the existing `Signal` model; downstream portfolio/risk/execution components remain responsible for position mechanics. The first release is deliberately deterministic and paper/backtest only; the exact proprietary indicator rules will be inserted once the user's Pine Script is supplied.

**Tech Stack:** Python 3.11+, Pydantic, pandas, NumPy, pytest, existing `hedge_fund` v2 architecture.

**Spec:** Conversation-approved design for the user's Unicorn + Fractal trading bot, summarized in this repository plan.

## Global Constraints

- Preserve the existing `AlphaModel -> Signal -> pipeline` architecture.
- Alpha models produce views only; they must not place orders or choose portfolio size.
- All signal calculations must be point-in-time and use only bars with timestamps at or before the requested `date`.
- No live-money execution is introduced in this phase; execution is backtest or paper only.
- The model must return a valid `Signal.value` in `[-1.0, 1.0]`.
- Missing/insufficient price history must result in an abstain signal rather than fabricated data.
- The exact Unicorn + Fractal proprietary rules are not guessed; the initial model provides an isolated, testable structure that can be replaced/refined from the user's Pine Script.

## Review Focus

1. Look-ahead leakage at the requested date — covered by the point-in-time model tests.
2. Insufficient candles — covered by the abstain test.
3. Flat/zero-range candles and zero-volume data — covered by numeric-safety tests.
4. Conflicting trend/fractal conditions — covered by signal composition tests.
5. Signal magnitude outside the contract — covered by clamping tests.

### Task 1: Add the Unicorn + Fractal signal model

**Files:**
- Create: `hedge_fund/signals/unicorn_fractal.py`
- Modify: `hedge_fund/signals/__init__.py`
- Test: `tests/signals/test_unicorn_fractal.py`

**Interfaces:**
- Consumes: `DataClient.get_prices(ticker, start_date, end_date)` and `Price` objects.
- Produces: `UnicornFractalModel.name -> "unicorn_fractal"`; `predict(ticker, date, data_client) -> Signal`.

- [ ] **Step 1: Write failing tests**

```python
from hedge_fund.data.models import Price
from hedge_fund.signals.unicorn_fractal import UnicornFractalModel


class FakeDataClient:
    def __init__(self, prices):
        self.prices = prices

    def get_prices(self, ticker, start_date, end_date, **kwargs):
        return [p for p in self.prices if p.time[:10] <= end_date]


def make_prices(n=40):
    return [
        Price(open=100+i, high=102+i, low=99+i, close=101+i, volume=1000, time=f"2026-09-{i+1:02d}T10:00:00")
        for i in range(n)
    ]


def test_model_returns_signal_with_contract():
    model = UnicornFractalModel()
    signal = model.predict("NIFTY50", "2026-09-21", FakeDataClient(make_prices()))
    assert signal.model_name == "unicorn_fractal"
    assert signal.ticker == "NIFTY50"
    assert -1.0 <= signal.value <= 1.0


def test_model_abstains_when_history_is_insufficient():
    model = UnicornFractalModel(min_bars=30)
    signal = model.predict("NIFTY50", "2026-09-21", FakeDataClient(make_prices(10)))
    assert signal.value == 0.0


def test_model_does_not_use_future_bars():
    prices = make_prices(40)
    prices.append(Price(open=1000, high=1100, low=900, close=1090, volume=100000, time="2026-09-22T10:00:00"))
    client = FakeDataClient(prices)
    signal = UnicornFractalModel().predict("NIFTY50", "2026-09-21", client)
    assert signal.metadata["bars_used"] == 21


def test_signal_components_are_bounded():
    signal = UnicornFractalModel().predict("NIFTY50", "2026-09-21", FakeDataClient(make_prices()))
    assert all(-1.0 <= value <= 1.0 for value in signal.components.values())
```

- [ ] **Step 2: Run the focused tests and verify they fail**

Run:

```bash
pytest tests/signals/test_unicorn_fractal.py -v
```

Expected: collection/import failure because `UnicornFractalModel` does not yet exist.

- [ ] **Step 3: Implement the minimal model**

The model will:

```python
class UnicornFractalModel(QuantModel):
    @property
    def name(self) -> str:
        return "unicorn_fractal"

    def predict(self, ticker: str, date: str, data_client: DataClient) -> Signal:
        ...
```

It will fetch a bounded history ending at `date`, compute normalized trend/fractal components, combine them into a clamped conviction, and return an abstain signal when there are fewer than `min_bars` usable rows. The initial deterministic components are explicitly named `trend`, `fractal`, and `momentum` so the proprietary Pine logic can later replace those calculations without changing the public interface.

- [ ] **Step 4: Register the model**

Add:

```python
from hedge_fund.signals.unicorn_fractal import UnicornFractalModel

ALPHA_MODEL_REGISTRY["unicorn_fractal"] = UnicornFractalModel
```

and export it in `__all__`.

- [ ] **Step 5: Run focused tests**

Run:

```bash
pytest tests/signals/test_unicorn_fractal.py -v
```

Expected: all focused tests PASS.

- [ ] **Step 6: Commit**

```bash
git add hedge_fund/signals/unicorn_fractal.py hedge_fund/signals/__init__.py tests/signals/test_unicorn_fractal.py
git commit -m "feat: add Unicorn Fractal alpha model"
```

### Task 2: Add reusable market features

**Files:**
- Create: `hedge_fund/features/__init__.py`
- Create: `hedge_fund/features/market_features.py`
- Test: `tests/features/test_market_features.py`

**Interfaces:**
- Consumes: `list[Price]`.
- Produces: `build_market_features(prices) -> dict[str, float]` with bounded, finite values.

- [ ] **Step 1: Write tests for trend, momentum, volatility and fractal structure.**
- [ ] **Step 2: Run focused tests and verify failure.**
- [ ] **Step 3: Implement pure functions with NumPy/pandas only.**
- [ ] **Step 4: Verify finite/bounded outputs for normal, flat and short series.**
- [ ] **Step 5: Commit with `feat: add reusable market feature layer`**

### Task 3: Integrate the signal into the existing pipeline

**Files:**
- Modify: the existing v2 pipeline/strategy configuration files identified by the current model registry and `run_cycle` wiring.
- Test: the corresponding pipeline test module.

**Interfaces:**
- Consumes: registered `unicorn_fractal` alpha model.
- Produces: a normal `Signal` entry that can participate in existing composite signal/portfolio construction without changing the existing `Signal` schema.

- [ ] **Step 1: Add a pipeline test that selects `unicorn_fractal` by registry name.**
- [ ] **Step 2: Run the focused pipeline test and verify failure.**
- [ ] **Step 3: Wire the model through the existing registry/config path only; do not duplicate pipeline logic.**
- [ ] **Step 4: Run the existing signal/pipeline tests.**
- [ ] **Step 5: Commit with `feat: wire Unicorn Fractal into v2 pipeline`**

### Task 4: Add deterministic risk rules for paper/backtest execution

**Files:**
- Create: `hedge_fund/risk/trading_risk.py`
- Test: `tests/risk/test_trading_risk.py`

**Interfaces:**
- Consumes: signal, account equity, entry price, stop price, daily P&L and exposure.
- Produces: a decision object containing `allowed`, `quantity`, `risk_amount`, and `reason`.

- [ ] **Step 1: Test maximum-risk-per-trade sizing, daily-loss rejection, and exposure rejection.**
- [ ] **Step 2: Verify failing tests.**
- [ ] **Step 3: Implement deterministic sizing/rejection rules.**
- [ ] **Step 4: Run risk tests.**
- [ ] **Step 5: Commit with `feat: add trading risk guardrails`**

### Task 5: Add paper broker behavior

**Files:**
- Create: `hedge_fund/brokers/paper.py`
- Test: `tests/brokers/test_paper.py`

**Interfaces:**
- Consumes: approved order intents.
- Produces: simulated fills, positions, cash and realized/unrealized P&L.

- [ ] **Step 1: Test buy, sell, close and rejected order paths.**
- [ ] **Step 2: Verify failure.**
- [ ] **Step 3: Implement using the existing `Broker` protocol rather than inventing a parallel interface.**
- [ ] **Step 4: Run broker tests.**
- [ ] **Step 5: Commit with `feat: add paper broker`**

### Task 6: Add Unicorn + Fractal backtest harness

**Files:**
- Create or extend the existing v2 backtesting test/module at the location used by `backtest_fund`.
- Test: `tests/backtesting/test_unicorn_fractal_backtest.py`

**Interfaces:**
- Consumes: historical OHLCV, model, risk rules and simulated broker.
- Produces: equity curve and metrics including total return, win rate, profit factor, max drawdown and trade count.

- [ ] **Step 1: Add a deterministic synthetic price-series regression test.**
- [ ] **Step 2: Verify failure.**
- [ ] **Step 3: Connect the model to the existing backtesting engine.**
- [ ] **Step 4: Verify no future bar can affect a prior decision.**
- [ ] **Step 5: Run all backtest tests.**
- [ ] **Step 6: Commit with `feat: backtest Unicorn Fractal strategy`**

### Task 7: Add configuration and documentation

**Files:**
- Modify: `README.md`
- Modify: `.env.example` only if a new non-secret configuration variable is actually required.
- Create: `docs/unicorn-fractal.md`

- [ ] **Step 1: Document model selection, signal semantics, risk defaults and paper-only behavior.**
- [ ] **Step 2: Document that exact proprietary Unicorn + Fractal rules require the user's Pine Script before claiming parity.**
- [ ] **Step 3: Run the complete test suite.**
- [ ] **Step 4: Commit with `docs: document Unicorn Fractal trading workflow`**

### Final Verification

- [ ] Run the full pytest suite.
- [ ] Verify the model registry contains `unicorn_fractal`.
- [ ] Verify signals are point-in-time.
- [ ] Verify risk rejection works before any paper order is submitted.
- [ ] Verify no live broker credentials or live execution path is enabled by default.
- [ ] Review the branch diff for accidental changes outside the feature.
- [ ] Open a pull request from `feature/unicorn-fractal-trading` into `main` only after all tests pass.
