# RESULT_BIGUP_MEDIUPDOWN — đo lại BIG_UP / MEDIUM_UP / MEDIUM_DOWN (code cũ `157cf4d`) vs BIG_DOWN hiện tại

Ngày: 2026-09-22. Pre-reg: `docs/PREREG_BIGUP_MEDIUPDOWN.md` (commit `5102899`, chốt TRƯỚC khi chạy).
Script: `research/analysis/bigup_mediumdown.py` (sinh tín hiệu) + `bigup_mediumdown_stats.py` (đo).
0-sim, **thuần Python**, không Java, không push. DEV + đối chiếu; **KHÔNG chạm 2026.**

## KẾT LUẬN (một dòng)

**NO-GO cả 3 level** (`BIG_UP`, `MEDIUM_UP`, `MEDIUM_DOWN`): không level nào đạt cổng GO — phần
fire **độc lập với MOM15 đều không có edge**, edge dương (nếu có) **chỉ nằm ở phần trùng MOM15**,
và **không ổn định** (sign-flip theo năm, 2022 âm; DEV CI chứa 0). Không có gì để áp vào mô hình
hiện tại từ nhánh này. Dòng tham chiếu `BIG_DOWN_OLD` cũng không GO.

Điều này **đo lại và XÁC NHẬN** (không chép) kết luận cũ của `docs/SURVEY_OLDCODE_SIGNALS.md` §4 về
`MEDIUM_DOWN` ("correlated MOM15"), đồng thời **phủ định** khả năng có "cược mới độc lập" từ
`BIG_UP`/`MEDIUM_UP`.

---

## 1. Logic cũ vs BIG_DOWN hiện tại (bảng so sánh 4 cột)

Xem chi tiết + file:line ở `docs/PREREG_BIGUP_MEDIUPDOWN.md` §1 (nguồn: `/home/ubuntu/trend_review/old_era/`,
commit `157cf4da1b7778b5476ac5371c6467381c43b8ba`, 2025-10-08).

| | **BIG_UP (cũ)** | **MEDIUM_UP (cũ)** | **MEDIUM_DOWN (cũ)** | **BIG_DOWN hiện tại (HEAD)** |
|---|---|---|---|---|
| trigger | `rateUpAvg > 0.025` | `rateUpAvg > 0.015` | `rateDownAvg < -0.030` ∨ (`rateDownAvg < -0.014` ∧ `rateDown15MAvg < -0.07`) | `rateDownAvg < -0.03157` (`MS_DOWN_BIG_AVG`) |
| neo BTC | không | không | không | cũ có `btcRateChange < -0.01`; **HEAD BỎ** |
| chọn symbol | top-2 **rớt 15M sâu nhất** (`getTopSymbol` trên `rateDown15M2Symbols`) | như BIG_UP | như BIG_UP | `getTopSymbolArray`: xếp theo **pNoPump tăng** (score selector) khi `BD_SEL_MODE=off` (default) |
| số coin/lần | 2 | 2 | 2 | 2 |
| sizing | full budget (×1.2 nếu ETH trend buy) | **½** budget | **½** budget | full + (BdSizeAdapt/tier/vol/pacing, mặc định off) |
| gate 15M | **không** (era `157cf4d` chưa có gate) | không | không | **không** (`if (!levelChange.equals(BIG_DOWN))` mới qua `EntryGate`) |
| exit | chung (TP = `priceMax15M`) | chung | chung | chung (không có nhánh exit riêng theo level) |
| DCA config | `(15, -0.08, false)` | `(15, -0.15, false)` | `(15, -0.08, false)` | `(8, -0.05, isAll=true)` |
| cap phụ | — | — | — | `ConcCapLiveGuard` (trần leg BD/60′), `HoldoutSeal` |

**Khác bản chất (không chỉ ngưỡng):**
1. HEAD **xóa toàn bộ họ level** (BIG_UP/MEDIUM_UP/MEDIUM_DOWN/SMALL_*/*_15M) — chỉ còn BIG_DOWN.
2. HEAD **bỏ neo BTC** khỏi BIG_DOWN (xem §5, dòng tham chiếu: neo BTC cũ đổi hẳn tính chất mẫu).
3. HEAD **đổi tiêu chí chọn coin**: "rớt 15M sâu nhất" → "pNoPump thấp nhất theo selector".
4. Sizing BIG_UP/BIG_DOWN = full; MEDIUM_UP/MEDIUM_DOWN = ½ (HEAD giữ full cho BIG_DOWN).

---

## 2. Kiểm chứng tái tạo dữ liệu (trước khi tin kết quả)

Scalar tái tạo từ `raw/*.f32` (627 symbol, 1M, closed bars) so với `market.bin` — nguồn sim dùng
(số tham chiếu ở `docs/DIAG_BIGDOWN_TRIGGER_MECHANISM.md` §3.3):

| `rateDownAvg` | tái tạo (2.63M phút) | `market.bin` (§3.3) |
|---|---|---|
| p50 | **-0.000647** | **-0.000647** |
| p25 | -0.001369 | -0.001366 |
| min (p0) | **-0.354162** | **-0.354162** |
| mean / std | -0.000808 / 0.001473 | -0.000782 / 0.001376 |

⇒ Tái tạo **khớp tới 6 chữ số** ở p50/p0. Phép đo đứng trên chuỗi causal đúng chuỗi hệ thống dùng.
(Chênh lệch nhỏ ở mean/std là do cửa sổ/ universe khác chút: 2021-01..2025-12 vs 2021-07..2025-12.)

Số phút `rateDownAvg < -0.03157` = **166** phút (toàn dải) — cùng bậc với 124 phút của `market.bin`
(§3.4). `rateDown15MAvg < -0.028` = 0.50% số phút.

---

## 3. Kết quả đo (fire per-minute, lock = HOLD 24h, chi phí 0.10% + slip + funding)

`k = 3` level quyết định (`BIG_UP`, `MEDIUM_UP`, `MEDIUM_DOWN`) + 1 dòng `BIG_DOWN_OLD` **tham
chiếu** (descriptive, ngoài tập quyết định). Tổng **1 812 event**, 469 symbol, 2021-01..2025-12.

### 3.1 Headline

| Level | N | meanNet | meanRaw | win | CI72h (×1.0) | p(>0) | CI72h **×1.21** | **DEV 2022-01..2024-06** | ICC(day) | ICC(72h) |
|---|---|---|---|---|---|---|---|---|---|---|
| **BIG_UP** | 320 | +29.86% | +35.63% | 69.4% | [2.14%, 51.41%] | 0.995 | [0.05%, 59.67%] | **+0.87%**, p=0.63 | 0.009 | 0.031 |
| **MEDIUM_UP** | 914 | +4.56% | +6.41% | 59.8% | [1.72%, 7.36%] | 0.999 | [1.14%, 7.97%] | **+1.84%**, p=0.94 | 0.278 | 0.103 |
| **MEDIUM_DOWN** | 444 | +7.07% | +11.43% | 61.7% | [2.12%, 12.39%] | 0.999 | [0.86%, 13.28%] | **+1.25%**, p=0.73 | **0.447** | **0.312** |
| BIG_DOWN_OLD (ref) | 134 | +19.21% | +27.51% | 78.4% | [8.96%, 27.46%] | 1.000 | [8.02%, 30.40%] | +4.04%, p=0.987 | 0.146 | 0.168 |

Null test (block sign-flip 72h, seed 20260905): p(≥obs) = 0.014 / 0.002 / 0.002 / 0.000 → headline
mean khác 0 về mặt thống kê **trên toàn dải**, nhưng đó là do vài episode (xem §3.4).

### 3.2 Theo năm (sign-flip rõ)

| Năm | BIG_UP | MEDIUM_UP | MEDIUM_DOWN |
|---|---|---|---|
| 2021 | +24.89% (N=84) | +11.12% (N=278) | +16.13% (N=180) |
| 2022 | **−7.91%** (N=38) | **−0.50%** (N=190) | **−0.30%** (N=54) |
| 2023 | +6.79% (N=20) | +4.90% (N=64) | +1.83% (N=64) |
| 2024 | +3.78% (N=62) | +4.93% (N=124) | +0.68% (N=80) |
| 2025 | +63.75% (N=116) | **+0.95%** (N=258) | +1.24% (N=66) |

`%coin+`: BIG_UP 72.2% (234 sym), MEDIUM_UP 64.4% (371), MEDIUM_DOWN 63.4% (213).

### 3.3 ĐIỀU KIỆN TIÊN QUYẾT — overlap MOM15 (`rateDown15MAvg < -0.028` tại mốc 15m gần nhất)

| Level | % fire lúc **MOM15 firing** | edge MOM15-FIRING | edge **MOM15-QUIET** (phần độc lập) |
|---|---|---|---|
| BIG_UP | **81.25%** (260/320) | +36.06% (p=0.998) | **+2.99%** (p=0.807, CI chứa 0) |
| MEDIUM_UP | **51.86%** (474/914) | +8.76% (p=1.000) | **+0.03%** (p=0.519) |
| MEDIUM_DOWN | **60.36%** (268/444) | +11.33% (p=1.000) | **+0.58%** (p=0.607, CI chứa 0) |
| BIG_DOWN_OLD (ref) | 65.67% (88/134) | +27.43% (p=1.000) | +3.49% (p=0.977) |

Secondary (ngày, `printDone.csv` C2b DEV): fire-days trùng ngày có lệnh MOM15 = 38.0% / 28.8% /
42.2%; fire trùng `(sym, ngày)` với lệnh MOM15 = **0.00%** cả 3.

**Đọc:** cả 3 level **trùng MOM15 ở 52–81% số fire**, và **toàn bộ edge dương tập trung ở phần
trùng đó**. Phần fire "độc lập" (MOM15 im) — chính là phần có thể thêm `n_eff` — có edge ≈ 0
(p 0.52–0.81, CI chứa 0) ở cả 3 level.

### 3.4 Tập trung đuôi cực mạnh (giải thích con số headline)

| Level | median net | p10 / p90 | top 5% event = % tổng net |
|---|---|---|---|
| BIG_UP | +8.45% | −16.9% / +64.1% | **59.3%** |
| MEDIUM_UP | +3.93% | −17.2% / +25.5% | **64.1%** |
| MEDIUM_DOWN | +3.74% | −15.6% / +29.8% | **51.0%** |
| BIG_DOWN_OLD (ref) | +11.45% | −5.5% / +55.0% | 26.3% |

Top event dồn vào **cùng vài mốc capitulation toàn thị trường**: `2025-10-10 21:1x–21:2x`
(BIG_UP: PLUME +617%, HEI +565%…), `2021-05-19` (crash), `2022-05-12/13` (LUNA),
`2022-11-09` (FTX). ⇒ "edge" này là **bounce sau capitulation diện rộng**, không phải một tín hiệu
phân biệt được; xem thêm ICC(day) cao (0.28–0.45) ở MEDIUM_UP/MEDIUM_DOWN.

Ghi chú: subset `ONSET` trùng khít toàn mẫu (lock HOLD đã bảo đảm ≥24h giữa 2 fire cùng symbol),
nên không tách được thêm thông tin.

---

## 4. Cổng GO/NO-GO (PREREG §5) — theo từng level

| Điều kiện GO | BIG_UP | MEDIUM_UP | MEDIUM_DOWN |
|---|---|---|---|
| 1. `mean(net)>0` DEV **và** CI ×1.21 loại 0 | ✗ DEV +0.87%, p=0.63 | ✗ DEV +1.84%, p=0.94 | ✗ DEV +1.25%, p=0.73 |
| 2. ICC episode đủ thấp | ✓ 0.031 | ~ 0.103 | ✗ **0.312** |
| 3. Overlap MOM15 thấp **và** phần độc lập có edge | ✗ 81% trùng; quiet +3.0% (p=0.81) | ✗ 52% trùng; quiet +0.03% (p=0.52) | ✗ 60% trùng; quiet +0.58% (p=0.61) |
| 4. Ổn định (không sign-flip; `%coin+ ≥ 50%`) | ✗ 2022 −7.9%; 2025 +63.8% | ✗ 2022 −0.5%; 2025 +0.95% | ✗ 2022 −0.3%; 2025 +1.2% |
| **Kết luận** | **NO-GO** | **NO-GO** | **NO-GO** |

`BIG_DOWN_OLD` (tham chiếu): cũng không đạt (điều kiện 1 chỉ vừa đủ ở DEV p=0.987 nhưng CI ×1.21
chạm 0; overlap 66%; gần như toàn bộ edge ở 2021/2025).

**Không thêm biến thể, không đổi ngưỡng, không nới HOLD sau khi thấy số** (chống leak L2 /
multiple-comparison). `k = 3`.

---

## 5. Đối chiếu với kết luận cũ (đo lại, không chép)

- `SURVEY_OLDCODE_SIGNALS.md` §4 xếp `MEDIUM_DOWN` vào nhóm "LOẠI vì correlated MOM15" — trước đây
  **chưa đo lại**. Đo lại: **XÁC NHẬN** (60.4% fire trùng MOM15; 39.6% còn lại edge ≈ 0).
- SURVEY §4 nói `BIG_UP`/`MEDIUM_UP` "momentum-up breadth, prior yếu, chủ yếu vai trò gate" — đo
  lại: **XÁC NHẬN** (edge nằm ở phần trùng MOM15 81%/52%; phần độc lập ≈ 0).
- SURVEY xếp `BIG_DOWN` cũ = "đã dùng" — nhưng neo `btcRateChange < -0.01` của bản cũ khác hẳn
  bản HEAD (HEAD bỏ neo này). Đo tham chiếu: `BIG_DOWN_OLD` có mẫu nhỏ hơn (134 vs 166 phút trigger),
  phần MOM15-quiet dương nhẹ (+3.49%, p=0.977, CI ×1.21 chạm 0) — **không đủ để GO**, nhưng nêu ở
  đây như một khác biệt quan sát được giữa bản cũ và bản HEAD.

---

## 6. Apply — KHÔNG có gì để tích hợp

Vì cả 3 level **NO-GO**, **không đề xuất tích hợp vào code sản xuất** và **không tự sửa code**.

Nếu owner vẫn muốn theo hướng này, ghi rõ các hướng **phải pre-reg riêng** (không được làm ngầm):
1. **"Độc lập MOM15" không mua được edge** ở đây: thêm `BIG_UP`/`MEDIUM_UP`/`MEDIUM_DOWN` làm
   trigger entry = thêm cược **trùng** nhánh momentum/capitulation đang giao dịch (52–81% fire
   trùng MOM15) ⇒ **không tăng `n_eff`**, chỉ tăng đòn bẩy vào cùng loại ngày.
2. Khác biệt duy nhất còn thấy được là **neo BTC** của bản `BIG_DOWN` cũ so với HEAD — nhưng đó là
   câu hỏi **khác** (đổi trigger BIG_DOWN hiện tại), cần pre-reg riêng + parity gate + đo trên
   harness Java (không được suy từ file này).
3. Nếu muốn thử dù sao: bắt buộc flag mới **default OFF**, parity gate (byte-identical khi OFF),
   và pre-reg riêng cho bước tích hợp. Bản thân phép đo này **không** dùng để bật bất kỳ default nào.

---

## 7. Hạn chế (trung thực)

1. Harness **không áp** gate 15M/selector (đúng era `157cf4d` không có gate) — nên đây là edge của
   **tín hiệu thô**, không phải của leg sau gate hiện tại.
2. Chọn coin = đúng luật cũ ("top-2 rớt 15M sâu nhất"); HEAD dùng tiêu chí khác (pNoPump) ⇒ kết quả
   **không** so sánh 1-1 với leg BIG_DOWN hiện tại.
3. `lock = HOLD 24h` là **abstraction** ghi trước (live unlock khi vị thế đóng theo TP/SL) — có thể
   làm số fire khác live, không sửa sau khi thấy số.
4. Không tái tạo được `Constants.diedSymbol` và vũ trụ chính xác của từng ngày; universe = 627
   symbol có file 1M (gồm coin delist).
5. Overlap MOM15 dùng `rateDown15MAvg` tại **mốc 15m-align gần nhất**, còn trigger cấp độ dùng giá
   trị **cùng phút** — định nghĩa cầu nối giống `PREREG_REVERSAL_BOUNCE.md` §4, ghi rõ ở đây.
6. `min net = -100%` (vài coin về 0/delist trong 24h) — đo trên giá close, không mô hình thanh lý.

---

## 8. Artifact + tuân thủ

- Pre-reg `docs/PREREG_BIGUP_MEDIUPDOWN.md` (commit `5102899`) có **TRƯỚC** mọi phép đo; sau khi
  chạy **không sửa thiết kế** (trigger/selection/lock/HOLD/cổng).
- Script trong repo: `research/analysis/bigup_mediumdown.py`, `bigup_mediumdown_stats.py`.
- Không `claude-run`/Claude Code; không Java trên Oracle; **thuần Python** (đọc `raw/*.f32` +
  Aerospike `funding_data` chỉ-đọc). Không push. 2026 không đụng (dữ liệu ≤ 2025-12-31).
- File tạm `/tmp/bigup_mediumdown/` đã dọn sau khi chốt số (report.txt nằm trong chính tài liệu này).
