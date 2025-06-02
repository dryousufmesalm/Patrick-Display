"""
Test script to verify the full authentication flow works properly
"""
import asyncio
import logging
from Views.auth import supabase_auth

logging.basicConfig(level=logging.INFO)


async def test_full_auth_flow():
    """Test the complete authentication flow using the new Supabase system"""
    try:
        print("Testing complete authentication flow...")

        test_email = "youssefmesalm@yahoo.com"
        test_password = "1223334444"

        print(f"\n1. Testing login with: {test_email}")

        # Test login using the Views.auth.supabase_auth module (the one used by UI)
        success, message = await supabase_auth.login(test_email, test_password)

        if success:
            print(f"   ✓ Login successful: {message}")

            # Test getting current user
            print(f"\n2. Testing get current user:")
            current_user = await supabase_auth.get_current_user()

            if current_user:
                print(f"   ✓ Current user retrieved:")
                print(f"     ID: {current_user['id']}")
                print(f"     Email: {current_user['email']}")

                # Test getting user accounts
                print(f"\n3. Testing get user accounts:")
                user_id = current_user['id']
                accounts = await supabase_auth.get_user_accounts(user_id)
                print(f"   Found {len(accounts)} accounts for user")

                # Test authentication check
                print(f"\n4. Testing authentication check:")
                is_auth = await supabase_auth.is_authenticated()
                print(f"   Is authenticated: {is_auth}")

                # Test logout
                print(f"\n5. Testing logout:")
                logout_success, logout_message = await supabase_auth.logout()
                print(f"   Logout result: {logout_success} - {logout_message}")

                # Verify logged out
                print(f"\n6. Verifying logout:")
                is_auth_after = await supabase_auth.is_authenticated()
                print(f"   Is authenticated after logout: {is_auth_after}")

            else:
                print(f"   ✗ Could not get current user data")

        else:
            print(f"   ✗ Login failed: {message}")

        # Clean up
        await supabase_auth.cleanup_auth()
        print(f"\n✅ Authentication flow test completed")

    except Exception as e:
        print(f"Error in authentication flow test: {e}")

if __name__ == "__main__":
    asyncio.run(test_full_auth_flow())
