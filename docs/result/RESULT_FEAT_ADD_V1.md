# RESULT_FEAT_ADD_V1 — V1 (26 cột: 21 keeper + 5 prescreen) trên nền G2+FLAT3

**Ngày:** 2026-09-29 · **Nhánh:** `module` · **Trạng thái:** ĐO XONG (sim Kaggle + MTM phút + chấm §9). **Không** chạm 242/shadow-c3/holdout 2026; không dùng fold 2026.
**Pre-reg (chốt TRƯỚC số, commit `672350e9`):** `docs/prereg/PREREG_FEAT_ADD_V1.md`, md5 `9ce3d65868c053ceaa564c184e6245ff` (đã xác nhận md5 sau cp).
**Code:** `research/analysis/feat_add_v1_kernel.py` (kernel Kaggle) · `research/analysis/feat_add_v1_score.py` (chấm) · thô: `docs/result/feat_add_v1.json`.
**Kernel:** `chuyendinh/sim-featv1-b0` · `chuyendinh/sim-featv1-v1` (Kaggle CPU, jar `sim-jar-gdv2` sha `7368be46…`, bundle `sim-x1-2021-bundle`).

---

## 0. RỦI RO / CẢNH BÁO TRƯỚC (đọc trước khi đọc số)

1. **[ĐO] V1 KHÔNG đạt T1 §9 trên G2+FLAT3** — 2 vi phạm: UW MTM phút cửa sổ **353 ngày > 250** (năm 2022: 310 ngày) và **năm 2022 âm (−1,01%)**. Theo luật pre-reg "FAIL ⇒ loại". Nhãn máy `V1 ~ B0` chỉ là do CI ΔCalmar rộng chứa 0; **điểm ước lượng của V1 tệ hơn B0 ở mọi thước đo tăng trưởng** (ΔCAGR CI95 không chứa 0, cả 2 cách bootstrap).
2. **[ĐO] Kết quả ĐI NGƯỢC kỳ vọng "gate rộng khuếch đại lợi thế V1":** trên nền cũ (KEEPLEG0) V1 đã kém MOC (−7,4% equity, cửa sổ 2022+); trên G2+FLAT3 kém hơn nữa (−15,4%). Không có bằng chứng V1 có lợi ở tầng sim.
3. **[SUY LUẬN] Sát thương tập trung 2022** (fold huấn luyện ít lịch sử nhất; 2022Q2 −5,31% ROI, UW 310 ngày); 2025 V1 nhỉnh hơn B0 (+2,6 pp) — có thể là hiệu ứng "nhiều dữ liệu hơn cho 5 feature", nhưng **KHÔNG** kiểm định thêm (không tune sau khi thấy số) — chỉ là giả thuyết cho vòng sau, cần pre-reg riêng.
4. Bootstrap ΔCalmar_MTM có CI rất rộng (block-72h ±46, episode ±8.5): với k=1 vẫn **không** phân biệt được Calmar; kết luận "loại" dựa trên **T1 FAIL** + **ΔCAGR/ΔΣPnL âm ngoài CI**, không dựa vào CI Calmar.
5. maxDD/UW MTM phút là **một quan sát lịch sử**, không CI cực trị; 2 arm chung ~9 đợt thị trường (không độc lập).
6. Nền cũ (S3, KEEPLEG0/T170 gate) và nền mới (G2+FLAT3, R4 size) khác **nhiều thứ** (gate, exit, sizing) — so "V1 vs MOC" cũ/mới là đối chiếu mô tả, không tách được riêng hiệu ứng gate.

---

## 1. CỔNG (PASS hết trước khi đọc số)

| cổng | kết quả |
|---|---|
| Pre-reg md5 | `9ce3d658…` khớp, commit trước số ✓ |
| **Bins V1 khớp giao thức** [ĐO] | 16 fold DEV `20220101..20251001`: **kích thước file byte-y hệt `predwf_G015x26` deploy** (16/16), cùng tập khoá (ts,sym) (16/16; thứ tự dòng khác — mapper S1 chuẩn hoá), 0 NaN, p∈[0,1], `tsmax` ≤ 2025-12-31 (không rò 2026). Nguồn: Stage 2 (cùng trainer/recipe/seed/GPU Kaggle; `n_train/pos/spw` fold 20220101 = 3.730.472 / 0,26989 / 2,705276 khớp deploy — RESULT_STAGE2_TRAIN §1). ⇒ **tái dùng bins, KHÔNG retrain**. (`~/claude_master/0929/featv1_binval.json`) |
| **B0 parity** [ĐO] | printDone md5 = **`650c386f0d0dfea334af9d55ca2f21d4`**, n = 2517, eq = 131 908 ✓ — chứng minh **hai đường**: (a) bundle nguyên (`g2flat3-val`, `trail2-g2-flat3`) và (b) đường REBUILD funding mới (`sim-featv1-b0`, kernel này). Funding md5 `8e57d900…` ✓, bins sha `407e2aba…` ✓, jar `7368be46…` ✓, mapper 863 ✓ |
| **V1 tất định** [ĐO] | bins sha `7b4cc34a…` và funding md5 `d5acde84…` **trùng đúng** kênh V1 của Stage 3 (cùng bins + cùng map S1 + cùng 2 fold 2021 của MOC) ⇒ dựng bins/funding tái lập được |
| Cửa sổ sạch [ĐO] | 434/434 lệnh vào < 2022-01-01 **giống hệt** B0/V1; equity 2021-12-31 = **41 486** cả hai ⇒ so 2022+ là so sạch (2 fold 2021H2 của V1 = bins MOC) |
| MTM tái lập [ĐO] | công cụ MTM (cửa sổ reset) tái lập đúng số đã công bố của S3 trên nền cũ: MOC maxDD −19,96% / UW 147,2; V1 −19,44% / UW 170,5 ✓ |
| `|n_V1 − 2517|/2517` | **+2,78%** (< 10%, không cờ) |

**Cửa sổ so sánh = 2022-01-01 .. 2025-12-30** (entry ≥ 2022-01-01; CAGR/quý/năm trên equity ngày từ 2021-12-31; MTM phút chạy từ 2021-07-01, DD/UW của cửa sổ reset đỉnh tại 2022-01-01 UTC). Các chi tiết thi hành này KHÔNG đổi thiết kế (xem §8).

---

## 2. BẢNG CHÍNH (k = 1, inflate 1,0) — cửa sổ 2022+

| arm | n (cửa sổ / toàn kỳ) | equity 2021-12-31 → 2025-12-30 | CAGR % | maxDD MTM phút % | UW MTM phút (ngày) | quý xấu nhất ROI % | conc 1 coin % | **Calmar_MTM** | **T1** |
|---|---|---|---:|---:|---:|---:|---:|---:|---|
| **B0** (G2+FLAT3) | 2083 / 2517 | 41 486 → 131 908 | 33,56 | −17,68 | 87 | −0,77 | 4,09 | **1,898** | PASS |
| **V1** (G2+FLAT3, bins V1) | 2153 / 2587 | 41 486 → 111 569 | 28,08 | −22,17 | **353** | −5,31 | 4,30 | **1,267** | **FAIL** |
| Δ (V1 − B0) | +70 (+3,4%) | −20 339 (−15,4%) | −5,48 pp | −4,49 pp | +265 | −4,54 pp | +0,22 | **−0,631** | |

Chi tiết T1 V1: maxDD phút/năm tệ nhất −22,17% (2022) ≤ 40 ✓ · **UW 352,5 > 250 ✗** · quý xấu −5,31 ≥ −20 ✓ · **năm âm: 2022 (−1,01%) ✗** · conc 4,30 ≤ 15 ✓. B0: 5/5 ✓.

Tỷ lệ chất lượng lệnh (cửa sổ): win% 86,27 → 84,58 · TSloss% 13,83 → 15,05 · mP|SM 7,76 → 7,61 · mP|SL −14,44 → −16,76 · ΣPnL 90 422 → 70 083 (−22,5%).

## 3. BOOTSTRAP ΔCalmar_MTM (V1 − B0), NREP 2000, seed 20260905, inflate 1,0

| phương pháp | ΔCalmar_MTM obs | CI95 | chứa 0? | ΔCAGR CI95 (pp) | ΔΣPnL CI95 (USDT) |
|---|---:|---|---|---|---|
| block-72h (paired, K=122) | −0,631 | [−52,20; +40,01] | CÓ | [−80,3; −17,7] | [−33 481; −7 375] |
| episode-cluster (K=96) | −0,631 | [−7,79; +9,20] | CÓ | [−9,68; −2,22] | [−33 049; −7 753] |

⇒ CI ΔCalmar chứa 0 (không có phía dương). **ΔCAGR và ΔΣPnL: CI KHÔNG chứa 0, âm** ở cả hai phương pháp (Calmar trong bootstrap là thang equity đóng — khác thang Calmar_MTM điểm, như các vòng trước).

## 4. VERDICT theo luật pre-reg

| điều kiện "V1 thắng" | kết quả |
|---|---|
| T1 đạt | **KHÔNG** (UW 353 > 250; 2022 âm) |
| Calmar_MTM V1 > B0 | KHÔNG (1,267 < 1,898) |
| hoặc n cao hơn & Calmar ≥ 0,90×B0 (=1,708) | KHÔNG (n +70 nhưng 1,267 < 1,708) |
| CI ΔCalmar (block-72h VÀ episode) không chứa 0 phía dương | KHÔNG |

### **V1 KHÔNG thắng B0 — và T1 FAIL ⇒ loại V1 trên G2+FLAT3.** Điểm +1,9% của nền cũ **không lặp lại**.
(Đọc "block-72h + episode" theo hướng CHẶT — cả hai CI đều phải dương — đã khai báo trong header script trước khi xem số; kết luận không đổi nếu chỉ dùng block-72h.)

## 5. BẢNG QUÝ + NĂM (V1 vs B0, cửa sổ 2022+)

| quý | n B0 | n V1 | ROI% B0 | ROI% V1 | dROI |
|---|---:|---:|---:|---:|---:|
| 2022Q1 | 63 | 84 | +4,43 | +2,56 | −1,87 |
| 2022Q2 | 200 | 253 | −0,77 | −5,31 | −4,54 |
| 2022Q3 | 56 | 25 | +6,76 | +2,12 | −4,65 |
| 2022Q4 | 104 | 85 | +0,43 | −0,19 | −0,61 |
| 2023Q1 | 109 | 102 | +8,39 | +7,06 | −1,33 |
| 2023Q2 | 135 | 105 | +13,42 | +13,40 | −0,01 |
| 2023Q3 | 89 | 68 | +10,69 | +7,68 | −3,00 |
| 2023Q4 | 194 | 203 | +13,28 | +14,94 | +1,66 |
| 2024Q1 | 188 | 242 | +14,72 | +11,15 | −3,57 |
| 2024Q2 | 143 | 142 | +1,33 | +0,40 | −0,93 |
| 2024Q3 | 102 | 95 | +7,05 | +6,38 | −0,67 |
| 2024Q4 | 166 | 205 | +15,21 | +15,31 | +0,10 |
| 2025Q1 | 174 | 186 | +13,53 | +14,77 | +1,24 |
| 2025Q2 | 25 | 24 | +2,49 | +2,11 | −0,38 |
| 2025Q3 | 53 | 48 | −0,24 | +0,98 | +1,21 |
| 2025Q4 | 282 | 286 | +11,56 | +11,63 | +0,06 |

| năm | n B0 | n V1 | ROI% B0 | ROI% V1 | dROI | maxDD phút B0 | maxDD phút V1 | UW ngày B0 | UW ngày V1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2022 | 423 | 447 | +11,11 | **−1,01** | −12,12 | −17,68 | −22,17 | 70 | **310** |
| 2023 | 527 | 478 | +54,14 | +50,27 | −3,87 | −4,28 | −4,77 | 46 | 46 |
| 2024 | 599 | 684 | +43,35 | +36,88 | −6,48 | −10,69 | −10,85 | 87 | 117 |
| 2025 | 534 | 544 | +29,51 | +32,09 | +2,59 | −15,56 | −16,00 | 68 | 65 |

(Quý/năm: n theo ngày vào lệnh; ROI theo equity ngày. Bảng theo quý chuẩn `qstat_r4.py` toàn kỳ: `~/claude_master/0929/featv1_qstat_{b0,v1}.txt`.)
[ĐO] V1 kém hơn ở 11/16 quý; hơn ở 5/16 quý (2023Q4, 2024Q4, 2025Q1, 2025Q3, 2025Q4: +0,06..+1,66 pp) — chênh nhỏ so với thiệt hại 2022 (−12,1 pp năm).

## 6. PHÂN BỔ ROI (`roidist.py`, lệnh vào ≥ 2022-01-01; ROI = profit% lệnh)

```
bucket       | B0 n / PnL(k) / %PnL | V1 n / PnL(k) / %PnL
<0 (lo)      |  286    -59.9  -66.3% |  331    -60.1  -85.8%
0-3%         |   41      0.6    0.7% |   30      0.3    0.5%
3-5%         |  544     27.7   30.6% |  558     23.8   33.9%
5-7%         |  533     35.4   39.2% |  556     31.2   44.4%
7-10%        |  381     34.1   37.7% |  394     30.7   43.8%
10-15%       |  206     27.1   30.0% |  196     21.5   30.7%
15-25%       |   51      9.2   10.2% |   51      8.5   12.1%
25-50%       |   14      3.6    3.9% |   14      3.3    4.7%
50-100%      |   23      8.3    9.2% |   19      7.1   10.1%
100%+        |    4      4.3    4.8% |    4      3.8    5.4%
TOTAL        | 2083     90.4 100.0% | 2153     70.1 100.0%
win% quantiles p25/50/75/90/95/99: B0 [4.99, 6.37, 8.5, 12.0, 15.5, 63.96] | V1 [4.99, 6.0, 8.5, 12.0, 14.99, 56.47]
top-1% lệnh chiếm %PnL: B0 13.8 | V1 16.5
```
[ĐO] Cơ chế: V1 vào **thêm 45 lệnh thua** (331 vs 286; tổng lỗ USDT gần như y nhau −60,1k vs −59,9k dù equity — và size — của V1 thấp hơn theo thời gian) và **mất lãi ở mọi bucket thắng ≥3%** (3-5%: −3,9k; 5-7%: −4,2k; 7-10%: −3,4k; 10-15%: −5,6k), đuôi phải (p95, p99, 50-100%) mỏng hơn. Đây là **lệnh biên nhiều hơn, chất lượng/lệnh thấp hơn**, cùng dấu với kết luận S3 (V0/V1 "nhiều lệnh, mP thấp hơn").

## 7. SO VỚI NỀN CŨ (+1,9%): gate rộng có khuếch đại lợi thế V1 không?

| thước (cửa sổ 2022+, V1 so với arm nền cùng nền) | nền CŨ (S3: KEEPLEG0, V1 vs MOC) | nền MỚI (G2+FLAT3, V1 vs B0) |
|---|---:|---:|
| Δ equity cuối | −7,4% | **−15,4%** |
| Δ ΣPnL cửa sổ | −12,0% | **−22,5%** |
| ΔCAGR | −2,44 pp | **−5,48 pp** |
| ΔCalmar_MTM | −0,089 | **−0,631** |
| Δn (cửa sổ) | +183 | +70 |
| T1 | PASS (cả hai) | **V1 FAIL** |

- [ĐO] **Không khuếch đại theo hướng có lợi**: lợi thế V1 (nếu có) đã **không xuất hiện** trên nền G2+FLAT3; thiệt hại gấp ~2 lần nền cũ.
- **Về "+1,9%":** con số này đến từ `RESULT_STAGE3_SIM_XCHECK` — V1 của đường đối chiếu độc lập (97 202) so với V1 đã công bố (95 405), tức chênh giữa **hai đường cài đặt** của cùng kênh V1 (đường đó chưa qua cổng parity, tự XCHECK ghi "KHÔNG dùng làm bằng chứng"), **không** phải V1 so với MOC. Trên đường đã qua cổng parity (S3), V1 vs MOC = **−7,4%** equity. ⇒ "V1 +1,9% vs mốc" không có nền vững để "lặp lại".
- [SUY LUẬN] Nguyên nhân khả dĩ: gate G2 (ngưỡng ratio W90) đọc trực tiếp `symbolPred = 1−P(win)`; bins V1 có P(win) hiệu chuẩn cao hơn (S3: mean symbolPred 0,165 vs 0,1815) ⇒ ngưỡng gate thấp hơn ⇒ nhiều lệnh biên hơn (n +3,4%) mà không kèm chất lượng — kênh HIỆU CHUẨN/GATE, không phải kênh chọn coin (thứ tự coin vẫn do S1). Chưa kiểm trực tiếp.

## 8. GIỚI HẠN / KHAI BÁO CHI TIẾT THI HÀNH (không đổi thiết kế)

1. **Cửa sổ 2022+**: V1 dùng bins MOC cho 2 fold 2021H2 (Stage 2 chỉ train 16 fold từ 2022) ⇒ kết luận chỉ nói về 16 fold 2022+. Prefix 2021H2 giống hệt (§1) nên cửa sổ so sạch.
2. **UW cửa sổ** đo trên chuỗi phút với đỉnh reset tại 2022-01-01 UTC (không mang đỉnh 2021); **maxDD năm** = năm UTC 2022..2025. Cả hai đối xứng giữa 2 arm. Điểm 2022-01-01 UTC lệch 7h so với biên ngày giờ VN — không đáng kể.
3. **Bootstrap**: chỉ lệnh vào ≥ 2022-01-01; `CAP0` = equity 2021-12-31 (41 486; 35 000 của các vòng trước là vốn đầu kỳ 2021-07); lưới khối 72h chung (blk2), NREP 2000, seed 20260905; inflate 1,0 (k = 1 ứng viên).
4. `profile_hash` của arm B0 ở đường REBUILD (`ad1161f9…`) khác đường bundle (`c47b73f3…`) vì `WFO_FUNDING_PRED_DIR` được ghi đè sang thư mục bins dựng trong kernel — hành vi giao dịch y hệt (md5 printDone trùng byte).
5. Chi phí mô hình = mức "legacy" của sim (như trail2/GDV2 driver); 1 lần test duy nhất, không lặp/tune.
6. Không chạy V2/V3/V4/V0/V5 (ngoài pre-reg). Không đụng 2026/HoldoutSeal/ONNX/`NUM_FEATURES`/242/shadow.

## 9. NƠI LƯU ARTIFACT

| gì | ở đâu |
|---|---|
| printDone + sim.out B0/V1 | `/home/ubuntu/kaggle_sim/out/featv1-b0/` · `featv1-v1/` (storage/, logs/, result.json); nền cũ tham chiếu: `featv1-ref-s3moc` / `featv1-ref-s3v1` (symlink → s3-moc / s3-V1) |
| Kernel | `chuyendinh/sim-featv1-b0` · `chuyendinh/sim-featv1-v1` (~28–30 phút/kênh, chi phí Kaggle = 0) |
| Chấm + JSON | `docs/result/feat_add_v1.json` · `research/analysis/feat_add_v1_score.py` |
| Bins V1 xác minh | `~/claude_master/0929/featv1_binval.json` |
| MTM phút cache / log | `~/claude_master/0929/featv1_mtm.json` · `featv1_score.log` · `featv1_roidist.txt` · `featv1_tables.md` · `featv1_qstat_{b0,v1}.txt` |
