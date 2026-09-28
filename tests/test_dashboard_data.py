import unittest
from io import BytesIO

import pandas as pd

from src.dashboard_data import Rules, normalize, read_csv, review_metrics, score_transactions


class DashboardDataTests(unittest.TestCase):
    def setUp(self):
        self.raw = pd.DataFrame({
            "date": ["2025-01-01 00:00", "2025-01-01 01:00", "2025-01-01 02:00", "2025-01-01 03:00"],
            "payer": ["A", "C", "B", "B"], "payee": ["B", "B", "D", "E"],
            "value": [100, 100, 150, 200],
        })
        self.mapping = {"time": "date", "sender": "payer", "receiver": "payee", "amount": "value"}

    def test_custom_columns_and_no_label(self):
        d, q = normalize(self.raw, self.mapping)
        self.assertEqual(q["usable"], 4)
        self.assertEqual(d["currency"].unique().tolist(), ["Unknown"])
        self.assertIsNone(review_metrics(score_transactions(d, Rules())))

    def test_threshold_changes_queue_and_history_patterns(self):
        d, _ = normalize(self.raw, self.mapping)
        strict = score_transactions(d, Rules(amount=1000, frequency=2, fan_in=2, alert_score=5))
        relaxed = score_transactions(d, Rules(amount=1000, frequency=2, fan_in=2, alert_score=2))
        self.assertLess(int(strict["alert"].sum()), int(relaxed["alert"].sum()))
        self.assertTrue(bool(relaxed.loc[2, "rapid_outflow"]))
        self.assertEqual(int(relaxed.loc[1, "distinct_senders_rolling"]), 2)

    def test_cleaning_removes_invalid_and_duplicate_rows(self):
        bad = pd.concat([self.raw, self.raw.iloc[[0]], self.raw.iloc[[1]]], ignore_index=True)
        bad.loc[5, "value"] = -3
        _, q = normalize(bad, self.mapping)
        self.assertEqual((q["invalid"], q["duplicates"], q["usable"]), (1, 1, 4))

    def test_large_upload_is_rejected_without_silent_sampling(self):
        with self.assertRaisesRegex(ValueError, "超过"):
            read_csv(BytesIO(b"a\n1\n2\n3\n"), max_rows=2)


if __name__ == "__main__":
    unittest.main()
