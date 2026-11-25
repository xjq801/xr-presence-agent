"""Paired analysis of a two-period VR audio crossover experiment.

spatial_presence is an already scored IPQ spatial-presence mean on the 0–6
version of the scale. ssq_total is an already weighted, nonnegative SSQ total.
"""

import csv
import math
import random
from collections import defaultdict
from statistics import fmean, mean


METRICS = ("spatial_presence", "ssq_total", "task_seconds", "errors")
PRIMARY = METRICS[0]
COLUMNS = ("participant", "sequence", "period", "condition", *METRICS)
BOOTSTRAP_RESAMPLES = 4000
BOOTSTRAP_SEED = 20261125


def _text(value):
    return "" if value is None else str(value).strip()


def _observation(name, value):
    """Return None for missing, nonfinite or out-of-range measurements."""
    try:
        number = float(_text(value))
    except ValueError:
        return None
    if not math.isfinite(number) or number < 0:
        return None
    if name == PRIMARY and number > 6:
        return None
    if name == "task_seconds" and number == 0:
        return None
    if name == "errors" and not number.is_integer():
        return None
    return number


def _percentile(ordered_values, probability):
    position = (len(ordered_values) - 1) * probability
    i = int(position)
    fraction = position - i
    if fraction == 0:
        return ordered_values[i]
    return (1 - fraction) * ordered_values[i] + fraction * ordered_values[i + 1]


def _mean_finite(values):
    values = list(values)
    try:
        return fmean(values)
    except OverflowError:
        # A finite average can have an intermediate sum beyond float range.
        return float(mean(values))


def _summarize(pairs):
    """Each tuple represents one participant, in condition order (A, B)."""
    n = len(pairs)
    summary = dict(n_pairs=n, mean_a=None, mean_b=None, mean_difference=None, ci95=None)
    if n == 0:
        return summary
    differences = [b - a for a, b in pairs]
    summary.update(mean_a=_mean_finite(a for a, _ in pairs), mean_b=_mean_finite(b for _, b in pairs),
                   mean_difference=_mean_finite(differences))
    if n >= 2:
        if min(differences) == max(differences):
            summary["ci95"] = [differences[0], differences[0]]
        else:
            rng = random.Random(BOOTSTRAP_SEED)
            estimates = sorted(_mean_finite(rng.choices(differences, k=n))
                               for _ in range(BOOTSTRAP_RESAMPLES))
            summary["ci95"] = [_percentile(estimates, q) for q in (0.025, 0.975)]
    return summary


def _check_design(records):
    if len(records) != 2:
        return "row_count", f"需要两行，实际有 {len(records)} 行。"
    sequences = {_text(row["sequence"]).upper() for row in records}
    if len(sequences) != 1 or not sequences <= {"AB", "BA"}:
        return "invalid_sequence", "两行须属于同一序列 AB 或 BA。"
    if sorted(_text(row["period"]) for row in records) != ["1", "2"]:
        return "invalid_period", "期次须为 1 和 2，且各出现一次。"
    sequence = next(iter(sequences))
    if any(_text(row["condition"]).upper() != sequence[int(_text(row["period"])) - 1]
           for row in records):
        return "condition_order", "条件与该序列对应期次的安排不一致。"
    return None


def _validate_columns(columns):
    if len(columns) != len(set(columns)):
        raise ValueError("表头有重复字段，请为每列使用不同的名称。")
    missing = sorted(set(COLUMNS) - set(columns))
    if missing:
        raise ValueError("缺少必需字段：" + ", ".join(missing))


def audit_pairs(rows):
    """Check each pair without computing any estimates."""
    participants = defaultdict(list)
    row_count = 0
    for row_count, row in enumerate(rows, 1):
        if None in row:
            raise ValueError(f"第 {row_count} 条记录比表头多出字段，请检查分隔符。")
        _validate_columns(list(row))
        participant = _text(row["participant"])
        if not participant:
            raise ValueError(f"第 {row_count} 条记录缺少 participant，无法确定配对。")
        participants[participant].append(row)

    issues = []
    excluded = []
    by_metric = {name: [] for name in METRICS}
    by_sequence = {"AB": [], "BA": []}
    for participant, records in sorted(participants.items()):
        design_error = _check_design(records)
        if design_error:
            code, detail = design_error
            issues.append(dict(participant=participant, code=code, detail=detail))
            excluded.append(participant)
            continue

        # Pair by condition, even for BA participants and unsorted input files.
        a, b = sorted(records, key=lambda r: _text(r["condition"]).upper())
        sequence = _text(a["sequence"]).upper()
        for name in METRICS:
            values = (_observation(name, a[name]), _observation(name, b[name]))
            if None in values:
                code = "invalid_primary" if name == PRIMARY else "invalid_secondary"
                conditions = "/".join(c for c, v in zip("AB", values) if v is None)
                detail = f"{name} 在条件 {conditions} 下缺失或超出取值范围。"
                issues.append(dict(participant=participant, code=code, metric=name, detail=detail))
                if name == PRIMARY:
                    excluded.append(participant)
                    break
                continue
            by_metric[name].append(values)
            if name == PRIMARY:
                by_sequence[sequence].append(values)

    return {
        "counts": {
            "rows": row_count,
            "participants": len(participants),
            "included_pairs": len(by_metric[PRIMARY]),
            "excluded_pairs": len(excluded),
        },
        "by_metric": by_metric,
        "by_sequence": by_sequence,
        "issues": issues,
        "excluded_participants": excluded,
    }


def summarize_pairs(audit):
    return {name: _summarize(pairs) for name, pairs in audit["by_metric"].items()}


def inspect_order(audit):
    return {order: _summarize(pairs) for order, pairs in audit["by_sequence"].items()}


def assemble_analysis(audit, metrics, groups):
    return {
        "counts": audit["counts"], "issues": audit["issues"],
        "excluded_participants": audit["excluded_participants"],
        "metrics": metrics, "sequence_summary": groups,
        "method": {
            "difference": "B - A",
            "confidence_level": 0.95,
            "ci": "paired participant percentile bootstrap",
            "resamples": BOOTSTRAP_RESAMPLES,
            "seed": BOOTSTRAP_SEED,
            "limitations": "小样本或差值无变异时，区间可能不稳定或退化为单点。顺序分层只作描述。",
        },
    }


def analyze_rows(rows):
    """Compute descriptive estimates for validated, complete participant pairs."""
    audit = audit_pairs(rows)
    return assemble_analysis(audit, summarize_pairs(audit), inspect_order(audit))


def read_csv(path):
    """Yield records from a UTF-8 CSV with or without BOM."""
    try:
        with open(path, newline="", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file, strict=True)
            _validate_columns(reader.fieldnames or [])
            yield from reader
    except UnicodeDecodeError as exc:
        raise ValueError("CSV 文件需要使用 UTF-8 编码。") from exc
    except csv.Error as exc:
        raise ValueError(f"CSV 语法错误：{exc}") from exc


def analyze_csv(path):
    return analyze_rows(read_csv(path))
