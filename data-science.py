from dataclasses import dataclass
from typing import Dict, List, Callable
import numpy as np
import psycopg2
import pandas as pd
from datetime import datetime

class TickDataProvider:
    def __init__(self, connection_string):
        self.conn_string = connection_string
        
    def connect(self):
        return psycopg2.connect(self.conn_string)
    
    def get_tick_range(self, symbol, start_time, end_time):
        """Fetch tick data for a specific symbol and time range"""
        with self.connect() as conn:
            query = """
                SELECT timestamp, price, volume, bid, ask
                FROM ticks 
                WHERE symbol = %s AND timestamp BETWEEN %s AND %s
                ORDER BY timestamp
            """
            return pd.read_sql(query, conn, params=(symbol, start_time, end_time))
    
    def get_live_tick_stream(self, symbols):
        """Create a generator for streaming live ticks"""
        # Implementation for real-time tick streaming
        pass

@dataclass
class Position:
    symbol: str
    entry_price: float
    entry_time: datetime
    direction: int  # 1 for long, -1 for short
    size: float
    strategy_id: str
    current_price: float = None
    max_favorable_excursion: float = 0
    max_adverse_excursion: float = 0

class StrategyManager:
    def __init__(self):
        self.strategies = {}
        self.active_positions = []
        
    def register_strategy(self, strategy_id, strategy_func):
        """Register a trading strategy function"""
        self.strategies[strategy_id] = strategy_func
    
    def process_tick(self, tick_data):
        """Process incoming tick data through all strategies"""
        signals = []
        for strategy_id, strategy_func in self.strategies.items():
            signal = strategy_func(tick_data, self._get_strategy_positions(strategy_id))
            if signal:
                signals.append((strategy_id, signal))
        return signals
    
    def _get_strategy_positions(self, strategy_id):
        """Get all positions for a specific strategy"""
        return [p for p in self.active_positions if p.strategy_id == strategy_id]
    
    def update_positions(self, tick_data):
        """Update all position metrics including MFE/MAE"""
        for position in self.active_positions:
            if position.symbol == tick_data.get('symbol'):  # Use .get() instead of direct access
                position.current_price = tick_data['price']
                
                # Calculate profit/loss
                pl = (position.current_price - position.entry_price) * position.direction * position.size
                
                # Update MFE (Maximum Favorable Excursion)
                if pl > position.max_favorable_excursion:
                    position.max_favorable_excursion = pl
                    
                # Update MAE (Maximum Adverse Excursion)
                if pl < position.max_adverse_excursion:
                    position.max_adverse_excursion = pl

class PortfolioEvaluator:
    def __init__(self, strategy_manager, risk_settings):
        self.strategy_manager = strategy_manager
        self.risk_settings = risk_settings
        
        required_settings = ['mfe_exit_threshold']
        for setting in required_settings:
            if setting not in risk_settings:
                raise ValueError(f"Missing required risk setting: {setting}")
        
    def evaluate_exit_conditions(self):
        """Evaluate if any positions should be closed based on portfolio metrics"""
        positions = self.strategy_manager.active_positions
        if not positions:
            return []
            
        # Group positions by symbol for collective evaluation
        symbol_groups = {}
        for position in positions:
            if position.symbol not in symbol_groups:
                symbol_groups[position.symbol] = []
            symbol_groups[position.symbol].append(position)
        
        exit_signals = []
        
        for symbol, pos_group in symbol_groups.items():
            # Calculate collective MFE for this symbol's positions
            total_mfe = sum(p.max_favorable_excursion for p in pos_group)
            current_pl = sum((p.current_price - p.entry_price) * p.direction * p.size 
                             for p in pos_group)
            
            # MFE-based trailing stop logic
            # If current P&L has fallen more than X% from MFE, exit positions
            if total_mfe > 0 and current_pl < total_mfe * (1 - self.risk_settings['mfe_exit_threshold']):
                for position in pos_group:
                    exit_signals.append((position, "MFE_TRAILING_STOP"))
                    
        return exit_signals
    
    def calculate_portfolio_metrics(self):
        """Calculate overall portfolio performance metrics"""
        positions = self.strategy_manager.active_positions
        
        metrics = {
            "total_positions": len(positions),
            "net_exposure": sum(p.size * p.direction for p in positions),
            "total_profit_loss": sum((p.current_price - p.entry_price) * p.direction * p.size 
                                     for p in positions if p.current_price),
            "max_drawdown": self._calculate_max_drawdown(),
            "strategy_correlation": self._calculate_strategy_correlation()
        }
        
        return metrics
    
    def _calculate_max_drawdown(self):
        """Calculate maximum drawdown from equity curve"""
        # TODO: Implement max drawdown calculation
        return 0.0  # Temporary placeholder
    
    def _calculate_strategy_correlation(self):
        """Calculate correlation matrix between strategy returns"""
        # TODO: Implement correlation calculation
        return {}  # Temporary placeholder

class ExecutionSimulator:
    def __init__(self, strategy_manager, portfolio_evaluator):
        self.strategy_manager = strategy_manager
        self.portfolio_evaluator = portfolio_evaluator
        self.trade_history = []
        
    def process_tick_data(self, tick):
        """Process a single tick through the entire system"""
        required_fields = ['symbol', 'price', 'timestamp']
        for field in required_fields:
            if field not in tick:
                raise ValueError(f"Missing required tick field: {field}")

        # Update all position metrics with new tick
        self.strategy_manager.update_positions(tick)
        
        # Evaluate if any positions should be closed
        exit_signals = self.portfolio_evaluator.evaluate_exit_conditions()
        for position, reason in exit_signals:
            self._close_position(position, tick, reason)
        
        # Process tick through strategies and get new signals
        new_signals = self.strategy_manager.process_tick(tick)
        for strategy_id, signal in new_signals:
            if signal['action'] == 'BUY':
                self._open_position(strategy_id, tick, signal['size'], 1)
            elif signal['action'] == 'SELL':
                self._open_position(strategy_id, tick, signal['size'], -1)
                
        # Update portfolio metrics
        metrics = self.portfolio_evaluator.calculate_portfolio_metrics()
        return metrics
    
    def _open_position(self, strategy_id, tick, size, direction):
        position = Position(
            symbol=tick['symbol'],
            entry_price=tick['price'],
            entry_time=tick['timestamp'],
            direction=direction,
            size=size,
            strategy_id=strategy_id
        )
        self.strategy_manager.active_positions.append(position)
        self.trade_history.append({
            'action': 'OPEN',
            'timestamp': tick['timestamp'],
            'position': position
        })
        
    def _close_position(self, position, tick, reason):
        position.exit_price = tick['price']
        position.exit_time = tick['timestamp']
        position.exit_reason = reason
        
        self.strategy_manager.active_positions.remove(position)
        self.trade_history.append({
            'action': 'CLOSE',
            'timestamp': tick['timestamp'],
            'position': position,
            'reason': reason
        })