# PREREG_SHORT_FULLCHAIN — SHORT: GHÉP 3 TẦNG THEO TỪNG BƯỚC (S1 selector → GATE → SIM)

Chốt: **2026-10-01**, branch `module`, repo `/home/ubuntu/src/BinanceFuturesJava`.
File này commit **TRƯỚC** mọi commit script/kết quả của vòng này (đúng
`docs/runbooks/AGENT_RUNBOOK.md` luật 2; sai thứ tự commit ⇒ kết quả **VOID**).
Sau khi chạy **KHÔNG sửa thiết kế** (pick, gate, cơ chế thoát, chi phí, chỉ số, lưới, luật kết luận).

Trạng thái: **ĐANG CHỜ ĐO**.

Nền: `RESULT_SHORT_FEASIBILITY` (`9c570e6f`) · `RESULT_SHORT_PATHEXIT` (`c4d56074`) ·
`RESULT_SHORT_PATHEXIT_PSOFT` (`05169026`).

---

## 0. QUAN HỆ VỚI CÁC VÒNG TRƯỚC (owner: "đi TỪNG BƯỚC, đi lẻ không ra kết quả")

Mọi vòng trước **đo LẺ từng tầng**: `RESULT_SHORT_FEASIBILITY` đo **đảo-gate 0-sim**;
`RESULT_SHORT_PATHEXIT`/`_PSOFT` đo **nhãn path-aware nhưng KHÔNG có gate, và lưới thoát thiếu
TRAILING** (chỉ TP/SL/time-stop). Vòng này **ghép ĐÚNG 3 tầng theo bước** trên **cùng một hệ**:

1. **S1 selector** (0-sim) → chốt "selector OK".
2. **+ GATE `predRisk4H`** (0-sim) → đo **2 hướng** (CHẶN / THUẬN).
3. **+ SIM đường giá 1m thật (first-hit)** với **TRAILING + SL CỨNG + time-stop** (lưới khoá).

---

## 1. RÀNG BUỘC (CỨNG)

1. **Train CHỈ trên KAGGLE**; phần đường giá = **Python offline stream Aerospike `kline_1m_opt`**;
   **KHÔNG chạy Java / engine-sim trên Oracle**; Kaggle bận ⇒ DỪNG + báo rõ (dùng `kaggle kernels
   status`, KHÔNG tin "0/5 slot" của CLI 1.6.17). (Vòng này **không cần train mới** — tái dùng
   selector S1 đã có ⇒ 0 kernel Kaggle; ghi rõ.)
2. KHÔNG chạm production / 242 / ONNX / LIVE / 2026. **KHÔNG sửa `.java`**.
3. KHÔNG push file dữ liệu (panel/bins/1m); chỉ push `.md` / `.py` / `.json` tổng hợp.
4. **DEV ≤ 2025-12-31** (cắt mọi `ts + 72h ≤ 2025-12-31T00:00Z`, seal 2026).
5. Disk `/` ~83 % ⇒ **stream** (KHÔNG dump 1m ra đĩa); output tool nhỏ; commit sớm + push.
6. **CHỈ `git add <file CỦA MÌNH>`**, TUYỆT ĐỐI KHÔNG `git add .`/`-A` (working tree có file của job khác).

---

## 2. (BƯỚC 1) SELECTOR S1 — định nghĩa + tiêu chí "OK"

- Nguồn: `/home/ubuntu/ledger/pred_s1a2x1.parquet` (6 573 909 dòng `(ts, sym, score)`, ts lưới **15m UTC**,
  17 349 tick, 620 sym, 2022-01-01 → 2025-12-31). `score` **THẤP = TỐT (cho long)**.
- Quy ước khóa: **`s1 = −score`**; **ứng viên SHORT = decile 0 của `s1`** mỗi tick
  (= `score` CAO nhất ≈ 10 % "tệ nhất" theo S1). Song song báo **K=8** (8 score cao nhất/tick) làm mốc
  "chọn lọc gắt" đối chiếu.
- Đo **rank-IC**: `Spearman(s1, ret_h)` cross-section mỗi snapshot, h ∈ {1h, 4h, 24h}; forward return
  tính từ `/home/ubuntu/java/fsrun/CLOSES_1H.bin` (`ctime = open+1h`, causal), **tổng** + **theo năm
  2022–2025** + **CI block-72h** (NREP=2000, SEED=20260905, `inflate ×1,21`).
- Đo **bảng decile** 0..9 (mean `ret_h` / horizon) + d0 theo năm.
- **Tiêu chí "selector OK" (khóa):** tồn tại decile SHORT (d0) có `mean ret_24h < 0` **và** cùng **dấu âm
  ở ≥ 3/4 năm** **và** |`mean ret_24h`| **> ngưỡng chi phí `0,2098 %`** (fee_rt+slip_rt).
  (Chỉ **xác nhận chất lượng xếp hạng**; KHÔNG tự là GO.)
- **0-sim**, script `research/analysis/short_fullchain_s1.py` → `research/analysis/out/short_fullchain_s1.json`.

## 3. (BƯỚC 2) GHEP GATE `predRisk4H` — 2 HƯỚNG

- Gate = `predRisk4H` từ `research/parity/data/p15_dev.csv` (**market-level, 1 giá trị/phút**,
  2 500 260 dòng, 2021-03-31 → 2025-12-31). Đọc tại **phút quyết định = `ts_15m//60000 + 14`** (causal;
  trùng phút vào lệnh ở bước 3). ⚠️ **Caveat giữ nguyên:** cột `predRisk4H` này từ set **CŨ**, tài liệu
  `RESULT_PREDBIN_REPRO` §… ghi **KHÔNG leak-free** ⇒ vùng < 2025-12 **in-sample lạc quan**; ghi rõ khi đọc.
- Ngưỡng khóa (theo phân vị **trên DEV**, tính 1 lần): **`q10`**, **`q20`**, **`q80`**, **`q90`** của `predRisk4H`.
  `risk CAO ⇔ predRisk4H thấp` (âm hơn = drawdown dự báo lớn hơn); `risk THẤP ⇔ predRisk4H cao`.
- **2 hướng (khóa):**
  - **(a) gate CHẶN:** bỏ lệnh khi gate báo "risk cao" (`g ≤ q10`, phụ `q20`).
  - **(b) gate THUẬN:** chỉ vào khi gate báo "risk thấp" (`g ≥ q90`, phụ `q80`).
  - (phụ, khám phá) **(c) gate NGHỊCH:** chỉ vào khi "risk cao" (`g ≤ q10`) — đối chứng dấu.
- Đo cho mỗi hướng: **n** (số pick) · tỷ lệ bị chặn/giữ · **rank-IC(s1, ret24)** trong tập giữ ·
  **mean `ret_24h` của d0** trong tập giữ · **theo năm**.
- **0-sim**, script `research/analysis/short_fullchain_gate.py` → `…/out/short_fullchain_gate.json`.

## 4. (BƯỚC 3) SIM SHORT — ĐƯỜNG GIÁ 1m (first-hit THẬT) + TRAILING + SL CỨNG

### 4.1 Pick
S1 panel, **ứng viên SHORT = decile 0** mỗi tick (như §2). Mô phỏng **TOÀN BỘ pick decile 0** (để cắt
theo gate SAU, 1 lượt stream).

### 4.2 Đường giá (nguồn + offset khóa)
Aerospike `test.kline_1m_opt` (127.0.0.1:3222), key `YYYYMMDD-HHMM` (TZ+7), protobuf+snappy.
- Giá vào = **close nến 1m tại `m0+14`** với `m0 = ts_15m` (open nến 15m) — **khớp TUYỆT ĐỐI `close(t)` của
  `.pb`** (đã kiểm `mae=0` ở `RESULT_SHORT_PATHEXIT` §1). Path = nến `m0+15 .. m0+14+h`.
- **Stream 1 lượt, buffer trượt 72h, KHÔNG ghi đĩa.** (Cross-check lại `.pb` trên chính pick đã mô phỏng.)

### 4.3 Cơ chế thoát (KHÓA) — lưới **TRAILING × SL × time-stop**
Vào short tại `P`. Đơn vị %, pnl short = `−(price/P − 1)` trừ phí/funding.
- **SL CỨNG** `SL`: khi `high ≥ P·(1+SL)` (nến đầu) ⇒ `pnl = −SL`.
- **TRAILING** `T`: theo dõi **đáy-lợi** `runmin = min(low)`; level `= runmin·(1+T)`; khi `high ≥ level`
  ⇒ `pnl = −(level/P − 1)`.
- **Time-stop** `TS`: nếu chưa chạm ⇒ đóng tại `close(m0+14+TS)` ⇒ `pnl = −(close/P − 1)`.
- **Thứ tự trong 1 nến (khóa):** nếu cùng nến chạm **cả SL lẫn TRAIL** ⇒ **ưu tiên SL** (bảo thủ).
- **Lưới (KHÓA):** `T ∈ {3 %, 5 %, 8 %}` × `SL ∈ {10 %, 15 %, 20 %}` × `TS ∈ {24h, 72h}` = **18 tổ hợp**.

### 4.4 Chi phí (khóa)
- Base **0,112 %/vòng**; stress **0,150 %** (báo phụ).
- Funding: short **TRẢ** `−0,585 %/72h`; **pro-rata theo thời gian giữ** (`−0,585·(hours/72)`).

### 4.5 Chấm + CI (khóa)
Trên OOS 2022-01..2025-12-31, mean per-tick (decile 0):
**n · net% · winrate · giữ (h) · `p01`/`max_loss` · theo năm · CI block-72h** (NREP=2000, SEED=20260905,
ngoài-CI = ngoài **raw VÀ ×1,21**). Mỗi tổ hợp báo cho **3 nhánh**: **(A) không gate**, **(B) gate CHẶN
(q10)**, **(C) gate THUẬN (q90)**.
**§9** (`docs/runbooks/RISK_APPETITE.md` §9, dùng lại `research/analysis/reset_rule_score.py` cho tầng
rủi ro/độ bền khi dựng được đường equity từ legs): báo T1 (maxDD/UW/quý/0-năm-âm/conc) · T2 (`q*`,
top-1 %) · T3 (non-inferior vs nhánh A) · T4 (n mục tiêu) — **tầng nào không dựng được thì ghi "N/A +
lý do", KHÔNG bịa**.

### 4.6 Luật kết luận (KHÓA TRƯỚC)
**GO** (đáng dựng đường SELL) chỉ khi tồn tại tổ hợp trong lưới §4.3, **ở một nhánh gate**, đạt **cả**:

| # | Điều kiện (khóa) |
|---|---|
| **A** | net(decile0) **> 0** đã credit funding pro-rata, **ngoài CI** (raw **và** ×1,21), mean |
| **B** | net > 0 ở **≥ 3/4 năm** (2022–2025) |

Cộng báo cáo §9. **NO-GO** nếu A **hoặc** B FAIL. Bắt buộc báo phụ trợ:
(i) **gate có làm short > 0 & ngoài CI không**; (ii) **2023 còn âm không**; (iii) **số tổ hợp đạt GO**
(> 1 "vùng đẹp" ⇒ ít overfit, = 1 ⇒ cảnh báo overfit); (iv) **nguyên nhân THẬT** nếu NO-GO.

## 5. VIỆC **BỎ** + lý do (ghi TRƯỚC)

| # | việc | trạng thái | lý do |
|---|---|---|---|
| 1 | Train lại selector/gate (kernel Kaggle) | ⛔ BỎ | S1 panel + gate pred ĐÃ CÓ; không cần train mới ⇒ 0 kernel |
| 2 | Horizon 48h | ⛔ BỎ | ngoài lưới khóa (24/72h) |
| 3 | Java engine-sim / ONNX / production / 242 / LIVE | ⛔ BỎ | §1.2 |
| 4 | Push panel/bins/1m | ⛔ BỎ | §1.3 |
| 5 | Sửa `.java` | ⛔ BỎ | §1.2 |
| 6 | Liquidation/tick trong nến | ⛔ BỎ | chỉ có OHLC 1m (không biết thứ tự trong nến ⇒ quy ước ưu tiên SL) |
| 7 | Short trên toàn bộ 620 sym (không xếp hạng) | ⛔ BỎ | câu hỏi là S1-selector decile 0 |

## 6. Sản phẩm

| File | Nội dung |
|---|---|
| `docs/prereg/PREREG_SHORT_FULLCHAIN.md` | file này (commit TRƯỚC đo) |
| `research/analysis/short_fullchain_s1.py` | bước 1 (selector IC/decile) |
| `research/analysis/short_fullchain_gate.py` | bước 2 (gate 2 hướng) |
| `research/analysis/short_fullchain_sim.py` | bước 3 (sim 1m trailing+SL) |
| `docs/result/RESULT_SHORT_FULLCHAIN.md` (+`.json`) | kết quả + trả lời 4 câu |
