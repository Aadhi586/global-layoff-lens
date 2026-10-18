"""Smoke and behavior checks for every public API route."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from backend.app import app


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health_overview_and_filtering(self):
        self.assertEqual(self.client.get("/api/health").status_code, 200)
        all_data = self.client.get("/api/overview").json()
        self.assertEqual(all_data["events"], 4615)
        filtered = self.client.get("/api/overview", params={"year": 2026}).json()
        self.assertLess(filtered["events"], all_data["events"])
        self.assertIn("Series A", all_data["stage_options"])
        by_stage = self.client.get("/api/overview", params={"stage": "Series A"}).json()
        self.assertLess(by_stage["events"], all_data["events"])

    def test_dataset_search_sort_pagination_and_empty_state(self):
        response = self.client.get("/api/dataset", params={"page": 1, "page_size": 5, "sort_by": "date", "columns": "company,date"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["rows"]), 5)
        self.assertEqual(response.json()["columns"], ["company", "date"])
        self.assertEqual(self.client.get("/api/dataset", params={"search": "no-such-record-xyz"}).json()["total"], 0)
        self.assertEqual(self.client.get("/api/dataset", params={"sort_by": "unknown"}).status_code, 422)

    def test_company_comparison_and_not_found(self):
        company = self.client.get("/api/companies", params={"limit": 1}).json()["items"][0]["company"]
        self.assertEqual(self.client.get(f"/api/company/{company}").status_code, 200)
        other = self.client.get("/api/companies", params={"limit": 2}).json()["items"][1]["company"]
        comparison = self.client.get("/api/compare", params={"company_a": company, "company_b": other})
        self.assertEqual(comparison.status_code, 200)
        self.assertEqual(len(comparison.json()["companies"]), 2)
        self.assertEqual(self.client.get("/api/compare", params={"company_a": company, "company_b": company}).status_code, 422)
        self.assertEqual(self.client.get("/api/company/DefinitelyNotACompany").status_code, 404)
        self.assertEqual(self.client.get("/api/stability", params={"name": company}).status_code, 200)

    def test_analysis_and_documentation_endpoints(self):
        for path in ("/api/industries", "/api/countries", "/api/stages", "/api/trends", "/api/eda/statistics",
                     "/api/eda/distributions", "/api/eda/correlation", "/api/cleaning", "/api/insights"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)
        self.assertEqual(self.client.get("/api/trends", params={"granularity": "bad"}).status_code, 422)
        self.assertEqual(self.client.get("/api/eda/distributions", params={"field": "company"}).status_code, 422)
        self.assertEqual(self.client.get("/api/dataset", params={"year": 2026, "start_date": "bad-date"}).status_code, 422)
        search = self.client.get("/api/search", params={"q": "canada"})
        self.assertEqual(search.status_code, 200)
        self.assertTrue(search.json()["countries"])


if __name__ == "__main__":
    unittest.main()
