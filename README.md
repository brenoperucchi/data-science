# Quantitative Trading Portfolio SDK

## Overview

This project provides a sophisticated SDK for evaluating and managing multiple trading strategies (robots) as a cohesive portfolio for the Brazilian stock market (B3). Unlike traditional trading platforms, our approach leverages high-resolution tick data and real-time portfolio analytics to optimize trade execution.

## Purpose

Traditional backtesting platforms (like Strategy Quant) rely on simplified market approximations and tend to evaluate strategies in isolation. Our SDK addresses these limitations by:

1. **Using accurate tick data** instead of unreliable OHLC data from MT5
2. **Evaluating multiple strategies together** to understand portfolio-level dynamics
3. **Optimizing trade exits based on collective performance** metrics like Maximum Favorable Excursion (MFE)
4. **Providing real-time portfolio evaluation** for dynamic decision making

## Core Features

- **Tick Data Integration**: Direct connection to TimescaleDB for efficient retrieval of historical and streaming tick data
- **Multi-Strategy Evaluation**: Concurrent simulation of multiple trading robots with correlation analysis
- **MFE-Based Exit Logic**: Dynamic trade exits based on portfolio-level Maximum Favorable Excursion
- **Real-Time Analytics**: Continuous calculation of key risk metrics and performance indicators
- **Modular Architecture**: Easily extendable with custom strategies and analytics

## System Architecture

The SDK consists of four primary components:

1. **Data Layer**: Efficient tick data retrieval from TimescaleDB
2. **Strategy Manager**: Multi-strategy simulation and position tracking
3. **Portfolio Evaluator**: Collective performance analysis and MFE-based exit rules
4. **Execution Module**: Trade simulation and performance reporting

## Installation

```bash
# Clone the repository
git clone https://github.com/your-username/quantitative-trading-portfolio-sdk.git

# Create a Python virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

```python
from data_science import TickDataProvider, StrategyManager, PortfolioEvaluator, ExecutionSimulator

# Initialize components
tick_provider = TickDataProvider("postgresql://user:password@localhost:5432/tickdb")
strategy_manager = StrategyManager()
portfolio_evaluator = PortfolioEvaluator(strategy_manager, {"mfe_exit_threshold": 0.3})
execution_simulator = ExecutionSimulator(strategy_manager, portfolio_evaluator)

# Register trading strategies
strategy_manager.register_strategy("rsi_strategy", rsi_strategy_function)
strategy_manager.register_strategy("macd_strategy", macd_strategy_function)

# Run backtest with historical data
historical_ticks = tick_provider.get_tick_range("PETR4", "2023-01-01", "2023-01-31")
for tick in historical_ticks.to_dict('records'):
    metrics = execution_simulator.process_tick_data(tick)

