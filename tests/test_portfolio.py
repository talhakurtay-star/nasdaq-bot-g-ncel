import pytest

from nasdaqbot.portfolio import Portfolio


def test_buy_reduces_cash_and_adds_shares():
    p = Portfolio(cash=1000.0)
    p.buy(5, 100.0)
    assert p.shares == 5
    assert p.cash == pytest.approx(500.0)
    assert p.equity(100.0) == pytest.approx(1000.0)


def test_sell_returns_cash():
    p = Portfolio(cash=1000.0)
    p.buy(5, 100.0)
    p.sell(5, 120.0)
    assert p.shares == 0
    assert p.cash == pytest.approx(1100.0)


def test_cannot_overspend():
    p = Portfolio(cash=100.0)
    with pytest.raises(ValueError):
        p.buy(2, 100.0)


def test_sell_caps_at_held_shares():
    p = Portfolio(cash=1000.0)
    p.buy(3, 100.0)
    p.sell(10, 100.0)  # sadece 3 satılabilir
    assert p.shares == 0


def test_commission_applied():
    p = Portfolio(cash=1000.0, commission=0.01)
    p.buy(5, 100.0)  # maliyet 500 + 5 komisyon
    assert p.cash == pytest.approx(495.0)


def test_rebalance_to_full_then_cash():
    p = Portfolio(cash=1000.0)
    p.rebalance_to(1.0, 100.0)
    assert p.shares == pytest.approx(10.0)
    assert p.cash == pytest.approx(0.0, abs=1e-6)
    p.rebalance_to(0.0, 110.0)
    assert p.shares == pytest.approx(0.0)
    assert p.cash == pytest.approx(1100.0)


def test_rebalance_half():
    p = Portfolio(cash=1000.0)
    p.rebalance_to(0.5, 100.0)
    assert p.position_value(100.0) == pytest.approx(500.0, abs=1.0)


def test_rebalance_with_commission_no_negative_cash():
    p = Portfolio(cash=1000.0, commission=0.005)
    p.rebalance_to(1.0, 100.0)
    assert p.cash >= -1e-9
