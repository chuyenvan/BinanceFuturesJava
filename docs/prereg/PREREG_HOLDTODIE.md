# PREREG_HOLDTODIE — TẮT time-stop 168h ("hold to die") trên nền `G2 + FLAT3`: có MỞ THÊM entry không?

**Chốt TRƯỚC khi có số.** Ngày: **2026-09-30** (TASK HoldToDie). Nhánh `module`, HEAD `da56927a`.
Nguồn: owner 2026-09-30 — *"tìm cách mở rộng tiếp entry … trước khi có dòng lệnh cũng sau 168h thử OFF nó hold-to-die xem kết quả … vẫn giữ dca 1;1;1;1, qua 4 leg rồi thì ko vào thêm nữa để nó tự trôi"*.
Luật chấm: `docs/runbooks/RISK_APPETITE.md` §9. Nền: `profiles/g2_flat3.properties` + `docs/result/RESULT_GDV2_P3.md` + `docs/decisions/0013-giu-g2-chuyen-ofi.md`.

> **KHÔNG thêm/bớt arm, KHÔNG đổi LUẬT KẾT LUẬN sau khi thấy số.** Lệch dự báo ⇒ chỉ BÁO lệch.

---

## 0. MỤC ĐÍCH (1 câu)

Trên nền **`G2 + FLAT3`** giữ nguyên mọi thứ (rolling gate G2 · FLAT3 exit · KEEPLEG0 DCA `1,1,1,1` scale 6.0 · `SIM_F_BASE=0.015` · `SELECTOR_RANK_TOPK=16` · nhịp 1' · `CONC_CAP 15 %` · phí base 0,112 %/vòng),
**TẮT `SIM_LOSER_TIME_STOP_HOURS` (168h → 0)** — tức "vào lệnh xong thì KHÔNG bị đóng cứng sau 168h, để nó tự trôi" —
và đo **dứt khoát**: (1) có **mở thêm entry** không (Δn); (2) **chất lượng (T3) + rủi ro (UW, ddPhút)** thay đổi bao nhiêu, có **vỡ trần `UW ≤ 250`** hay **trần maxDD MTM 40 %/năm** không; (3) **vì sao `n` đổi** (time-stop có đang "giữ slot" chặn entry không); (4) H1 có **qua 4 tầng §9** ⇒ đáng giữ, hay **NULL**.

## 1. NỀN CHUNG + RÀNG BUỘC CỨNG

- Nền: `profiles/g2_flat3.properties` = `r4_kg0_k16_f015_g155` + **GDV2 rolling gate ratio W90** `PCT 0.999950829`
  + **FLAT3 exit** (`TS_GIVEBACK_RATIO=1.0`, `SIM_TS_MAX_GAP=0.03`, `WEAK=0.03`; giữ `SIM_RATE_PROFIT_STOP_MARKET=0.07`).
  **KHÔNG mở gate** (`SIM_GATE_DYN_SCALE`/`PCT`/window giữ y G2). **KHÔNG** đổi `DCA_GRID_WEIGHTS=1,1,1,1`, `DCA_GRID_SCALE=6.0`, K, size.
- **Hết 4 leg DCA thì KHÔNG vào thêm** — đúng lưới 4 leg, KHÔNG thêm level (xác nhận rõ trong arm).
- Sim chạy **TRÊN KAGGLE** (0 sim Oracle). Bundle `sim-x1-2021-bundle`, **jar DÙNG LẠI `sim-jar-gdv2`**
  (sha256 `7368be46edb3fa387a41585bea18feb81ab812ebabdc9ff245f6d25947a82d6a`) — **KHÔNG build lại, KHÔNG merge**.
  `sim_end_date=20251231`. **Kaggle không chạy được ⇒ DỪNG + báo RÕ.**
- **DEV ≤ 2025-12-31** (không đọc/không dùng 2026). **KHÔNG** chạm production/242/ONNX/LIVE. **KHÔNG push file dữ liệu**.

## 2. CÁCH TẮT time-stop (đọc CODE, `file:line`)

- Key: `SIM_LOSER_TIME_STOP_HOURS` → `Configs.LOSER_TIME_STOP_HOURS` (parse: `src/main/java/com/binance/chuyennd/tradecore/Configs.java:903`;
  default `0`: `Configs.java:481`).
- Áp dụng: `src/main/java/com/binance/chuyennd/research/SimulatorMarketLevelTicker1MStopLoss.java:1020` (`int loserTsHours = Configs.LOSER_TIME_STOP_HOURS;`)
  và **cổng điều kiện `:1026`** — `if (loserTsHours > 0 && orderMulti.priceSL == null) { … đóng tại min(open,close) … }`.
- ⇒ **`SIM_LOSER_TIME_STOP_HOURS = 0` LÀ CÁCH TẮT ĐÚNG** (`<= 0` ⇒ nhánh không chạy ⇒ cúm không bị đóng cứng theo giờ;
  đúng như comment code *"0=tat"*, `Configs.java:477`). **H1 = set `= 0`. H0 = giữ `=168` (y profile, 0 override).**

## 3. HAI ARM KHOÁ TRƯỚC (KHÔNG thêm/bớt)

Nền chung = `PROFILE r4_kg0_k16_f015_g155` + **6 override = `g2_flat3`** (`SIM_GATE_ROLLING_MODE=ratio`,
`SIM_GATE_ROLLING_DAYS=90`, `SIM_GATE_ROLLING_PCT=0.999950829`, `TS_GIVEBACK_RATIO=1.0`,
`SIM_TS_MAX_GAP=0.03`, `SIM_TS_MAX_GAP_WEAK=0.03`) — y hệt `RESULT_TRAIL2_G2.md`/`RESULT_DOUBLE_ENTRIES.md`.

| arm | khác biệt (trên nền chung) | ý nghĩa |
|---|---|---|
| **H0** (control) | **y nguyên `g2_flat3`** — KHÔNG override time-stop (`SIM_LOSER_TIME_STOP_HOURS=168`) | parity anchor: md5 phải KHỚP baseline đã công bố |
| **H1** (hold-to-die) | thêm đúng **1 override** `SIM_LOSER_TIME_STOP_HOURS=0`; **GIỮ** `DCA_GRID_WEIGHTS=1,1,1,1` + `DCA_GRID_SCALE=6.0` (4 leg, không thêm level) | vào lệnh không còn bị đóng cứng sau 168h |

Tag Kaggle: `htd-h0`, `htd-h1` (kernel `chuyendinh/sim-htd-h0` / `sim-htd-h1`).

### 3.1 Dự báo TRƯỚC (từ bằng chứng cũ — để đối chiếu, KHÔNG dùng để đổi luật)

- **Bằng chứng CŨ (`docs/analysis/RULERS_CURRENT.md` §10.4 + `docs/result/RESULT_EXIT_STRUCT.md` dòng A1):**
  trong bối cảnh CŨ (**nhịp 15′ / K=8**, `B* = kg0-g170`), arm **"grid + BỎ TS168"** cho
  `n 780` · `CAGR 17,29 → 9,05 %` · `maxDD −6,27 → −12,38` · **`UW 166 → 318` (VƯỢT trần 250)** ⇒ **PHÁ HOẠI**.
  Cúm thua lỗ bị giữ "sống" → chiếm slot/vốn → tail rủi ro + CAGR sụp.
- **Vòng NÀY kiểm lại trong bối cảnh MỚI (G2, nhịp 1', K=16, rolling gate)** — cơ chế có thể KHÁC.
- **Dự báo có hướng:** `n` H1 **có thể thay đổi** (time-stop đóng cúm sớm ⇒ giải phóng slot/coin ⇒ có thể MỞ thêm entry;
  hoặc `n` giảm nếu cúm "sống" lâu chiếm slot) — **không chốt dấu**; `UW`/`ddPhút` H1 **dự báo XẤU HƠN** H0;
  rủi ro chính = **vỡ `UW ≤ 250`** (tiền lệ `UW 318`) và **2022/2025 âm**.

## 4. CỔNG PARITY (buộc — đọc TRƯỚC khi kết luận H1)

- **H0 = baseline `g2_flat3`** phải khớp **`md5(printDone.csv) = 650c386f0d0dfea334af9d55ca2f21d4`**
  (= artifact `g2flat3-val`/`trail2-g2-flat3`, `n 2517`, eq `131 908`). **Lệch ⇒ DỪNG**, báo parity FAIL, không kết luận.
- `[GATE-RATIO]` bật thật (`mode ratio`, `pct=0.999950829`, `days=90`) · `[CONC-PC] SUMMARY blocked=0`.
- Ghi `jar_sha256` (phải `7368be46…`) + `symbol_mapper=863`. Parity dùng **md5 `printDone.csv`**, KHÔNG dùng `PROFILE_HASH`.

## 5. CHẤM 4 TẦNG §9 (as-is — phí base đã nằm trong artifact)

Công cụ: `research/analysis/holdtodie_driver.py` (gọi thẳng `research/analysis/reset_rule_score.py`:
`load_legs`/`load_daily`/`core_metrics`/`ci_pair`/`run_mtm` — KHÔNG viết lại thuật toán). Chấm **as-is** (không hiệu chỉnh lại phí).

| tầng | ngưỡng |
|---|---|
| **T1** RÀO RỦI RO (MTM phút) | maxDD **MTM phút**/năm ≤ 40 % · **`UW ≤ 250` ngày** · quý xấu nhất ≥ −20 % · **0 năm âm** · conc 1 coin ≤ 15 % |
| **T2** ĐỘ BỀN | `q* ≥ 15 %` · `%PnL top-1% lệnh ≤ 25 %` |
| **T3** NON-INFERIORITY vs **H0** | `win% ≥ −2,0 pp` · `TSloss% ≤ +2,5 pp` (CI **block-72h**, **2000 rep**, seed **`20260905`**, **`inflate(k)`**) |
| **T4** MỤC TIÊU | `n` **MỤC TIÊU CHÍNH** (báo cáo) · **`Calmar_MTM ≥ 0,90 × H0`** · **`conc ≤ H0`** |

- **`k` = 1** (đúng **1 arm** đối chiếu vs baseline H0) ⇒ **`inflate(k=1) = 1,0`** (single comparison, KHÔNG hiệu chỉnh đa so sánh — đồng quy `reset_rule_cadence_driver.py`).
- `Calmar_MTM = CAGR / |maxDD MTM-phút toàn kỳ|`; `Calmar_MTM ≥ 0,90 × H0(đo được)` (H0 kỳ vọng ~1,88–1,94).
- Phụ: **bảng theo NĂM và QUÝ** (`n`, `ΣPnL`, `win%`) cho **cả 2 arm**.

## 6. LUẬT KẾT LUẬN (chốt TRƯỚC)

1. **Parity H0** (mục 4) FAIL ⇒ DỪNG, báo parity FAIL, **không** kết luận về H1.
2. H1 **chỉ** được coi là **ỨNG VIÊN giữ/đề xuất** nếu **PASS CẢ T1–T4** §9.
3. H1 **FAIL bất kỳ tầng nào** ⇒ **NULL** cho trục "tắt TS 168h"; ghi rõ tầng vỡ + số cụ thể.
4. Nếu H1 **PASS cả 4 tầng**: vì **`n` là mục tiêu chính** ⇒ **đáng đề xuất đổi** khi **`Δn = n(H1) − n(H0) ≥ +1 %`**
   (≥ ~25 lệnh). Nếu **PASS nhưng `Δn < +1 %`** ⇒ *"qua cổng nhưng KHÔNG mở thêm entry"* ⇒ **không đề xuất đổi**.
5. Báo cáo luôn **`Δn` (+%) · `ΔUW` · `ΔddPhút` · `Δwin%` · `ΔTSloss%`** và **đối chiếu với bằng chứng cũ `UW 318`**.
6. **Trả lời riêng câu (3):** time-stop 168h có đang **"giữ slot" chặn entry** không — đo bằng **số vị thế đồng thời** và **thời gian giữ TB** (nếu số liệu cho phép từ artifact).

## 7. OUTPUT

`docs/prereg/PREREG_HOLDTODIE.md` (này) + `docs/result/RESULT_HOLDTODIE.md` (+ `docs/result/holdtodie.json`). Commit + **push**.
