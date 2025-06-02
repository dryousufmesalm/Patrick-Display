# Real-Time Trading System with Supabase Integration

## Overview

This is a completely refactored real-time trading system that eliminates PocketBase dependencies and provides sub-second performance with direct Supabase integration. The system is designed for high-frequency trading with multiple strategies, accounts, and symbols.

## Key Features

- **Real-Time Performance**: Sub-second updates with 100ms polling intervals
- **Direct Supabase Integration**: No local caching or syncing required
- **Multiple Strategy Support**: Currently supports CycleTrader and AdaptiveHedging, extensible for more
- **Multi-Account Management**: Each user can run multiple accounts with different strategies
- **Connection Resilience**: Automatic reconnection with exponential backoff
- **Event-Driven Architecture**: Real-time event processing and command handling
- **Performance Monitoring**: Built-in performance tracking and health monitoring

## Architecture

### Core Components

```
TradingSystemManager
├── Supabase Service (Real-time DB operations)
├── MetaTrader 5 Connector (Trading execution)
└── Multiple Trading Bots
    ├── Strategy Instances (per symbol)
    ├── Event Processing
    └── Performance Monitoring
```

### Database Collections (Supabase)

The system uses the following collections:

- `users` - User accounts and authentication
- `meta-trader-accounts` - MetaTrader account information
- `bots` - Bot instances and status
- `bot-configs` - Bot configurations and parameters
- `strategies` - Available trading strategies
- `cycles` - Trading cycles (grouped orders)
- `orders` - Individual trade orders
- `events` - System events and commands
- `symbols` - Trading symbols configuration

## Quick Start

### 1. Environment Setup

Create a `.env` file in the Patrick-Display directory:

```bash
# Supabase Configuration
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_anon_key

# System Configuration
MAX_BOTS=10
UPDATE_INTERVAL=0.1
HEARTBEAT_INTERVAL=60
LOG_LEVEL=INFO

# MetaTrader 5 Configuration
MT5_LOGIN=your_mt5_login
MT5_PASSWORD=your_mt5_password
MT5_SERVER=your_mt5_server
```

### 2. Install Dependencies

```bash
# Activate virtual environment
cd Patrick-Display
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install requirements
pip install -r requirements_realtime.txt
```

### 3. Run the System

```bash
python main_realtime.py
```

## Strategy Implementation

### Creating a New Strategy

1. Inherit from `BaseStrategy`:

```python
from Strategy.base_strategy import BaseStrategy

class MyNewStrategy(BaseStrategy):
    def __init__(self, meta_trader, config, supabase_client, symbol, bot):
        super().__init__(meta_trader, config, supabase_client, symbol, bot)
        # Custom initialization

    async def initialize(self) -> bool:
        # Custom initialization logic
        return await super().initialize()

    async def analyze_market(self) -> bool:
        # Market analysis logic
        pass

    async def execute_strategy(self):
        # Strategy execution logic
        pass
```

2. Register in `TradingBotV2`:

```python
elif self.strategy_type == 'MyNewStrategy':
    strategy = MyNewStrategy(
        self.meta_trader,
        strategy_config,
        self.supabase_client,
        symbol,
        self
    )
```

### Current Strategies

#### CycleTrader

- **Purpose**: Executes systematic trading cycles
- **Key Features**: Grid trading, cycle management, profit targeting
- **Best For**: Range-bound markets, systematic profit collection

#### AdaptiveHedging

- **Purpose**: Dynamic hedging based on market conditions
- **Key Features**: Risk management, adaptive positioning, hedge optimization
- **Best For**: Volatile markets, risk mitigation

## Event Processing

### Event Types

The system processes various event types:

- `MARKET_UPDATE` - Price and market data changes
- `CYCLE_COMPLETE` - Trading cycle completion
- `ORDER_FILLED` - Order execution confirmation
- `COMMAND` - External commands to bots
- `HEARTBEAT` - System health monitoring
- `ERROR` - Error notifications

### Real-Time Event Flow

```
Market Data → MetaTrader → Strategy Analysis → Database Update → Event Generation → Strategy Response
```

## Configuration Management

### Bot Configuration Structure

```python
{
    "name": "MyBot_EURUSD",
    "strategy_type": "CycleTrader",
    "symbols": ["EURUSD"],
    "magic": 12345,
    "configs": {
        "lot_size": 0.01,
        "distance": 50,
        "target_profit": 100,
        "max_cycles": 5
    }
}
```

### Parameter Storage

All parameters are stored in the `bot-configs` collection:

- Strategy-specific settings
- Risk management parameters
- Trading preferences
- Symbol configurations

## Performance Optimization

### Sub-Second Updates

- 100ms event polling interval
- Async/await throughout the codebase
- Connection pooling for database operations
- Batch operations where possible

### Memory Management

- Efficient data structures
- Regular cleanup of completed cycles
- Connection pooling to prevent leaks
- Event queue management

### Error Handling

- Exponential backoff for connection failures
- Graceful degradation during outages
- Comprehensive logging for debugging
- Automatic recovery mechanisms

## Monitoring and Debugging

### Performance Metrics

The system tracks:

- Events processed per minute
- Database query performance
- Bot health status
- Strategy execution times
- Connection stability

### Logging

Structured logging with multiple levels:

- `INFO`: General system operation
- `WARNING`: Recoverable issues
- `ERROR`: Serious problems requiring attention
- `DEBUG`: Detailed execution traces

### Health Monitoring

- Automatic bot health checks
- Connection monitoring
- Performance degradation detection
- Automatic restart capabilities

## Migration from Old System

### Removed Components

- All PocketBase dependencies
- Local database synchronization
- Blocking I/O operations
- Legacy strategy implementations

### New Benefits

- **Performance**: 10x faster with async operations
- **Reliability**: Direct database connections eliminate sync issues
- **Scalability**: Better resource utilization
- **Maintainability**: Cleaner, more organized code structure

### Migration Steps

1. **Backup Data**: Export existing configurations
2. **Update Environment**: Set Supabase credentials
3. **Install Dependencies**: New async libraries
4. **Test Connections**: Verify Supabase and MetaTrader connectivity
5. **Import Configurations**: Transfer bot configs to new format
6. **Start System**: Launch with monitoring

## Troubleshooting

### Common Issues

1. **Connection Failures**

   - Check Supabase credentials
   - Verify network connectivity
   - Review firewall settings

2. **MetaTrader Issues**

   - Ensure MT5 is running
   - Check login credentials
   - Verify server connectivity

3. **Performance Issues**
   - Monitor system resources
   - Check database query performance
   - Review event queue processing

### Debug Mode

Enable detailed logging:

```bash
export LOG_LEVEL=DEBUG
python main_realtime.py
```

## Future Enhancements

### Planned Features

- **WebSocket Integration**: Real-time web dashboard updates
- **Machine Learning**: Predictive analytics for strategy optimization
- **Multi-Broker Support**: Support for additional trading platforms
- **Advanced Risk Management**: Portfolio-level risk controls
- **API Gateway**: REST API for external integrations

### Strategy Extensions

- **Scalping Strategy**: High-frequency micro-trades
- **Trend Following**: Momentum-based trading
- **News Trading**: Event-driven strategies
- **Arbitrage**: Cross-market opportunities

## Support and Contribution

### Getting Help

1. Check the logs for detailed error information
2. Review the troubleshooting section
3. Test individual components in isolation
4. Use debug mode for detailed tracing

### Contributing

1. Follow the existing code patterns
2. Add comprehensive error handling
3. Include performance monitoring
4. Write async-compatible code
5. Document new features thoroughly

---

**Note**: This system requires careful configuration and monitoring. Always test with demo accounts before using in production trading environments.
