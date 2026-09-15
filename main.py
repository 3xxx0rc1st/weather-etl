"""
ETL-конвейер: geo → OpenWeatherMap → SQLite (с дедупом) → Markdown (из БД).

Запуск:
    python main.py
"""
import logging
import sys

from config import ENVIRONMENT
from geo import get_location
from weather import get_forecast, WeatherAPIError
from db import init_db, save_forecast, load_forecast
from export_md import save_markdown

logging.basicConfig(
    level=logging.DEBUG if ENVIRONMENT == "development" else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("main")


def run() -> None:
    logger.info("Шаг 1/4: определяю местоположение по IP...")
    location = get_location()
    logger.info(
        "Город: %s (%s), источник: %s",
        location.city,
        f"{location.lat:.4f}, {location.lon:.4f}" if location.has_coords else "координаты неизвестны",
        location.source,
    )

    logger.info("Шаг 2/4: запрашиваю прогноз OpenWeatherMap...")
    try:
        forecasts = get_forecast(location)
    except WeatherAPIError as exc:
        logger.error("Не удалось получить прогноз: %s", exc)
        sys.exit(1)
    logger.info("Получено агрегированных дней: %d", len(forecasts))

    logger.info("Шаг 3/4: инициализирую БД и сохраняю данные (с проверкой дублей)...")
    init_db()
    inserted, skipped = save_forecast(location.city, forecasts)
    logger.info("Вставлено: %d, пропущено как дубликаты: %d", inserted, skipped)

    logger.info("Шаг 4/4: формирую Markdown-отчёт из БД...")
    rows = load_forecast(location.city)
    path = save_markdown(location.city, rows)
    logger.info("Отчёт сохранён: %s", path)

    print(f"\nГотово! Отчёт: {path}")


if __name__ == "__main__":
    run()