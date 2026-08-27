"""Dual-shape error envelope {code, message, details, detail} is applied globally."""

from __future__ import annotations

import unittest
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app

LOGIN_URL = "/api/v1/auth/login"
VENDORS_URL = "/api/v1/p2p/vendors"


def _access_token(body: dict) -> str:
    data = body.get("data") or {}
    return data.get("accessToken") or data.get("access_token")


class ErrorEnvelopeTests(unittest.TestCase):
    client: TestClient
    _client_cm: object

    @classmethod
    def setUpClass(cls) -> None:
        cls._client_cm = TestClient(app)
        cls.client = cls._client_cm.__enter__()

    @classmethod
    def tearDownClass(cls) -> None:
        cls._client_cm.__exit__(None, None, None)

    def test_404_includes_code_message_and_detail(self) -> None:
        login = self.client.post(LOGIN_URL, json={"email": "admin@demo-business.com", "password": "admin123"})
        self.assertEqual(login.status_code, 200, login.text)
        token = _access_token(login.json())
        response = self.client.get(
            f"{VENDORS_URL}/{uuid4()}",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 404, response.text)
        body = response.json()
        self.assertEqual(body["code"], "404")
        self.assertTrue(body["message"])
        self.assertEqual(body["detail"], body["message"])
        self.assertIn("details", body)

    def test_401_includes_code_message_and_detail(self) -> None:
        response = self.client.get(VENDORS_URL)
        self.assertEqual(response.status_code, 401, response.text)
        body = response.json()
        self.assertEqual(body["code"], "401")
        self.assertTrue(body["message"])
        self.assertEqual(body["detail"], body["message"])
