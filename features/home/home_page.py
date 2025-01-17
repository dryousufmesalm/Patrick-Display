import flet
from features.globals.app_router import AppRoutes, AppRouter
from features.globals.app_state import store
from pb import start_pocketbase

def build(page: flet.Page):
    page.title = "Home"
    home_page = HomePageView()
    page.horizontal_alignment = flet.CrossAxisAlignment.CENTER
    page.vertical_alignment = flet.MainAxisAlignment.CENTER
    # Add the home page to the views before any update
    page.views.append(
        flet.View(
            AppRoutes.HOME,
            [
                flet.Container(
                    content=home_page,
                    alignment=flet.alignment.center,
                ),
            ],
        )
    )

    page.update()

class HomePageView(flet.Column):
    def __init__(self):
        super().__init__()
        self.horizontal_alignment = flet.CrossAxisAlignment.CENTER
        self.alignment = flet.MainAxisAlignment.CENTER
        self.spacing = 30

        self.headline = flet.Text(
            value="Patrick Display",
            style=flet.TextStyle(
                size=28,
                weight=flet.FontWeight.BOLD,
                color=flet.Colors.PRIMARY,
            ),
            text_align=flet.TextAlign.CENTER,
        )

        self.localdb_button = flet.ElevatedButton(
            text="Local server is running" if store.local_db else "Launch local server",
            on_click=self.toggle_localdb,
            expand=False,
            width=300,
        )

        self.mt5_button = flet.ElevatedButton(
            text="MT5 connected" if store.Mt5_authorized else "Connect MT5",
            on_click=self.launch_mt5,
            expand=False,
            width=300,
        )

        self.login_button = flet.ElevatedButton(
            text="Remote server connected" if store.token else "Login to remote server",
            on_click=self.login_to_server,
            expand=False,
            width=300,
        )

        self.logout_button = flet.ElevatedButton(
            text="Logout",
            on_click=self.on_logout,
            expand=False,
            width=300,
            color=flet.Colors.ERROR,
            visible=False,
        )

        # self.feedback_history = flet.ListView(
        #     expand=False,
        #     height=200,
        # )

        self.controls = [
            self.headline,
            self.localdb_button,
            self.mt5_button,
            self.login_button,
            self.logout_button,
        ]

    # def show_feedback(self, message, is_error=False):
    #     feedback_item = flet.Text(
    #         value=message,
    #         style=flet.TextStyle(
    #             color=flet.Colors.ERROR if is_error else flet.Colors.SECONDARY,
    #         ),
    #     )
        # self.feedback_history.controls.append(feedback_item)
        # self.feedback_history.update()

    def toggle_localdb(self, e):
        # self.show_feedback("Processing...", is_error=False)

        if store.get_local_db():
            store.set_local_db(False)
            self.localdb_button.text = "Launch local server"
            # self.show_feedback("LocalDB stopped successfully.")
        else:
            start_pocketbase()
            store.set_local_db(True)
            self.localdb_button.text = "Local server is running"
            # self.show_feedback("LocalDB launched successfully.")

        self.update()

    def launch_mt5(self, e):
        # self.show_feedback("MT5 launched", is_error=False)
        AppRouter.change_route(AppRoutes.LOGIN_MT5)
        store.Mt5_authorized = True
        self.mt5_button.text = "MT5 Connected"
        self.update()

    def login_to_server(self, e):
        # self.show_feedback("Logged in to server", is_error=False)
        AppRouter.change_route(AppRoutes.LOGIN_PB)
        self.login_button.text = "Remote server connected"
        self.logout_button.visible = True
        self.update()

    def on_logout(self, e):
        # self.show_feedback("Logged out successfully.", is_error=False)
        store.token = None
        self.login_button.text = "Login to remote server"
        self.logout_button.visible = False
        self.update()
