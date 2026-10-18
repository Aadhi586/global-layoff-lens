"""Cleaning pipeline checks using isolated temporary fixtures."""
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from backend.services.data_cleaner import clean


class PipelineTests(unittest.TestCase):
    def test_duplicate_invalid_date_negative_and_percentage_handling(self):
        rows = [
            {"company":"Example A", "location":"City", "total_laid_off":10, "date":"2024-01-01", "percentage_laid_off":.25, "industry":"Tech", "source":"https://example.test", "stage":"Series A", "funds_raised":50, "country":"Canada", "date_added":"2024-01-02"},
            {"company":"Example A", "location":"City", "total_laid_off":10, "date":"2024-01-01", "percentage_laid_off":.25, "industry":"Tech", "source":"https://example.test", "stage":"Series A", "funds_raised":50, "country":"Canada", "date_added":"2024-01-02"},
            {"company":"Example B", "location":"City", "total_laid_off":-3, "date":"not-a-date", "percentage_laid_off":1.2, "industry":"Tech", "source":"", "stage":"Seed", "funds_raised":-1, "country":"Canada", "date_added":"2024-02-02"},
        ]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); raw=root/"raw.csv"; processed=root/"processed.csv"; metadata=root/"metadata"
            pd.DataFrame(rows).to_csv(raw, index=False)
            report = clean(raw, processed, metadata)
            result = pd.read_csv(processed)
            self.assertEqual(report["before"]["rows"], 3)
            self.assertEqual(report["removed_duplicates"], 1)
            self.assertEqual(report["invalid_values"]["date"], 1)
            self.assertEqual(report["invalid_values"]["total_laid_off_negative"], 1)
            self.assertEqual(report["invalid_values"]["percentage_laid_off_above_one"], 1)
            self.assertEqual(report["invalid_values"]["funds_raised_negative"], 1)
            self.assertEqual(report["removed_missing_required"], 1)
            self.assertEqual(len(result), 1)
            self.assertEqual(report["after"]["rows"], 1)
            self.assertTrue((metadata/"cleaning_report.json").exists())
            self.assertTrue((metadata/"eda_summary.json").exists())


if __name__ == "__main__":
    unittest.main()
