"""
Test script to check the actual structure of the users table
"""
import asyncio
import logging
from services.supabase_service import SupabaseService

logging.basicConfig(level=logging.INFO)


async def check_user_structure():
    """Check the actual structure of the users table"""
    try:
        service = SupabaseService()
        await service.initialize()

        print("Checking users table structure...")

        # Get all columns by selecting everything from one record
        result = await service.client.table('users').select('*').limit(1).execute()

        if result.data and len(result.data) > 0:
            user_record = result.data[0]
            print(f"\nFound user record with {len(user_record)} fields:")
            print("Available columns:")
            for key, value in user_record.items():
                value_preview = str(
                    value)[:50] + "..." if len(str(value)) > 50 else str(value)
                print(f"   {key}: {value_preview}")
        else:
            print("No user records found")

        await service.close()

    except Exception as e:
        print(f"Error checking user structure: {e}")

if __name__ == "__main__":
    asyncio.run(check_user_structure())
