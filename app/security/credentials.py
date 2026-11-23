import json

from cryptography.fernet import Fernet
from flask import current_app


"""
   This file contains the credentials for the database
   It is used to encrypt and decrypt sensitive data
"""

def encrypt_credentials(username=None, password=None):

    key = current_app.config["CREDENTIAL_ENCRYPTION_KEY"]

    credentials = {
        "username": username,
        "password": password
    }

    encrypted = Fernet(key.encode()).encrypt(
        json.dumps(credentials).encode()
    )

    return encrypted.decode()


def decrypt_credentials(encrypted_credentials):

    key = current_app.config["CREDENTIAL_ENCRYPTION_KEY"]

    decrypted = Fernet(key.encode()).decrypt(
        encrypted_credentials.encode()
    )

    return json.loads(decrypted.decode())