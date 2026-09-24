# PREREG — EXIT VARIANTS TRÊN NỀN NHIỀU LỆNH (GD92 & T100)

Chốt **TRƯỚC** khi chạy bất kỳ sim nào. Ngày 2026-09-24. Branch `module` (HEAD `b50833f`).
Sim chạy **trên Kaggle CPU kernel** (`docs/runbooks/KAGGLE_SIM.md`) — **KHÔNG** chạy Java/sim trên Oracle
(Oracle chỉ `mvn -o package`). **KHÔNG** `claude-run`/Claude Code. **KHÔNG** push. DEV only
(cửa sổ `2021-07-01 .. 2025-12-31`, không chạm 2026).

---

## 0. VÌ SAO CÓ VÒNG NÀY — sửa một lỗi DÁN NHÃN của vòng trước

Vòng trước (`docs/prereg/PREREG_GD92_X_EXIT.md` / `docs/result/RESULT_GD92_X_EXIT.md`, commit `0d1d690`/`4e263c2`)
dán nhãn chân **"(A) GD92-only"** cho cấu hình chạy trên profile
**`x1_gs_t170`** + 2 key rolling. Nhưng `x1_gs_t170` = **T170** (gate scale **1.70**), còn
định nghĩa GD92 là **`x1_c3_full` + `SIM_GATE_ROLLING_PCT=0.92` + `SIM_GATE_ROLLING_DAYS=90`**
(gate scale **1.00**). Bằng chứng số học: chân đó ra **1,108 leg / equity 99,179** — đúng cỡ
**nền T170 (1,089 leg)**, KHÔNG phải cỡ nền GD92 (2,632 leg).

⇒ **Hệ quả (phải ghi rõ):** vòng trước **chưa bao giờ** test exit variant trên **nền nhiều lệnh**.
Cả 4 chân A/B/C/D đều nằm trên nền T170 (1,089 leg) — đúng chỗ đã test 6 lần trước đó.
Số liệu vòng trước **không sai**; chỉ **nhãn nền sai**.

Yêu cầu owner: *"tư duy là trailing hiện tại có thể đang ko đổi vì T170 có ít lệnh nên ko tạo ra
khác biệt. test với GD92 nhiều lệnh hoặc có thể test với T100."* ⇒ Vòng này test lại trên **2 nền
nhiều lệnh**: GD92 (2,632) và T100 (2,559).

---

## 1. SỰ THẬT ĐÃ XÁC MINH (dùng lại, không suy diễn lại)

| mốc | cấu hình | n (leg) | equity | md5 `printDone.csv` |
|---|---|---|---|---|
| **T170** (`x1_gs_t170`) | gate scale 1.70, không rolling | **1,089** | **111,070** | `efb793e2468ca3a7318da0f0ad23d4fc` |
| **T100** (`x1_c3_full`) | gate scale 1.00, không rolling | **2,559** | **121,770** | `dc16e4da6ff6cb7b8d41c592bc3d9c45` |
| **GD92** (`profiles/archive/x1_gd92.properties`) | `x1_c3_full` + `SIM_GATE_ROLLING_PCT=0.92` + `SIM_GATE_ROLLING_DAYS=90`; `PROFILE_HASH=52ee74bb5477b363 keys=21` | **2,632** | **133,944** | (chưa có md5 chuẩn — xem §4) |

- GD92 tái lập trên `wfo_ds_x1_2021`: **CAGR 34.76% · maxDD toàn kỳ −16.55% · UW toàn kỳ 278**
  (`docs/result/RESULT_GD92_RECHECK.md`).
- Bản CŨ của GD92 (dataset `wfo_ds_x1`, cửa sổ từ **2022-01**): **2,355 · 128,979**.
- **T100/GD92 base đã FAIL rào cứng toàn kỳ ngay từ đầu**: T100 maxDD −16.13% / UW 248;
  GD92 maxDD −16.55% / UW 278 (`docs/result/RESULT_GD92_RECHECK.md` §4).
  ⇒ **GO là KHÔNG THỂ cho 2 nền này.** Vòng này vì vậy là **PHÉP ĐO CƠ CHẾ**
  ("exit có tác dụng khi n nhiều không?"), và phải nói rõ điều đó khi báo cáo.

⚠️ Code rolling **KHÔNG có trên `module`** (`GateRollingThreshold.java` bị xoá ở `f1c43a3`).
Dùng `git cherry-pick -n 1db0613` (branch `gd92-recheck`), build jar, chạy, **sau đó
`git checkout -- src/`** để trả `module` nguyên trạng. **KHÔNG merge**. Ghi rõ sha256 jar.

---

## 2. THIẾT KẾ — 6 chân (nền × exit) + 3 baseline

**Nền (2):**

- **(G) GD92** = profile `x1_c3_full` + `SIM_GATE_ROLLING_PCT=0.92` + `SIM_GATE_ROLLING_DAYS=90`
  (tập key/giá trị **trùng khít** `profiles/archive/x1_gd92.properties`; `PROFILE_HASH` không
  phụ thuộc thứ tự — `Cfg.java:117` hash `TreeMap` — nên hai đường tương đương từng key).
- **(T) T100** = profile `x1_c3_full` nguyên bản.

**Exit override (3) — lấy ĐÚNG từ `prof_run.properties` của các run cũ, không tự diễn giải:**

| nhãn | override | nguồn |
|---|---|---|
| **HINGE V3** | `SIM_TS_PNOPUMP_WEAK_THR=0.17` | `devrun/X1_TH_WEAK17_2021` ⇒ `profiles/x1_th_weak17.properties` (diff vs `x1_gs_t170` = **đúng 1 dòng**, `RESULT_TRAIL_HINGE.md` §1) |
| **LADDER L1** | `TS_LADDER=1` · `TS_LADDER_LO=0.00,0.10,0.25,0.50,1.00` · `TS_LADDER_GAPS=0.04,0.08,0.15,0.25,0.35` | `kaggle_sim/out/tl-l1/prof_run.properties` |
| **CAP 10/30** | `SIM_TS_MAX_GAP=0.30` · `SIM_TS_MAX_GAP_WEAK=0.10` | `kaggle_sim/out/tc-cap/prof_run.properties` (diff vs `tc-par` = **đúng 2 dòng**) |

**9 chân (tất cả + `SIM_TRAIL_TRACE=1`, đo-lường-only — tiền lệ `tl-par` == `tl-part`
byte-identical, `RESULT_TRAIL_LADDER.md` §1):**

| # | tag | nền | exit override |
|---|---|---|---|
| 1 | `hn-par1` | `x1_gs_t170` (T170) | — (cổng parity 1 + mốc capture) |
| 2 | `hn-t100` | `x1_c3_full` (T100) | — (**cổng parity 2** + baseline nền T) |
| 3 | `hn-g92` | GD92 | — (**tái lập** + baseline nền G) |
| 4 | `hn-t-hi` | T100 | HINGE V3 |
| 5 | `hn-t-la` | T100 | LADDER L1 |
| 6 | `hn-t-cp` | T100 | CAP 10/30 |
| 7 | `hn-g-hi` | GD92 | HINGE V3 |
| 8 | `hn-g-la` | GD92 | LADDER L1 |
| 9 | `hn-g-cp` | GD92 | CAP 10/30 |

Tất cả: `TICKER_SOURCE=file`, `SIM_END_DATE=20251231`, `TIME_RUN=20210701`, mapper ≥ 800
(guard), guard tổng ticker ≥ 1,826 ngày.

---

## 3. CỔNG CHẶN — chạy TRƯỚC, chưa qua thì DỪNG

| cổng | điều kiện PASS | nếu FAIL |
|---|---|---|
| **P1 parity** | `hn-par1` md5 `efb793e2468ca3a7318da0f0ad23d4fc`, n=1089, eq 111,070 | DỪNG, báo RO |
| **P2 parity** | `hn-t100` md5 `dc16e4da6ff6cb7b8d41c592bc3d9c45`, n=2559, eq 121,770 | DỪNG, báo RO |
| **P3 tái lập GD92** | `hn-g92` cho **n ≈ 2,632 · eq ≈ 133,944** (recheck) | giải thích được lệch mới đọc tiếp; lệch kiểu 2022-01 (2,355/128,979) ⇒ **SAI CỬA SỔ**, DỪNG |
| **P4 rolling thật** | log `hn-g92/hn-g-*` có `[GATE-ROLL] BAT: pct=0.92 window=90d`, `nBeforeFirst=0` | DỪNG, báo RO |
| **P5 key bind** | md5 của 6 chân exit **KHÁC** md5 baseline nền tương ứng (ít nhất 1 chân nền khác) | chân không đổi = **VÔ HIỆU**, báo rõ |

`PROFILE_HASH` trên Kaggle **không** so được với Oracle (đổi `WFO_FUNDING_PRED_DIR` mount) —
so bằng `keys=` + md5 `printDone.csv` + so key-set/giá trị với profile Oracle (đã diff cục bộ
trước khi chạy).

---

## 4. CHẤM — 5 rate chất lượng + CI hai độ rộng

- **5 rate**: `win%` · `TSloss%` · `mP|SM` · `mP|SL` · `meanP` (định nghĩa như
  `research/analysis/gd92xexit_score.py`, tái dùng nguyên).
- **Baseline để so = baseline CỦA CHÍNH NỀN**:
  - nền **G**: `hn-g-hi`, `hn-g-la`, `hn-g-cp` **vs `hn-g92`**;
  - nền **T**: `hn-t-hi`, `hn-t-la`, `hn-t-cp` **vs `hn-t100`**.
  - Bổ sung (tham chiếu, không phải tiêu chí): `hn-g92` vs `hn-t100` (tách riêng tác dụng
    **gate**), và mọi chân vs **T170** (mốc incumbent, "T170 = 0/5").
- **CI**: block-72h, **2000 rep**, seed **20260905**, anchor **2021-07-01**, báo **CẢ HAI** độ
  rộng: legacy **×1.21** và chuẩn hoá **`inflate(k) = sqrt(2 ln k)`** với **k = 3**
  (`1.482304`). **"Ngoài CI" = ngoài ở CẢ HAI độ rộng** (tiền lệ `traillad_score.py`).
- **Câu hỏi trung tâm:** ở mỗi nền, **bao nhiêu rate ngoài CI** (TỐT/XẤU) và **độ lớn Δ** là bao
  nhiêu — so với **T170 (0/5)**. ⇒ **Hiệu ứng của exit có TĂNG theo n không?**

## 5. RÀO CỨNG (`docs/runbooks/RISK_APPETITE.md`) — kiểm **CẢ theo năm LẪN toàn kỳ**

`maxDD ≤ 30%/năm` · `UW ≤ 200 ngày` · `quỹ xấu nhất ≥ −15%` · `không năm âm` · `tập trung 1 coin ≤ 15%`.

> Biết trước: **T100 và GD92 base đã FAIL toàn kỳ** (maxDD −16.13%/−16.55%, UW 248/278).
> ⇒ Rào cứng ở vòng này **không thể** cho GO; nó là **thông tin cơ chế** (exit có kéo được
> UW/maxDD không) và **được báo cáo nguyên vẹn**, không dùng để "cứu" chân nào.

**Bắt buộc:** bảng PnL chi tiết theo năm cho **9 chân** (năm · n · win% · TSloss% · meanP ·
PnL(USDT) · ret% · maxDD% · UW · qmin% · equity) + `n`/`hold`/`turnover`/`capture ratio`
(nhóm đỉnh ≥ 20/50/100% từ `trailTrace.csv`).

## 6. LUẬT KẾT LUẬN (khoá trước)

- **Phần (a) — exit có tác dụng ở n cao không?** Trả lời bằng số: số rate ngoài CI (cả hai độ
  rộng) ở mỗi nền, độ lớn Δ, và so với T170 (0/5). Đây là câu trả lời **cơ chế**, độc lập với
  rào cứng.
- **Phần (b) — có GO không?** **GO chỉ khi**: ≥ 2 rate **TỐT** ngoài CI **và** 0 rate **XẤU**
  ngoài CI **và** hết rào cứng **toàn kỳ**. Vì T100/GD92 base FAIL toàn kỳ từ đầu ⇒ **đáp án đã
  là KHÔNG**; nếu đo được tác dụng thì đó là **cơ chế đáng theo một vòng mới trên nền PASS**
  (T170), **không** phải GO cho GD92/T100.
- Nếu **không** có tác dụng ⇒ **NULL** + nói rõ **có nên đóng hẳn trục exit không**.

## 7. MULTIPLICITY

`k = 3` cho mỗi nền (3 exit × 2 nền = 6 chân exit, mỗi nền chấm với `k=3`). Nếu vòng này tình cờ
có tác dụng, phải tính thêm **số vòng exit đã chạy chống T170 trong chương trình** (TRAIL-HINGE 3 ·
TRAIL-LADDER 3 · TRAIL-CAP-1030 2 · CLOSE-BIGGAP 18 · PEAK-CLOSE 1 · GD92×EXIT 3 · vòng này 6)
trước khi coi là tín hiệu. Kết quả NULL ⇒ không cần viện đến multiplicity.

## 8. DỰ ĐOÁN GHI TRƯỚC (để đối chiếu sau, không sửa)

| dự đoán | lý do |
|---|---|
| ≥1 chân exit ở nền nhiều lệnh có **≥1 rate ngoài CI** (khả năng cao nhất: `TSloss%` hoặc `meanP`) | exit bind nhiều hơn khi n lớn (2,559–2,632 vs 1,089) ⇒ hiệu ứng đo được nhiều hơn |
| **Không** chân nào đạt GO | T100/GD92 base FAIL rào cứng toàn kỳ; và mọi vòng exit trước đều NULL |
| LADDER L1 làm **tăng** số leg đạt đỉnh ≥ 50% và SumPnL nhóm đó (như trên T170) nhưng **không** tăng capture theo lệnh | cơ chế gap lớn hơn ⇒ sống lâu hơn |
| GD92-base (gate) làm rate chất lượng **xấu** hơn T100-base | `RESULT_GD92_RECHECK.md`: rolling gate kéo chất lượng xuống |

## 9. KỶ LUẬT

Không push. Không merge `gd92-recheck`. Code rolling cherry-pick `-n` rồi `git checkout -- src/`.
Chỉ commit docs + script + profile. Không chạm 242. Không đóng holdout 2026. Không quét biến thể
GD92 (0.88/0.90/0.94/0.96, W=60/120/180) hay biến thể exit mới. Không đổi incumbent (T170 giữ).
