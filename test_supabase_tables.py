"""
Test script to check what tables exist in Supabase database
"""
import asyncio
import logging
from services.supabase_service import SupabaseService

logging.basicConfig(level=logging.INFO)


async def test_tables():
    """Test what tables are accessible in Supabase"""
    try:
        service = SupabaseService()
        await service.initialize()

        print("Testing Supabase table access...")

        # Test users table
        print("\n1. Testing 'users' table:")
        try:
            result = await service.client.table('users').select('id, email').limit(5).execute()
            print(
                f"   ✓ 'users' table exists - found {len(result.data)} records")
            if result.data:
                print(f"   Sample: {result.data[0]}")
        except Exception as e:
            print(f"   ✗ 'users' table error: {e}")

        # Test meta-trader-accounts table
        print("\n2. Testing 'meta-trader-accounts' table:")
        try:
            result = await service.client.table('meta-trader-accounts').select('id').limit(5).execute()
            print(
                f"   ✓ 'meta-trader-accounts' table exists - found {len(result.data)} records")
        except Exception as e:
            print(f"   ✗ 'meta-trader-accounts' table error: {e}")

        # Test with different naming conventions
        print("\n3. Testing alternative table names:")
        alternative_names = [
            'MetaTraderAccounts',
            'metatraderaccounts',
            'meta_trader_accounts',
            'mt_accounts',
            'accounts'
        ]

        for table_name in alternative_names:
            try:
                result = await service.client.table(table_name).select('id').limit(1).execute()
                print(f"   ✓ Table '{table_name}' exists")
            except Exception as e:
                print(f"   ✗ Table '{table_name}' does not exist")

        # Test other expected tables
        print("\n4. Testing other trading tables:")
        trading_tables = ['bots', 'cycles', 'orders', 'events', 'symbols']

        for table_name in trading_tables:
            try:
                result = await service.client.table(table_name).select('id').limit(1).execute()
                print(f"   ✓ Table '{table_name}' exists")
            except Exception as e:
                print(f"   ✗ Table '{table_name}' error: {e}")

        await service.close()

    except Exception as e:
        print(f"Error testing tables: {e}")

if __name__ == "__main__":
    asyncio.run(test_tables())
