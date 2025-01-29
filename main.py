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


flet.app(main)
