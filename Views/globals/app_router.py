from enum import StrEnum
import flet


class AppRoutes(StrEnum):

    LOGIN_PB = "/PB"
    ADD_ACCOUNT = "/ACCOUNT"
    HOME = "/"
    USER = "/user/:id"
    ACCOUNTS = "/accounts/:user"
    Bot = "/bot/:user/:account/:id"
    BOTS = "/bots/:user/:account"
    LOGIN_MT5 = "/MT5/:user/:account"


class AppRouter:
    current_route: AppRoutes = AppRoutes.HOME
    page: flet.Page

    @staticmethod
    def change_route(route: AppRoutes):
        AppRouter.current_route = route
        AppRouter.page.route = AppRouter.current_route
        AppRouter.page.update()

    @staticmethod
    def snackbar(msg: str, color: flet.Colors = flet.Colors.PRIMARY):
        AppRouter.page.snack_bar = flet.SnackBar(
            content=flet.Text(msg),
            bgcolor=color,
        )
        AppRouter.page.snack_bar.open = True
        AppRouter.page.update()
