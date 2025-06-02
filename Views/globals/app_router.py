from enum import StrEnum
import flet


class AppRoutes(StrEnum):

    # Legacy PocketBase routes (deprecated)
    LOGIN_PB = "/PB"
    ADD_ACCOUNT = "/ACCOUNT"

    # New Supabase routes
    LOGIN_SUPABASE = "/login"
    ACCOUNTS_SUPABASE = "/accounts"
    QUICK_LOGIN = "/quick-login"

    # Phase 2: Bot management and monitoring routesq
    BOT_SELECTION = "/bots/:user/:account"
    SYSTEM_MONITOR = "/monitor/:user/:account/:session"

    # Core routes (legacy)
    HOME = "/"
    USER = "/user/:id"
    ACCOUNTS = "/accounts/:user"
    Bot = "/bot/:user/:account/:id"
    BOTS = "/bots/:user/:account"
    LOGIN_MT5 = "/MT5/:user/:account"
