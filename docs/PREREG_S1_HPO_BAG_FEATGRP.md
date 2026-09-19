# PREREG_S1_HPO_BAG_FEATGRP — S1_HPO_BAG_FEATGRP: 3 pre-reg độc lập (HPO / bagging / feature-group), OFFLINE

Chốt trước khi đo bất kỳ ứng viên nào. Commit file này PHẢI đứng trước commit
`docs/RESULT_S1_HPO_BAG_FEATGRP.md`; nếu thứ tự commit ngược lại thì toàn bộ kết quả VÔ HIỆU.

Thiết kế do MASTER chốt; agent thực thi KHÔNG được đổi ngưỡng/công thức sau khi thấy số.

**Phạm vi cứng:** OFFLINE thuần (python/pandas/xgboost CPU, `n_jobs=4` mọi run). KHÔNG sim Java,
KHÔNG sinh bins/dataset mới, KHÔNG GPU (luật cấm GPU cho rank-IC — `FS_RESULT.md` §0.2: nhiễu
backend GPU 0.018/tick > mọi hiệu ứng job này đi tìm). KHÔNG chạm dữ liệu 2026 (mọi fold OOS
`< 2026-01-01`). KHÔNG tune sau khi thấy số — 6+1+3 = 10 ứng viên (+ 1 đối chứng nhiễu) được
liệt kê ĐẦY ĐỦ dưới đây, không thêm/bớt sau commit. KHÔNG git push, KHÔNG ssh 242.

## 0. Nền — dữ liệu, mã nguồn, môi trường

| | |
|---|---|
| Repo | Oracle `/home/ubuntu/src/BinanceFuturesJava`, branch `module`, HEAD `2fd7357` |
| Script gốc tái dùng | `research/pipeline/x1/x1_s1_rank.py` (73 dòng, không sửa) |
| Script vòng này | `research/analysis/s1_hpo_bag_featgrp.py` (copy khối load-data/nhãn/purge/run của
  script gốc, tham số hoá KEEP/hyperparameter/seed/bagging — logic nhãn `rel5`, group `qid`,
  purge 72h, `assert tr.ts.max()<c` giữ Y NGUYÊN, không viết lại) |
| Ledger pool | `/home/ubuntu/ledger/cand_dev_x1.parquet` (g1lite, 7,020,129 dòng, ts 2021-03-31→2025-12-31) |
| Feature 40 cột | `/home/ubuntu/featv2/feat_v2_x1.parquet` (42 cột kể cả ts,sym; đã xác nhận đủ 16 cột nhóm P3 + `noise_0`) |
| Nhãn phụ | `/home/ubuntu/ledger/path_labels.parquet` (`g1_replay`, join `ts+sym`, giống hệt
  `research/analysis/gate_vs_rank3.py` dòng 7-13) |
| Python / xgboost / pandas / numpy / scipy | 3.10.12 / **3.2.0** / 2.3.3 / 2.2.6 / 1.15.3 (đo trực tiếp bước 1, khớp `research/pipeline/README.md` §4) |
| RAM / core | 23G / 4 core Oracle. `nice -n 10` mọi job train. |
| Output | `/home/ubuntu/s1hpo/pred_<name>.parquet` (mỗi ứng viên) + `/home/ubuntu/s1hpo/result.json` |

### 0.1 KEEP-9 gốc (baseline, giữ y hệt production)

```
KEEP9 = [vol_7d, dd_7d, rk_dd_7d, hrs_since_high_7d, ret_3d, rk_ret_3d, ret_14d, ls_global, rk_oi_delta24h]
```

### 0.2 Hyperparameter baseline (y hệt `x1_s1_rank.py` dòng 55, KHÔNG đổi trừ khi pre-reg P1 nói rõ)

```
XGBRanker(objective="rank:ndcg", n_estimators=300, max_depth=4, learning_rate=0.05,
          subsample=0.8, colsample_bytree=0.8, min_child_weight=50, n_jobs=4,
          tree_method="hist", random_state=42,
          lambdarank_pair_method="topk", lambdarank_num_pair_per_sample=8)
```

Nhãn `rel5` = ngũ phân vị trong tick của `rel = g1lite - median_tick(g1lite)`. Group `qid` =
`pd.factorize(tr.ts, sort=True)[0]` (1 group = 1 tick 15m). Purge = 72h (`tr = D[D.ts < c-72h]`).
`assert tr.ts.max() < c` giữ nguyên ở mọi fold/mọi ứng viên.

### 0.3 18 fold cutoff (2021Q3 → 2025Q4)

```
20210701 20211001 20220101 20220401 20220701 20221001 20230101 20230401 20230701 20231001
20240101 20240401 20240701 20241001 20250101 20250401 20250701 20251001
```

Fold index 0-9 = **SELECT** (OOS 2021Q3→2023Q4, 10 fold, dùng để xếp hạng/đề cử ứng viên).
Fold index 10-17 = **CONFIRM** (OOS 2024Q1→2025Q4, 8 fold, dùng để kết luận cuối — nested:
chỉ ứng viên đề cử của từng pre-reg mới được kiểm ở đây, không kiểm cả bó).
Toàn bộ 18 fold train trong MỘT lần gọi `run()` (D nạp một lần, mỗi fold độc lập theo cutoff —
đã xác nhận về mặt toán học là tương đương byte-for-byte với cách chia 2 lệnh riêng
16-fold/2-fold mà `RESULT_S1_OI12.md`/`RESULT_DEV2021.md` từng dùng, vì mỗi fold chỉ phụ thuộc
`D` và cutoff của chính nó, không phụ thuộc các cutoff khác trong cùng lệnh gọi).

## 1. Cổng REPRODUCTION (bắt buộc trước hết, DỪNG nếu FAIL)

Chạy `x1_s1_rank.py` (bản GỐC, không sửa) với `X1_LNAME=cand_dev_x1`,
`X1_FEAT=/home/ubuntu/featv2/feat_v2_x1.parquet`, KEEP=KEEP9, hai lệnh gọi tách biệt để so
đúng 2 artifact đã có:

- `X1_CUTS="20220101 20220401 ... 20251001"` (16 fold 2022+) → so với `ledger/pred_s1a2x1.parquet`.
- `X1_CUTS="20210701 20211001"` (2 fold 2021H2) → so với `ledger/pred_s1a2x1_y21.parquet`.

Tiêu chí PASS: `spearman(pred_mới.score, pred_cũ.score) = 1.000000` trên join `(ts,sym)` đầy đủ
(không thiếu dòng nào ở cả hai chiều), VÀ `edge5 g1lite` in ra khớp số đã ghi trong
`docs/RESULT_S1_OI12.md` §6 (16-fold ALL **+15.41%**, 2021 2-fold **+7.545%**) trong `±0.05pp`.
FAIL bất kỳ điều nào ⇒ DỪNG, ghi rõ version xgboost/python/n_jobs, KHÔNG chạy tiếp bất kỳ pre-reg nào.

Sau khi PASS, baseline dùng cho cả 3 pre-reg = **một lần train duy nhất trên đủ 18 fold**
(gộp 2 lệnh trên vào 1 lệnh `X1_CUTS` 18 giá trị, KEEP9, seed 42) — theo lý do toán học ở §0.3,
predictions của baseline 18-fold này phải trùng tuyệt đối với việc ghép hai file
`pred_s1a2x1_y21.parquet` + `pred_s1a2x1.parquet`; script phải TỰ kiểm lại điều này
(spearman=1.0 trên phần chồng lấp) trước khi dùng làm baseline chung.

## 2. Harness đo lường chung (dùng cho cả 3 pre-reg — TÁI DÙNG `PREREG_FS.md` §3 và
`research/analysis/trend_rank_ic.py::block_ci`)

### 2.1 Metric chính — edge5 OOS

Theo TICK: `e[ts] = mean(g1lite | rank_trong_tick(score) <= 5) - mean(g1lite | toàn tick)`,
`rank` = `groupby(ts).score.rank(method="first")` (score THẤP = TỐT, mặc định `ascending=True`
⇒ rank 1 = score thấp nhất = tốt nhất — đúng quy ước `x1_s1_rank.py` dòng 62, KHÔNG đảo dấu).
Gộp khối 72h: `block_id = ts // (72h)`.

### 2.2 Metric phụ — rank-IC Spearman trong tick

`ic[ts] = spearmanr(-score, outcome)` trên các tick có `>= 10` dòng (ngưỡng `min_n=10` của
`PREREG_FS.md` §3.1/`gate_vs_rank3.py`). **BẪY dấu:** `score` thấp = tốt, nên phải dùng
`-score` (hoặc rank `ascending=True` rồi đảo dấu tương quan) — dùng thẳng `score` mà không đảo
dấu, hoặc đảo dấu sai chiều khi dùng rank số, sẽ cho IC ngược dấu hoàn toàn (xem
`gate_vs_rank3.py` dòng đầu: "Lan truoc toi xep giam dan => dao nguoc => ket luan sai").
Đo trên **`g1lite`** (nhãn train) và trên **`g1_replay`** (`path_labels.parquet`, join
`(ts,sym)` inner, **in tỉ lệ ghép** = số dòng join được / tổng dòng OOS của candidate).

### 2.3 CI — paired block-bootstrap khối 72h

- `Δ[ts] = metric_variant[ts] - metric_baseline[ts]` (ghép cặp theo cùng `ts`; tập `ts` của
  variant và baseline PHẢI trùng nhau tuyệt đối vì cùng fold/cùng OOS rows, chỉ khác feature/
  hyperparameter/seed — script phải assert điều này).
- `block_id = ts // (72*3600000)`; `NREP=2000`, `SEED=20260919`,
  `numpy.random.default_rng(SEED)` (một seed cố định cho toàn bộ vòng, dùng lại cho mọi lần
  resample của mọi pre-reg/mọi ứng viên — không seed lại theo ứng viên).
  Resample: chọn lại `n_blocks` khối có hoàn lại, ước lượng lại = tổng trọng số theo số tick
  mỗi khối (giống hệt `trend_rank_ic.block_ci`), lấy percentile 2.5/97.5 của phân phối bootstrap
  của TRUNG BÌNH `Δ` ⇒ `[lo_raw, hi_raw]`.
- Hiệu chỉnh nhiều-ứng-viên: `inflate(k) = sqrt(2*ln k)` nếu `k>=2`, `= 1.0` nếu `k=1`
  (công thức chuẩn theo `docs/AUDIT_CI_INFLATE_STANDARDIZATION.md` §1, KHÔNG dùng hằng số lịch
  sử `1.21`). Áp dụng quanh TÂM (đúng quy ước `c3_rates.py`/`AUDIT_CI_INFLATE` §1.1):
  `c=(lo_raw+hi_raw)/2`, `h=(hi_raw-lo_raw)/2`, CI báo cáo = `[c - h*inflate(k), c + h*inflate(k)]`.
- **THẮNG** ở một cửa sổ: `Δ trung bình > 0` VÀ CI hiệu chỉnh không chứa 0.
  **THUA**: `Δ trung bình < 0` VÀ CI hiệu chỉnh không chứa 0. Còn lại: **NULL**.

### 2.4 Thủ tục nested (SELECT chọn, CONFIRM kết luận)

1. Train baseline (1 lần) + toàn bộ ứng viên của MỘT pre-reg trên đủ 18 fold.
2. **SELECT** (fold 0-9): tính `Δedge5` trung bình theo tick (không cần CI) cho từng ứng viên.
   Ứng viên có `Δedge5` (SELECT) cao nhất = **đề cử** của pre-reg đó. (P2 chỉ có 1 ứng viên nên
   đề cử là chính nó, không cần so sánh.)
3. **CONFIRM** (fold 10-17): CHỈ đề cử được kiểm — tính CI (§2.3) cho `Δedge5` và cả hai
   `Δrank-IC` với `k` = số ứng viên của pre-reg đó (P1 k=6, P2 k=1, P3 k=3). Phán quyết
   THẮNG/NULL/THUA của TOÀN pre-reg = phán quyết của đề cử trên CONFIRM theo metric CHÍNH
   (edge5); rank-IC báo cáo song song, không phải luật quyết định.
4. Không kiểm cả bó ứng viên trên CONFIRM (đúng chỉ đạo MASTER — tránh multiplicity kép).

### 2.5 Sanity bắt buộc mỗi ứng viên (dừng nếu fail)

- Số tick OOS mỗi fold bằng đúng baseline (cùng `D`, cùng cutoff).
- `score` không NaN/Inf.
- `assert tr.ts.max() < c` (đã có sẵn trong khối copy từ `x1_s1_rank.py`, không tắt).
- Tỉ lệ ghép `g1_replay` (`(ts,sym)` inner join) `>= 95%`; nếu thấp hơn, dừng và báo cáo thay vì
  âm thầm dùng phần ghép được.

## 3. P1 — S1_HPO (k=6): mỗi ứng viên đổi ĐÚNG 1 hyperparameter so với baseline §0.2

| id | thay đổi (so baseline) |
|---|---|
| H1 | `max_depth=3` |
| H2 | `max_depth=6` |
| H3 | `n_estimators=150` |
| H4 | `n_estimators=600` |
| H5 | `min_child_weight=200` |
| H6 | `lambdarank_num_pair_per_sample=16` |

Feature set = KEEP9 (không đổi), seed = 42 (không đổi), mọi tham số khác giữ baseline.

**Dự đoán ghi trước (MASTER):** NULL — rank-IC nhiễu theo tick ước lượng ~0.018 (theo
`FS_RESULT.md` §0.2, nhiễu backend GPU/seed cùng bậc độ lớn với hiệu ứng hyperparameter ở đây)
lớn hơn hiệu ứng kỳ vọng của việc đổi 1 hyperparameter. Ứng viên đề cử nhiều khả năng H4 hoặc H2
(tăng độ phức tạp mô hình) nhưng dự đoán KHÔNG vượt CI trên fold xác nhận.

## 4. P2 — S1_BAG (k=1): bagging 5 seed, trung bình HẠNG trong tick

5 model cùng hyperparameter baseline §0.2, chỉ đổi `random_state ∈ {42,1,2,3,4}` (seed 42 =
đúng model baseline, tái dùng không train lại). Score cuối cho mỗi tick =
**trung bình HẠNG trong tick của 5 model** (`groupby(ts).rank(method="first")` của từng model
rồi lấy trung bình 5 hạng — KHÔNG trung bình score thô, vì scale/độ lệch score giữa các seed có
thể khác nhau còn hạng thì luôn so sánh được). So với baseline = seed 42 đơn (đã có từ cổng
reproduction/§1, không train lại).

**Dự đoán ghi trước (MASTER):** Δedge5 dương nhỏ, khả năng cao NẰM NGOÀI CI vì bagging chỉ giảm
variance của model chứ không thêm thông tin mới về dữ liệu — đây là ứng viên **thực tế nhất**
của vòng này (chi phí thấp, không đổi feature/nhãn).

**Nếu THẮNG:** phải ghi rõ chi phí — train ×5 (thời gian + CPU), và pipeline sinh bins
(`build_map.py`/`x1_build_map.py`) phải sửa để nhận **hạng trung bình** thay vì `score` đơn
model trước khi có thể đưa vào production — **KHÔNG tự sinh bins/sim ở vòng này**, chỉ đề xuất
bước tiếp theo cho MASTER quyết.

## 5. P3 — S1_FEATGRP (k=3): thêm 1 nhóm feature vào KEEP-9

| id | nhóm thêm | feature |
|---|---|---|
| G1 | sức mạnh tương đối vs BTC/thị trường | `rs_btc_3d, rs_btc_7d, rs_mkt_3d, rs_mkt_7d, rk_rs_btc_7d` |
| G2 | funding/carry | `fund_last, fund_sum_3d, fund_sum_7d, fund_trend, fund_z_30d, rk_fund_sum_3d` |
| G3 | chân trời dài (drawdown/vị trí/vol/return 30d) | `dd_30d, pos_30d, vol_30d, ret_7d, rk_ret_7d` |

Mỗi ứng viên = KEEP9 + đúng 1 nhóm (14, 15, hoặc 14 feature tổng — G1: 14, G2: 15, G3: 14).
Hyperparameter/seed giữ baseline §0.2. Kèm đối chứng nhiễu **bắt buộc**: `noise_0` (đã có sẵn
trong `feat_v2_x1.parquet`) thêm vào KEEP-9 làm feature thứ 10, chạy CÙNG toàn bộ pipeline —
đây KHÔNG phải ứng viên thứ 4 (không tính vào `k=3`), mà là kiểm định tính hợp lệ của harness.

**Luật đối chứng nhiễu (bắt buộc dừng nếu vi phạm):** trên cửa sổ SELECT, nếu
`abs(Δedge5[noise_0]) >= inflate(3) * sd_boot(Δedge5[noise_0], khối 72h)` — tức đạt cùng ngưỡng
sẽ dùng để công nhận một ứng viên thật — thì **harness bị coi là LỖI**: DỪNG ngay, không báo
cáo bất kỳ kết quả P1/P2/P3 nào khác, ghi rõ lý do nghi ngờ (rò rỉ nhãn, lỗi purge, lỗi join).
Ngưỡng này soi cả trên CONFIRM để báo cáo (không phải điều kiện dừng ở CONFIRM, vì CONFIRM chỉ
kiểm đề cử — nhưng nếu `noise_0` vô tình được chọn làm đề cử ở SELECT thì tự nó đã là bằng
chứng harness lỗi).

**Dự đoán ghi trước (MASTER):** NULL cả 3 nhóm — cùng họ dữ liệu (giá/khối lượng/funding ở
thang giờ) với `FS_RESULT.md` (0/16 ứng viên PASS) và `RESULT_S1_OI12.md` (OI: model dùng được
feature, edge5 g1lite ranking +15.91% nhưng NULL dưới gate T170 — bài học "offline tốt ≠ sim
tốt" không áp dụng trực tiếp ở vòng OFFLINE thuần này nhưng cảnh báo diễn giải quá tay một
Δedge5 dương nhỏ). Nếu có tín hiệu thật, dự đoán nằm ở **G1** (sức mạnh tương đối — hướng dữ
liệu S1 hiện chưa có, khác owned bởi FS/OI12).

## 6. Ngoài phạm vi (không làm trong vòng này)

Đổi nhãn (`g1lite`, `rel5`), đổi cách chọn 40→9 feature nền, GPU, sinh bins/dataset/sim mới,
chạm dữ liệu 2026, tune sau khi thấy số, thêm/bớt ứng viên sau khi commit file này, deploy bất
kỳ kết quả nào (kể cả THẮNG) — mọi đề xuất áp dụng phải là một pre-reg RIÊNG do MASTER duyệt.

## 7. Thứ tự thực hiện

1. `mkdir -p /home/ubuntu/s1hpo`; kiểm `df -h`, version xgboost/pandas/python (đã đo — xem §0).
2. Cổng reproduction §1. FAIL ⇒ dừng.
3. Ước lượng thời gian: đo thời gian train baseline đủ 18 fold ở bước cổng reproduction (gộp
   lại 1 lệnh), nhân theo `(1 + 6 + 5 + 4)` lần (baseline + 6 HPO + 5 seed bag [4 train mới +
   1 tái dùng] + 3 featgrp + 1 noise). Nếu tổng ước lượng **> 6 giờ**, báo MASTER TRƯỚC khi
   chạy toàn bộ, không tự cắt fold để rút ngắn.
4. Chạy tuần tự từng ứng viên (`nice -n 10`, `n_jobs=4`), lưu `pred_<name>.parquet`, log mỗi
   fold (số dòng train/oos, edge5 fold đó) để có thể dừng giữa chừng mà không mất tiến độ.
5. Tính harness §2 cho từng pre-reg theo thủ tục nested §2.4, xuất `/home/ubuntu/s1hpo/result.json`.
6. Sanity §2.5 cho mọi ứng viên.
7. Viết `docs/RESULT_S1_HPO_BAG_FEATGRP.md`: phán quyết P1/P2/P3 (THẮNG/NULL/THUA), bảng
   Δedge5/Δrank-IC + CI (SELECT và CONFIRM), đối chứng nhiễu, đối chiếu dự đoán MASTER, chi phí
   P2 nếu THẮNG, bước kế tiếp CHỈ dưới dạng đề xuất, md5/sha256 của `pred_s1a2x1.parquet` +
   `pred_s1a2x1_y21.parquet` gốc dùng làm neo cổng reproduction.
8. Commit cả hai file docs + script, kết thúc message bằng dòng đồng tác giả.

## Phụ lục §0 — Gate đính chính (viết TRƯỚC khi xem bất kỳ kết quả P1/P2/P3 nào)

Cổng reproduction §1 (bản gốc) FAIL lần chạy đầu: `repro16 vs pred_s1a2x1`
spearman=0.834341 max|d|=527.4; `repro_y21 vs pred_s1a2x1_y21` spearman=0.760614 max|d|=127.2 —
trong khi edge5 in ra khớp tuyệt đối số mốc (`+15.415%` vs `+15.41%`, `+7.545%` vs `+7.545%`).

Chẩn đoán (đúng nghi vấn MASTER nêu ở Bước 1): cột `score` mà `run_variant()` ghi ra là **HẠNG
trong tick** (`rank_sum/len(model_kwargs_list)`, dùng chung cho cả đơn model và bagging P2),
KHÔNG phải giá trị `-p` liên tục toàn cục như `x1_s1_rank.py` ghi vào `pred_s1a2x1*.parquet`.
Hai đại lượng khác thang đo (hạng cục bộ reset mỗi tick, vs điểm liên tục toàn cục) nên
`spearman` tính GLOBAL trên toàn bộ join (không nhóm theo tick) thấp dù model tái lập tuyệt đối
trong từng tick — đây là lỗi ĐỊNH NGHĨA GATE, không phải model khác.

Xác nhận thực nghiệm (`cmp()` trong `gate_reproduction()` được vá thêm chẩn đoán trong-tick
trước khi đổi tiêu chí PASS — xem `/home/ubuntu/s1hpo/gate2.log`, `gate3.log`):

| cửa sổ | rank_exact_match_frac | intick_spearman median | intick_spearman min | frac(≥0.999) | n_ticks |
|---|---|---|---|---|---|
| 16-fold (2022–2025) | 1.000000 | 1.000000 | 0.552560 | 0.9995 | 17349 |
| y21 (2021H2) | 1.000000 | 0.999998 | 0.999608 | 1.0000 | 934 |

`rank_exact_match_frac=1.0` ở CẢ HAI cửa sổ (đo trên từng dòng, không phải trung bình xấp xỉ)
là bằng chứng mạnh nhất: `rank(method="first")` trong tick của score mới TRÙNG TUYỆT ĐỐI với
score cũ ở 100% số dòng ⇒ model tái lập y hệt, không phải model khác/downcast/version xgboost
khác biệt (kết luận đủ rõ ở bước (b), không cần chạy tiếp bước chẩn đoán (c) float32→float64).
Vài tick có intick spearman thấp cục bộ (min=0.552560 ở cửa sổ 16-fold) là ARTIFACT của
`spearmanr` tự tie-break riêng (không phải `method="first"`) trên nhóm rất nhỏ có giá trị trùng
nhau — không mâu thuẫn với `rank_exact_match_frac=1.0`.

**Quyết định (chốt trước khi chạy P1–P3, không đổi sau khi thấy số):** sửa tiêu chí PASS của
`gate_reproduction()` từ "spearman toàn cục = 1.0" thành 3 điều kiện: (a) số dòng join = số
dòng mới = số dòng cũ ở cả hai chiều; (b) `rank_exact_match_frac >= 0.999999` (thay cho
"spearman trong tick min ≥ 0.999" đề xuất ban đầu, vì tiêu chí đó nhạy với artifact tie-break ở
tick cực nhỏ như trên, trong khi rank-khớp-tuyệt-đối bất biến với tie-break và trả lời trực
tiếp câu hỏi "có tái lập đúng thứ tự xếp hạng hay không"); (c) `edge5` khớp mốc
`RESULT_S1_OI12.md` §6 trong `±0.05pp` (giữ nguyên ngưỡng gốc §1, không nới thêm). KHÔNG đổi
logic model/nhãn/purge/feature/hyperparameter — chỉ đổi định nghĩa GATE (cách so sánh), như chỉ
đạo Bước 1(b) của MASTER. Chạy lại `python3 s1_hpo_bag_featgrp.py gate` sau khi vá
(`/home/ubuntu/s1hpo/gate3.log`, `gate_result.json`): **PASS** — `rank_exact_match_frac=
1.000000` cả hai cửa sổ, `edge5` 16-fold `+15.415%` (mốc `+15.41%`, lệch 0.005pp), y21
`+7.545%` (mốc `+7.545%`, lệch <0.001pp).

Thời gian đo được: `load_D()` lần đầu (cache OS lạnh) mất ~30 phút; các lần chạy sau (cache ấm,
cùng máy) chỉ ~10–20 giây. `repro16` (16 fold) ~10-11 phút, `repro_y21` (2 fold) ~20 giây. Số
lần train-18-fold cần cho toàn vòng (baseline 1 + P1 6 HPO + P2 bag 5 seed [script hiện train
đủ cả 5 seed, không tái dùng seed-42 baseline dù pre-reg §4 kỳ vọng tái dùng — chênh lệch chi
phí nhỏ, không ảnh hưởng thiết kế/kết luận, ghi nhận ở RESULT §"thời gian"] + P3 3 nhóm + 1
noise) = 1+6+5+4 = 16 lần train-18-fold ≈ 16 × ~11 phút ≈ **~2.9 giờ** — dưới ngưỡng báo MASTER
6 giờ ở §7 mục 3, nên tiếp tục chạy `full` theo đúng thứ tự P2→P1→P3 mà không dừng xin duyệt
trước.

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01UoVRjusfNM2USSVNKQrm7z
