"""
Custom storage engine that encrypts files on save and decrypts on read.
Uses the same FIELD_ENCRYPTION_KEY as the database fields.
"""

from django.core.files.storage import FileSystemStorage
from django.core.files.base import ContentFile
from cryptography.fernet import Fernet
from django.conf import settings


class EncryptedFileSystemStorage(FileSystemStorage):
    def _get_fernet(self):
        # Uses the key from your .env file
        return Fernet(settings.FIELD_ENCRYPTION_KEY.encode())

    def _save(self, name, content):
        """Encrypt the file bytes before saving to disk."""
        # Read the original file bytes
        original_bytes = content.read()
        # Encrypt them
        encrypted_bytes = self._get_fernet().encrypt(original_bytes)
        # Save the encrypted bytes to disk
        return super()._save(name, ContentFile(encrypted_bytes))

    def _open(self, name, mode="rb"):
        """Decrypt the file bytes when opening."""
        # Open the encrypted file from disk
        file = super()._open(name, mode)
        # Read and decrypt
        decrypted_bytes = self._get_fernet().decrypt(file.read())
        # Return as a standard Django file object
        return ContentFile(decrypted_bytes, name=name)