# PREREG_S1_NOISE_CAL — hiệu chuẩn đối chứng nhiễu (NOISE_CAL) cho vòng S1_HPO_BAG_FEATGRP

Chốt TRƯỚC khi xem bất kỳ số nào của noise_1..noise_4. Commit file này PHẢI đứng trước bất kỳ
cập nhật nào của `docs/result/RESULT_S1_HPO_BAG_FEATGRP.md` dựa trên kết quả NOISE_CAL; nếu ngược lại
kết quả VÔ HIỆU. Thiết kế do MASTER chốt; agent thực thi KHÔNG được đổi ngưỡng/công thức/nhánh
quyết định sau khi thấy số.

## 0. Bối cảnh

`docs/prereg/PREREG_S1_HPO_BAG_FEATGRP.md` Sec 5 quy định: nếu đối chứng nhiễu `noise_0` (thêm vào
KEEP-9 làm feature thứ 10) vượt ngưỡng `inflate(3) × sd_boot` trên cửa sổ SELECT thì DỪNG, coi
harness LỖI. Vòng chạy `full` (xem `/home/ubuntu/s1hpo/result.json`, `gate2.log`) cho:
P1/P2/P3 đều NULL trên CONFIRM, nhưng `noise_0` **vượt ngưỡng trên SELECT**:

| | giá trị |
|---|---|
| `select_mean_edge5` (noise_0) | −0.4574pp |
| `select_sd_boot_edge5` | 0.0016246 |
| ngưỡng `inflate(3) × sd_boot` | 0.0024082 |
| `select_exceeds_threshold` | **True** |
| `confirm_edge5_ci` (noise_0) | mean +0.127pp, CI chứa 0 (NULL) |

Theo luật Sec 5, vòng `full` đã DỪNG, chưa viết RESULT. MASTER nghi ngờ: control NÀY thiết kế
sai, không phải leak — `inflate(3) = sqrt(2·ln 3) = 1.4823σ` áp cho **một cột nhiễu đơn** là
ngưỡng ~86.1% two-sided (`2·Φ(−1.4823) ≈ 0.1382`), tức về mặt cấu tạo một cột nhiễu thuần có
xác suất ~13.8% bắn ngưỡng này chỉ do phương sai lấy mẫu (đặc biệt khi SELECT có mẫu nhỏ nên
`sd_boot` ước lượng không ổn định) — KHÔNG cần có leak/lỗi harness. NOISE_CAL đo trực tiếp giả
thuyết này bằng cách lặp lại phép đo trên 4 cột nhiễu độc lập khác.

## 1. Mục tiêu

Đo tỉ lệ dương-tính-giả (exceed-rate) của chính ngưỡng `inflate(3) × sd_boot` trên SELECT và
trên CONFIRM, dùng 5 cột nhiễu độc lập (kể cả `noise_0`), để phân biệt "control mis-calibrated
do bản chất thống kê của ngưỡng đơn-cột + mẫu nhỏ" khỏi "lỗi harness thật (leak/purge/join)".

## 2. Thiết kế

- **4 cột nhiễu mới bổ sung** `noise_1, noise_2, noise_3, noise_4` — uniform(0,1), độc lập theo
  từng dòng (`ts_h`, `sym`) của `feat_v2_x1.parquet`, giống hệt cách `noise_0` được sinh
  (`research/pipeline/x1/x1_feat_v2_build.py` dòng 108-109: `rng=np.random.default_rng(20260902)`
  rồi `for k in range(3): F[f"noise_{k}"]=rng.random(...)` — 3 draw TUẦN TỰ từ CÙNG MỘT stream
  seed `20260902`). Xác nhận thực nghiệm: `noise_0/1/2` đã sẵn có trong
  `/home/ubuntu/featv2/feat_v2_x1.parquet` (đo `corr(noise_0,noise_1)=-0.000089`,
  `corr(noise_0,noise_2)=+0.000282`, `corr(noise_1,noise_2)=-0.000029` — thực tế độc lập).
  ⇒ **Tái dùng `noise_1`, `noise_2` có sẵn** (seed nguồn `20260902`, cùng file feature, không
  sinh dataset mới) thay vì tạo cột trùng lặp không cần thiết.
  Sinh MỚI `noise_3` (seed **20260920**) và `noise_4` (seed **20260921**) — mỗi cột 1 draw
  `np.random.default_rng(seed).random(len(F), dtype=float32)` trên đúng tập dòng
  `(ts_h, sym)` của `feat_v2_x1.parquet`, merge vào `D` bằng đúng khoá `ts_h,sym` mà
  `load_D()` dùng cho mọi feature khác — KHÔNG ghi đè file `feat_v2_x1.parquet` gốc (giữ
  nguyên dataset, chỉ merge cột nhiễu tạm thời trong bộ nhớ của script NOISE_CAL).
- Mỗi cột nhiễu thêm riêng lẻ vào KEEP-9 làm feature thứ 10 (`FE = KEEP9 + [noise_i]`), train
  ĐÚNG pipeline `run_variant()` 18 fold (baseline hyperparameter §0.2 của
  `PREREG_S1_HPO_BAG_FEATGRP.md`, seed=42, KHÔNG đổi logic train/nhãn/purge — tái dùng nguyên
  hàm `load_D`, `run_variant`, `edge5_series`, `rankic_series`, `block_ci_diff`, `sd_boot`,
  `inflate`, `verdict` từ `research/analysis/s1_hpo_bag_featgrp.py`, import module, không copy
  sửa logic).
- **Baseline**: tái sử dụng `/home/ubuntu/s1hpo/pred_baseline18.parquet` đã có sẵn (seed 42,
  KEEP9, đã PASS tự-kiểm `spearman=1.0` trong `result.json.baseline18_selfcheck`) — ghép lại
  `g1lite` từ `D` (cùng `ts,sym`) và suy lại cột `fold` từ đúng 18 cửa sổ cutoff
  (`CUT_MS_18`/`CUTS18`, cùng công thức `lo,hi` trong `run_variant()`) — KHÔNG train lại baseline
  (tiết kiệm ~11 phút, không đổi kết quả vì cùng model/predictions).
- `Δedge5` = SELECT (fold 0-9, OOS 2021Q3→2023Q4) và CONFIRM (fold 10-17, OOS 2024Q1→2025Q4),
  đúng định nghĩa nested Sec 2.4 của `PREREG_S1_HPO_BAG_FEATGRP.md`.
- `sd_boot`/CI: block-bootstrap khối 72h, `NREP=2000`, seed `20260919` (dùng lại đúng seed cố
  định của toàn vòng, theo Sec 2.3 — không seed riêng theo cột nhiễu).
- **Ngưỡng dùng để đếm exceed trên SELECT**: `inflate(3) × sd_boot(Δedge5_SELECT)` — DÙNG ĐÚNG
  `k=3` như P3 dùng cho `noise_0` (không đổi thành `k=5`), vì mục tiêu là đo tỉ lệ bắn của
  CHÍNH ngưỡng đó (ngưỡng cố định, không phụ thuộc số cột nhiễu đang thử).
- **Ngưỡng dùng để đếm exceed trên CONFIRM**: CI hiệu chỉnh `inflate(3)` quanh tâm của
  `Δedge5_CONFIRM` (đúng công thức Sec 2.3/`block_ci_diff(k=3)`) — "exceed" = CI không chứa 0
  (tương đương định nghĩa THẮNG/THUA của `verdict()`).
- Gộp với `noise_0` (đã có từ vòng `full`) ⇒ **tổng 5 cột nhiễu độc lập**. Đếm số cột vượt
  ngưỡng trên SELECT (`select_exceeds_threshold=True`) và trên CONFIRM (`contains_zero=False`).

### Bảng seed (chốt trước khi chạy)

| cột | nguồn | seed |
|---|---|---|
| noise_0 | có sẵn `feat_v2_x1.parquet` | 20260902 (draw #0 của rng) |
| noise_1 | có sẵn `feat_v2_x1.parquet` | 20260902 (draw #1, cùng rng stream) |
| noise_2 | có sẵn `feat_v2_x1.parquet` | 20260902 (draw #2, cùng rng stream) |
| noise_3 | sinh mới trong script NOISE_CAL | **20260920** |
| noise_4 | sinh mới trong script NOISE_CAL | **20260921** |

Bootstrap CI (SELECT sd_boot + CONFIRM CI): seed `20260919`, `NREP=2000`, khối 72h — không đổi
theo cột nhiễu (Sec 2.3 pre-reg gốc).

## 3. Sanity bắt buộc mỗi cột (dừng nếu fail)

- Số tick OOS mỗi fold = baseline (cùng `D`, cùng cutoff).
- `score` không NaN/Inf (`n_bad_score=0`).
- `assert tr.ts.max() < c` (nguyên khối `run_variant()`, không tắt).
- Tập `ts` OOS của candidate trùng tuyệt đối tập `ts` của baseline (`assert set(...) == set(...)`
  nguyên như `eval_candidate()` gốc).
- `g1_replay` join-rate trong phạm vi coverage (`ts <= REPLAY_MAX_TS`) `>= 95%` (đúng Sec 2.5).

## 4. Cây quyết định pre-declare (ghi TRƯỚC khi chạy, KHÔNG đổi sau khi thấy số)

Gọi `n_select` = số cột (trong 5) có `select_exceeds_threshold=True`,
`n_confirm` = số cột (trong 5) có CONFIRM CI không chứa 0 (exceed).

- **(a)** Nếu `n_select ∈ {1,2}` (khớp kỳ vọng ~13.8%/cột × 5 cột của biến cố hai phía 1.4823σ)
  VÀ `n_confirm ∈ {0,1}` ⇒ **kết luận: đối chứng nhiễu ở tầng SELECT là control
  MIS-CALIBRATED (dương-tính-giả do ngưỡng đơn-cột + nhỏ mẫu), KHÔNG phải leak.** SELECT tái
  định nghĩa là **DIAGNOSTIC-ONLY** (chỉ dùng để đề cử ứng viên trong nội bộ mỗi pre-reg, không
  phải cổng dừng harness); **CONFIRM là cổng quyết định duy nhất** cho THẮNG/NULL/THUA. Được
  phép viết `docs/result/RESULT_S1_HPO_BAG_FEATGRP.md` với phán quyết P1/P2/P3 = NULL theo CONFIRM
  (đã có sẵn trong `result.json`, không đổi).
- **(b)** Nếu `n_select >= 3` ⇒ ngưỡng SELECT hỏng nặng hơn dự đoán (tỉ lệ bắn cao hơn ~13.8%/cột
  kỳ vọng nhiều) — **vẫn kết luận DIAGNOSTIC-ONLY** như (a) NẾU `n_confirm <= 1`, nhưng ghi
  **cảnh báo mạnh** trong RESULT + đề xuất MASTER thiết kế lại ngưỡng SELECT (ví dụ: tăng `k`
  hiệu dụng, dùng ngưỡng theo phân vị mô phỏng thay vì `inflate(k)` lý thuyết, hoặc nhiều
  cột nhiễu hơn) cho vòng sau. Vẫn được viết RESULT như (a).
- **(c)** Nếu `n_confirm >= 2` (bất kể `n_select`) ⇒ **KHÔNG viết RESULT** — đây là dấu hiệu lỗi
  harness/leak THẬT ở tầng quyết định (CONFIRM), không phải artifact ngưỡng. DỪNG, báo MASTER,
  điều tra: in `feature_importances_` của cột nhiễu tương ứng trên các fold CONFIRM, kiểm lại
  `assert tr.ts.max() < c` từng fold, kiểm khoá join `(ts_h, sym)` của merge feature.

`n_confirm >= 2` được ưu tiên override thành nhánh (c) ngay cả khi `n_select` rơi vào vùng (a)
hoặc (b), vì CONFIRM là cổng quyết định — bất thường ở đó nghiêm trọng hơn bất thường ở SELECT.

## 5. Dự đoán ghi trước (MASTER)

Dự đoán rơi vào nhánh **(a)**: SELECT ~1-2/5 cột bắn ngưỡng (đúng bản chất thống kê của ngưỡng
`inflate(3)` đơn-cột), CONFIRM 0/5 (không có leak/lỗi harness thật).

## 6. Ngoài phạm vi

Đổi ngưỡng/thiết kế đo P1-P3 đã chốt, GPU, sim Java, sinh bins/dataset mới (ghi đè
`feat_v2_x1.parquet` hay tạo file mới), chạm dữ liệu 2026, tune sau khi thấy số, git push, ssh
242.

## 7. Output

`/home/ubuntu/s1hpo/noisecal.json`: bảng đầy đủ 5 cột nhiễu (SELECT mean/sd_boot/threshold/
exceeds, CONFIRM CI/verdict), `n_select_exceed`, `n_confirm_exceed`, nhánh (a/b/c) trúng, bảng
seed dùng.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01UoVRjusfNM2USSVNKQrm7z
