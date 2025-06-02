"""
Bot Selection and Configuration Page for Phase 2
Allows users to select strategies, configure parameters, and launch trading systems
"""

import flet
import asyncio
import json
from typing import Dict, List, Optional, Any
from Views.auth import supabase_auth
from Views.globals.app_logger import app_logger
from Views.globals.app_router import AppRoutes
from fletx import Xview


class BotSelectionPageView(Xview):
    """
    Bot Selection and Configuration Page
    Shows available strategies with configuration options
    """

    def __init__(self, page, state, params):
        super().__init__(page, state, params)
        self.user_id = params.get('user', None)
        self.account_id = params.get('account', None)
        self.account_data = None
        self.selected_strategy = None
        self.strategy_config = {}
        self.available_strategies = self.get_available_strategies()

    def get_available_strategies(self) -> Dict[str, Dict]:
        """Get available trading strategies with their configurations"""
        return {
            "CycleTrader": {
                "name": "Cycle Trader v2",
                "description": "Advanced cycle-based trading strategy with auto-trade capabilities",
                "icon": flet.Icons.AUTORENEW,
                "color": flet.Colors.BLUE,
                "default_config": {
                    "lot_sizes": "0.01,0.02,0.03,0.04,0.05",
                    "take_profit": 5,
                    "max_cycles": 1,
                    "pips_step": 0,
                    "slippage": 3,
                    "zones": "500",
                    "zone_forward": 1,
                    "zone_forward2": 1,
                    "autotrade": False,
                    "autotrade_threshold": 0,
                    "auto_candle_close": False,
                    "candle_timeframe": "H1",
                    "hedge_sl": 100,
                    "prevent_opposing_trades": True,
                    "autotrade_pips_restriction": 100
                },
                "config_fields": [
                    {"name": "lot_sizes", "label": "Lot Sizes", "type": "text",
                        "hint": "Comma-separated values (e.g., 0.01,0.02,0.03)"},
                    {"name": "take_profit",
                        "label": "Take Profit ($)", "type": "number", "hint": "Profit target in USD"},
                    {"name": "max_cycles", "label": "Max Cycles",
                        "type": "number", "hint": "Maximum concurrent cycles"},
                    {"name": "autotrade", "label": "Auto Trade",
                        "type": "boolean", "hint": "Enable automatic trading"},
                    {"name": "autotrade_threshold", "label": "Auto Trade Threshold",
                        "type": "number", "hint": "Price threshold for auto trading"},
                    {"name": "auto_candle_close", "label": "Auto Candle Close",
                        "type": "boolean", "hint": "Close positions on candle close"},
                    {"name": "candle_timeframe", "label": "Candle Timeframe", "type": "select", "options": [
                        "M1", "M5", "M15", "M30", "H1", "H4", "D1"], "hint": "Timeframe for candle close"},
                    {"name": "zones", "label": "Zone Array", "type": "text",
                        "hint": "Comma-separated zone values"},
                    {"name": "prevent_opposing_trades", "label": "Prevent Opposing Trades",
                        "type": "boolean", "hint": "Prevent conflicting positions"}
                ]
            },
            "AdaptiveHedging": {
                "name": "Adaptive Hedging v2",
                "description": "Sophisticated hedging strategy with risk management and correlation analysis",
                "icon": flet.Icons.SHIELD,
                "color": flet.Colors.GREEN,
                "default_config": {
                    "hedge_distance": 50,
                    "lot_progression": "0.01,0.02,0.04,0.08,0.16,0.32",
                    "max_hedge_levels": 6,
                    "hedge_profit_target": 10,
                    "martingale_multiplier": 2.0,
                    "hedge_activation_loss": -5,
                    "max_drawdown": -100,
                    "auto_hedge": True,
                    "hedge_all_symbols": False,
                    "correlation_threshold": 0.8,
                    "daily_profit_target": 50,
                    "daily_loss_limit": -50
                },
                "config_fields": [
                    {"name": "hedge_distance",
                        "label": "Hedge Distance (Pips)", "type": "number", "hint": "Distance between hedge orders in pips"},
                    {"name": "lot_progression", "label": "Lot Progression", "type": "text",
                        "hint": "Comma-separated lot sizes for hedge levels"},
                    {"name": "max_hedge_levels", "label": "Max Hedge Levels",
                        "type": "number", "hint": "Maximum number of hedge levels"},
                    {"name": "hedge_profit_target",
                        "label": "Hedge Profit Target ($)", "type": "number", "hint": "Profit target for hedge cycles"},
                    {"name": "martingale_multiplier", "label": "Martingale Multiplier",
                        "type": "number", "hint": "Lot size multiplier for progression"},
                    {"name": "hedge_activation_loss",
                        "label": "Hedge Activation Loss ($)", "type": "number", "hint": "Loss threshold to activate hedging"},
                    {"name": "max_drawdown",
                        "label": "Max Drawdown ($)", "type": "number", "hint": "Emergency stop loss level"},
                    {"name": "auto_hedge", "label": "Auto Hedge",
                        "type": "boolean", "hint": "Enable automatic hedging"},
                    {"name": "daily_profit_target",
                        "label": "Daily Profit Target ($)", "type": "number", "hint": "Daily profit goal"},
                    {"name": "daily_loss_limit",
                        "label": "Daily Loss Limit ($)", "type": "number", "hint": "Daily loss limit"}
                ]
            }
        }

    def build(self):
        """Build the bot selection and configuration page"""

        async def load_account_data():
            """Load account data from Supabase"""
            try:
                if not self.account_id:
                    self.show_error("No account ID provided")
                    return

                account = await supabase_auth.get_account_by_id(self.account_id)
                if account:
                    self.account_data = account
                    await self.refresh_account_display()
                else:
                    self.show_error("Account not found")

            except Exception as e:
                app_logger.error(f"Error loading account data: {e}")
                self.show_error(f"Failed to load account: {str(e)}")

        async def on_strategy_select(strategy_key: str):
            """Handle strategy selection"""
            try:
                self.selected_strategy = strategy_key
                strategy_info = self.available_strategies[strategy_key]
                self.strategy_config = strategy_info['default_config'].copy()

                app_logger.info(f"Selected strategy: {strategy_info['name']}")
                await self.refresh_strategy_config()

            except Exception as e:
                app_logger.error(f"Error selecting strategy: {e}")
                self.show_error(f"Failed to select strategy: {str(e)}")

        async def on_config_change(field_name: str, value: Any):
            """Handle configuration field changes"""
            try:
                self.strategy_config[field_name] = value
                app_logger.info(f"Updated {field_name} = {value}")

            except Exception as e:
                app_logger.error(f"Error updating config: {e}")

        async def on_launch_bot(e):
            """Handle bot launch"""
            if not self.selected_strategy:
                self.show_error("Please select a strategy first")
                return

            if not self.account_data:
                self.show_error("Account data not loaded")
                return

            # Show loading state
            launch_button.disabled = True
            launch_button.text = "Launching..."
            launch_progress.visible = True
            self.update()

            try:
                # Create trading session
                session_id = await supabase_auth.create_trading_session(
                    self.user_id,
                    self.account_id,
                    [self.selected_strategy],
                    self.strategy_config
                )

                if session_id:
                    self.show_success("Trading system launched successfully!")

                    # Navigate to monitoring page
                    await asyncio.sleep(2)
                    self.go(
                        f"/monitor/{self.user_id}/{self.account_id}/{session_id}")
                else:
                    self.show_error("Failed to create trading session")

            except Exception as e:
                app_logger.error(f"Error launching bot: {e}")
                self.show_error(f"Failed to launch bot: {str(e)}")
            finally:
                launch_button.disabled = False
                launch_button.text = "Launch Trading System"
                launch_progress.visible = False
                self.update()

        async def on_back_to_accounts(e):
            """Navigate back to account selection"""
            self.go(AppRoutes.ACCOUNTS_SUPABASE)

        # Page title
        page_title = flet.Text(
            value="Select Trading Strategy",
            style=flet.TextStyle(
                size=32,
                weight=flet.FontWeight.BOLD,
                color=flet.Colors.PRIMARY,
            ),
            text_align=flet.TextAlign.CENTER,
        )

        # Account info banner
        self.account_banner = flet.Container(
            content=flet.Text(
                value="Loading account information...",
                text_align=flet.TextAlign.CENTER,
            ),
            padding=flet.Padding(20, 15, 20, 15),
            bgcolor=flet.Colors.SURFACE,
            border_radius=8,
            margin=flet.Margin(0, 0, 0, 20),
        )

        # Strategy selection cards
        self.strategy_cards = flet.Row(
            controls=[],
            alignment=flet.MainAxisAlignment.CENTER,
            spacing=20,
        )

        # Configuration panel
        self.config_panel = flet.Container(
            content=flet.Text(
                value="Select a strategy to configure",
                text_align=flet.TextAlign.CENTER,
                color=flet.Colors.ON_SURFACE_VARIANT,
            ),
            padding=flet.Padding(40, 40, 40, 40),
            bgcolor=flet.Colors.SURFACE,
            border_radius=12,
            visible=False,
        )

        # Launch button and progress
        launch_button = flet.ElevatedButton(
            text="Launch Trading System",
            icon=flet.Icons.ROCKET_LAUNCH,
            on_click=on_launch_bot,
            width=300,
            height=50,
            style=flet.ButtonStyle(
                bgcolor=flet.Colors.PRIMARY,
                color=flet.Colors.ON_PRIMARY,
                elevation=3,
            ),
        )

        launch_progress = flet.ProgressBar(
            visible=False,
            width=300,
        )

        # Back button
        back_button = flet.TextButton(
            text="← Back to Accounts",
            icon=flet.Icons.ARROW_BACK,
            on_click=on_back_to_accounts,
        )

        # Status message
        self.status_message = flet.Text(
            value="",
            text_align=flet.TextAlign.CENTER,
            visible=False,
        )

        # Build strategy cards
        self.build_strategy_cards(on_strategy_select)

        # Main content
        main_content = flet.Column(
            controls=[
                page_title,
                self.account_banner,
                flet.Text(
                    value="Choose a trading strategy:",
                    style=flet.TextStyle(
                        size=18, weight=flet.FontWeight.W_500),
                    text_align=flet.TextAlign.CENTER,
                ),
                self.strategy_cards,
                flet.Container(height=30),
                self.config_panel,
                flet.Container(height=20),
                launch_progress,
                launch_button,
                self.status_message,
                flet.Container(height=30),
                back_button,
            ],
            horizontal_alignment=flet.CrossAxisAlignment.CENTER,
            spacing=20,
        )

        # Load account data on page load
        asyncio.create_task(load_account_data())

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
            bgcolor=flet.Colors.SURFACE,
            scroll=flet.ScrollMode.AUTO,
        )

    def build_strategy_cards(self, on_select_callback):
        """Build strategy selection cards"""
        self.strategy_cards.controls.clear()

        for strategy_key, strategy_info in self.available_strategies.items():

            async def create_select_handler(key):
                return lambda e: asyncio.create_task(on_select_callback(key))

            card = flet.Container(
                content=flet.Column(
                    controls=[
                        flet.Icon(
                            name=strategy_info['icon'],
                            size=64,
                            color=strategy_info['color'],
                        ),
                        flet.Text(
                            value=strategy_info['name'],
                            style=flet.TextStyle(
                                size=18,
                                weight=flet.FontWeight.BOLD,
                            ),
                            text_align=flet.TextAlign.CENTER,
                        ),
                        flet.Text(
                            value=strategy_info['description'],
                            style=flet.TextStyle(
                                size=12,
                                color=flet.Colors.ON_SURFACE_VARIANT,
                            ),
                            text_align=flet.TextAlign.CENTER,
                        ),
                        flet.Container(height=10),
                        flet.ElevatedButton(
                            text="Select Strategy",
                            on_click=lambda e, key=strategy_key: asyncio.create_task(
                                on_select_callback(key)),
                            style=flet.ButtonStyle(
                                bgcolor=strategy_info['color'],
                                color=flet.Colors.ON_PRIMARY,
                            ),
                        ),
                    ],
                    horizontal_alignment=flet.CrossAxisAlignment.CENTER,
                    spacing=10,
                ),
                padding=flet.Padding(30, 30, 30, 30),
                bgcolor=flet.Colors.SURFACE,
                border_radius=15,
                border=flet.Border.all(width=1, color=flet.Colors.OUTLINE),
                shadow=flet.BoxShadow(
                    spread_radius=1,
                    blur_radius=8,
                    color=flet.Colors.with_opacity(0.2, flet.Colors.SHADOW),
                    offset=flet.Offset(0, 2),
                ),
                width=300,
                ink=True,
            )

            self.strategy_cards.controls.append(card)

    async def refresh_account_display(self):
        """Refresh account information display"""
        if not self.account_data:
            return

        account_info = flet.Row(
            controls=[
                flet.Icon(
                    name=flet.Icons.ACCOUNT_BALANCE_WALLET,
                    color=flet.Colors.PRIMARY,
                    size=24,
                ),
                flet.Column(
                    controls=[
                        flet.Text(
                            value=f"{self.account_data.get('name', 'Unknown Account')}",
                            style=flet.TextStyle(
                                size=16,
                                weight=flet.FontWeight.BOLD,
                            ),
                        ),
                        flet.Text(
                            value=f"Account: {self.account_data.get('account_number', 'N/A')} | "
                            f"Broker: {self.account_data.get('broker', 'N/A')} | "
                            f"Balance: {self.account_data.get('currency', '$')} {self.account_data.get('balance', 0):,.2f}",
                            style=flet.TextStyle(
                                size=12,
                                color=flet.Colors.ON_SURFACE_VARIANT,
                            ),
                        ),
                    ],
                    spacing=2,
                ),
            ],
            alignment=flet.MainAxisAlignment.CENTER,
            spacing=15,
        )

        self.account_banner.content = account_info
        self.update()

    async def refresh_strategy_config(self):
        """Refresh strategy configuration panel"""
        if not self.selected_strategy:
            return

        strategy_info = self.available_strategies[self.selected_strategy]

        # Configuration form controls
        config_controls = [
            flet.Text(
                value=f"Configure {strategy_info['name']}",
                style=flet.TextStyle(
                    size=20,
                    weight=flet.FontWeight.BOLD,
                ),
            ),
            flet.Container(height=20),
        ]

        # Add configuration fields
        for field in strategy_info['config_fields']:
            field_control = self.create_config_field(field)
            config_controls.append(field_control)
            config_controls.append(flet.Container(height=15))

        self.config_panel.content = flet.Column(
            controls=config_controls,
            spacing=10,
        )
        self.config_panel.visible = True
        self.update()

    def create_config_field(self, field_config: Dict) -> flet.Control:
        """Create a configuration field control"""
        field_name = field_config['name']
        field_label = field_config['label']
        field_type = field_config['type']
        field_hint = field_config.get('hint', '')

        current_value = self.strategy_config.get(field_name, '')

        if field_type == "text" or field_type == "number":
            return flet.TextField(
                label=field_label,
                hint_text=field_hint,
                value=str(current_value),
                keyboard_type=flet.KeyboardType.NUMBER if field_type == "number" else flet.KeyboardType.TEXT,
                on_change=lambda e, name=field_name: asyncio.create_task(
                    self.on_config_change(name, e.control.value)),
                width=400,
            )
        elif field_type == "boolean":
            return flet.Row(
                controls=[
                    flet.Switch(
                        label=field_label,
                        value=bool(current_value),
                        on_change=lambda e, name=field_name: asyncio.create_task(
                            self.on_config_change(name, e.control.value)),
                    ),
                    flet.Text(
                        value=field_hint,
                        style=flet.TextStyle(
                            size=12,
                            color=flet.Colors.ON_SURFACE_VARIANT,
                        ),
                    ),
                ],
                spacing=10,
            )
        elif field_type == "select":
            options = field_config.get('options', [])
            return flet.Dropdown(
                label=field_label,
                hint_text=field_hint,
                value=str(current_value),
                options=[flet.dropdown.Option(opt) for opt in options],
                on_change=lambda e, name=field_name: asyncio.create_task(
                    self.on_config_change(name, e.control.value)),
                width=400,
            )
        else:
            return flet.Text(f"Unknown field type: {field_type}")

    async def on_config_change(self, field_name: str, value: Any):
        """Handle configuration field changes"""
        try:
            # Convert value based on field type
            field_info = None
            for strategy_info in self.available_strategies.values():
                for field in strategy_info.get('config_fields', []):
                    if field['name'] == field_name:
                        field_info = field
                        break
                if field_info:
                    break

            if field_info:
                if field_info['type'] == 'number':
                    try:
                        value = float(value) if '.' in str(
                            value) else int(value)
                    except ValueError:
                        value = 0
                elif field_info['type'] == 'boolean':
                    value = bool(value)

            self.strategy_config[field_name] = value
            app_logger.info(f"Updated {field_name} = {value}")

        except Exception as e:
            app_logger.error(f"Error updating config: {e}")

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
