# weather-etl

ETL на Python: IP-геолокация → прогноз погоды (OpenWeatherMap) → агрегация
по дням → SQLite (с защитой от дублей) → выгрузка в Markdown.

## Архитектура

```
geo.py        → город/координаты по IP: GEO_API_URL → ipinfo.io → ip-api.com → freeipapi.com → GEO_API_FALLBACK_CITY
weather.py    → запрос к OpenWeatherMap (5 дней / 3ч интервалы) + агрегация в DayForecast
db.py         → SQLAlchemy-модель WeatherForecast, запись в БД с дедупом по (city, forecast_date)
export_md.py  → чтение из БД + рендер Markdown-отчёта (таблица с выровненными колонками)
config.py     → вся конфигурация из переменных окружения / .env
main.py       → точка входа, дергает всё по цепочке
```

Поток данных:

```
IP → Location(city, lat?, lon?)
   → OWM forecast (40 точек, 3ч интервалы)
   → агрегация в 4 DayForecast (today + 3 дня)
   → SQLite: weather_forecast (INSERT, дубли по city+forecast_date пропускаются)
   → SELECT по городу, ORDER BY forecast_date
   → output/forecast.md
```

## Установка

```bash
git clone git@github.com:<your-username>/weather-etl.git
cd weather-etl
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Вставь свой `WEATHER_API_KEY` в `.env` — бесплатный ключ без карты:
https://openweathermap.org/api.

## Запуск

```bash
python main.py
```

## Переменные окружения

| Переменная | Назначение | По умолчанию |
|---|---|---|
| `WEATHER_API_KEY` | ключ OpenWeatherMap | — (обязателен) |
| `WEATHER_API_BASE_URL` | базовый URL эндпоинта forecast | `https://api.openweathermap.org/data/2.5/forecast` |
| `GEO_API_URL` | основной гео-провайдер | `https://ipapi.co/json/` |
| `GEO_API_FALLBACK_CITY` | резервный город | `Moscow` |
| `DB_URL` | DSN БД (sqlite или шаблон с `{user}`/`{password}`) | `sqlite:///./data/weather.db` |
| `DB_USER` / `DB_PASSWORD` | учётные данные для не-sqlite `DB_URL` | — |
| `ENVIRONMENT` | `development` / `production` — влияет на уровень логов | `development` |
| `OUTPUT_FILE` | путь для Markdown-отчёта | `./output/forecast.md` |
| `FORECAST_DAYS` | сколько дней агрегировать (today + N-1) | `4` |

## Схема БД (`weather_forecast`)

| Поле | Тип | Описание |
|---|---|---|
| `id` | Integer, PK | автоинкрементный идентификатор |
| `city` | String | название города |
| `forecast_date` | Date | дата прогноза |
| `temp_min` | Float | минимальная температура, °C |
| `temp_max` | Float | максимальная температура, °C |
| `humidity` | Integer | средняя влажность, % |
| `wind_speed` | Float | максимальная скорость ветра, м/с |
| `description` | String | описание погоды |
| `created_at` | DateTime | время записи в БД |
