# AUDIT 2026-07-30 — constraint `TOO_MUCH_CAPITAL_LOCK` + `TOO_FEW_TRADES` (READ-ONLY)

> Bước 1 của NEXT trong `HANDOFF_20260729_entry_alpha_harness.md`. KHÔNG sửa code, KHÔNG chạy job.
> Mọi số đọc từ source + `D:\claudedata\step2_final_verdict.md` đã có. Quyết định thuộc Uni.

## Vị trí code (single source)

| Thứ | File:dòng |
|---|---|
| Ngưỡng 2 constraint | `ai_ml/hpo/HPOFitnessCalculatorV4.java:36-40` |
| Áp dụng constraint | `HPOFitnessCalculatorV4.java:172-193` |
| Gọi cho CẢ IS và OOS (dùng chung 1 hàm `backtest`) | `ai_ml/wfo/framework/tasks/StrategyWfoTask.java:315` (def `:303`; IS `:222`, OOS `:239`) |
| Dùng note chấm verdict | `StrategyWfoTask.java:346` (posCount++), `:352` (posRatio), `:356` (gọi collectSuccessWfe, def `:435`) |
| Ngưỡng verdict pre-reg | `StrategyWfoTask.java:53-55` |
| `timeUpdate` refresh mỗi tick | `research/OrderTargetInfoTest.java:125` |
| Lệnh còn MỞ cuối kỳ nhồi vào `allOrderDone` | `research/SimulatorMarketLevelTicker1MStopLoss.java:392-410` (`timeUpdate` gán ở `:404`, put ở `:409`) |

3 ngưỡng (`MAX_PCT_HELD_OVER_7D`, `MAX_DD_PCT`, `MIN_POS_YEAR_RATIO`) là `public static` **thuần** —
KHÔNG có env override (khác `WFO_MOM15_LO/HI`). Mỗi lần đổi ngưỡng = rebuild + scp jar.

⚠️ **min-trade floor KHÔNG phải field** — literal `5` và `0.33f` hardcode inline tại `:109` trong
`evaluateDetailed`. ⇒ **P5 phải EXTRACT field trước, không chỉ bọc env.** Scope P5 lớn hơn tưởng.

## Logic chính xác

```
minTrades       = max(5, windowDays * 0.33)
pctHeldOver7d   = #{order : timeUpdate - timeStart > 7d} / tradeCount    // đếm LEG, không cân notional
reject TOO_FEW_TRADES        iff tradeCount   < minTrades                // check TRƯỚC cả PnL
reject TOO_MUCH_CAPITAL_LOCK iff pctHeldOver7d > 0.02                    // check SAU PnL>0, SAU ddPct
```

Thứ tự check ĐẦY ĐỦ (đã verify): `TOO_FEW_TRADES` (`:173`) → `BURN_ACCOUNT` (`:180`) →
`OVER_MAXDD` (`:181`) → `TOO_MUCH_CAPITAL_LOCK` (`:182`) → `UNSTABLE_ACROSS_YEARS` (`:191`).

`windowDays` = độ dài range thật → IS 12 tháng ⇒ `minTrades = 120`.
OOS 3 tháng = 90–92 ngày ⇒ `minTrades` **29 hoặc 30**, không đồng nhất: window Jan–Apr (w4, w8, w12)
có 90 ngày ⇒ `(int)(90*0.33) = 29`; các window khác 91–92 ngày ⇒ 30.

## L1 — ORDERING INVERSION: ramp `TOO_FEW_TRADES` ĐÈ mọi reject khác (BUG, không phải "ngưỡng chặt")

V4.2 đổi TOO_FEW từ hằng `REJECT_BASE` sang ramp tỉ lệ (nhánh `:173-179`, công thức `:177`).
So sánh thang điểm (`REJECT_BASE = -100000f`, `:51`):

```
TOO_FEW      : -100000 * (1 - N/minTrades)   in (-100000, 0)
CAPITAL_LOCK : -100000 - 100 * pctHeld       in [-100100, -100002)
OVER_MAXDD   : -100000 - 100 * ddPct         <  -100065
BURN_ACCOUNT : -100000 + totalProfit         <= -100000
```

Comment `:174-176` (bất biến cụ thể ở `:175`) chỉ chứng minh bất biến so với **SUCCESS**, KHÔNG xét
thứ bậc giữa các reject.
Hệ quả số học: genome chỉ có **1 lệnh** trên IS 12 tháng (minTrades=120) ghi
`-100000*(1-1/120) = -99166.7`, **CAO HƠN** genome có PnL dương nhưng capital-lock (`-100002`).

⇒ Khi không sample nào đạt SUCCESS trên IS, HPO **ưu tiên genome gần-như-không-trade** hơn genome
đang lãi. Đây là cơ chế sinh trực tiếp "7/13 window ZERO/TOO_FEW" của verdict cũ.

## L2 — CAPITAL_LOCK bind hết sample ⇒ hàm mục tiêu ÂM THẦM đổi thành "giữ càng ngắn càng tốt"

Nếu mọi sample IS đều CAPITAL_LOCK thì `finalFitness = -100000 - 100*pctHeld` ⇒ argmax = **min
pctHeldOver7d**. Calmar bị loại HOÀN TOÀN khỏi bài toán chọn genome.

Nhánh A step-2 có `isNote = TOO_MUCH_CAPITAL_LOCK` ở **mọi** window (kể cả IS) → điều kiện này
KHÔNG hiếm, nó là **mặc định**.

**Hệ quả chiến lược:** harness đang **chủ động chọn genome đánh lướt**. Chiến lược là long-only +
trailing + không hard-SL — "nuôi lãi" NGHĨA LÀ giữ dài. Constraint 2% biến giữ dài thành tiêu chí
bị loại. Và **6/17 gene LÀ exit param** (`StrategyWfoTask.java:77-82` — `RATE_PROFIT_STOP_MARKET`,
`TS_PROFIT_MULTIPLIER`, `TS_DYNAMIC_K`, `TS_MAX_GAP`, `TS_MAX_GAP_WEAK`, `TS_WEAK_MOMENTUM_THRES`;
toàn bộ 17 gene ở `:69-85`) → HPO đang chọn chúng.
⇒ Hành vi "chọn coin pump nhưng đánh lướt" KHÔNG chỉ do label 6%, mà bị **fitness harness cưỡng chế**.
⇒ Tune exit TRƯỚC khi sửa harness là vô nghĩa: harness sẽ kéo exit về lướt lần nữa.

## L3 — 0.02 là RATIO, không scale-invariant ⇒ thực chất zero-tolerance ở window ngắn

Ngưỡng 0.02 hiệu chỉnh từ backtest FULL 2021-2026, **70 711 lệnh**, %held>7d thực = 0.31%
(headroom ~6×, xem javadoc `:24-30`). Ở window OOS 3 tháng, N chỉ 17–500:

| N (trades) | ngưỡng 0.02*N | số leg >7d ĐỦ để loại |
|---:|---:|---:|
| 17 | 0.34 | **1** |
| 35 | 0.70 | **1** |
| 53 | 1.06 | 2 |
| 142 | 2.84 | 3 |
| 245 | 4.90 | 5 |

Cụ thể **w6 (35 trades, net +690.40, winRate 1.000)** bị loại bởi có thể chỉ **MỘT** leg giữ >7 ngày.
Headroom 6× mà ngưỡng được thiết kế để có đã biến mất hoàn toàn.

Thêm: lệnh còn MỞ cuối window bị force-close vào `allOrderDone` (`Simulator...:392-410`) với
`timeUpdate` = tick cuối (`OrderTargetInfoTest:125` refresh mỗi tick) ⇒ mọi vị thế mở >7 ngày ở mép
phải window đều tính held-too-long. Window càng ngắn, tỉ lệ mép phải càng lớn.

## L4 — Metric đo SAI thứ nó khai

`pctHeldOver7d` đếm theo **LEG**, không cân notional, không cân thời gian. 1 vị thế bé nằm 8 ngày =
bị loại; 29 vị thế lớn nằm 6.9 ngày = PASS. Tên constraint là "giam vốn", đại lượng đo là "tỉ lệ
lệnh chậm". Hai thứ khác nhau.

## L5 — Aggregate BẤT ĐỐI XỨNG: window bị disqualify bị phạt HAI lần

- `posRatio = posCount / n` (`posCount++` `:346`, `posRatio` `:352`) — mẫu số `n` gồm CẢ window
  disqualify ⇒ tính là **fail**.
- `wfeMedian` chỉ lấy window `SUCCESS` (`collectSuccessWfe` gọi `:356`, def `:435`) ⇒ window đó bị
  **xoá khỏi** median.

Window lãi-nhưng-CAPITAL_LOCK kéo `posRatio` xuống nhưng KHÔNG được góp WFE (thường là WFE tốt).
Thiên lệch một chiều về FAIL.

## L6 (phụ) — hai ngưỡng maxDD không khớp

`MAX_DD_PCT = 0.65` (fitness, `:36`) vs `PASS_MAXDD_OOS = 0.50` (verdict, `StrategyWfoTask:55`).
Window ddPct 0.60 → note SUCCESS nhưng phá verdict maxDD. Lệch theo chiều bảo thủ, ưu tiên thấp.

## ĐỊNH LƯỢNG — 2 constraint này loại bao nhiêu window ĐANG LÃI

Nhánh A frozen (leakage-free), vùng verdict w2–w14, N=13:

| oosNote | # window | Σ oosPnl (net) |
|---|---:|---:|
| `SUCCESS` | 1 (w7) | +690.21 |
| `TOO_MUCH_CAPITAL_LOCK` | **8** (w3,5,6,8,9,10,11,12) | **+9 277.19 — DƯƠNG toàn bộ** |
| `TOO_FEW_TRADES` | 4 (w2,4,13,14) | +138.41 (w2 +211.88, w4 +4.75, w13 −21.06, w14 −57.16) |

Reconcile: `690.21 + 9 277.19 + 138.41 = 10 105.81` ≈ `Σ net non-w15 = +10 105.82` của
`step2_final_verdict.md` (lệch 0.01 do làm tròn từng window) ✓.

⚠️ **2 lỗi trong `step2_final_verdict.md` cần sửa:**
1. §"bằng chứng phụ trợ" ghi "7 window TOO_MUCH_CAPITAL_LOCK" — **bảng cho 8**. Văn bản cho
   1+7+4 = 12 ≠ 13. Số bảng đúng (1+8+4 = 13 ✓).

**Số học posRatio nếu sửa — PRE-REGISTER TRƯỚC KHI CHẠY:**

| kịch bản | posCount/13 | % | vs PASS 70% |
|---|---:|---:|---|
| hiện tại | 1/13 | 7.7% | FAIL |
| CAPITAL_LOCK → report-only trên OOS | 9/13 | **69.2%** | **FAIL, thiếu ĐÚNG 1 window** |
| + hạ sàn min-trade OOS xuống <=17 (vớt w2) | 10/13 | **76.9%** | PASS ngưỡng này |

w4 (2 trades) và w13/w14 (âm) FAIL ở mọi kịch bản hợp lý — đúng, chúng nên fail.

⇒ **Sửa CAPITAL_LOCK một mình KHÔNG đủ (69.2% < 70%). Phải sửa cả 2.**
WFE_median >= 0.5 và worstDdPct <= 0.50 CHƯA biết (bảng step-2 không có cột `wfe`/`ddPct`) ⇒ KHÔNG
được nói PASS.

## ĐỀ XUẤT NỚI CÓ NGUYÊN TẮC (P0–P6) — chờ Uni quyết, CHƯA làm gì

**Tiền lệ trong CHÍNH file này:** `MIN_POS_YEAR_RATIO` từng loại oan genome tốt vì ngưỡng
full-backtest áp lên window 12 tháng, đã được vá bằng **guard theo độ dài window**
(`spanYears` `:190`, guard `:191`, comment giải thích từ `:185`). `MAX_PCT_HELD_OVER_7D` và
`minTrades` là **cùng một lớp lỗi, chưa được vá**. Đề xuất dưới áp đúng nguyên tắc đó.

| ID | Nội dung | Sửa lỗ hổng | Chi phí |
|---|---|---|---|
| **P0** | Đặt ramp TOO_FEW xuống DƯỚI mọi reject khác (vd `2*REJECT_BASE + ramp`) | L1 | 1 dòng |
| **P1** | Tách ngữ nghĩa IS vs OOS: trên OOS chỉ `ZERO_TRADES`+`BURN_ACCOUNT` disqualify; CAPITAL_LOCK/TOO_FEW/UNSTABLE → report-only flag | L2, L5 | trung bình |
| **P2** | `pctHeldOver7d` → `Σ notional*max(0, held-7d) / (capital*windowDuration)`; ngưỡng hiệu chỉnh lại BẰNG ĐO trên run full 2021-2026. Stopgap 1 dòng: `heldTooLong > max(2, 0.02*N)` | L3, L4 | ~15 dòng + 1 lần đo |
| **P3** | `minTrades` trên OOS: từ disqualifier → sàn tuyệt đối nhỏ (10–15 lệnh) hoặc cờ low-N | TOO_FEW | nhỏ |
| **P4** | `posRatio` và `wfeMedian` dùng CÙNG tập window; hợp nhất `MAX_DD_PCT` với `PASS_MAXDD_OOS` | L5, L6 | nhỏ |
| **P5** | Env-hoá ngưỡng theo pattern `WFO_MOM15_LO/HI`. ⚠️ min-trade floor phải **extract field** trước (đang hardcode literal `:109`) | hạ tầng | nhỏ-trung bình |
| **P6** | Surface `TS_GIVEBACK_RATIO` vào RESULT_JSON (nó KHÔNG phải gene ⇒ không có provenance) | provenance | nhỏ |

**P1 là NỚI một tiêu chí đã pre-register** ⇒ bắt buộc báo cáo **song song cả 2 con số** (semantics cũ
và mới), KHÔNG thay lặng lẽ. Uni chốt semantics nào chính thức.

### Thứ tự + gate dừng

1. **P0 + P5 + P6** (rebuild 1 lần, không đổi verdict semantics).
   Gate: chạy lại nhánh A frozen N=1 13 window → `oosPnl` **bất biến**, note không xấu đi.
2. **P1 + P3** (dưới cờ env, báo cáo song song 2 semantics).
   Gate pre-register: posRatio(mới) >= 70% VÀ WFE_median(tập mới) >= 0.5 VÀ worstDdPct <= 0.50.
   **Dự đoán: 10/13 = 76.9%.** Ra khác 76.9% ⇒ có gì ngoài dự đoán, DỪNG điều tra.
3. **P2** (metric đúng + hiệu chỉnh ngưỡng bằng đo).
4. **P4**, rồi mới **N=30 confirm**. KHÔNG N=30 trước khi harness ổn định.

Bước 2 của NEXT handoff (fitness mismatch §K: chọn bằng `Calmar*factor`, chấm bằng `raw-PnL-WFE`)
**CÙNG GỐC với P1** — cả hai là "hàm chọn ≠ hàm chấm". Làm liền mạch.

## Chưa xác minh (read-only, rẻ)

- Per-window `heldTooLong` **tuyệt đối**: log `[BT ...] held>7d=` in `pctHeldOver7d`; parse
  `/home/ubuntu/claudedata/.run/stage2_branchA.log` cho số leg chính xác. Xác nhận w6 = 1 leg.
- `wfe` + `oosDdPct` per-window nhánh A — cần cho gate bước 2.
- `bestIsNote` của các run HPO N=30 cũ — xác nhận L1/L2 đã kích hoạt trong production.

## Quyết định thuộc Uni

Làm P0+P5+P6 trước hay gộp luôn P1+P3; semantics %OOS chính thức sau khi nới; commit khối
uncommitted (`SELECTOR_RANK_TOPK`/`OFFSET`, `GATE_COUNT_ONLY`, frozen-genome inject) hay không.
