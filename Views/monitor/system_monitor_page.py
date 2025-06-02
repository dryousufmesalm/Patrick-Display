"""
System Monitoring Page for Phase 2
Real-time monitoring of active trading sessions with process management
"""

import flet
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from Views.auth import supabase_auth
from Views.globals.app_logger import app_logger
from Views.globals.app_router import AppRoutes
from services.process_manager import get_process_manager
from fletx import Xview


class SystemMonitorPageView(Xview):
    """
    System Monitoring Page
    Shows active trading sessions with real-time health metrics
    """

    def __init__(self, page, state, params):
        super().__init__(page, state, params)
        self.user_id = params.get('user', None)
        self.account_id = params.get('account', None)
        self.session_id = params.get('session', None)
        self.process_manager = None
        self.refresh_task = None
        self.active_sessions = {}
        self.refresh_interval = 5  # seconds

    def build(self):
        """Build the system monitoring page"""

        async def initialize_monitoring():
            """Initialize monitoring components"""
            try:
                self.process_manager = await get_process_manager()
                await self.start_refresh_task()
                app_logger.info("System monitoring initialized")

            except Exception as e:
                app_logger.error(f"Error initializing monitoring: {e}")
                self.show_error(f"Failed to initialize monitoring: {str(e)}")

        async def on_stop_session(session_id: str):
            """Handle session stop request"""
            try:
                if not self.process_manager:
                    self.show_error("Process manager not initialized")
                    return

                # Show confirmation dialog
                confirm_result = await self.show_confirmation(
                    "Stop Trading Session",
                    f"Are you sure you want to stop session {session_id[:8]}?"
                )

                if confirm_result:
                    success = await self.process_manager.stop_trading_system(session_id)
                    if success:
                        self.show_success(
                            "Trading session stopped successfully")
                        await self.refresh_sessions()
                    else:
                        self.show_error("Failed to stop trading session")

            except Exception as e:
                app_logger.error(f"Error stopping session: {e}")
                self.show_error(f"Failed to stop session: {str(e)}")

        async def on_restart_session(session_id: str):
            """Handle session restart request"""
            try:
                if not self.process_manager:
                    self.show_error("Process manager not initialized")
                    return

                await self.process_manager.restart_process(session_id)
                self.show_success("Trading session restart initiated")
                await self.refresh_sessions()

            except Exception as e:
                app_logger.error(f"Error restarting session: {e}")
                self.show_error(f"Failed to restart session: {str(e)}")

        async def on_refresh(e):
            """Handle manual refresh"""
            await self.refresh_sessions()

        async def on_back_to_bots(e):
            """Navigate back to bot selection"""
            if self.account_id:
                self.go(f"/bots/{self.user_id}/{self.account_id}")
            else:
                self.go(AppRoutes.ACCOUNTS_SUPABASE)

        async def on_stop_all(e):
            """Handle stop all sessions request"""
            try:
                if not self.process_manager:
                    self.show_error("Process manager not initialized")
                    return

                # Show confirmation dialog
                confirm_result = await self.show_confirmation(
                    "Stop All Trading Sessions",
                    "Are you sure you want to stop ALL active trading sessions?"
                )

                if confirm_result:
                    await self.process_manager.stop_all_systems()
                    self.show_success("All trading sessions stopped")
                    await self.refresh_sessions()

            except Exception as e:
                app_logger.error(f"Error stopping all sessions: {e}")
                self.show_error(f"Failed to stop all sessions: {str(e)}")

        # Page title
        page_title = flet.Text(
            value="Trading System Monitor",
            style=flet.TextStyle(
                size=32,
                weight=flet.FontWeight.BOLD,
                color=flet.Colors.PRIMARY,
            ),
            text_align=flet.TextAlign.CENTER,
        )

        # Controls header
        header_controls = flet.Row(
            controls=[
                flet.ElevatedButton(
                    text="Refresh",
                    icon=flet.Icons.REFRESH,
                    on_click=on_refresh,
                ),
                flet.ElevatedButton(
                    text="Stop All",
                    icon=flet.Icons.STOP,
                    on_click=on_stop_all,
                    style=flet.ButtonStyle(
                        bgcolor=flet.Colors.ERROR,
                        color=flet.Colors.ON_ERROR,
                    ),
                ),
                flet.TextButton(
                    text="← Back to Bots",
                    icon=flet.Icons.ARROW_BACK,
                    on_click=on_back_to_bots,
                ),
            ],
            alignment=flet.MainAxisAlignment.SPACE_BETWEEN,
            width=800,
        )

        # System overview
        self.overview_card = flet.Container(
            content=flet.Text(
                value="Loading system overview...",
                text_align=flet.TextAlign.CENTER,
            ),
            padding=flet.Padding(20, 15, 20, 15),
            bgcolor=flet.Colors.SURFACE,
            border_radius=8,
            margin=flet.Margin(0, 0, 0, 20),
        )

        # Active sessions container
        self.sessions_container = flet.Column(
            controls=[],
            spacing=15,
        )

        # Status message
        self.status_message = flet.Text(
            value="",
            text_align=flet.TextAlign.CENTER,
            visible=False,
        )

        # Main content
        main_content = flet.Column(
            controls=[
                page_title,
                header_controls,
                self.overview_card,
                flet.Text(
                    value="Active Trading Sessions:",
                    style=flet.TextStyle(size=20, weight=flet.FontWeight.BOLD),
                ),
                self.sessions_container,
                self.status_message,
            ],
            horizontal_alignment=flet.CrossAxisAlignment.CENTER,
            spacing=20,
        )

        # Initialize monitoring
        asyncio.create_task(initialize_monitoring())

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

    async def start_refresh_task(self):
        """Start the automatic refresh task"""
        if self.refresh_task and not self.refresh_task.done():
            self.refresh_task.cancel()

        self.refresh_task = asyncio.create_task(self.auto_refresh_loop())

    async def auto_refresh_loop(self):
        """Automatic refresh loop"""
        try:
            while True:
                await self.refresh_sessions()
                await asyncio.sleep(self.refresh_interval)

        except asyncio.CancelledError:
            app_logger.info("Auto refresh task cancelled")
        except Exception as e:
            app_logger.error(f"Error in auto refresh loop: {e}")

    async def refresh_sessions(self):
        """Refresh session data and update UI"""
        try:
            if not self.process_manager:
                return

            # Get active sessions from process manager
            self.active_sessions = await self.process_manager.get_active_sessions()

            # Update overview
            await self.update_overview()

            # Update sessions display
            await self.update_sessions_display()

        except Exception as e:
            app_logger.error(f"Error refreshing sessions: {e}")

    async def update_overview(self):
        """Update system overview display"""
        try:
            total_sessions = len(self.active_sessions)
            running_sessions = sum(1 for session in self.active_sessions.values()
                                   if session['status'] == 'running')

            total_memory = sum(session.get('memory_mb', 0)
                               for session in self.active_sessions.values())
            avg_cpu = sum(session.get('cpu_percent', 0)
                          for session in self.active_sessions.values()) / max(1, total_sessions)

            overview_info = flet.Row(
                controls=[
                    self.create_stat_card("Total Sessions", str(
                        total_sessions), flet.Icons.DASHBOARD, flet.Colors.BLUE),
                    self.create_stat_card("Running", str(
                        running_sessions), flet.Icons.PLAY_CIRCLE, flet.Colors.GREEN),
                    self.create_stat_card(
                        "Memory Usage", f"{total_memory:.1f} MB", flet.Icons.MEMORY, flet.Colors.ORANGE),
                    self.create_stat_card(
                        "Avg CPU", f"{avg_cpu:.1f}%", flet.Icons.SPEED, flet.Colors.PURPLE),
                ],
                alignment=flet.MainAxisAlignment.SPACE_AROUND,
                spacing=20,
            )

            self.overview_card.content = overview_info
            self.update()

        except Exception as e:
            app_logger.error(f"Error updating overview: {e}")

    def create_stat_card(self, title: str, value: str, icon: str, color: str) -> flet.Container:
        """Create a statistics card"""
        return flet.Container(
            content=flet.Column(
                controls=[
                    flet.Icon(
                        name=icon,
                        color=color,
                        size=32,
                    ),
                    flet.Text(
                        value=title,
                        style=flet.TextStyle(
                            size=12,
                            color=flet.Colors.ON_SURFACE_VARIANT,
                        ),
                        text_align=flet.TextAlign.CENTER,
                    ),
                    flet.Text(
                        value=value,
                        style=flet.TextStyle(
                            size=18,
                            weight=flet.FontWeight.BOLD,
                        ),
                        text_align=flet.TextAlign.CENTER,
                    ),
                ],
                horizontal_alignment=flet.CrossAxisAlignment.CENTER,
                spacing=5,
            ),
            padding=flet.Padding(15, 15, 15, 15),
            bgcolor=flet.Colors.SURFACE,
            border_radius=8,
            width=150,
        )

    async def update_sessions_display(self):
        """Update the sessions display"""
        try:
            self.sessions_container.controls.clear()

            if not self.active_sessions:
                # No active sessions
                no_sessions_card = flet.Container(
                    content=flet.Column(
                        controls=[
                            flet.Icon(
                                name=flet.Icons.HOURGLASS_EMPTY,
                                size=64,
                                color=flet.Colors.ON_SURFACE_VARIANT,
                            ),
                            flet.Text(
                                value="No Active Trading Sessions",
                                style=flet.TextStyle(
                                    size=20,
                                    weight=flet.FontWeight.BOLD,
                                    color=flet.Colors.ON_SURFACE_VARIANT,
                                ),
                            ),
                            flet.Text(
                                value="Start a new trading session from the bot selection page",
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
                    bgcolor=flet.Colors.SURFACE,
                    border_radius=12,
                    width=700,
                )
                self.sessions_container.controls.append(no_sessions_card)
            else:
                # Display active sessions
                for session_id, session_info in self.active_sessions.items():
                    session_card = self.create_session_card(
                        session_id, session_info)
                    self.sessions_container.controls.append(session_card)

            self.update()

        except Exception as e:
            app_logger.error(f"Error updating sessions display: {e}")

    def create_session_card(self, session_id: str, session_info: Dict) -> flet.Container:
        """Create a session monitoring card"""

        async def on_stop_click():
            await self.on_stop_session(session_id)

        async def on_restart_click():
            await self.on_restart_session(session_id)

        # Status color and icon
        status = session_info.get('status', 'unknown')
        if status == 'running':
            status_color = flet.Colors.GREEN
            status_icon = flet.Icons.PLAY_CIRCLE
        elif status in ['stopping', 'stopped']:
            status_color = flet.Colors.RED
            status_icon = flet.Icons.STOP_CIRCLE
        elif status == 'restarting':
            status_color = flet.Colors.ORANGE
            status_icon = flet.Icons.RESTART_ALT
        else:
            status_color = flet.Colors.GREY
            status_icon = flet.Icons.HELP

        # Calculate uptime
        started_at = datetime.fromisoformat(
            session_info['started_at'].replace('Z', '+00:00'))
        uptime = datetime.utcnow() - started_at.replace(tzinfo=None)
        uptime_str = self.format_timedelta(uptime)

        # Session details
        config = session_info.get('config', {})
        strategies = config.get('strategies', [])

        session_details = flet.Column(
            controls=[
                flet.Row(
                    controls=[
                        flet.Text(
                            value=f"Session {session_id[:8]}...",
                            style=flet.TextStyle(
                                size=16,
                                weight=flet.FontWeight.BOLD,
                            ),
                        ),
                        flet.Row(
                            controls=[
                                flet.Icon(
                                    name=status_icon,
                                    color=status_color,
                                    size=20,
                                ),
                                flet.Text(
                                    value=status.title(),
                                    style=flet.TextStyle(
                                        color=status_color,
                                        weight=flet.FontWeight.BOLD,
                                    ),
                                ),
                            ],
                            spacing=5,
                        ),
                    ],
                    alignment=flet.MainAxisAlignment.SPACE_BETWEEN,
                ),
                flet.Row(
                    controls=[
                        flet.Text(
                            value=f"Account: {config.get('account_id', 'N/A')}",
                            style=flet.TextStyle(
                                size=12, color=flet.Colors.ON_SURFACE_VARIANT),
                        ),
                        flet.Text(
                            value=f"Strategies: {', '.join(strategies)}",
                            style=flet.TextStyle(
                                size=12, color=flet.Colors.ON_SURFACE_VARIANT),
                        ),
                    ],
                    spacing=20,
                ),
                flet.Row(
                    controls=[
                        flet.Text(
                            value=f"Uptime: {uptime_str}",
                            style=flet.TextStyle(
                                size=12, color=flet.Colors.ON_SURFACE_VARIANT),
                        ),
                        flet.Text(
                            value=f"PID: {session_info.get('pid', 'N/A')}",
                            style=flet.TextStyle(
                                size=12, color=flet.Colors.ON_SURFACE_VARIANT),
                        ),
                        flet.Text(
                            value=f"Restarts: {session_info.get('restart_count', 0)}",
                            style=flet.TextStyle(
                                size=12, color=flet.Colors.ON_SURFACE_VARIANT),
                        ),
                    ],
                    spacing=20,
                ),
            ],
            spacing=8,
        )

        # Performance metrics
        cpu_percent = session_info.get('cpu_percent', 0)
        memory_mb = session_info.get('memory_mb', 0)

        metrics = flet.Row(
            controls=[
                flet.Container(
                    content=flet.Column(
                        controls=[
                            flet.Text(
                                value="CPU",
                                style=flet.TextStyle(
                                    size=10, color=flet.Colors.ON_SURFACE_VARIANT),
                                text_align=flet.TextAlign.CENTER,
                            ),
                            flet.Text(
                                value=f"{cpu_percent:.1f}%",
                                style=flet.TextStyle(
                                    size=14, weight=flet.FontWeight.BOLD),
                                text_align=flet.TextAlign.CENTER,
                            ),
                        ],
                        spacing=2,
                    ),
                    width=60,
                ),
                flet.Container(
                    content=flet.Column(
                        controls=[
                            flet.Text(
                                value="Memory",
                                style=flet.TextStyle(
                                    size=10, color=flet.Colors.ON_SURFACE_VARIANT),
                                text_align=flet.TextAlign.CENTER,
                            ),
                            flet.Text(
                                value=f"{memory_mb:.0f}MB",
                                style=flet.TextStyle(
                                    size=14, weight=flet.FontWeight.BOLD),
                                text_align=flet.TextAlign.CENTER,
                            ),
                        ],
                        spacing=2,
                    ),
                    width=80,
                ),
            ],
            spacing=10,
        )

        # Control buttons
        controls = flet.Row(
            controls=[
                flet.ElevatedButton(
                    text="Stop",
                    icon=flet.Icons.STOP,
                    on_click=lambda e: asyncio.create_task(on_stop_click()),
                    style=flet.ButtonStyle(
                        bgcolor=flet.Colors.ERROR,
                        color=flet.Colors.ON_ERROR,
                    ),
                    disabled=(status != 'running'),
                ),
                flet.ElevatedButton(
                    text="Restart",
                    icon=flet.Icons.RESTART_ALT,
                    on_click=lambda e: asyncio.create_task(on_restart_click()),
                    disabled=(status not in ['running', 'error']),
                ),
            ],
            spacing=10,
        )

        # Session card
        card = flet.Container(
            content=flet.Row(
                controls=[
                    flet.Container(
                        content=session_details,
                        expand=True,
                    ),
                    flet.Container(
                        content=metrics,
                        width=150,
                    ),
                    flet.Container(
                        content=controls,
                        width=200,
                    ),
                ],
                alignment=flet.MainAxisAlignment.SPACE_BETWEEN,
            ),
            padding=flet.Padding(25, 20, 25, 20),
            margin=flet.Margin(0, 0, 0, 15),
            bgcolor=flet.Colors.SURFACE,
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
            width=800,
        )

        return card

    def format_timedelta(self, td: timedelta) -> str:
        """Format a timedelta to a readable string"""
        total_seconds = int(td.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"

    async def show_confirmation(self, title: str, message: str) -> bool:
        """Show a confirmation dialog"""
        # For now, return True (would implement actual dialog in full version)
        return True

    async def on_stop_session(self, session_id: str):
        """Handle session stop request"""
        try:
            if not self.process_manager:
                self.show_error("Process manager not initialized")
                return

            success = await self.process_manager.stop_trading_system(session_id)
            if success:
                self.show_success("Trading session stopped successfully")
                await self.refresh_sessions()
            else:
                self.show_error("Failed to stop trading session")

        except Exception as e:
            app_logger.error(f"Error stopping session: {e}")
            self.show_error(f"Failed to stop session: {str(e)}")

    async def on_restart_session(self, session_id: str):
        """Handle session restart request"""
        try:
            if not self.process_manager:
                self.show_error("Process manager not initialized")
                return

            await self.process_manager.restart_process(session_id)
            self.show_success("Trading session restart initiated")
            await self.refresh_sessions()

        except Exception as e:
            app_logger.error(f"Error restarting session: {e}")
            self.show_error(f"Failed to restart session: {str(e)}")

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

    def cleanup(self):
        """Cleanup when page is destroyed"""
        if self.refresh_task and not self.refresh_task.done():
            self.refresh_task.cancel()
