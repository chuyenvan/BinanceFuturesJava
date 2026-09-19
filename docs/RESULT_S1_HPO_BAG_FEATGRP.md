# RESULT_S1_HPO_BAG_FEATGRP — S1_HPO_BAG_FEATGRP: 3 pre-reg độc lập (HPO / bagging /
feature-group) trên S1, OFFLINE + hiệu chuẩn đối chứng nhiễu (NOISE_CAL)

Pre-reg: `docs/PREREG_S1_HPO_BAG_FEATGRP.md` (chốt trước, commit `a04fc10`/`b4cf870`) +
`docs/PREREG_S1_NOISE_CAL.md` (chốt trước khi xem số noise_1..4, commit `6af7ba5`, đứng trước
file RESULT này theo đúng thứ tự bắt buộc). Script: `research/analysis/s1_hpo_bag_featgrp.py`
(P1/P2/P3 + noise_0) và `research/analysis/s1_noise_cal.py` (noise_1..4, import lại
`s1_hpo_bag_featgrp`, không sửa logic train/nhãn/purge).

## 0. Cổng REPRODUCTION (gate) — định nghĩa cuối cùng

Cổng gốc (spearman toàn cục = 1.0) FAIL lần chạy đầu vì lý do ĐỊNH NGHĨA: cột `score` của script
này là **hạng trong tick**, còn `pred_s1a2x1*.parquet` cũ lưu **điểm liên tục toàn cục** — hai
đại lượng khác thang đo. Sau khi vá chẩn đoán trong-tick (xem `docs/PREREG_S1_HPO_BAG_FEATGRP.md`
Phụ lục §0, `/home/ubuntu/s1hpo/gate2.log`/`gate3.log`), tiêu chí PASS cuối cùng (chốt TRƯỚC khi
xem P1/P2/P3):

(a) số dòng join = số dòng mới = số dòng cũ ở cả hai chiều; (b) `rank_exact_match_frac >=
0.999999`; (c) `edge5` khớp mốc `RESULT_S1_OI12.md` §6 trong `±0.05pp`.

| cửa sổ | n_join | rank_exact_match_frac | edge5 (mới) | mốc | lệch |
|---|---|---|---|---|---|
| 16-fold (2022-2025) | 6,573,909 | **1.000000** | +15.415% | +15.41% | 0.005pp |
| y21 (2021H2) | 112,048 | **1.000000** | +7.545% | +7.545% | <0.001pp |

**PASS.** `baseline18_selfcheck`: baseline 18-fold (1 lần train duy nhất) trùng tuyệt đối với
ghép `pred_s1a2x1_y21`+`pred_s1a2x1` của cổng reproduction (`spearman=1.000000`,
`n_b18=n_split=n_join=6,685,957`). `baseline_sanity`: 18,283 tick OOS, `n_bad_score=0`,
`replay_join_rate_covered=0.9999` (xem giới hạn coverage ở §4).

md5/sha256 neo cổng reproduction (`ledger/pred_s1a2x1.parquet`, `ledger/pred_s1a2x1_y21.parquet`):

| file | md5 |
|---|---|
| `pred_s1a2x1.parquet` | `94d703a195e0d5b62ff9a3c7fac9cf87` |
| `pred_s1a2x1_y21.parquet` | `a9d29c811d06e2b688fa37553ea7a72a` |

sha256: `pred_s1a2x1.parquet` = `2618fe1a0235d8ed3602f7b4bf37d8ba611e4e6c923854e10184d036065309fe`;
`pred_s1a2x1_y21.parquet` = `4b3da56052aee909a50f0960891a7801b67401a9be608efc850126139e111683`.

## 1. NOISE_CAL — hiệu chuẩn đối chứng nhiễu (pre-reg `docs/PREREG_S1_NOISE_CAL.md`)

**Bối cảnh:** vòng chạy `full` gốc cho P1/P2/P3 NULL trên CONFIRM, nhưng đối chứng `noise_0`
(feature thứ 10 = cột nhiễu, thêm vào KEEP-9 giống P3) **vượt ngưỡng `inflate(3)×sd_boot` trên
SELECT** (`select_mean_edge5=-0.4574pp`, ngưỡng `0.2408pp`) — theo luật Sec 5 gốc, điều này buộc
DỪNG toàn bộ và coi harness LỖI. MASTER nghi ngờ đây là control **mis-calibrated** (ngưỡng
`inflate(3)=1.4823σ` áp cho MỘT cột đơn tương đương biến cố hai phía ~13.8%/cột, không phải bằng
chứng leak), và NOISE_CAL được thiết kế để đo trực tiếp giả thuyết này bằng 4 cột nhiễu độc lập
bổ sung.

**Thiết kế:** `noise_1`, `noise_2` tái dùng cột có sẵn trong `feat_v2_x1.parquet` (cùng seed gốc
`20260902`, 3 draw tuần tự từ 1 rng stream — xác nhận độc lập thực nghiệm: `corr(noise_0,
noise_1)=-0.000089`, `corr(noise_0,noise_2)=+0.000282`, `corr(noise_1,noise_2)=-0.000029`).
`noise_3` (seed **20260920**), `noise_4` (seed **20260921**) sinh mới, merge tạm vào `D` qua
đúng khoá `ts_h,sym` — không ghi đè `feat_v2_x1.parquet` gốc. Mỗi cột train **đúng pipeline 18
fold** (baseline hyperparameter/seed=42, tái dùng nguyên `load_D`/`run_variant`/metric của
`s1_hpo_bag_featgrp.py`), **tái dùng baseline `pred_baseline18.parquet`** đã có sẵn (không train
lại — baseline_reused sanity khớp tuyệt đối `result.json.baseline_sanity`: cùng 18,283 tick,
cùng `replay_join_rate_overall=0.132546`). Ngưỡng SELECT dùng đúng `k=3`/`inflate(3)` như P3
dùng cho `noise_0`, để đo tỉ lệ bắn của CHÍNH ngưỡng đó.

**Sự cố kỹ thuật (đã sửa trước khi có kết quả):** lần chạy đầu `s1_noise_cal.py` lỗi
`AttributeError` khi tái dựng `fold`/`g1lite` cho baseline tái dùng — hoá ra
`pred_baseline18.parquet` đã được `main()` của `s1_hpo_bag_featgrp.py` ghi đè bằng dataframe ĐẦY
ĐỦ (`ts,sym,g1lite,yr,score,fold`), không phải bản rút gọn `ts,sym,score` mà `run_variant()` tự
lưu nội bộ. Sửa bằng cách đọc trực tiếp file (không suy lại gì) — không có kết quả noise nào
được tính trước khi phát hiện lỗi, không ảnh hưởng tính hợp lệ pre-reg. Commit sửa lỗi
`bc9b8bf` (sau `docs/PREREG_S1_NOISE_CAL.md` commit `6af7ba5`).

**Kết quả — 5 cột nhiễu (SELECT dùng để đếm exceed-rate, CONFIRM là cổng quyết định):**

| cột | seed | SELECT Δedge5 | ngưỡng SELECT | vượt SELECT? | CONFIRM Δedge5 (CI 95%, inflate(3)) | CONFIRM verdict |
|---|---|---|---|---|---|---|
| noise_0 | 20260902 (draw#0) | −0.4574pp | 0.2408pp | **CÓ** | +0.127pp [−1.316, +1.708] | NULL |
| noise_1 | 20260902 (draw#1) | −0.2171pp | 0.3198pp | không | +0.660pp [−0.733, +2.103] | NULL |
| noise_2 | 20260902 (draw#2) | −0.1640pp | 0.1831pp | không | +0.426pp [−0.642, +1.448] | NULL |
| noise_3 | 20260920 | −0.1427pp | 0.3062pp | không | +0.760pp [−0.472, +2.124] | NULL |
| noise_4 | 20260921 | −0.0745pp | 0.1536pp | không | +1.085pp [−0.207, +2.346] | NULL |

**exceed-rate SELECT = 1/5 (noise_0 only); exceed-rate CONFIRM = 0/5** (mọi cột đều CI chứa 0
trên metric quyết định `Δedge5`). Sanity mọi cột: `n_bad_score=0`, tick set OOS trùng tuyệt đối
baseline (18,283 tick), `g1_replay` coverage khớp baseline (`0.9999` trong phạm vi covered),
`assert tr.ts.max()<c` giữ nguyên trong `run_variant()` (không tắt).

**Áp cây quyết định pre-declare (§4 `PREREG_S1_NOISE_CAL.md`):** `n_select=1 ∈ {1,2}` VÀ
`n_confirm=0 ∈ {0,1}` ⇒ **nhánh (a)**: đối chứng nhiễu ở tầng SELECT là control
**MIS-CALIBRATED** (dương-tính-giả do ngưỡng đơn-cột `inflate(3)` áp cho SELECT mẫu nhỏ — đúng
như dự đoán MASTER, ~13.8%/cột × 5 cột), **KHÔNG phải leak**. SELECT được tái định nghĩa là
**DIAGNOSTIC-ONLY** (chỉ dùng để đề cử ứng viên trong nội bộ mỗi pre-reg); **CONFIRM là cổng
quyết định duy nhất** cho THẮNG/NULL/THUA. RESULT này viết theo đúng nhánh (a): P1/P2/P3 = NULL
theo CONFIRM (§2), không có gì cần điều tra thêm ở tầng harness.

**Quan sát phụ (không đổi phán quyết, chỉ ghi nhận trung thực):** metric phụ `Δrank-IC(g1lite)`
trên CONFIRM có CI không chứa 0 (âm) ở 2/9 ứng viên/cột đã đo trong toàn bộ vòng: `P3_G1`
(`-0.00486`, CI`[-0.00854,-0.00110]`) và **`noise_3`** (`-0.00210`, CI`[-0.00420,-0.0001]`) — kể
cả một cột NHIỄU THUẦN cũng cho CI IC-lite "có ý nghĩa" trên CONFIRM. Điều này củng cố đúng quy
ước pre-reg gốc (Sec 2.4): `rank-IC` chỉ **báo cáo song song**, KHÔNG phải luật quyết định — nếu
dùng IC-lite làm cổng thay vì `edge5`, tỉ lệ dương-tính-giả trên CONFIRM sẽ cao hơn 0/5 rõ rệt.
Phán quyết P1/P2/P3 trong RESULT này giữ nguyên theo `edge5` như pre-reg đã chốt.

## 2. Phán quyết P1/P2/P3 (theo CONFIRM — cổng quyết định duy nhất, xem §1)

Đơn vị `Δedge5`: điểm phần trăm (pp). CI = block-bootstrap khối 72h, `NREP=2000`,
`seed=20260919`, hiệu chỉnh `inflate(k)` quanh tâm (k = số ứng viên của pre-reg đó).

### 2.1 P1 — S1_HPO (k=6, đổi đúng 1 hyperparameter/ứng viên so baseline)

| id | thay đổi | SELECT Δedge5 | CONFIRM Δedge5 [CI 95%] | CONFIRM Δrank-IC(g1lite) [CI] | verdict |
|---|---|---|---|---|---|
| H1 | max_depth=3 | +0.172pp | +0.821pp [−0.597, +2.296] | −0.00066 [−0.00519, +0.00400] | NULL |
| H2 | max_depth=6 | −0.178pp | −1.269pp [−4.352, +1.579] | −0.00304 [−0.00798, +0.00195] | NULL |
| H3 | n_estimators=150 | −0.081pp | +0.713pp [−1.336, +2.867] | −0.00116 [−0.00464, +0.00225] | NULL |
| H4 | n_estimators=600 | −0.087pp | −0.499pp [−1.959, +0.945] | −0.00102 [−0.00431, +0.00241] | NULL |
| H5 | min_child_weight=200 | +0.069pp | +0.623pp [−0.901, +2.229] | +0.00055 [−0.00178, +0.00318] | NULL |
| H6 | num_pair_per_sample=16 | +0.080pp | +0.287pp [−1.278, +1.858] | +0.00126 [−0.00215, +0.00499] | NULL |

Đề cử SELECT (cao nhất): **H1**. **Phán quyết P1 = NULL** (CONFIRM CI của H1 chứa 0).

### 2.2 P2 — S1_BAG (k=1, bagging 5 seed, trung bình HẠNG trong tick vs seed-42 đơn)

| candidate | SELECT Δedge5 | CONFIRM Δedge5 [CI 95%] | CONFIRM Δrank-IC(g1lite) [CI] | verdict |
|---|---|---|---|---|
| BAG5 (seed 42,1,2,3,4) | −0.060pp | +0.478pp [−0.138, +1.063] | +0.00031 [−0.00045, +0.00117] | NULL |

**Phán quyết P2 = NULL.** CI hẹp hơn hẳn P1/P3 (k=1, không cần hiệu chỉnh đa-ứng-viên) nhưng vẫn
chứa 0. Chi phí: script train đủ cả 5 seed (không tái dùng seed-42 baseline như pre-reg kỳ vọng
ban đầu — ghi nhận chênh lệch chi phí nhỏ, không ảnh hưởng kết luận).

### 2.3 P3 — S1_FEATGRP (k=3, thêm 1 nhóm feature vào KEEP-9)

| id | nhóm | SELECT Δedge5 | CONFIRM Δedge5 [CI 95%] | CONFIRM Δrank-IC(g1lite) [CI] | verdict |
|---|---|---|---|---|---|
| G1 | rel-strength vs BTC/mkt | +0.047pp | +0.406pp [−1.323, +2.201] | −0.00486 [−0.00854, −0.00110]* | NULL |
| G2 | funding/carry | −0.044pp | +2.621pp [−1.310, +7.159] | −0.00112 [−0.00590, +0.00370] | NULL |
| G3 | long-horizon (dd/pos/vol/ret 30d) | +0.141pp | +0.512pp [−2.139, +3.261] | +0.00621 [−0.00189, +0.01464] | NULL |
| noise_0 (đối chứng) | 1 cột nhiễu | −0.457pp | +0.127pp [−1.316, +1.708] | −0.00140 [−0.00334, +0.00047] | NULL |

*G1 có `Δrank-IC(g1lite)` CI không chứa 0 trên CONFIRM (âm) — xem §1 "quan sát phụ": KHÔNG dùng
làm cơ sở phán quyết vì `noise_3` (cột nhiễu thuần) cũng cho cùng hiện tượng, và pre-reg gốc quy
định `edge5` là metric quyết định duy nhất.

Đề cử SELECT (cao nhất): **G3**. **Phán quyết P3 = NULL** (CONFIRM CI của G3 chứa 0). Đối chứng
`noise_0` đã qua hiệu chuẩn NOISE_CAL (§1): SELECT bắn ngưỡng là artifact thống kê, CONFIRM NULL
— harness hợp lệ, phán quyết P3 = NULL đứng vững.

### 2.4 Tổng kết

**P1 = NULL, P2 = NULL, P3 = NULL** — không có lever HPO/bagging/feature-group nào mua được edge
có ý nghĩa thống kê trên CONFIRM (2024Q1→2025Q4) so với baseline KEEP-9/seed-42/hyperparameter
gốc.

## 3. Đối chiếu dự đoán pre-reg

| pre-reg | dự đoán MASTER | thực tế | khớp? |
|---|---|---|---|
| P1 (HPO) | NULL, đề cử nhiều khả năng H4/H2 | NULL, đề cử thực tế **H1** | verdict khớp, đề cử lệch (H1 không nằm trong 2 ứng viên MASTER nêu) |
| P2 (bagging) | Δedge5 dương nhỏ, khả năng cao NGOÀI CI (NULL) | Δedge5 CONFIRM dương nhỏ (+0.478pp), NGOÀI CI → NULL | khớp hoàn toàn |
| P3 (featgrp) | NULL cả 3 nhóm; nếu có tín hiệu thật, nằm ở G1 | NULL cả 3 nhóm; SELECT cao nhất là **G3** (không phải G1) | verdict khớp, tín hiệu SELECT lệch hướng dự đoán |
| NOISE_CAL | rơi vào nhánh (a): SELECT ~1-2/5, CONFIRM 0/5 | SELECT **1/5**, CONFIRM **0/5** → nhánh (a) | **khớp chính xác** |

## 4. Giới hạn

- `g1_replay` (`path_labels.parquet`) chỉ phủ đến **2024-06-30** (hết fold 11) — fold 12-17 (nửa
  sau 2024 → 2025) KHÔNG có `g1_replay`, nên `Δrank-IC(g1_replay)` trên CONFIRM chỉ còn dữ liệu
  thật ở fold 10-11 (2024 Q1-Q2), phần còn lại của cửa sổ CONFIRM chỉ có `Δrank-IC(g1lite)` +
  `Δedge5(g1lite)` — không ảnh hưởng phán quyết chính (luôn theo `edge5`, đo đủ trên toàn bộ
  18,283 tick) nhưng làm CI của `Δrank-IC(g1_replay)` rộng hơn (chỉ ~1,160 tick thay vì 13,914).
- SELECT (fold 0-9, 2021Q3→2023Q4) có mẫu nhỏ ở một số fold (fold 6-7: 44-76 tick OOS) khiến
  `sd_boot` SELECT kém ổn định — chính là lý do NOISE_CAL (§1) phải hiệu chuẩn lại vai trò của
  SELECT: chỉ dùng để đề cử (diagnostic), không dùng làm cổng dừng harness.
- P2 (BAG5) tốn chi phí train ×5 so với 1 candidate đơn của P1/P3 — script hiện tại train đủ cả
  5 seed thay vì tái dùng model seed-42 của baseline như pre-reg §4 kỳ vọng ban đầu (chênh lệch
  chi phí nhỏ, đã ghi nhận, không ảnh hưởng kết luận).
- NOISE_CAL đo 5 cột nhiễu — cỡ mẫu 5 vẫn nhỏ để ước lượng chính xác một tỉ lệ ~13.8% (khoảng tin
  cậy nhị thức cho 1/5 khá rộng); kết luận nhánh (a) dựa trên khớp ĐỊNH TÍNH với kỳ vọng lý
  thuyết (không phải kiểm định giả thuyết chính thức về tỉ lệ) — đủ để phân biệt "harness lỗi rõ
  ràng" (sẽ cho tỉ lệ CONFIRM cao) khỏi "control mis-calibrated" (CONFIRM 0/5 quan sát được),
  nhưng không định lượng chính xác tỉ lệ dương-tính-giả thật của ngưỡng.

## 5. Kết luận

**Các lever HPO (P1), bagging (P2), và nhóm-feature bổ sung (P3) trên S1 KHÔNG mua được edge có
ý nghĩa thống kê trên CONFIRM.** Đây là xác nhận thứ **BA** liên tiếp (sau `FS_RESULT.md`: 0/16
ứng viên feature-selection PASS, và `RESULT_S1_OI12.md`: OI cải thiện ranking offline nhưng NULL
dưới gate sim T170) rằng, ở lưới thời gian giờ hiện tại, dữ liệu **giá/khối lượng/funding/OI**
cho S1 đã **cạn dư địa cải thiện bằng cách xoay hyperparameter, bagging, hoặc thêm tổ hợp feature
mới từ cùng họ dữ liệu này** — kể cả khi offline ranking (SELECT/CONFIRM edge5 g1lite) đôi lúc
lên đến hai chữ số phần trăm ở baseline, không ứng viên nào tách biệt được khỏi baseline một
cách có ý nghĩa thống kê trên cửa sổ xác nhận độc lập.

NOISE_CAL (§1) đồng thời xác nhận: đối chứng nhiễu `noise_0` bắn ngưỡng trên SELECT ở vòng `full`
là **artifact hiệu chuẩn của chính ngưỡng** (`inflate(3)` áp cho một cột đơn ~13.8% dương-tính-
giả hai phía), không phải bằng chứng leak/lỗi harness — harness `s1_hpo_bag_featgrp.py` được xác
nhận đáng tin cậy để dùng lại cho các vòng offline S1 sau này, với khuyến nghị: (i) không dùng
`select_exceeds_threshold` của MỘT cột nhiễu đơn làm điều kiện DỪNG cứng ở các vòng sau — nên
dùng nhiều cột nhiễu (như NOISE_CAL) hoặc ngưỡng theo phân vị mô phỏng thay vì `inflate(k)` lý
thuyết cho vai trò "gác cổng SELECT"; (ii) `rank-IC` phụ (đặc biệt trên `g1lite`) có tỉ lệ
dương-tính-giả không nhỏ ở CONFIRM ngay cả với cột nhiễu thuần (§1) — tiếp tục giữ nguyên tắc
pre-reg gốc: chỉ `edge5` là luật quyết định, `rank-IC` chỉ báo cáo song song.

**Đề xuất cho MASTER (không tự thực hiện trong vòng này):** hướng còn lại cho S1 là (a) **nguồn
dữ liệu mới** — long/short-ratio hoặc liquidation collector cần thêm lịch sử trước khi có đủ dữ
liệu OOS để kiểm định nghiêm túc, hoặc (b) **cấu trúc bài toán khác** (đổi nhãn/horizon/cách gộp
tick, đổi đơn vị group `qid`, hoặc kiến trúc model khác ngoài `XGBRanker` rank:ndcg) — cả hai đều
ngoài phạm vi cứng của vòng offline thuần này (Sec 6 pre-reg gốc: không đổi nhãn, không sinh
dataset/bins mới).

## 6. Thời gian & môi trường

- Vòng `full` (P1+P2+P3+noise_0, 16 lần train-18-fold): `elapsed_sec_total` = 11,935.5s (~3.3h).
- Vòng NOISE_CAL (4 lần train-18-fold, tái dùng baseline có sẵn): quan sát thực tế theo log
  `20:35:16→21:21:09` (Oracle time) ≈ 46 phút (~11.5 phút/cột, khớp ước lượng pre-reg ~45 phút).
- Môi trường: python 3.10.12, xgboost **3.2.0**, pandas 2.3.3, numpy 2.2.6, scipy 1.15.3, Oracle
  23G RAM / 4 core, `n_jobs=4`/`nice -n 5` mọi job train. Không GPU, không sim Java, không chạm
  dữ liệu 2026, không git push, không ssh 242.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01UoVRjusfNM2USSVNKQrm7z
