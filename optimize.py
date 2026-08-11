"""
Оптимизация параметров стратегии SberStrategy

Цель: найти комбинацию параметров RSI и SL/TP, которая даёт:
  - Sharpe Ratio >= 1.0
  - Total Return > 25%

Перебирает 19 комбинаций параметров, запускает VectorBT для каждой
и выводит таблицу результатов, отсортированную по Sharpe Ratio.

Как запустить:
  python optimize.py
  (или установить MODE="optimize" в main.py)
"""

import pandas as pd
import vectorbt as vbt
from strategy import SberStrategy


def main():
    """
    Главная функция оптимизации.

    1. Загружает исторические данные
    2. Перебирает комбинации (rsi_buy, rsi_sell, sl%, tp%)
    3. Для каждой считает метрики через VectorBT
    4. Выводит отсортированную таблицу результатов
    """
    # Загружаем данные
    DATA_FILE = "data/sber_2022-01-03_2025-06-30.csv"
    print(f"Загружаю данные: {DATA_FILE}")
    df_full = pd.read_csv(DATA_FILE, parse_dates=["datetime"])

    # Набор параметров для перебора
    # Каждый кортеж: (rsi_buy, rsi_sell, stop_loss%, take_profit%)
    params = [
        # С SL/TP
        (35, 65, 2.0, 5.0),
        (35, 65, 1.5, 4.0),
        (40, 60, 1.5, 4.0),
        (40, 60, 2.0, 6.0),
        (30, 70, 1.5, 4.0),
        (30, 70, 2.0, 5.0),
        (35, 65, 1.0, 3.0),
        (40, 60, 1.0, 3.0),
        (35, 65, 2.5, 5.0),
        (40, 60, 2.5, 5.0),
        (35, 65, 2.0, 4.0),
        (40, 60, 2.0, 4.0),
        # Более агрессивные
        (35, 65, 1.5, 3.0),
        (40, 60, 1.5, 3.0),
        (30, 70, 1.0, 2.5),
        (35, 65, 1.0, 2.5),
        # Без SL/TP
        (35, 65, 0, 0),
        (40, 60, 0, 0),
        (30, 70, 0, 0),
    ]

    print(f"Перебираю {len(params)} комбинаций параметров...\n")

    results = []

    for rsi_buy, rsi_sell, sl, tp in params:
        # Создаём стратегию с текущими параметрами
        strategy = SberStrategy(
            rsi_buy=rsi_buy,
            rsi_sell=rsi_sell,
            use_or_logic=True,      # OR-логика (лучшая)
            use_trend_filter=True,  # SMA200 фильтр
            stop_loss_pct=sl,
            take_profit_pct=tp,
        )

        # Генерируем сигналы
        df = strategy.generate_signals(df_full.copy())

        # Применяем SL/TP, если они заданы
        if sl > 0 or tp > 0:
            df = strategy.apply_sl_tp(df)

        # Колонки для VectorBT
        df["entries"] = df["signal"] == "BUY"
        df["exits"] = df["signal"] == "SELL"

        # Запускаем VectorBT
        df_idx = df.set_index("datetime")
        portfolio = vbt.Portfolio.from_signals(
            close=df_idx["close"],
            entries=df_idx["entries"],
            exits=df_idx["exits"],
            init_cash=100000,
            fees=0.0005,
            freq="1h",
        )

        # Собираем метрики
        trades_count = portfolio.trades.count()
        if trades_count > 0:
            wins = (portfolio.trades.pnl > 0).sum()
            win_rate = wins / trades_count * 100
        else:
            win_rate = 0

        results.append({
            "rsi_buy": rsi_buy,
            "rsi_sell": rsi_sell,
            "sl%": sl,
            "tp%": tp,
            "Return%": round(portfolio.total_return() * 100, 2),
            "Sharpe": round(portfolio.sharpe_ratio(), 4),
            "DD%": round(portfolio.max_drawdown() * 100, 2),
            "Trades": trades_count,
            "WinRate%": round(win_rate, 1),
        })

    # Сортируем по Sharpe Ratio (от лучшего к худшему)
    results.sort(key=lambda x: x["Sharpe"], reverse=True)

    # Выводим таблицу
    print("РЕЗУЛЬТАТЫ ОПТИМИЗАЦИИ (отсортировано по Sharpe)")
    print("=" * 80)
    header = f"{'rsi_buy':>8} {'rsi_sell':>8} {'sl%':>5} {'tp%':>5} {'Return%':>8} {'Sharpe':>8} {'DD%':>6} {'Trades':>7} {'WinRate%':>8}"
    print(header)
    print("-" * 80)

    for r in results:
        print(
            f"{r['rsi_buy']:>8} "
            f"{r['rsi_sell']:>8} "
            f"{r['sl%']:>5} "
            f"{r['tp%']:>5} "
            f"{r['Return%']:>8} "
            f"{r['Sharpe']:>8} "
            f"{r['DD%']:>6} "
            f"{r['Trades']:>7} "
            f"{r['WinRate%']:>8}"
        )

    # Выводим лучшие комбинации
    print("\n\n=== ЛУЧШИЕ КОМБИНАЦИИ (Sharpe >= 0.9, Return > 20%) ===")
    best = [r for r in results if r["Sharpe"] >= 0.9 and r["Return%"] > 20]
    for r in best:
        print(
            f"RSI({r['rsi_buy']}/{r['rsi_sell']}) "
            f"SL={r['sl%']}% TP={r['tp%']}%  →  "
            f"Return={r['Return%']}%  Sharpe={r['Sharpe']}  "
            f"DD={r['DD%']}%  Trades={r['Trades']}  WinRate={r['WinRate%']}%"
        )


if __name__ == "__main__":
    main()