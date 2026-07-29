from __future__ import annotations

from datetime import datetime, timezone

import pytest

from domain.events.domain_event import DomainEvent
from domain.events.license_validated import LicenseValidated
from domain.events.market_data_received import MarketDataReceived
from domain.events.order_filled import OrderFilled
from domain.events.order_placed import OrderPlaced
from domain.events.position_closed import PositionClosed


def test_domain_event_event_name():
    class SampleEvent(DomainEvent):
        pass
    assert SampleEvent().event_name == "SampleEvent"


def test_license_validated_event():
    evt = LicenseValidated(hwid="abc123", valid=True)
    assert evt.hwid == "abc123"
    assert evt.valid is True
    assert evt.event_name == "LicenseValidated"


def test_market_data_received_event():
    ts = datetime(2023, 1, 1, tzinfo=timezone.utc)
    evt = MarketDataReceived(symbol="BTCUSDT", timestamp=ts, close=50000.0, volume=10.0)
    assert evt.symbol == "BTCUSDT"
    assert evt.close == 50000.0
    assert evt.event_name == "MarketDataReceived"


def test_order_placed_event():
    evt = OrderPlaced(order_id="ORD-1", side="BUY", order_type="MARKET", quantity=1.0, price=100.0)
    assert evt.order_id == "ORD-1"
    assert evt.side == "BUY"
    assert evt.event_name == "OrderPlaced"


def test_order_filled_event():
    evt = OrderFilled(order_id="ORD-1", filled_price=100.0, quantity=1.0)
    assert evt.order_id == "ORD-1"
    assert evt.quantity == 1.0
    assert evt.event_name == "OrderFilled"


def test_position_closed_event():
    evt = PositionClosed(position_id=1, pnl=10.0, exit_price=110.0)
    assert evt.position_id == 1
    assert evt.pnl == 10.0
    assert evt.event_name == "PositionClosed"
