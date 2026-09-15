"""
Определение местоположения по IP.

Порядок попыток:
  1. GEO_API_URL (настраивается через .env, по умолчанию https://ipapi.co/json/)
     — парсер понимает несколько распространённых форматов ответа
     (city/latitude/longitude, city/lat/lon, city/loc="lat,lon", cityName/latitude/longitude).
  2. ipinfo.io    — GET https://ipinfo.io/json
  3. ip-api.com   — GET http://ip-api.com/json/  (лимит 45 req/min)
  4. freeipapi.com — GET https://freeipapi.com/api/json/
  5. Fallback: город из GEO_API_FALLBACK_CITY, координаты неизвестны —
     в этом случае прогноз запрашивается по имени города (q={city}), а не по lat/lon.
"""
import logging
from dataclasses import dataclass
from typing import Optional

import requests

from config import GEO_API_URL, GEO_API_FALLBACK_CITY

logger = logging.getLogger(__name__)

TIMEOUT = 5  # секунд на запрос


@dataclass
class Location:
    city: str
    lat: Optional[float]
    lon: Optional[float]
    source: str

    @property
    def has_coords(self) -> bool:
        return self.lat is not None and self.lon is not None


def _parse_generic(data: dict) -> tuple[str, float, float]:
    """Пытается вытащить city/lat/lon из разных известных форматов ответа гео-API."""
    city = data.get("city") or data.get("cityName")

    lat = data.get("latitude", data.get("lat"))
    lon = data.get("longitude", data.get("lon"))

    if (lat is None or lon is None) and "loc" in data:
        # формат ipinfo.io: "loc": "55.7558,37.6176"
        lat_str, lon_str = str(data["loc"]).split(",")
        lat, lon = lat_str, lon_str

    if not city or lat is None or lon is None:
        raise ValueError("в ответе нет city/координат в известном формате")

    return city, float(lat), float(lon)


def _try_configured_geo_api() -> Location:
    resp = requests.get(GEO_API_URL, timeout=TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    city, lat, lon = _parse_generic(data)
    return Location(city=city, lat=lat, lon=lon, source=GEO_API_URL)


def _try_ipinfo() -> Location:
    resp = requests.get("https://ipinfo.io/json", timeout=TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    city, lat, lon = _parse_generic(data)
    return Location(city=city, lat=lat, lon=lon, source="ipinfo.io")


def _try_ip_api() -> Location:
    resp = requests.get("http://ip-api.com/json/", timeout=TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    if data.get("status") != "success":
        raise ValueError(f"ip-api.com: status={data.get('status')}, msg={data.get('message')}")
    city, lat, lon = _parse_generic(data)
    return Location(city=city, lat=lat, lon=lon, source="ip-api.com")


def _try_freeipapi() -> Location:
    resp = requests.get("https://freeipapi.com/api/json/", timeout=TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    city, lat, lon = _parse_generic(data)
    return Location(city=city, lat=lat, lon=lon, source="freeipapi.com")


def _fallback() -> Location:
    logger.warning(
        "Все гео-API недоступны или вернули некорректные данные — "
        "использую GEO_API_FALLBACK_CITY=%s (координаты неизвестны, "
        "прогноз будет запрошен по имени города)",
        GEO_API_FALLBACK_CITY,
    )
    return Location(city=GEO_API_FALLBACK_CITY, lat=None, lon=None, source="env-fallback")


def get_location() -> Location:
    """
    Пытается определить местоположение по цепочке провайдеров.
    Никогда не бросает исключение наружу — в худшем случае вернёт fallback по городу.
    """
    providers = (_try_configured_geo_api, _try_ipinfo, _try_ip_api, _try_freeipapi)

    for provider in providers:
        try:
            location = provider()
            logger.info("Геолокация определена через %s: %s", location.source, location.city)
            return location
        except requests.exceptions.Timeout:
            logger.warning("%s: таймаут запроса", provider.__name__)
        except requests.exceptions.RequestException as exc:
            logger.warning("%s недоступен: %s", provider.__name__, exc)
        except (ValueError, KeyError, TypeError) as exc:
            logger.warning("%s вернул некорректные данные: %s", provider.__name__, exc)

    return _fallback()