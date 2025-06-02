"""
Account Selection Page for Supabase Integration
Displays user's MetaTrader accounts loaded from Supabase
"""

import flet
import asyncio
from typing import List, Dict, Optional
from Views.auth import supabase_auth
from Views.globals.app_logger import app_logger
from Views.globals.app_router import AppRoutes
from fletx import Xview


class AccountSelectionPageView(Xview):
    """
    Account Selection Page
    Shows user's MetaTrader accounts loaded from Supabase
    """

    def __init__(self, page=None, state=None, params=None):
        super().__init__(page, state, params)
        self.accounts = []
        self.user_id = None
        self.loading = True

    def build(self):
        """Build the account selection page"""

        async def load_accounts():
            """Load user accounts from Supabase"""
            try:
                # Get current user ID
                self.user_id = await supabase_auth.get_current_user_id()

                if not self.user_id:
                    app_logger.error("No authenticated user found")
                    self.go(AppRoutes.LOGIN_SUPABASE)
                    return

                # Load accounts
                app_logger.info(f"Loading accounts for user {self.user_id}")
                self.accounts = await supabase_auth.get_user_accounts(self.user_id)

                app_logger.info(f"Loaded {len(self.accounts)} accounts")

                # Update UI
                self.loading = False
                await self.refresh_accounts_display()

            except Exception as e:
                app_logger.error(f"Error loading accounts: {e}")
                self.loading = False
                self.show_error(f"Failed to load accounts: {str(e)}")

        async def refresh_accounts():
            """Refresh accounts from server"""
            refresh_button.disabled = True
            refresh_button.text = "Refreshing..."
            self.update()

            try:
                self.accounts = await supabase_auth.get_user_accounts(self.user_id)
                await self.refresh_accounts_display()
                self.show_success("Accounts refreshed successfully")

            except Exception as e:
                app_logger.error(f"Error refreshing accounts: {e}")
                self.show_error(f"Failed to refresh accounts: {str(e)}")

            finally:
                refresh_button.disabled = False
                refresh_button.text = "Refresh Accounts"
                self.update()

        async def on_account_select(account_id: str, account_name: str):
            """Handle account selection"""
            try:
                app_logger.info(
                    f"Account selected: {account_name} ({account_id})")

                # Navigate to bot selection for this account
                self.go(f"/bots/{self.user_id}/{account_id}")

            except Exception as e:
                app_logger.error(f"Error selecting account: {e}")
                self.show_error(f"Failed to select account: {str(e)}")

        async def on_logout(e):
            """Handle logout"""
            try:
                success, message = await supabase_auth.logout()
                if success:
                    app_logger.info("User logged out")
                    self.go(AppRoutes.LOGIN_SUPABASE)
                else:
                    self.show_error(f"Logout failed: {message}")

            except Exception as e:
                app_logger.error(f"Logout error: {e}")
                self.show_error("Logout failed")

        async def on_refresh(e):
            """Handle refresh button click"""
            await refresh_accounts()

        # UI Components
        page_title = flet.Text(
            value="Select Trading Account",
            style=flet.TextStyle(
                size=32,
                weight=flet.FontWeight.BOLD,
                color=flet.Colors.PRIMARY,
            ),
            text_align=flet.TextAlign.CENTER,
        )

        subtitle = flet.Text(
            value="Choose a MetaTrader account to start trading",
            style=flet.TextStyle(
                size=16,
                color=flet.Colors.ON_SURFACE_VARIANT,
            ),
            text_align=flet.TextAlign.CENTER,
        )

        # Refresh button
        refresh_button = flet.ElevatedButton(
            text="Refresh Accounts",
            icon=flet.Icons.REFRESH,
            on_click=on_refresh,
        )

        # Logout button
        logout_button = flet.TextButton(
            text="Logout",
            icon=flet.Icons.LOGOUT,
            on_click=on_logout,
        )

        # Header controls
        header_row = flet.Row(
            controls=[
                refresh_button,
                logout_button,
            ],
            alignment=flet.MainAxisAlignment.SPACE_BETWEEN,
            width=800,
        )

        # Loading indicator
        self.loading_indicator = flet.ProgressRing()

        # Status message
        self.status_message = flet.Text(
            value="",
            text_align=flet.TextAlign.CENTER,
            visible=False,
        )

        # Accounts container
        self.accounts_container = flet.Column(
            controls=[],
            spacing=15,
            horizontal_alignment=flet.CrossAxisAlignment.CENTER,
        )

        # Main content
        main_content = flet.Column(
            controls=[
                page_title,
                subtitle,
                flet.Container(height=30),
                header_row,
                flet.Container(height=20),
                self.loading_indicator if self.loading else flet.Container(),
                self.status_message,
                self.accounts_container,
            ],
            horizontal_alignment=flet.CrossAxisAlignment.CENTER,
            spacing=20,
        )

        # Load accounts on page load
        asyncio.create_task(load_accounts())

        return flet.View(
            horizontal_alignment=flet.CrossAxisAlignment.CENTER,
            vertical_alignment=flet.MainAxisAlignment.START,
            controls=[
                flet.Container(
                    content=main_content,
                    padding=flet.Padding(40, 40, 40, 40),
                    margin=flet.Margin(0, 40, 0, 40),
                )
            ],
            bgcolor="#f5f5f5",
            scroll=flet.ScrollMode.AUTO,
        )

    async def refresh_accounts_display(self):
        """Refresh the accounts display"""
        self.accounts_container.controls.clear()

        # Hide loading indicator
        self.loading_indicator.visible = False

        if not self.accounts:
            # No accounts found
            no_accounts_message = flet.Container(
                content=flet.Column(
                    controls=[
                        flet.Icon(
                            name=flet.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED,
                            size=64,
                            color=flet.Colors.ON_SURFACE_VARIANT,
                        ),
                        flet.Text(
                            value="No Trading Accounts Found",
                            style=flet.TextStyle(
                                size=20,
                                weight=flet.FontWeight.BOLD,
                                color=flet.Colors.ON_SURFACE_VARIANT,
                            ),
                        ),
                        flet.Text(
                            value="Please add a MetaTrader account through the web interface",
                            style=flet.TextStyle(
                                size=14,
                                color=flet.Colors.ON_SURFACE_VARIANT,
                            ),
                            text_align=flet.TextAlign.CENTER,
                        ),
                    ],
                    horizontal_alignment=flet.CrossAxisAlignment.CENTER,
                    spacing=15,
                ),
                padding=flet.Padding(40, 60, 40, 60),
                bgcolor="#ffffff",
                border_radius=12,
                width=600,
            )
            self.accounts_container.controls.append(no_accounts_message)
        else:
            # Display accounts
            for account in self.accounts:
                account_card = self.create_account_card(account)
                self.accounts_container.controls.append(account_card)

        self.update()

    def create_account_card(self, account: Dict) -> flet.Container:
        """Create an account card widget"""

        async def on_select():
            await on_account_select(account['id'], account['name'])

        async def on_account_select(account_id: str, account_name: str):
            """Handle account selection"""
            try:
                app_logger.info(
                    f"Account selected: {account_name} ({account_id})")

                # Navigate to bot selection for this account
                self.go(f"/bots/{self.user_id}/{account_id}")

            except Exception as e:
                app_logger.error(f"Error selecting account: {e}")
                self.show_error(f"Failed to select account: {str(e)}")

        # Account status color
        status = account.get('status', 'unknown').lower()
        if status == 'connected':
            status_color = flet.Colors.GREEN
            status_icon = flet.Icons.CHECK_CIRCLE
        elif status == 'disconnected':
            status_color = flet.Colors.RED
            status_icon = flet.Icons.ERROR
        elif status == 'trading':
            status_color = flet.Colors.BLUE
            status_icon = flet.Icons.TRENDING_UP
        else:
            status_color = flet.Colors.ORANGE
            status_icon = flet.Icons.WARNING

        # Account details
        account_info = flet.Column(
            controls=[
                flet.Row(
                    controls=[
                        flet.Text(
                            value=account.get('name', 'Unknown Account'),
                            style=flet.TextStyle(
                                size=18,
                                weight=flet.FontWeight.BOLD,
                            ),
                        ),
                        flet.Icon(
                            name=status_icon,
                            color=status_color,
                            size=20,
                        ),
                    ],
                    alignment=flet.MainAxisAlignment.SPACE_BETWEEN,
                ),
                flet.Text(
                    value=f"Account: {account.get('account_number', 'N/A')}",
                    style=flet.TextStyle(
                        size=14,
                        color=flet.Colors.ON_SURFACE_VARIANT,
                    ),
                ),
                flet.Text(
                    value=f"Broker: {account.get('broker', 'N/A')}",
                    style=flet.TextStyle(
                        size=14,
                        color=flet.Colors.ON_SURFACE_VARIANT,
                    ),
                ),
                flet.Text(
                    value=f"Server: {account.get('server', 'N/A')}",
                    style=flet.TextStyle(
                        size=14,
                        color=flet.Colors.ON_SURFACE_VARIANT,
                    ),
                ),
                flet.Row(
                    controls=[
                        flet.Text(
                            value=f"Balance: {account.get('currency', '$')} {account.get('balance', 0):,.2f}",
                            style=flet.TextStyle(
                                size=14,
                                weight=flet.FontWeight.BOLD,
                                color=flet.Colors.PRIMARY,
                            ),
                        ),
                        flet.Text(
                            value=f"Status: {status.title()}",
                            style=flet.TextStyle(
                                size=12,
                                color=status_color,
                            ),
                        ),
                    ],
                    alignment=flet.MainAxisAlignment.SPACE_BETWEEN,
                ),
            ],
            spacing=8,
        )

        # Select button
        select_button = flet.ElevatedButton(
            text="Select Account",
            icon=flet.Icons.ARROW_FORWARD,
            on_click=lambda e: asyncio.create_task(on_select()),
            style=flet.ButtonStyle(
                bgcolor=flet.Colors.PRIMARY,
                color=flet.Colors.ON_PRIMARY,
            ),
        )

        # Card container
        card = flet.Container(
            content=flet.Row(
                controls=[
                    flet.Container(
                        content=account_info,
                        expand=True,
                    ),
                    flet.Container(
                        content=select_button,
                        alignment=flet.alignment.center_right,
                    ),
                ],
                alignment=flet.MainAxisAlignment.SPACE_BETWEEN,
            ),
            padding=flet.Padding(25, 20, 25, 20),
            margin=flet.Margin(0, 0, 0, 15),
            bgcolor="#ffffff",
            border_radius=12,
            border=flet.Border(
                left=flet.BorderSide(width=4, color=status_color)
            ),
            shadow=flet.BoxShadow(
                spread_radius=1,
                blur_radius=8,
                color=flet.Colors.with_opacity(0.2, flet.Colors.SHADOW),
                offset=flet.Offset(0, 2),
            ),
            width=700,
            ink=True,
            on_click=lambda e: asyncio.create_task(on_select()),
        )

        return card

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
