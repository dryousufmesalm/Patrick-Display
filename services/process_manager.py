"""
Process Management Service for Trading Systems
Handles launching, monitoring, and managing multiple trading system processes
"""

import asyncio
import subprocess
import logging
import os
import signal
import psutil
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
from services.supabase_auth_service import get_auth_service

logger = logging.getLogger(__name__)


class TradingProcessManager:
    """
    Manages multiple trading system processes
    Handles launching, monitoring, and cleanup
    """

    def __init__(self):
        self.active_processes: Dict[str, Dict] = {}
        self.process_configs: Dict[str, Dict] = {}
        self.monitoring_tasks: Dict[str, asyncio.Task] = {}
        self.auth_service = None
        self.base_path = Path(__file__).parent.parent
        self.start_time = datetime.utcnow()

    async def initialize(self):
        """Initialize the process manager"""
        try:
            self.auth_service = await get_auth_service()
            logger.info("Trading Process Manager initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize process manager: {e}")
            return False

    async def launch_trading_system(self, session_id: str, user_id: str, account_id: str,
                                    strategies: List[str], config: Dict) -> bool:
        """
        Launch a new trading system process

        Args:
            session_id: Unique session ID
            user_id: User ID from Supabase
            account_id: MetaTrader account ID
            strategies: List of strategy names to run
            config: Strategy configuration parameters

        Returns:
            bool: True if launch successful, False otherwise
        """
        try:
            if session_id in self.active_processes:
                logger.warning(f"Trading system {session_id} already running")
                return False

            # Prepare process configuration
            process_config = {
                'session_id': session_id,
                'user_id': user_id,
                'account_id': account_id,
                'strategies': strategies,
                'config': config,
                'started_at': datetime.utcnow().isoformat(),
                'status': 'starting'
            }

            # Create process launch command
            launch_command = self.create_launch_command(process_config)

            if not launch_command:
                logger.error("Failed to create launch command")
                return False

            # Launch the process
            process = await self.start_process(launch_command, process_config)

            if process:
                # Store process information
                self.active_processes[session_id] = {
                    'process': process,
                    'config': process_config,
                    'status': 'running',
                    'started_at': datetime.utcnow(),
                    'last_heartbeat': datetime.utcnow(),
                    'restart_count': 0
                }

                # Start monitoring task
                monitor_task = asyncio.create_task(
                    self.monitor_process(session_id)
                )
                self.monitoring_tasks[session_id] = monitor_task

                # Update session status in database
                await self.update_session_status(session_id, 'running')

                logger.info(
                    f"Trading system {session_id} launched successfully")
                return True
            else:
                logger.error(
                    f"Failed to start process for session {session_id}")
                return False

        except Exception as e:
            logger.error(f"Error launching trading system {session_id}: {e}")
            return False

    def create_launch_command(self, config: Dict) -> Optional[List[str]]:
        """Create the command to launch the enhanced trading system"""
        try:
            # Path to the enhanced trading system launcher
            launcher_script = self.base_path / "main_trading_launcher.py"

            if not launcher_script.exists():
                logger.error(
                    f"Enhanced launcher script not found: {launcher_script}")
                return None

            # Create command with arguments for enhanced launcher
            command = [
                "python",
                str(launcher_script),
                "--session-id", config['session_id'],
                "--user-id", config['user_id'],
                "--account-id", config['account_id'],
                "--strategies", ",".join(config['strategies']),
                "--config", json.dumps(config['config'])
            ]

            logger.info(f"Created launch command: {' '.join(command)}")
            return command

        except Exception as e:
            logger.error(f"Error creating launch command: {e}")
            return None

    async def start_process(self, command: List[str], config: Dict) -> Optional[subprocess.Popen]:
        """Start the trading system process"""
        try:
            # Set environment variables
            env = os.environ.copy()
            env['TRADING_SESSION_ID'] = config['session_id']
            env['TRADING_USER_ID'] = config['user_id']
            env['TRADING_ACCOUNT_ID'] = config['account_id']

            # Start process
            process = subprocess.Popen(
                command,
                env=env,
                cwd=str(self.base_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            # Wait a moment to see if process starts successfully
            await asyncio.sleep(2)

            if process.poll() is None:  # Process is still running
                logger.info(f"Process started with PID: {process.pid}")
                return process
            else:
                # Process exited immediately
                stdout, stderr = process.communicate()
                logger.error(
                    f"Process exited immediately. Stdout: {stdout}, Stderr: {stderr}")
                return None

        except Exception as e:
            logger.error(f"Error starting process: {e}")
            return None

    async def monitor_process(self, session_id: str):
        """Monitor a trading system process"""
        try:
            while session_id in self.active_processes:
                process_info = self.active_processes[session_id]
                process = process_info['process']

                # Check if process is still running
                if process.poll() is not None:
                    # Process has exited
                    logger.warning(
                        f"Process {session_id} has exited with code {process.poll()}")

                    # Check if we should restart
                    if await self.should_restart_process(session_id):
                        await self.restart_process(session_id)
                    else:
                        await self.cleanup_process(session_id)
                        break

                # Update heartbeat
                process_info['last_heartbeat'] = datetime.utcnow()

                # Check process health
                await self.check_process_health(session_id)

                # Sleep before next check
                await asyncio.sleep(30)  # Check every 30 seconds

        except Exception as e:
            logger.error(f"Error monitoring process {session_id}: {e}")
            await self.cleanup_process(session_id)

    async def should_restart_process(self, session_id: str) -> bool:
        """Determine if a process should be restarted"""
        try:
            process_info = self.active_processes.get(session_id)
            if not process_info:
                return False

            restart_count = process_info.get('restart_count', 0)
            max_restarts = 3  # Maximum number of restart attempts

            if restart_count >= max_restarts:
                logger.warning(
                    f"Process {session_id} has reached maximum restart attempts")
                return False

            # Check if the process ran for at least 5 minutes before crashing
            started_at = process_info.get('started_at')
            if started_at:
                runtime = datetime.utcnow() - started_at
                if runtime.total_seconds() < 300:  # Less than 5 minutes
                    logger.warning(
                        f"Process {session_id} crashed too quickly, not restarting")
                    return False

            return True

        except Exception as e:
            logger.error(
                f"Error checking restart eligibility for {session_id}: {e}")
            return False

    async def restart_process(self, session_id: str):
        """Restart a trading system process"""
        try:
            logger.info(f"Restarting process {session_id}")

            # Get the original configuration
            process_info = self.active_processes.get(session_id)
            if not process_info:
                logger.error(f"Process info not found for {session_id}")
                return

            original_config = process_info['config']
            restart_count = process_info.get('restart_count', 0) + 1

            # Cleanup the old process
            await self.cleanup_process(session_id, update_db=False)

            # Update session status
            await self.update_session_status(session_id, 'restarting')

            # Restart with same configuration
            success = await self.launch_trading_system(
                session_id,
                original_config['user_id'],
                original_config['account_id'],
                original_config['strategies'],
                original_config['config']
            )

            if success:
                # Update restart count
                self.active_processes[session_id]['restart_count'] = restart_count
                logger.info(
                    f"Process {session_id} restarted successfully (attempt {restart_count})")
            else:
                logger.error(f"Failed to restart process {session_id}")
                await self.update_session_status(session_id, 'error')

        except Exception as e:
            logger.error(f"Error restarting process {session_id}: {e}")
            await self.update_session_status(session_id, 'error')

    async def stop_trading_system(self, session_id: str) -> bool:
        """Stop a trading system process"""
        try:
            if session_id not in self.active_processes:
                logger.warning(f"Trading system {session_id} not found")
                return False

            process_info = self.active_processes[session_id]
            process = process_info['process']

            logger.info(f"Stopping trading system {session_id}")

            # Update status to stopping
            await self.update_session_status(session_id, 'stopping')

            # Try graceful shutdown first
            if process.poll() is None:
                try:
                    process.terminate()
                    await asyncio.wait_for(
                        asyncio.create_task(
                            self.wait_for_process_exit(process)),
                        timeout=30
                    )
                except asyncio.TimeoutError:
                    # Force kill if graceful shutdown fails
                    logger.warning(f"Force killing process {session_id}")
                    process.kill()

            # Cleanup
            await self.cleanup_process(session_id)

            logger.info(f"Trading system {session_id} stopped successfully")
            return True

        except Exception as e:
            logger.error(f"Error stopping trading system {session_id}: {e}")
            return False

    async def restart_trading_system(self, session_id: str) -> bool:
        """Restart a specific trading system"""
        try:
            if session_id not in self.active_processes:
                logger.warning(f"Trading system {session_id} not found")
                return False

            # Get the original configuration
            process_info = self.active_processes[session_id]
            config = process_info['config']

            # Stop the current process
            await self.stop_trading_system(session_id)

            # Wait a moment
            await asyncio.sleep(2)

            # Restart with the same configuration
            return await self.launch_trading_system(
                config['session_id'],
                config['user_id'],
                config['account_id'],
                config['strategies'],
                config['config']
            )

        except Exception as e:
            logger.error(f"Error restarting trading system {session_id}: {e}")
            return False

    async def wait_for_process_exit(self, process: subprocess.Popen):
        """Wait for a process to exit"""
        while process.poll() is None:
            await asyncio.sleep(0.1)

    async def cleanup_process(self, session_id: str, update_db: bool = True):
        """Clean up process resources"""
        try:
            # Remove from active processes
            if session_id in self.active_processes:
                del self.active_processes[session_id]

            # Cancel monitoring task
            if session_id in self.monitoring_tasks:
                self.monitoring_tasks[session_id].cancel()
                del self.monitoring_tasks[session_id]

            # Update database status
            if update_db:
                await self.update_session_status(session_id, 'stopped')

            logger.info(f"Cleaned up process {session_id}")

        except Exception as e:
            logger.error(f"Error cleaning up process {session_id}: {e}")

    async def check_process_health(self, session_id: str):
        """Check the health of a trading system process"""
        try:
            process_info = self.active_processes.get(session_id)
            if not process_info:
                return

            process = process_info['process']

            # Check CPU and memory usage
            try:
                ps_process = psutil.Process(process.pid)
                cpu_percent = ps_process.cpu_percent()
                memory_info = ps_process.memory_info()
                memory_mb = memory_info.rss / 1024 / 1024

                # Update process health metrics
                process_info['cpu_percent'] = cpu_percent
                process_info['memory_mb'] = memory_mb
                process_info['last_health_check'] = datetime.utcnow()

                # Log health metrics
                logger.debug(
                    f"Process {session_id} health - CPU: {cpu_percent}%, Memory: {memory_mb:.1f}MB")

                # Check for concerning resource usage
                if memory_mb > 1000:  # More than 1GB
                    logger.warning(
                        f"High memory usage for process {session_id}: {memory_mb:.1f}MB")

                # Check for high CPU usage
                if cpu_percent > 90:  # More than 90% CPU
                    logger.warning(
                        f"High CPU usage for process {session_id}: {cpu_percent}%")

                # Check heartbeat file
                await self.check_process_heartbeat(session_id)

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                logger.warning(
                    f"Could not get resource info for process {session_id}")

        except Exception as e:
            logger.error(
                f"Error checking process health for {session_id}: {e}")

    async def check_process_heartbeat(self, session_id: str):
        """Check process heartbeat file for additional health information"""
        try:
            heartbeat_file = self.base_path / f"session_{session_id}.heartbeat"

            if heartbeat_file.exists():
                with open(heartbeat_file, 'r') as f:
                    heartbeat_data = json.load(f)

                # Check if heartbeat is recent (within last 2 minutes)
                heartbeat_time = datetime.fromisoformat(
                    heartbeat_data['timestamp'].replace('Z', '+00:00'))
                time_diff = datetime.utcnow() - heartbeat_time.replace(tzinfo=None)

                if time_diff.total_seconds() > 120:  # 2 minutes
                    logger.warning(
                        f"Stale heartbeat for session {session_id}: {time_diff.total_seconds()} seconds")
                else:
                    # Update process info with heartbeat data
                    process_info = self.active_processes.get(session_id)
                    if process_info:
                        process_info['heartbeat_status'] = heartbeat_data.get(
                            'status', 'unknown')
                        process_info['session_stats'] = heartbeat_data.get(
                            'stats', {})

            else:
                logger.debug(
                    f"No heartbeat file found for session {session_id}")

        except Exception as e:
            logger.error(f"Error checking heartbeat for {session_id}: {e}")

    async def update_session_status(self, session_id: str, status: str):
        """Update session status in database"""
        try:
            if self.auth_service:
                success = await self.auth_service.update_trading_session_status(session_id, status)
                if success:
                    logger.debug(
                        f"Updated session {session_id} status to {status}")
                else:
                    logger.warning(
                        f"Failed to update session {session_id} status")

        except Exception as e:
            logger.error(f"Error updating session status: {e}")

    async def get_active_sessions(self) -> Dict[str, Dict]:
        """Get information about all active trading sessions"""
        try:
            sessions_info = {}

            for session_id, process_info in self.active_processes.items():
                process = process_info['process']

                # Get process stats (use cached values if available)
                cpu_percent = process_info.get('cpu_percent', 0)
                memory_mb = process_info.get('memory_mb', 0)

                # If not cached, get fresh stats
                if cpu_percent == 0 and memory_mb == 0:
                    try:
                        ps_process = psutil.Process(process.pid)
                        cpu_percent = ps_process.cpu_percent()
                        memory_info = ps_process.memory_info()
                        memory_mb = memory_info.rss / 1024 / 1024
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass

                # Calculate uptime
                uptime_seconds = int(
                    (datetime.utcnow() - process_info['started_at']).total_seconds())

                sessions_info[session_id] = {
                    'status': process_info['status'],
                    'started_at': process_info['started_at'].isoformat(),
                    'last_heartbeat': process_info['last_heartbeat'].isoformat(),
                    'restart_count': process_info.get('restart_count', 0),
                    'pid': process.pid,
                    'cpu_percent': cpu_percent,
                    'memory_mb': memory_mb,
                    'uptime_seconds': uptime_seconds,
                    'config': process_info['config'],
                    'heartbeat_status': process_info.get('heartbeat_status', 'unknown'),
                    'session_stats': process_info.get('session_stats', {}),
                    'last_health_check': process_info.get('last_health_check', process_info['started_at']).isoformat()
                }

            return sessions_info

        except Exception as e:
            logger.error(f"Error getting active sessions: {e}")
            return {}

    async def get_manager_stats(self) -> Dict[str, Any]:
        """Get overall process manager statistics"""
        try:
            total_sessions = len(self.active_processes)
            running_sessions = len(
                [p for p in self.active_processes.values() if p['status'] == 'running'])

            # Calculate total resource usage
            total_cpu = 0
            total_memory = 0

            for process_info in self.active_processes.values():
                total_cpu += process_info.get('cpu_percent', 0)
                total_memory += process_info.get('memory_mb', 0)

            # Get system uptime
            manager_uptime = int((datetime.utcnow(
            ) - self.start_time).total_seconds()) if hasattr(self, 'start_time') else 0

            return {
                'total_sessions': total_sessions,
                'running_sessions': running_sessions,
                'stopped_sessions': total_sessions - running_sessions,
                'total_cpu_percent': total_cpu,
                'total_memory_mb': total_memory,
                'manager_uptime_seconds': manager_uptime,
                'last_updated': datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error getting manager stats: {e}")
            return {}

    async def stop_all_systems(self):
        """Stop all active trading systems"""
        try:
            logger.info("Stopping all active trading systems")

            # Get list of session IDs to avoid modifying dict during iteration
            session_ids = list(self.active_processes.keys())

            # Stop all processes
            for session_id in session_ids:
                await self.stop_trading_system(session_id)

            logger.info("All trading systems stopped")

        except Exception as e:
            logger.error(f"Error stopping all systems: {e}")

    async def cleanup_all(self):
        """Clean up all resources"""
        try:
            await self.stop_all_systems()

            # Cancel all monitoring tasks
            for task in self.monitoring_tasks.values():
                task.cancel()

            self.monitoring_tasks.clear()
            self.active_processes.clear()

            logger.info("Process manager cleanup completed")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


# Global process manager instance
_process_manager: Optional[TradingProcessManager] = None


async def get_process_manager() -> TradingProcessManager:
    """Get or create the global process manager instance"""
    global _process_manager

    if _process_manager is None:
        _process_manager = TradingProcessManager()
        await _process_manager.initialize()

    return _process_manager


async def cleanup_process_manager():
    """Cleanup the global process manager instance"""
    global _process_manager

    if _process_manager:
        await _process_manager.cleanup_all()
        _process_manager = None
