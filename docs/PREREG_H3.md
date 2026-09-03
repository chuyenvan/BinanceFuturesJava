# PRE-REG H3 — ĐẦU TỰ TIN TUYỆT ĐỐI (viết TRƯỚC khi chạy, 2026-09-03)

## Vì sao
Gate dùng **giá trị tuyệt đối** của score selector: `dyn_thr = 0.008 * max(0.26787, score/0.15 * 1.2876)` — **chi co can duoi, KHONG co tran** (0.214% .. 2.206%).
Vì thế mọi model mới đều phải bị quantile-map về phân phối của G015 để gate cư xử y hệt ⇒ **không cải thiện được phần tuyệt đối**.

Đo trên ledger v3 (15,442,092 dòng / 86,971 tick, DEV 2021-04→2024-06):

| score G015 (thấp = tự tin) | n | g1lite TB | >5% | admit |
|---|---|---|---|---|
| <0.10 | 1,171 | +9.18% | 67.2% | 99.7% |
| 0.10–0.20 | 28,288 | +8.54% | 56.2% | 54.9% |
| **0.20–0.30** | **181,925** | **+6.33%** | **48.9%** | **6.7%** |
| ≥0.30 | 15,230,708 | +1.33% | 23.4% | 0.1% |

- 60.19% số dòng được admit đến từ nhóm `score<0.30` = 1.37% pool.
- Hiệu chuẩn G015 **đơn điệu hoàn hảo** (20/20 bucket tăng) nhưng **spearman(p_g015, g1lite) = 0.1675** — xếp đúng chiều, phân biệt yếu.
- Trần lý thuyết: gate với score thật admit 0.3116% ở g1lite +0.0910; gate với score ORACLE admit 7.8855% ở +0.2115.

Nới ngưỡng cho **mọi** coin đã thử và fail (H1a `MIN_MOMENTUM_15M` 0.008→0.006: DD −21→−44; H1b `PREDICT_SYMBOL_RATE_MAX` 0.15→0.30: 3678 lệnh, fail) vì lệnh thêm vào **dồn cụm theo thời gian** trong regime xấu. Một đầu tuyệt đối **tốt hơn** thì nới có chọn lọc và tự từ chối trong regime xấu ⇒ không mắc lỗi đó.

> **DINH CHINH 2026-09-03 (loi ghi chep, khong phai doi code).** Ban pre-reg dau tien cua muc nay
> viet `dyn_thr = 0.008 x clamp(score/0.15 x 1.2876, 0.26787, 2.14135)`, tuc co TRAN 1.713%. SAI:
> `AIRejectFilter` chi co can duoi (`Math.max(AI_DYNAMIC_MIN, scale)`), nguong tang don dieu tan 2.206%.
> `AI_DYNAMIC_MAX` la tran UNG VIEN o tang 1 selector, khong phai tran cua nguong; tang 1 con bi
> bo qua khi `SELECTOR_RANK_TOPK>0` (C2b: 8). `ledger.py`/`ledger3.py` tinh `dyn_thr` bang cong thuc
> co tran nen **danh gia THAP nguong that trong dai score (0.2494, 0.3212]**; cac so admit/g1lite
> duoi day da duoc DO LAI bang cong thuc dung (xem muc "Do lai" o cuoi file).

## Giả thuyết
Một model xác suất **có hiệu chuẩn** thay `p_g015` sẽ (a) phân biệt tốt hơn và (b) khi cắm vào đúng công thức gate cũ, cho **nhiều lệnh hơn ở chất lượng không kém**.

## Thiết kế
- Dữ liệu: **CHỈ DEV**. `cand_dev3.parquet` (mọi tick) + `feat_v2.parquet` + `path_labels.parquet`. Không đụng bất kỳ file VALIDATION nào.
- Nhãn: `y = 1[g1lite > 0.05]` (nhị phân, tuyệt đối — cố ý KHÔNG cross-sectional, vì vai trò của đầu này là mức tuyệt đối).
- WFO 10 cutoff `20220101…20240401`, purge 72h, `assert tr.ts.max() < cutoff`. OOS = quý kế tiếp.
- Model: XGBClassifier, `device=cuda`, `objective=binary:logistic`, `eval_metric=logloss`, 400 cây, depth 5, lr 0.05, `min_child_weight=100`, subsample 0.8, colsample 0.8, seed 42.
- **Hai biến thể, không hơn** (giới hạn multiple testing):
  - **A3a** = 9 feature V3 + `p15`. Đầu ĐỘC LẬP, không nhìn G015.
  - **A3b** = A3a + `p_g015`. Đầu XẾP CHỒNG lên G015.
- Đối chứng bắt buộc: **shuffle-label** với permutation ĐỘC LẬP từng tick (lỗi cũ: `groupby.transform(sample(random_state=1))` cho cùng permutation với group cùng kích thước ⇒ giữ bias thứ tự dòng).

## Tiêu chí (chốt TRƯỚC, không sửa sau khi thấy kết quả)

**Cổng 1 — offline, phải đạt HẾT thì mới được chạy sim:**
1. Phân biệt: `spearman(pred, g1lite)` OOS ≥ **0.2175** (= 0.1675 của G015 + 0.05).
2. Hiệu chuẩn: Brier score OOS **thấp hơn** Brier của `p_g015`; và trên 20 bucket, `max|pred_TB − observed|` ≤ **0.05**.
3. Gate offline (cắm score mới vào ĐÚNG công thức `dyn_thr` cũ): so với G015 (admit 0.3116%, g1lite admit +0.0910), phải đạt **cả hai**: admit ≥ 0.3116% **và** g1lite của hàng admit ≥ +0.0910. (Nhiều hơn mà chất lượng không kém.)
4. Shuffle-label: spearman ≤ 0.02 và g1lite của hàng admit ≈ trung bình pool (±0.01). Nếu shuffle cũng "thắng" ⇒ có leak, DỪNG.
5. Dương ở **cả 3 năm** 2022, 2023, 2024 cho tiêu chí 1.

**Cổng 2 — sim trên Oracle (chỉ chạy nếu Cổng 1 đạt):** thay C2b chỉ khi đạt HẾT:
- CAGR ≥ **C2b + 2.0pp**
- maxDD **không tệ hơn 2pp** so với C2b và ≤ 15%
- quý dương ≥ **8/10**
- 2022 ≥ 0%

Không đạt ⇒ ĐÓNG nhánh H3, ghi lại, không dò tham số thêm.

**VALIDATION:** không chạm trong toàn bộ H3. Chỉ khi Cổng 2 đạt mới bàn tới, và phải cảnh báo 3 lần theo GUARDRAIL L3.

## Đầu ra
- `/kaggle/working/pred_h3a.parquet`, `pred_h3b.parquet` — cột `ts, sym, p_abs` (OOS 10 fold).
- `/kaggle/working/h3_metrics.json` — toàn bộ số của Cổng 1.
- Kéo về Oracle: `kaggle kernels output chuyendinh/h3-abs-head-gpu -p /home/ubuntu/ledger/h3`
