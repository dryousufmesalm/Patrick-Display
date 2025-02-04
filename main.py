import flet
from fletx import Xapp, route
from Views.login.metatrader_login_page import Mt5LoginPageView
from Views.login.pocketbase_login_page import RemoteLoginPageView
from Views.users.UserPageView import UserPageView
from Views.home.add_account import AddAccountView
from Views.users.AccountPageView import AccountPageView
from Views.users.BotsPageView import BotsPageView
from Views.home.homepage import HomePageView
from Views.globals.app_router import AppRoutes
from Views.globals.app_logger import app_logger
import threading
import asyncio

from DB.remote_login.repositories.remote_login_repo import RemoteLoginRepo

from Views.auth.auth import login
from DB.db_engine import engine
from helpers.store import store

import multiprocessing


def main(page: flet.Page):
    # 0. Register Globals
    # Register the page to the AppState to allow changing the page route from anywhere
    page.title = "Patrick Display"

    Xapp(
        page=page,
        routes=[
            route(route=AppRoutes.ADD_ACCOUNT, view=AddAccountView),
            route(route=AppRoutes.LOGIN_PB, view=RemoteLoginPageView),
            # Add more routes as needed...
            route(route=AppRoutes.LOGIN_MT5, view=Mt5LoginPageView),
            route(route=AppRoutes.HOME, view=HomePageView),
            route(route=AppRoutes.USER, view=UserPageView),
            route(route=AppRoutes.ACCOUNTS, view=AccountPageView),
            route(route=AppRoutes.BOTS, view=BotsPageView),
        ],
    )

    async def fetch_data():
        try:
            remote_logger = RemoteLoginRepo(engine=engine)
            users = remote_logger.get_All_users()
            for user in users:
                await login(user.username, user.password)
            page.update()
        except Exception as e:
            app_logger.error(f"Failed to load saved credentials: {e}")

        # Start API call in a background thread
    threading.Thread(target=lambda: asyncio.run(
        fetch_data()), daemon=True).start()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    flet.app(main)
