"""
Test script to verify authentication against public.users table
"""
import asyncio
import logging
from services.supabase_auth_service import SupabaseAuthService

logging.basicConfig(level=logging.INFO)


async def test_authentication():
    """Test authentication against public.users table"""
    try:
        auth_service = SupabaseAuthService()
        await auth_service.initialize()

        print("Testing authentication against public.users table...")

        # First, let's see what users exist
        print("\n1. Checking available users:")
        result = await auth_service.client.table('users').select('id, email, email_verified, status').execute()

        if result.data:
            print(f"   Found {len(result.data)} users:")
            for i, user in enumerate(result.data[:5]):  # Show first 5 users
                print(
                    f"   {i+1}. Email: {user['email']}, Verified: {user.get('email_verified', 'N/A')}, Status: {user.get('status', 'N/A')}")
        else:
            print("   No users found")
            return

        # Test authentication with the first user
        test_email = result.data[0]['email']
        test_password = "testpassword123"  # Use a test password

        print(f"\n2. Testing login with email: {test_email}")
        success, message, user_data = await auth_service.login(test_email, test_password)

        if success:
            print(f"   ✓ Login successful!")
            print(f"   User ID: {user_data['user']['id']}")
            print(f"   Email: {user_data['user']['email']}")
            print(
                f"   Profile data available: {bool(user_data.get('profile'))}")

            # Test getting user accounts
            print(
                f"\n3. Testing getting accounts for user ID: {user_data['user']['id']}")
            accounts = await auth_service.get_user_accounts(user_data['user']['id'])
            print(f"   Found {len(accounts)} accounts for this user")

            # Test logout
            print(f"\n4. Testing logout:")
            logout_success, logout_message = await auth_service.logout()
            print(f"   Logout result: {logout_success} - {logout_message}")

        else:
            print(f"   ✗ Login failed: {message}")

        await auth_service.close()

    except Exception as e:
        print(f"Error testing authentication: {e}")

if __name__ == "__main__":
    asyncio.run(test_authentication())
