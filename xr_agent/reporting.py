"""Render a single agent run to portable Chinese Markdown or offline HTML."""

import html
import math
import re
from dataclasses import dataclass, field


TITLE = "XR 空间声音与在场感实验分析报告"
METRIC_LABELS = {
    "spatial_presence": "IPQ 空间在场感（0–6 分）",
    "ssq_total": "模拟器晕动症问卷 SSQ 总分",
    "task_seconds": "任务用时（秒）",
    "errors": "错误次数（次）",
}
STATUS_LABELS = {
    "ready": "已完成",
    "review": "需复核",
    "blocked": "分析已暂停",
}


@dataclass
class Section:
    title: str
    paragraphs: list = field(default_factory=list)
    headers: tuple = ()
    rows: list = field(default_factory=list)
    items: list = field(default_factory=list)


def _number(value, signed=False):
    if value is None or not math.isfinite(value):
        return "—"
    # Avoid a signed negative zero when a tiny effect rounds to zero.
    rounded = round(value, 2) or 0
    return f"{rounded:+.2f}" if signed else f"{rounded:.2f}"


def _interval(bounds):
    if bounds is None:
        return "—"
    return f"[{_number(bounds[0], True)}, {_number(bounds[1], True)}]"


def _metric_row(label, metric):
    return (
        label, metric["n_pairs"], _number(metric["mean_a"]), _number(metric["mean_b"]),
        _number(metric["mean_difference"], True), _interval(metric["ci95"]),
    )


def _sections(record):
    status = record["status"]
    source = record["source"]
    analysis = record.get("analysis") or {}
    source_note = (
        "输入为合成演示数据。表中的差值仅用于验证计算流程，不能用来判断真实参与者的体验。"
        if source == "synthetic" else
        "输入为本次提供的 CSV 文件。对真实体验的解释取决于数据来源、采集过程和量表计分是否可靠。"
    )
    yield Section("分析任务", [
        f"目标：{record['goal']}",
        f"运行状态：{STATUS_LABELS[status]}。{source_note}",
    ])

    counts = analysis.get("counts")
    if counts:
        yield Section(
            "数据纳入情况",
            ["每名参与者按条件配对。纳入人数以主要指标 IPQ 空间在场感为准，次要指标各自使用有效配对。"],
            ("输入记录数", "参与者数", "纳入配对数", "排除人数"),
            [tuple(counts[key] for key in ("rows", "participants", "included_pairs", "excluded_pairs"))],
        )

    if status == "blocked":
        yield Section("分析结果", ["本次运行已暂停，结果表和效果判断不予生成。请根据运行记录修正输入后重新分析。"])
    elif analysis.get("metrics"):
        metrics = analysis["metrics"]
        yield Section(
            "两种条件的配对结果",
            ["A 为普通立体声，B 为随头转动的空间声。先为每名参与者计算 B 减 A，再对有效配对取均值。正值表示 B 的数值较高。"
             "IPQ 空间在场感分数越高表示在场感越强，SSQ 总分越高表示症状越重。"
             "用时与错误次数保留原单位。"],
            ("指标", "配对数", "A 均值", "B 均值", "平均差 B−A", "探索性 95% 区间"),
            [_metric_row(label, metrics[key]) for key, label in METRIC_LABELS.items() if key in metrics],
        )
        sequence = analysis.get("sequence_summary", {})
        if sequence:
            yield Section(
                "按体验顺序查看空间在场感",
                ["AB 组先体验 A，BA 组先体验 B。两个组均按 B 减 A 计算，分组结果用于查看顺序差异的线索。"],
                ("体验顺序", "配对数", "A 均值", "B 均值", "平均差 B−A", "探索性 95% 区间"),
                [_metric_row(key, sequence[key]) for key in ("AB", "BA") if key in sequence],
            )
        yield Section("区间的解释", [
            "95% 区间通过对参与者的配对差值进行有放回重抽样估计。有效配对少于两对时不计算区间，"
            "表中以“—”显示。小样本的区间可能不稳定，差值完全相同时区间会缩为单点。",
            "配对均值和分组区间用于描述本次输入。仅凭这些结果无法排除练习、疲劳、残留效应或个体差异的影响。",
        ])

    if "issues" in analysis:
        issues = analysis["issues"]
        if issues:
            yield Section(
                "数据核查记录", headers=("参与者", "问题代码", "说明"),
                rows=[(issue["participant"], issue["code"], issue["detail"]) for issue in issues],
            )
        else:
            yield Section("数据核查记录", ["本次配对校验未记录到异常。"])
    if record.get("actions"):
        yield Section("后续操作", items=record["actions"])
    if record.get("trace"):
        yield Section(
            "Agent 工具调用记录", headers=("步骤", "工具", "调用原因", "观察结果"),
            rows=[(i, step["tool"], step["reason"], step["observation"])
                  for i, step in enumerate(record["trace"], 1)],
        )


def _plain(value):
    return " ".join(str(value).splitlines()).strip()


def _md(value):
    # Source-provided goal, participant IDs and observations may contain markup.
    text = html.escape(_plain(value), quote=False)
    escaped = re.sub(r"([\\`*_{}\[\]()#+!|~])", r"\\\1", text)
    return re.sub(r"^(\s*)(-|\d+\.)(?=\s)", lambda m: m[1] + m[2][:-1] + "\\" + m[2][-1], escaped)


def render_markdown(record):
    """Return a self-contained report suitable for a Markdown viewer."""
    lines = [f"# {TITLE}", ""]
    for section in _sections(record):
        lines.extend([f"## {section.title}", ""])
        for paragraph in section.paragraphs:
            lines.extend([_md(paragraph), ""])
        if section.headers:
            lines.extend(["| " + " | ".join(section.headers) + " |",
                          "| " + " | ".join("---" for _ in section.headers) + " |"])
            for row in section.rows:
                lines.append("| " + " | ".join(_md(cell) for cell in row) + " |")
            lines.append("")
        if section.items:
            lines.extend("- " + _md(item) for item in section.items)
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


CSS = """
:root { color-scheme: light; }
* { box-sizing: border-box; }
body { margin: 0; color: #172c37; background: #eef3f4; font: 16px/1.65 system-ui, "Microsoft YaHei", sans-serif; }
main { max-width: 980px; margin: 2rem auto; padding: 2rem 3rem; background: white; }
h1 { font-size: 1.8rem; margin: 0 0 1.4rem; line-height: 1.3; }
h2 { font-size: 1.2rem; color: #0c5161; margin: 1.8rem 0 .5rem; break-after: avoid; }
p, ul { margin: .5rem 0; } ul { padding-left: 1.5rem; }
.table-wrap { overflow-x: auto; }
table { border-collapse: collapse; width: 100%; font-size: .93rem; }
th, td { border: 1px solid #ccd7d9; padding: .4rem .55rem; text-align: left;
          vertical-align: top; overflow-wrap: anywhere; font-variant-numeric: tabular-nums; }
th { background: #e6f0f0; } p, li { overflow-wrap: anywhere; }
@media (max-width: 640px) { main { margin: 0; padding: 1rem; } }
@media print {
  @page { margin: 15mm; }
  body, main { background: white; margin: 0; padding: 0; max-width: none; }
  body { font-size: 10.5pt; } h1 { font-size: 17pt; } h2 { font-size: 12.5pt; }
  .table-wrap { overflow: visible; } tr { break-inside: avoid; } thead { display: table-header-group; }
}
"""


def _html(value):
    return html.escape(_plain(value), quote=True)


def render_html(record):
    """Return an offline, printable HTML document with escaped run data."""
    parts = ['<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">',
             '<meta name="viewport" content="width=device-width, initial-scale=1">',
             f"<title>{TITLE}</title><style>{CSS}</style></head><body><main><h1>{TITLE}</h1>"]
    for section in _sections(record):
        parts.extend(["<section>", f"<h2>{section.title}</h2>"])
        parts.extend(f"<p>{_html(p)}</p>" for p in section.paragraphs)
        if section.headers:
            parts.append('<div class="table-wrap"><table><thead><tr>')
            parts.extend(f'<th scope="col">{_html(label)}</th>' for label in section.headers)
            parts.append("</tr></thead><tbody>")
            for row in section.rows:
                parts.append("<tr>" + "".join(f"<td>{_html(cell)}</td>" for cell in row) + "</tr>")
            parts.append("</tbody></table></div>")
        if section.items:
            parts.append("<ul>" + "".join(f"<li>{_html(item)}</li>" for item in section.items) + "</ul>")
        parts.append("</section>")
    parts.append("</main></body></html>")
    return "\n".join(parts) + "\n"
