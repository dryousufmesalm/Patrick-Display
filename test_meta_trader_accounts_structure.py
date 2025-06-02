"""
Test script to check the actual structure of the meta_trader_accounts table
"""
import asyncio
import logging
from services.supabase_service import SupabaseService

logging.basicConfig(level=logging.INFO)


async def check_meta_trader_accounts_structure():
    """Check the actual structure of the meta_trader_accounts table"""
    try:
        service = SupabaseService()
        await service.initialize()

        print("Checking meta_trader_accounts table structure...")

        # Get all columns by selecting everything from one record
        result = await service.client.table('meta_trader_accounts').select('*').limit(1).execute()

        if result.data and len(result.data) > 0:
            account_record = result.data[0]
            print(f"\nFound account record with {len(account_record)} fields:")
            print("Available columns:")
            for key, value in account_record.items():
                value_preview = str(
                    value)[:50] + "..." if len(str(value)) > 50 else str(value)
                print(f"   {key}: {value_preview}")
        else:
            print("No account records found")

        await service.close()

    except Exception as e:
        print(f"Error checking meta_trader_accounts structure: {e}")

if __name__ == "__main__":
    asyncio.run(check_meta_trader_accounts_structure())
