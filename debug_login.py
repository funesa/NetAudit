import os
from database import init_db, get_session
from models import User
from security import decrypt_value, encrypt_value, get_key
from ad_helper import authenticate_ad

print("--- STARTING LOGIN DEBUG ---")

# 1. Check Encryption Key
try:
    key = get_key()
    print(f"[OK] Encryption Key loaded. Type: {type(key)}")
except Exception as e:
    print(f"[FAIL] Error loading encryption key: {e}")

# 2. Check Database & User
init_db()
session = get_session()
username = 'pofjunior'
target_pass = 'admin'

print(f"\n--- Checking User: {username} ---")
user = session.query(User).filter_by(username=username).first()

if not user:
    print(f"[FAIL] User '{username}' NOT FOUND in local database!")
else:
    print(f"[OK] User found. ID: {user.id}, Role: {user.role}")
    print(f"Stored Password Hash (first 50 chars): {user.password[:50]}...")
    
    # 3. Test Decryption
    try:
        decrypted = decrypt_value(user.password)
        print(f"[OK] Decryption successful. Password is: '{decrypted}'")
        
        if decrypted == target_pass:
            print("[SUCCESS] Local password matches 'admin'.")
        else:
            print(f"[INFO] Local password is NOT 'admin'. It is: '{decrypted}'")
            
    except Exception as e:
        print(f"[FAIL] Decryption FAILED: {e}")
        print("Possible causes: Key mismatch, corrupted data, or legacy plain text.")

# 4. Test Encryption Cycle
print("\n--- Testing Encryption Cycle ---")
try:
    test_str = "test_password_123"
    encrypted = encrypt_value(test_str)
    decrypted_back = decrypt_value(encrypted)
    if test_str == decrypted_back:
        print("[OK] Encryption/Decryption cycle works correctly.")
    else:
        print("[FAIL] Cycle mismatch!")
except Exception as e:
    print(f"[FAIL] Cycle error: {e}")

# 5. Test AD (Optional)
print("\n--- Testing AD Auth (Simulation) ---")
try:
    # We pass a wrong password just to see if it connects or fails immediately
    # If returns False, it means it tried. If errors, it crashes.
    print("Attempting AD bind check...")
    ad_result = authenticate_ad(username, "wrong_pass_test")
    print(f"[INFO] AD Auth Result for wrong pass: {ad_result}")
    if ad_result is False:
        print("[OK] AD Auth logic ran without crashing.")
except Exception as e:
    print(f"[FAIL] AD Auth Logic Crashed: {e}")

session.close()
print("\n--- DEBUG COMPLETE ---")
