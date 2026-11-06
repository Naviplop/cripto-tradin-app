from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pytest

from domain.entities.account import Account
from domain.entities.order import OrderSide
from domain.entities.portfolio import Portfolio
from domain.entities.position import Position
from domain.value_objects.money import Money


def test_position_is_open_initially():
    pos = Position(id=1, side=OrderSide.BUY, entry_price=Money(100.0), quantity=1.0)
    assert pos.is_open() is True


def test_position_close_sets_fields():
    pos = Position(id=1, side=OrderSide.BUY, entry_price=Money(100.0), quantity=1.0)
    exit_price = Money(110.0)
    pnl = pos.close(exit_price)
    assert pos.closed_at is not None
    assert pos.close_price == exit_price
    assert pos.realized_pnl == pnl
    assert pnl == Money(10.0)


def test_position_close_short():
    pos = Position(id=1, side=OrderSide.SELL, entry_price=Money(100.0), quantity=1.0)
    exit_price = Money(90.0)
    pnl = pos.close(exit_price)
    assert pnl == Money(10.0)


def test_position_close_already_closed_raises():
    pos = Position(id=1, side=OrderSide.BUY, entry_price=Money(100.0), quantity=1.0)
    pos.close(Money(110.0))
    with pytest.raises(ValueError):
        pos.close(Money(120.0))


def test_position_update_unrealized_pnl_long():
    pos = Position(id=1, side=OrderSide.BUY, entry_price=Money(100.0), quantity=1.0)
    pnl = pos.update_unrealized_pnl(Money(110.0))
    assert pnl == Money(10.0)


def test_position_update_unrealized_pnl_short():
    pos = Position(id=1, side=OrderSide.SELL, entry_price=Money(100.0), quantity=1.0)
    pnl = pos.update_unrealized_pnl(Money(90.0))
    assert pnl == Money(10.0)


def test_portfolio_add_duplicate_position_raises():
    acc = Account(balance=Money("1000.0"), initial_balance=Money("1000.0"))
    port = Portfolio(account=acc)
    pos = Position(id=1, side=OrderSide.BUY, entry_price=Money(100.0), quantity=1.0)
    port.add_position(pos)
    with pytest.raises(ValueError):
        port.add_position(pos)


def test_portfolio_close_position_not_found_raises():
    acc = Account(balance=Money("1000.0"), initial_balance=Money("1000.0"))
    port = Portfolio(account=acc)
    with pytest.raises(ValueError):
        port.close_position(999, 110.0)


def test_portfolio_total_unrealized_pnl():
    acc = Account(balance=Money("1000.0"), initial_balance=Money("1000.0"))
    port = Portfolio(account=acc)
    pos = Position(id=1, side=OrderSide.BUY, entry_price=Money(100.0), quantity=1.0)
    port.add_position(pos)
    pos.update_unrealized_pnl(Money(110.0))
    assert port.total_unrealized_pnl() == 10.0


def test_portfolio_total_equity():
    acc = Account(balance=Money("1000.0"), initial_balance=Money("1000.0"))
    port = Portfolio(account=acc)
    assert port.total_equity() == 1000.0


def test_money_is_positive_negative():
    m = Money("10.0")
    assert m.is_positive() is True
    assert m.is_negative() is False
    n = Money("-5.0")
    assert n.is_positive() is False
    assert n.is_negative() is True


def test_money_equality_and_hash():
    a = Money("10.0")
    b = Money("10.0")
    assert a == b
    assert hash(a) == hash(b)
