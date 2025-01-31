import flet
import asyncio
from Views.auth import auth
from Views.globals.app_logger import app_logger
from Views.globals.app_router import AppRouter, AppRoutes
from DB.mt5_login.repositories.mt5_login_repo import MT5LoginRepo
from DB.db_engine import engine
from fletx import Xview


class Mt5LoginPageView(Xview):

    # Load saved credentials

    def build(self):
        user_id = self.get_param('user')
        account = self.get_param('account')

        def on_program_path_picker_pressed(e: flet.FilePickerResultEvent):
            if e.files:
                program_path_text.value = e.files[0].path
            else:
                program_path_text.value = "Cancelled!"
            program_path_text.update()

        async def return_back(e):
            self.back()

        async def on_login(e):
            login_progress.visible = True
            login_progress.update()
            await asyncio.sleep(1)
            data: dict[str, any] = {
                "username":   username.value,
                "password":   password.value,
                "server":   server.value,
                "program_path":   program_path_text.value,
                "user": user_id,
                "account": account,

            }
            result = await auth.launch_metatrader(**data)

            login_progress.visible = False

            if result:
                # TODO: navigate to the home page
                app_logger.info("Login successful, navigating to home page")
                self.back()
                mt5_logger = MT5LoginRepo(engine=engine)
                mt5_logger.set_mt5_credentials(data)

            else:
                app_logger.error(msg=f"Login failed")

        def load_saved_credentials():
            try:
                mt5_logger = MT5LoginRepo(engine=engine)

                # Assuming `local_auth` has a method `get_credentials` returning a dict with keys 'username' and 'password'
                credentials = mt5_logger.get_mt5_credentials()
                if credentials is None:
                    return None

                return credentials
            except Exception as e:
                app_logger.error(f"Failed to load saved credentials: {e}")
                return None
        credentials = load_saved_credentials()
        headline = flet.Text(
            value="Login to Metatrader 5 ",
            style=flet.TextStyle(
                size=24,
                weight=flet.FontWeight.BOLD,
                color=flet.Colors.PRIMARY,
            ),
            text_align=flet.TextAlign.CENTER,
        )

        username = flet.TextField(label="Username", expand=False, width=500,
                                        value=credentials.username if credentials is not None else "")
        password = flet.TextField(label="Password", password=True, width=500,
                                        value=credentials.password if credentials is not None else "")
        server = flet.TextField(label="Server", expand=False, width=500,
                                value=credentials.server if credentials is not None else "")
        program_path_picker_dialog = flet.FilePicker(
            on_result=on_program_path_picker_pressed,
        )

        select_program_path_button = flet.Button(
            text="Select Program Path",
            icon=flet.Icons.UPLOAD_FILE,
            on_click=lambda _:   program_path_picker_dialog.pick_files(
                allow_multiple=False,
            ),
        )
        # back button
        back_button = flet.Button(
            text="< Return to Home",
            on_click=return_back,
            expand=False,
            width=200,
            color=flet.Colors.TERTIARY,
        )

        program_path_text = flet.Text(
            value=credentials.program_path if credentials is not None else "",
        )
        login_progress = flet.ProgressBar(visible=False)
        return flet.View(
            horizontal_alignment=flet.CrossAxisAlignment.CENTER,
            vertical_alignment=flet.MainAxisAlignment.CENTER,
            controls=[
                headline,
                username,
                password,
                server,
                program_path_picker_dialog,
                flet.Row(
                    controls=[
                        select_program_path_button,
                        flet.Button(
                            text="Login",
                            on_click=on_login,
                            expand=False,
                            width=200,
                            color=flet.Colors.SECONDARY,
                        ),
                    ],
                    alignment=flet.MainAxisAlignment.CENTER,
                ),
                program_path_text,
                login_progress,
                back_button,
            ]
        )
