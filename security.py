from cryptography.fernet import Fernet
import os
import json
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Chave fixa derivada para garantir que os dados possam ser lidos em qualquer reinício
# Em produção real, isso deveria vir de variável de ambiente ou cofre seguro.
# Para este executável standalone, usamos uma "salt" fixa no código.
SALT = b'NetAudit_Secure_Salt_2026'
MASTER_KEY_SRC = b'NetAudit_Enterprise_Master_Key'

def get_key():
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=SALT,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(MASTER_KEY_SRC))
    return key

cipher = Fernet(get_key())

def encrypt_value(text):
    if not text: return ""
    return cipher.encrypt(text.encode()).decode()

def decrypt_value(text):
    if not text: return ""
    try:
        return cipher.decrypt(text.encode()).decode()
    except:
        return text # Retorna texto original se não estiver encriptado (migração)

def save_encrypted_json(filepath, data, fields_to_encrypt):
    """Salva JSON encriptando campos específicos"""
    encrypted_data = []
    
    # Se for lista
    if isinstance(data, list):
        for item in data:
            new_item = item.copy()
            for field in fields_to_encrypt:
                if field in new_item:
                    new_item[field] = encrypt_value(new_item[field])
            encrypted_data.append(new_item)
    # Se for dict
    elif isinstance(data, dict):
        encrypted_data = data.copy()
        for field in fields_to_encrypt:
            if field in encrypted_data:
                encrypted_data[field] = encrypt_value(encrypted_data[field])
                
    with open(filepath, 'w') as f:
        json.dump(encrypted_data, f, indent=2)

def load_encrypted_json(filepath, fields_to_decrypt, default=None):
    """Carrega JSON decriptando campos específicos"""
    if not os.path.exists(filepath):
        return default or []
        
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
            
        if isinstance(data, list):
            for item in data:
                for field in fields_to_decrypt:
                    if field in item:
                        item[field] = decrypt_value(item[field])
        elif isinstance(data, dict):
            for field in fields_to_decrypt:
                if field in data:
                    data[field] = decrypt_value(data[field])
                    
        return data
    except:
        return default or []
