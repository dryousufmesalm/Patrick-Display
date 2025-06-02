#!/usr/bin/env python3
"""
Comprehensive Testing Script for Real-Time Trading System V2
Tests all Phase 1 and Phase 2 implementations
"""

import asyncio
import logging
import time
import sys
import os
from datetime import datetime
from typing import Dict, List

# Add project root to Python path
sys.path.insert(0, os.path.dirname(__file__))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SystemTest")


class SystemTestSuite:
    """Comprehensive test suite for the trading system"""

    def __init__(self):
        self.test_results: Dict[str, bool] = {}
        self.test_times: Dict[str, float] = {}
        self.errors: List[str] = []

    async def run_all_tests(self):
        """Run all system tests"""
        logger.info("🚀 Starting comprehensive system tests...")
        start_time = time.time()

        # Test phases
        await self.test_phase_1_critical_fixes()
        await self.test_phase_2_core_integration()
        await self.test_system_integration()

        # Generate report
        total_time = time.time() - start_time
        await self.generate_test_report(total_time)

    async def test_phase_1_critical_fixes(self):
        """Test Phase 1: Critical Fixes"""
        logger.info("📋 Testing Phase 1: Critical Fixes")

        # Test 1: Import Path Fixes
        await self.test_import_paths()

        # Test 2: MT5 Connector Implementation
        await self.test_mt5_connector()

        # Test 3: Service Methods
        await self.test_service_methods()

    async def test_phase_2_core_integration(self):
        """Test Phase 2: Core Integration"""
        logger.info("🔄 Testing Phase 2: Core Integration")

        # Test 1: WebSocket Service
        await self.test_websocket_service()

        # Test 2: Error Recovery Service
        await self.test_error_recovery_service()

    async def test_system_integration(self):
        """Test full system integration"""
        logger.info("🌐 Testing System Integration")

        # Test 1: Component Communication
        await self.test_component_communication()

    async def test_import_paths(self):
        """Test import path fixes"""
        test_name = "Import Paths"
        start_time = time.time()

        try:
            # Test main system imports
            from main_realtime_v2 import RealTimeTradingSystemV2
            from services.supabase_service import SupabaseService
            from Bots.trading_bot_v2 import TradingBotV2
            from Orders.orders_manager_v2 import OrdersManagerV2
            from cycles.cycles_manager_v2 import CyclesManagerV2
            from MetaTrader.mt5_real_connector import MT5RealConnector
            from services.websocket_service import TradingWebSocketService
            from services.error_recovery_service import ErrorRecoveryService

            logger.info("✅ All imports successful")
            self.test_results[test_name] = True

        except ImportError as e:
            logger.error(f"❌ Import error: {e}")
            self.test_results[test_name] = False
            self.errors.append(f"Import Path Test: {e}")

        self.test_times[test_name] = time.time() - start_time

    async def test_mt5_connector(self):
        """Test MT5 connector implementation"""
        test_name = "MT5 Connector"
        start_time = time.time()

        try:
            from MetaTrader.mt5_real_connector import MT5RealConnector

            # Test connector creation
            connector = MT5RealConnector()

            # Test required methods exist
            assert hasattr(
                connector, 'initialize'), "Missing initialize method"
            assert hasattr(connector, 'login'), "Missing login method"
            assert hasattr(connector, 'close'), "Missing close method"
            assert hasattr(
                connector, 'get_all_positions'), "Missing get_all_positions method"

            logger.info("✅ MT5 Connector implementation complete")
            self.test_results[test_name] = True

        except Exception as e:
            logger.error(f"❌ MT5 Connector test failed: {e}")
            self.test_results[test_name] = False
            self.errors.append(f"MT5 Connector Test: {e}")

        self.test_times[test_name] = time.time() - start_time

    async def test_service_methods(self):
        """Test service method implementations"""
        test_name = "Service Methods"
        start_time = time.time()

        try:
            from services.supabase_service import SupabaseService

            # Test Supabase service
            service = SupabaseService()

            # Test required methods exist
            assert hasattr(
                service, 'close'), "SupabaseService missing close method"

            logger.info("✅ Service methods implemented")
            self.test_results[test_name] = True

        except Exception as e:
            logger.error(f"❌ Service methods test failed: {e}")
            self.test_results[test_name] = False
            self.errors.append(f"Service Methods Test: {e}")

        self.test_times[test_name] = time.time() - start_time

    async def test_websocket_service(self):
        """Test WebSocket service"""
        test_name = "WebSocket Service"
        start_time = time.time()

        try:
            from services.websocket_service import TradingWebSocketService, WebSocketMessage

            # Test service creation
            ws_service = TradingWebSocketService()

            # Test message creation
            message = WebSocketMessage("test", {"data": "test"})
            message_dict = message.to_dict()

            assert message_dict['type'] == "test", "WebSocket message structure invalid"

            logger.info("✅ WebSocket service validated")
            self.test_results[test_name] = True

        except Exception as e:
            logger.error(f"❌ WebSocket service test failed: {e}")
            self.test_results[test_name] = False
            self.errors.append(f"WebSocket Service Test: {e}")

        self.test_times[test_name] = time.time() - start_time

    async def test_error_recovery_service(self):
        """Test error recovery service"""
        test_name = "Error Recovery Service"
        start_time = time.time()

        try:
            from services.error_recovery_service import ErrorRecoveryService

            # Test service creation
            recovery_service = ErrorRecoveryService()

            # Test component registration
            recovery_service.register_component(
                "test_component", critical=True)
            assert "test_component" in recovery_service.components, "Component registration failed"

            logger.info("✅ Error recovery service validated")
            self.test_results[test_name] = True

        except Exception as e:
            logger.error(f"❌ Error recovery service test failed: {e}")
            self.test_results[test_name] = False
            self.errors.append(f"Error Recovery Service Test: {e}")

        self.test_times[test_name] = time.time() - start_time

    async def test_component_communication(self):
        """Test component communication"""
        test_name = "Component Communication"
        start_time = time.time()

        try:
            # Test that main system can import and reference all components
            from main_realtime_v2 import RealTimeTradingSystemV2

            # Test system creation (without full initialization)
            system = RealTimeTradingSystemV2("test_account")

            # Verify component attributes exist
            assert hasattr(
                system, 'supabase_service'), "Missing supabase_service attribute"
            assert hasattr(
                system, 'mt5_connector'), "Missing mt5_connector attribute"
            assert hasattr(
                system, 'websocket_service'), "Missing websocket_service attribute"

            logger.info("✅ Component communication structure validated")
            self.test_results[test_name] = True

        except Exception as e:
            logger.error(f"❌ Component communication test failed: {e}")
            self.test_results[test_name] = False
            self.errors.append(f"Component Communication Test: {e}")

        self.test_times[test_name] = time.time() - start_time

    async def generate_test_report(self, total_time: float):
        """Generate comprehensive test report"""
        logger.info("\n" + "="*80)
        logger.info("📊 COMPREHENSIVE TEST REPORT")
        logger.info("="*80)

        # Summary statistics
        total_tests = len(self.test_results)
        passed_tests = sum(
            1 for result in self.test_results.values() if result)
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests) * \
            100 if total_tests > 0 else 0

        logger.info(f"📈 SUMMARY:")
        logger.info(f"  Total Tests: {total_tests}")
        logger.info(f"  Passed: {passed_tests}")
        logger.info(f"  Failed: {failed_tests}")
        logger.info(f"  Success Rate: {success_rate:.1f}%")
        logger.info(f"  Total Time: {total_time:.2f}s")

        # Detailed results
        logger.info(f"\n📋 DETAILED RESULTS:")
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            time_taken = self.test_times.get(test_name, 0)
            logger.info(f"  {status} {test_name:<25} ({time_taken:.3f}s)")

        # Errors
        if self.errors:
            logger.info(f"\n🚨 ERRORS:")
            for error in self.errors:
                logger.info(f"  - {error}")

        logger.info("="*80)


async def main():
    """Main test execution"""
    try:
        test_suite = SystemTestSuite()
        await test_suite.run_all_tests()

        # Exit with appropriate code
        failed_tests = sum(
            1 for result in test_suite.test_results.values() if not result)
        sys.exit(1 if failed_tests > 0 else 0)

    except Exception as e:
        logger.error(f"❌ Test suite failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
