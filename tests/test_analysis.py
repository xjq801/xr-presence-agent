import csv
import tempfile
import unittest
from pathlib import Path

from xr_agent.analysis import COLUMNS, analyze_csv, analyze_rows


def pair(participant, sequence, a, b):
    return [
        dict(participant=participant, sequence=sequence, period=str(i), condition=c,
             spatial_presence=a if c == "A" else b, ssq_total=0, task_seconds=20,
             errors=0)
        for i, c in enumerate(sequence, 1)
    ]


class AnalysisTests(unittest.TestCase):
    def test_direction_sequence_and_bootstrap(self):
        rows = pair("P1", "AB", 1, 4) + pair("P2", "BA", 4, 3)
        result = analyze_rows(reversed(rows))
        self.assertEqual(result["metrics"]["spatial_presence"],
                         dict(n_pairs=2, mean_a=2.5, mean_b=3.5, mean_difference=1, ci95=[-1, 3]))
        self.assertEqual(result["sequence_summary"]["AB"]["mean_difference"], 3)
        self.assertEqual(result["sequence_summary"]["BA"]["mean_difference"], -1)
        self.assertEqual(result, analyze_rows(rows))

    def test_primary_or_design_errors_exclude_whole_pair(self):
        good = pair("Good", "BA", 0, 6)
        missing = pair("Missing", "AB", "", 3)
        wrong = pair("Wrong", "AB", 3, 3)
        wrong[0]["condition"] = "B"
        duplicate = pair("Duplicate", "AB", 2, 3)
        duplicate.append(dict(duplicate[0]))
        result = analyze_rows(good + missing + wrong + duplicate)
        self.assertEqual(result["counts"], dict(rows=9, participants=4, included_pairs=1,
                                                excluded_pairs=3))
        self.assertEqual(result["excluded_participants"], ["Duplicate", "Missing", "Wrong"])
        self.assertEqual({r["code"] for r in result["issues"]},
                         {"invalid_primary", "condition_order", "row_count"})
        self.assertEqual(result["metrics"]["ssq_total"]["n_pairs"], 1)
        self.assertIsNone(result["metrics"]["spatial_presence"]["ci95"])

    def test_secondary_is_endpoint_wise_and_values_are_checked(self):
        ab = pair("A", "AB", 2, 3)
        ba = pair("B", "BA", 4, 3)
        ab[0].update(errors="1.5", task_seconds="0", ssq_total="inf")
        ba[1]["ssq_total"] = ""
        result = analyze_rows(ab + ba)
        self.assertEqual(result["counts"]["included_pairs"], 2)
        self.assertEqual(result["metrics"]["errors"]["n_pairs"], 1)
        self.assertEqual(result["metrics"]["task_seconds"]["n_pairs"], 1)
        self.assertEqual(result["metrics"]["ssq_total"]["n_pairs"], 0)
        self.assertIsNone(result["metrics"]["ssq_total"]["mean_difference"])
        self.assertEqual(len(result["issues"]), 4)

    def test_empty_and_no_variation(self):
        self.assertEqual(analyze_rows([])["counts"]["rows"], 0)
        rows = pair("A", "AB", 5, 5) + pair("B", "BA", 4, 4)
        self.assertEqual(analyze_rows(rows)["metrics"]["spatial_presence"]["ci95"], [0, 0])
        for row in rows:
            row["task_seconds"] = 1e308
        self.assertEqual(analyze_rows(rows)["metrics"]["task_seconds"]["mean_a"], 1e308)

    def test_missing_identity_and_required_columns(self):
        with self.assertRaisesRegex(ValueError, "participant"):
            analyze_rows(pair("", "AB", 1, 2))
        with self.assertRaisesRegex(ValueError, "缺少必需字段"):
            analyze_rows([{"participant": "P1"}])

    def test_csv_header_encoding_and_delimiters(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.csv"
            with path.open("w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=COLUMNS)
                writer.writeheader()
                writer.writerows(pair("甲", "BA", 3, 5))
            self.assertEqual(analyze_csv(path)["metrics"]["spatial_presence"]["mean_difference"], 2)
            with path.open("a", encoding="utf-8") as f:
                f.write(",".join(["x"] * (len(COLUMNS) + 1)) + "\n")
            with self.assertRaisesRegex(ValueError, "多出字段"):
                analyze_csv(path)
            path.write_text(",".join((*COLUMNS, "errors")), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "重复"):
                analyze_csv(path)

    def test_nonfinite_and_out_of_range_primary_and_bad_period(self):
        for value in ["NaN", "Infinity", "-0.2", "6.1", "bad"]:
            with self.subTest(value=value):
                self.assertEqual(analyze_rows(pair("P", "AB", value, 5))["counts"]["included_pairs"], 0)
        bad_sequence = pair("P", "AB", 1, 2)
        bad_sequence[1]["sequence"] = "BA"
        self.assertEqual(analyze_rows(bad_sequence)["issues"][0]["code"], "invalid_sequence")
        repeated_period = pair("P", "AB", 1, 2)
        repeated_period[1]["period"] = "1"
        self.assertEqual(analyze_rows(repeated_period)["issues"][0]["code"], "invalid_period")


if __name__ == "__main__":
    unittest.main()
