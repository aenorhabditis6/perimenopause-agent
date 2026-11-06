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

## 隐私：三个模式和一个本地模型

三个模式从最私密排到最省心。邮箱接入时，每封邮件都先过一个**本地分类模型**（fastText，量化后 363 KB，每封 0.016 ms），在设备上判断它是什么。私人邮件在这一步就停下，哪个模式都不会发出去。另外有一道保险：模型认为一封邮件有 10% 以上的可能是私人邮件，它也不离开设备（`PERSONAL_GUARD`）。

| 模式 | 什么会离开设备 | 谁做抽取 | 她要做什么 |
| --- | --- | --- | --- |
| **Manual** | 只有她自己上传的收据照片，发出前去掉 GPS 位置等所有元数据；照片不保存，只留抽出来的一行 | Claude 看照片 | 每次拍一张收据 |
| **Filtered**（默认） | 本地模型判为有用、又在她勾选的类别里的邮件全文（Lisa 的 134 封里有 75 封）。勾选“在设备上抽取”后，一封邮件都不发，只发结构化的行 | Claude，或设备上的规则 | 一次性勾选类别 |
| **Full** | 除了私人邮件以外的所有邮件（98 封），以及所有数据源 | Claude | 什么都不用做 |

在 Lisa 的数据上，Filtered 加“在设备上抽取”时，4 个日期上的发现和交给 Claude 时完全一样。代价是规则只认识见过的邮件格式；而且关掉某一类，就会少一类发现。比如关掉药房，agent 不知道哪天开始了治疗，就不会有“改变有没有用”这张卡。Manual 模式只有她上传的那几张收据，证据通常不够，诱因卡片不会出现，这也是它的代价。

Manual 模式的演示：点 Manual，左栏点一张示例收据（`lisa_demo_data/receipt_photos/`，带有假的 GPS 元数据），右栏会显示读出来的那一行和“已去掉 GPS 位置”。没有 API key 时，示例照片按答案文件读出；读新照片需要 Claude。

**本地模型的测试结果**（训练集是 2600 封另外合成的邮件，商家、措辞、年份都和 Lisa 的不同；测试集是 Lisa 的 135 封）：

- 私人邮件被误判成“有用”、会离开设备的：0 封
- 有用邮件被漏掉的：0 / 76
- 无关邮件会被发给 Claude 的：4 封（网球俱乐部的简报），加上 10% 那道保险后是 0 封，有用邮件仍然一封不漏
- 总体准确率 86%；错误主要是把 14 封新闻简报或学校通知当成私人邮件，偏保守，不会泄露
- 去掉发件人姓名和地址后再测，准确率不变，泄露和漏掉仍然是 0，说明模型靠的是内容，不是记住发件人

这些数字来自合成数据，只能说明流程是通的，不代表真实邮箱上的效果。正式版的 Private 模式可以用手机上的端侧大模型来做抽取，替代现在的规则。

```bash
.venv/bin/python app/local_model/make_corpus.py   # 生成训练邮件
.venv/bin/python app/local_model/train.py         # 训练 + 在 Lisa 的邮件上测 → app/local_model/metrics.json
.venv/bin/python scripts/eval_private_mode.py     # Private 模式端到端：抽取准确率 + 发现是否和答案一致
```

## Claude 这一步（C 负责）

```bash
.venv/bin/python scripts/extract_all.py --limit 10                              # 先试 10 封
.venv/bin/python scripts/eval_extraction.py cache/extracted_events_first10.json # 对答案
.venv/bin/python scripts/extract_all.py                                         # 本地模型放行的 75 封 → cache/extracted_events.json
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
