"""Legacy password support for accounts imported from the original (Django 1.3) site.

Django 5.1 removed SHA1PasswordHasher. Keeping it LAST in PASSWORD_HASHERS lets old
"sha1$salt$hash" passwords still log in; Django then re-hashes them with the default
(PBKDF2) on that successful login. Once no users have sha1 hashes left, delete this file
and the PASSWORD_HASHERS override in settings.py.
"""
import hashlib

from django.contrib.auth.hashers import BasePasswordHasher, mask_hash, must_update_salt
from django.utils.crypto import constant_time_compare
from django.utils.translation import gettext_noop as _


class LegacySHA1PasswordHasher(BasePasswordHasher):
    algorithm = "sha1"

    def encode(self, password, salt):
        self._check_encode_args(password, salt)
        digest = hashlib.sha1((salt + password).encode()).hexdigest()
        return "%s$%s$%s" % (self.algorithm, salt, digest)

    def decode(self, encoded):
        algorithm, salt, digest = encoded.split("$", 2)
        assert algorithm == self.algorithm
        return {"algorithm": algorithm, "hash": digest, "salt": salt}

    def verify(self, password, encoded):
        decoded = self.decode(encoded)
        return constant_time_compare(encoded, self.encode(password, decoded["salt"]))

    def safe_summary(self, encoded):
        decoded = self.decode(encoded)
        return {
            _("algorithm"): decoded["algorithm"],
            _("salt"): mask_hash(decoded["salt"], show=2),
            _("hash"): mask_hash(decoded["hash"]),
        }

    def must_update(self, encoded):
        return must_update_salt(self.decode(encoded)["salt"], self.salt_entropy)

    def harden_runtime(self, password, encoded):
        pass
