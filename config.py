"""
Вся конфигурация — из переменных окружения / .env. Имена переменных заданы ТЗ.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# --- OpenWeatherMap ---
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "")
WEATHER_API_BASE_URL = os.getenv(
    "WEATHER_API_BASE_URL", "https://api.openweathermap.org/data/2.5/forecast"
)
OWM_UNITS = os.getenv("OWM_UNITS", "metric")
OWM_LANG = os.getenv("OWM_LANG", "ru")

# --- Геолокация ---
# Основной (настраиваемый) гео-провайдер. По умолчанию ipapi.co, но можно
# подставить ipinfo.io/json, ip-api.com/json/ и т.д. — парсер в geo.py
# понимает несколько распространённых форматов ответа.
GEO_API_URL = os.getenv("GEO_API_URL", "https://ipapi.co/json/")
GEO_API_FALLBACK_CITY = os.getenv("GEO_API_FALLBACK_CITY", "Moscow")

# --- База данных ---
# DB_URL может быть:
#   - готовым sqlite DSN:                sqlite:///./data/weather.db
#   - шаблоном с плейсхолдерами для других СУБД:
#       postgresql://{user}:{password}@localhost:5432/weather
#     тогда DB_USER/DB_PASSWORD подставляются в шаблон.
DB_URL = os.getenv("DB_URL", "sqlite:///./data/weather.db")
DB_USER = os.getenv("DB_USER", "")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")


def build_database_url() -> str:
    """Собирает финальный SQLAlchemy DSN из DB_URL (+ DB_USER/DB_PASSWORD, если нужны)."""
    if "{user}" in DB_URL or "{password}" in DB_URL:
        return DB_URL.format(user=DB_USER, password=DB_PASSWORD)
    return DB_URL


DATABASE_URL = build_database_url()

# --- Прочее ---
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")  # development | production
OUTPUT_FILE = os.getenv("OUTPUT_FILE", "./output/forecast.md")

# Сколько дней агрегировать: today + (N-1) дней вперёд
FORECAST_DAYS = int(os.getenv("FORECAST_DAYS", "4"))