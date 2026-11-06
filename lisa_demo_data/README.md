# Lisa 的合成数据（hackathon demo 用）

Lisa Hartley 是虚构人物：46 岁，住在 Oakland，戴 Oura 戒指，从不记录症状。这里所有人名、商家、地址都是编的，邮箱一律用保留域名 `.example`。数据覆盖 2026-07-06 到 2026-11-04 共 122 个晚上；11-05 早上那封诊所提醒邮件是现场演示时“到达”的。

```bash
python3 generate_lisa_data.py      # 重新生成全部数据（seed 固定为 94，结果每次一样）
python3 analysis/analyze.py        # 不用 LLM 的参考分析，输出 analysis/expected_insights.json
python3 preview/build_preview.py   # 重建邮箱预览页 preview/inbox_preview.html
```

换一个 seed：`LISA_SEED=7 python3 generate_lisa_data.py`。seed 94 是从 300 个里挑出来的，诱因、对照组和治疗前后的差异在它上面最清楚。

## 文件

| 路径 | 内容 | 格式 |
| --- | --- | --- |
| `profile/lisa_profile.json` | 人物资料、作息、设备、经期历史、故事时间线 | 自定义 JSON |
| `emails/emails.json` | 收件箱 134 封（纯文本 + HTML 正文） | 类 Gmail 的消息列表 |
| `emails/live_demo_email.json` | 现场演示时到达的复诊提醒（11-05 08:12） | 同上，单封 |
| `emails/eml/*.eml` | 同样 135 封邮件的 .eml 文件，可以拖进 Apple Mail 或 Outlook 打开 | RFC 5322 |
| `calendar/events.json` | 日历事件（网球、读书会、聚会、出差、就诊） | Google Calendar API v3 `events.list` |
| `wearables/oura/*.json` | sleep、daily_sleep、daily_readiness、daily_activity、workout、enhanced_tag（空）、personal_info | Oura API v2，字段名对照官方 OpenAPI 1.43 |
| `wearables/apple_health/export.xml` | 同一批夜晚，换成 Apple Watch 记录的版本，外加 iPhone 里的经期记录 | Apple Health 导出格式 |
| `app_state/confirmations.json` | Lisa 在 app 里点过的 9 次一键确认 | 自定义 JSON |
| `truth/` | **答案，只给团队看，不要喂给 agent**：每晚的真实情况、每封邮件应该抽取出什么 | CSV / JSON |
| `analysis/analyze.py` | 参考统计实现：适配器、夜间发热判定、诱因、前后对比、周期 | Python 标准库 |
| `preview/inbox_preview.html` | 通用邮箱界面，带 “Agent view” 开关和“模拟新邮件”按钮 | 单文件 HTML，双击打开 |

## 埋进数据里的故事（参考分析的实际输出）

| 场景 | 时间 | 数据里能看到的 |
| --- | --- | --- |
| 察觉 | 08-13 早上 | 过去 14 晚有 5 晚夜间发热醒来；前 28 晚的基线是每周 0.2 次 |
| 找诱因 | 07-24 至 09-03 | 有酒的晚上 7 晚里有 6 晚发热，其他晚上 32 晚里有 8 晚（p = 0.005）。打网球的晚上没有差别（5 晚里 2 晚，其他 37 晚里 13 晚）；在外吃饭但没喝酒的那 1 晚没有发热 |
| 改变有没有用 | 09-04 开始新处方 | 夜间发热每周 3.2 次 → 0.5 次（08-07 至 09-03 对比 10-08 至 11-04，p = 0.002）；喝酒频率前后都是每周 1.5 次，夜里醒着的时间平均 44 → 34 分钟 |
| 就诊摘要 | 11-05 提醒邮件到达 | 11-10 复诊（Dr. Elena Ruiz）；已经试过降温枕套、吸湿睡衣、褪黑素、床头风扇；最近 4 个周期长度 26、38、22、43 天 |

“夜间发热”的判定规则：当晚 `temperature_deviation ≥ +0.30 °C`，并且 01:30–05:00 之间有一段至少 15 分钟的清醒。Oura 和 Apple 两套数据用同一条规则，跑出来的结论完全一致。

## 容易踩的坑

- **Oura 的 `day` 是醒来那天。** 10-14 晚上喝的酒，对应的是 `day = 10-15` 的睡眠。合成数据按这个规则生成；接真实数据时请再核对一次。
- **Oura 公开 API 没有经期接口**（OpenAPI 1.43 里没有任何 cycle 或 period 端点）。所以经期来自 Apple Health 里 Lisa 自己记的经期，这是她原本就有的习惯。
- **夏令时**：11-01 凌晨 2 点结束夏令时，之后的时间戳是 `-08:00`。算时长要用 UTC，不要直接拿本地时间相减。
- **私人邮件不读**：朋友、家人、同事的邮件在发给 Claude 之前就按发件人过滤掉（answer key 里标为 `skip_personal`），只处理自动发出的收据、预订和预约。社交活动的线索来自日历标题。
- **药名不会出现在邮件里**：药房邮件只说“有 1 个处方可取”，治疗开始的日期靠 Lisa 在 app 里点一次确认。
- **陷阱邮件**：09-19 的本地新闻简报提到了 “Oakland Wine Walk”，那不是 Lisa 的安排，抽取时不应该算成喝酒证据。
- **每封 HTML 邮件页脚都写着 “Synthetic demo email”**，截图流出去也能看出是假数据。
