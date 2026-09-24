# RESULT_STAGE3_SIM — SIM 3 biến thể feature (V0 21 / V1 26 / V5 31) vs MỐC 45-feature (KEEPLEG0)

**Ngày:** 2026-09-25 · **Chi nhánh:** `module` · **Trạng thái:** ĐO XONG (sim + MTM phút + chấm điểm)
**Tiền đăng ký (chốt TRƯỚC, commit trước khi push kernel):** `docs/prereg/PREREG_STAGE3_SIM.md` (commit `b49a44a`)
**Code:** `b49a44a` (pre-reg + `s3_funding.py`) · `1b28afa` (`s3_kernel.py` / `s3_build_map.py` / `s3_intraday.py` / `s3_score.py`)
**Kernel:** `chuyendinh/sim-s3-moc` · `sim-s3-v0` · `sim-s3-v1` · `sim-s3-v5` · `sim-s3-mtm` · `sim-s3-probe`
**Cửa sổ:** DEV `2021-07-01 .. 2025-12-30` (48 tháng + 2021H2) · **KHÔNG chạm 2026/HoldoutSeal/ONNX/LIVE** · **KHÔNG push git**
**Chi phí Kaggle = 0** (CPU kernel không tính quota; GPU không dùng) · **không** chạy Java/sim trên Oracle (shadow LIVE)

---

## 0. TRẢ LỜI NGẮN

Nền = **FLATGRID KEEPLEG0**; 4 kênh **cùng một cấu hình, chỉ khác thư mục bins** (`WFO_FUNDING_PRED_DIR`).

| kênh | vector | n | equity | SumPnL | maxDD **phút** | UW phút (ngày) | 5 rate vs MỐC | quyết định |
|---|---|---:|---:|---:|---:|---:|---|---|
| **MỐC** (45 feat) | 45 | 1.085 | 103.083 | 68.083 | **−19,96 %** | 147,2 | — | mốc |
| **V0** (21 keeper) | 21 | 1.200 | 88.146 | 53.146 | −19,47 % | 147,2 | **0 TỐT / 2 XẤU** | **NULL** |
| **V1** (21+5 thật) | 26 | 1.268 | 95.405 | 60.406 | −19,44 % | 170,5 | 0 TỐT / 0 XẤU | **NULL** |
| **V5** (21+5+5 nhiễu) | 31 | 1.239 | 93.632 | 58.632 | −19,75 % | 222,3 | 0 TỐT / 0 XẤU | **NULL** |

- **Không kênh nào được GIỮ/ĐỔI** (luật §4 pre-reg: cần ≥2 rate TỐT ngoài CI **và** 0 rate XẤU) ⇒ **NULL toàn bộ**, giữ nguyên 45-feature như đang chạy.
- **(1) Cắt 45→21 có làm tệ đi không?** **CÓ, nhưng ở tầng CHẤT LƯỢNG LỆNH, không ở tầng RÀO RỦI RO**: V0 **xấu hơn mốc ngoài CI ở 2/5 rate** (`mP|SM` −0,739 [−1,540; −0,012]; `meanP` −1,159 [−2,310; −0,143]), `n` **+10,6 %** (1.200 vs 1.085), equity −14,5 % (info, **không** phải tiêu chí) — **tất cả rào cứng §7 vẫn PASS** (cả theo năm lẫn toàn kỳ).
- **(2) V1/V5 vs V0 phân biệt được không?** **KHÔNG** (0/5 cả hai chiều) ⇒ SIM **không** tách được *feature thật* khỏi *cột nhiễu*; V1/V5 vs MỐC cũng 0/5. Chuỗi V0/V1/V5 **bất khả phân biệt trong CI** ⇒ **NULL** (khớp Stage 2).
- **(3) Có nên đổi selector sang 21 feature không?** **KHÔNG.** Không có bằng chứng tốt hơn; V0 lại có 2 rate XẤU ngoài CI. Đổi `NUM_FEATURES`/ONNX = **đụng đường LIVE** ⇒ **ngoài phạm vi vòng này**, cần owner duyệt riêng (chưa làm).

---

## 1. CỔNG — đạt hết (điều kiện đọc số)

| cổng | kết quả |
|---|---|
| **P0** mapper | **863** (≥800) ở cả 5 kernel ✓ |
| **P1** MỐC = mốc Kaggle | md5 `printDone.csv` = **`99e42b75cf1a2142f9cd14dc72e371ba`** ✓ · **n = 1.085** ✓ · equity **103.083** ✓ |
| **P2** dựng lại funding byte-faithful | `md5_funding` = **`8e57d900d5c54c744bfcaf5c9b27fc93`** ✓ (= manifest bundle) · `binsSha256` = **`407e2aba…`** ✓ |
| **P3** đồng nhất dữ liệu | `market.bin`/`pred.bin` **copy NGUYÊN BYTE** từ bundle (`4ab691c908fc545c…` / `5dd6bb4c3f98d89d…`, có guard md5 trong kernel) ⇒ 4 kênh dùng **cùng** market/pred |
| **jar** | sha256 `2c2f8aef78c98470fdc3b0d464edd7ec2c604a7589985b1f4211c1da05fcdca0` = jar của bundle ✓ |
| **MTM mốc phút (cổng bắt buộc trước khi đọc maxDD)** | kênh MỐC tái lập **đúng số đã công bố** của KEEPLEG0: minute maxDD **−19,96 %** (149.1 §3), UW **147,2 ngày**, năm xấu nhất **2025 −19,96 %**; V1 0,18 USDT · V2-rel **0,0129 %** · V3 **0,001 %** · V5 **0,001 pp** — **PASS toàn bộ** (ngưỡng: 1 USDT / 0,05 % / 1 % / 0,1 pp) |

- `binsSha256` từng kênh: MỐC `407e2aba…` · V0 `9709dd62…` · V1 `7b4cc34a…` · V5 `d649e8c1…`; `md5_funding`: `8e57d900…` / `e942ad45…` / `d5acde84…` / `192cbe66…`.
- Nguồn ranker S1 (`pred_s1a2x1.parquet`) sha256 **`2618fe1a0235d8ed3602f7b4bf37d8ba611e4e6c923854e10184d036065309fe`** = đúng bản dùng để dựng bins MỐC (`BINS_MANIFEST` §X1) ⇒ 4 kênh **cùng thứ tự coin**, chỉ khác **multiset `P(win)`**.

## 2. CƠ CHẾ + CHẤT LƯỢNG LỆNH

| kênh | n | win% | TSloss% | mP\|SM | mP\|SL | meanP | hold_med (h) | turn (lệnh/ngày) | Σfunding | ΣPnL | Σfund/ΣPnL |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| MỐC | 1.085 | 88,20 | 10,32 | **7,961** | −19,300 | **5,147** | 5,0 | 0,660 | −2.359 | 68.083 | −3,47 % |
| V0 | 1.200 | 87,83 | 11,25 | 7,222 | −21,521 | 3,988 | 5,9 | 0,730 | −2.045 | 53.146 | −3,85 % |
| V1 | 1.268 | 88,17 | 11,04 | 7,639 | −20,980 | 4,479 | 6,4 | 0,771 | −3.260 | 60.406 | −5,40 % |
| V5 | 1.239 | 87,73 | 11,14 | 7,622 | −22,032 | 4,319 | 5,9 | 0,754 | −3.657 | 58.632 | −6,24 % |

**Vì sao 4 kênh khác nhau (kênh GATE):** `symbolPred` (= `1−P(win)`) của 4 kênh lệch hệ thống — mean **0,1815** (MỐC) vs **0,1708** (V0) / **0,1649** (V1) / **0,1656** (V5); p50 0,1705 vs 0,1683/0,1543/0,1586. `dyn_thr = SIM_MIN_MOMENTUM_15M · max(MIN, symbolPred/0,15 · MULT)` ⇒ symbolPred **thấp hơn ⇒ ngưỡng gate thấp hơn ⇒ nhiều lệnh hơn** (đúng với `n` +10,6 %/+16,9 %/+14,2 %). Đây là **kênh HIỆU CHUẨN của model**, khớp `RESULT_G4` ("giá trị load-bearing ở GATE").

## 3. 5 RATE + CI (ghép cặp block-72h, 2.000 rep, seed 20260905) — `k=3`, hệ số `inflate(3)=1.482304`

“Ngoài CI” = ngoài **cả hai** độ rộng (1,21 legacy **và** 1,4823).

| so | win% | TSloss% | mP\|SM | mP\|SL | meanP | TỐT/XẤU |
|---|---|---|---|---|---|---|
| **V0 − MỐC** | −0,369 [−2,645; +1,733] | +0,927 [−1,347; +3,443] | **−0,739 [−1,540; −0,012]** | −2,221 [−7,594; +3,062] | **−1,159 [−2,310; −0,143]** | **0 TỐT / 2 XẤU** |
| **V1 − MỐC** | −0,032 [−2,207; +1,974] | +0,718 [−1,617; +3,136] | −0,322 [−0,856; +0,267] | −1,680 [−7,593; +4,096] | −0,668 [−1,653; +0,258] | 0 / 0 |
| **V5 − MỐC** | −0,471 [−2,852; +1,848] | +0,815 [−1,828; +3,363] | −0,339 [−0,883; +0,193] | −2,733 [−10,177; +4,689] | −0,828 [−1,821; +0,103] | 0 / 0 |
| V1 − V0 *(phụ)* | +0,337 [−1,784; +2,442] | −0,209 [−2,471; +1,964] | +0,417 [−0,101; +1,061] | +0,541 [−6,437; +8,417] | +0,491 [−0,697; +1,865] | 0 / 0 |
| V5 − V0 *(phụ)* | −0,101 [−2,283; +2,179] | −0,112 [−2,538; +2,144] | +0,400 [−0,311; +1,194] | −0,512 [−8,644; +8,552] | +0,331 [−0,835; +1,597] | 0 / 0 |
| V1 − V5 *(phụ)* | +0,438 [−0,869; +1,674] | −0,097 [−1,343; +1,235] | +0,017 [−0,441; +0,567] | +1,053 [−1,723; +3,856] | +0,160 [−0,328; +0,656] | 0 / 0 |

- `mP|SL` rộng nhất (CI ±8 USDT) vì số lệnh STOP_LOSS ít ⇒ **không** rate nào của `mP|SL` ngoài CI.
- **`meanP` là rate CHẤT LƯỢNG**, không phải kênh sizing (mMargin mới là kênh thang đo).

## 4. RÀO CỨNG `RISK_APPETITE.md` §7 — maxDD/UW trên **MTM MỐC PHÚT**

| kênh | maxDD phút toàn kỳ | UW phút (ngày) | quý xấu nhất | năm âm | conc 1 coin | **RÀO (năm + toàn kỳ)** |
|---|---:|---:|---:|---:|---:|---|
| MỐC | −19,96 % *(ngày −11,21 %)* | 147,2 | −1,08 % | 0 | 7,12 % | **PASS** |
| V0 | −19,47 % *(ngày −11,37 %)* | 147,2 | −1,53 % | 0 | 8,14 % | **PASS** |
| V1 | −19,44 % *(ngày −12,16 %)* | 170,5 | −2,52 % | 0 | 9,60 % | **PASS** |
| V5 | −19,75 % *(ngày −11,91 %)* | 222,3 | −2,17 % | 0 | 9,25 % | **PASS** |

Theo năm (`maxDD_phút% / UW_phút ngày / ret% / qmin%`, ngưỡng 40 % · 250 · ≥−20 % · ≥0):

| kênh | 2021H2 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|
| MỐC | −11,05/37,0/+12,21/+4,44 P | −15,43/74,0/+12,59/−1,08 P | −5,03/64,4/+34,96/−0,37 P | −12,16/91,5/+32,13/−0,92 P | −19,96/129,0/+30,81/+1,27 P |
| V0 | −11,05/37,0/+12,21/+4,44 P | −17,66/74,2/+10,47/−1,53 P | −3,91/82,0/+23,57/+0,40 P | −12,43/117,1/+35,83/−1,34 P | −19,47/74,8/+21,12/+1,24 P |
| V1 | −11,05/37,0/+12,21/+4,44 P | −15,74/76,5/+10,95/−2,52 P | −4,17/45,4/+33,70/−0,86 P | −12,86/114,9/+39,14/−2,50 P | −19,44/164,8/+17,70/+1,94 P |
| V5 | −11,05/37,0/+12,21/+4,44 P | −17,85/68,0/+7,11/−1,87 P | −4,04/45,4/+37,65/+0,10 P | −14,16/117,3/+36,72/−2,17 P | −19,75/**222,3**/+18,27/+1,27 P |

- **Chuỗi NGÀY che mất 7,3–8,8 pp drawdown** (MỐC −11,21 % ngày vs −19,96 % phút) — đúng như `RESULT_INTRADAY_DD`. **Biến thể P=bar.low** (căng hơn): −24,16 % / −23,35 % / −23,31 % / −23,76 % (vẫn < 40 %).
- UW toàn kỳ phút = **y hệt** UW ngày ở mọi kênh (điểm `maxDD_m` trùng ngày đỉnh) → không có kênh nào lách rào bằng cách "UW đo ngày".

## 5. BẢNG PnL CHI TIẾT THEO NĂM (n + PnL USDT) + TOTAL

| kênh | 2021H2 | 2022 | 2023 | 2024 | 2025 | **TOTAL** | equity cuối |
|---|---|---|---|---|---|---|---|
| MỐC | 149 / +4.273 | 196 / +4.943 | 126 / +15.376 | 281 / +19.210 | 333 / +24.282 | **1.085 / +68.083** | 103.083 |
| V0 | 149 / +4.273 | 222 / +4.111 | 139 / +10.155 | 326 / +19.235 | 364 / +15.373 | **1.200 / +53.146** | 88.146 |
| V1 | 149 / +4.273 | 252 / +4.300 | 134 / +14.682 | 335 / +22.800 | 398 / +14.350 | **1.268 / +60.406** | 95.405 |
| V5 | 149 / +4.273 | 237 / +2.794 | 113 / +15.839 | 332 / +21.265 | 408 / +14.462 | **1.239 / +58.632** | 93.632 |

- **2021H2 GIỐNG HỆT TUYỆT ĐỐI ở cả 4 kênh (149 lệnh / +4.273 / +12,21 % / maxDD −2,46 %)** — đúng như thiết kế (2 fold 2021 dùng chung bins của MỐC; xem §7.1) ⇒ khác biệt giữa các kênh **chỉ** đến từ 16 fold 2022+.
- Cả 4 kênh **không năm nào âm**; PnL kém hơn của các biến thể tập trung ở **2025** (MỐC +24.282 vs V0 +15.373 / V1 +14.350 / V5 +14.462) — các biến thể vào nhiều lệnh hơn nhưng chất lượng/lệnh thấp hơn.

## 6. KẾT LUẬN THEO LUẬT §4 + TRẢ LỜI

| kênh | n | TỐT/5 | XẤU/5 | rào năm | rào toàn kỳ | **quyết định** |
|---|---:|---:|---:|---|---|---|
| V0 | 1.200 | 0 | **2** | PASS | PASS | **NULL** |
| V1 | 1.268 | 0 | 0 | PASS | PASS | **NULL** |
| V5 | 1.239 | 0 | 0 | PASS | PASS | **NULL** |

**(1) Cắt 45→21 có làm hệ thống tệ đi không?** — **CÓ, và đo được**: V0 xấu hơn MỐC ngoài CI ở **2/5 rate** (`mP|SM`, `meanP`), vào **+10,6 %** lệnh, PnL toàn kỳ −14,7 k USDT (equity 88.146 vs 103.083, **info, không phải tiêu chí**). **Nhưng** cơ chế là **hiệu chuẩn GATE** (model 21-feature cho `P(win)` cao hơn ⇒ ngưỡng gate thấp hơn ⇒ nhiều lệnh biên hơn), **không** phải chọn sai coin: thứ tự coin do **S1** quyết định ở **mọi** kênh. **Rào rủi ro KHÔNG bị phá** (maxDD phút −19,47 % < 40 %; UW 147,2 ≤ 250; qmin −1,53 % ≥ −20 %; không năm âm; conc 8,14 % ≤ 15 %).
**(2) V1/V5 vs V0 (feature thật vs nhiễu)?** — **KHÔNG phân biệt được** (0/5; `mP|SM` của V1−V0 chỉ vượt ở độ rộng 1,21). Even V1/V5 vs MỐC cũng 0/5 ⇒ **cả chuỗi bất khả phân biệt** trong CI ⇒ kết luận **NULL** ở tầng sim, **khớp** kết luận NULL của Stage 2: nội dung 5 feature **không** load-bearing.
**(3) Có nên đổi selector sang 21 feature?** — **KHÔNG**: (a) không có rate TỐT nào ngoài CI, lại có 2 rate XẤU; (b) đổi `NUM_FEATURES`/ONNX = **đụng đường LIVE** ⇒ cần owner duyệt riêng; vòng này **không** chạm.

## 7. GIỚI HẠN / KHAI BÁO SAI LỆCH (ghi rõ, không giấu)

1. **2 fold 2021 dùng bins của MỐC cho MỌI kênh** (Stage 2 chỉ train 16 fold từ 2022): không có lựa chọn nào khác nếu muốn 4 kênh **cùng độ phủ**; đã kiểm bằng số — 2021H2 **byte-identical** giữa 4 kênh (§5). Hệ quả: kết luận chỉ nói về **16 fold 2022+**.
2. **Vòng này đo KÊNH HIỆU CHUẨN/GATE của việc cắt 45→21**, không đo kênh chọn coin: `c4_build_map s1a2x1` giữ **thứ tự coin = S1** và chỉ thay **multiset `P(win)`** cấp cho gate. Muốn đo kênh chọn coin thì phải map bằng **chính `p` của arm** (`score = −p`) — **chưa chạy**, và nói chung đã biết từ `G5`/`RESULT_G4` rằng kênh multiset chính là kênh load-bearing.
3. **V0/V1/V5 vs MỐC khác nhau 2 thứ so với "cắt cột" thuần**: (a) bỏ cột **và** (b) **train lại** net015 (cùng recipe/seed/device Kaggle GPU của Stage 2, khác vector cột). Không tách được hai phần này — nhưng cả hai đều là "hệ quả của việc cắt 45→21" khi triển khai thật.
4. **`maxDD`/`UW` phút** là **MỘT quan sát lịch sử**, không có CI (không bootstrap được cho cực trị); 10 episode lớn nhất phụ thuộc ~9 đợt thị trường, không độc lập.
5. **`k=3`** đã khai báo trước (3 ứng viên vs MỐC); các so sánh phụ (V1−V0, V5−V0, V1−V5) báo cùng độ rộng `inflate(3)` **không** tính thêm thành họ mới ⇒ chúng chỉ có tính **mô tả**, không dùng để "GIỮ".
6. **Không** chạy: 6 arm (V2/V3/V4 bỏ theo pre-reg), 2026/HoldoutSeal, `juice`, ONNX/`NUM_FEATURES`/`shadow_c3`, không push git.
7. **Hạ tầng:** sim Kaggle ↔ mốc Kaggle; hạt giống so sánh duy nhất khác nhau giữa 4 kênh là **thư mục bins** (đã kiểm: cùng jar, cùng market/pred byte-identical, cùng profile/hash hành vi, cùng cửa sổ, cùng ticker).

## 8. NƠI LƯU ARTIFACT

| gì | ở đâu |
|---|---|
| `printDone.csv` + `sim.out` + `result.json` 4 kênh | `/home/ubuntu/kaggle_sim/out/s3-{moc,V0,V1,V5}/` (kéo từ kernel) |
| MTM mốc phút (4 kênh) + cổng nghiệm thu | `/home/ubuntu/kaggle_sim/out/s3-mtm/**/mtm_result.json` |
| Bảng chấm điểm đầy đủ (JSON) | `/home/ubuntu/kaggle_sim/out/s3_score.json` |
| Kernel | `chuyendinh/sim-s3-{moc,v0,v1,v5}` · `sim-s3-mtm` · `sim-s3-probe` |
| Dataset mới | `chuyendinh/s3-s1-sc` (`pred_s1a2x1.parquet`) · `chuyendinh/s3-moc-2021bins` (2 fold 2021 của mốc) |
| Bins Stage 2 (nguồn) | kernel `chuyendinh/g015p2-stage2-featvar-gpu` → `stage2/{V0,V1,V5}/predict_wf_*.bin` |

*Sinh bởi `research/analysis/s3_score.py` từ artifact kernel.*
