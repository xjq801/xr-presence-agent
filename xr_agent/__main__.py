"""python -m xr_agent --help"""

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

from .agent import review
from .protocol import write_plan
from .reporting import render_html, render_markdown


def export_review(directory, record):
    (directory / "analysis.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    for name, render in (("report.html", render_html), ("report.md", render_markdown)):
        (directory / name).write_text(render(record), encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description="空间声音与在场感配对实验智能体")
    modes = parser.add_subparsers(dest="mode", required=True)
    plan = modes.add_parser("plan", help="生成随机平衡排程、记录表和实验方案")
    plan.add_argument("--participants", type=int, required=True)
    plan.add_argument("--seed", type=int, default=42)
    audit = modes.add_parser("review", help="质控并生成配对结果和行动记录")
    audit.add_argument("csv", type=Path)
    audit.add_argument("--source", choices=("synthetic", "supplied"), required=True,
                       help="synthetic 为模拟，supplied 为自行提供的记录")
    demo = modes.add_parser("demo", help="运行内置合成样例")
    demo.add_argument("--case", choices=("clean", "mixed", "blocked"), default="mixed")
    for mode in (plan, audit, demo):
        mode.add_argument("--out", type=Path, required=True, help="新建的输出目录，每次运行使用新目录")
    args = parser.parse_args(argv)
    try:
        dest = args.out.resolve()
        if dest.exists():
            raise ValueError("输出目录已存在，请指定一个新目录。")
        dest.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=dest.parent) as tmp:
            staged = Path(tmp) / "run"
            staged.mkdir()
            if args.mode == "plan":
                write_plan(staged, args.participants, args.seed)
                message = "排程与记录表已生成"
            else:
                if args.mode == "demo":
                    path = Path(__file__).parent.parent / "examples" / f"{args.case}.csv"
                    source = "synthetic"
                else:
                    path, source = args.csv, args.source
                record = review(path, source)
                export_review(staged, record)
                message = f"分析状态 {record['status']}"
            if dest.exists():
                raise FileExistsError("输出目录已存在")
            os.rename(staged, dest)
    except (ValueError, OSError) as error:
        print(f"运行失败：{error}", file=sys.stderr)
        return 2
    print(f"{message} | {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
