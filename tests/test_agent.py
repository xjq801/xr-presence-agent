import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from xr_agent.agent import review
from xr_agent.protocol import schedule, write_plan


EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


class AgentTests(unittest.TestCase):
    def test_clean_fixture(self):
        result = review(EXAMPLES / "clean.csv", "synthetic")
        self.assertEqual(result["status"], "ready")
        data = result["analysis"]
        self.assertEqual(data["counts"]["included_pairs"], 12)
        self.assertAlmostEqual(data["metrics"]["spatial_presence"]["mean_difference"], 3.8 / 12)
        self.assertEqual(data["sequence_summary"]["BA"]["n_pairs"], 6)

    def test_mixed_fixture(self):
        result = review(EXAMPLES / "mixed.csv", "synthetic")
        self.assertEqual(result["status"], "review")
        data = result["analysis"]
        self.assertEqual(data["counts"]["included_pairs"], 9)
        self.assertEqual(data["metrics"]["task_seconds"]["n_pairs"], 8)
        self.assertEqual(data["excluded_participants"], ["S003", "S008", "S010"])

    def test_blocked_agent_skips_estimation(self):
        with patch("xr_agent.agent.summarize_pairs", side_effect=AssertionError("unexpected tool call")):
            result = review(EXAMPLES / "blocked.csv", "synthetic")
        self.assertEqual(result["status"], "blocked")
        self.assertIsNone(result["analysis"]["metrics"]["spatial_presence"]["mean_difference"])
        self.assertEqual([step["tool"] for step in result["trace"]], ["audit_pairs", "request_correction"])

    def test_plan_is_reproducible_and_balanced(self):
        for n in (2, 11, 12):
            rows = schedule(n, 42)
            self.assertEqual(rows, schedule(n, 42))
            orders = [row["sequence"] for row in rows if row["period"] == 1]
            self.assertLessEqual(abs(orders.count("AB") - orders.count("BA")), 1)
            for row in rows:
                self.assertEqual(row["condition"], row["sequence"][row["period"] - 1])
        with tempfile.TemporaryDirectory() as temp:
            write_plan(Path(temp), 3, 7)
            with (Path(temp) / "worksheet.csv").open(encoding="utf-8-sig", newline="") as handle:
                self.assertTrue(all(row["spatial_presence"] == "" for row in csv.DictReader(handle)))
        with self.assertRaises(ValueError):
            schedule(1, 42)
