# REVIEW_GATE_FEATLABEL — Có nên chỉnh `FEATURES`/`LABEL` của GATE (model market 33 feature) để mở gate không?

**Ngày:** 2026-09-30 · **Nhánh:** `module` · **Loại:** CHỈ ĐỌC + THIẾT KẾ (**0 train / 0 sim / 0 GPU**).
**Câu hỏi owner:** *"ra lại xem có nên điều chỉnh features, label để tối ưu gate không. cái model market đang dùng 33 features ấy"*.
**Kế thừa:** `docs/decisions/0013-giu-g2-chuyen-ofi.md` · `docs/plan/SUGGEST_DOUBLE_ENTRIES.md` (`8c0cd751`) · `RESULT_DOUBLE_ENTRIES.md` (`60384406`).
**Ràng buộc:** không chạm production/`242`/ONNX/`NUM_FEATURES`/`extractFeatures45`/LIVE · DEV ≤ 2025-12-31 · không push file dữ liệu.

---

## 0. TRẢ LỜI THẲNG

> **NULL.** Điều chỉnh `FEATURES`/`LABEL` của gate **KHÔNG** phải là đường để *mở gate (nhiều sự kiện hơn) mà giữ chất lượng*.
> Ba lý do, có số:
>
> 1. **Cơ học — dưới baseline `G2` số sự kiện KHÔNG do model quyết.** `G2` = gate rolling **`MODE=ratio`**:
>    `r = p15/(max(DYN_MIN, sp/SCORE_BASE·DYN_MULT)·SCALE)`, `PASS ⟺ r > q_t`, `q_t` = phân vị `pct` cuộn 90 ngày **của chính `r`**
>    (comment gốc: *"r đã chuẩn hoá theo score selector ⇒ tỉ lệ pass gần hằng số theo thời gian"*, `GateRollingRatio.java:19-24`).
>    ⇒ **mọi thay đổi chỉ làm DỊCH/ĐỔI THANG `p15` bị `q_t` hấp thụ** (tỉ lệ pass ≈ `1−pct` bất kể hiệu chuẩn model).
>    Núm `n` dưới `G2` là **`SIM_GATE_ROLLING_PCT` (config)**, không phải model. Kênh duy nhất còn lại của model là **XẾP HẠNG** → chất lượng (`T3`), không phải số.
> 2. **Đo — IC tốt hơn KHÔNG chuyển thành sim.** `RESULT_GATEFEAT` (`d01d59a0`): bỏ 6 feature ⇒ IC OOS **0,5335 → 0,5494 (+0,0159, P=1.000)** nhưng
>    sim 48 tháng **0/5 rate ngoài CI** (equity 107.101 vs 111.428, **−3,9 %**) ⇒ **giữ nguyên 33 feature**.
> 3. **Đo — đổi LABEL làm gate MỞ 2× thì chất lượng VỠ.** `RESULT_GATE_TOPK_LABEL_SIM` (`0d0bdd5c`): label = kết cục thật top-K S1 ⇒
>    `n_pass 1442 vs 841` (long hơn 2×) nhưng **4/5 rate chất lượng ngoài CI hướng XẤU** + FAIL ràng buộc cứng (2025 âm −10,35 %, UW 418, maxDD −20,81 %), equity −51 %.
>    Và `RESULT_GATE_H72` (`d39f0158`): label 4h→72h ⇒ **4/5 rate ngoài CI hướng xấu** ⇒ LOẠI.
>
> **Nút thắt thật:** (a) ở **LIVE** = ngưỡng tuyệt đối nằm ngoài support của **regime 2026 yên ắng** — và `PASS2` chứng minh **không phải lỗi feature/pipeline**;
> (b) ở **DEV/sim (G2)** = **burstiness của thị trường** (gate đóng ~56 % số tuần vì *không có tín hiệu*, `OFI_V3_EVENT2`: coverage 43,6 %, 102/234 tuần mở; `K_DENSITY`: gap dài nhất **129,24 ngày giống hệt** ở K=8/12/16).
> Cả hai **KHÔNG** sửa được bằng features/label của gate model.
>
> ⇒ **Không đề xuất đổi 33 feature và không đề xuất đổi label gate.** Cửa duy nhất còn là **nguồn sự kiện thứ 2** (đã chọn, `0013`) — và OFI V3 vừa **NO-GO** (`d6f2bbba`).

---

## 1. VIỆC 1 — INVENTORY: MỌI VÒNG ĐÃ THỬ TRÊN TRỤC **FEATURES / LABEL CỦA GATE**

Tách rõ 3 trục. Cột "trục" ghi **(i) feature** · **(ii) label** · **(iii) ngưỡng/calib** (*KHÔNG phải* features/label).

### (i) FEATURE của gate (thêm/bớt)

| # | vòng | commit | làm gì | kết quả THẬT | kết luận đã chốt |
|---|---|---|---|---|---|
| F1 | `RESULT_GATEFEAT` + `PREREG_GATEFEAT` | kq `d01d59a0` · prereg `8fc7d90d` | ablation **33 feature V3FULL** của gate p15, WFO OOS 19 fold DEV, IC spearman de-overlap 15m; CYC1–CYC7 + COMBO + SIM48 | STAGE0 IC **0,5335**. BỎ được: `rsi14` (+0,0013), `monthOfYear` (+0,0144), `fundingRateRaw` (+0,0024); GIỮ: `basketVolSpike` (−0,0015), `basketMomentum1H` (−0,0011), `momentumAcceleration` (−0,0042). CYC_COMBO 30f **IC 0,5483 (+0,0148)**; CYC7 27f **IC 0,5494 (+0,0159)**. **SIM48 `X1_C3_FULL_GF27` vs parity: 0/5 rate ngoài CI**, equity 107.101 vs 111.428 | **GIỮ 33 feature** vào sản xuất. *"IC OOS là điều kiện CẦN, KHÔNG đủ"* |
| F2 | (đối chiếu) `RESULT_FEAT_ADD_V1` + `PREREG_FEAT_ADD_V1` | kq `a3f0d14a` · prereg `672350e9` | thêm feature — nhưng là **selector 45/26 cột** (G015), KHÔNG phải gate | V1 (26 cột) trên G2+FLAT3: **T1 FAIL** (UW 353 > 250; 2022 −1,01 %), ΔCAGR −5,48 pp (CI âm) ⇒ loại | **KHÁC TRỤC** (selector) — không dùng làm bằng chứng cho gate |
| F3 | (đối chiếu) `RESULT_FEAT_CUT_RVOL15M` + `PREREG_FEAT_CUT_RVOL15M` + `PREREG_FEAT_ABLATION` | kq `376810aa` · prereg `76d9ba06` | cắt `rvol15m` — **selector 45 cột**, KHÔNG phải gate | Cổng tầng model KÉM rõ (Δq −0,00201, Δlift@8 −0,00274, cả 2 ngoài CI) ⇒ DỪNG, **giữ rvol15m** | **KHÁC TRỤC** (selector) |

**Kết luận trục (i):** trên trục feature **của gate** chỉ có **đúng 1 vòng (F1)** đã chạy, và nó đã **đóng**: bỏ 6/33 feature làm IC tăng có ý nghĩa nhưng **sim không cải thiện** ⇒ giữ 33.

### (ii) LABEL của gate (định nghĩa target)

| # | vòng | commit | label thử | kết quả THẬT | kết luận đã chốt |
|---|---|---|---|---|---|
| L1 | `RESULT_GATE_H72` + `PREREG_GATE_H72` | `d39f0158` | horizon **72h** (`retEnd_72h>0.015`) thay 4h | proxy: rank-IC vs `g1lite` **−0,01277 vs +0,14412** (Δ **−0,15689** ngoài CI). Sim 48m: **4/5 rate chất lượng ngoài CI hướng XẤU** (win% −9,30 pp; TSloss +12,13 pp) ⇒ **XẤU HƠN RÕ** | **LOẠI** (không chạy thêm) |
| L2 | `RESULT_GATE_TOPK_LABEL` + `RESULT_GATE_TOPK_LABEL_SIM` + `PREREG_GATE_TOPK_LABEL` | offline `884031eb` · sim `0d0bdd5c` · prereg `70e8d8ff` | label = **kết cục THẬT của top-K S1** (`y=(g1lite>0)`), population = top-K S1 | offline AUC **0,590 vs 0,563** (+0,027 nhưng **2024 kém hơn** −0,012). Sim 18-fold (T170): gate **LONG HƠN ~2×** (`n_pass` 1442 vs 841, mean p 0,67 vs 0,45) ⇒ **4/5 rate ngoài CI hướng XẤU** + FAIL ràng buộc cứng; equity **54.077 vs 111.070 (−51 %)** | **LOẠI — giữ T170** |
| L3 | `RESULT_LABEL_NETTHR` + `PREREG_LABEL_NETTHR` | kq `557bf3f9` · prereg `1cdacdc2` | ngưỡng nhãn **NET_THR** 0,010/0,015/0,020 (selector G015) | M_010: ΔrankIC **+0,00800** (16/16 fold) NHƯNG lift@8 **−0,05948** (CI âm), AUC −0,0144 ⇒ **không qua cổng ⇒ không sim**. Kết: *"label-threshold = tradeoff vol-tilt, KHÔNG phải lever ranking miễn phí"* | **KHÁC TRỤC** (selector) nhưng **cùng họ chứng cứ**: đổi ngưỡng nhãn không phải lever |
| L4 | `LABELH_RESULT` + `PREREG_LABELH` | kq `1a49abf1` · prereg `e22cbc93` | horizon nhãn selector **72h→4h** | 3 tiêu chí đều **không tách được khỏi 0** ⇒ không khác biệt đo được | **KHÁC TRỤC** (selector) |
| L5 | `RESULT_P15_SOURCE` + `PREREG_P15_SOURCE` · `RESULT_FEAT_DIFF_PASS1` · `RESULT_FEATDIFF_PASS2` | `bcfa83b8` · `26e4b3fb` · `d024f310` | *(không đổi label — kiểm **nguồn/thang đo** của p15 live)* | xem §2.4 | **nguồn p15 = OK khi kiểm cùng-regime** |

**Kết luận trục (ii):** cả **2 label gate** đã thử (horizon dài hơn; kết cục trade thật) **đều XẤU**; và L2 chính là phép thử "gate mở 2× mà giữ chất lượng" — **đã trả lời KHÔNG** (trên nền T170 ngưỡng cứng).

### (iii) NGƯỠNG / CALIB — **KHÔNG phải** features/label (ghi để không lẫn trục)

| # | vòng | commit | kết quả THẬT | kết luận |
|---|---|---|---|---|
| T1 | `RESULT_GATESCALE` + `PREREG_GATESCALE` | `1985a81` | scale 0,80/1,30/1,70 (nền X1_C3_FULL, ngưỡng cứng): L80 = n 3462 nhưng 3 rate chất lượng **ngoài CI xấu**; không điểm nào vượt ngưỡng | NULL |
| T2 | `RESULT_GATE_CALIB` + `PREREG_GATE_CALIB` | `52f6123` | 1,30 / 2,10 quanh T170: **0/5 rate ngoài CI** cả hai; T130 còn FAIL ràng buộc cứng (UW 221 > 200) | NULL — giữ T170 |
| T3 | `RESULT_GATEDYN` + `RESULT_GATEDYN2` + `PREREG_GATEDYN/GATEDYN2` | `3cdccd0`, `1c1ecca` | rolling percentile: GD92 (n 2355, CV quý 0,518) → về sau **D1/D2** |
| T4 | `RESULT_DOUBLE_ENTRIES` + `RESULT_GD92_R4_P3` | `60384406`, `68a2836` | **`D2` (`pct 0,92` + `scale 1,00`) = n 4287 (2,1×) nhưng FAIL CẢ 4 TẦNG** (UW 278 · q\* 10,2 · top-1 26,03 % · win −4,43 pp · TSloss +6,18 pp · Calmar 1,400) | **⚠️ VẠCH CẢNH BÁO** — mở gate bằng config ⇒ vỡ T3 |
| T5 | `RESULT_FLATGATE` · `RESULT_GATE_RECAL` · `RESULT_GATE_ROOTCAUSE` | `371c49c0` | phẳng/quantile-cuộn trên nguồn live: **0/3 PASS** (UW 568–773; 3/5 rate ngoài CI) | ĐÓNG |
| T6 | `RESULT_REGIME_GATE` · `RESULT_BREADTH_GATE_SIM` | `9c5b74d`, `83f5457` | regime-adaptive MA200 **PASS** (CAGR 32,95 vs 29,27; maxDD −11,84) nhưng **FAIL UW 2025** (223 > 200) | NULL ở ràng buộc cứng |
| T7 | `RESULT_GATEDYN2` → `G2` = baseline (`profiles/g2_flat3.properties`) | `a1008f35` | `pct 0,99995083`/90 ngày: n **2509**, PASS 4 tầng | **BASELINE hiện hành** |

---

## 2. VIỆC 2 — ĐÁNH GIÁ: CÒN CỬA NÀO?

### 2.1 FEATURE — feature chưa thử, có cơ sở mở gate?

33 feature hiện có đã phủ: momentum(6+accel) · trend(2) · vol(4+termStructure) · **breadth(5)** · rsi/volumeSpike/distMA20 · **funding(3)** · calendar(4) · basket(4).
Có cơ sở về **độ lớn** nhưng **chưa có ở gate**:

| ứng viên (market-level) | cơ sở | ước lượng ΔIC | ước lượng ΔSỐ SỰ KIỆN (mở gate) |
|---|---|---|---|
| **OI tổng hợp** (`oi_delta`, `oi_z` market) | selector 45 cột dùng `oi_delta24h`/`oi_z`; trong `FEAT_CUT_RVOL15M §3` `oi_delta24h` hấp thụ **+3,94 pp** gain khi cắt rvol15m ⇒ OI mang thông tin độ lớn | ~ **≤ +0,01** (cùng bậc các feature yếu; F1 cho ±0,002–0,015/feature) | **≈ 0** — dưới `G2` tỉ lệ pass do `pct` quyết (§0.1); dưới ngưỡng cứng thì **F1 đã cho thấy IC tăng ≠ thêm lệnh** |
| **liquidity/turnover market** | `RESULT_COST_LIQUIDITY` (`cd5e758`): thanh khoản **không** dự báo chất lượng (rho ≈ 0) | ~0 | ~0 |
| **regime/breadth bổ sung** | đã có 5 feature breadth + `btcDominance`; `RESULT_BREADTH_GATE_SIM` thử **regime theo breadth** và **không pass ràng buộc cứng** | ~0–0,005 | ~0 |
| **order-flow imbalance (OFI)** | ứng viên mạnh nhất — nhưng là **nguồn sự kiện thứ 2**, KHÔNG phải feature của gate market | — | **đã đo: NO-GO** (`d6f2bbba`: 99,95 % pick OFI nằm trong pool S1; 293 entry thật/4 năm; net âm) |

**Chi phí cái rẻ nhất (OI market-level):** phải sửa **extractor Java + replay Aerospike hàng chục giờ** (chính `PREREG_GATEFEAT §1` đã khai: thêm feature ngoài store = đổi extractor + replay, cần pre-reg riêng + owner chỉ định).
⇒ **Không đáng**: kỳ vọng ΔIC ≤ 0,01 (dưới ngưỡng nhiễu retrain ~0,0007 nhưng cùng bậc F1) và **kênh "mở gate" ≈ 0**.

### 2.2 LABEL — định nghĩa CHƯA thử, cái nào đổi được BIÊN QUYẾT ĐỊNH?

| định nghĩa chưa thử | có đổi được biên (mở gate) không? |
|---|---|
| **net-of-cost tradeability** (`y = net sau 0,4 % > 0`) | Chỉ **dịch/đổi thang** p ⇒ dưới `G2` **bị `q_t` hấp thụ**; dưới ngưỡng cứng thì **cùng họ L3** (NET_THR: IC↑ nhưng lift@8↓) ⇒ **không mở gate mà giữ chất lượng** |
| **label = PnL của ĐÚNG luật thoát (FLAT3/TS) trên top-K S1** | ≈ **L2 đã làm** (label = `g1lite` = kết cục trade thật) ⇒ đã đo: **gate mở 2× nhưng vỡ chất lượng**. Chỉ khác là xấp xỉ exit (`g1lite` 5 %/72h vs FLAT3). Bản "đúng bit-exact" đắt (cần `path_labels.g1_replay` chỉ có ở tập lấy mẫu) và **kỳ vọng cùng dấu** |
| **horizon khác** | L1 đã quét đúng chiều "dài hơn" (4h→72h) ⇒ **XẤU HƠN**; `LABEL_ROI2/3` cho thấy 72h **tương quan tốt nhất với ROI thật** ⇒ đã ở đỉnh, không còn dư địa |
| **magnitude/quantile label** (dự báo biên độ thay vì dấu) | Đây là **chỗ duy nhất còn trống về mặt định nghĩa** — nhưng nó chỉ tác động **xếp hạng** (không phải hiệu chuẩn) ⇒ §2.3 |

**Trả lời thẳng:** **KHÔNG có định nghĩa label nào đổi được BIÊN QUYẾT ĐỊNH (mở gate) mà giữ T3.** Cái duy nhất đổi được biên là **ngưỡng** (`pct`/`scale`) — và **mọi lần mở ngưỡng đã đo đều vỡ T3** (`D2`, `G1`, `B3/B4`, GDV2 W30; §1.iii).

### 2.3 ĐÁNH ĐỔI THẬT (cảnh báo `D2`)

Mở gate ⇒ chất lượng đi đâu, bằng số:

| vòng | n | chất lượng vs baseline |
|---|---|---|
| `D2` (`pct 0,92`+`scale 1,00`) | **4287 (2,1×)** | win% −4,43 pp · TSloss% +6,18 pp · UW 278 · Calmar 1,400 · **FAIL 4/4 tầng** |
| `GATE_TOPK_LABEL` (đổi label) | `n_pass` 1442 vs 841 | equity **−51 %** · FAIL ràng buộc cứng |
| `GATESCALE L80` (scale 0,80) | 3462 | 3 rate chất lượng **ngoài CI xấu** |
| `GATE_H72` (label 72h) | 2815 | 4/5 rate ngoài CI **hướng xấu** |
| GDV2 `W30` | 3199 | **FAIL 4/4** (2022 âm, UW 472,6) |

⇒ **Quy luật bất biến qua MỌI trục** (feature/label/ngưỡng): mở ⇒ n↑ ⇒ T3/T1 vỡ. **Không có ngoại lệ nào đã đo.**

### 2.4 ⚠️ NÚT THẮT: MODEL GATE hay NGUỒN/THANG ĐO p15 CỦA LIVE?

Đây là câu phải trả lời thẳng. **Có DIỄN BIẾN quan trọng giữa hai vòng:**

- **`RESULT_GATE_ROOTCAUSE`** (`b65a19a0`, prereg `371c49c0`, 27/09): `S_live` (242, 8996 mẫu, 12/08–27/09/2026) vs `S_dev` (2.500.260 mẫu) **lệch HÌNH DẠNG**: `D=11,26`; thân affine `live ≈ 0,33 + 1,07·dev` nhưng **đuôi bị cắt** (live max **2,30 %** vs DEV 12,261 %). Kết luận: **ngưỡng phải tính từ nguồn LIVE**; phương án A (phân vị cuộn) **0/3 PASS** ⇒ ĐÓNG.
- **`RESULT_FEATDIFF_PASS2`** (`d024f310`, prereg `2f24fe1`, 28/09) — **kiểm CÙNG PHÚT (regime-matched)**: `p15` LIVE 2026-09-28 (n=556) **0,9426 %** vs DEV tái tạo **cùng phút** **0,9484 %** — lệch **0,0058 pp**; và `max` LIVE **1,2633 %** ≈ **p99 của chính 2026-Q3** (1,244 %).
  ⇒ **PASS2 LẬT ngược cách đọc "nguồn bị hỏng":** p15 live **bình thường**; cái làm p15 "hẹp" là **REGIME 2026 yên ắng**, không phải feature/pipeline/scale.
- **`RESULT_P15_SOURCE`** (`bcfa83b8`): "scaler thiếu" là **red herring** (áp scaler còn NÉN ~8–10×).

**Trả lời (4):**
1. **Trên LIVE:** nút thắt **KHÔNG phải model gate, và cũng KHÔNG (nữa) phải "nguồn/thang đo bị hỏng"** — mà là **ngưỡng tuyệt đối 2,947–3,760 % nằm NGOÀI support của regime hiện tại**. `PASS2` chứng minh p15 có đơn vị/thang đo ĐÚNG khi kiểm cùng-regime ⇒ features/label của gate **chỉ là phụ**; cái cần sửa là **cách biểu diễn ngưỡng theo nguồn/regime** (`PREREG_GATE_RECAL` — đề xuất, **chưa chạy**).
2. **Trên DEV/sim (`G2`):** nút thắt **KHÔNG phải model** — mà là **`pct` (config) + burstiness của thị trường**. Gate đóng **56 % số tuần** vì *không có tín hiệu cần thiết*, không vì model yếu (`K_DENSITY`: gap dài nhất **129,24 ngày GIỐNG HỆT** ở K=8/12/16 ⇒ không K nào lấp được tuần đóng).
3. ⇒ **Features/label của gate KHÔNG thể là lever `n`.** Kênh duy nhất của model dưới `G2` là **xếp hạng → chọn ĐÚNG lệnh nào pass** (chất lượng), và `F1` cho thấy cải thiện xếp hạng/IC ở đây **không chuyển thành sim tốt hơn**.

---

## 3. VIỆC 3 — ĐỀ XUẤT

### 3.1 KẾT LUẬN CHÍNH: **NULL**

**Không có cửa feature/label nào mở được nhiều sự kiện hơn mà giữ chất lượng.** Dân số chứng cứ:
- **1/1** vòng feature gate (F1): IC +0,0159 nhưng sim **0/5** ⇒ loại.
- **2/2** vòng label gate (L1, L2): **XẤU**; L2 chính là phép thử "mở 2×" ⇒ **vỡ chất lượng**.
- **7** vòng ngưỡng/calib: **mọi lần mở đều vỡ T3/T1** (điển hình `D2` 2,1× ⇒ FAIL 4/4).
- **3** vòng nguồn live: `PASS2` ⇒ nguồn **không lỗi**; nút thắt = **ngưỡng vs regime**.
- **1** vòng nguồn-sự-kiện-thứ-2 (OFI V3): **NO-GO** (`d6f2bbba`).

### 3.2 CỬA HẸP DUY NHẤT CÒN TRỐNG (không hứa mở gate) → pre-reg ngắn

Có **đúng 1 ô chưa từng chạy**, ghi rõ để owner quyết: **mọi vòng feature/label của gate ở trên đều đo trên nền NGƯỠNG CỐ ĐỊNH** (T170 scale 1,70; `X1_C3_FULL` scale 1,0) — **chưa vòng nào đo dưới gate `MODE=ratio` (G2)**.
Dưới ratio gate, hiệu chuẩn bị hấp thụ và **chỉ còn xếp hạng** ⇒ câu hỏi hẹp, hợp lệ: *"biến thể gate tốt hơn về XẾP HẠNG có cải thiện **chất lượng trên ĐÚNG tập được admit** không?"* — đây là câu **CHẤT LƯỢNG (T3)**, **KHÔNG** phải câu mở gate.

⇒ Đã viết pre-reg **`docs/prereg/PREREG_GATE_FEATLABEL.md`** (§CHƯA CHẠY): **3 biến thể**, **tầng 1 OFFLINE (0 sim, CPU, ~1–2 giờ)**, có **cổng DỪNG cứng** — chỉ được chạy sim nếu tầng 1 vượt cổng. Kỳ vọng ghi trước: **NULL** (theo `F1` + `L2`).
**Ưu tiên: THẤP.** Không phải đường tới ×2 `n`.

### 3.3 VÒNG SAU / CẦN DỮ LIỆU MỚI (đánh dấu rõ)

| việc | vì sao thuộc vòng sau | cần gì mới |
|---|---|---|
| **OI market-level / liquidity feature cho gate** | phải sửa **extractor Java + replay Aerospike**; kỳ vọng ΔIC ≤ 0,01, kênh mở gate ≈ 0 | export gate dataset có cột OI aggregate; pre-reg riêng + owner chỉ định feature |
| **Label = PnL exit bit-exact (FLAT3) trên top-K S1** | `g1_replay` chỉ có ở tập lấy mẫu ⇒ không phủ toàn pool | `path_labels` phủ toàn bộ top-K DEV |
| **Ngưỡng biểu diễn theo nguồn live (RECAL)** | đã có pre-reg `PREREG_GATE_RECAL` (**đề xuất, chưa chạy**) — đúng chỗ đau nhất của LIVE | owner duyệt; sửa `EntryGate`/profile (đụng đường LIVE) |
| **Nguồn sự kiện thứ 2** | hướng cấu trúc đã chọn (`0013`); OFI V3 NO-GO ⇒ cần ứng viên khác | dữ liệu nguồn mới (không phải feature của gate) |

---

## 4. MỤC BỎ + LÝ DO

- **Bỏ: retrain gate 27-feature rồi sim trên G2** — `F1` đã chạy đúng phép này (SIM48) và **0/5**; lặp lại trên nền khác **không thêm thông tin** (cùng tầng model, cùng kết luận) trừ khi vào §3.2 (khi đó tầng 1 offline chặn trước).
- **Bỏ: thêm OI/liquidity vào gate ngay** — chi phí replay lớn, kỳ vọng ΔIC ≤ 0,01, kênh mở gate ≈ 0; không có dữ liệu sẵn ⇒ **vòng sau**.
- **Bỏ: thử label "net-of-cost" cho gate** — cùng họ `L3` (NET_THR) và `L2`; đã có bằng chứng dấu.
- **Bỏ: đọc `RESULT_FEAT_ADD_V1` / `FEAT_CUT_RVOL15M` / `FEAT_ABLATION` / `LABELH` / `LABEL_ROI*` như bằng chứng cho GATE** — đó là **selector 45/26 cột**, khác trục (task yêu cầu phân biệt rõ).
- **Bỏ: chạy sim/Java/ONNX/WFO trong bài này** — ràng buộc cứng (0 train/0 sim), và câu hỏi gốc đã trả lời được bằng tổng hợp chứng cứ có sẵn.

## 5. BẰNG CHỨNG THÔ (đường dẫn, không dán số)

```bash
# feature gate
docs/result/RESULT_GATEFEAT.md · docs/prereg/PREREG_GATEFEAT.md        # prereg 8fc7d90d · kq d01d59a0
# label gate
docs/result/RESULT_GATE_H72.md · docs/prereg/PREREG_GATE_H72.md        # d39f0158
docs/result/RESULT_GATE_TOPK_LABEL.md · RESULT_GATE_TOPK_LABEL_SIM.md  # 884031eb · 0d0bdd5c · prereg 70e8d8ff
# nguồn/thang đo p15 live
docs/result/RESULT_GATE_ROOTCAUSE.md (b65a19a0) · RESULT_FEATDIFF_PASS2.md (d024f310) · RESULT_P15_SOURCE.md (bcfa83b8)
# ngưỡng/calib (KHÁC trục)
docs/result/RESULT_GATESCALE.md · RESULT_GATE_CALIB.md · RESULT_FLATGATE.md · RESULT_REGIME_GATE.md · RESULT_BREADTH_GATE_SIM.md
docs/result/RESULT_DOUBLE_ENTRIES.md (60384406) · docs/plan/SUGGEST_DOUBLE_ENTRIES.md (8c0cd751)
# cơ chế ratio gate (quyết định số sự kiện do PCT, không do model)
src/main/java/com/binance/chuyend/ai_ml/onnx/entry/GateRollingRatio.java:19-24
# nguồn sự kiện thứ 2
docs/result/RESULT_OFI_V3_EVENT2.md (d6f2bbba) · docs/decisions/0013-giu-g2-chuyen-ofi.md
```
