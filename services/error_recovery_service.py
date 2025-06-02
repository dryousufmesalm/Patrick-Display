"""
Error Recovery Service for Trading System
Handles automatic error recovery, circuit breakers, and graceful degradation
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from enum import Enum
import traceback

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    FAILED = "failed"


class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit breaker triggered
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreaker:
    """Circuit breaker pattern implementation"""

    def __init__(self, failure_threshold: int = 5, timeout: int = 60, success_threshold: int = 3):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.success_threshold = success_threshold

        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED

    async def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker moving to HALF_OPEN state")
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            await self._on_success()
            return result

        except Exception as e:
            await self._on_failure(e)
            raise

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if self.last_failure_time is None:
            return True
        return (datetime.utcnow() - self.last_failure_time).seconds > self.timeout

    async def _on_success(self):
        """Handle successful operation"""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self._reset()
        else:
            self.failure_count = 0

    async def _on_failure(self, exception: Exception):
        """Handle failed operation"""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(
                f"Circuit breaker OPENED due to {self.failure_count} failures")

    def _reset(self):
        """Reset circuit breaker to closed state"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        logger.info("Circuit breaker CLOSED - normal operation resumed")


class RetryStrategy:
    """Configurable retry strategy with exponential backoff"""

    def __init__(self, max_attempts: int = 3, base_delay: float = 1.0, max_delay: float = 60.0):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay

    async def execute(self, func: Callable, *args, **kwargs):
        """Execute function with retry logic"""
        last_exception = None

        for attempt in range(self.max_attempts):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)

            except Exception as e:
                last_exception = e

                if attempt < self.max_attempts - 1:
                    delay = min(self.base_delay *
                                (2 ** attempt), self.max_delay)
                    logger.warning(
                        f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"All {self.max_attempts} attempts failed")

        raise last_exception


class ComponentHealth:
    """Health tracking for system components"""

    def __init__(self, name: str, critical: bool = False):
        self.name = name
        self.critical = critical
        self.status = HealthStatus.HEALTHY
        self.last_check = datetime.utcnow()
        self.error_count = 0
        self.consecutive_failures = 0
        self.last_error = None
        self.recovery_attempts = 0

    def update_health(self, is_healthy: bool, error: Exception = None):
        """Update health status"""
        self.last_check = datetime.utcnow()

        if is_healthy:
            if self.status != HealthStatus.HEALTHY:
                logger.info(
                    f"Component {self.name} recovered to HEALTHY status")
            self.status = HealthStatus.HEALTHY
            self.consecutive_failures = 0
        else:
            self.error_count += 1
            self.consecutive_failures += 1
            self.last_error = error

            # Determine status based on failure count
            if self.consecutive_failures >= 10:
                self.status = HealthStatus.FAILED
            elif self.consecutive_failures >= 5:
                self.status = HealthStatus.CRITICAL
            elif self.consecutive_failures >= 3:
                self.status = HealthStatus.DEGRADED

            logger.warning(
                f"Component {self.name} status: {self.status.value} ({self.consecutive_failures} consecutive failures)")

    def get_health_info(self) -> Dict:
        """Get component health information"""
        return {
            'name': self.name,
            'status': self.status.value,
            'critical': self.critical,
            'last_check': self.last_check.isoformat(),
            'error_count': self.error_count,
            'consecutive_failures': self.consecutive_failures,
            'last_error': str(self.last_error) if self.last_error else None,
            'recovery_attempts': self.recovery_attempts
        }


class ErrorRecoveryService:
    """
    Central error recovery service for the trading system
    Manages circuit breakers, retry strategies, and component health
    """

    def __init__(self):
        self.components: Dict[str, ComponentHealth] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.retry_strategies: Dict[str, RetryStrategy] = {}

        # Recovery functions
        self.recovery_functions: Dict[str, Callable] = {}

        # Statistics
        self.total_errors = 0
        self.recovery_attempts = 0
        self.successful_recoveries = 0

        # Health check settings
        self.health_check_interval = 30  # seconds
        self.last_health_check = datetime.utcnow()

    def register_component(self, name: str, critical: bool = False,
                           circuit_breaker_config: Dict = None,
                           retry_config: Dict = None,
                           recovery_function: Callable = None):
        """Register a component for monitoring"""

        # Register component health
        self.components[name] = ComponentHealth(name, critical)

        # Setup circuit breaker
        if circuit_breaker_config:
            self.circuit_breakers[name] = CircuitBreaker(
                **circuit_breaker_config)
        else:
            self.circuit_breakers[name] = CircuitBreaker()

        # Setup retry strategy
        if retry_config:
            self.retry_strategies[name] = RetryStrategy(**retry_config)
        else:
            self.retry_strategies[name] = RetryStrategy()

        # Register recovery function
        if recovery_function:
            self.recovery_functions[name] = recovery_function

        logger.info(f"Registered component: {name} (critical: {critical})")

    async def execute_with_protection(self, component_name: str, func: Callable, *args, **kwargs):
        """Execute function with full error protection"""
        try:
            # Get protection mechanisms
            circuit_breaker = self.circuit_breakers.get(component_name)
            retry_strategy = self.retry_strategies.get(component_name)
            component = self.components.get(component_name)

            if not circuit_breaker or not component:
                raise ValueError(f"Component {component_name} not registered")

            # Execute with circuit breaker and retry
            async def protected_execution():
                if retry_strategy:
                    return await retry_strategy.execute(func, *args, **kwargs)
                else:
                    if asyncio.iscoroutinefunction(func):
                        return await func(*args, **kwargs)
                    else:
                        return func(*args, **kwargs)

            result = await circuit_breaker.call(protected_execution)

            # Update health on success
            component.update_health(True)

            return result

        except Exception as e:
            self.total_errors += 1

            # Update component health
            if component_name in self.components:
                self.components[component_name].update_health(False, e)

            # Attempt recovery
            await self._attempt_recovery(component_name, e)

            # Re-raise exception
            raise

    async def _attempt_recovery(self, component_name: str, error: Exception):
        """Attempt to recover a failed component"""
        try:
            self.recovery_attempts += 1

            if component_name in self.recovery_functions:
                recovery_func = self.recovery_functions[component_name]
                component = self.components[component_name]

                component.recovery_attempts += 1

                logger.info(
                    f"Attempting recovery for component: {component_name}")

                if asyncio.iscoroutinefunction(recovery_func):
                    await recovery_func(error)
                else:
                    recovery_func(error)

                self.successful_recoveries += 1
                logger.info(
                    f"Recovery successful for component: {component_name}")

        except Exception as recovery_error:
            logger.error(
                f"Recovery failed for component {component_name}: {recovery_error}")

    async def health_check(self) -> Dict[str, Any]:
        """Perform system-wide health check"""
        current_time = datetime.utcnow()
        self.last_health_check = current_time

        health_report = {
            'timestamp': current_time.isoformat(),
            'overall_status': HealthStatus.HEALTHY.value,
            'components': {},
            'statistics': {
                'total_errors': self.total_errors,
                'recovery_attempts': self.recovery_attempts,
                'successful_recoveries': self.successful_recoveries,
                'recovery_rate': self.successful_recoveries / max(self.recovery_attempts, 1)
            },
            'circuit_breakers': {}
        }

        # Check component health
        critical_failed = False
        any_degraded = False

        for name, component in self.components.items():
            health_info = component.get_health_info()
            health_report['components'][name] = health_info

            if component.critical and component.status in [HealthStatus.CRITICAL, HealthStatus.FAILED]:
                critical_failed = True
            elif component.status in [HealthStatus.DEGRADED, HealthStatus.CRITICAL]:
                any_degraded = True

        # Check circuit breaker states
        for name, breaker in self.circuit_breakers.items():
            health_report['circuit_breakers'][name] = {
                'state': breaker.state.value,
                'failure_count': breaker.failure_count,
                'success_count': breaker.success_count
            }

        # Determine overall status
        if critical_failed:
            health_report['overall_status'] = HealthStatus.CRITICAL.value
        elif any_degraded:
            health_report['overall_status'] = HealthStatus.DEGRADED.value

        return health_report

    async def get_component_status(self, component_name: str) -> Optional[Dict]:
        """Get status of specific component"""
        if component_name in self.components:
            return self.components[component_name].get_health_info()
        return None

    async def force_recovery(self, component_name: str):
        """Force recovery attempt for specific component"""
        if component_name in self.recovery_functions:
            await self._attempt_recovery(component_name, Exception("Manual recovery triggered"))
        else:
            logger.warning(
                f"No recovery function registered for component: {component_name}")

    async def reset_circuit_breaker(self, component_name: str):
        """Reset circuit breaker for specific component"""
        if component_name in self.circuit_breakers:
            self.circuit_breakers[component_name]._reset()
            logger.info(
                f"Circuit breaker reset for component: {component_name}")

    def get_statistics(self) -> Dict:
        """Get error recovery statistics"""
        return {
            'total_errors': self.total_errors,
            'recovery_attempts': self.recovery_attempts,
            'successful_recoveries': self.successful_recoveries,
            'recovery_rate': self.successful_recoveries / max(self.recovery_attempts, 1),
            'components_count': len(self.components),
            'critical_components': sum(1 for c in self.components.values() if c.critical),
            'last_health_check': self.last_health_check.isoformat()
        }


# Global service instance
_error_recovery_service: Optional[ErrorRecoveryService] = None


def get_error_recovery_service() -> ErrorRecoveryService:
    """Get or create the global error recovery service"""
    global _error_recovery_service

    if _error_recovery_service is None:
        _error_recovery_service = ErrorRecoveryService()

    return _error_recovery_service
