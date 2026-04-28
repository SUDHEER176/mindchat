import os
from supabase import create_client, Client
from dotenv import load_dotenv
import getpass

# Load keys from backend .env
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not url or not key:
    print("❌ Error: Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in .env")
    exit(1)

supabase: Client = create_client(url, key)

print("=" * 50)
print("  Mindful Companion — Admin User Creator")
print("  Uses Service Role Key (bypasses rate limits)")
print("=" * 50)

email = input("\nEnter email address: ").strip()
if not email:
    print("❌ Email cannot be empty.")
    exit(1)

password = getpass.getpass("Enter password (min 6 chars): ").strip()
if len(password) < 6:
    print("❌ Password must be at least 6 characters.")
    exit(1)

try:
    user = supabase.auth.admin.create_user({
        "email": email,
        "password": password,
        "email_confirm": True  # Auto-confirms — no email verification needed
    })
    print(f"\n✅ Success! User created and confirmed.")
    print(f"   Email    : {email}")
    print(f"   User ID  : {user.user.id}")
    print(f"\n👉 You can now Sign In with these credentials on the login page.")

except Exception as e:
    err = str(e).lower()
    if "already exists" in err or "already been registered" in err:
        print(f"\n💡 A user with '{email}' already exists.")
        print("   → Just go to the login page and use Sign In (not Sign Up).")
    elif "invalid email" in err:
        print(f"\n❌ Invalid email format: {email}")
    elif "password" in err:
        print(f"\n❌ Password issue: {e}")
    else:
        print(f"\n❌ Failed to create user: {e}")
