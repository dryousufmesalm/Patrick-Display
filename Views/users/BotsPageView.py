import flet
from helpers.store import store
from helpers.actions_creators import GetUser, GetAccount,isMt5Authorized
from Views.globals.app_router import AppRoutes
from fletx import Xview


class BotsPageView(Xview):
    def build(self):
        account_id = self.get_param('account')
        user_id = self.get_param('user')
        user_data =  GetUser(user_id)
        if not user_data:
            self.back()
        auth = user_data.get('auth_api')
        bots = auth.get_account_bots(account_id)
        account_data = GetAccount(user_id, account_id)
        headline = flet.Text(
            value=account_data.name + " account",
            style=flet.TextStyle(
                size=28,
                weight=flet.FontWeight.BOLD,
                color=flet.Colors.PRIMARY,
            ),
            text_align=flet.TextAlign.CENTER,
        )

        # states = store.get_state()
        # users = states['users']['users']
        bots_buttons = []
        for bot in bots:
            bots_buttons.append(
                flet.ElevatedButton(
                    text=bot.name,
                    expand=False,
                    width=300,
                    # on_click=lambda e, bot=bot: self.go(
                    #     f'/bot/{user_id}/{account_id}/{bot.id}'),
                )
            )
        back_button = flet.Button(
            text="< back",
            on_click=lambda e: self.back(),
            expand=False,
            width=200,
            color=flet.Colors.TERTIARY,
        )
        launch_metatrader = flet.ElevatedButton(
            text="Metatrader is running" if isMt5Authorized(user_id,account_id) else "Launch MT5",
            on_click=lambda e: self.go(f'/MT5/{user_id}/{account_id}'),
            expand=False,
            width=200,
        )
        Bots_headline = flet.Text(
            value="Bots",
            style=flet.TextStyle(
                size=28,
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
                launch_metatrader,
                Bots_headline,
                *bots_buttons,
                back_button,
            ]

        )
