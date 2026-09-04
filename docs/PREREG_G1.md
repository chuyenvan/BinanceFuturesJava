# PREREG_G1 — G015 huấn luyện lại ở horizon 72h (`G72`)

**Chốt trước khi train. Không sửa sau khi thấy số. Null hợp lệ và phải báo cáo.**

Ngày: 2026-09-05 (Oracle). Phạm vi: **DEV** `2022-01-01 → 2024-06-30` (GMT+7). Không VAL.
Không GPU. Không push.

## 0. Vấn đề — lỗi cấu trúc, không phải tinh chỉnh tham số

C2b trộn hai thang đo từ hai horizon:

| tầng | model | nhãn | horizon | vai trò |
|---|---|---|---|---|
| GIÁ TRỊ gate (`dyn_thr`, `symbolPred`) | `G015x26` — XGBClassifier 45 feature | `maxFav_4h >= 0.06` | **4h** | đặt ngưỡng + chia STRONG/WEAK |
| THỨ TỰ coin | `S1` — XGBRanker 9 feature | `rel5` (quintile trong tick của `g1lite − median`) | **72h** | chọn top-8 |
| vị thế thực tế | — | — | **tới 168h** | time-stop |

`build_map.py:28-45` giữ NGUYÊN multiset P(win) per-tick của G015x26 ⇒ **tầng đặt giá trị gate
đang chạy ở horizon 4h**, ngắn hơn cả horizon nhãn của selector (72h) lẫn thời gian giữ (168h).

**Động cơ (KHÔNG phải bằng chứng):** đo trên 970 lệnh thật của C2b, cùng công thức `g1lite`
chỉ đổi horizon: 4h spearman +0.258 / AUC 0.747; 24h +0.396 / 0.875; 72h +0.474 / 0.928.
Cùng horizon 72h đổi công thức: `maxFav` 0.472 · `g1lite` 0.474 · `ARM7` 0.476 · `pathq` 0.452
(trong nhiễu của nhau); chỉ `retEnd` 0.373 kém rõ. ⇒ horizon là trục có tác dụng, công thức
thì không.

⚠️ **Bảng trên bị nhiễm window overlap** — ROI hiện thực hoá tới 168h nên nhãn 72h dùng chung
nhiều đường giá hơn nhãn 4h. `docs/LABEL_ROI2_RESULT.md` mục 2 đã bị retract vì đúng lý do này.
**Không dùng bảng đó làm bằng chứng.** Bằng chứng phải đến từ phép đo trong pre-reg này.

## 1. Giả thuyết

**H1 (giai đoạn 1):** một G015 huấn luyện lại với nhãn ở horizon 72h xếp hạng **outcome 72h thật**
tốt hơn G015 nhãn 4h, trên cùng OOS DEV, cùng feature, cùng hyperparam, cùng seed.

**H2 (giai đoạn 2, chỉ chạy nếu cổng PASS):** thay thang giá trị gate bằng `G72` (S1 KHÔNG đổi)
làm GIẢM `TSloss%` và TĂNG `win%` mà không phá ràng buộc rủi ro.

⚠️ **Cảnh báo tự thân, ghi TRƯỚC khi thấy số:** H1 gần như hiển nhiên đúng — `G72` được train
trên chính họ nhãn dùng để chấm (`maxFav_72h`), `G4_repro` thì không. Giai đoạn 1 vì vậy là
**cổng kiểm tra đường ống**, KHÔNG phải bằng chứng kinh tế. Nó chỉ có quyền quyết định
"có chạy sim hay không". Một H1 PASS **không** được diễn giải là "72h tốt hơn".
Nếu H1 FAIL thì đường ống hoặc nhãn có lỗi, và dừng là đúng.

## 2. Cổng REPRO — chạy TRƯỚC, quan trọng nhất

Nếu không phân biệt được "đổi label" với "đổi pipeline" thì mọi kết quả giai đoạn 1 là vô nghĩa.

- Script: `research/pipeline/g72_train.py` = bản **sao nguyên văn** của
  `research/analysis/g015_rebuild.py` (bản đã sinh `predwf_G015_v2`, chứng minh byte-identical
  2 lần — `docs/G015_PROVENANCE.md §0`), chỉ thêm **tham số hoá nhãn qua env**
  (`G72_LABEL_H`, `G72_WIN`) với **mặc định = 4h / 0.06 = hành vi cũ**.
- Chạy `G4_repro` = script mới với **mặc định** (`G72_LABEL_H=4`, `G72_WIN=0.06`),
  `OUT_DIR=/home/ubuntu/g72/G4_repro`.
- So với `/home/ubuntu/predwf_G015_v2/` (10 file bins, sha256 trong `docs/G015_PROVENANCE.md §1`).

**Tiêu chí (chốt):**
1. **PRIMARY:** `spearman(pred_G4repro, pred_v2)` trên toàn bộ bản ghi 10 fold, khớp theo
   `(ts, symId)`. **< 0.99 ⇒ DỪNG TOÀN BỘ.** Không train `G72`, không chạy sim.
2. Phụ (báo cáo, không phải cổng): số fold byte-identical sha256 / 10. Kỳ vọng 10/10 vì
   pipeline gốc đã chứng minh deterministic; nếu spearman >= 0.99 mà không byte-identical thì
   ghi rõ và tiếp tục.

## 3. Biến thể `G72` — đổi ĐÚNG một thứ

Giữ nguyên: kiến trúc `XGBClassifier`, `n_estimators=400, max_depth=5, learning_rate=0.05,
subsample=0.8, colsample_bytree=0.8, min_child_weight=20, eval_metric=auc, tree_method=hist,
n_jobs=4, random_state=42`; 45 feature (40 Tool1 `f0..f39` + 5 OI, `merge_asof backward tol 2h`);
10 cutoff WFO `20220101..20240401`, OOS 3 tháng; **purge 72h**; TZ +7h; `TS_HI=2024-07-01`;
**CPU** (GPU BỊ CẤM — `AGENT_RUNBOOK` bẫy 7, `C2B_SPEC §2.4`).

Đổi duy nhất — nhãn:

| | `G4_repro` (= G015 hiện tại) | `G72` |
|---|---|---|
| nhãn | `maxFav_4h >= 0.06` | **`maxFav_72h >= 0.07`** |
| bộ lọc đủ bar | `nBars_4h >= 16` | `nBars_72h >= 288` |
| base rate (mẫu 1 file 2022Q2) | 0.0668 | 0.4165 |

`scale_pos_weight = (1-pos)/pos` giữ **nguyên công thức**; giá trị của nó đổi theo base rate —
đó là hệ quả của việc đổi nhãn, không phải tham số bị chỉnh tay.

Vì sao ngưỡng **0.07**: đúng `SIM_RATE_PROFIT_STOP_MARKET=0.07` trong `profiles/c2b_min.properties`
⇒ nhãn khớp đúng sự kiện hệ cần dự đoán ("lệnh này có ARM không"), không phải một số tự chọn.

## 4. Tập chấm điểm và outcome — chốt trước

- **Tập:** `/home/ubuntu/g015/pool/pool_dev.parquet` — **15,442,092** dòng
  `(ts, sym, p15, g1lite, p_old)`, `ts` từ `2021-12-31 17:00` đến `2024-06-30 16:45` UTC
  (= `2022-01-01 00:00 → 2024-06-30 23:45` GMT+7). Đây đúng là hợp của 10 fold OOS DEV.
  **Không thêm, không bớt dòng nào ngoài bước join nhãn dưới đây.**
- **Outcome PRIMARY:** `Y72 = 1[maxFav_72h >= 0.07]`, đọc từ `/home/ubuntu/label_15m/*.pb`,
  giữ `nBars_72h >= 288` và `maxFav_72h` không NaN. Dòng pool không join được nhãn thì **loại**,
  và **báo cáo tỉ lệ mất**.
- **Outcome SECONDARY (báo cáo, KHÔNG dùng để phán quyết):** `g1lite` (cột có sẵn trong pool).

**Thước đo:**

| # | thước | trên outcome | dùng để |
|---|---|---|---|
| M1 | **AUC** | `Y72` | **CỔNG GO/NO-GO** |
| M2 | spearman | `Y72` | báo cáo |
| M3 | spearman | `g1lite` | báo cáo |

## 5. Thống kê — block bootstrap, chốt trước

- **Khối:** 72h theo lịch (`block_id = floor((ts - ts_min) / 72h)`), ~304 khối trên DEV.
  Lý do: `docs/F4_TIMING.md` — `n_eff` tỉ lệ với **số khối 72h** (độ dài lịch sử), KHÔNG với
  số dòng; `n = 15.4M` dòng là ảo tưởng power.
- **2000 rep**, lấy khối **có hoàn lại**, `seed = 20260906`, **common random numbers** giữa
  `G72` và `G4_repro` ⇒ hiệu là **ghép cặp**.
- CI95 = percentile 2.5/97.5, sau đó **nhân độ rộng ×1.21** quanh điểm ước lượng
  (`docs/COV_RESULT.md`: `sd_boot` của họ chuỗi này hụt ~21%):
  `[pt − 1.21·(pt−lo), pt + 1.21·(hi−pt)]`.

**Cách tính để chạy được 2000 rep trên 15.4M dòng (chốt trước, là một phần định nghĩa thước đo):**
- **AUC:** rời rạc hoá điểm số vào **4096 bin phân vị** tính MỘT LẦN trên toàn mẫu gộp cả hai
  model; mỗi khối lưu ma trận đếm `(4096 × 2)`. AUC của một rep tính **chính xác** từ tổng đếm
  bằng công thức Mann–Whitney có xử lý ties (`0.5` trong bin). Báo cáo sai số do binning bằng
  cách so AUC-binned với AUC-chính-xác trên toàn mẫu (1 lần).
- **Spearman:** rank-transform `pred`, `Y72`, `g1lite` **một lần trên toàn mẫu**, rồi tính
  **Pearson** trên mẫu resample bằng tổng thống kê đủ theo khối
  (`n, Σx, Σy, Σx², Σy², Σxy`). Đây là định nghĩa được chốt; nó không tính lại rank trong từng rep.

## 6. CỔNG GO/NO-GO — chốt trước, không thương lượng

Sang giai đoạn 2 **chỉ khi CẢ HAI**:
1. `AUC(G72, Y72) > AUC(G4_repro, Y72)` (điểm ước lượng), **VÀ**
2. CI95 (đã ×1.21) của **hiệu ghép cặp** `d = AUC(G72,Y72) − AUC(G4_repro,Y72)`
   **không chứa 0**.

Không đạt ⇒ **null, dừng, KHÔNG chạy sim nào.**
M2/M3 không có quyền phủ quyết và không có quyền cứu.

## 7. Giai đoạn 2 — chỉ phác thảo ở đây, pre-reg riêng

Nếu cổng PASS: sinh bins `G72` → `build_map.py` với **đúng thứ tự S1 của C2b** (`pred_s1a2`,
S1 KHÔNG đổi) → **ĐÚNG 2 sim run**: `G1_parity` (bins G015x26 cũ, phải byte-identical C2b:
md5 `8f7afdfb27b15f5b6d4c886700def93c`, `b:60390`, 970 lệnh) và `G1_g72` (bins mới).
Chi tiết + tiêu chí PRIMARY viết ở `docs/PREREG_G1_SIM.md`, **commit trước khi chạy**.
Parity fail ⇒ dừng.

## 8. Điều KHÔNG được làm

- Không chạy VAL. Không GPU. Không push. Không xoá file của user.
- Không quá 2 sim run. **S1 không đổi.** Không đổi bất kỳ param exit/gate/sizing nào.
- Không sửa file này sau khi thấy số. Nếu phát hiện lỗi thiết kế thì ghi vào phần
  "giới hạn phép đo" của `docs/G1_HORIZON.md`, không sửa ngược pre-reg.
- Không dùng equity làm tiêu chí (`sd(ΔCAGR)` = 2.57pp; `E[max nhiễu]` N=50 = +7.2pp;
  DEV đã ~125 run). Equity báo riêng, dán nhãn "không phải tiêu chí".
- 1 slot JVM, `pgrep java` rỗng, `df -h /` trước khi build (dưới 5G ⇒ dừng), `rm -rf $DS` sau.

## 9. Giá trị hạ tầng — kết luận RIÊNG, không trộn với PRIMARY

Chốt trước: dù giai đoạn 1 hay 2 ra null, `G72` vẫn có giá trị hạ tầng độc lập:
`predwf_G015x26` **không reproduce được** (mất bản export Tool1 2021 — `docs/G015X26_PROVENANCE.md §1`),
là single point of failure của baseline, và **không có bin nào trước `20220101`** nên chặn việc
mở DEV về 2021. Một model G015 train hôm nay thì reproduce được và train được trên 2021.
Kết luận này **không được** dùng để biện minh cho việc chấp nhận `G72` vào baseline nếu PRIMARY
không đạt.

## 10. Kết quả sẽ ghi ở đâu

`docs/G1_HORIZON.md`: cổng REPRO → giai đoạn 1 + CI → cổng GO/NO-GO → (giai đoạn 2 nếu có) →
phán quyết → mục "giá trị hạ tầng" riêng → "giới hạn phép đo" gồm caveat window overlap.
Script: `research/pipeline/g72_train.py`, `research/analysis/g1_horizon_eval.py`.
Cập nhật `docs/QUEUE.md`.
