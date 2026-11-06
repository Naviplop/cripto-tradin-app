from __future__ import annotations

from domain.repositories.interfaces import IAccountRepository


class GetAccountBalanceHandler:
    def __init__(self, account_repo: IAccountRepository) -> None:
        self._account_repo = account_repo

    async def handle(self, query: GetAccountBalanceQuery) -> dict:
        snapshot = self._account_repo.get_latest_snapshot()
        if snapshot:
            query.result = {
                "balance": snapshot["balance"],
                "initial_balance": snapshot["initial_balance"],
                "total_equity": snapshot["total_equity"],
                "positions_count": 0,
            }
        else:
            query.result = {
                "balance": 10000.0,
                "initial_balance": 10000.0,
                "total_equity": 10000.0,
                "positions_count": 0,
            }
        return query.result
