# PREREG_FUNDING_FACTOR — funding rate như (a) FACTOR cross-section và (b) THÀNH PHẦN CHI PHÍ

Chốt: **2026-09-22, TRƯỚC khi chạy bất kỳ phép đo nào.** Commit file này phải có TRƯỚC mọi commit
script/kết quả (đúng `docs/AGENT_RUNBOOK.md` luật 2; thứ tự commit ngược ⇒ kết quả **VOID**). Sau khi
chạy **KHÔNG sửa thiết kế** (grid lấy mẫu, decile, HOLD, phí, cổng thống kê, số rep, seed, K).

## 0. Vì sao + câu hỏi phải trả lời

Hệ thống là **LONG-ONLY perp** ⇒ **funding dương = CHI PHÍ** khi giữ lệnh, **funding âm = THU NHẬP**.
Funding hiện là **số hạng chi phí có mặt trong mọi mô phỏng** (`FundingFeeManager`, cache
`symbol -> TreeMap<time, rate>`, dùng ở `SimulatorMarketLevelTicker1MStopLoss:1483`) nhưng **chưa bao
giờ được đo như một nhân tố**.

Tiền lệ phải đối chiếu: `docs/SURVEY_OLDCODE_SIGNALS.md` ghi rule cũ `FUNDING_FEE_BUY` đã chuyển sang
ML `funding_selector` và **ĐÃ ĐO → FAIL (WFE med 0,098)**. Đây **không** phải chạy lại rule ngưỡng cũ;
đây là **cách đặt vấn đề khác**: (a) funding như **factor cross-section**, (b) funding như **thành phần
chi phí** định lượng được. Kết quả của vòng này phải viện dẫn và **dẫn chiếu** tiền lệ đó.

Ba câu hỏi:

- **H1 (CHI PHÍ / persistence)** — funding tại lúc vào lệnh là thành phần chi phí: coin có funding
  **dương cao** có thật sự tốn kém hơn (funding tích luỹ qua thời gian giữ lớn hơn) không, và **tổng
  net** (đã trừ phí + slip + funding) có xấu hơn theo decile funding không?
- **H2 (FACTOR cross-section)** — xếp hạng funding tại từng mốc funding: coin funding **thấp/âm** (Q1)
  có forward return tốt hơn phần còn lại **theo hướng long-only dùng được** không?
- **H3 (OVERLAY lên MOM15)** — funding tại entry có **tách được lệnh thắng/thua** của MOM15 không?
  (đây là cái quyết định, khớp phát hiện "edge nằm ở TIMING": `RESULT_F4_TIMING.md`,
  `DIAG_ENTRYGATE_PRED15M_REGIME.md`).

## 1. Ràng buộc (bắt buộc)

- **KHÔNG** `claude-run` / Claude Code. **KHÔNG** chạy Java trên Oracle (đang có job shadow).
  **THUẦN PYTHON**: đọc `raw/<sym>.f32` + Aerospike set `funding_data` (**chỉ ĐỌC**).
- **KHÔNG chạm HOLDOUT 2026** (cắt ≤ `2025-12-31`).
- **KHÔNG push.** Pre-reg này commit TRƯỚC; sau khi chạy không sửa thiết kế. Dọn file tạm sau khi chốt.
- **KHÔNG tự tích hợp** bất kỳ thứ gì vào hệ thống (mọi đề xuất nếu có chỉ là đề xuất + cờ default OFF).

## 2. BUOC 0 — kiểm dữ liệu TRƯỚC thiết kế (đã chạy, ghi vào đây)

Script `research/analysis/funding_coverage.py` (chỉ đọc, chỉ thống kê coverage), kết quả
`/tmp/funding_factor/coverage.csv`:

| Mục | Kết quả |
|---|---|
| Nguồn | Aerospike `test.funding_data`, bin `f_data` = **Snappy(JSON {ts_ms: rate})** (khớp `DataManagerAerospikeFloatSim.writeFundingMap`) |
| Namespace/set | `test` / `funding_data` (`AEROSPIKE_SET_NAME_FUNDINGFEE`) |
| Số symbol | **831** record, decode OK **831/831**, fail 0 |
| Số event | **2 394 587** (min 2, median 2 754, max 9 040/symbol) |
| Khoảng thời gian | 2021-01-01 00:00 UTC → **2026-08-05** (dùng ≤ 2025-12-31) |
| Tần suất | **hỗn hợp 4h và 8h**: 476 symbol cadence trung vị 4h (00/04/08/12/16/20 UTC), 345 symbol 8h (00/08/16 UTC); BTC/ETH/SOL 8h suốt 2021–2025 |
| Key format | `symbol` (userKey), value = blob `f_data` |
| Bản ghi rác | 3 symbol có ts = 0 hoặc âm (`GAIBUSDT`, `GRAMUSDT`, `STPTUSDT`) ⇒ **lọc `ts ≥ 2021-01-01`** |
| Đơn vị | rate thập phân (vd 0,00009642 = 0,009642%/kỳ); funding dương = long TRẢ |

⇒ **Dữ liệu ĐỌC ĐƯỢC**, đủ dài, đủ symbol. **TIẾP TỤC** (không rơi vào nhánh DỪNG).

Kiểm chứng phụ (đã chạy, ghi trước khi đo): `raw/` có **627 file** `<sym>.f32` (1 nến 1 phút/dòng:
`int32 epoch_minute + float32 O/H/L/C/V`, UTC, 2021-01-01..2025-12-31), giao với funding_data là
627 symbol (subset của 831).

## 3. Cửa sổ mẫu

| Nhãn | Cửa sổ (entry) | Vai trò |
|---|---|---|
| **DEV** | `[2022-01-01, 2026-01-01)` = 2022-01 → 2025-12 | **CHÍNH (headline)** |
| **ALL** | `[2021-01-01, 2026-01-01)` = 2021-01 → 2025-12 | **PHỤ** (gồm 2021 ⇒ không sạch bằng DEV) |

Kết luận **chỉ dựa trên DEV**; ALL để đối chiếu. Cảnh báo ghi trước: 2021 là bull/alt-season mạnh
(đã thấy ở mọi vòng trước) nên ALL có thể dương giả.

## 4. Harness TÁI SỬ DỤNG NGUYÊN (không đổi — để so được với các vòng trước)

| Thành phần | Giá trị (KHOÁ) |
|---|---|
| Nguồn giá | `raw/<sym>.f32` (627 USDT-perp, 1 nến 1M/dòng, chỉ nến **đã đóng**, UTC, 2021-01-01..2025-12-31) |
| Nguồn funding | Aerospike `test.funding_data` (**chỉ đọc**), cadence thực tế 4h/8h hỗn hợp |
| Entry | `close(m_e)`, `m_e` = phút của mốc funding (xem §5) |
| Exit | `close` của nến cuối có dữ liệu trong `(m_e, m_e+HOLD]`; nếu nến đó ≤ nến entry ⇒ `short_delist=1` (**GIỮ**); `m_e+HOLD > 2025-12-31 23:59` ⇒ **edge-censored, LOẠI** |
| HOLD | `{240, 1440, 4320}` phút (4h/24h/72h). **HOLD chính = 1440 (24h)** — khớp live & neo MOM15 |
| Phí (exchange) | `{0.05%, 0.10%, 0.15%}` round-trip. **Phí exchange ≠ funding** (không đếm hai lần) |
| Slippage | `0.5 × (high(m_e) − low(m_e)) / entry` |
| Funding tích luỹ | `f_cum = cum[hi] − cum[lo]` với `lo = searchsorted(ft, m_e·60000, 'right')`, `hi = searchsorted(ft, m_x·60000, 'right')`, `ft` = mảng ts event (ms), `cum` = tổng luỹ kế rate ⇒ **cộng các event có `ts ∈ (m_e·60000, m_x·60000]`** |
| **net** | `net = raw − phí − slip − f_cum` (long: funding dương ⇒ trừ; funding âm ⇒ cộng) |
| CI | block-bootstrap **block = 72h** (`entry_ts // (72·60)`), **2000 rep**, **seed 20260905**, percentile 2,5/97,5, nửa-độ-rộng **×1,21** ⇒ `CI72h×1.21`; báo kèm `p(mean>0)` |
| Null | block **sign-flip** 72h, 2000 rep, seed 20260905 ⇒ `p(≥obs)` |
| ICC | theo ngày entry (GMT+7, `entry_ts+420`) và theo block 72h |
| Decay | theo năm (GMT+7) |
| N vs N_eff | `N` = số mẫu; `N_eff` = số **block 72h** khác nhau (funding event **cụm theo thời điểm** ⇒ N_eff mới là lực thật) |

## 5. Grid lấy mẫu + định nghĩa `f_entry` (KHOÁ)

### 5.1 Grid A (chính) — mẫu tại **mốc funding của từng symbol**

Một mẫu = một cặp `(symbol, T)` với `T` = **một event funding của chính symbol đó** trong cửa sổ.
`m_e = T // 60000` (phút). Chỉ nhận mẫu nếu nến `m_e` **tồn tại** trong `raw/<sym>.f32`.

**`f_entry` = rate của event funding cuối cùng có `ts ≤ m_e·60000`** (với mẫu này ⇒ chính là rate tại
`T`, tức **rate đã biết tại thời điểm vào lệnh**). Đây là **predictor**, KHÔNG phải số hạng PnL.

**Không đếm hai lần:** `f_cum` chỉ tính các event **sau** `m_e` (§4), nên event tại `T` **không** nằm
trong `f_cum`; nó chỉ dùng làm biến phân loại. Phí exchange là hằng số riêng.

### 5.2 Decile cross-section

Trong mỗi phút `m_e`, xếp hạng **tất cả symbol có mẫu tại `m_e`** theo `f_entry` tăng dần ⇒
`D1` (funding thấp nhất/âm nhất) … `D10` (funding cao nhất). Yêu cầu **≥ 50 symbol** trong phút đó,
nếu không ⇒ **bỏ phút đó**. Decile gán **một lần** (độc lập với tính hợp lệ của từng HOLD) để tránh
thiên lệch thành phần.

### 5.3 Grid B (robustness, DESCRIPTIVE) — chỉ mốc 8h-aligned (00/08/16 UTC)

Để mọi symbol cùng có mặt ⇒ kiểm tra kết quả H1/H2 không phải artefact của việc lẫn 2 cadence.
Báo riêng, **không** dùng để tuyên bố.

### 5.4 MOM15 (neo + nền của H3)

Sinh lại **đúng** chuỗi causal mà repo dùng (chép từ `PREREG_HARNESS_CONTROL.md` /
`research/analysis/level_sensitivity.py`): `rc = C/O−1`, `d15 = C/max(H,15)−1`,
`rd15 = rateDown15MAvg` = trung bình **bottom-k** của `d15` trong phút, `k = min(100, ⌊n·4/5⌋)`,
`n ≥ 50` (MIN_SYM); **fire**: `rd15 < −0,028`; **chọn**: `k=1` coin d15 thấp nhất, lock 1440 phút/symbol
(= `SMALL_DOWN_15M` live). Neo này **phải tái tạo được** số đã công bố (§7) — nếu không ⇒ **VOID**.

## 6. Giả thuyết, test khoá, K, cổng thống kê

**HOLD chính = 24h (1440).** 4h/72h = **descriptive**, không tuyên bố.

| # | Giả thuyết | Chuỗi thống kê | Hướng 1 phía |
|---|---|---|---|
| **T1** | H1: net giảm đơn điệu theo decile funding | với mỗi phút: `d(m) = mean_net(D10, m) − mean_net(D1, m)` (equal-weight trong decile) | `mean < 0` |
| **T2** | H2: subset long-only funding thấp có lãi sau chi phí | với mỗi phút: `mean_net(D1, m)` (bỏ phút không đủ 50) | `mean > 0` |
| **T3** | H3: tại **phút MOM15 fire**, funding tại entry tách được thắng/thua | **pool P-COIN MOM15** (mọi coin trong cross-section tại phút fire): 2 mẫu `G_lo = {f_entry ≤ 0}`, `G_hi = {f_entry > 0}`; đại lượng = `mean_net(G_lo) − mean_net(G_hi)` (bootstrap khối 2 mẫu) | `diff > 0` |

**K = 3** (đúng 3 test trên, cả 3 ở DEV, HOLD 24h, phí 0,10%). Ngưỡng: `α = 0,05`, Bonferroni
`p_B = 0,05/3 = 0,016667` (một phía); báo `CI72h×1.21` **và** `CI-Bonf3`.

**Cổng kết luận (KHOÁ):**
- **GO** cho một test ⟺ `CI72h×1.21` **và** `CI-Bonf3` đều nằm đúng phía 0, **VÀ** |hiệu ứng| ≥ **MDE**
  đo được của chính chuỗi đó (điều kiện thực nghiệm), VÀ **dấu nhất quán** ở 4h & 72h (descriptive),
  VÀ **≥ 60%** số phút có dấu đúng (one-sided sign consistency).
- **NO-GO** ⟺ CI chứa 0 **hoặc** vượt ngưỡng nhưng |hiệu ứng| < MDE (⇒ "không phân giải được", ghi rõ).
- **NULL** phải nói rõ là NULL, kèm MDE. Không có "gần đạt".

**Descriptive bắt buộc báo (không tính là test):**
1. Bảng theo decile (D1..D10): `raw`, `slip`, `f_cum`, `net` × HOLD — để tách **cơ học** (f_cum) khỏi
   **giá** (raw): `spread net = spread raw − spread slip − spread f_cum`.
2. `corr(f_entry, f_cum)` (Spearman) — persistence của funding (nền của H1).
3. IC cross-section (Spearman) `f_entry` vs `net` theo từng phút → trung bình + phân vị.
4. **H3b (low power, chỉ descriptive)**: trên **M-LEVEL MOM15 `k=1`** (đúng live): net của subset
   `f_entry ≤ 0` vs `> 0`; và net của MOM15 sau khi **lọc bỏ** `f_entry > 0`. Ghi rõ N≈7,1k DEV ⇒
   **MDE ≈ 2%** ⇒ test này **KHÔNG đủ lực** cho hiệu ứng ≲2%/lệnh (nói trước, không kết luận từ nó).
5. Đường MDE theo N và MDE của cả 3 test chính.
6. Null sign-flip 72h cho cả 3 test chính; ICC(ngày)/ICC(72h); `%coin+` (≥1/≥5/≥10 trade) và theo năm.
7. Grid B (8h-aligned) cho H1/H2.
8. ALL (đối chiếu) cho cả 3 test.

## 7. Kiểm chứng tái tạo (PHẢI khớp, nếu không ⇒ VOID)

| Kiểm chứng | Số tham chiếu đã công bố | Nguồn |
|---|---|---|
| `total_rows` cross-section `d15` | **619 073 711** | `RESULT_HARNESS_CONTROL.md` §1 |
| Phút MOM15 (`rd15 < −0,028`, `cnt ≥ 50`) | **13 150** (13 164 với `ok` rộng hơn) | `RESULT_LEVEL_SENSITIVITY.md` §0b |
| M-LEVEL MOM15 `k=1` ALL | **11 367** | `RESULT_LEVEL_SENSITIVITY.md` §0 |
| M-LEVEL MOM15 `k=1` DEV | **7 128** | idem |
| MOM15 M-LEVEL DEV, 24h, phí 0,10%, net | **+1,5931%** (1,6931% @0,05%) | idem §2 grid |
| MOM15 M-LEVEL DEV, 24h: N_blk | **301** | idem |

Nếu lệch ⇒ ghi rõ nguyên nhân (thường do `ok` chặt hơn) và **không dùng số lệch để kết luận**.

## 8. MDE + power — ghi trước khi biết kết quả

`MDE(80%)` = X nhỏ nhất trong lưới `{0,02; 0,05; 0,1; 0,2; 0,25; 0,5; 1; 2; 4}%` có `power ≥ 80%`,
với `h_r` = nửa-độ-rộng `CI72h×1.21` của chuỗi **center**. Kỳ vọng ghi trước:
- T1/T2 (grid A, N≈1,3–2,0 M, N_eff≈500 block) ⇒ kỳ vọng MDE **≲ 0,1%/lệnh** ⇒ phân giải được hiệu ứng nhỏ.
- T3 (P-COIN MOM15, N≈2,35 M, N_eff≈301) ⇒ kỳ vọng MDE **≈ 1–2%/lệnh**.
- H3b (`k=1`, N≈7,1k) ⇒ **MDE ≈ 2%/lệnh** ⇒ **thiếu lực**, chỉ descriptive.

## 9. Cách áp NẾU có GO (chỉ đề xuất, KHÔNG tự tích hợp)

Nếu và chỉ nếu một test GO: đề xuất ở `docs/RESULT_FUNDING_FACTOR.md` **kèm rủi ro + điều kiện**:
(i) **lọc** bỏ tín hiệu khi `f_entry > ngưỡng` (flag default **OFF**), (ii) **sizing** theo funding
(tỉ lệ nghịch với `f_entry`), (iii) **feature** cho gate/selector. Mọi phương án phải nêu
**parity gate** (Python↔Java), **pre-reg riêng** cho việc áp dụng, và **không** động vào live.

## 10. Artifacts

- Script: `research/analysis/funding_coverage.py` (Buoc 0), `research/analysis/funding_factor.py`
  (sinh mẫu + MOM15, lưu trung gian **ngoài repo**), `research/analysis/funding_factor_stats.py`.
- Trung gian: `/tmp/funding_factor/*.npz` (resume được), log `/tmp/funding_factor/*.log`.
- Kết quả: `docs/RESULT_FUNDING_FACTOR.md`. Commit pre-reg + script + kết quả. **KHÔNG push.**
- Dọn file tạm sau khi chốt số; **giữ** `pools.npz`-style summary trong `/tmp` tới khi commit xong.

## 11. Multiplicity

K = 3 (T1/T2/T3) ⇒ Bonferroni 0,05/3. Các bảng 4h/72h, ALL, grid B, decile, IC, H3b là
**descriptive**; nếu bất kỳ ô nào trông "đẹp" mà không nằm trong 3 test khoá ⇒ **không được** tuyên bố.

## 12. Nhánh vô hiệu ghi trước

1. Funding decode fail / quá thưa ⇒ DỪNG (không xảy ra ở Buoc 0).
2. Không tái tạo được §7 ⇒ VOID, báo lỗi harness.
3. `N_eff` quá nhỏ (không tính được CI có nghĩa) ⇒ chỉ báo descriptive, không kết luận.

## 13. Dẫn chiếu tiền lệ (bắt buộc trong kết quả)

`docs/SURVEY_OLDCODE_SIGNALS.md`: `FUNDING_FEE_BUY` → ML `funding_selector` → **FAIL (WFE med 0,098)**.
Kết quả vòng này **phải** nêu rõ nó **nhất quán hay mâu thuẫn** với tiền lệ đó, và vì sao cách đặt
vấn đề khác (factor/chi phí, không phải rule ngưỡng).
