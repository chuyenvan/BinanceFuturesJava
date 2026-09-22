# RESULT_BREADTH_GATE_SIM.md — TASK B2 Bước 6: sim gate breadth-regime (top-50/MA200/50%)

Thực thi: 2026-09-21, executor Sonnet (session `session_01UoVRjusfNM2USSVNKQrm7z`), 3 sim tuần tự trên Oracle
`/home/ubuntu/src/BinanceFuturesJava` nhánh `module`. Thiết kế khoá trước ở `docs/PREREG_BREADTH_GATE_SIM.md`
(commit `83f5457`). Không sửa file `.java` nào, không sửa `breadth_regime.py`/`regime_build_ma200.py`/
`bigdown_struct.py`/`x1_rates.py`/`regime_updown_metrics.py` (chỉ đọc lại dùng nguyên văn).

## 0. Cổng an toàn

- **Holdout 2026**: mọi sim chạy `SIM_END_DATE=20251231`; CSV regime `regime_daily_breadth.csv` chỉ phủ
  tới `2025-12-31` (lead-in từ `2021-06-01`). Không đụng seal 2026.
- **Cổng OFF byte-identical**: PASS, nhưng có 1 lần sửa lỗi thực thi cần ghi rõ (không hồi tố):
  - Lần chạy `OFFCHECK` đầu tiên (`X1_C3_FULL_2021_REGIME_BR_OFFCHECK`, `TRADING_PROFILE=x1_gs_t170.properties`,
    `SIM_GATE_REGIME_ADAPTIVE` không bật) cho md5 `495954e140ec66443c70b4cc5bcbc5ff` (941 dòng) — **KHÁC**
    md5 tham chiếu bắt buộc `efb793e2468ca3a7318da0f0ad23d4fc`.
  - Chẩn đoán: script runner mới `run_breadth_gate.sh` copy `config.properties` từ
    `configs/sim_dev_file.properties` (file dùng chung cho họ tag khác, `TIME_RUN=20220101`), trong khi
    họ tag `..._2021` (bao gồm `X1_GS_T170_2021` tham chiếu) dùng `TIME_RUN=20210701`. Đây là lỗi cấu hình
    runner, không phải lỗi Java/gate.
  - Sửa: thêm `sed -i 's/^TIME_RUN=.*/TIME_RUN=20210701/' config.properties` vào `run_breadth_gate.sh`
    ngay sau bước copy config, TRƯỚC khi thấy kết quả đúng.
  - Chạy lại `OFFCHECK`: md5 = `efb793e2468ca3a7318da0f0ad23d4fc`, n=1089 dòng — **khớp tuyệt đối** với
    `X1_GS_T170_2021/storage/printDone.csv` tham chiếu. **Cổng OFF: PASS.**
- **shadow-c3**: dừng trước chuỗi sim, bật lại ngay sau, verify sạch log:
  - `sudo systemctl stop shadow-c3` lúc **17:50:59 → Stopped 17:51:00** (+07, 2026-09-21).
  - Chuỗi sim: T170 OFF-verify (lặp lại sau fix) → BR → BR0 (tuần tự, mỗi lần kiểm `free -g`≥12G và
    `pgrep -af "Simulator|ExportWfo|s1_hpo|xgboost"`/`pgrep java` rỗng trước khi chạy).
  - `sudo systemctl start shadow-c3` lúc **18:51:17** → log `[SHADOW] so vi the giay khoi tao,
    ledger=/home/ubuntu/shadow_c3/ledger.csv ... open=12 realized=1535.13 paperEquity=35000.0` xuất hiện
    18:51:31 — ledger reload đúng, không mất trạng thái.
  - Downtime shadow-c3: **~60 phút 18 giây** (17:51:00 → 18:51:17).
  - Log sau khi bật lại (18:51 → 19:00): chỉ có `-2015` (Invalid API-key/IP whitelist — lỗi phụ đã biết,
    kèm 1 `NullPointerException` liên đới, đúng pattern cũ) và **KHÔNG có `-2014`**. Sạch theo tiêu chuẩn.
- **git**: không push/checkout/reset trong suốt quá trình; `.git/index.lock` không gặp phải lần nào.
- **Diff Java**: `git diff --stat -- '*.java'` = rỗng (0 dòng thay đổi) — xác nhận trước và sau toàn bộ round.

## 1. Bảng chính (metrics `breadth_gate_metrics.py`, đọc nguyên văn hàm của `bigdown_struct.py`/`c3_rates.py`)

| tag | n lệnh | n_eff_total | ICC(ROI, ngày) | maxDD% | UW (ngày) | CAGR% | equity |
|---|---:|---:|---:|---:|---:|---:|---:|
| T170 (`X1_GS_T170_2021`, tham chiếu) | 1089 | 606.26 | 0.0516 | -11.844 | 92 | 29.27 | 111,070 |
| T100/gate-1.0 (`X1_C3_FULL_2021`) | 2559 | 1103.86 | 0.1016 | -16.129 | 248 | 31.94 | 121,770 |
| **BR** (`X1_C3_FULL_2021_REGIME_BR`) | 1582 | **741.83** | 0.0827 | -11.842 | **180** | 30.12 | 114,410 |
| BR0 (control, `X1_C3_FULL_2021_REGIME_BR0`, g0=1.39) | 1429 | 641.19 | 0.0918 | -13.220 | 221 | 30.12 | 114,416 |

CAGR CI95 (bootstrap block-72h, `cagr_ci_t170.py --k 2`, k=2 vì 2 biến thể BR/BR0 kiểm cùng round):

| tag | CAGR% | CI95 | CI95_inflated(k=2) |
|---|---:|---|---|
| BR | 30.123 | [16.081, 46.156] | [13.413, 48.824] |
| BR0 | 30.124 | [15.905, 47.496] | [13.102, 50.299] |

(CI-floor T170 khoá trước ở PREREG = 14.80%. Ghi chú: điểm CAGR của BR (30.12%) vượt xa ngưỡng 14.80% —
u2 PASS theo đúng công thức đã khoá (so điểm CAGR với ngưỡng cố định) — nhưng cận dưới CI95_inflated(k=2)
của chính BR = 13.413% lại thấp hơn 14.80% một chút, tức khoảng tin cậy riêng của BR không tách biệt hẳn
khỏi vùng nhiễu ở mức inflation k=2. Đây là bối cảnh bổ sung, KHÔNG làm đổi verdict u2 vì công thức khoá
trước không yêu cầu so CI của BR với 14.80%.)

### UW theo năm (ngày âm liên tục dài nhất TRONG từng năm riêng)

| tag | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---:|---:|---:|---:|---:|
| T170 | 37 | 72 | 63 | 92 | 52 |
| T100/gate-1.0 | 47 | 64 | 45 | 121 | 227 |
| **BR** | 46 | 72 | 63 | 121 | **58** |
| BR0 | 27 | 109 | 44 | 119 | 221 |

### CAGR theo năm (%)

| tag | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---:|---:|---:|---:|---:|
| T170 | 12.21 | 19.58 | 34.96 | 32.06 | 32.71 |
| T100/gate-1.0 | 9.28 | 17.31 | 60.43 | 45.28 | 16.45 |
| BR | 4.20 | 19.59 | 47.01 | 45.17 | 22.92 |
| BR0 | 8.70 | 15.75 | 42.66 | 30.62 | 39.42 |

## 2. Khẩu vị hiện hành THEO NĂM (`x1_rates.py --appetite current --k 2`, ngưỡng maxDD≤30%, UW≤200,
năm không âm, quý≥-15%)

| tag | 2021 | 2022 | 2023 | 2024 | 2025 | Tổng kết |
|---|---|---|---|---|---|---|
| T170 | PASS | PASS | PASS | PASS | PASS | **PASS cả 5 năm** |
| T100/gate-1.0 | PASS | PASS | PASS | PASS | **FAIL** (UW=227>200) | FAIL 2025 |
| **BR** | PASS | PASS | PASS | PASS | **PASS** (UW=58) | **PASS cả 5 năm — LẦN ĐẦU TIÊN qua 7 vòng thử regime** |
| BR0 | PASS | PASS | PASS | PASS | **FAIL** (UW=221>200) | FAIL 2025 |

Chi tiết 2025: T100 maxDD=-10.60% UW=227 ret=16.45% quý_min=-2.47% → FAIL (chỉ vì UW). BR0 maxDD=-6.72%
UW=221 ret=39.42% quý_min=1.60% → FAIL (chỉ vì UW). **BR maxDD=-5.76% UW=58 ret=22.92% quý_min=-0.36% →
PASS toàn bộ 4 tiêu chí.** BR là biến thể regime ĐẦU TIÊN (trong 7 vòng, kể cả round Bước 2/4 trước đó)
đưa UW-2025 xuống dưới ngưỡng 200 — và không phải sát ngưỡng mà rất sâu (58 ngày, bằng 25.5% của T100 và
26.2% của BR0 cùng năm).

## 3. Đánh giá u1–u5 (công thức khoá ở PREREG §3)

| # | Tiêu chí | Ngưỡng | Giá trị BR | Kết quả |
|---|---|---|---|---|
| u1 | breadth: n_eff_total(BR) ≥ 1.5× n_eff_total(T170) | ≥ 909.38 | 741.83 (×1.224) | **FAIL** |
| u2 | khẩu vị `current` PASS mọi năm + CAGR(BR) ≥ CI-floor T170 (14.80%) | 5/5 năm PASS, CAGR≥14.80% | 5/5 PASS, CAGR=30.12% | **PASS** |
| u3 | vs T170: maxDD(BR) ≥ -14.805% AND UW(BR) ≤ 115 | cả 2 | maxDD=-11.842% (PASS) và UW=180 (FAIL, >115) | **FAIL** |
| u4 | nhắm đúng: UW(BR) < UW(BR0) toàn kỳ AND UW_2025(BR) < UW_2025(BR0) | cả 2 | 180<221 (PASS) và 58<221 (PASS) | **PASS** |
| u5 | giữ uptrend: CAGR 2023 & 2024 BR ≥ 90%×gate-1.0(T100) | 2023≥54.39%, 2024≥40.75% | 2023=47.01% (FAIL), 2024=45.17% (PASS) | **FAIL** (do 2023) |

**THẮNG = cả 5 pass → KHÔNG đạt.**
**NULL = u1 fail HOẶC u2 vỡ HOẶC BR0≈BR ở u4 → u1 FAIL đơn lẻ đã kích hoạt NULL** (dù u2 PASS toàn phần
lần đầu tiên, và u4 PASS rõ ràng, không phải BR0≈BR).

## 4. Phán quyết: **NULL** (nhưng là NULL có cấu trúc mới, khác hẳn 6 lần NULL trước)

Theo quy tắc đã khoá trong PREREG, chỉ cần u1 fail là đủ để verdict = NULL, bất kể u2–u5. Kết quả round
này đúng là NULL theo nghĩa đó: **n_eff_total(BR) chỉ đạt ×1.224 lần T170, không tới ngưỡng ×1.5 đã khoá**
— tức gate breadth (not_up 72.3% thời gian trong cửa sổ sim, xem `docs/PREREG_BREADTH_GATE_SIM.md`) đóng
quá thường xuyên, số lệnh hiệu dụng độc lập không đủ lớn để kết luận "vượt trội" theo tiêu chuẩn thống kê
đã đặt ra trước.

Tuy nhiên cấu trúc thất bại của round này **khác về chất** so với 6 lần NULL trước (Bước 2 R/R0, Bước 4
gate-adaptive up1.0-1.2, và các định nghĩa B/C ở Bước 5.3):
- Đây là **lần ĐẦU TIÊN u2 (khẩu vị `current` PASS mọi năm, đặc biệt UW-2025≤200) đạt trọn vẹn** — các
  round trước đều NULL/FAIL ngay ở u2 (UW-2025 luôn >200, thường 220-350+ ngày). BR đưa UW-2025 xuống 58
  ngày — vượt xa dự đoán "có thể lần đầu về ≤200" trong PREREG, không phải chỉ vừa lọt ngưỡng.
- **u4 PASS rõ ràng và mạnh** (UW BR=180 vs BR0=221 toàn kỳ; UW-2025 BR=58 vs BR0=221 — chênh lệch gần
  4 lần) — bằng chứng breadth-regime **nhắm đúng** thời điểm rủi ro thực sự (UW-2025 của thị trường), chứ
  không chỉ đơn thuần giảm rủi ro bằng cách khoá gate nhiều hơn theo tổng thời gian (BR0 dùng đúng cùng
  một gate cố định 1.39, khớp tổng số lệnh với BR, nhưng KHÔNG giảm được UW-2025 tương ứng — 221 ngày,
  gần bằng T100).
- Điểm nghẽn là **u1 (breadth/thống kê)** và **u3 phần UW toàn kỳ** (180>115) và **u5 phần 2023** (CAGR
  2023 của BR=47.01% chỉ bằng 77.8% của T100, dưới ngưỡng 90%) — tức cái giá phải trả để mua được UW-2025
  thấp là: (a) n_eff không đủ lớn để thắng thống kê, (b) UW toàn kỳ (tổng hợp, không riêng 2025) vẫn cao
  hơn T170 gốc 96% (180 vs ngưỡng 115), (c) một phần lợi nhuận uptrend 2023 bị cắt do gate not_up chặn cả
  giai đoạn 2023 có breadth<50% dù giá vẫn đi lên cục bộ (not_up% 2023 = 66.0%, xem CSV regime).

## 5. Đối chiếu dự báo (PREREG §"DỰ BÁO CẢNH BÁO", khoá trước khi chạy)

| Dự báo | Kết quả thực tế | Đối chiếu |
|---|---|---|
| (i) not_up quá thường xuyên → n_eff không đạt ×1.5 | not_up=72.3% toàn cửa sổ sim; n_eff BR/T170=×1.224 | **Đúng như dự báo, xác nhận chính xác** |
| (ii) CAGR 2023/2024 có thể bị cắt do not_up chặn giai đoạn uptrend cục bộ | 2023: BR=47.01% < 90%×T100=54.39% → mất; 2024: BR=45.17% ≥ 90%×T100=40.75% → giữ được | **Đúng một phần** — chỉ 2023 bị mất, 2024 giữ được (không mất cả 2 năm như lo ngại tệ nhất) |
| (iii) UW-2025 "có thể lần đầu về ≤200" | UW-2025(BR) = 58 ngày | **Vượt xa dự báo** — không chỉ về ≤200 mà giảm rất sâu, mạnh nhất từng thấy qua 7 vòng thử regime |

## 6. Khuyến nghị

- **Không triển khai BR vào production** trong round này: verdict khoá trước là NULL do u1 fail — quy tắc
  chống dredging trong PREREG đã cấm mở biến thể mới (vd. up-gate 1.2 thay vì 1.0, hoặc ngưỡng khác 50%)
  trong CHÍNH round này: *"Nếu Bước 6 cho n_eff BR quá thấp (u1 fail vì notup thường xuyên) → đó là kết
  quả, KHÔNG mở biến thể up1.2/ngưỡng khác trong round này (chống dredging)."*
- Ghi nhận: đây là kết quả **gần nhất với THẮNG** qua toàn bộ 7 vòng thử nghiệm regime (Bước 2→6) — lần
  đầu tiên u2 pass trọn vẹn VÀ u4 pass rõ ràng đồng thời. Nếu Uni/MASTER muốn tiếp tục hướng breadth-regime,
  gợi ý hướng khảo sát cho MỘT round MỚI (PREREG riêng, không dredging trong round này):
  - Nới up-gate từ 1.0 lên giá trị trung gian (vd 1.1-1.2) để tăng n_eff mà vẫn giữ được phần lớn hiệu quả
    nhắm UW-2025 của not_up=1.7.
  - Hoặc nới ngưỡng breadth từ 50% lên cao hơn một chút (giảm % thời gian not_up) — đánh đổi giữa n_eff và
    độ chọn lọc.
  - Cả hai hướng đều cần PREREG mới, độc lập, với u1-u5 (hoặc bộ tiêu chí điều chỉnh) khoá lại trước khi
    chạy, để không vi phạm nguyên tắc chống dredging đã áp dụng nhất quán qua các round trước.

## 7. Thay đổi code (0 diff Java)

File mới (chưa từng có), tất cả trên nhánh `module`, không sửa file cũ nào đã liệt kê ở BƯỚC 0:

- `research/analysis/breadth_regime_csv.py` — sinh CSV regime causal từ định nghĩa A đã khoá (top-50/MA200
  trailing/ngưỡng 50%), chỉ import + dùng nguyên văn hàm của `breadth_regime.py`/`trend_rank_ic.py`, không
  sửa 2 file đó. Output: `/home/ubuntu/regime_work/regime_daily_breadth.csv` (1675 dòng, lead-in
  2021-06-01 → 2025-12-31; not_up trong cửa sổ sim 2021-07-01→2025-12-31 = 72.3%).
- `profiles/x1_c3_full_regime_br.properties` — profile BR: `SIM_GATE_REGIME_ADAPTIVE=1`,
  `SIM_REGIME_FILE=.../regime_daily_breadth.csv` (up=1.00 mặc định `EntryGate.REGIME_SCALE_UP`, not_up=1.70
  final `REGIME_SCALE_NOTUP` — không cần override `SIM_REGIME_SCALE_UP` vì khớp mặc định).
  - `profiles/x1_c3_full_regime_br0.properties` — profile control BR0: `SIM_GATE_DYN_SCALE=1.39` (gate cố
    định, nội suy log-tuyến tính khoá trước trong PREREG để khớp tổng số lệnh với BR: n(T100,g=1.00)=2559,
    n(T170,g=1.70)=1089 → b=(ln1089-ln2559)/0.70, a=ln2559-b·1.00 → mục tiêu n≈1582 (n thực tế BR) → g0=1.39
    (làm tròn 2 số thập phân, trong [0.50,2.00]).
- `research/pipeline/x1/run_breadth_gate.sh` — runner 3 lệnh `OFFCHECK|BR|BR0`, theo mẫu `run_flatgate.sh`
  Bước 2, có sửa lỗi `TIME_RUN=20210701` (xem §0) so với bản nháp đầu.
- `research/analysis/breadth_gate_metrics.py` — tính u1/u3/u4 (raw metrics), dùng nguyên văn hàm của
  `bigdown_struct.py` (`icc_for`, `n_eff`, `maxdd_decomp`, `label_trades`, `build_bd_flags`,
  `load_trades_utc`, `hourly_grid`) và `c3_rates.py` (`equity`, `stats`) — không sửa 2 file gốc. u2/u5 tính
  riêng bằng `x1_rates.py --appetite current --k 2` (không lặp lại logic ở đây).
- `research/analysis/out/breadth_gate_metrics.json` — output số liệu đầy đủ (n_eff, maxDD, UW, CAGR theo
  năm, uw_by_year, top10 worst days...) cho cả 4 tag T170/T100/BR/BR0.

Không sửa: `RegimeSchedule.java`, `EntryGate.java`, `breadth_regime.py`, `regime_build_ma200.py`,
`bigdown_struct.py`, `x1_rates.py`, `regime_updown_metrics.py`, `c3_rates.py`, `cagr_ci_t170.py`.

---
Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01UoVRjusfNM2USSVNKQrm7z
