"""
Выгрузка сохранённых в БД данных в Markdown-файл.
Формат — по примеру из ТЗ: заголовок, локация, период, таблица с выровненными
колонками, сортировка по дате (данные уже приходят отсортированными из db.load_forecast).
"""
import os
from typing import List

from config import OUTPUT_FILE
from db import WeatherForecast

COLUMNS = ["Дата", "Мин. темп. (°C)", "Макс. темп. (°C)", "Описание", "Влажность (%)", "Ветер (м/с)"]


def _row_values(row: WeatherForecast) -> List[str]:
    return [
        row.forecast_date.strftime("%Y-%m-%d"),
        f"{row.temp_min:.0f}",
        f"{row.temp_max:.0f}",
        row.description.capitalize(),
        f"{row.humidity}",
        f"{row.wind_speed:.0f}",
    ]


def _render_table(rows: List[WeatherForecast]) -> str:
    data_rows = [_row_values(r) for r in rows]

    # выравнивание колонок по ширине самого длинного значения — чтобы .md
    # читался опрятно и в сыром виде, не только в рендере
    widths = [len(col) for col in COLUMNS]
    for values in data_rows:
        for i, value in enumerate(values):
            widths[i] = max(widths[i], len(value))

    def fmt_row(values: List[str]) -> str:
        cells = [v.ljust(widths[i]) for i, v in enumerate(values)]
        return "| " + " | ".join(cells) + " |"

    header = fmt_row(COLUMNS)
    separator = "|" + "|".join("-" * (w + 2) for w in widths) + "|"
    body = [fmt_row(values) for values in data_rows]

    return "\n".join([header, separator, *body])


def render_markdown(city: str, rows: List[WeatherForecast]) -> str:
    if not rows:
        raise ValueError("Нет данных для выгрузки — БД пуста для этого города")

    period_start = rows[0].forecast_date.strftime("%Y-%m-%d")
    period_end = rows[-1].forecast_date.strftime("%Y-%m-%d")

    lines = [
        "# Прогноз погоды",
        "",
        "Автоматически сформированный отчёт: геолокация по IP → OpenWeatherMap → SQLite → Markdown.",
        "",
        f"Автоматически определённая локация: {city}  ",
        f"Период: {period_start} – {period_end}  ",
        "",
        _render_table(rows),
        "",
    ]
    return "\n".join(lines)


def save_markdown(city: str, rows: List[WeatherForecast], path: str = OUTPUT_FILE) -> str:
    md = render_markdown(city, rows)
    out_dir = os.path.dirname(path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(md)
    return path