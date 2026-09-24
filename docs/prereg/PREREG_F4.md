# PREREG_F4 — Tầng TIMING có phải là nơi chứa alpha không?

**Trạng thái:** chốt trước khi đo. Commit này phải đứng TRƯỚC commit kết quả.
**Phạm vi:** OFFLINE thuần. Không chạy Java sim, không chạy VAL, không sửa code simulator,
không dùng GPU (`AGENT_RUNBOOK` bẫy số 7).

## 0. Vì sao F4 tồn tại

`docs/experiment/F3_SUPPLY.md` mục G đo được: `sd(p15)` trong tick = **0** ⇒ `p15` là **scalar toàn
thị trường mỗi tick**, không phải điểm từng coin. `spearman(npass, p15) = +0.454` vs
`spearman(npass, U) = +0.021`. Cộng với `docs/analysis/SELECTOR_LADDER_Q.md` (selector ladder chưa
thiết lập), giả thuyết làm việc là: **hệ này là market-timing đội lốt hệ chọn coin** — một
scalar quyết định KHI NÀO giao dịch.

Nếu đúng, đơn vị quan sát không còn là 970 lệnh mà là tick 15 phút ⇒ lần đầu có power.

## 1. CẢNH BÁO TRƯỚC KHI ĐO — hai điểm phải ghi trước, không được sửa sau

### 1.1 `cand_dev.parquet` KHÔNG chứa 87,600 tick

`ledger.py:28` chỉ giữ tick có `p15 >= 0.008`. Đã kiểm đếm:

| tập | số tick 15m (DEV 2022-01-01..2024-06-30) |
|---|---|
| lưới lịch đầy đủ (`wfo_gate_pred.csv`) | **87,552** |
| trong đó `p15 >= 0.008` (= toàn bộ `cand_dev`) | **4,639 (5.30%)** |
| có ≥1 record `predwf_G015x26` | 87,547 (99.994%) |
| tick gate-ĐÓNG có pred G015 | 82,908 / 82,913 |

⇒ Muốn có n = 87,552 thì **phải dựng lại lưới tick mở rộng** từ chính các nguồn gốc mà
`ledger.py` dùng (`wfo_gate_pred.csv` + `predwf_G015x26` + `label_15m/*.pb`), KHÔNG dùng
`cand_dev.parquet` làm khung. Đây chính là "câu hỏi còn mở" mà `F3_SUPPLY` mục Hệ quả ghi là
chưa ai kiểm. Việc dựng lại này được khai báo ở đây, trước khi đo, và **không đổi định nghĩa
`p15` / `score_g015` / `g1lite` / `dyn_thr`** so với `ledger.py` + `gate_cfg.py`.

### 1.2 Con số power "SE ≈ 0.0034" trong đề bài là ƯỚC LƯỢNG QUÁ LẠC QUAN

`1/sqrt(87552) = 0.0034` chỉ đúng khi các tick độc lập. Chúng không độc lập: nhãn `g1lite`
nhìn 72h tới ⇒ 288 tick liên tiếp dùng chung cửa sổ nhãn. Cận trên bi quan của sai số là
`1/sqrt(87552/288) = 1/sqrt(304) = 0.057` — **gấp 17 lần** con số trong đề bài. Sự thật nằm
giữa hai cận, và **block bootstrap khối 72h là trọng tài duy nhất**. Ghi trước: nếu CI sau
bootstrap rộng cỡ 0.05 thì F4 KHÔNG có power như kỳ vọng và phải báo cáo đúng như vậy, không
được quay sang dùng SE iid.

### 1.3 2021 KHÔNG dùng được làm hold-out phụ

`predwf_G015x26` chỉ có bins từ `predict_wf_20220101.bin` trở đi. Không có `score_g015` cho
2021 ⇒ không dựng được `Y_tick`. Hold-out phụ 2021 **huỷ**, ghi là không khả thi, không thay
bằng cửa sổ khác.

## 2. Đơn vị quan sát và biến mục tiêu

**Đơn vị:** một tick 15 phút trên lưới lịch DEV `2022-01-01 00:00 → 2024-06-30 23:45`
(giờ VN, `TZ = UTC+7`, khớp `ledger.py`).

**Tick hợp lệ:** có ≥ 8 coin đồng thời có (a) `p_g015` từ `predwf_G015x26` và (b) nhãn với
`nBars_72h >= 288`. Tick không đủ 8 coin bị loại khỏi MỌI phép tính, kể cả mục false negative.
Số tick hợp lệ được báo cáo trước bảng kết quả.

**PRIMARY — `Y_tick`** = `mean(g1lite)` của **top-8 coin theo `score_g015` tăng dần**
(`score_g015 = 1 - p_g015`, thấp = tốt, đúng `ledger.py:55`) trong tick đó.
`g1lite` theo `ledger.py`: nếu `maxFav_72h >= 0.05` thì `maxFav_72h - min(0.5*maxFav_72h, 0.08)`,
ngược lại `retEnd_72h`.

**SECONDARY (báo cáo, KHÔNG dùng để chọn):**
- `Y2` = `P(maxFav_72h >= 0.07)` của top-8.
- `Y3` = `mean(g1lite)` của top-3.

## 3. ĐÚNG 5 ứng viên timing — không thêm cái thứ 6

`E[max nhiễu]` với N=5 là `1.79 × sd`. Danh sách đóng từ thời điểm commit này.

| # | tên | dựng thế nào | có sẵn tại thời điểm tick? |
|---|---|---|---|
| 1 | `p15` | `predReturn15M` tại tick, `wfo_gate_pred.csv` | CÓ — incumbent, biến bind của gate |
| 2 | `br_lag3` | cột `f_br_lag3` của `/home/ubuntu/featv2/GATE_BREADTH_DAILY.csv`, merge_asof **backward** theo `date` | xem §3.1 |
| 3 | `mkt_vol7` | `mean(vol_7d)` cross-section các coin trong tick, `feat_v2.parquet` (lưới GIỜ) merge_asof backward | CÓ |
| 4 | `mkt_dd7` | `mean(dd_7d)` cross-section các coin trong tick, cùng nguồn | CÓ |
| 5 | `p15_ma24h` | trung bình trượt 96 tick (24h) của `p15`, **trailing, gồm tick hiện tại** | CÓ |

### 3.1 Ghi trước một lỗ hổng của ứng viên 2

`gate_persist.py:26` — `f_br_lag3 = br.shift(3)`, đã kiểm số học: `corr(f_br_lag3, br.shift(+3)) = 1.0000`,
với tương lai `corr(..., br.shift(-3)) = -0.12` ⇒ đúng là **lag lùi**, không phải lead.

NHƯNG `br` tự nó là nhãn nhìn tới (`maxFav_72h >= 0.06`). `br` của ngày `D` dùng nhãn của các
tick trong `[D, D+1)`, mỗi nhãn nhìn 72h ⇒ cửa sổ đóng muộn nhất tại `D+4`. Lag 3 ngày ⇒ tại
tick ngày `D`, `f_br_lag3 = br(D-3)` có cửa sổ đóng tại `D+1` ⇒ **rò rỉ tối đa ~1 ngày**.

Xử lý đã chốt: `br_lag3` **vẫn dự thi đúng như đề bài**, và song song báo cáo một **chẩn đoán
KHÔNG dự thi** là `br_lag4` (= `br` của hàng ngày `D'` cuối cùng thoả `D' + 4 ngày <= t`), sạch
rò rỉ theo xây dựng. `br_lag4` **không được phép thắng** và không tính vào N=5.

`AUDIT_APPLIED` B8 ghi "IC +0.30 với breadth 3 ngày **tới**" — đó là IC với **target tương lai**
(cột `tgt`), một đại lượng khác hẳn `Y_tick`. Con số +0.30 KHÔNG phải dự đoán cho F4 và không
được dùng làm mốc so.

## 4. Tiêu chí PRIMARY và ngưỡng chấp nhận

**Thống kê thi đấu:** `S_v = |rank-IC|` = `|spearman(v, Y_tick)|` trên toàn DEV.
Dùng trị tuyệt đối vì hai trong năm ứng viên (`mkt_vol7`, `mkt_dd7`) không có dấu tiên nghiệm;
chốt một quy tắc chung cho cả năm để không phải chọn sau khi thấy số. **Rank-IC có dấu vẫn
được báo cáo đầy đủ** cho từng ứng viên.

**CI:** block bootstrap **khối 72h = 288 tick liên tiếp**, moving-block trên chuỗi tick đã sắp
thời gian, **2000 rep, seed 20260905**. Độ rộng CI nhân **`f = 1.21`** (`docs/result/COV_RESULT.md` §4,
hệ số coverage đã đo). Dùng **common random numbers**: mọi ứng viên tái mẫu trên CÙNG một bộ
2000 chỉ số khối ⇒ CI của HIỆU là CI của phân bố `S_v - S_p15` trên cùng bộ rep đó.

**Nhất quán dấu:** rank-IC có dấu tính riêng cho 2022 / 2023 / 2024 (2024 chỉ nửa đầu).

> **NGƯỠNG (chốt trước):** ứng viên `v` ĐÁNH BẠI incumbent khi và chỉ khi
> **(a)** CI95 (đã ×1.21) của `S_v − S_p15` **không chứa 0** và cận dưới > 0, **VÀ**
> **(b)** dấu rank-IC của `v` **giống nhau ở cả 2022, 2023, 2024**.
> Không đạt cả hai ⇒ **ghi null, `p15` giữ nguyên.** Không có hạng mục "thắng một phần".

## 5. Câu hỏi FALSE NEGATIVE — đo riêng, KHÔNG phải cuộc thi

Không có ngưỡng pass/fail. Chỉ định lượng, và bắt buộc báo **CẢ HAI** định nghĩa gate.

`F3_SUPPLY` giới hạn 3: `gate_dyn_ok` offline chỉ tái lập **61.5%** giờ-entry thật, còn
`p15 >= 0.008` tái lập **92.2%**. Vì vậy cấm chọn một định nghĩa.

- **Gate-A** (lỏng, tái lập 92.2%): tick MỞ ⟺ `p15 >= 0.008`.
- **Gate-B** (chặt, tái lập 61.5%): tick MỞ ⟺ có ≥1 coin trong tick thoả `p15 >= dyn_thr(score_g015)`,
  `dyn_thr` lấy từ `research/analysis/gate_cfg.py` (KHÔNG hardcode).

Với mỗi định nghĩa báo:
1. số tick MỞ / ĐÓNG, và `median(Y_tick | MỞ)` làm mốc `m`;
2. `q = P(Y_tick > m | ĐÓNG)` — bao nhiêu % tick-đóng vượt trung vị tick-mở;
3. **khối lượng cơ hội bị bỏ lỡ** = `q × (số tick ĐÓNG)`, và tỷ số của nó với `0.5 × (số tick MỞ)`;
4. phân vị `Y_tick` của hai nhóm (p10/p25/p50/p75/p90) để thấy hình dạng, không chỉ một con số.

Ghi trước: `q` gần 0.5 KHÔNG có nghĩa là "gate vô dụng" — nó có nghĩa là gate không tách được
`Y_tick` theo trung vị. Diễn giải P&L bị CẤM ở mục này (không có sim, `g1lite` không phải P&L).

## 6. Model tổ hợp — ĐÚNG MỘT, khai báo tại đây

Chỉ được train duy nhất model này; nếu không train thì ghi rõ là không train.

- Thuật toán: `xgboost.XGBRegressor`, **`device="cpu"`, `tree_method="hist"`** (GPU BỊ CẤM).
- Feature: **đúng 5 biến** ở §3, không thêm, không transform ngoài rank-normalize trong fold train.
- Target: `Y_tick`.
- WFO: theo **quý**; fold `k` train trên mọi quý `< k`, test trên quý `k`; quý đầu không test.
- **Purge 72h** hai phía quanh ranh giới fold (bỏ 288 tick mỗi bên).
- `n_estimators=300, max_depth=4, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8`,
  **`random_state=42`**, không early stopping (không có valid set sạch).
- Báo rank-IC out-of-sample của dự báo ghép, **cùng CI (block 72h, 2000 rep, seed 20260905, ×1.21)
  và cùng ngưỡng §4**. Model cũng phải thoả (a) và (b) mới được coi là đánh bại `p15`.

## 7. Cấm — vi phạm là sai, không phải lựa chọn

1. Không thêm ứng viên thứ 6 sau khi thấy kết quả. Không đổi `Y_tick`. Không đổi cửa sổ.
2. Không sửa file này sau commit đầu tiên. Sửa = huỷ toàn bộ F4.
3. Không chạy Java sim, không chạy VAL, không push, không xoá file của user, không GPU.
4. Equity/P&L KHÔNG phải tiêu chí và không xuất hiện trong phán quyết (`AGENT_RUNBOOK` §0.3).
5. Không đoán số. Confound không khử được ⇒ ghi "không kết luận được".
6. Null là kết quả hợp lệ và có giá trị.

## 8. Dự đoán ghi trước (để lần sau biết mình sai ở đâu)

1. `p15` sẽ có rank-IC dương và lớn nhất trong 5; không ứng viên nào đạt cả (a) và (b).
2. `p15_ma24h` sẽ gần `p15` nhưng thấp hơn — tín hiệu là mức tức thời, không phải xu hướng.
3. `q` ở Gate-A sẽ **> 0.40**, tức khối lượng cơ hội bỏ lỡ lớn về tuyệt đối, vì tick-đóng
   nhiều gấp ~18 lần tick-mở. Đây sẽ là con số đáng chú ý nhất của F4, không phải cuộc thi.
4. CI sau block bootstrap sẽ rộng hơn 0.0034 rất nhiều (§1.2).

Sai dự đoán nào thì ghi rõ dự đoán đó SAI trong `docs/experiment/F4_TIMING.md`.

## 9. Đầu ra

- Script: `research/analysis/f4_timing.py` (module `logging`, KHÔNG `print()`).
- Kết quả: `docs/experiment/F4_TIMING.md`.
- `docs/plan/QUEUE.md`: thêm dòng `F4 — DONE <commit>`.
