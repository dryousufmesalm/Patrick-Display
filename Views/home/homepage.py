import flet
from helpers.store import store
from Views.globals.app_router import AppRoutes
from fletx import Xview


class HomePageView(Xview):
    def build(self):
        headline = flet.Text(
            value="Patrick Display",
            style=flet.TextStyle(
                size=28,
                weight=flet.FontWeight.BOLD,
                color=flet.Colors.PRIMARY,
            ),
            text_align=flet.TextAlign.CENTER,
        )
        add_account_button = flet.ElevatedButton(
            text="Add User",
            expand=False,
            on_click=lambda e: self.go(AppRoutes.LOGIN_PB),
            width=300,
        )

        states = store.get_state()
        users = states['users']['users']
        user_buttons = []
        for user in users:
            user_buttons.append(
                flet.ElevatedButton(
                    text=user['name'],
                    expand=False,
                    width=300,
                    on_click=lambda e, user=user: self.go(
                        f'/accounts/{user["id"]}'),
                )
            )
            
        users_headline = flet.Text(
            value="Users",
            style=flet.TextStyle(
                size=18,
                weight=flet.FontWeight.BOLD,
                color=flet.Colors.PRIMARY,
            ),
            text_align=flet.TextAlign.CENTER,
        )
        return flet.View(
            horizontal_alignment=flet.CrossAxisAlignment.CENTER,
            vertical_alignment=flet.MainAxisAlignment.CENTER,
            controls=[
                headline,
                add_account_button,
                users_headline,
                *user_buttons,
            ]

        )
