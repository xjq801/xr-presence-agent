# 空间声音与在场感配对实验智能体

这个离线 Agent 服务于一项 VR 组内实验。每位参与者各体验一次普通立体声（A）和随头转动的空间声（B）。它先生成 AB/BA 排程，收到两期记录后核对配对，再按结果选择计算差值、检查顺序或请求修正。主要结果是 IPQ 空间在场感，辅助结果是 SSQ 不适、任务用时与错误次数。

## 两步体验

可先查看一次真实运行生成的[混合样例分析报告](examples/report-mixed.md)，其中的输入均为合成记录。

在装有 Python 3.9 或更高版本的电脑上克隆仓库并进入项目目录。仅使用 Python 标准库，无需配置模型、密钥或联网服务。

```bash
git clone https://github.com/xjq801/xr-presence-agent.git
cd xr-presence-agent
python -m xr_agent demo --case mixed --out runs/demo
```

用浏览器打开 `runs/demo/report.html`。程序会解释为什么空间在场感保留 9 对、任务用时只有 8 对，并列出需核查的样例编号。相同结果也保存在 `report.md`，完整数值与行动记录在 `analysis.json`。每次运行请指定新输出目录，以保留既有结果。

## 从方案到分析

```bash
python -m xr_agent plan --participants 12 --seed 42 --out runs/plan
python -m xr_agent review examples/clean.csv --source synthetic --out runs/clean
python -m unittest discover -s tests -v
```

1. `plan` 生成 `protocol.md`、含分配结果的 `schedule.csv` 和等待填分的 `worksheet.csv`。偶数时两种顺序人数相同，奇数时相差一人。种子控制随机排程。
2. 采集时保留原始排程，使用化名。固定头显、耳机、音量标定、场景、画质和任务。按所用问卷版本先把条目统一计分，再录入量表得分。
3. 自行提供的文件可运行 `python -m xr_agent review runs/plan/worksheet.csv --source supplied --out runs/observed`。先填写工作表。来源由操作者声明，内置演示一律标为模拟。分析在本机完成。

### CSV 字段

| 字段 | 含义及导入口径 |
| --- | --- |
| participant | 匿名编号，同一人两行 |
| sequence | AB 或 BA，两期相同 |
| period、condition | 期次 1 或 2，以及该期实际记录的 A 或 B；按编号和条件配对 |
| spatial_presence | 已计分的 IPQ 空间在场感子量表均分，统一至 0–6；如采用 −3 至 +3 版本，先按相应版本完成条目计分，再将均分加 3 |
| ssq_total | 已计分的 SSQ 总分，须为有限非负数 |
| task_seconds | 任务完成时间，单位为秒，须大于 0 |
| errors | 错误次数，须为非负整数 |

使用 UTF-8 CSV，支持带 BOM。缺失测量留空，零值按字段含义处理。主终点缺失、重复或缺少期次、条件与所记顺序矛盾时，整人的配对退出本次分析。某个次要结果缺失时，只对该结果排除该人。表头错误或缺少参与者编号会终止运行并显示原因。程序检查记录内部的一致性；录入时仍需与保存的排程及设备日志核对。

### 三个可复现的情景

| 合成输入 | 可用主终点 | Agent 的选择 |
| --- | ---: | --- |
| `clean` · 24 行 | 12/12 | `ready`，输出四项结果和顺序分层。主要差值 +0.32 分 |
| `mixed` · 23 行 | 9/12 | `review`，列出三人配对排除原因，并单独标出一人的用时缺失 |
| `blocked` · 5 行 | 0/3 | `blocked`，跳过估计工具，只输出诊断与修正提示 |

命令格式为 `python -m xr_agent demo --case clean --out runs/another`。样例中的所有值均由 `examples/build_examples.py` 构造，可重新生成。样例间共享记录，用于验证同一套策略在不同输入下的选择。

### 如何解读

每位参与者先计算 B−A，再对配对差取算术平均。每项结果单独报告 A、B 均值、有效对数、均值差和按参与者重抽样的探索性 95% 百分位区间（4,000 次，种子 20261125）。少于两对时区间留空。按 AB/BA 分层有助于发现顺序差异的线索。样本少时区间不稳定，退出和残留效应也可能影响真实研究。模拟数据只验证软件，不提供空间声改善体验的实验证据。

## 程序入口

| 路径 | 职责 |
| --- | --- |
| `xr_agent/__main__.py` | 处理命令、写入完整运行目录 |
| `xr_agent/agent.py` | 读取审查结果，选择下一项工具并记录原因 |
| `xr_agent/protocol.py` | 生成随机平衡排程、记录表与实验说明 |
| `xr_agent/analysis.py` | 核查配对、计算指标、按体验顺序分层 |
| `xr_agent/reporting.py` | 输出可离线查看的中文 Markdown 和 HTML |
| `examples/`、`tests/` | 合成输入与可重复的功能检查 |

## 方法来源

- Potter, Cvetković & De Sena (2022). *On the Relative Importance of Visual and Spatial Audio Rendering on VR Immersion*. [原文](https://doi.org/10.3389/frsip.2022.904866)
- iGroup Presence Questionnaire. [量表说明](https://www.igroup.org/pq/ipq/index) · [历史数据库与 0–6 计分](https://www.igroup.org/pq/ipq/data.php)
- Kennedy et al. (1993). *Simulator Sickness Questionnaire: An Enhanced Method for Quantifying Simulator Sickness*. [原文](https://doi.org/10.1207/s15327108ijap0303_3)
