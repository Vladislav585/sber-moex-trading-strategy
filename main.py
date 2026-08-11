"""
EasyProject — Торговая стратегия для акций Сбербанка (SBER)

Часовой таймфрейм, индикаторы: MACD + RSI + SMA200.

Режимы работы (переменная MODE):
  - download  — скачать историю с MOEX
  - backtest  — запустить бэктест на заданном периоде
  - realtime  — получать сигналы в реальном времени
  - optimize  — подобрать лучшие параметры стратегии

Как запустить:
  1. Установить MODE = "download", запустить: python main.py
  2. Установить MODE = "backtest", запустить: python main.py
  3. Поменять DATE_FROM / DATE_TO / CASH / FEES под себя
"""

from data_load import download_all_sber_1h, get_period_for_backtest
from strategy import SberStrategy
import pandas as pd
import vectorbt as vbt

# НАСТРОЙКИ (меняй под себя)
MODE = "backtest"        # download / backtest / realtime / optimize

DATE_FROM = "2022-01-03" # дата начала бэктеста
DATE_TO = "2025-06-30"   # дата окончания бэктеста
CASH = 100000            # стартовый капитал
FEES = 0.0005            # комиссия (0.05%)
INTERVAL_SECONDS = 3600  # интервал проверки в realtime-режиме (1 час)

# Файлы с данными
ALL_DATA_FILE = "data/sber_1h_all.csv"

# РЕЖИМ: download
def run_download():
    """Скачать все часовые свечи SBER c MOEX и сохранить в CSV."""
    print("Скачиваю исторические данные SBER с MOEX...")
    download_all_sber_1h(ALL_DATA_FILE)
    print("Готово! Данные сохранены в", ALL_DATA_FILE)

# РЕЖИМ: backtest
def run_backtest(date_from: str, date_to: str, cash: float, fees: float):
    """
    Полный цикл бэктеста:
      1. Вырезать нужный период из общего файла
      2. Рассчитать индикаторы и сигналы (BUY / SELL / HOLD)
      3. Запустить VectorBT для расчёта метрик
    """
    # проверяем, есть ли данные
    from pathlib import Path
    if not Path(ALL_DATA_FILE).exists():
        print("Ошибка: нет файла с данными. Сначала запусти MODE='download'")
        return

    # 1. Вырезаем период
    period_file = f"data/sber_{date_from}_{date_to}.csv"
    signals_file = f"data/signals_{date_from}_{date_to}.csv"

    print(f"1. Вырезаю период {date_from} … {date_to}")
    get_period_for_backtest(
        input_file=ALL_DATA_FILE,
        date_from=date_from,
        date_to=date_to,
        output_file=period_file,
    )

    # 2. Создаём стратегию с лучшими параметрами
    strategy = SberStrategy(
        rsi_buy=30,
        rsi_sell=70,
        use_or_logic=True,      # OR-логика: MACD ИЛИ RSI
        use_trend_filter=True,  # SMA200 фильтр
        stop_loss_pct=0.0,      # без стоп-лосса
        take_profit_pct=0.0,    # без тейк-профита
    )

    print("2. Рассчитываю индикаторы и сигналы...")
    df = strategy.run_backtest(csv_path=period_file, output_path=signals_file)

    # 3. Бэктест через VectorBT
    print("3. Запускаю бэктест VectorBT...")
    df_vbt = pd.read_csv(signals_file, parse_dates=["datetime"])
    df_vbt = df_vbt.set_index("datetime")

    portfolio = vbt.Portfolio.from_signals(
        close=df_vbt["close"],
        entries=df_vbt["entries"],           # True на свечах с сигналом BUY
        exits=df_vbt["exits"],               # True на свечах с сигналом SELL
        init_cash=cash,
        fees=fees,
        freq="1h",                           # часовые свечи
    )

    # 4. Выводим результаты
    print("\n" + "=" * 50)
    print("РЕЗУЛЬТАТЫ БЭКТЕСТА")
    print("=" * 50)
    print(portfolio.stats())

    print("\nОсновные метрики:")
    print(f"  Доходность:     {portfolio.total_return():.2%}")
    print(f"  Sharpe Ratio:   {portfolio.sharpe_ratio():.2f}")
    print(f"  Max Drawdown:   {portfolio.max_drawdown():.2%}")
    print(f"  Сделок:         {portfolio.trades.count()}")

    return portfolio

# РЕЖИМ: realtime
def run_realtime(interval_seconds: int):
    """Запуск стратегии в реальном времени. Каждые N секунд проверяет сигнал."""
    strategy = SberStrategy(
        rsi_buy=30,
        rsi_sell=70,
        use_or_logic=True,
        use_trend_filter=True,
    )
    strategy.run_realtime(interval_seconds=interval_seconds)

# РЕЖИМ: optimize
def run_optimize():
    """Запустить оптимизацию параметров стратегии."""
    from optimize import main as optimize_main
    optimize_main()

# ТОЧКА ВХОДА
if __name__ == "__main__":
    print("EasyProject — торговая стратегия SBER (1h)")
    print(f"Режим: {MODE}")
    print("-" * 40)

    if MODE == "download":
        run_download()

    elif MODE == "backtest":
        run_backtest(
            date_from=DATE_FROM,
            date_to=DATE_TO,
            cash=CASH,
            fees=FEES,
        )

    elif MODE == "realtime":
        run_realtime(interval_seconds=INTERVAL_SECONDS)

    elif MODE == "optimize":
        run_optimize()

    else:
        print("Неизвестный режим. Доступно: download / backtest / realtime / optimize")