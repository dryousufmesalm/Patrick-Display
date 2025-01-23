import flet
import asyncio
from features.auth import auth
from features.globals.app_logger import app_logger
from features.globals.app_router import AppRouter, AppRoutes
from DB.mt5_login.repositories.mt5_login_repo  import MT5LoginRepo
from DB.db_engine import engine

def build(page: flet.Page):
    page.title = "Login to MT5"
    login_page = LoginPageView()
    page.overlay.append(login_page.program_path_picker_dialog)
    page.views.append(
        flet.View(
            AppRoutes.LOGIN_MT5,
            [
                login_page,
            ],
        )
    )
    # page.add(
    #     flet.Container(
    #         content=login_page,
    #     )
    # )
    page.update()


class LoginPageView(flet.Column):
    def __init__(self):
        super().__init__()
        self.horizontal_alignment = flet.CrossAxisAlignment.CENTER
        self.alignment = flet.MainAxisAlignment.CENTER
        self.spacing = 20
      # Load saved credentials
        self.credentials= self.load_saved_credentials()
        self.headline = flet.Text(
            value="Login to Metatrader 5 ",
            style=flet.TextStyle(
                size=24,
                weight=flet.FontWeight.BOLD,
                color=flet.Colors.PRIMARY,
            ),
            text_align=flet.TextAlign.CENTER,
        )

        self.username = flet.TextField(label="Username", expand=False ,width=500,value=self.credentials.username if self.credentials is not None else "")
        self.password = flet.TextField(label="Password", password=True, width=500,value=self.credentials.password if self.credentials is not None else "")
        self.server = flet.TextField(label="Server", expand=False ,width=500,value=self.credentials.server if self.credentials is not None else "")
        self.program_path_picker_dialog = flet.FilePicker(
            on_result=self.on_program_path_picker_pressed,
        )
        self.select_program_path_button = flet.Button(
            text="Select Program Path",
            icon=flet.Icons.UPLOAD_FILE,
            on_click=lambda _: self.program_path_picker_dialog.pick_files(
                allow_multiple=False,
            ),
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
            self.server,
            flet.Row(
                controls=[
                    self.select_program_path_button,
                    flet.Button(
                        text="Login",
                        on_click=self.on_login,
                        expand=False,
                        width=200,
                        color=flet.Colors.SECONDARY,
                    ),
                ],
                alignment=flet.MainAxisAlignment.CENTER,
            ),
            self.program_path_text,
            self.login_progress,
            self.back_button,
        ]
        

    def on_program_path_picker_pressed(self, e: flet.FilePickerResultEvent):
        if e.files:
            self.program_path_text.value = e.files[0].path
        else:
            self.program_path_text.value = "Cancelled!"
        self.program_path_text.update()
    async def retuen_home(self, e):
        AppRouter.change_route(AppRoutes.HOME)
        self.update()
        
    async def on_login(self, event):
        self.login_progress.visible = True
        self.update()

        await asyncio.sleep(1)
        data: dict[str, any] = {
            "username": self.username.value,
            "password": self.password.value,
            "server": self.server.value,
            "program_path": self.program_path_text.value,
   
        }
        result = await auth.launch_metatrader(**data)
        
        self.login_progress.visible = False
        self.update()
        if result:
            # TODO: navigate to the home page
            app_logger.info("Login successful, navigating to home page")
            AppRouter.change_route(AppRoutes.HOME)
            mt5_logger=MT5LoginRepo(engine=engine)
            mt5_logger.set_mt5_credentials(data)
            
        else:
            app_logger.error(msg=f"Login failed")
    def load_saved_credentials(self):
        try:
            mt5_logger=MT5LoginRepo(engine=engine)
            
            # Assuming `local_auth` has a method `get_credentials` returning a dict with keys 'username' and 'password'
            credentials = mt5_logger.get_mt5_credentials()
            if credentials is None:
                return None
            
            return credentials
        except Exception as e:
            app_logger.error(f"Failed to load saved credentials: {e}")
            return None
