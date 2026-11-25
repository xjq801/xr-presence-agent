"""Observation-driven policy. One goal, a small tool set and an explicit trace."""

from .analysis import (
    METRICS, assemble_analysis, audit_pairs, inspect_order, read_csv, summarize_pairs,
)


GOAL = "评估头动空间声相对普通立体声的配对空间在场感差值。"


def review(path, source):
    if source not in {"synthetic", "supplied"}:
        raise ValueError("需要标注输入数据来源。")
    audit = audit_pairs(read_csv(path))
    counts = audit["counts"]
    pairs = counts["included_pairs"]
    trace = []
    actions = []

    def record(tool, reason, observation):
        trace.append(dict(tool=tool, reason=reason, observation=observation))

    record("audit_pairs", "先核对每人的分期、顺序和主要终点。",
           f"读取 {counts['rows']} 行，识别 {counts['participants']} 人，保留 {pairs} 对。")
    if not pairs:
        status = "blocked"
        empty = dict(n_pairs=0, mean_a=None, mean_b=None, mean_difference=None, ci95=None)
        metrics = {name: empty.copy() for name in METRICS}
        groups = {name: empty.copy() for name in ("AB", "BA")}
        record("request_correction", "没有可用于主要终点的完整配对。", "停止解读差值，输出核查清单。")
        actions.append("按配对诊断检查原始记录和分配顺序，补正可追溯的值后重新运行。")
    else:
        metrics = summarize_pairs(audit)
        primary = metrics["spatial_presence"]
        record("summarize_pairs", "主要终点具备可用配对。",
               f"按人计算 B−A，均值差 {primary['mean_difference']:+.3f} 分。")
        groups = inspect_order(audit)
        ab, ba = (groups[key]["n_pairs"] for key in ("AB", "BA"))
        record("inspect_order", "检查差值是否集中在某一种体验顺序。", f"AB 纳入 {ab} 对，BA 纳入 {ba} 对。")
        if not ab or not ba:
            actions.append("核对仅有一种有效顺序的原因；当前资料无法比较两种体验顺序。")
        elif abs(ab - ba) > 1:
            actions.append("两种顺序的有效人数不平衡，请复核缺失与退出是否集中于同一顺序。")
        if counts["excluded_pairs"]:
            actions.append("核对被排除者的原始记录与退出原因，保留排除记录。")
        if pairs < 2:
            actions.append("只有一对可用观测，仅可描述该人的差值。")
        incomplete = [key for key, value in metrics.items() if value["n_pairs"] < pairs]
        if incomplete:
            actions.append("次要结果存在缺项，使用各指标自己的有效对数：" + "、".join(incomplete) + "。")
        status = "review" if actions else "ready"
        record("prepare_output", "根据诊断选择后续动作。",
               "需要复核，保留可用配对的描述。" if actions else "配对和顺序检查通过，可查看描述性汇总。")
    if source == "synthetic":
        actions.append("本次记录为合成样例，仅用于检验软件流程。")
    result = assemble_analysis(audit, metrics, groups)
    return dict(goal=GOAL, source=source, status=status, trace=trace, actions=actions, analysis=result)
