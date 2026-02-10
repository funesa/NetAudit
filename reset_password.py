from database import init_db, get_session
from models import User
from security import encrypt_value

print("--- RESETTING PASSWORD ---")
try:
    init_db()
    session = get_session()
    user = session.query(User).filter_by(username='pofjunior').first()
    
    if user:
        print(f"User found: {user.username}")
        new_pass = encrypt_value('admin')
        user.password = new_pass
        session.commit()
        print("SUCCESS: Password reset to 'admin'.")
    else:
        print("ERROR: User 'pofjunior' not found.")
        
    session.close()
except Exception as e:
    print(f"FATAL ERROR: {e}")
print("--- RESET COMPLETE ---")
