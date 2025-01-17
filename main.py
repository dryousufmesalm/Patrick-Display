import flet
from features.login import pocketbase_login_page
from features.login import metatrader_login_page
from features.home import home_page
from features.globals.app_logger import app_logger
from features.globals.app_router import AppRouter, AppRoutes


def main(page: flet.Page):
    # 0. Register Globals
    # Register the page to the AppState to allow changing the page route from anywhere
    AppRouter.page = page
    page.horizontal_alignment = 'CENTER'
    page.vertical_alignment = flet.MainAxisAlignment.CENTER
    page.horizontal_alignment = flet.CrossAxisAlignment.CENTER
    def on_route_change(e: flet.RouteChangeEvent):
        route = e.route
        app_logger.info(f"Navigated to {route}")
        # Clear the views on the page
        page.views.clear()
        # Create the new view based on the route
        if route == AppRoutes.LOGIN_MT5:
            metatrader_login_page.build(page)
        elif route == AppRoutes.LOGIN_PB:
            pocketbase_login_page.build(page)
        elif route == AppRoutes.HOME:
            home_page.build(page)
        else:
            page.title = "404"
            page.add(flet.Text("404 - Page Not Found"))

        page.update()

    page.on_route_change = on_route_change

    home_page.build(page)


flet.app(main)
