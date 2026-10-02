# PREREG_SHORT_BETANEUTRAL — short top-K8 (model nhãn ngược) vs long EW cùng tick, tách beta alt

Ngày **2026-10-02**, branch `module`. Nguồn: `docs/audit/AUDIT_SHORT_REVIEW_20261002.md` §10 (commit `a6867424`),
MASTER duyệt chạy **đúng 1 vòng**. Pre-reg này commit **TRƯỚC** khi đo (chưa có bất kỳ số spread/IC nào của vòng này).
0-sim, 0 kernel Kaggle, 0 Java, không sửa `.java`, không chạm 242/LIVE, **không chạm 2026**.

## 1. Giả thuyết

- **H1.** Kỹ năng xếp hạng của model short nhãn ngược (`ndown` 1,5 %/72h; rank-IC ≈ +0,052) là **alpha cross-section
  thật** bị beta alt che. Đo **beta-neutral** thì spread `short top-K8 + long EW cùng tick` **> 0 sau phí CẢ 2 chân +
  funding CẢ 2 chân**, ngoài CI, bền theo năm.
- **H0.** spread ≤ 0.

## 2. Dữ liệu (khoá, đã có sẵn)

| Thành phần | Đường dẫn | Ghi chú |
|---|---|---|
| bins score | `~/sm_pathexit/sm/OLD_ndown_S42/predict_wf_{16 fold 20220101..20251001}.bin` | slot 3 = head 72h (`short_model_score.read_bins`); recipe = SHORT42 |
| nhãn | `/home/ubuntu/ds_label15m/funding_label_*.pb` | `retEnd_72h`, `maxFav_72h`, `tHitFav_72h` (phút), `nBars_72h ≥ 288` |
| symbol map | `/home/ubuntu/claudedata/oi/symbol_map.csv` | (giống hệt `kaggle_oi_stage/symbol_map.csv`) |
| funding | `/tmp/fund_cache.npz` (Aerospike `test.funding_data`, exact) | cùng cache V3/V4 |

DEV 2022-01-01..2025-12-31. Nếu bins/nhãn/cache thiếu ⇒ **BLOCKED** (không train lại, không đổi bins).

## 3. Định nghĩa (khoá)

- **tick** = mỗi mốc quyết định `tEpochMs` (lưới 15 phút) có trong bins ∩ nhãn hợp lệ.
- **Cửa sổ đo chính:** tick `t` với `2022-01-01 ≤ t ≤ 2026-01-01 00:00 UTC − 72h` (= `t + 72h ≤ 1767225600000`) ⇒ toàn bộ
  cửa sổ giữ nằm trong DEV, **không** dùng giá/funding 2026. (Sanity §5 dùng đúng cửa sổ V3 `t < 1767225600000` để tái lập.)
- **Universe nhãn tại t:** mọi dòng nhãn có `symbol ∈ symbol_map`, `nBars_72h ≥ 288`, `retEnd_72h` hữu hạn, tại đúng `t`.
- **Tập ứng viên short tại t:** dòng thuộc bins ∩ universe nhãn, score hữu hạn, **qua N1b**: `r1 ≥ 0` với `r1` = rate của
  kỳ settle funding **kế tiếp sau t** (đúng định nghĩa V3, `Fund.compute`), `r1` hữu hạn.
- **Chân SHORT:** **top-K = 8 theo score trong tập ứng viên ĐÃ lọc N1b** (lọc trước, xếp hạng sau — đúng chữ §10 "top-K
  theo score **sau** lọc N1b"; khác cách V3 chọn-rồi-lọc). Cắt cứng **+30 %**: `pnl_s = −0,30` nếu `maxFav_72h ≥ 0,30`
  ngược lại `−retEnd_72h`. Funding chân short **exact theo coin**: `f_s = Σ rate trong (t, t+72h]` ⇒ short **NHẬN** khi rate>0
  (`+f_s`), cả cửa sổ 72h kể cả lệnh bị cắt (bảo thủ, như V3).
- **Chân LONG EW:** trung bình **đều** `retEnd_72h` của **mọi** symbol trong universe nhãn tại t (**không lọc**, không cắt):
  `R_EW(t)`. Funding chân long: `F_EW(t)` = trung bình `f_72h` của các symbol đó có funding hữu hạn; long **TRẢ** khi rate>0
  (`−F_EW`). Cùng notional với chân short (tổng short = tổng long).
- **Spread tại tick t** (một danh mục beta-neutral = short rổ K8 + long rổ EW):

  `spread(t) = mean_{i∈K8(t)}( pnl_s,i + f_s,i ) + R_EW(t) − F_EW(t) − 2 × 0,112 %`

  **Ghi chú dấu (sửa lỗi gõ của bản nháp TRƯỚC khi đo):** công thức nháp §10 viết `− mean_EW(ret_72h)`; với chân **LONG**
  EW, PnL chân long là **`+R_EW`** (nháp viết dấu trừ sẽ thành short cả 2 chân, cộng thêm beta, trái với H1 "tách beta").
  Dấu funding trong nháp (`+f_s − f̄_EW`) đã khớp với long EW. Bản khoá dùng `+R_EW`. Đây là sửa dấu duy nhất, không đổi
  cấu hình.
- **Phí:** 0,112 %/chân/vòng (phí `RATE_FEE` 1 lần + slip 2 chân, `RESULT_COST_TRUTH`), **× 2 chân = 0,224 %/vòng**.
  Stress: **0,150 %/chân ⇒ 0,300 %/vòng**.
- **Trung bình:** spread/lệnh = **trung bình theo tick** của `spread(t)` (mỗi tick 1 giá trị, như `_per_tick` của V3).
- **CI:** `short_model_score.ci_mean` — block lịch **72h** theo thời gian (cluster = block 72h), **NREP 2000**, **seed
  20260905**, percentile 2,5/97,5 trên chuỗi `spread(t)`; **×1,21** quanh mean (legacy). "Ngoài 0" = cả raw **và** ×1,21.
- **Theo năm:** mean `spread(t)` theo năm UTC của t, 2022/2023/2024/2025.
- **β:** OLS theo tick: (a) `β_short` = hệ số của `mean_{K8} retEnd_72h` (chưa cắt) trên `R_EW(t)` (kỳ vọng ≈ 1);
  (b) `β_spread` = hệ số của `spread(t)` trên `R_EW(t)` (kỳ vọng ≈ 0). Chỉ báo cáo.
- **IC theo năm:** rank-IC = Spearman(score, −retEnd_72h) **trong từng tick** trên **toàn bộ** bins ∩ universe nhãn (KHÔNG
  lọc N1b), rồi mean theo tick trong năm. Hạng không xử lý ties (score liên tục).
- **Directional đối chiếu (cùng tập K8 sau N1b):** `mean_{K8}(pnl_s + f_s) − 0,112 %` theo tick, CI, theo năm. Chỉ đối chiếu.
- **F3-bound (phụ, KHÔNG dùng cho verdict):** với lệnh bị cắt (`maxFav_72h ≥ 0,30`), funding short chỉ tính trong
  `(t, t + tHitFav_72h]` (`tHitFav_72h` = phút tới đỉnh ≥ +30 % ⇒ ≥ thời điểm chạm +30 %, nên vẫn bảo thủ); báo spread lại.

## 4. Cấu hình DUY NHẤT (khoá, không quét)

K = 8 · filter N1b (duy nhất; **không** chồng L1b′/K3/regime) · T = 72h · cắt +30 % · phí 0,112 %/chân × 2 · funding exact
2 chân · bins SHORT42 (`OLD_ndown_S42`) duy nhất. **Không** biến thể nào khác được chạy hay báo cáo.

## 5. Sanity bắt buộc (trước khi đọc số chính)

Tái lập **baseline V3** `base_k8_T72_C30` (không lọc; top-8 theo score trên toàn bins ∩ nhãn; cắt +30 %; cửa sổ V3
`t < 1767225600000`; `net_pre` = mean theo tick của `mean_{K8}(pnl_s) − 0,112 %`; `fund_mean` = mean `f_72h` theo dòng):

| Đại lượng | Mục tiêu (V3, `RESULT_SHORT_V3.md` §1) | Dung sai |
|---|---|---|
| `net_pre` | **+0,409 %** | ±0,03 pp ⇒ [+0,379; +0,439] % |
| `fund_mean` | **−0,580 %** | ±0,03 pp ⇒ [−0,610; −0,550] % |

Lệch bất kỳ ⇒ **VOID**: không báo số chính, RESULT ghi VOID + lý do. (Tham khảo, không phải cổng: V3 arm SHORT42 riêng
`/tmp/smv3.json` = net_pre +0,386 % · fund_mean −0,581 %; nếu bins `OLD_ndown_S42` trùng bins V3 thì phải khớp gần tuyệt đối.)

## 6. Luật GO / NO-GO (cố định, cơ học)

**GO-nghiên-cứu** ⇔ cả 5:

1. Sanity §5 **PASS**.
2. mean `spread` > 0 **và** CI raw **và** CI ×1,21 đều **> 0** (cận dưới > 0).
3. ≥ **3/4 năm** mean `spread` > 0.
4. rank-IC > 0 **cả 4 năm**.
5. Stress phí 0,150 %/chân: mean `spread_stress` > 0 (điểm ước lượng).

Thiếu bất kỳ ⇒ **NO-GO và ĐÓNG HƯỚNG SHORT trên dữ liệu hiện có** (chỉ mở lại khi có data mới: liquidation/L2 từ 09/2026
tích luỹ đủ forward). **Không** luật winrate. **Không** vòng "thử thêm biến thể" sau khi thấy số.
GO **chỉ** mở bước kế: đánh giá mức SỔ (long R4 + short sleeve) theo §9 MTM — **không** build đường SELL.

## 7. Cấm

Tune K/C/T/filter · thêm feature · dùng seed/bins khác để "chọn" · chạm 2026 · sửa `.java` · Java sim trên Oracle ·
Kaggle · báo số chính khi sanity VOID.

## 8. Ước tính trước (chống tự lừa)

Excess gross ~+0,34 %/72h − phí 2 chân 0,224 % ⇒ **~+0,1 %/72h**; nếu CI co ~5–8× như STATE thì half-width ~±0,08–0,12 %
⇒ **ngưỡng sát**; khả năng GO ~20–30 % (audit §10).

## 9. Sản phẩm

| File | Nội dung |
|---|---|
| `research/analysis/short_betaneutral_score.py` | chấm 0-sim (logging, argparse) |
| `docs/result/RESULT_SHORT_BETANEUTRAL.json` | số tổng hợp nhỏ |
| `docs/result/RESULT_SHORT_BETANEUTRAL.md` | verdict + bảng 5 điều kiện |
