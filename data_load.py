"""
Загрузка данных с MOEX (Московская биржа)

Две функции:
  1. download_all_sber_1h — скачать ВСЕ часовые свечи SBER
  2. get_period_for_backtest — вырезать нужный период из общего файла

API MOEX: https://iss.moex.com/iss/ — бесплатно, без ключа.
"""

import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests


# Адрес, по которому MOEX отдаёт свечи SBER
CANDLES_URL = (
    "https://iss.moex.com/iss/engines/stock/markets/"
    "shares/boards/TQBR/securities/SBER/candles.json"
)


def download_all_sber_1h(output_file: str = "sber_1h_all.csv",
                         start_date: str = "2000-01-01"):
    """
    Скачать все часовые свечи SBER с MOEX от start_date до сегодня.

    Библиотека 'requests' делает запросы по одной странице (пагинация),
    пока MOEX не вернёт пустой список. Между запросами пауза 0.2 сек.

    Результат: CSV-файл с колонками:
        datetime, open, high, low, close, volume
    """
    all_chunks = []   # сюда собираем куски данных
    offset = 0        # смещение для пагинации
    today = datetime.now().strftime("%Y-%m-%d")

    print(f"Качаю свечи с {start_date} по {today}...")

    while True:
        # Параметры запроса к MOEX
        params = {
            "from": start_date,
            "till": today,
            "interval": 60,         # 60 минут = часовые свечи
            "start": offset,        # смещение (пагинация)
            "iss.meta": "off",      # не возвращать мета-информацию
            "iss.only": "candles",  # только свечи
        }

        # Отправляем запрос
        response = requests.get(CANDLES_URL, params=params, timeout=30)
        response.raise_for_status()                  # проверка на ошибку HTTP
        data = response.json()["candles"]["data"]    # список свечей
        columns = response.json()["candles"]["columns"]  # названия колонок

        # Если MOEX вернул пустой список — данные закончились
        if not data:
            break

        # Превращаем в DataFrame и добавляем в общий список
        chunk = pd.DataFrame(data, columns=columns)
        all_chunks.append(chunk)

        print(f"  Загружено: {offset + len(chunk)} свечей")
        offset += len(chunk)

        # Пауза, чтобы не нагружать сервер MOEX
        time.sleep(0.2)

    # Если не скачалось ни одной свечи — выходим
    if not all_chunks:
        print("Данные не найдены.")
        return

    # Склеиваем все куски в один DataFrame
    df = pd.concat(all_chunks, ignore_index=True)

    # Оставляем только нужные колонки и переименовываем
    df = df[["begin", "open", "high", "low", "close", "volume"]].copy()
    df.rename(columns={"begin": "datetime"}, inplace=True)

    # Превращаем строки с датами в datetime
    df["datetime"] = pd.to_datetime(df["datetime"])

    # Сортируем по дате и удаляем дубликаты
    df = df.sort_values("datetime").drop_duplicates("datetime").reset_index(drop=True)

    # Создаём папку data/ и сохраняем
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_file, index=False)

    print(f"\nГотово! Сохранено в {output_file}")
    print(f"Всего свечей: {len(df)}")
    print(f"Период: {df['datetime'].iloc[0]}  →  {df['datetime'].iloc[-1]}")


def get_period_for_backtest(input_file: str,
                            date_from: str,
                            date_to: str,
                            output_file: str = None):
    """
    Вырезать из большого CSV-файла свечи за указанный период.

    Параметры:
        input_file  — откуда читать (например, "data/sber_1h_all.csv")
        date_from   — начало периода (например, "2022-01-03")
        date_to     — конец периода (например, "2025-06-30")
        output_file — куда сохранить (если None — не сохраняет, только возвращает)

    Возвращает: DataFrame с отфильтрованными данными.
    """
    # Читаем файл
    df = pd.read_csv(input_file, parse_dates=["datetime"])

    # Превращаем строки в datetime
    date_from = pd.to_datetime(date_from)
    date_to = pd.to_datetime(date_to) + pd.Timedelta(days=1)  # включаем последний день

    # Фильтруем строки по дате
    mask = (df["datetime"] >= date_from) & (df["datetime"] < date_to)
    result = df[mask].copy()

    # Сортируем и сбрасываем индексы
    result = result.sort_values("datetime").reset_index(drop=True)

    # Если указан output_file — сохраняем
    if output_file:
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        result.to_csv(output_file, index=False)
        print(f"  Период сохранён: {output_file}")

    # Печатаем статистику
    print(f"  Найдено свечей: {len(result)}")
    if len(result) > 0:
        print(f"  Период: {result['datetime'].iloc[0]}  →  {result['datetime'].iloc[-1]}")

    return result


# Если запустить этот файл напрямую — скачает данные и вырежет период
if __name__ == "__main__":
    # 1. Качаем всю историю
    download_all_sber_1h("data/sber_1h_all.csv")

    # 2. Вырезаем тестовый период
    get_period_for_backtest(
        input_file="data/sber_1h_all.csv",
        date_from="2024-01-01",
        date_to="2024-06-30",
        output_file="data/sber_backtest_period.csv",
    )