"""
Test script to verify authentication with specific user email
"""
import asyncio
import logging
from services.supabase_auth_service import SupabaseAuthService

logging.basicConfig(level=logging.INFO)


async def test_specific_user():
    """Test authentication with the specific user email"""
    try:
        auth_service = SupabaseAuthService()
        await auth_service.initialize()

        test_email = "youssefmesalm@yahoo.com"
        test_password = "1223334444"

        print(f"Testing authentication for: {test_email}")

        # First check if user exists
        print("\n1. Checking if user exists:")
        result = await auth_service.client.table('users').select('*').eq('email', test_email).execute()

        if result.data and len(result.data) > 0:
            user_record = result.data[0]
            print(f"   ✓ User found!")
            print(f"   ID: {user_record['id']}")
            print(f"   Email: {user_record['email']}")
            print(
                f"   Email Verified: {user_record.get('email_verified', 'N/A')}")
            print(f"   Status: {user_record.get('status', 'N/A')}")

            # Test authentication
            print(f"\n2. Testing authentication:")
            success, message, user_data = await auth_service.login(test_email, test_password)

            if success:
                print(f"   ✓ Authentication successful!")
                print(f"   User ID: {user_data['user']['id']}")
                print(f"   Email: {user_data['user']['email']}")
            else:
                print(f"   ✗ Authentication failed: {message}")

        else:
            print(f"   ✗ User not found with email: {test_email}")
            print("\n   Available users:")
            all_users = await auth_service.client.table('users').select('id, email').limit(10).execute()
            for user in all_users.data:
                print(f"     - {user['email']}")

        await auth_service.close()

    except Exception as e:
        print(f"Error testing specific user: {e}")

if __name__ == "__main__":
    asyncio.run(test_specific_user())
