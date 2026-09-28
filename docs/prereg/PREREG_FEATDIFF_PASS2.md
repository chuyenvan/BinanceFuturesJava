# PRE-REG PASS 2 — DIFF 33 FEATURE: SO SÁNH **REGIME-MATCHED** (LIVE vs EXPORT DEV)

Trạng thái: **CHỐT TRƯỚC** khi nhìn bất kỳ thống kê Pass-2 nào. Tệp này **KHÔNG được sửa** sau khi có số.
Tiếp nối: `docs/result/RESULT_FEAT_DIFF_PASS1.md` (PASS 1) + `docs/result/RESULT_DEVEXPORT_202609_AUDIT.md`
(ghép 469 dòng / 385 phút, shift_sd thô — **chưa kiểm soát regime**).

> ## ⛔ 2026 VẪN LÀ HOLDOUT
> Toàn bộ 2026 (đặc biệt 2026-07 → 2026-09) **CHỈ dùng cho AUDIT / ĐỐI CHIẾU**. **TUYỆT ĐỐI KHÔNG** dùng để
> chọn/hiệu chuẩn ngưỡng, chọn tham số, chọn feature, hay bất kỳ quyết định thiết kế nào. **2026 CHƯA UNSEAL.**

## 0. VẤN ĐỀ PHƯƠNG PHÁP (lý do tồn tại Pass 2)

Cửa sổ LIVE (cuối 09/2026, ~1 ngày, BTCUSDT) nằm trong **1 regime thị trường**; cửa sổ DEV 2026-07→09 trải
nhiều regime. So **giá trị tuyệt đối** (shift_sd thô của PASS 1 / Audit) trộn **lệch do chế độ thị trường**
(lệch giả) với **lệch do pipeline/nguồn** (lệch thật). Pass 2 **bắt buộc kiểm soát regime** trước khi kết luận.

## 1. NGUỒN DỮ LIỆU (chốt trước)

| | đường dẫn | ghi chú |
|---|---|---|
| LIVE shadow | `/home/ubuntu/shadow_c3/app/feat_dump/feat_dump_*.csv.gz` | 36 cột = `ts,symbol` + 33 feat + `p15_out` |
| LIVE 242 | `/home/chuyennd/java/v_t_m/feat_dump/feat_dump_*.csv.gz` | qua ssh read-only (-p 2222, key id_rsa_chuyennd) |
| EXPORT DEV (2026-07→09) | `~/claudedata/devexport_202609/devexport_20260701_20260928_FULL.csv.gz` | 129.137 dòng, 36 cột, sha256 `3c328e54…` |
| DEV dài (regime mẫu) | `~/claudedata/gate15m_v2_full.csv` | 2021→2026-06, dùng làm **tham chiếu regime**, KHÔNG ghép cặp |
| funding LIVE dùng | **Aerospike `103.157.218.242:3222` ns `ticker`** set `funding_data` | xác nhận từ `~/shadow_c3/app/config.properties` (`AEROSPIKE_HOST=103.157.218.242`, `AEROSPIKE_NAMESPACE=ticker`) |
| market_data_object | local `127.0.0.1:3222` ns `test` / 226 `161.118.212.3:3222` ns `test` | **mới nhất 2026-08-13** ⇒ thiếu 08-14→nay |

## 2. GIẢ THUYẾT (chốt trước)

- **H_regime (đối chứng):** phần lớn lệch thô của PASS 1/Audit là **do regime** ⇒ sau regime-match sẽ **tắt**
  (|d| giảm mạnh).
- **H_true (cần tìm):** tồn tại feature **còn lệch sau khi regime-match** ⇒ lệch **thật** do pipeline/nguồn/đơn vị.
- **H_cutduoi:** feature nào trong nhóm dẫn dắt **đuôi dưới p15** (PASS 1 §4: `momentumAcceleration`,
  `momentum15M`, `momentum1M`, `volatility1H/15M/24H`) mà **còn lệch thật** ⇒ nghi phạm số 1 gây p15 live bị cut.

## 3. PHƯƠNG PHÁP SO SÁNH REGIME-MATCHED (chốt trước)

Với **mỗi feature trong 33** (không gồm `volatilityRegime`):

- **(a) Rank/percentile TRONG chính cửa sổ** (không so tuyệt đối): với mỗi cửa sổ (live, DEV) tính biến thể
  `x → pct(x)` theo CDF nội bộ cửa sổ đó; so `mean(pct_live)` vs `mean(pct_dev)` và `sd`. Chỉ số:
  `rank_shift = mean(pct_live) − mean(pct_dev)` (đơn vị: phân vị). Cờ lệch-hình-dạng: `spearman < 0.9`.
- **(b) Ghép cặp LIVE↔DEV **cùng regime**:** biến regime `R` = **decile của `volatility24H`** tính trên **pool
  chung** (live ∪ DEV); (biến thể phụ: decile của `btcDominance`). Với mỗi dòng live, đối chiếu với **các dòng
  DEV trong CÙNG decile `R`**. Chỉ số chính:
  - `d_matched_sd = |mean_live(R) − mean_dev(R)| / sd_dev(R)`, lấy **trung bình có trọng số theo số dòng live mỗi decile**;
  - `n_matched` = số dòng live có ít nhất 1 dòng DEV cùng decile.
- **(c) Cùng thời điểm trong ngày (same hour):** giới hạn thêm đối chiếu về **cùng `hourOfDay`** để loại yếu tố
  phiên giao dịch; lặp lại (b) trên tập `R ∩ hour`, báo `d_matched_sd_hour`.

**Nhánh xử lý khi thiếu dữ liệu (chốt trước):** decile nào không có dòng DEV ⇒ loại khỏi trung bình trọng số và
**ghi rõ số decile bị loại** (không được ngầm bỏ). Nếu `n_matched < 300` ⇒ không kết luận cứng cho feature đó.

## 4. NGƯỠNG + LUẬT KẾT LUẬN (chốt trước; không đổi sau khi thấy số)

**Ngưỡng nghi ngờ (mỗi feature):**
- `|d_matched_sd| > 0.5` **VÀ** `n_matched ≥ 300` ⇒ **lệch có kiểm soát regime** (lệch THẬT).
- `|rank_shift| > 0.10` (phân vị) ⇒ lệch vị trí theo rank.
- `spearman_matched < 0.9` (chỉ khi có cặp cùng decile ≥ 300) ⇒ lệch hình dạng.
- `std_live == 0` (hằng số) ⇒ feature chết; `NaN-rate_live > 1%` ⇒ nghi thiếu nguồn.

**Kết luận (chốt trước):**
1. **Nghi phạm CHỐT** = các feature có `|d_matched_sd| > 0.5 & n_matched ≥ 300` (đã loại regime) — xếp hạng
   giảm dần theo `|d_matched_sd|`, kèm hệ số hiệu ứng và `n`.
2. **Lệch THẬT (không do regime)** ⇔ thỏa (1) **VÀ** có **cơ chế** (hằng số / sai đơn vị / bị kẹp / nguồn khác).
   Chỉ xếp "lệch thật" khi nêu được cơ chế; còn lại ghi "còn lệch, chưa rõ cơ chế".
3. **Feature khả dĩ nhất gây cut đuôi p15 live** = feature thỏa "lệch thật" **VÀ** nằm trong nhóm dẫn dắt đuôi
   p15 (PASS 1 §4) **VÀ** hướng lệch làm **biên độ p15 live nhỏ hơn** DEV (nén đuôi lên). Nêu cơ chế tuyến tính
   (feature × trọng số model → p15).
4. **Bước tiếp:** cần thêm bao nhiêu dòng live (mục tiêu ≥ 2.000 dòng / ≥ 7 ngày, nhiều regime) + có thể sửa
   ngay không (nếu biết nguồn sai) + **rủi ro khi sửa** (đụng ONNX/LIVE ⇒ cần owner duyệt).
5. Nếu **không** feature nào vượt ngưỡng (1) ⇒ lệch PASS 1/Audit **chủ yếu do regime** ⇒ nghi (ii) model/store gốc.

## 5. RANH GIỚI (CỨNG)

- **CHỈ ĐỌC** trên Oracle + 242 (không ghi/sửa/restart/kill; không đọc key). Không chạy Java/sim/WFO.
- Nặng ⇒ chạy **Kaggle/local**; **giữ box Oracle NHẸ** (shadow đang chạy). Python nhẹ local được phép.
- **KHÔNG** chạm ONNX / `NUM_FEATURES` / `extractFeatures45` / đường LIVE.
- **KHÔNG** push file dữ liệu lên git (chỉ code/doc). `git push` code/doc được phép. Commit **sớm** + push.
- `df -h /` ~93% ⇒ file nhỏ, dọn ngay. Output tool **rất nhỏ** (≤ ~60 dòng/file).
- **2026 = AUDIT-ONLY, vẫn HOLDOUT** — không dùng cho ngưỡng/tham số/thiết kế.

## 6. GHI KẾT QUẢ Ở

`docs/result/RESULT_FEATDIFF_PASS2.md` (+ `docs/result/RESULT_FEATDIFF_PASS2.json` nhỏ). Mục "bỏ / lý do" khai RÕ.
