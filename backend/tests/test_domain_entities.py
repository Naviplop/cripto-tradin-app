from __future__ import annotations

from decimal import Decimal

import pytest

from domain.entities.account import Account
from domain.entities.order import Order, OrderSide, OrderType
from domain.entities.portfolio import Portfolio
from domain.entities.position import Position
from domain.entities.trade import Trade
from domain.value_objects.leverage import Leverage
from domain.value_objects.money import Money
from domain.value_objects.order_side import OrderSide as OSSide
from domain.value_objects.order_type import OrderType as OTType
from domain.value_objects.order_status import OrderStatus
from domain.value_objects.risk_params import RiskParams
from domain.value_objects.time_in_force import TimeInForce


def test_money_add_sub():
    a = Money("10.5")
    b = Money("2.5")
    assert (a + b).to_float() == 13.0
    assert (a - b).to_float() == 8.0


def test_money_mul_div():
    m = Money("10.0")
    assert (m * 2).to_float() == 20.0
    assert (m / 2).to_float() == 5.0


def test_money_currency_mismatch_raises():
    usd = Money("1.0", "USDT")
    eur = Money("1.0", "EUR")
    with pytest.raises(ValueError):
        usd + eur


def test_money_invalid_amount_raises():
    with pytest.raises((ValueError, Exception)):
        Money("not-a-number")


def test_leverage_valid():
    lev = Leverage(10)
    assert lev.value == 10


def test_leverage_invalid_type_raises():
    with pytest.raises(TypeError):
        Leverage("10")


def test_leverage_negative_raises():
    with pytest.raises(ValueError):
        Leverage(-1)


def test_account_deposit_and_withdraw():
    acc = Account(balance=Money("100.0"), initial_balance=Money("100.0"))
    acc.deposit(Money("50.0"))
    assert acc.balance.to_float() == 150.0
    acc.withdraw(Money("30.0"))
    assert acc.balance.to_float() == 120.0


def test_account_withdraw_currency_mismatch_raises():
    acc = Account(balance=Money("100.0"), initial_balance=Money("100.0"))
    eur = Money("10.0", "EUR")
    with pytest.raises(ValueError):
        acc.withdraw(eur)


def test_account_realize_pnl():
    acc = Account(balance=Money("100.0"), initial_balance=Money("100.0"))
    acc.realize_pnl(Money("15.0"))
    assert acc.balance.to_float() == 115.0


def test_portfolio_total_equity():
    acc = Account(balance=Money("1000.0"), initial_balance=Money("1000.0"))
    p = Portfolio(account=acc)
    assert p.total_equity() == 1000.0


def test_trade_defaults():
    t = Trade(id="TRD-1", side=OrderSide.BUY, entry_price=100.0, exit_price=110.0, quantity=1.0, pnl=10.0)
    assert t.pnl == 10.0


def test_order_status_enum():
    assert OrderStatus.PENDING.value == "PENDING"
    assert OrderStatus.FILLED.value == "FILLED"


def test_order_side_enum():
    assert OSSide.BUY.value == "BUY"
    assert OSSide.SELL.value == "SELL"


def test_order_type_enum():
    assert OTType.MARKET.value == "MARKET"
    assert OTType.LIMIT.value == "LIMIT"


def test_time_in_force_enum():
    assert TimeInForce.GTC.value == "GTC"
    assert TimeInForce.IOC.value == "IOC"


def test_risk_params_valid():
    rp = RiskParams(max_position_size_usdt=1000.0, max_drawdown_pct=0.5, max_open_positions=5)
    assert rp.max_position_size_usdt == 1000.0
    assert rp.max_drawdown_pct == 0.5
    assert rp.max_open_positions == 5


def test_risk_params_invalid_drawdown_raises():
    with pytest.raises(ValueError):
        RiskParams(max_position_size_usdt=1000.0, max_drawdown_pct=0.0, max_open_positions=5)


def test_risk_params_invalid_position_size_raises():
    with pytest.raises(ValueError):
        RiskParams(max_position_size_usdt=-1.0, max_drawdown_pct=0.5, max_open_positions=5)


def test_risk_params_invalid_open_positions_raises():
    with pytest.raises(ValueError):
        RiskParams(max_position_size_usdt=1000.0, max_drawdown_pct=0.5, max_open_positions=0)
