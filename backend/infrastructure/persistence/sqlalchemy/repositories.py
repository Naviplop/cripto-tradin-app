from __future__ import annotations

from datetime import datetime
from typing import Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from domain.entities.position import Position
from domain.entities.trade import Trade
from domain.value_objects.money import Money
from domain.repositories.interfaces import (
    IAccountRepository,
    ILicenseRepository,
    IMarketDataRepository,
    IModelRepository,
    IPositionRepository,
    ITradeRepository,
)


class Base(DeclarativeBase):
    pass


class AccountSnapshot(Base):
    __tablename__ = "account_snapshots"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    balance: Mapped[float] = mapped_column(nullable=False)
    initial_balance: Mapped[float] = mapped_column(nullable=False)
    total_equity: Mapped[float] = mapped_column(nullable=False)
    timestamp: Mapped[datetime] = mapped_column(default=datetime.now)


class Position(Base):
    __tablename__ = "positions"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    side: Mapped[str] = mapped_column(nullable=False)
    entry_price: Mapped[float] = mapped_column(nullable=False)
    quantity: Mapped[float] = mapped_column(nullable=False)
    tp: Mapped[Optional[float]] = mapped_column(nullable=True)
    sl: Mapped[Optional[float]] = mapped_column(nullable=True)
    unrealized_pnl: Mapped[float] = mapped_column(default=0.0)
    timestamp: Mapped[datetime] = mapped_column(default=datetime.now)


class Trade(Base):
    __tablename__ = "trades"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    side: Mapped[str] = mapped_column(nullable=False)
    entry_price: Mapped[float] = mapped_column(nullable=False)
    exit_price: Mapped[float] = mapped_column(nullable=False)
    quantity: Mapped[float] = mapped_column(nullable=False)
    pnl: Mapped[float] = mapped_column(nullable=False)
    timestamp: Mapped[datetime] = mapped_column(default=datetime.now)


class Prediction(Base):
    __tablename__ = "predictions"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(default=datetime.now)
    score: Mapped[float] = mapped_column(nullable=False)
    signal: Mapped[str] = mapped_column(nullable=False)
    candles_used: Mapped[int] = mapped_column(nullable=False)
    model_loaded: Mapped[bool] = mapped_column(default=False)


class LicenseCache(Base):
    __tablename__ = "license_cache"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    hwid: Mapped[str] = mapped_column(unique=True, nullable=False)
    license_key: Mapped[Optional[str]] = mapped_column(nullable=True)
    valid: Mapped[bool] = mapped_column(default=False)
    expiry: Mapped[Optional[str]] = mapped_column(nullable=True)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.now)


class UnitOfWork:
    def __init__(self, database_url: str) -> None:
        self._engine = create_engine(database_url, future=True)
        self._SessionFactory = sessionmaker(bind=self._engine, autoflush=False, autocommit=False, expire_on_commit=False)
        self._session = None
        self.positions = PositionRepository(self._get_session)
        self.trades = TradeRepository(self._get_session)
        self.accounts = AccountRepository(self._get_session)
        self.models = ModelRepository(self._get_session)
        self.licenses = LicenseRepository(self._get_session)
        self.market = MarketDataRepository(self._get_session)

    def _get_session(self):
        if self._session is None:
            self._session = self._SessionFactory()
        return self._session

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            self.commit()
        else:
            self.rollback()
        self.close()

    def commit(self):
        if self._session is not None:
            self._session.commit()

    def rollback(self):
        if self._session is not None:
            self._session.rollback()

    def close(self):
        if self._session is not None:
            self._session.close()
            self._session = None


class PositionRepository(IPositionRepository):
    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    def add(self, position: Position) -> Position:
        session = self._session_factory()
        orm = Position(
            side=position.side.value,
            entry_price=position.entry_price.to_float(),
            quantity=position.quantity,
            tp=position.tp.to_float() if position.tp else None,
            sl=position.sl.to_float() if position.sl else None,
            unrealized_pnl=position.unrealized_pnl.to_float(),
            timestamp=position.timestamp,
        )
        session.add(orm)
        session.commit()
        session.refresh(orm)
        position.id = orm.id
        session.close()
        return position

    def get_by_id(self, position_id: int) -> Optional[Position]:
        session = self._session_factory()
        orm = session.get(Position, position_id)
        session.close()
        if not orm:
            return None
        return self._to_domain(orm)

    def get_open(self) -> list:
        session = self._session_factory()
        try:
            return [self._to_domain(p) for p in session.query(Position).filter(Position.closed_at == None).all()]
        finally:
            session.close()

    def remove(self, position_id: int) -> None:
        session = self._session_factory()
        orm = session.query(Position).filter(Position.id == position_id).first()
        if orm:
            session.delete(orm)
            session.commit()
        session.close()

    def update_unrealized_pnl(self, position_id: int, unrealized_pnl: Money) -> None:
        session = self._session_factory()
        orm = session.query(Position).filter(Position.id == position_id).first()
        if orm:
            orm.unrealized_pnl = unrealized_pnl.to_float()
            session.commit()
        session.close()

    def _to_domain(self, row) -> Position:
        from domain.value_objects.order_side import OrderSide
        return Position(
            id=row.id,
            side=OrderSide(row.side),
            entry_price=Money(row.entry_price),
            quantity=row.quantity,
            tp=Money(row.tp) if row.tp is not None else None,
            sl=Money(row.sl) if row.sl is not None else None,
            unrealized_pnl=Money(row.unrealized_pnl),
            timestamp=row.timestamp,
        )


class TradeRepository(ITradeRepository):
    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    def save(self, trade: Trade) -> Trade:
        session = self._session_factory()
        orm = Trade(
            side=trade.side.value,
            entry_price=trade.entry_price.to_float(),
            exit_price=trade.exit_price.to_float(),
            quantity=trade.quantity,
            pnl=trade.pnl.to_float(),
            timestamp=trade.timestamp,
        )
        session.add(orm)
        session.commit()
        session.refresh(orm)
        trade.id = str(orm.id)
        session.close()
        return trade

    def get_by_id(self, trade_id: str) -> Optional[Trade]:
        session = self._session_factory()
        orm = session.get(Trade, int(trade_id))
        session.close()
        if not orm:
            return None
        return self._to_domain(orm)

    def list_recent(self, limit: int = 100) -> list:
        session = self._session_factory()
        try:
            orms = session.query(Trade).order_by(Trade.id.desc()).limit(limit).all()
            return [self._to_domain(r) for r in orms]
        finally:
            session.close()

    def _to_domain(self, row) -> Trade:
        return Trade(
            id=str(row.id),
            side=row.side,
            entry_price=Money(row.entry_price),
            exit_price=Money(row.exit_price),
            quantity=row.quantity,
            pnl=Money(row.pnl),
            timestamp=row.timestamp,
        )


class AccountRepository(IAccountRepository):
    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    def save_snapshot(self, balance: Money, initial_balance: Money) -> None:
        session = self._session_factory()
        orm = AccountSnapshot(
            balance=balance.to_float(),
            initial_balance=initial_balance.to_float(),
            total_equity=balance.to_float(),
            timestamp=datetime.now(),
        )
        session.add(orm)
        session.commit()
        session.close()

    def get_latest_snapshot(self) -> Optional[dict]:
        session = self._session_factory()
        try:
            orm = session.query(AccountSnapshot).order_by(AccountSnapshot.id.desc()).first()
            if not orm:
                return None
            return {
                "balance": orm.balance,
                "initial_balance": orm.initial_balance,
                "total_equity": orm.total_equity,
                "timestamp": orm.timestamp.isoformat() if orm.timestamp else None,
            }
        finally:
            session.close()


class ModelRepository(IModelRepository):
    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    def save_prediction(self, score: float, signal: str, candles_used: int, model_loaded: bool) -> None:
        session = self._session_factory()
        orm = Prediction(
            score=score,
            signal=signal,
            candles_used=candles_used,
            model_loaded=model_loaded,
            timestamp=datetime.now(),
        )
        session.add(orm)
        session.commit()
        session.close()

    def get_recent_predictions(self, limit: int = 100) -> list:
        session = self._session_factory()
        try:
            orms = session.query(Prediction).order_by(Prediction.id.desc()).limit(limit).all()
            return [
                {
                    "id": r.id,
                    "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                    "score": r.score,
                    "signal": r.signal,
                    "candles_used": r.candles_used,
                    "model_loaded": bool(r.model_loaded),
                }
                for r in orms
            ]
        finally:
            session.close()


class LicenseRepository(ILicenseRepository):
    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    def get_cached_state(self, hwid: str) -> Optional[dict]:
        session = self._session_factory()
        try:
            orm = session.query(LicenseCache).filter(LicenseCache.hwid == hwid).first()
            if not orm:
                return None
            return {
                "hwid": orm.hwid,
                "license_key": orm.license_key,
                "valid": bool(orm.valid),
                "expiry": orm.expiry,
                "updated_at": orm.updated_at.isoformat() if orm.updated_at else None,
            }
        finally:
            session.close()

    def save_state(self, hwid: str, license_key: str, valid: bool, expiry: Optional[str]) -> None:
        session = self._session_factory()
        orm = session.query(LicenseCache).filter(LicenseCache.hwid == hwid).first()
        if orm:
            orm.license_key = license_key
            orm.valid = valid
            orm.expiry = expiry
            orm.updated_at = datetime.now()
        else:
            orm = LicenseCache(
                hwid=hwid,
                license_key=license_key,
                valid=valid,
                expiry=expiry,
                updated_at=datetime.now(),
            )
            session.add(orm)
        session.commit()
        session.close()


class MarketDataRepository(IMarketDataRepository):
    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    def get_candles(self, symbol: str, interval: str, limit: int) -> list:
        return []

    def get_ticker(self, symbol: str) -> dict:
        return {}

    def get_orderbook(self, symbol: str, limit: int) -> dict:
        return {}
