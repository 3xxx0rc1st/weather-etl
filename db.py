"""
Слой хранения: SQLAlchemy ORM поверх БД, заданной DATABASE_URL (по умолчанию SQLite).
"""
import logging
import os
from datetime import datetime
from typing import List, Tuple

from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Date, DateTime, UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, sessionmaker

from config import DATABASE_URL
from weather import DayForecast

logger = logging.getLogger(__name__)

Base = declarative_base()


class WeatherForecast(Base):
    __tablename__ = "weather_forecast"
    # защита от дублей и на уровне БД тоже — на случай параллельных запусков
    __table_args__ = (UniqueConstraint("city", "forecast_date", name="uq_city_forecast_date"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    city = Column(String(120), nullable=False)
    forecast_date = Column(Date, nullable=False)
    temp_min = Column(Float, nullable=False)
    temp_max = Column(Float, nullable=False)
    humidity = Column(Integer, nullable=False)
    wind_speed = Column(Float, nullable=False)
    description = Column(String(200), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<WeatherForecast {self.city} {self.forecast_date} {self.temp_min}/{self.temp_max}>"


_engine = None
_SessionFactory = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(DATABASE_URL, echo=False, future=True)
    return _engine


def init_db() -> None:
    """Создаёт директорию под sqlite-файл (если нужно) и таблицы, если их ещё нет."""
    if DATABASE_URL.startswith("sqlite:///"):
        db_file = DATABASE_URL.replace("sqlite:///", "", 1)
        db_dir = os.path.dirname(db_file)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

    engine = get_engine()
    Base.metadata.create_all(engine)
    logger.info("БД инициализирована: %s", DATABASE_URL)


def get_session():
    global _SessionFactory
    if _SessionFactory is None:
        _SessionFactory = sessionmaker(bind=get_engine(), future=True)
    return _SessionFactory()


def save_forecast(city: str, forecasts: List[DayForecast]) -> Tuple[int, int]:
    """
    Вставляет прогноз в БД, пропуская записи, которые уже есть для пары
    (city, forecast_date) — не перезаписываем существующие данные.
    Возвращает (сколько вставлено, сколько пропущено как дубликаты).
    """
    session = get_session()
    inserted = 0
    skipped = 0
    try:
        for f in forecasts:
            exists = (
                session.query(WeatherForecast)
                .filter_by(city=city, forecast_date=f.forecast_date)
                .first()
            )
            if exists:
                logger.info("Пропускаю дубликат: %s / %s уже есть в БД", city, f.forecast_date)
                skipped += 1
                continue

            session.add(
                WeatherForecast(
                    city=city,
                    forecast_date=f.forecast_date,
                    temp_min=f.temp_min,
                    temp_max=f.temp_max,
                    humidity=f.humidity,
                    wind_speed=f.wind_speed,
                    description=f.description,
                )
            )
            inserted += 1

        session.commit()
        logger.info("Вставлено новых записей: %d, пропущено дублей: %d", inserted, skipped)
        return inserted, skipped
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def load_forecast(city: str) -> List[WeatherForecast]:
    """Читает все сохранённые прогнозы по городу, отсортированные по дате — для выгрузки в Markdown."""
    session = get_session()
    try:
        return (
            session.query(WeatherForecast)
            .filter_by(city=city)
            .order_by(WeatherForecast.forecast_date.asc())
            .all()
        )
    finally:
        session.close()