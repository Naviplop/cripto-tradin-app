from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Depends, FastAPI, Request

from config.settings import Settings, get_settings
from domain.repositories.interfaces import (
    IAccountRepository,
    ILicenseRepository,
    IMarketDataRepository,
    IModelRepository,
    IPositionRepository,
    ITradeRepository,
)
from domain.services import RiskEngine
from infrastructure.persistence.sqlalchemy.unit_of_work import UnitOfWork, create_session_factory


def get_settings_dep() -> Settings:
    return get_settings()


def get_unit_of_work(request: Request) -> UnitOfWork:
    uow_factory = request.app.state.uow_factory
    return UnitOfWork(uow_factory)


async def get_trade_repository(uow: UnitOfWork = ...) -> AsyncGenerator:
    from infrastructure.persistence.sqlalchemy.repositories import SqlAlchemyTradeRepository
    yield SqlAlchemyTradeRepository(uow)


async def get_position_repository(uow: UnitOfWork = ...) -> AsyncGenerator:
    from infrastructure.persistence.sqlalchemy.repositories import SqlAlchemyPositionRepository
    yield SqlAlchemyPositionRepository(uow)


async def get_license_repository(uow: UnitOfWork = ...) -> AsyncGenerator:
    from infrastructure.persistence.sqlalchemy.repositories import SqlAlchemyLicenseRepository
    yield SqlAlchemyLicenseRepository(uow)


async def get_market_data_repository() -> AsyncGenerator:
    from infrastructure.persistence.sqlalchemy.repositories import SqlAlchemyMarketDataRepository
    yield SqlAlchemyMarketDataRepository()


async def get_model_repository(uow: UnitOfWork = ...) -> AsyncGenerator:
    from infrastructure.persistence.sqlalchemy.repositories import SqlAlchemyModelRepository
    yield SqlAlchemyModelRepository(uow)


async def get_account_repository(uow: UnitOfWork = ...) -> AsyncGenerator:
    from infrastructure.persistence.sqlalchemy.repositories import SqlAlchemyAccountRepository
    yield SqlAlchemyAccountRepository(uow)


def get_risk_engine() -> RiskEngine:
    from domain.services.risk_engine import RiskEngine
    
    class DefaultRiskEngine(RiskEngine):
        def validate_order(self, order, positions, balance):
            violations = []
            if order.quantity <= 0:
                violations.append("Quantity must be positive")
            return violations

        def compute_position_size(self, balance, entry_price, risk_params):
            return 0.0

        def check_drawdown(self, initial_balance, current_balance):
            return current_balance < initial_balance * 0.5

    return DefaultRiskEngine()
