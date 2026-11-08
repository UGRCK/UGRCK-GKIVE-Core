"""Run five sequential local API smoke tests for the UGRCK server.

Usage:
    python3 test_api.py

The test harness starts an ephemeral server bound only to 127.0.0.1 and shuts
it down after the tests. No external service or third-party package is needed.
"""
import json
import threading
import unittest
from http.server import HTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from server import UGRCKEnterpriseServer


class QuietUGRCKServer(UGRCKEnterpriseServer):
    def log_message(self, format, *args):
        pass


class SequentialApiSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = HTTPServer(("127.0.0.1", 0), QuietUGRCKServer)
        cls.base_url = f"http://127.0.0.1:{cls.httpd.server_port}"
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join(timeout=2)

    def post_json(self, path, body):
        request = Request(
            self.base_url + path,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=3) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            return error.code, json.loads(error.read().decode("utf-8"))

    def test_1_valid_state_is_accepted(self):
        payload = {
            "target_system": {
                "identifier": "test-valid",
                "domain": "test",
                "state": [0.88, 0.92, 0.85, 0.90],
                "flows": {"stream_1": [0.05, 0.05, 0.05, 0.05]},
                "lower_bounds": [1e-9] * 4,
            },
            "control_vectors": {
                "gradient": [1.0] * 4,
                "dynamic_matrix": [1.0] * 4,
            },
        }
        status, response = self.post_json("/api/v1/kernel/execute", payload)
        self.assertEqual(status, 200)
        self.assertEqual(response["status"], "success")
        self.assertEqual(len(response["renewed_state"]), 4)

    def test_2_zero_state_coordinate_is_rejected(self):
        payload = {
            "target_system": {
                "identifier": "test-zero",
                "domain": "test",
                "state": [0.0, 0.85, 0.90, 0.95],
                "flows": {},
                "lower_bounds": [1e-9] * 4,
            },
            "control_vectors": {"gradient": [1.0] * 4, "dynamic_matrix": [1.0] * 4},
        }
        status, response = self.post_json("/api/v1/kernel/execute", payload)
        self.assertEqual(status, 400)
        self.assertEqual(response["status"], "RED_BOLT")

    def test_3_negative_state_coordinate_is_rejected(self):
        payload = {
            "target_system": {
                "identifier": "test-negative",
                "domain": "test",
                "state": [0.8, -0.1, 0.9, 0.95],
                "flows": {},
                "lower_bounds": [1e-9] * 4,
            },
            "control_vectors": {"gradient": [1.0] * 4, "dynamic_matrix": [1.0] * 4},
        }
        status, response = self.post_json("/api/v1/kernel/execute", payload)
        self.assertEqual(status, 400)
        self.assertEqual(response["status"], "RED_BOLT")

    def test_4_unknown_endpoint_returns_not_found(self):
        status, response = self.post_json("/unknown", {})
        self.assertEqual(status, 404)
        self.assertEqual(response["error"], "Endpoint not found")

    def test_5_malformed_json_is_reported_as_server_error_current_behavior(self):
        request = Request(
            self.base_url + "/api/v1/kernel/execute",
            data=b"{invalid json",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with self.assertRaises(HTTPError) as raised:
            urlopen(request, timeout=3)
        self.assertEqual(raised.exception.code, 500)
        response = json.loads(raised.exception.read().decode("utf-8"))
        self.assertIn("error", response)


if __name__ == "__main__":
    unittest.main(verbosity=2)
