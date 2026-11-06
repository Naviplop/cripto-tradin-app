from __future__ import annotations

from typing import List

from domain.entities.account import Account
from domain.entities.position import Position
from domain.entities.trade import Trade


class Portfolio:
    def __init__(self, account: Account) -> None:
        self.account = account
        self.positions: List[Position] = []
        self.trades: List[Trade] = []

    def add_position(self, position: Position) -> None:
        if any(p.id == position.id for p in self.positions if p.id is not None):
            raise ValueError("Position already in portfolio")
        self.positions.append(position)

    def close_position(self, position_id: int, exit_price: float) -> Trade:
        for pos in self.positions:
            if pos.id == position_id:
                pnl = pos.close(Money(exit_price))
                trade = Trade(
                    id=f"TRD-{len(self.trades) + 1:06d}",
                    side=pos.side,
                    entry_price=pos.entry_price,
                    exit_price=pos.close_price or Money(exit_price),
                    quantity=pos.quantity,
                    pnl=pnl,
                )
                self.trades.append(trade)
                self.positions.remove(pos)
                self.account.realize_pnl(pnl)
                return trade
        raise ValueError("Position not found")

    def total_unrealized_pnl(self) -> float:
        return sum(p.unrealized_pnl.to_float() for p in self.positions)

    def total_equity(self) -> float:
        return self.account.total_equity.to_float()
