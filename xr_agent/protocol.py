"""Materialize the study protocol and a randomly counterbalanced worksheet."""

import csv
import random
from pathlib import Path

from .analysis import COLUMNS
PROTOCOL = """# 空间声音与在场感配对实验

## 研究问题

同一个人在同一场景完成同一项任务时，用随头转动的空间声（B）替换普通立体声（A），其 IPQ 空间在场感评分如何变化？主要估计量是每人 B 减 A 后所得差值的平均数。

## 体验与记录

1. 使用同一个头显、耳机、音量标定、声源素材、场景、画质和任务。A 使用固定普通立体声；B 根据头部朝向更新声音方位。预检 B 的追踪方向，记录设备型号与渲染配置。
2. 按 schedule.csv 指定的顺序执行。任务可设为找到场景内发声物体并确认。事先固定练习流程、每段时长、间隔、确认方式和错误定义，对两种条件一视同仁。记录退出原因，允许随时停止。
3. 每段结束后用预定版本的完整 IPQ 采集体验，将正反向条目按该版本统一计分，再把空间在场感子量表均分换算至 0–6；如已在 −3 至 +3 上完成同向计分，均分加 3。另记已计分的 SSQ 总分、完成时间（秒）与错误次数。未完成或未采得的值留空，不以零替代。
4. worksheet.csv 使用化名，每人每期一行。保留分配时生成的 participant、sequence、period、condition；校对原始记录后填入结果。序列字段表示预先分配的顺序，评估工具检查文件内部一致性，不能独立核实实际播放条件。
5. 两组人数尽量相等。AB 先 A 后 B，BA 相反。分析时保留 B−A 的统一方向，并按顺序分别呈现；练习、疲劳或前一条件的残留影响仍需在实际设计中控制。

## 量表与指标

IPQ 空间在场感是主要结果。SSQ 记录不适，任务时间与错误数反映任务表现。分开报告四个指标，不相加为一个体验总分。正式采集前应确定量表版本、主要分析与缺失处理，并记录中途退出。该程序接收已计分的量表结果，不承担逐题反向编码。

IPQ 官方资料：https://www.igroup.org/pq/ipq/data.php
SSQ 原始论文：https://doi.org/10.1207/s15327108ijap0303_3
"""


def write_csv(path, fields, rows):
    with Path(path).open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def schedule(participants, seed):
    if not 2 <= participants <= 5000:
        raise ValueError("参与人数须在 2 至 5000 之间。")
    rng = random.Random(seed)
    orders = ["AB", "BA"] * (participants // 2)
    if participants % 2:
        orders.append(rng.choice(["AB", "BA"]))
    rng.shuffle(orders)
    return [
        {"participant": f"P{index:03}", "sequence": order,
         "period": period, "condition": condition}
        for index, order in enumerate(orders, 1)
        for period, condition in enumerate(order, 1)
    ]


def write_plan(directory, participants, seed):
    rows = schedule(participants, seed)
    write_csv(directory / "schedule.csv", COLUMNS[:4], rows)
    write_csv(directory / "worksheet.csv", COLUMNS, rows)
    plan = f"\n本次排程为 {participants} 个化名，排程种子 {seed}。\n"
    (directory / "protocol.md").write_text(PROTOCOL + plan, encoding="utf-8")
