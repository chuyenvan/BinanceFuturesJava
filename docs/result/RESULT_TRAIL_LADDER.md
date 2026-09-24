# RESULT_TRAIL_LADDER — gap trailing BẬC THANG theo đỉnh: **NO-GO** (NULL trên 5 rate chất lượng)

Ngày: 2026-09-23. Pre-reg: `docs/prereg/PREREG_TRAIL_LADDER.md` (**commit `f8e7333`**, chốt TRƯỚC khi chạy biến
thể; sau đó **không sửa thiết kế**). Code: **commit `a7b7725`**. Script: `research/analysis/traillad_run.py`
(đẩy 5 chân lên Kaggle) + `research/analysis/traillad_score.py` (chấm điểm). Toàn bộ sim chạy **trên Kaggle
CPU kernel** — **KHÔNG** chạy Java sim trên Oracle (`shadow-c3` vẫn `active`; Oracle chỉ **build jar**),
**KHÔNG** `claude-run`/Claude Code, **KHÔNG push**, **KHÔNG chạm HOLDOUT 2026** (dữ liệu ≤ 2025-12-31).
Trung gian `/home/ubuntu/tl_work/` + output `/home/ubuntu/kaggle_sim/out/tl-*`.

---

## 0. KẾT LUẬN (một dòng)

> **NO-GO / NULL — giữ nguyên T170.** Đổi **HÌNH DẠNG hàm gap** (trần phẳng → bậc thang lớn dần theo đỉnh)
> **KHÔNG** sinh ra rate chất lượng nào ngoài CI theo hướng tốt: **0/5 rate ở cả 3 biến thể** (và 0/5 rate
> XẤU ngoài CI). Cả 3 biến thể **PASS** rào cứng rủi ro. Riêng câu hỏi *"có bắt được sóng lớn hơn không"*:
> **CHƯA ĐỦ KẾT LUẬN** — số lệnh đạt `peak ≥ +50%` **tăng thật** (29 → 38 ở L1 / 48 ở L2) và `SumPnL` của
> nhóm đó **tăng có ý nghĩa** (block-72h: **+10 483** / **+13 630** USDT, CI không chứa 0), **nhưng** đây là
> nhóm **hậu-chọn theo đỉnh đã xảy ra** (gap lớn hơn ⇒ nhiều lệnh sống sót tới đỉnh cao hơn ⇒ nhóm đổi thành
> phần), **capture ratio theo lệnh KHÔNG tăng** (ở nhóm `≥20%` còn **giảm có ý nghĩa**: −0,053 / −0,117), và
> **tổng thể không đổi** (meanP +0,005/+0,009/−0,006; equity 111 070 → 114 756 / 109 739 / 111 230). Không
> biến thể nào đủ điều kiện áp dụng; nếu muốn theo hướng này phải mở **vòng mới** với endpoint (capture /
> PnL nhóm sóng lớn) **khai báo TRƯỚC**, không dùng kết quả hậu-chọn này để GO.

---

## 1. CỔNG BƯỚC 0 — parity của jar MỚI với cờ OFF: **PASS (byte-identical)**

| chân | jar `JAR_SHA256` (từ `result.json`) | equity | n | md5 `printDone.csv` | `[TRAIL-LADDER-CFG]` |
|---|---|---|---|---|---|
| `tl-par` (flag OFF, trace OFF — **cổng nghiêm ngặt**) | `65ae500f6b9f5232…` | 111 070 | 1089 | **`efb793e2468ca3a7318da0f0ad23d4fc`** | `on=false lo=[] gaps=[] trace=false` |
| `tl-part` (flag OFF, trace ON) | `65ae500f6b9f5232…` | 111 070 | 1089 | **`efb793e2468ca3a7318da0f0ad23d4fc`** | `on=false lo=[] gaps=[] trace=true` |
| Oracle `X1_GS_T170_2021` (tham chiếu) | — | 111 070 | 1089 | **`efb793e2468ca3a7318da0f0ad23d4fc`** | — |

- `diff tl-par/printDone.csv tl-part/printDone.csv` = **0 dòng**; md5 cả hai = md5 Oracle ⇒ **byte-identical**.
- ⇒ (a) cờ mới **default OFF ⇒ KHÔNG đổi một byte** nào của `printDone.csv` (**cổng BƯỚC 0 ĐẠT**);
  (b) file đo lường `trailTrace.csv` **trơ** với `printDone.csv` (chân `tl-part` giống hệt `tl-par`) —
  chứng minh cơ chế "file RIÊNG, không thêm cột" là đúng;
- (c) **KHÔNG có trường hợp "VÔ HIỆU"**: md5 của L1/L2/L3 (`89b3419a…` / `dd2dd161…` / `f6335d74…`) **đều
  khác** `efb793e2…` ⇒ cờ `TS_LADDER` **bind thật** trong đường sim.
- `n_trades` = 1089 ở cả 2 chân parity; `symbol_mapper=863` (≥ guard 800) cả 5 chân.

## 2. Commit

| commit | nội dung |
|---|---|
| `f8e7333` | **PREREG_TRAIL_LADDER** (chốt TRƯỚC khi chạy mọi biến thể) |
| `a7b7725` | Cơ chế gap bậc thang (`Configs` + `TradeUtils` + `OrderTargetInfoTest`) + trace đo lường (`TraceOrderDone.printTrailTrace` + gọi ở `Simulator`) + 3 profile `x1_tl_l1/l2/l3` + `traillad_run.py` + `traillad_score.py` + `TrailLadderTest` (**151/151 test PASS** — 146 cũ + **5 mới**) |

## 3. Cơ chế đã thêm (đúng như pre-reg §3)

- `Configs`: `TS_LADDER` (công tắc) + `TS_LADDER_LO[]` + `TS_LADDER_GAPS[]` (2 mảng, đọc qua `Cfg`);
  `validateLadder()` **fail-fast `exit 2`** nếu lệch độ dài / `LO` không tăng / `GAPS ≤ 0` (không âm thầm
  rơi về default). Log khởi động: `[CFG] TS_LADDER ON lo=[…] gaps=[…]` (xác nhận trên **cả 3** chân: L1
  `[0.0,0.1,0.25,0.5,1.0]/[0.04,0.08,0.15,0.25,0.35]`, L2 `…/[0.04,0.1,0.2,0.35,0.5]`,
  L3 `[0.5,1.0]/[0.25,0.4]`).
- `TradeUtils.trailFromLadder`: `gap = GAPS[i]` (chỉ số **cuối cùng** có `peak ≥ LO[i]`); dưới `LO[0]` ⇒
  **công thức CŨ** `trailFromCap` (L3 mới dùng nhánh này); `gap ← min(gap, peak×0.9)` ⇒ **BẤT BIẾN
  "SL luôn trên entry"** giữ nguyên; làm tròn bước `0.005` **giống hệt** đường cũ.
- 🔴 **KHÔNG là gene HPO — và đó là CHỦ Ý** (ghi rõ theo yêu cầu brief): `StrategyWfoTask` áp gene bằng
  **reflection lên field SCALAR** của `Configs` (`Field.setFloat/setInt`); `TS_LADDER_LO`/`TS_LADDER_GAPS`
  là **`float[]`** nên reflection **không chạm tới được** ⇒ **mảng KHÔNG được HPO điều khiển** (cùng tiền lệ
  `DCA_GRID_LEVELS`/`DCA_GRID_WEIGHTS`, `Configs.java:208`). Vòng này **không chạy HPO**, không tune sau khi
  thấy số. `TrailLadderTest` chốt lại 3 bảng L1/L2/L3 + bất biến `rate > 0` trên lưới đỉnh 7%..300%.
- Đo lường (`SIM_TRAIL_TRACE`, default OFF): file **RIÊNG** `storage/trailTrace.csv` = `printDone` rút gọn
  **+ cột `peak` = `maePeak`** (đỉnh thật của cụm từ leg đầu). **KHÔNG thêm cột vào `printDone.csv`** (tiền lệ
  `PREARM_SL` X2 / `SELRANK` X3).

## 4. Bảng chính — 5 rate chất lượng (toàn bộ leg) + CI **HAI độ rộng**

`k = 3` ⇒ nở rộng chuẩn hoá `inflate(3) = 1,482304` (**chặt hơn**); brief yêu cầu `x1.21` (**rộng hơn**).
Bootstrap block-72h, **2000 rep, seed `20260905`**, mốc neo block **cố định 2021-07-01**. "Ngoài CI" chỉ
được tính khi ngoài ở **CẢ HAI** độ rộng.

| tag | n | win% | TSloss% | mP\|SM | mP\|SL | meanP |
|---|---:|---:|---:|---:|---:|---:|
| `tl-par` (= T170, tham chiếu) | 1089 | 88,25 | 9,73 | 7,642 | −16,992 | 5,244 |
| `tl-part` (đối chứng nội bộ: flag OFF + trace ON) | 1089 | 88,25 | 9,73 | 7,642 | −16,992 | 5,244 |
| **L1** thang nhẹ | 1086 | 88,21 | 9,58 | 7,621 | −17,149 | 5,249 |
| **L2** thang dốc | 1087 | 88,50 | 9,48 | 7,600 | −17,179 | 5,252 |
| **L3** chỉ nới ở vùng lãi lớn | 1089 | 88,25 | 9,73 | 7,635 | −16,992 | 5,238 |

Hiệu (biến thể − T170) + CI:

| tag | rate | hiệu | CI @1,21 | CI @1,482304 | ngoài CI | hướng |
|---|---|---:|---|---|---|---|
| `tl-part` | **cả 5 rate** | **0,000** | `[0,000; 0,000]` | `[0,000; 0,000]` | – | **(đối chứng: hai chân byte-identical ⇒ hiệu đúng bằng 0 — kiểm chứng máy chấm)** |
| L1 | win% | −0,032 | [−0,951; +0,969] | [−1,167; +1,186] | – | |
| L1 | TSloss% | −0,157 | [−0,942; +0,474] | [−1,101; +0,633] | – | |
| L1 | mP\|SM | −0,021 | [−0,360; +0,405] | [−0,446; +0,492] | – | |
| L1 | mP\|SL | −0,157 | [−0,492; +0,071] | [−0,555; +0,134] | – | |
| L1 | meanP | +0,005 | [−0,336; +0,398] | [−0,419; +0,480] | – | |
| L2 | win% | +0,254 | [−0,598; +1,273] | [−0,809; +1,483] | – | |
| L2 | TSloss% | −0,258 | [−1,161; +0,448] | [−1,342; +0,629] | – | |
| L2 | mP\|SM | −0,041 | [−0,548; +0,421] | [−0,657; +0,530] | – | |
| L2 | mP\|SL | −0,187 | [−0,552; +0,075] | [−0,622; +0,146] | – | |
| L2 | meanP | +0,009 | [−0,410; +0,374] | [−0,498; +0,463] | – | |
| L3 | win% | 0,000 | [0,000; 0,000] | [0,000; 0,000] | – | |
| L3 | TSloss% | 0,000 | [0,000; 0,000] | [0,000; 0,000] | – | |
| L3 | mP\|SM | −0,007 | [−0,077; +0,047] | [−0,091; +0,061] | – | |
| L3 | mP\|SL | 0,000 | [0,000; 0,000] | [0,000; 0,000] | – | |
| L3 | meanP | −0,006 | [−0,069; +0,042] | [−0,082; +0,055] | – | |

⇒ **0/5 rate ngoài CI (tốt) và 0/5 rate XẤU ngoài CI** ở **cả 3** biến thể. L3 yếu nhất về tác động
(win%/TSloss%/mP|SL **không đổi một chút** — cơ chế chỉ chạm đỉnh ≥ 50%, mà T170 chỉ có 29/1089 leg
(2,7%) từng đạt mức đó, nên ảnh hưởng tổng thể gần như bằng 0 — **đúng như cơ chế dự đoán**, không phải
"vô hiệu": md5 L3 **khác** T170).

## 5. Ràng buộc CỨNG (`docs/runbooks/RISK_APPETITE.md`) — **PASS cả 3 biến thể**

| tag | equity cuối | CAGR% | maxDD% | UW ngày | quý xấu nhất | năm âm | tập trung 1 coin | PASS |
|---|---:|---:|---:|---:|---:|---|---:|---|
| `tl-par` / `tl-part` | 111 070 | 29,27 | −11,84 | 92 | −0,92 | không | 9,77% | ✔ |
| **L1** | 114 756 | 30,21 | −12,03 | 119 | −1,37 | không | 9,79% | ✔ |
| **L2** | 109 739 | 28,92 | −9,31 | **164** | −2,07 | không | 7,23% | ✔ (UW sát trần 200) |
| **L3** | 111 230 | 29,31 | −11,84 | 88 | −0,65 | không | 9,77% | ✔ |

Theo năm (maxDD% / UW / return%):

| năm | T170 | L1 | L2 | L3 |
|---|---|---|---|---|
| 2021 | −2,46 / 37 / +12,21 | −2,45 / 37 / +11,79 | −2,45 / 38 / +11,70 | −2,46 / 37 / +12,21 |
| 2022 | −11,84 / 72 / +19,58 | −12,03 / 73 / +22,61 | −9,31 / 73 / +22,02 | −11,84 / 72 / +19,58 |
| 2023 | −2,73 / 63 / +34,96 | −2,75 / 62 / +38,17 | −3,47 / 86 / +34,97 | −2,73 / 63 / +34,43 |
| 2024 | −6,60 / 92 / +32,14 | −6,72 / 119 / +30,48 | −6,72 / 119 / +27,30 | −6,60 / 88 / +32,47 |
| 2025 | −4,23 / 52 / +32,71 | −4,33 / 52 / +32,77 | −3,97 / **164** / +33,96 | −4,23 / 52 / +33,09 |

Không năm nào âm; maxDD mọi năm ≤ 12,03% (trần 30%); tập trung ≤ 9,79% (trần 15%).

## 6. 🎯 "BẮT SÓNG LỚN" — mục đích của thay đổi (pre-reg §3.2)

Nhóm = leg có `peak = (maePeak−entry)/entry ≥ 20% / 50% / 100%` (từ `trailTrace.csv`; baseline = `tl-part`
vì `printDone` giống hệt `tl-par`). `%trailing` = tỉ lệ thoát bằng **trailing** (`STOP_MARKET_DONE`);
`med_gap_pp` = khoảng cách **còn cách đỉnh** lúc thoát (điểm phần trăm).

**peak ≥ +20%**

| tag | n (/% tổng) | %trailing | med_gap_pp | mean_gap_pp | med_capture | mean_capture | SumPnL (USDT) |
|---|---:|---:|---:|---:|---:|---:|---:|
| T170 | 123 (11,3%) | 98,4 | 8,14 | 31,70 | **0,662** | **0,596** | 51 997 |
| L1 | **146** (13,4%) | 98,6 | 14,89 | 32,36 | 0,624 | 0,544 | **64 331** |
| L2 | **166** (15,3%) | 98,8 | 19,69 | 31,70 | 0,537 | 0,479 | **64 223** |
| L3 | 123 (11,3%) | 98,4 | 8,15 | 32,76 | 0,662 | 0,588 | 52 210 |

**peak ≥ +50%**

| tag | n (/% tổng) | %trailing | med_gap_pp | mean_gap_pp | med_capture | mean_capture | SumPnL |
|---|---:|---:|---:|---:|---:|---:|---:|
| T170 | 29 (2,7%) | 93,1 | 64,70 | 103,64 | 0,406 | 0,420 | 23 049 |
| L1 | **38** (3,5%) | 94,7 | 48,46 | 88,83 | 0,574 | 0,435 | **33 532** |
| L2 | **48** (4,4%) | 95,8 | 39,08 | 72,05 | 0,537 | 0,448 | **36 679** |
| L3 | 29 (2,7%) | 93,1 | 64,70 | 108,11 | 0,406 | 0,385 | 23 307 |

**peak ≥ +100%**

| tag | n | %trailing | med_gap_pp | mean_gap_pp | med_capture | mean_capture | SumPnL |
|---|---:|---:|---:|---:|---:|---:|---:|
| T170 | 21 | 90,5 | 112,34 | 135,83 | 0,262 | 0,308 | 15 906 |
| L1 | 23 | 91,3 | 103,40 | 128,11 | 0,326 | 0,335 | 19 155 |
| L2 | 23 | 91,3 | **79,31** | 114,13 | **0,441** | 0,374 | 19 637 |
| L3 | 22 | 90,9 | 107,87 | 133,16 | 0,309 | 0,319 | 17 655 |

**[POST-HOC — KHÔNG phải tiêu chí pre-reg] CI block-72h (inflate(3)=1,482304) cho nhóm sóng lớn**
(`d = biến thể − T170`; `*` = CI không chứa 0; nhóm **chọn theo đỉnh đã xảy ra ⇒ có post-selection**):

| nhóm | tag | n_var / n_base | `d_capture` | `d_SumPnL` |
|---|---|---:|---|---|
| ≥20% | L1 | 146 / 123 | **−0,053 [−0,103; −0,011] \*** | **+12 333 [+2 475; +23 280] \*** |
| ≥20% | L2 | 166 / 123 | **−0,117 [−0,199; −0,047] \*** | +12 226 [−803; +26 507] |
| ≥20% | L3 | 123 / 123 | −0,008 [−0,029; +0,005] | +212 [−884; +1 449] |
| ≥50% | L1 | 38 / 29 | +0,014 [−0,155; +0,168] | **+10 483 [+1 315; +21 317] \*** |
| ≥50% | L2 | 48 / 29 | +0,028 [−0,239; +0,222] | **+13 630 [+1 677; +27 207] \*** |
| ≥50% | L3 | 29 / 29 | −0,035 [−0,135; +0,022] | +258 [−848; +1 498] |
| ≥100% | L1 | 23 / 21 | +0,027 [−0,036; +0,142] | +3 249 [−2 450; +9 962] |
| ≥100% | L2 | 23 / 21 | +0,066 [−0,026; +0,191] | +3 731 [−2 129; +9 817] |
| ≥100% | L3 | 22 / 21 | +0,011 [−0,009; +0,047] | +1 748 [−1 311; +6 556] |

**Đọc bảng này cho đúng (3 điều):**

1. **Gap lớn hơn ⇒ ít bị "trượt sóng" hơn: CÓ, đo được.** Số lệnh sống tới `peak ≥ 50%` tăng
   **29 → 38 (L1) / 48 (L2)**; `SumPnL` của nhóm đó **tăng có ý nghĩa thống kê** (+10,5k / +13,6k USDT);
   khoảng cách **còn cách đỉnh lúc thoát** giảm rõ (median 64,7 → 48,5 / **39,1** điểm %; nhóm ≥100%:
   112,3 → 79,3). Đây đúng là hướng owner muốn.
2. **NHƯNG `capture ratio` theo lệnh KHÔNG tăng — và ở nhóm `≥20%` còn GIẢM có ý nghĩa** (−0,053 / −0,117):
   gap lớn hơn ⇒ nhả lại nhiều hơn từ đỉnh ⇒ tỉ lệ `exit/peak` **giảm** một cách **cơ học**. Đó là lý do
   "capture ratio" **không** được dùng làm tiêu chí GO.
3. **Nhóm là HẬU-CHỌN theo đỉnh đã xảy ra** ⇒ "n tăng" **không** phải bằng chứng độc lập: chính vì gap lớn
   hơn nên lệnh dễ sống sót tới đỉnh cao hơn (đúng cơ chế) — nhưng nó cũng nói lên rằng **phần lợi nằm ở
   nhóm sóng lớn** trong khi **phần còn lại nhả bớt**: L1 tổng +3 687 USDT nhưng nhóm ≥20% +12 333 ⇒ **các
   lệnh không sóng lớn mất ~8,6k**; L2 tổng **−1 330** trong khi nhóm ≥20% +12 226 ⇒ phần còn lại mất ~13,6k.
   ⇒ **tái phân phối**, không phải cải thiện tổng thể.

## 7. PnL / EQUITY — báo riêng (KHÔNG dùng để chọn)

| tag | equity cuối | Δ vs T170 | SumPnL toàn bộ | PnL/leg | meanP |
|---|---:|---:|---:|---:|---:|
| T170 | 111 070 | — | 76 070 | 69,85 | 5,244 |
| L1 | 114 756 | **+3,3%** | 79 757 | 73,44 | 5,249 |
| L2 | 109 739 | **−1,2%** | 74 740 | 68,76 | 5,252 |
| L3 | 111 230 | **+0,1%** | 76 230 | 70,09 | 5,238 |

Theo level (n / SumPnL / meanP):

| tag | `PREDICT_SYMBOL_TRADE` | `BIG_DOWN` | `DCA_LEVEL1` |
|---|---|---|---|
| T170 | 821 / 47 114,5 / 4,221 | 248 / 16 254,4 / 4,786 | 20 / 12 701,3 / 52,888 |
| L1 | 818 / 47 893,4 / 4,189 | 248 / **19 309,1** / 5,111 | 20 / 12 554,4 / 50,301 |
| L2 | 820 / 44 115,7 / 4,126 | 248 / **17 535,5** / 5,024 | 19 / 13 088,6 / 56,835 |
| L3 | 821 / 47 315,3 / 4,214 | 248 / 16 223,4 / 4,786 | 20 / 12 691,5 / 52,888 |

Không chọn biến thể theo equity (luật cứng #3 `AGENT_RUNBOOK`; bài học `RESULT_SEL_BIGDOWN`: `DROP`
+28% equity mà 0/3 rate ngoài CI ⇒ NULL).

## 8. Kết luận theo luật pre-reg §5

| biến thể | rate ngoài CI hướng TỐT | rate XẤU ngoài CI | ràng buộc cứng | verdict |
|---|---:|---:|---|---|
| L1 "thang nhẹ" | **0/5** | 0/5 | PASS | **NULL** |
| L2 "thang dốc" | **0/5** | 0/5 | PASS (UW 164 sát trần) | **NULL** |
| L3 "chỉ nới vùng lãi lớn" | **0/5** | 0/5 | PASS | **NULL** |

- Không biến thể nào đạt **≥2 rate ngoài CI cùng hướng tốt** ⇒ **NO-GO**.
- Không có biến thể **đơn lẻ** nào đạt ⇒ **không phải UNCONFIRMED**, mà là **bác bỏ** theo cả 3 cách chia bậc.
- Không rate nào **XẤU** ngoài CI ⇒ **không phải THUA**; đây là "đổi hình dạng hàm **không làm gì** ở mức
  tổng thể" — khớp dự đoán §6 pre-reg.
- Câu hỏi riêng *"bắt sóng lớn"*: **CHƯA ĐỦ KẾT LUẬN** (đúng như pre-reg §5 bullet 1 dự liệu) — có dịch
  chuyển **thật** về phân bố (n nhóm ≥50%, SumPnL nhóm) nhưng đó là **hậu-chọn**, capture/lệnh **không** tăng,
  tổng thể **không** đổi. Muốn kết luận phải mở vòng mới với endpoint khai báo trước (ví dụ: PnL của cụm
  *đã* vượt +X% trong lúc mở, đo **tại thời điểm vượt**, không chọn theo đỉnh cuối cùng).
- Không tune sau khi thấy số. Không áp dụng biến thể nào; **giữ nguyên T170**.

## 9. Tài nguyên Kaggle đã dùng (chi phí 0 — CPU kernel không tính quota)

| chân | tag kernel | profile | JVM (s) | kết thúc (giờ VN) |
|---|---|---|---:|---|
| cổng parity (flag OFF, trace OFF) | `chuyendinh/sim-tl-par` | `x1_gs_t170` | 1356,3 | 16:45:32 |
| đối chứng nội bộ (flag OFF, trace ON) | `chuyendinh/sim-tl-part` | `x1_gs_t170` | 1198,1 | 16:42:08 |
| V1 | `chuyendinh/sim-tl-l1` | `x1_tl_l1` | 1230,3 | 16:43:06 |
| V2 | `chuyendinh/sim-tl-l2` | `x1_tl_l2` | 1197,6 | 16:42:08 |
| V3 | `chuyendinh/sim-tl-l3` | `x1_tl_l3` | 1352,6 | 16:45:26 |
| **tổng** | **5 chân, CHẠY SONG SONG 5/5 slot** | — | — | **~26 phút wall** (push 16:21 → fetch 16:46:51) |

- 🔎 **Đo được lần đầu: 5/5 kernel chạy đồng thời trên bundle 5,3 GB KHÔNG vỡ trần** (`docs/runbooks/KAGGLE_SIM_48M.md`
  §7 để ngỏ) — cả 5 `RUNNING` cùng lúc, tất cả `COMPLETE`, JVM 1198-1356 s (không chậm hơn đáng kể so với
  chạy đơn 1217 s của tiền lệ).
- Dataset MỚI: `chuyendinh/sim-jar-trailladder` (95 MB: `sim.jar` + `prof_x1_tl_l1/l2/l3.properties`) —
  dùng tham số `jar_ds` để đổi CODE **không** phải tạo lại bundle 5,3 GB. Kernel in `JAR_SHA256=` và ghi vào
  `result.json`: cả 5 chân **cùng một jar** `65ae500f6b9f5232…` (không có chuyện dùng nhầm jar cũ âm thầm).
- 5 slot dùng 5 → account còn 0 slot trong lúc chạy (đã xong, đã giải phóng).

## 10. File liên quan + vệ sinh

- `docs/prereg/PREREG_TRAIL_LADDER.md` (`f8e7333`), `docs/result/RESULT_TRAIL_LADDER.md` (file này),
  `research/analysis/traillad_run.py`, `research/analysis/traillad_score.py`,
  `src/.../TrailLadderTest.java`, `profiles/x1_tl_l{1,2,3}.properties`,
  `tools/kaggle_sim.py` (không sửa — dùng `jar_ds`/`bundle_ds` đã có).
- Bằng chứng số: `/home/ubuntu/kaggle_sim/out/{tl-par,tl-part,tl-l1,tl-l2,tl-l3}/`
  (`printDone.csv`, `trailTrace.csv`, `sim.out`, `result.json`) + `/home/ubuntu/tl_work/score.txt`,
  `score_all.json`, `build.log` — **giữ lại**.
- Thư mục stage jar (để tạo version dataset sau này): `/home/ubuntu/trladder_jar/` (hardlink `sim.jar`).
- **Không** đụng `shadow-c3` (vẫn `active`), **không** systemctl/kill, **không push**, **không** ssh 242.
- Cờ `TS_LADDER` + `SIM_TRAIL_TRACE` để lại trong code (**default OFF** = byte-identical) làm công cụ cho
  vòng sau; **không** bật ở đâu trong config chạy thật.
