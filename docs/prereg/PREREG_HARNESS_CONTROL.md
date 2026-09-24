# PREREG_HARNESS_CONTROL — hiệu chuẩn BỘ ĐO (positive/negative control + MDE) trước khi tin bất kỳ kết luận NULL nào

Chốt: **2026-09-22, TRƯỚC khi chạy bất kỳ phép đo nào.** Commit file này phải có TRƯỚC mọi commit
script/kết quả (đúng `docs/runbooks/AGENT_RUNBOOK.md` luật 2). Sau khi chạy **KHÔNG sửa thiết kế** (trigger,
selection, HOLD, chi phí, cổng thống kê, số rep, seed).

## 0. Vì sao + câu hỏi phải trả lời

Sau một chuỗi kết quả **NULL** trên DEV (reversal-bounce NO-GO; BIG_UP/MEDIUM_UP/MEDIUM_DOWN
NO-GO), owner nghi ngờ "có gì đó không an tâm". Câu hỏi duy nhất cần trả lời:

> **Bộ đo của mình có PHÁT HIỆN ĐƯỢC một tín hiệu đã biết là CÓ THẬT không?**
> Nếu không ⇒ mọi kết luận NULL trước đây phải xét lại.

Ba phần: **A. positive control** (tín hiệu đã biết là thật), **B. negative control/placebo**
(hiệu ứng = 0), **C. power/MDE** (hiệu ứng nhỏ nhất DEV phát hiện được, %/lệnh).

## 1. Ràng buộc (bắt buộc)

- **KHÔNG** `claude-run` / Claude Code. **KHÔNG** chạy Java trên Oracle (đang có job shadow).
  **THUẦN PYTHON** (đọc `raw/*.f32` + Aerospike `funding_data` chỉ-ĐỌC). KHÔNG push.
- **DEV only** cho headline (định nghĩa §3). **KHÔNG chạm HOLDOUT 2026** (dữ liệu chặn ≤
  2025-12-31).
- Pre-reg này commit TRƯỚC; sau đó không sửa thiết kế.

## 2. Harness TÁI SỬ DỤNG NGUYÊN (không được đổi — để so sánh được với 2 vòng trước)

Toàn bộ dưới đây **chép nguyên** từ `docs/prereg/PREREG_REVERSAL_BOUNCE.md` §2/§3/§5 và
`docs/prereg/PREREG_BIGUP_MEDIUPDOWN.md` §2/§4 (hai vòng đã chạy):

| Thành phần | Giá trị (KHÓA) |
|---|---|
| Nguồn dữ liệu | Aerospike set `kline_1m_opt` (127.0.0.1:3222) đã extract causal ra `raw/<sym>.f32` (627 USDT-perp, 1 nến 1M/dòng `int32 epoch_minute + float32 O/H/L/C/V`, UTC, dải 2021-01-01..2025-12-31); chỉ dùng nến **đã đóng** ⇒ causal. Đây là **cùng nguồn** BD/MOM15 (SURVEY §1) |
| Funding | Aerospike set `funding_data` (chỉ đọc), per-symbol, 8h cadence; tổng rate trong `(m, exit]`; long trả funding dương |
| Entry | `close(m)` của nến 1M đã đóng |
| HOLD | **1440 phút (24h)**, không tune |
| Exit | close của nến có dữ liệu **cuối cùng** trong `(m, m+1440]`; nếu hụt ⇒ `short_delist=1` (GIỮ trong mẫu); nếu `m+1440` vượt nến cuối dải ⇒ **edge-censored, LOẠI** |
| Chi phí | taker `0.0005×2 = 0.10%` + slippage `0.5×(high(m)−low(m))/entry` + funding |
| net | `net = raw − 0.001 − slip − funding` |
| CI | block-bootstrap moving-block, **block = 72h** (`entry_ts // (72·60)`), **2000 rep**, **seed 20260905**, percentile 2.5/97.5, nửa-độ-rộng **×1.21** (`CI_INFLATE_LEGACY`) ⇒ `CI72h×1.21`; báo kèm `p(mean>0)` |
| Null test | block **sign-flip** permutation 72h, 2000 rep, seed 20260905 |
| ICC | `(MSB−MSW)/(MSB+(k0−1)·MSW)` theo ngày entry và theo block 72h |
| Decay | theo năm (nhãn ngày GMT+7 = `entry_ts+420`) |
| Universe | toàn bộ 627 symbol có file 1M (gồm coin delist — không lọc survivorship) |

**Cách chia DEV (đúng định nghĩa 2 vòng trước):** `DEV = entry_ts ∈ [2022-01-01 00:00 UTC,
2024-07-01 00:00 UTC)` = 2022-01-01..2024-06-30. `NON-DEV` = 2021 + 2024-07-01..2025-12-31.
Headline = DEV; ALL = 2021-2025 (chỉ để đối chiếu).

**Triggers/selection cấp độ (chép nguyên 2 vòng trước):** scalar cross-sectional tái tạo đúng
`calRateChangeAvg` (k = `min(100, ⌊n·4/5⌋)`, `n ≥ 50` symbol/phút); `d15_i(m) = close_i/max(high_i,
15 nến liền trước, gồm m) − 1`; `rateDown15MAvg(m)` = trung bình **k giá trị nhỏ nhất** của `d15`
trên toàn cross-section. Fire = mỗi phút 1M (không giới hạn mốc 15m — đúng nhịp live
`getMarketStatus1M`). Chọn symbol: xếp `d15` **tăng dần** (rớt sâu nhất trước), bỏ symbol đang
**lock**, lấy **k** coin; `lock` = sau khi fire `(m,s)` thì `s` khoá tới `m+1440` (abstraction ghi
trước, giống 2 vòng trước). Không áp gate/selector/sizing.

## 3. A. POSITIVE CONTROL — MOM15

**Định nghĩa MOM15 (đã grep repo TRƯỚC khi viết pre-reg này):** trong repo có 2 dạng:
1. Gate momentum 15m của HEAD = `tradecore/EntryGate` trên `predReturn15M` với `thrBase =
   Configs.MIN_MOMENTUM_15M = 0.02284f` (`Configs.java:392`) — đầu vào là **output model**, KHÔNG
   tính được thuần Python ⇒ không dùng.
2. Dạng **market-level** đã được repo thiết lập = `SMALL_DOWN_15M` = **`rateDown15MAvg < -0.028`**,
   gọi là "= MOM15 live" (`docs/analysis/SURVEY_OLDCODE_SIGNALS.md` §1–§2 bảng tín hiệu;
   `MarketLevelChange.SMALL_DOWN_15M`; 2 pre-reg trước §4/§3 dùng đúng dạng này).

**A dùng dạng (2)** (tính được causal từ chính `raw/*.f32`, cùng thước với 2 vòng trước):
fire tại phút `m` ⟺ `rateDown15MAvg(m) < -0.028` (finite) và `cnt(m) ≥ 50`.

- **A-PRIMARY**: `k = 1` (chọn 1 coin rớt 15M sâu nhất) — đúng `SMALL_DOWN_15M` live
  (`numberOrder = NUMBER_ENTRY_EACH_SIGNAL/2 = 1`, `DetectEntrySignal2TradeNormal.java:191-206`).
- **A-SECONDARY (descriptive)**: `k = 2` — so táo-với-táo với dòng BIG_UP/MEDIUM_UP/MEDIUM_DOWN
  của vòng trước (cùng luật chọn).

Cả hai đi qua **đúng harness §2** (long, HOLD 24h, trừ phí+slip+funding).

**Tiên lượng ghi trước:** net **DƯƠNG rõ rệt**, CI72h×1.21 **KHÔNG chứa 0**. Cơ sở: 2 vòng trước
đã đo phần "MOM15-firing" của BIG_UP/MEDIUM_UP/MEDIUM_DOWN cho edge dương lớn trên toàn dải
(+36.1% / +8.8% / +11.3%). Đây là **tiên lượng**, không phải kết luận.

**Cổng PASS của A (chốt trước):** A-PRIMARY có `mean(net) > 0` trên DEV **và** `CI72h×1.21 lo > 0`.
- Nếu **ĐẠT** ⇒ bộ đo phát hiện được tín hiệu thật; các NULL trước đây là "thật sự không thấy edge".
- Nếu **KHÔNG ĐẠT** ⇒ **báo RO ngay**, và kết luận: bộ đo có vấn đề hệ thống **hoặc** DEV thật sự
  thiếu hiệu ứng đó; mọi kết luận NULL trước đây **phải xét lại**. Để phân biệt hai khả năng, bắt
  buộc báo kèm: (i) số của A trên **toàn dải 2021-2025** và theo **từng năm**; (ii) A-SECONDARY;
  (iii) kết quả B-SECONDARY (§4) — nếu "cùng phút, symbol ngẫu nhiên" cũng ra edge dương lớn thì
  edge đó là **hiệu ứng thời điểm (market timing)** có thật trong dữ liệu và bộ đo tái tạo được.

## 4. B. NEGATIVE CONTROL (placebo) — 200 rep

**B-PRIMARY — "day-permute" (giữ symbol + giữ chính xác phút-trong-ngày, ngày ngẫu nhiên):**
Với mỗi event của A-PRIMARY (m_i, s_i): `off_i = m_i mod 1440` (giờ:phút UTC). Với rep r
(r = 1..200, seed = `20260905 + r`): chọn **ngẫu nhiên đều** một ngày trong DEV sao cho (i) nến 1M
của `s_i` tồn tại tại `m' = ngày + off_i`, (ii) `m' ∈ DEV`, (iii) `m'+1440 ≤ nến cuối dải`; nếu tập
hợp ngày hợp lệ rỗng → event đó không đóng góp (báo số bị loại). `m' = m_i` (shift 0) bị **loại**
khỏi tập hợp lệ. Sau đó chạy **đúng harness §2** (cùng symbol, cùng HOLD, cùng chi phí).
⇒ Mỗi rep có **đúng N = N_A_PRIMARY_DEV event**, **phân bố phút-trong-ngày khớp chính xác** MOM15,
**ngày ngẫu nhiên đều trên DEV**, cùng universe symbol.

**B-SECONDARY (descriptive) — "same-minute random symbol":** tại **đúng các phút event** của
A-PRIMARY, thay symbol bằng một symbol **ngẫu nhiên đều** trong tập candidate cùng phút (mọi symbol
có `d15` hợp lệ tại phút đó), 200 rep, cùng harness. Đây là **phép tách hiệu ứng**: B-SECONDARY
giữ **thời điểm**, bỏ **chọn symbol**; so với A-PRIMARY cho biết edge đến từ timing hay selection.

**Tiên lượng ghi trước:** B-PRIMARY `mean(net) ≈ 0` (không dương), CI72h×1.21 **chứa 0**.

**Đo (chốt trước):**
- `FP_1side` = % rep có `CI72h×1.21 lo > 0` (đúng nghĩa "báo nhầm edge DƯƠNG" — cùng cổng với cổng
  GO của 2 vòng trước). **Tiên lượng ≤ 5%.**
- `FP_2side` = % rep có CI **loại 0** (lo>0 hoặc hi<0). Báo kèm, và báo cả % `CI hi < 0`
  (drag chi phí làm mean placebo âm là **có thật**, không phải false-positive).
- Nếu `FP_1side` cao bất thường (>10%) ⇒ **báo RO: harness có vấn đề về kiểm định**.

## 5. C. POWER / MDE (minimum detectable effect), đơn vị **%/lệnh**

Trên **chuỗi placebo B-PRIMARY** (200 rep): với mỗi rep, dựng chuỗi có **mean đúng bằng X**:
`net_shift = (net − mean(net_rep)) + X`, quét `X ∈ {0.25%, 0.5%, 1%, 2%, 4%}`.
**Phát hiện** = `CI72h×1.21 lo > 0` (đúng cổng dùng cho A và cho cổng GO 2 vòng trước).
200 rep mỗi X ⇒ tỉ lệ phát hiện `power(X)`.
- **MDE** = X nhỏ nhất có `power ≥ 80%`. Nếu 4% chưa đạt 80% ⇒ báo `MDE > 4%`.
- **N tham chiếu của headline MDE** = `N_A_PRIMARY_DEV`.
- **Đường MDE theo N (chốt trước):** lặp cùng thủ tục trên chuỗi placebo **lấy mẫu con** (không
  hoàn lại, ngẫu nhiên, seed `20260905+r`) với `N ∈ {100, 200, 500, 1000, 2000, 5000, 20000,
  50000}` (bỏ N > N_placebo), 200 rep/N ⇒ đọc được MDE cho ứng viên có N khác.

**So sánh (chốt trước, lấy từ RESULT docs, không đo lại):**

| Ứng viên đã NULL | N (DEV) | net DEV đo được | nguồn |
|---|---|---|---|
| reversal-bounce long | 1 179 302 | **−0.080%** | `docs/result/RESULT_REVERSAL_BOUNCE.md` |
| BIG_UP (code cũ) | ~89 (tổng theo năm) | **+0.87%** | `docs/result/RESULT_BIGUP_MEDIUPDOWN.md` §3.1–3.2 |
| MEDIUM_UP (code cũ) | ~316 | **+1.84%** | nt |
| MEDIUM_DOWN (code cũ) | ~158 | **+1.25%** | nt |

(N của BIG_UP/MEDIUM_UP/MEDIUM_DOWN = tổng N theo năm 2022+2023+2024 trong bảng §3.2 của doc đó —
là **cận trên** cho DEV vì 2024 chỉ tính 6 tháng; ghi rõ nguồn, không đo lại.)

**Kết luận bắt buộc của C:** với mỗi ứng viên NULL, trả lời **"hiệu ứng đo được có NẰM DƯỚI MDE
không?"** ⇒ phân biệt **"DEV cần (thật sự không có edge)"** vs **"DEV thiếu power"**.

## 6. Kiểm chứng tái tạo (trước khi tin kết quả)

- `rateDown15MAvg < -0.028` phải chiếm **≈ 0.50% số phút** (số đã in ở
  `docs/result/RESULT_BIGUP_MEDIUPDOWN.md` §2) và phân bố `rateDownAvg/rateDown15MAvg` phải khớp lại
  (p50/p0 của `rateDownAvg` không đổi vì vòng này không cần `rateDownAvg`).
- B-PRIMARY phải có mean ≈ 0 và CI chứa 0; A-PRIMARY phải dương mạnh. Hai điều này **đối chứng
  nhau**: nếu cả A và B đều ~0, hoặc cả hai đều dương mạnh, phải dừng và báo RO (không tự sửa
  thiết kế giữa đường).

## 7. Artifact + tuân thủ

- Script: `research/analysis/harness_control.py` (sinh tín hiệu + placebo) và
  `research/analysis/harness_control_stats.py` (thống kê A/B/C). File tạm `/tmp/harness_ctl/`
  (dọn sau khi chốt số).
- Kết quả: `docs/result/RESULT_HARNESS_CONTROL.md` (bảng + số + kết luận A/B/C + MDE %/lệnh).
- KHÔNG `claude-run`; KHÔNG Java; không push; 2026 không đụng; sau khi chạy không sửa thiết kế.
