"""
Получение прогноза с OpenWeatherMap (эндпоинт /data/2.5/forecast — бесплатный
тариф, 5 дней по 3-часовым интервалам, 40 точек) и агрегация в прогноз по дням
(today + 3 дня по умолчанию), по формулам из ТЗ:
  - temp_min = min(main.temp_min) за день
  - temp_max = max(main.temp_max) за день
  - humidity = mean(main.humidity) за день, округлено до целого
  - wind_speed = max(wind.speed) за день
  - description = самое частое описание за день (тай-брейк — ближе к полудню)
"""
import logging
from collections import defaultdict, Counter
from dataclasses import dataclass
from datetime import datetime, date
from statistics import mean
from typing import List

import requests

from config import WEATHER_API_KEY, WEATHER_API_BASE_URL, OWM_UNITS, OWM_LANG, FORECAST_DAYS
from geo import Location

logger = logging.getLogger(__name__)


class WeatherAPIError(Exception):
    """Любая проблема с получением/разбором прогноза — сеть, ключ, город, лимиты, формат."""


@dataclass
class DayForecast:
    forecast_date: date
    temp_min: float
    temp_max: float
    humidity: int
    wind_speed: float
    description: str
    points_count: int


def fetch_raw_forecast(location: Location) -> dict:
    if not WEATHER_API_KEY:
        raise WeatherAPIError(
            "Не задан WEATHER_API_KEY в переменных окружения. "
            "Получи бесплатный ключ на https://openweathermap.org/api и положи в .env"
        )

    params = {
        "appid": WEATHER_API_KEY,
        "units": OWM_UNITS,
        "lang": OWM_LANG,
    }
    if location.has_coords:
        params["lat"] = location.lat
        params["lon"] = location.lon
    else:
        # координат нет (сработал env-fallback по городу) — ищем по названию
        params["q"] = location.city

    try:
        resp = requests.get(WEATHER_API_BASE_URL, params=params, timeout=10)
    except requests.exceptions.Timeout as exc:
        raise WeatherAPIError("Таймаут запроса к OpenWeatherMap") from exc
    except requests.exceptions.RequestException as exc:
        raise WeatherAPIError(f"OpenWeatherMap недоступен: {exc}") from exc

    try:
        data = resp.json()
    except ValueError as exc:
        raise WeatherAPIError(f"Не удалось разобрать JSON от OpenWeatherMap: {exc}") from exc

    cod = str(data.get("cod", resp.status_code))
    if cod == "401":
        raise WeatherAPIError("Неверный или неактивированный WEATHER_API_KEY (401)")
    if cod == "404":
        raise WeatherAPIError(f"Город не найден на OpenWeatherMap (404): {location.city}")
    if resp.status_code == 429 or cod == "429":
        raise WeatherAPIError("Превышен лимит запросов к OpenWeatherMap (429 Too Many Requests)")
    if resp.status_code != 200 or cod != "200":
        raise WeatherAPIError(f"OpenWeatherMap вернул ошибку (cod={cod}): {data}")

    if "list" not in data or not data["list"]:
        raise WeatherAPIError(f"Пустой список точек прогноза в ответе OpenWeatherMap: {data}")

    return data


def _pick_description(points: List[dict]) -> str:
    """Самое частое описание за день; при ничьей — из точки ближе всего к 12:00."""
    descriptions = [p["weather"][0]["description"] for p in points]
    counts = Counter(descriptions)
    top_count = max(counts.values())
    candidates = {d for d, c in counts.items() if c == top_count}

    if len(candidates) == 1:
        return next(iter(candidates))

    best_point = min(
        (p for p in points if p["weather"][0]["description"] in candidates),
        key=lambda p: abs(datetime.fromtimestamp(p["dt"]).hour - 12),
    )
    return best_point["weather"][0]["description"]


def aggregate_by_day(raw: dict, days_limit: int = FORECAST_DAYS) -> List[DayForecast]:
    buckets: dict[date, list[dict]] = defaultdict(list)
    for point in raw["list"]:
        dt = datetime.fromtimestamp(point["dt"])
        buckets[dt.date()].append(point)

    sorted_days = sorted(buckets.keys())[:days_limit]

    result: List[DayForecast] = []
    for day in sorted_days:
        points = buckets[day]

        temp_mins = [p["main"]["temp_min"] for p in points]
        temp_maxs = [p["main"]["temp_max"] for p in points]
        humidity_values = [p["main"]["humidity"] for p in points]
        wind_speeds = [p["wind"]["speed"] for p in points]

        result.append(
            DayForecast(
                forecast_date=day,
                temp_min=round(min(temp_mins), 1),
                temp_max=round(max(temp_maxs), 1),
                humidity=round(mean(humidity_values)),
                wind_speed=round(max(wind_speeds), 1),
                description=_pick_description(points),
                points_count=len(points),
            )
        )
    return result


def get_forecast(location: Location) -> List[DayForecast]:
    raw = fetch_raw_forecast(location)
    return aggregate_by_day(raw)