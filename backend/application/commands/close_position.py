from __future__ import annotations

from typing import List

from domain.entities.account import Account
from domain.entities.portfolio import Portfolio
from domain.events.license_validated import LicenseValidated
from domain.repositories.interfaces import (
    IAccountRepository,
    ILicenseRepository,
    IModelRepository,
    IPositionRepository,
    ITradeRepository,
)
from domain.value_objects.money import Money


class ClosePositionCommand:
    def __init__(self, position_id: int, exit_price: float) -> None:
        self.position_id = position_id
        self.exit_price = exit_price
        self.trade_id: int | None = None
        self.pnl: float = 0.0
        self.error: str | None = None


class ClosePositionHandler:
    def __init__(
        self,
        license_repo: ILicenseRepository,
        account_repo: IAccountRepository,
        position_repo: IPositionRepository,
        trade_repo: ITradeRepository,
    ) -> None:
        self._license_repo = license_repo
        self._account_repo = account_repo
        self._position_repo = position_repo
        self._trade_repo = trade_repo

    async def handle(self, command: ClosePositionCommand, portfolio: Portfolio) -> int | None:
        try:
            trade = portfolio.close_position(command.position_id, command.exit_price)
            command.pnl = trade.pnl.to_float()
            command.trade_id = trade.id
            self._account_repo.save_snapshot(portfolio.account.balance, portfolio.account.initial_balance)
            return trade.id
        except ValueError as exc:
            command.error = str(exc)
            return None
