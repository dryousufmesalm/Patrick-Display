import flet
from fletx import Xapp, route

# Legacy views (PocketBase)
from Views.login.metatrader_login_page import Mt5LoginPageView
from Views.login.pocketbase_login_page import RemoteLoginPageView
from Views.users.UserPageView import UserPageView
from Views.home.add_account import AddAccountView
from Views.users.AccountPageView import AccountPageView
from Views.users.BotsPageView import BotsPageView
from Views.home.homepage import HomePageView

# New Supabase views
from Views.login.supabase_login_page import SupabaseLoginPageView, QuickLoginView
from Views.accounts.account_selection_page import AccountSelectionPageView

# Phase 2: Bot management and monitoring views
from Views.bots.bot_selection_page import BotSelectionPageView
from Views.monitor.system_monitor_page import SystemMonitorPageView

from Views.globals.app_router import AppRoutes
from Views.globals.app_logger import app_logger
import threading
import asyncio

from DB.remote_login.repositories.remote_login_repo import RemoteLoginRepo

# Legacy auth (PocketBase) - DEPRECATED
# from Views.auth.auth import login

# New Supabase auth
from Views.auth import supabase_auth

from DB.db_engine import engine, create_db_and_tables
from helpers.store import store

import multiprocessing


def main(page: flet.Page):
    # 0. Register Globals
    # Register the page to the AppState to allow changing the page route from anywhere
    page.title = "Patrick Trading System v2.0"

    Xapp(
        page=page,
        routes=[
            # New Supabase routes (primary)
            route(route=AppRoutes.LOGIN_SUPABASE, view=SupabaseLoginPageView),
            route(route=AppRoutes.ACCOUNTS_SUPABASE,
                  view=AccountSelectionPageView),
            route(route=AppRoutes.QUICK_LOGIN, view=QuickLoginView),

            # Phase 2: Bot management and monitoring routes
            route(route=AppRoutes.BOT_SELECTION, view=BotSelectionPageView),
            route(route=AppRoutes.SYSTEM_MONITOR, view=SystemMonitorPageView),

            # Legacy PocketBase routes (deprecated but kept for transition)
            route(route=AppRoutes.ADD_ACCOUNT, view=AddAccountView),
            route(route=AppRoutes.LOGIN_PB, view=RemoteLoginPageView),

            # Core application routes
            route(route=AppRoutes.LOGIN_MT5, view=Mt5LoginPageView),
            route(route=AppRoutes.HOME, view=HomePageView),
            route(route=AppRoutes.USER, view=UserPageView),
            route(route=AppRoutes.ACCOUNTS, view=AccountPageView),
            route(route=AppRoutes.BOTS, view=BotsPageView),
        ],
    )
    page.on_close = terminate_all_processes

    async def initialize_auth():
        """Initialize authentication system on startup"""
        try:
            app_logger.info("Initializing Supabase authentication...")

            # Check if user is already authenticated
            if await supabase_auth.is_authenticated():
                app_logger.info(
                    "User already authenticated, redirecting to accounts")
                page.go(AppRoutes.ACCOUNTS_SUPABASE)
            else:
                app_logger.info("No authenticated user, redirecting to login")
                page.go(AppRoutes.LOGIN_SUPABASE)

            page.update()

        except Exception as e:
            app_logger.error(f"Error initializing authentication: {e}")
            # Fallback to login page
            page.go(AppRoutes.LOGIN_SUPABASE)
            page.update()

    async def fetch_legacy_data():
        """Legacy data fetching for backward compatibility - DEPRECATED"""
        try:
            remote_logger = RemoteLoginRepo(engine=engine)
            users = remote_logger.get_All_users()  # Returns empty list now
            app_logger.info(
                f"Legacy data fetch: found {len(users)} users (expected: 0)")
            # Legacy login removed for security
            page.update()
        except Exception as e:
            app_logger.error(f"Failed to load legacy credentials: {e}")

    # Initialize authentication in background
    threading.Thread(target=lambda: asyncio.run(
        initialize_auth()), daemon=True).start()

    # Optional: Load legacy data for transition period
    # threading.Thread(target=lambda: asyncio.run(
    #     fetch_legacy_data()), daemon=True).start()


def terminate_all_processes():
    """Cleanup function called on app close"""
    try:
        # Cleanup Supabase auth
        asyncio.run(supabase_auth.cleanup_auth())

        # Cleanup processes
        for process in multiprocessing.active_children():
            process.terminate()

        # Cleanup threads
        for thread in threading.enumerate():
            if thread is not threading.main_thread():
                thread.join(timeout=2)  # Add timeout to prevent hanging

        app_logger.info("Application cleanup completed")

    except Exception as e:
        app_logger.error(f"Error during cleanup: {e}")


if __name__ == "__main__":
    multiprocessing.freeze_support()

    # Ensure database is initialized before starting the app
    try:
        app_logger.info("Initializing database...")
        create_db_and_tables()
        app_logger.info("Database initialization complete")
    except Exception as e:
        app_logger.error(f"Database initialization error: {e}")
        # Continue with app startup even if database initialization fails

    # Start the application
    app_logger.info("Starting Patrick Trading System v2.0...")
    flet.app(main)
