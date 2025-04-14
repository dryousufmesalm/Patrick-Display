# Technical Context

## Technologies Used

### Frontend

- **Flet**: Core UI framework
- **FletX**: Extended UI components and navigation
- **Python**: Primary programming language

### Backend and Data

- **SQLAlchemy**: Database ORM
- **PocketBase**: Remote database and authentication
- **MetaTrader 5 API**: Trading platform integration
- **SQLite**: Local database storage

### Development Tools

- **Virtual Environment**: For dependency isolation
- **Requirements.txt**: Dependency management
- **Git**: Version control

## Development Setup

- Python virtual environment (venv)
- Installed dependencies via requirements.txt
- Local SQLite database for data persistence
- PocketBase server for remote data

## Technical Constraints

- MetaTrader 5 API limitations
- Platform compatibility requirements
- Authentication security requirements
- Performance considerations for real-time data

## Dependencies

Major dependencies include:

- flet/fletx for UI components
- MetaTrader5 for trading platform integration
- pocketbase for remote database operations
- sqlalchemy/sqlmodel for database interactions
- asyncio/threading for asynchronous operations

## Architecture

- Model-View pattern with route-based navigation
- Component-based UI structure
- Multi-threaded operations for background tasks
- API-driven data retrieval and updates
