"""CORS is an exact origin allow-list. There is no *.vercel.app regex fallback."""

import unittest

from fastapi.testclient import TestClient
from starlette.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.main import app

HEALTH = "/health"
EVIL_VERCEL = "https://arbitrary-other-app.vercel.app"


class CorsAllowListTests(unittest.TestCase):
    client: TestClient
    _client_cm: object

    @classmethod
    def setUpClass(cls) -> None:
        cls._client_cm = TestClient(app)
        cls.client = cls._client_cm.__enter__()

    @classmethod
    def tearDownClass(cls) -> None:
        cls._client_cm.__exit__(None, None, None)

    def test_middleware_has_no_origin_regex(self) -> None:
        cors = next(item for item in app.user_middleware if item.cls is CORSMiddleware)
        self.assertIsNone(cors.kwargs.get("allow_origin_regex"))
        self.assertNotIn("allow_origin_regex", cors.kwargs)

    def test_pinned_origin_is_echoed(self) -> None:
        allowed = settings.cors_origin_list[0]
        response = self.client.get(HEALTH, headers={"Origin": allowed})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.headers.get("access-control-allow-origin"), allowed)

    def test_arbitrary_vercel_origin_is_rejected(self) -> None:
        self.assertNotIn(EVIL_VERCEL, settings.cors_origin_list)
        response = self.client.get(HEALTH, headers={"Origin": EVIL_VERCEL})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertNotEqual(response.headers.get("access-control-allow-origin"), EVIL_VERCEL)
        self.assertIsNone(response.headers.get("access-control-allow-origin"))

    def test_preflight_from_other_vercel_app_is_rejected(self) -> None:
        response = self.client.options(
            HEALTH,
            headers={
                "Origin": EVIL_VERCEL,
                "Access-Control-Request-Method": "GET",
            },
        )
        self.assertNotEqual(response.headers.get("access-control-allow-origin"), EVIL_VERCEL)


if __name__ == "__main__":
    unittest.main()
