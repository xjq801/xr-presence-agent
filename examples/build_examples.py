"""Rebuild the three fictional course fixtures. Run from this directory or any other."""

import csv
from pathlib import Path


def build():
    # Presence is an already-scored five-item mean on a 0–6 scale.
    a = [3.0, 3.6, 4.4, 2.8, 3.4, 4.0, 4.2, 3.2, 3.8, 3.4, 4.6, 3.0]
    delta = [.8, .4, -.2, 1.0, 0, .6, -.4, .2, .4, .8, -.2, .4]
    orders = ["AB", "BA", "BA", "AB", "BA", "AB", "BA", "AB", "AB", "BA", "AB", "BA"]
    time_delta = [-3, -2, 1, -4, 2, -1, 3, 0, -2, -3, 1, -1]
    ssq_delta = [0, 1, 0, -1, 0, 0, 1, 0, -1, 1, 0, 0]
    clean = []
    for i, order in enumerate(orders):
        for period, condition in enumerate(order, 1):
            b = condition == "B"
            clean.append(dict(
                participant=f"S{i + 1:03}", sequence=order, period=period, condition=condition,
                spatial_presence=round(a[i] + (delta[i] if b else 0), 1),
                ssq_total=round(3.74 * (1 + i % 3 + (ssq_delta[i] if b else 0)), 2),
                task_seconds=42 + 2 * (i % 5) + (time_delta[i] if b else 0),
                errors=max(0, (i % 3) - (1 if b and i % 2 else 0)),
            ))
    mixed = []
    for original in clean:
        row = original.copy()
        identifier = row["participant"]
        if identifier == "S010" and row["period"] == 2:
            continue
        if identifier == "S003" and row["condition"] == "B":
            row["spatial_presence"] = ""
        if identifier == "S008" and row["period"] == 2:
            row["condition"] = "A"
        if identifier == "S005" and row["condition"] == "B":
            row["task_seconds"] = ""
        mixed.append(row)
    bad_ids = {"S003", "S008", "S010"}
    blocked = [row for row in mixed if row["participant"] in bad_ids]
    root = Path(__file__).resolve().parent
    for name, rows in (("clean", clean), ("mixed", mixed), ("blocked", blocked)):
        with (root / f"{name}.csv").open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=list(clean[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)


if __name__ == "__main__":
    build()
