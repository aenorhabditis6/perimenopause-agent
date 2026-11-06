# Perimenopause agent (Claude hackathon)

一个被动的围绝经期 agent：读 wearable 数据，加上她邮箱里自动发来的收据、预订、预约和日历，找出她自己的规律，并在复诊前替她准备一页就诊摘要。仓库里全部是**合成数据**，人物 Lisa Hartley 是虚构的。

## 跑起来

```bash
/opt/homebrew/bin/python3.12 -m venv .venv      # 或任何 Python 3.12
.venv/bin/pip install -r requirements.txt
cp .env.example .env                              # 填上 ANTHROPIC_API_KEY；.env 不要提交
.venv/bin/uvicorn app.server:app --reload
```

打开 http://127.0.0.1:8000 。没有 API key 也能跑：右上角会显示 offline mode，抽取用答案文件，卡片和摘要用模板。设 `OFFLINE=1` 可以强制离线。

## 演示路径

顶部四个日期依次点：**Aug 13**（察觉）→ **Aug 23**（诱因）→ **Oct 8**（前后对比）→ **Nov 5**，再点 **▶ New email**：诊所的复诊提醒到达，就诊摘要流式出现在右栏。打开 **Agent view** 能看到每封邮件被读取、跳过还是什么都没留下。每张卡片点 “Why I said this” 展开证据表，有邮件来源的行可以点回原邮件。

## 目录

| 路径 | 内容 |
| --- | --- |
| `app/server.py` | FastAPI：页面和接口（`/api/emails`、`/api/insights?as_of=`、`/api/live-email`、`/api/brief/stream`） |
| `app/data.py` | 读数据、发件人过滤、卡片数字和模板文案、就诊摘要的输入 |
| `app/claude_calls.py` | 三处 Claude 调用：邮件抽取、卡片文案、就诊摘要（流式）。模型 `claude-opus-5-5` |
| `app/prompts/` | 三个系统提示词 |
| `app/static/index.html` | 前端，单文件，原生 JS |
| `scripts/` | 批量抽取、对答案评测、预生成卡片和备用摘要 |
| `cache/` | Claude 的输出；存在时 app 自动改用（演示兜底也靠它） |
| `lisa_demo_data/` | 合成数据、参考统计 `analysis/analyze.py`、答案 `truth/`。先读里面的 README |

## Claude 这一步（C 负责）

```bash
.venv/bin/python scripts/extract_all.py --limit 10                              # 先试 10 封
.venv/bin/python scripts/eval_extraction.py cache/extracted_events_first10.json # 对答案
.venv/bin/python scripts/extract_all.py                                         # 全部 115 封自动邮件 → cache/extracted_events.json
.venv/bin/python scripts/eval_extraction.py
.venv/bin/python scripts/precompute.py                                          # Claude 写卡片 + 备用就诊摘要
```

全量抽取写好之后，app 自动改用 Claude 的结果（右上角显示 `events from claude`）。统计的数字应该和用答案文件时一样，不一样就看 `eval_extraction.py` 的报错行。

代码里按默认开了 `fallbacks="default"`：安全分类器拒绝时，服务端自动换模型重跑。

## 分工和检查点

- **A · 数据与统计**：`lisa_demo_data/analysis/analyze.py`、`app/data.py`、接口。
- **B · 前端**：`app/static/index.html`，时间线、卡片、证据表、就诊摘要的样子。
- **C · Claude 与 slides**：`app/claude_calls.py`、`app/prompts/`、`scripts/`，最后改 slides。

检查点（从开工算）：1:20 抽取 10 封对上答案 → 3:00 各自 P0 完成 → 3:40 现场路径跑通 → 5:00 上台。过了 3:40 只打磨，不加功能。

## 规则

- `.env` 不提交；`truth/` 只给团队对答案用，不能喂给 agent。
- 每人改自己负责的文件；push 前先 `git pull --rebase`。
