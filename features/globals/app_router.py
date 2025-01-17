from enum import StrEnum
import flet


class AppRoutes(StrEnum):
    
    LOGIN_MT5 = "/MT5"
    LOGIN_PB= "/PB"
    HOME = "/"


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
