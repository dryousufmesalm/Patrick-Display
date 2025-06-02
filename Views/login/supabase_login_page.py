"""
Supabase Login Page for Flet UI
Modern authentication interface with Supabase backend
"""

import flet
import asyncio
from typing import Optional, Dict, Any
from Views.auth import supabase_auth
from Views.globals.app_logger import app_logger
from Views.globals.app_router import AppRoutes
from fletx import Xview


class SupabaseLoginPageView(Xview):
    """
    Modern Supabase Login Page
    Provides email/password authentication with session management
    """

    def __init__(self, page=None, state=None, params=None):
        super().__init__(page, state, params)
        self.login_in_progress = False

    def build(self):
        """Build the login page UI"""

        def return_home(e):
            """Navigate back to home page"""
            self.go(AppRoutes.HOME)
            self.update()

        def on_login(e):
            """Handle login button click"""
            if self.login_in_progress:
                return

            # Validate input
            if not email_field.value or not email_field.value.strip():
                self.show_error("Please enter your email address")
                return

            if not password_field.value or not password_field.value.strip():
                self.show_error("Please enter your password")
                return

            # Show loading state
            self.login_in_progress = True
            login_progress.visible = True
            login_button.text = "Logging in..."
            login_button.disabled = True
            self.update()

            try:
                # Simulate minimum loading time for better UX
                import time
                time.sleep(0.5)

                # Attempt login using sync wrapper to avoid event loop conflicts
                success, message = supabase_auth.login_sync(
                    email_field.value.strip(),
                    password_field.value
                )

                if success:
                    app_logger.info(
                        f"Login successful for {email_field.value}")
                    self.show_success("Login successful! Redirecting...")

                    # Small delay before navigation
                    time.sleep(1)

                    # Navigate to home page
                    self.go(AppRoutes.HOME)
                else:
                    app_logger.error(
                        f"Login failed for {email_field.value}: {message}")
                    self.show_error(f"Login failed: {message}")

            except Exception as e:
                app_logger.error(f"Login error: {e}")
                self.show_error(
                    "An unexpected error occurred. Please try again.")

            finally:
                # Hide loading state
                self.login_in_progress = False
                login_progress.visible = False
                login_button.text = "Login"
                login_button.disabled = False
                self.update()

        def on_forgot_password(e):
            """Handle forgot password click"""
            self.show_info("Password reset functionality will be added soon.")

        def on_create_account(e):
            """Handle create account click"""
            self.show_info(
                "Please visit our website to create a new account. Once created, you can use those same credentials here.")

        def on_email_submit(e):
            """Handle Enter key in email field"""
            password_field.focus()

        def on_password_submit(e):
            """Handle Enter key in password field"""
            # For Flet, we can trigger the button click directly
            login_button.on_click(e)

        # UI Components
        page_title = flet.Text(
            value="Peaceful Investment Trading System",
            style=flet.TextStyle(
                size=28,
                weight=flet.FontWeight.BOLD,
                color=flet.Colors.PRIMARY,
            ),
            text_align=flet.TextAlign.CENTER,
        )

        subtitle = flet.Text(
            value="Use your website account to access the trading platform",
            style=flet.TextStyle(
                size=16,
                color=flet.Colors.ON_SURFACE_VARIANT,
            ),
            text_align=flet.TextAlign.CENTER,
        )

        # Email field
        email_field = flet.TextField(
            label="Email Address",
            hint_text="Enter your email address",
            prefix_icon=flet.Icons.EMAIL,
            keyboard_type=flet.KeyboardType.EMAIL,
            width=400,
            on_submit=on_email_submit,
            autofocus=True,
        )

        # Password field
        password_field = flet.TextField(
            label="Password",
            hint_text="Enter your password",
            prefix_icon=flet.Icons.LOCK,
            password=True,
            can_reveal_password=True,
            width=400,
            on_submit=on_password_submit,
        )

        # Login button
        login_button = flet.ElevatedButton(
            text="Login",
            on_click=on_login,
            width=400,
            height=50,
            style=flet.ButtonStyle(
                bgcolor=flet.Colors.PRIMARY,
                color=flet.Colors.ON_PRIMARY,
                elevation=2,
            ),
        )

        # Progress indicator
        login_progress = flet.ProgressBar(
            visible=False,
            width=400,
        )

        # Additional options
        forgot_password_button = flet.TextButton(
            text="Forgot Password?",
            on_click=on_forgot_password,
        )

        create_account_button = flet.TextButton(
            text="Need an account? Create one on our website",
            on_click=on_create_account,
        )

        # Back button
        back_button = flet.TextButton(
            text="← Return to Home",
            on_click=return_home,
            icon=flet.Icons.HOME,
        )

        # Status message
        self.status_message = flet.Text(
            value="",
            text_align=flet.TextAlign.CENTER,
            visible=False,
        )

        # Main container
        login_container = flet.Container(
            content=flet.Column(
                controls=[
                    page_title,
                    subtitle,
                    flet.Container(height=30),  # Spacer
                    email_field,
                    password_field,
                    login_progress,
                    login_button,
                    flet.Container(height=20),  # Spacer
                    flet.Row(
                        controls=[
                            forgot_password_button,
                            create_account_button,
                        ],
                        alignment=flet.MainAxisAlignment.SPACE_BETWEEN,
                        width=400,
                    ),
                    self.status_message,
                    flet.Container(height=30),  # Spacer
                    back_button,
                ],
                horizontal_alignment=flet.CrossAxisAlignment.CENTER,
                spacing=15,
            ),
            padding=flet.Padding(40, 60, 40, 40),
            bgcolor="#ffffff",
            border_radius=12,
            shadow=flet.BoxShadow(
                spread_radius=1,
                blur_radius=15,
                color=flet.Colors.with_opacity(0.3, flet.Colors.SHADOW),
                offset=flet.Offset(0, 4),
            ),
        )

        # App info footer
        app_info = flet.Container(
            content=flet.Column(
                controls=[
                    flet.Text(
                        value="Peaceful Investment Trading Platform v2.0",
                        style=flet.TextStyle(
                            size=12,
                            color=flet.Colors.ON_SURFACE_VARIANT,
                        ),
                        text_align=flet.TextAlign.CENTER,
                    ),
                    flet.Text(
                        value="Unified authentication with website • Real-time MetaTrader 5 integration",
                        style=flet.TextStyle(
                            size=10,
                            color=flet.Colors.ON_SURFACE_VARIANT,
                        ),
                        text_align=flet.TextAlign.CENTER,
                    ),
                ],
                horizontal_alignment=flet.CrossAxisAlignment.CENTER,
                spacing=5,
            ),
            margin=flet.Margin(0, 40, 0, 0),
        )

        return flet.View(
            horizontal_alignment=flet.CrossAxisAlignment.CENTER,
            vertical_alignment=flet.MainAxisAlignment.CENTER,
            controls=[
                login_container,
                app_info,
            ],
            bgcolor="#f5f5f5",
        )

    def show_error(self, message: str):
        """Show error message"""
        self.status_message.value = message
        self.status_message.color = flet.Colors.ERROR
        self.status_message.visible = True
        self.update()

    def show_success(self, message: str):
        """Show success message"""
        self.status_message.value = message
        self.status_message.color = flet.Colors.PRIMARY
        self.status_message.visible = True
        self.update()

    def show_info(self, message: str):
        """Show info message"""
        self.status_message.value = message
        self.status_message.color = flet.Colors.ON_SURFACE_VARIANT
        self.status_message.visible = True
        self.update()

    def clear_message(self):
        """Clear status message"""
        self.status_message.visible = False
        self.update()


class QuickLoginView(Xview):
    """
    Quick login view for development/testing
    Pre-fills common test credentials
    """

    def __init__(self, page=None, state=None, params=None):
        super().__init__(page, state, params)

    def build(self):
        """Build quick login UI for testing"""

        async def quick_login(email: str, password: str):
            """Perform quick login with pre-set credentials"""
            try:
                success, message = await supabase_auth.login(email, password)

                if success:
                    app_logger.info(f"Quick login successful for {email}")
                    self.go(AppRoutes.HOME)
                else:
                    app_logger.error(f"Quick login failed: {message}")

            except Exception as e:
                app_logger.error(f"Quick login error: {e}")

        async def on_test_user_1(e):
            await quick_login("test@example.com", "testpassword")

        async def on_test_user_2(e):
            await quick_login("admin@example.com", "adminpassword")

        async def on_regular_login(e):
            self.go("/login")

        return flet.View(
            horizontal_alignment=flet.CrossAxisAlignment.CENTER,
            vertical_alignment=flet.MainAxisAlignment.CENTER,
            controls=[
                flet.Text(
                    value="Quick Login (Development)",
                    style=flet.TextStyle(size=24, weight=flet.FontWeight.BOLD),
                ),
                flet.Container(height=30),
                flet.ElevatedButton(
                    text="Test User 1",
                    on_click=on_test_user_1,
                    width=200,
                ),
                flet.ElevatedButton(
                    text="Admin User",
                    on_click=on_test_user_2,
                    width=200,
                ),
                flet.Container(height=20),
                flet.TextButton(
                    text="Regular Login",
                    on_click=on_regular_login,
                ),
            ],
        )
