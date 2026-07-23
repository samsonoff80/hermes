#!/usr/bin/env python3
"""Шифрование ключей провайдеров (Fernet).

ЧЕСТНО ОБ АЛГОРИТМЕ: используется cryptography.Fernet — это AES-128-CBC
с HMAC-SHA256 для аутентификации, а НЕ AES-256-GCM, как было написано
в README и в прежнем докстринге. Стойкость для нашей задачи достаточная,
но называть это AES-256-GCM неверно.

Формат в .env:
    GROQ_API_KEY_1=enc:gAAAAAB...

Ключ шифрования берётся ТОЛЬКО из переменной окружения
CONSILIUM_ENCRYPTION_KEY. Раньше при её отсутствии генерировался случайный
ключ на каждый старт процесса — расшифровать им ранее зашифрованные
значения было невозможно, то есть все enc:-ключи молча превращались в мусор.

Сгенерировать ключ:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""
import os
import logging
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger("consilium.crypto")

ENV_VAR = "CONSILIUM_ENCRYPTION_KEY"


class EncryptionKeyMissing(RuntimeError):
    """CONSILIUM_ENCRYPTION_KEY не задана, а в .env есть enc:-значения."""


def get_cipher() -> Fernet:
    key = os.environ.get(ENV_VAR, "").strip()
    if not key:
        raise EncryptionKeyMissing(
            f"{ENV_VAR} не задана. Сгенерируйте ключ командой "
            f'python -c "from cryptography.fernet import Fernet; '
            f'print(Fernet.generate_key().decode())" и добавьте его в окружение сервиса.'
        )
    try:
        return Fernet(key.encode())
    except (ValueError, TypeError) as e:
        raise EncryptionKeyMissing(f"{ENV_VAR} имеет неверный формат: {e}") from e


def encrypt_key(plain_key: str) -> str:
    """Возвращает значение уже с префиксом enc: — сразу можно класть в .env."""
    return "enc:" + get_cipher().encrypt(plain_key.encode()).decode()


def decrypt_key(encrypted_key: str) -> str:
    if encrypted_key.startswith("enc:"):
        encrypted_key = encrypted_key[4:]
    try:
        return get_cipher().decrypt(encrypted_key.encode()).decode()
    except InvalidToken as e:
        raise EncryptionKeyMissing(
            "Значение не расшифровывается текущим CONSILIUM_ENCRYPTION_KEY "
            "(ключ сменился или значение повреждено)."
        ) from e


def load_key(raw_value: str) -> str:
    """Прозрачно расшифровывает enc:-значения, обычные возвращает как есть."""
    if not raw_value or not raw_value.startswith("enc:"):
        return raw_value
    return decrypt_key(raw_value)


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Использование: python key_encryption.py <ключ-провайдера>")
        sys.exit(2)
    try:
        print(encrypt_key(sys.argv[1]))
    except EncryptionKeyMissing as e:
        print(f"Ошибка: {e}")
        sys.exit(1)
