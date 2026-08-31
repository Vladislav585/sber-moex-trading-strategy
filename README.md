# 📈 EasyProject — Торговая стратегия для акций Сбербанка (SBER)

> **Languages:** [🇷🇺 Русский](#russian-version) | [🇺🇸 English](#english-version)

Алгоритмическая торговая стратегия для акций **Сбербанка (SBER)** на часовом таймфрейме (**1h**).  
Данные загружаются с **MOEX бесплатно, без API-ключа**.  
Проект поддерживает **бэктест**, **realtime-сигналы** и **оптимизацию параметров**.

---
## 📚 Связь с учебным материалом

Этот проект является практическим продолжением моего учебного материала, который уже опубликован в моём GitHub-аккаунте.  
Он показывает, как идеи из учебника можно применить в реальном мини-проекте: от загрузки биржевых данных до построения, тестирования и оптимизации торговой стратегии.

Если вы пришли сюда из учебника, этот репозиторий можно рассматривать как пример более прикладной реализации описанных подходов.

---
## 🏆 Результаты лучшей стратегии

> Период тестирования: **2022-01-03 — 2025-06-30** | Стартовый капитал: **100 000 ₽** | Комиссия: **0.05%**

| Настройки | Доходность | Sharpe Ratio | Макс. просадка |
|-----------|------------|--------------|----------------|
| **RSI(30/70), OR-логика, SMA200, без SL/TP** | **103.4%** | **1.78** | **17.8%** |
| RSI(35/65), OR-логика, SMA200, SL=1.5%, TP=4% | 60.3% | 1.56 | 18.9% |

---

## ⚙️ Возможности

- 📥 Загрузка исторических часовых свечей SBER с **MOEX** (с 2000 года по сегодня)
- 📊 Бэктест стратегии на любом выбранном периоде
- ⚡ Realtime-режим: сигналы каждые N секунд
- 🔍 Оптимизация параметров RSI / Stop Loss / Take Profit
- 🧮 Индикаторы: **MACD**, **RSI**, **SMA200**
- 💾 Сохранение данных и сигналов в **CSV**

---

## 🛠 Стек технологий

| Библиотека | Назначение |
|-----------|------------|
| `pandas` | Работа с таблицами, чтение/запись CSV |
| `requests` | HTTP-запросы к API MOEX |
| `ta` | Расчёт индикаторов: MACD, RSI, SMA |
| `vectorbt` | Профессиональный бэктест и метрики |

---

## 📁 Структура проекта

```bash
EasyProject/
├── main.py              # Точка входа: выбор режима работы
├── data_load.py         # Загрузка данных с MOEX
├── strategy.py          # Торговая стратегия (MACD + RSI + SMA200)
├── optimize.py          # Оптимизация параметров стратегии
├── docs/
│   └── explanation.md   # Подробное описание проекта
└── data/
    ├── sber_1h_all.csv                  # Все исторические свечи
    ├── sber_<дата>_<дата>.csv           # Вырезка периода (бэктест)
    └── signals_<дата>_<дата>.csv        # Сигналы (бэктест)
```

---

## 🚀 Установка и запуск

### 1. Клонировать репозиторий

```bash
git clone https://github.com/Vladislav585/sber-moex-trading-strategy.git
cd sber-moex-trading-strategy
```

### 2. Установить зависимости

```bash
pip install pandas requests ta vectorbt
```

---

### 📥 Режим 1: Скачать исторические данные

В `main.py` установить:

```python
MODE = "download"
```

Запуск:

```bash
python main.py
```

Будет скачано **50 000+ свечей** (с 2000 года по сегодня) в файл `data/sber_1h_all.csv`.  
Достаточно сделать один раз.

---

### 📊 Режим 2: Бэктест

В `main.py` установить:

```python
MODE      = "backtest"
DATE_FROM = "2022-01-03"
DATE_TO   = "2025-06-30"
CASH      = 100000
FEES      = 0.0005
```

Запуск:

```bash
python main.py
```

**Что происходит:**
1. Вырезается нужный период → `data/sber_<дата>_<дата>.csv`
2. Рассчитываются сигналы → `data/signals_<дата>_<дата>.csv`
3. Запускается **VectorBT**
4. В консоль выводятся: доходность, Sharpe Ratio, просадка, количество сделок

---

### 🔍 Режим 3: Оптимизация параметров

```bash
python optimize.py
```

Или в `main.py`:

```python
MODE = "optimize"
```

**Что делает:**
- Перебирает **19 комбинаций** параметров RSI, SL и TP
- Считает по каждой: доходность, Sharpe, просадку, Win Rate, количество сделок
- Выводит таблицу, отсортированную по Sharpe Ratio
- Отдельно показывает лучшие конфигурации (Sharpe ≥ 0.9, Return > 20%)

---

### ⚡ Режим 4: Realtime-сигналы

В `main.py` установить:

```python
MODE             = "realtime"
INTERVAL_SECONDS = 3600   # проверять каждый час
```

Запуск:

```bash
python main.py
```

**Что делает:**
- Каждые `N` секунд загружает последние **~250 свечей** с MOEX
- Рассчитывает индикаторы
- Выводит текущий сигнал (`BUY` / `SELL` / `HOLD`) в консоль

---

## 📉 Как работает стратегия

### Индикаторы

| Индикатор | Параметры | Назначение |
|----------|-----------|------------|
| **MACD** | 12 / 26 / 9 | Направление и сила тренда |
| **RSI** | 14 | Перекупленность / перепроданность |
| **SMA200** | 200 | Фильтр глобального тренда |

### Логика сигналов

#### Режим OR (лучший по результатам оптимизации)

```
BUY  = (MACD пересёк сигнальную линию снизу вверх  ИЛИ  RSI < порога_buy)
       И цена выше SMA200

SELL = (MACD пересёк сигнальную линию сверху вниз  ИЛИ  RSI > порога_sell)
       И цена ниже SMA200
```

#### Режим AND (строже)

```
BUY  = MACD пересёк вверх  И  RSI < порога_buy  И  цена выше SMA200
SELL = MACD пересёк вниз   И  RSI > порога_sell  И  цена ниже SMA200
```

> Если `use_trend_filter=False` — фильтр SMA200 отключается.

### Stop Loss / Take Profit (опционально)

```python
stop_loss_pct   = 1.5   # продать, если цена упала на 1.5% от входа
take_profit_pct = 4.0   # продать, если цена выросла на 4% от входа
```

> Значение `0` — защита отключена. Лучший результат показала стратегия **без SL/TP**.

---

## 📋 Формат выходного CSV

После бэктеста создаётся `data/signals_<дата>_<дата>.csv`:

| Колонка | Описание |
|---------|----------|
| `signal` | `BUY`, `SELL` или `HOLD` |
| `entries` | `True` на свечах с сигналом **BUY** |
| `exits` | `True` на свечах с сигналом **SELL** |

---

## 💡 Ключевые особенности

- 🆓 **Бесплатные данные** — MOEX без API-ключа
- 🔄 **OR-логика** — более гибкие сигналы
- 📈 **Трендовый фильтр SMA200** — торговля по тренду
- 📦 **Пагинация** — загрузка данных частями без потерь
- ✂️ **Вырезка периода** — тест на любом интервале без повторного скачивания
- 📐 **Расширенные метрики** — Sharpe, просадка, Win Rate, количество сделок
- 📝 **Читаемый код** — комментарии на русском

---

## ⚠️ Дисклеймер

Проект создан **в образовательных целях** и **не является инвестиционной рекомендацией**.  
Любая торговля на финансовых рынках связана с риском потери капитала.  
Исторические результаты не гарантируют аналогичной доходности в будущем.

---

## 👤 Автор

- GitHub: [@Vladislav585](https://github.com/Vladislav585)
- Telegram: [@Vladosik585](https://t.me/Vladosik585)


<br/><br/>
<div align="center">
  <hr size="3" width="100%" color="gray">
  <h2 id="english-version">🇺🇸 English Version</h2>
  <hr size="3" width="100%" color="gray">
</div>
<br/>

# 📈 EasyProject — Trading Strategy for Sberbank Stocks (SBER)

Algorithmic trading strategy for **Sberbank (SBER)** stocks on an hourly timeframe (**1h**).  
Historical data is loaded from **MOEX for free, without an API key**.  
The project supports **backtesting**, **realtime signals** and **parameter optimization**.

---

## 📚 Related Educational Material

This project is a practical continuation of my educational material, which is already published on my GitHub account.  
It demonstrates how the ideas from the tutorial can be applied in a real mini-project: from loading market data to building, backtesting, and optimizing a trading strategy.

If you came here from the tutorial, this repository can be viewed as a more practical implementation of the approaches described there.

---

## 🏆 Best Strategy Results

> Test period: **2022-01-03 — 2025-06-30** | Starting capital: **100,000 ₽** | Commission: **0.05%**

| Settings | Return | Sharpe Ratio | Max Drawdown |
|----------|--------|--------------|--------------|
| **RSI(30/70), OR logic, SMA200, no SL/TP** | **103.4%** | **1.78** | **17.8%** |
| RSI(35/65), OR logic, SMA200, SL=1.5%, TP=4% | 60.3% | 1.56 | 18.9% |

---

## ⚙️ Features

- 📥 Download historical hourly SBER candles from **MOEX** (from 2000 to today)
- 📊 Backtest the strategy on any selected period
- ⚡ Realtime mode: signals every N seconds
- 🔍 Parameter optimization for RSI / Stop Loss / Take Profit
- 🧮 Indicators: **MACD**, **RSI**, **SMA200**
- 💾 Save data and signals to **CSV**

---

## 🛠 Tech Stack

| Library | Purpose |
|---------|---------|
| `pandas` | Data manipulation, CSV read/write |
| `requests` | HTTP requests to MOEX API |
| `ta` | Technical indicators: MACD, RSI, SMA |
| `vectorbt` | Professional backtesting and metrics |

---

## 📁 Project Structure

```bash
EasyProject/
├── main.py              # Entry point: mode selection
├── data_load.py         # Data loading from MOEX
├── strategy.py          # Trading strategy (MACD + RSI + SMA200)
├── optimize.py          # Strategy parameter optimization
├── docs/
│   └── explanation.md   # Detailed project description
└── data/
    ├── sber_1h_all.csv                  # All historical candles
    ├── sber_<date>_<date>.csv           # Period slice (backtest)
    └── signals_<date>_<date>.csv        # Signals (backtest)
```

---

## 🚀 Installation & Setup

### 1. Clone the repository

```bash
git clone https://github.com/Vladislav585/sber-moex-trading-strategy.git
cd sber-moex-trading-strategy
```

### 2. Install dependencies

```bash
pip install pandas requests ta vectorbt
```

---

### 📥 Mode 1: Download historical data

In `main.py` set:

```python
MODE = "download"
```

Run:

```bash
python main.py
```

This will download **50,000+ candles** (from 2000 to today) into `data/sber_1h_all.csv`.  
Only needs to be done once.

---

### 📊 Mode 2: Backtest

In `main.py` set:

```python
MODE      = "backtest"
DATE_FROM = "2022-01-03"
DATE_TO   = "2025-06-30"
CASH      = 100000
FEES      = 0.0005
```

Run:

```bash
python main.py
```

**What happens:**
1. The selected period is sliced → `data/sber_<date>_<date>.csv`
2. Signals are calculated → `data/signals_<date>_<date>.csv`
3. **VectorBT** runs the backtest
4. Console output: return, Sharpe Ratio, drawdown, number of trades

---

### 🔍 Mode 3: Parameter optimization

```bash
python optimize.py
```

Or in `main.py`:

```python
MODE = "optimize"
```

**What it does:**
- Iterates through **19 combinations** of RSI, SL and TP parameters
- Calculates for each: return, Sharpe, drawdown, Win Rate, number of trades
- Prints a table sorted by Sharpe Ratio
- Highlights the best configurations (Sharpe ≥ 0.9, Return > 20%)

---

### ⚡ Mode 4: Realtime signals

In `main.py` set:

```python
MODE             = "realtime"
INTERVAL_SECONDS = 3600   # check every hour
```

Run:

```bash
python main.py
```

**What it does:**
- Every `N` seconds fetches the latest **~250 candles** from MOEX
- Calculates indicators
- Prints the current signal (`BUY` / `SELL` / `HOLD`) to console

---

## 📉 How the Strategy Works

### Indicators

| Indicator | Parameters | Purpose |
|----------|-----------|---------|
| **MACD** | 12 / 26 / 9 | Trend direction and strength |
| **RSI** | 14 | Overbought / oversold detection |
| **SMA200** | 200 | Global trend filter |

### Signal Logic

#### OR Mode (best results from optimization)

```
BUY  = (MACD crossed signal line upward  OR  RSI < buy_threshold)
       AND price is above SMA200

SELL = (MACD crossed signal line downward  OR  RSI > sell_threshold)
       AND price is below SMA200
```

#### AND Mode (stricter)

```
BUY  = MACD crossed upward  AND  RSI < buy_threshold  AND  price above SMA200
SELL = MACD crossed downward  AND  RSI > sell_threshold  AND  price below SMA200
```

> If `use_trend_filter=False` — SMA200 filter is disabled.

### Stop Loss / Take Profit (optional)

```python
stop_loss_pct   = 1.5   # sell if price drops 1.5% from entry
take_profit_pct = 4.0   # sell if price rises 4% from entry
```

> Setting `0` disables protection. Best results were achieved **without SL/TP**.

---

## 📋 Output CSV Format

After backtesting, `data/signals_<date>_<date>.csv` is created:

| Column | Description |
|--------|-------------|
| `signal` | `BUY`, `SELL` or `HOLD` |
| `entries` | `True` on candles with **BUY** signal |
| `exits` | `True` on candles with **SELL** signal |

---

## 💡 Key Features

- 🆓 **Free data** — MOEX without API key
- 🔄 **OR logic** — more flexible signal generation
- 📈 **SMA200 trend filter** — trade with the trend
- 📦 **Pagination** — loads all data in chunks without loss
- ✂️ **Period slicing** — test any interval without re-downloading
- 📐 **Extended metrics** — Sharpe, drawdown, Win Rate, trade count
- 📝 **Readable code** — comments in Russian


---

## ⚠️ Disclaimer

This project was created **for educational purposes** and **does not constitute investment advice**.  
Trading in financial markets involves the risk of capital loss.  
Past performance does not guarantee similar results in the future.

---

## 👤 Author

- GitHub: [@Vladislav585](https://github.com/Vladislav585)
- Telegram: [@Vladosik585](https://t.me/Vladosik585)
