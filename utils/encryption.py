import os
import base64
import hashlib
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.fernet import MultiFernet
from utils.paths import get_app_data_dir
from utils.error_handler import (
    handle_encryption_save_error,
    handle_encryption_operation_error,
)


class TokenEncryption:
    ITERATIONS = 480000
    KEY_VERSION = 1

    def __init__(self):
        self.key_file = os.path.join(get_app_data_dir(), "data", ".encryption_key")
        self.salt_file = os.path.join(get_app_data_dir(), "data", ".salt")
        self.key = self._load_or_create_key()
        self.cipher_suite = self._initialize_cipher() if self.key else None

    def _generate_salt(self) -> bytes:
        return os.urandom(16)

    def _derive_key(self, base_key: bytes, salt: bytes) -> bytes:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=self.ITERATIONS,
        )
        return base64.urlsafe_b64encode(kdf.derive(base_key))

    def _load_or_create_key(self) -> bytes:
        try:
            if os.path.exists(self.key_file) and os.path.exists(self.salt_file):
                try:
                    with open(self.key_file, "rb") as f:
                        key = f.read()
                    with open(self.salt_file, "rb") as f:
                        salt = f.read()
                    return self._derive_key(key, salt)
                except Exception:
                    if os.path.exists(self.key_file):
                        os.remove(self.key_file)
                    if os.path.exists(self.salt_file):
                        os.remove(self.salt_file)

            base_key = os.urandom(32)
            salt = self._generate_salt()

            os.makedirs(os.path.dirname(self.key_file), exist_ok=True)

            self._secure_file_write(self.key_file, base_key)
            self._secure_file_write(self.salt_file, salt)

            self._set_file_attributes(self.key_file)
            self._set_file_attributes(self.salt_file)

            return self._derive_key(base_key, salt)
        except Exception:
            return None

    def _secure_file_write(self, filepath: str, data: bytes):
        try:
            with open(filepath, "wb") as f:
                if os.name == "posix":
                    import stat

                    os.chmod(filepath, stat.S_IRUSR | stat.S_IWUSR)
                f.write(data)
        except Exception:
            from utils.error_handler import handle_encryption_save_error

            handle_encryption_save_error(None)
            raise

    def _set_file_attributes(self, filepath: str):
        try:
            if os.name == "nt":
                import win32security
                import ntsecuritycon as con
                import win32api

                win32api.SetFileAttributes(filepath, 2)

                username = win32api.GetUserName()
                domain = win32api.GetComputerName()
                user_sid, domain, type = win32security.LookupAccountName(
                    domain, username
                )

                security = win32security.GetFileSecurity(
                    filepath, win32security.DACL_SECURITY_INFORMATION
                )
                dacl = win32security.ACL()

                dacl.AddAccessAllowedAce(
                    win32security.ACL_REVISION, win32security.GENERIC_ALL, user_sid
                )

                security.SetSecurityDescriptorDacl(1, dacl, 0)
                win32security.SetFileSecurity(
                    filepath, win32security.DACL_SECURITY_INFORMATION, security
                )
        except Exception:
            pass

    def _initialize_cipher(self) -> MultiFernet:
        if not self.key:
            return None
        return MultiFernet([Fernet(self.key)])

    def rotate_key(self):
        if not self.cipher_suite:
            raise Exception("Encryption not initialized")

        new_base_key = os.urandom(32)
        new_salt = self._generate_salt()
        new_key = self._derive_key(new_base_key, new_salt)

        self.cipher_suite = MultiFernet([Fernet(new_key), Fernet(self.key)])

        self._secure_file_write(self.key_file, new_base_key)
        self._secure_file_write(self.salt_file, new_salt)

        self.key = new_key

    def encrypt_token(self, token: str) -> str:
        try:
            if not self.cipher_suite:
                from utils.error_handler import handle_encryption_operation_error

                handle_encryption_operation_error(None, "initialize")
                return token

            versioned_data = f"v{self.KEY_VERSION}:{token}"
            return self.cipher_suite.encrypt(versioned_data.encode()).decode()
        except Exception:
            from utils.error_handler import handle_encryption_operation_error

            handle_encryption_operation_error(None, "encrypt")
            return token

    def decrypt_token(self, encrypted_token: str) -> str:
        try:
            if not self.cipher_suite:
                from utils.error_handler import handle_encryption_operation_error

                handle_encryption_operation_error(None, "initialize")
                return encrypted_token

            decrypted = self.cipher_suite.decrypt(encrypted_token.encode()).decode()

            if decrypted.startswith("v"):
                version, token = decrypted.split(":", 1)
                return token
            return decrypted
        except Exception:
            from utils.error_handler import handle_encryption_operation_error

            handle_encryption_operation_error(None, "decrypt")
            return encrypted_token
