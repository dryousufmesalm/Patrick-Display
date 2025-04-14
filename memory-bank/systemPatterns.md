# System Patterns

## Architecture Overview

Patrick Display follows a component-based architecture with route navigation, leveraging Flet/FletX for UI management and various backend services for data operations.

## Key Design Patterns

### Route-Based Navigation

- Uses FletX's route system for page navigation
- Centralized route definitions in AppRoutes
- View components mapped to specific routes

### View Components

- Each page is a separate view component
- Components follow a consistent interface pattern
- Views are modular and reusable

### Authentication Flow

- Dual authentication systems:
  - MetaTrader 5 login
  - PocketBase remote login
- Credential storage and retrieval
- Automatic login with saved credentials

### Data Management

- Repository pattern for data access
- SQLAlchemy/SQLModel for ORM operations
- Clean separation between data access and UI logic

### Concurrency Model

- Threading for background operations
- Asyncio for non-blocking API calls
- Process management for cleanup on application close

## Component Relationships

- Main app bootstraps the route system and initializes core services
- Views handle UI rendering and user interactions
- Repositories manage data operations
- Helpers provide utility functions across the application
- Store manages global state

## Execution Flow

1. Application startup in main.py
2. Route initialization and view registration
3. Background thread for credential loading and login
4. User interaction via routed views
5. Clean termination of processes on application close
