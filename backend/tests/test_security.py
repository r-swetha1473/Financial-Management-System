"""Password hashing tests — existing hashes must still verify after bcrypt rounds pin."""

import unittest

from passlib.context import CryptContext

from app.core.security import hash_password, verify_password


class BcryptRoundsTests(unittest.TestCase):
    def test_new_hashes_use_cost_12(self) -> None:
        hashed = hash_password("admin123")
        self.assertTrue(hashed.startswith("$2"))
        self.assertIn("$12$", hashed)

    def test_legacy_unpinned_hashes_still_verify(self) -> None:
        legacy = CryptContext(schemes=["bcrypt"], deprecated="auto")
        hashed = legacy.hash("admin123")
        self.assertTrue(verify_password("admin123", hashed))
        self.assertFalse(verify_password("wrong-password", hashed))

    def test_older_cost_10_hashes_still_verify(self) -> None:
        older = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=10)
        hashed = older.hash("admin123")
        self.assertIn("$10$", hashed)
        self.assertTrue(verify_password("admin123", hashed))


if __name__ == "__main__":
    unittest.main()
