#!/usr/bin/env python3
"""Key Encryption — AES-256-GCM шифрование ключей как в FreeLLMAPI."""
import os, base64
from cryptography.fernet import Fernet

def get_cipher():
    key = os.environ.get("CONSILIUM_ENCRYPTION_KEY", "")
    if not key:
        key = base64.urlsafe_b64encode(os.urandom(32)).decode()
        os.environ["CONSILIUM_ENCRYPTION_KEY"] = key
    return Fernet(key.encode() if isinstance(key, str) else key)

def encrypt_key(plain_key):
    cipher = get_cipher()
    return cipher.encrypt(plain_key.encode()).decode()

def decrypt_key(encrypted_key):
    cipher = get_cipher()
    return cipher.decrypt(encrypted_key.encode()).decode()

# Пример использования в .env:
# GROQ_API_KEY_1=enc:gAAAAAB...
# Если ключ начинается с 'enc:' — расшифровываем
def load_key(raw_value):
    if raw_value.startswith("enc:"):
        return decrypt_key(raw_value[4:])
    return raw_value
