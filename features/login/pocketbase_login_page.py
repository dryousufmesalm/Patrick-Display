import flet
import asyncio
from features.auth import auth

from features.globals.app_logger import app_logger
from features.globals.app_router import AppRouter, AppRoutes
from DB.remote_login.repositories.remote_login_repo import RemoteLoginRepo
from DB.db_engine import engine
def build(page: flet.Page):
    page.title = "Login to remote server"
    login_page = LoginPageView()
    page.horizontal_alignment = flet.CrossAxisAlignment.CENTER
    page.vertical_alignment = flet.MainAxisAlignment.CENTER
    page.views.append(
        flet.View(
            AppRoutes.LOGIN_PB,
            [
                flet.Container(
                    content=login_page,
                    alignment=flet.alignment.center
                ),
            ],
        )
    )
    page.update()


class LoginPageView(flet.Column):
    def __init__(self):
        super().__init__()
        self.horizontal_alignment = flet.CrossAxisAlignment.CENTER
        self.alignment = flet.MainAxisAlignment.CENTER
        self.spacing = 20
        self.credentials= self.load_saved_credentials() 
        self.headline = flet.Text(
            value="Login to Patrick Server",
            style=flet.TextStyle(
                size=24,
                weight=flet.FontWeight.BOLD,
                color=flet.Colors.PRIMARY,
            ),
            text_align=flet.TextAlign.CENTER,
        )

        self.username = flet.TextField(label="Username", expand=False ,width=500,value=self.credentials.username if self.credentials is not None else "")
        self.password = flet.TextField(label="Password", password=True, width=500,value=self.credentials.password if self.credentials is not None else "")  
        self.login_button = flet.Button(
            text="Login",
            on_click=self.on_login,
            expand=False,
            width=200,
            color=flet.Colors.SECONDARY,
        )
       # back button
        self.back_button = flet.Button(
            text="< Return to Home",
            on_click=self.retuen_home ,
            expand=False,
            width=200,
            color=flet.Colors.TERTIARY,
        )

        self.program_path_text = flet.Text("")
        self.login_progress = flet.ProgressBar(visible=False)
        
        self.controls = [
            self.headline,
            self.username,
            self.password,
            self.login_button,
            self.program_path_text,
            self.login_progress,
            self.back_button,
        ]
        


    async def retuen_home(self, e):
        AppRouter.change_route(AppRoutes.HOME)
        self.update()
        
    async def on_login(self, e):
        self.login_progress.visible = True
        self.update()

        await asyncio.sleep(1)
        data: dict[str, any] = {
            "username": self.username.value,
            "password": self.password.value,
        }
        result = await auth.login(**data)
        self.login_progress.visible = False
        self.update()
        if result[0]:
            # TODO: navigate to the home page
            app_logger.info("Login successful, navigating to home page")
            remote_logger= RemoteLoginRepo(engine=engine)
            credentials = remote_logger.set_pb_credentials(data)
            AppRouter.change_route(AppRoutes.HOME)
            if result[1]:
                app_logger.info(msg=result[1])
        else:
            app_logger.error(msg=f"Login failed: {result[1]}")


    def load_saved_credentials(self):
        try:
            # Assuming `local_auth` has a method `get_credentials` returning a dict with keys 'username' and 'password'
            remote_logger= RemoteLoginRepo(engine=engine)
            credentials = remote_logger.get_pb_credintials()
            if credentials is None:
                return None
            
            return credentials
        except Exception as e:
            app_logger.error(f"Failed to load saved credentials: {e}")
            return None
