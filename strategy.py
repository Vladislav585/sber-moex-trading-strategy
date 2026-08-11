"""
Торговая стратегия для SBER на часовом таймфрейме

Использует комбинацию трёх индикаторов:
  - MACD (12, 26, 9) — определяет тренд и моментум
  - RSI (14)         — определяет перекупленность / перепроданность
  - SMA (200)        — трендовый фильтр (глобальный тренд)

Логика сигналов (режим OR — лучший):
  BUY  = (MACD crosses UP  OR  RSI < rsi_buy)  AND  price > SMA200
  SELL = (MACD crosses DOWN OR  RSI > rsi_sell) AND  price < SMA200

Лучшие параметры (2022-01-03 … 2025-06-30):
  RSI(30/70), OR, SMA200, без SL/TP → Return=103.4%, Sharpe=1.78, DD=17.8%

Зависимости: pandas, ta (technical-analysis), requests
"""

import time
from datetime import datetime, timedelta

import pandas as pd
import requests
import ta


class SberStrategy:
    """
    Стратегия для SBER: MACD + RSI + SMA200.

    Пример использования:
        strategy = SberStrategy(rsi_buy=30, rsi_sell=70)
        df = strategy.run_backtest("data/sber_period.csv", "signals.csv")
    """

    def __init__(self,
                 macd_fast: int = 12,
                 macd_slow: int = 26,
                 macd_signal: int = 9,
                 rsi_period: int = 14,
                 rsi_buy: int = 30,
                 rsi_sell: int = 70,
                 sma_period: int = 200,
                 use_trend_filter: bool = True,
                 stop_loss_pct: float = 0.0,
                 take_profit_pct: float = 0.0,
                 use_or_logic: bool = True):
        """
        Параметры стратегии:
            macd_fast / macd_slow / macd_signal — периоды MACD
            rsi_period       — период RSI
            rsi_buy          — уровень "перепроданности" (RSI ниже = покупаем)
            rsi_sell         — уровень "перекупленности" (RSI выше = продаём)
            sma_period       — период SMA для трендового фильтра
            use_trend_filter — True = торговать только по тренду (SMA200)
            stop_loss_pct    — стоп-лосс в % (0 = отключён)
            take_profit_pct  — тейк-профит в % (0 = отключён)
            use_or_logic     — True = OR-логика, False = AND-логика
        """
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
        self.rsi_period = rsi_period
        self.rsi_buy = rsi_buy
        self.rsi_sell = rsi_sell
        self.sma_period = sma_period
        self.use_trend_filter = use_trend_filter
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.use_or_logic = use_or_logic

    # 1. РАСЧЁТ ИНДИКАТОРОВ
    def add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Добавить к DataFrame колонки с индикаторами:
            macd, macd_signal, macd_diff, rsi, sma200
        """
        df = df.copy()

        # MACD
        macd = ta.trend.MACD(
            df["close"],
            window_fast=self.macd_fast,
            window_slow=self.macd_slow,
            window_sign=self.macd_signal,
        )
        df["macd"] = macd.macd()
        df["macd_signal"] = macd.macd_signal()
        df["macd_diff"] = df["macd"] - df["macd_signal"]  # разница между линиями

        # RSI
        df["rsi"] = ta.momentum.RSIIndicator(
            df["close"],
            window=self.rsi_period,
        ).rsi()

        # SMA (скользящая средняя для трендового фильтра)
        df["sma200"] = ta.trend.SMAIndicator(
            df["close"],
            window=self.sma_period,
        ).sma_indicator()

        return df

    # 2. ГЕНЕРАЦИЯ СИГНАЛОВ (BUY / SELL / HOLD)
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Рассчитать индикаторы и сгенерировать сигналы.

        Возвращает DataFrame с колонкой "signal":
            "BUY"  — сигнал к покупке
            "SELL" — сигнал к продаже
            "HOLD" — держать позицию
        """
        df = self.add_indicators(df)

        # MACD пересечения
        # Берём предыдущие значения для поиска момента пересечения
        df["macd_prev"] = df["macd"].shift(1)
        df["macd_signal_prev"] = df["macd_signal"].shift(1)

        macd_cross_up = (
            (df["macd_prev"] < df["macd_signal_prev"]) &
            (df["macd"] > df["macd_signal"])
        )
        macd_cross_down = (
            (df["macd_prev"] > df["macd_signal_prev"]) &
            (df["macd"] < df["macd_signal"])
        )

        # RSI условия
        rsi_buy_cond = df["rsi"] < self.rsi_buy     # RSI ниже порога → перепродано
        rsi_sell_cond = df["rsi"] > self.rsi_sell   # RSI выше порога → перекуплено

        # Трендовый фильтр (SMA200)
        if self.use_trend_filter:
            trend_up = df["close"] > df["sma200"]    # цена выше SMA → восходящий тренд
            trend_down = df["close"] < df["sma200"]  # цена ниже SMA → нисходящий тренд
        else:
            # Если фильтр отключён — тренд всегда "разрешён"
            trend_up = pd.Series(True, index=df.index)
            trend_down = pd.Series(True, index=df.index)

        # Комбинируем сигналы
        # По умолчанию всё HOLD
        df["signal"] = "HOLD"

        if self.use_or_logic:
            # OR-логика: хотя бы одно условие + трендовый фильтр
            buy_signal = (macd_cross_up | rsi_buy_cond) & trend_up
            sell_signal = (macd_cross_down | rsi_sell_cond) & trend_down
        else:
            # AND-логика: все условия одновременно
            buy_signal = macd_cross_up & rsi_buy_cond & trend_up
            sell_signal = macd_cross_down & rsi_sell_cond & trend_down

        # Ставим сигналы (если одновременно BUY и SELL — ничего не делаем)
        df.loc[buy_signal & ~sell_signal, "signal"] = "BUY"
        df.loc[sell_signal & ~buy_signal, "signal"] = "SELL"

        # Удаляем временные колонки
        df = df.drop(columns=["macd_prev", "macd_signal_prev"])

        return df

    # 3. СТОП-ЛОСС И ТЕЙК-ПРОФИТ
    def apply_sl_tp(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Добавить стоп-лосс и тейк-профит поверх сигналов.

        Логика:
          - После BUY запоминаем цену входа
          - Если LOW свечи ниже SL → ставим SELL
          - Если HIGH свечи выше TP → ставим SELL
          - Если сигнал SELL → закрываем позицию

        Параметры SL/TP задаются при создании стратегии (stop_loss_pct, take_profit_pct).
        """
        # Если SL и TP отключены — ничего не делаем
        if self.stop_loss_pct <= 0 and self.take_profit_pct <= 0:
            return df

        df = df.copy()
        in_position = False
        entry_price = 0.0

        for i in range(len(df)):
            idx = df.index[i]   # индекс текущей строки

            # Открываем позицию на сигнале BUY
            if not in_position and df.loc[idx, "signal"] == "BUY":
                in_position = True
                entry_price = df.loc[idx, "close"]
                continue

            # Если мы в позиции — проверяем SL, TP и сигнал SELL
            if in_position:
                # Стоп-лосс
                if self.stop_loss_pct > 0:
                    sl_price = entry_price * (1 - self.stop_loss_pct / 100)
                    if df.loc[idx, "low"] <= sl_price:
                        df.loc[idx, "signal"] = "SELL"
                        in_position = False
                        continue

                # Тейк-профит
                if self.take_profit_pct > 0:
                    tp_price = entry_price * (1 + self.take_profit_pct / 100)
                    if df.loc[idx, "high"] >= tp_price:
                        df.loc[idx, "signal"] = "SELL"
                        in_position = False
                        continue

                # Обычный сигнал SELL (от стратегии)
                if df.loc[idx, "signal"] == "SELL":
                    in_position = False

        return df

    # 4. БЭКТЕСТ (запуск на исторических данных)
    def run_backtest(self,
                     csv_path: str,
                     output_path: str = "signals.csv",
                     use_sl_tp: bool = True) -> pd.DataFrame:
        """
        Запустить бэктест на исторических данных из CSV-файла.

        Параметры:
            csv_path    — путь к CSV с колонками: datetime, open, high, low, close, volume
            output_path — куда сохранить результат с сигналами
            use_sl_tp   — True = применить стоп-лосс и тейк-профит

        Возвращает: DataFrame с добавленными сигналами и колонками:
            signal, entries, exits
        """
        # Читаем данные
        df = pd.read_csv(csv_path, parse_dates=["datetime"])
        df = df.sort_values("datetime").reset_index(drop=True)

        # Генерируем сигналы
        df = self.generate_signals(df)

        # Применяем SL/TP
        if use_sl_tp:
            df = self.apply_sl_tp(df)

        # Колонки для VectorBT
        df["entries"] = df["signal"] == "BUY"   # True = войти в позицию
        df["exits"] = df["signal"] == "SELL"    # True = выйти из позиции

        # Сохраняем
        df.to_csv(output_path, index=False)

        # Статистика
        total = len(df)
        buys = (df["signal"] == "BUY").sum()
        sells = (df["signal"] == "SELL").sum()

        print(f"  Сигналы: BUY={buys}, SELL={sells}, всего свечей={total}")
        print(f"  Результат сохранён: {output_path}")

        return df

    # 5. РЕЖИМ РЕАЛЬНОГО ВРЕМЕНИ
    def fetch_latest_candles(self, count: int = 250) -> pd.DataFrame:
        """
        Скачать последние N часовых свечей SBER с MOEX.

        Берём данные за последние 60 дней (с запасом), возвращаем последние 'count' свечей.
        """
        today = datetime.now().strftime("%Y-%m-%d")
        sixty_days_ago = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")

        url = (
            "https://iss.moex.com/iss/engines/stock/markets/"
            "shares/boards/TQBR/securities/SBER/candles.json"
        )

        params = {
            "from": sixty_days_ago,
            "till": today,
            "interval": 60,
            "iss.meta": "off",
            "iss.only": "candles",
        }

        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()["candles"]["data"]
        columns = response.json()["candles"]["columns"]

        df = pd.DataFrame(data, columns=columns)
        df = df[["begin", "open", "high", "low", "close", "volume"]].copy()
        df.rename(columns={"begin": "datetime"}, inplace=True)
        df["datetime"] = pd.to_datetime(df["datetime"])

        df = df.sort_values("datetime").drop_duplicates("datetime").reset_index(drop=True)

        return df.tail(count)

    def get_current_signal(self) -> dict:
        """
        Получить текущий сигнал на основе последних данных с MOEX.

        Возвращает словарь с информацией о последней свече и сигнале.
        """
        df = self.fetch_latest_candles(count=250)
        df = self.generate_signals(df)

        last = df.iloc[-1]

        return {
            "datetime": last["datetime"],
            "close": last["close"],
            "macd": round(last["macd"], 4) if pd.notna(last.get("macd")) else None,
            "macd_signal": round(last["macd_signal"], 4) if pd.notna(last.get("macd_signal")) else None,
            "rsi": round(last["rsi"], 2) if pd.notna(last.get("rsi")) else None,
            "sma200": round(last["sma200"], 2) if pd.notna(last.get("sma200")) else None,
            "signal": last["signal"],
        }

    def run_realtime(self, interval_seconds: int = 3600):
        """
        Запустить бесконечный цикл проверки сигналов в реальном времени.

        Каждые interval_seconds секунд:
          1. Скачивает последние данные с MOEX
          2. Рассчитывает индикаторы
          3. Выводит текущий сигнал в консоль

        Для остановки нажми Ctrl+C.
        """
        print("Запуск режима реального времени. Нажми Ctrl+C для остановки.\n")

        while True:
            try:
                result = self.get_current_signal()

                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]")
                print(f"  Последняя свеча: {result['datetime']}")
                print(f"  Цена закрытия:  {result['close']}")
                print(f"  SMA200:         {result['sma200']}")
                print(f"  MACD:           {result['macd']}")
                print(f"  MACD Signal:    {result['macd_signal']}")
                print(f"  RSI:            {result['rsi']}")
                print(f"  >>> СИГНАЛ:     {result['signal']} <<<")
                print("-" * 40)

                time.sleep(interval_seconds)

            except KeyboardInterrupt:
                print("\nОстановлено пользователем.")
                break
            except Exception as e:
                print(f"Ошибка: {e}")
                time.sleep(60)


# Если запустить этот файл напрямую — запустится бэктест
if __name__ == "__main__":
    # Лучшая конфигурация по результатам оптимизации
    strategy = SberStrategy(
        rsi_buy=30,
        rsi_sell=70,
        use_or_logic=True,
        use_trend_filter=True,
        stop_loss_pct=0.0,
        take_profit_pct=0.0,
    )
    strategy.run_backtest(
        csv_path="data/sber_2022-01-03_2025-06-30.csv",
        output_path="data/signals_optimized.csv",
        use_sl_tp=True,
    )