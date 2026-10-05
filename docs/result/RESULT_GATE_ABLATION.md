# RESULT — GATE_ABLATION (Pha A chương trình GATE)

- **Pre-reg:** `docs/prereg/PREREG_GATE_ABLATION.md` commit **bfdd3407** (chốt TRƯỚC mọi pred.bin/train/sim). Driver `research/analysis/gate_ablation_driver.py` (a629ff6f = code_sha của 5 kernel). Số đầy đủ: `docs/result/gate_ablation.json`.
- **Ràng buộc đã giữ:** 0 sửa .java, 0 build, 0 Java/sim trên Oracle (retrain + nhãn 60' thuần Python), 0 chạm 242/shadow_c3, 2026 không dùng (feature/nhãn cắt `< 2026-01-01 +07`), RAM đỉnh 1,9G (retrain) / 0,6G (nhãn); lock `oracle_heavy.lock` khi chấm MTM (đã gỡ). 5 kernel Kaggle (≤ 2 song song), template = `tools/kaggle_sim.py` HEAD (md5 8b60b00a, NOWRITE242) + 1 khối chèn `pred_ds` (assert count==1).
- **Tham chiếu A1** = B0@K24 (`n700-a1`, printDone md5 d9abf35f, n 3526, eq 144 974). Mỗi arm chỉ thay cột p15 của `pred.bin` (ts + risk4h byte-identical) ⇒ ghép cặp trực tiếp với A1.

## 0. KẾT LUẬN (rủi ro trước)
1. **Nhiễu retrain gate model là LỚN và chi phối mọi so sánh tinh của gate.** G-SEED7 (chỉ đổi `random_state` 42→7; pearson p15 vs gốc 0,977–0,996/fold, IC 0,514 = gốc) cho **ΔCAGR22 −5,31pp** (CI raw [−10,63; −0,64] — loại 0), ΔPnL −21,8k (CI inflate [−40,8k; −2,9k]), 2022 ROI −11,7 điểm. ⇒ con số A1/B0 tự nó mang ±5pp "xổ số seed"; band này nuốt NOCAL (+3,16), RULE (+3,01), H60 (−2,78).
2. **Q1 không trả lời được theo luật:** G-RND trượt G2 (phút gate-mở 0,37×A1: nhiễu iid theo phút làm pass dồn cụm — 11,2 lệnh/phút, p90 = 24 = full K24 — thay vì 4,5). Chỉ tham khảo: ΔCAGR22 −30,1 (CI inflate [−66,7; +2,7]), ΔPnL −92k (CI inflate [−187k; −7k]), UW 400 ngày. Cần null giữ tự tương quan — đề xuất §8.
3. **Q2:** G-RULE (`−momentum15M`, 1 cột, chọn bằng định nghĩa) ΔCAGR22 **+3,01**, CI inflate [−16,4; +23,7] ⇒ theo luật **"33 feature ≈ 1 quy tắc"** (CI rất rộng: không đo được khác biệt; KHÔNG phải bằng chứng quy tắc tốt hơn).
4. **Q3:** G-NOCAL ΔCAGR22 **+3,16**, CI inflate [−9,0; +18,8]; |Δ| ≤ |Δ_SEED7| = 5,31 ⇒ **"không phân biệt được với nhiễu retrain"**; luật đơn giản hoá ĐẠT ⇒ **đề xuất bỏ 4 cột lịch vì robustness** (owner quyết). Rank-IC NOCAL 0,537 ≥ gốc 0,513.
5. **Q4:** G-H60 ΔCAGR22 **−2,78**, CI inflate [−14,2; +7,2], |Δ| ≤ 5,31 ⇒ "không phân biệt được với nhiễu retrain"; **NO-GO** §9 A.4 (c1 trượt, c4 2/4 năm). Giữ nhãn 15'.
6. **Q5:** |ΔCAGR22_SEED7| = **5,31pp**, ΔPnL −21,8k, ΔmaxDD −2,5pp, UW22 117→334 ngày.
7. Chênh lệch lớn tập trung ở **2022** (A1 ROI 2022 chỉ 5,7%; RULE/NOCAL +16–17 điểm, SEED7 −11,7): năm DD sâu nhất là nơi kết quả nhạy nhất với chi tiết model gate.

## 1. Cổng
| cổng | kết quả |
|---|---|
| **G0 tái lập** (retrain seed 42, 33 feat, `label_oldbasket`, purge 15', fold +07/UTC đúng recipe) | **PASS** 19/19: pearson min/median/max 0,9919 / 0,9970 / 0,9987 (min fold 5 = 2022Q3), spearman min/median 0,9805 / 0,9968; p50 khớp ≤ 1e-4. Cùng mức RESULT_PREDBIN_REPRO; không byte-identical. |
| **Cổng nhãn 60'** (bản dựng Python H=15' vs `label_oldbasket`) | **PASS**: pearson 0,99999999 (mọi năm ≥ 0,9999999), join 2 496 540 = 100% store 2021-01..2025-09, |Δ| median 2,6e-9. Nhãn 60' median 1,005% (15': 0,489%), corr(15',60') 0,786. |
| **G1 format** | **PASS 5/5**: n 2 500 260, header/size giống, `ts` + `risk4h` byte-identical. md5: RND `6aee82af7ba40b4c3bb5d5e5b66eadf6`, RULE `800a4ecc8580c5fb6c9e7e27a0f5bd72`, NOCAL `3c02be8674d7a4b827f6418a43a11ad8`, H60 `36a6048165da8725153e1da00580c729`, SEED7 `b737fb6d64d198c14654ea9c92510b36`. Spearman vs gốc: RND −0,0005, RULE 0,654, NOCAL 0,971, H60 0,946, SEED7 0,996. |
| **Parity Kaggle** | **PASS 5/5**: jar 7368be46, mapper ≥ 800, `SELECTOR_RANK_TOPK=24` + B0OV trong prof_run, log `PRED_MD5_BASE=5dd6bb4c…` + `PRED_MD5_USED` = md5 arm, Java `WfoDataset LOAD offline OK … pred=2500260 (md5 verified)`. |
| **G2 quota** (±25%: n/năm A1 732; phút gate-mở/năm A1 146,5) | RND **TRƯỢT** (n 0,92×, phút 0,37×) ⇒ lỗi cơ chế, không diễn giải. RULE 1,04×/0,82× · NOCAL 1,01×/0,96× · H60 1,01×/1,11× · SEED7 0,96×/0,98× — PASS. |

**Spot-check G1** (p15 %, gốc → thay thế; 00:00 +07 và phút p15 gốc max của ngày):

| mốc | gốc | RND | RULE | NOCAL | H60 | SEED7 |
|---|---|---|---|---|---|---|
| 2022-06-13 00:00 | 0,669 | 0,535 | 0,664 | 0,716 | 0,615 | 0,677 |
| 2022-06-13 21:43 (max) | 2,295 | 0,467 | 1,543 | 1,763 | 2,170 | 1,783 |
| 2024-08-05 00:00 | 0,780 | 0,823 | 1,012 | 0,842 | 0,640 | 0,753 |
| 2024-08-05 08:10 (max) | 7,539 | 1,063 | 7,733 | 8,181 | 5,309 | 8,254 |
| 2025-10-10 00:00 | 0,769 | 0,667 | 0,800 | 0,780 | 0,705 | 0,774 |
| 2025-10-10 22:32 (max) | 2,593 | 0,573 | 3,513 | 2,553 | 1,841 | 2,715 |

Ghi chú: `pred.bin` gốc thực ra phủ tới 2026-01-01 06:59 +07 (420 phút cuối = 23:59 UTC); 420 phút này nằm ngoài mọi fold +07 nên arm retrain/RULE giữ p15 gốc ở đó (RND thay). Sim dừng 2025-12-30 ⇒ không ảnh hưởng.

## 2. Bảng arm (cửa sổ 2022–2025; MTM ngày, rebase 2021-12-31)
| arm | n | n/năm | phút gate-mở/năm | lệnh/phút gate | CAGR22 | maxDD MTM | Calmar22 | UW22 (ngày) | PnL 2022–25 | eq cuối |
|---|---|---|---|---|---|---|---|---|---|---|
| **A1** | 3526 | 732 | 146,5 | 4,53 | 36,65 | −22,21 | 1,650 | 117 | 103 357 | 144 974 |
| G-RND ⚠G2 | 3101 | 671 | 54,8 | 11,23 | 6,51 | −19,18 | 0,340 | 400 | 11 211 | 50 279 |
| G-RULE | 3632 | 764 | 119,8 | 5,85 | 39,66 | −19,33 | 2,052 | 172 | 116 998 | 158 776 |
| G-NOCAL | 3557 | 738 | 140,5 | 4,78 | 39,81 | −19,39 | 2,053 | 115 | 116 234 | 157 491 |
| G-H60 | 3460 | 741 | 162,3 | 4,15 | 33,87 | −21,70 | 1,561 | 208 | 90 972 | 132 152 |
| G-SEED7 (báo cáo) | 3413 | 705 | 143,0 | 4,45 | 31,34 | −22,75 | 1,377 | 334 | 81 587 | 122 936 |

md5 printDone: RND 6044726d…, RULE a9e5ceb2…, NOCAL fcef48ef…, H60 37068c7d…, SEED7 8f5e2912… (đủ trong json). Trùng lệnh với A1 (Jaccard): RND 1,5 · RULE 22 · NOCAL 60 · H60 36 · SEED7 59 (phần trăm; SEED7 chỉ trùng 59 phần trăm lệnh A1 dù p15 corr 0,99) — json (`overlap_vs_A1`).

## 3. Δ vs A1 — bootstrap MTM ngày ghép cặp (block 10d, NREP 2000, seed 20260905); inflate √(2 ln 4) = 1,6651
| cặp | ΔCAGR22 | CI raw | CI inflate | ΔPnL | CI inflate ΔPnL | ΔmaxDD | ΔCalmar (bootstrap ngày) |
|---|---|---|---|---|---|---|---|
| RND − A1 ⚠G2 | −30,13 | [−52,08; −10,44] | [−66,68; +2,65] | −92 146 | [−186 977; −7 250] | −0,73 | −1,95 |
| RULE − A1 | +3,01 | [−8,65; +15,41] | [−16,41; +23,66] | +13 641 | [−28 343; +60 051] | +4,10 | +1,10 |
| NOCAL − A1 | +3,16 | [−4,13; +12,54] | [−8,98; +18,77] | +12 877 | [−13 070; +43 393] | +3,26 | +0,88 |
| H60 − A1 | −2,78 | [−9,66; +3,21] | [−14,24; +7,19] | −12 384 | [−43 108; +15 213] | +1,23 | +0,01 |
| SEED7 − A1 (ngoài k) | −5,31 | [−10,63; −0,64] | [−14,17; +2,46] | −21 770 | [−40 777; −2 927] | −2,52 | −0,62 |
| NOCAL − SEED7 (báo cáo) | +8,47 | [−0,49; +19,78] | [−6,45; +27,30] | +34 647 | [−215; +72 617] | +5,77 | +1,50 |
| H60 − SEED7 (báo cáo) | +2,53 | [−5,17; +10,23] | [−10,29; +15,36] | +9 386 | [−24 646; +40 153] | +3,75 | +0,63 |

## 4. Theo năm và theo quý
**ROI năm % (n lệnh đóng · PnL · DD MTM năm)** và **ΔROI vs A1**:

| arm | 2022 | 2023 | 2024 | 2025 | ΔROI 22/23/24/25 | năm ΔROI ≥ 0 |
|---|---|---|---|---|---|---|
| A1 | 5,7 (592 · 2 376 · −22,2) | 69,0 (756 · 30 520 · −5,1) | 47,7 (839 · 35 275 · −12,1) | 32,0 (742 · 35 185 · −18,0) | — | — |
| RND ⚠ | 17,7 (509 · 6 915 · −14,6) | −7,9 (662 · −3 558 · −19,2) | 25,1 (739 · 11 032 · −7,4) | −5,1 (773 · −3 179 · −18,6) | +12,0 / −76,9 / −22,6 / −37,2 | 1/4 |
| RULE | 22,8 (652 · 9 524 · −19,3) | 53,6 (719 · 27 701 · −9,1) | 45,1 (882 · 35 378 · −15,1) | 38,8 (804 · 44 395 · −17,5) | +17,1 / −15,3 / −2,6 / +6,8 | 2/4 |
| NOCAL | 22,0 (634 · 9 095 · −18,3) | 63,0 (758 · 31 889 · −5,0) | 46,8 (811 · 38 236 · −12,2) | 30,7 (749 · 37 014 · −19,4) | +16,3 / −6,0 / −0,9 / −1,3 | 1/4 |
| H60 | 6,2 (583 · 2 553 · −21,7) | 53,8 (634 · 23 641 · −6,1) | 54,8 (863 · 36 755 · −11,6) | 26,9 (885 · 28 024 · −17,8) | +0,5 / −15,2 / +7,2 / −5,1 | 2/4 |
| SEED7 | −6,0 (464 · −2 472 · −22,7) | 62,4 (757 · 24 394 · −6,7) | 43,7 (879 · 27 429 · −12,2) | 35,5 (721 · 32 236 · −17,2) | −11,7 / −6,6 / −4,0 / +3,5 | 1/4 |

**Δ lợi suất MTM theo quý vs A1 (điểm %)** — 22Q1..25Q4:
- RND ⚠: −5,0 +16,0 −6,6 +6,3 | −15,9 −23,2 −11,7 −13,0 | −3,7 −1,0 +0,5 −14,3 | −21,0 −6,8 −0,5 −5,8
- RULE: −5,5 +17,8 +2,5 +0,7 | −1,4 −4,7 −4,7 +0,2 | −0,2 −6,4 +0,4 +5,6 | +4,8 +2,6 −1,0 −0,6
- NOCAL: −1,1 +13,1 +3,3 −0,5 | −2,3 +0,9 −3,8 +1,3 | +3,2 −1,3 −0,1 −2,2 | +0,2 +0,4 −1,5 −0,0
- H60: −1,8 +1,3 +1,1 −0,2 | −5,9 −2,1 −1,8 −0,7 | +0,4 +5,0 +0,4 −1,0 | −3,6 −1,0 +2,8 −2,8
- SEED7: −1,6 −6,9 −2,5 −0,2 | −2,0 −2,6 −1,8 +2,0 | −2,0 +0,2 +0,9 −2,5 | +1,1 −0,2 −0,2 +2,4

Đọc: lợi thế RULE/NOCAL gần như toàn bộ là **22Q2** (+17,8 / +13,1 điểm; tháng LUNA/3AC); bỏ quý đó NOCAL ≈ A1, RULE âm 2023. SEED7 mất chủ yếu ở 22Q2 (−6,9). ⇒ 1 quý quyết định thứ hạng mọi arm.

## 5. Trả lời Q1–Q5 theo luật pre-reg
| Q | luật | kết quả |
|---|---|---|
| Q1 timing | G-RND ngoài CI inflate (âm) ⇒ có timing | **KHÔNG DIỄN GIẢI** — G-RND trượt G2 (phút gate-mở 0,37×). Tham khảo: CI inflate ΔCAGR22 chứa 0 (cận trên +2,65), ΔPnL inflate toàn âm; IC RND = 0. |
| Q2 33 feat vs 1 quy tắc | G-RULE trong CI ⇒ "≈" | **"33 feature ≈ 1 quy tắc"** (CI [−16,4; +23,7]; |Δ| 3,01 < band SEED7 5,31) |
| Q3 cột lịch | |Δ| ≤ |Δ_SEED7| ⇒ không phân biệt | **Không phân biệt được với nhiễu retrain** (3,16 ≤ 5,31); luật đơn giản hoá **ĐẠT** ⇒ đề xuất bỏ cột lịch (owner quyết) |
| Q4 nhãn 60' | band + GO §9 A.4 | **Không phân biệt được với nhiễu retrain** (2,78 ≤ 5,31); **NO-GO** (c1 Δ>0 ngoài CI: trượt; c2 DD −21,7 ≥ −40: đạt; c3 Calmar22 1,561 ≥ 0,9×1,650 = 1,485: đạt; c4 2/4 năm: trượt) |
| Q5 nhiễu retrain | báo cáo | **|ΔCAGR22| 5,31pp**, ΔPnL −21,8k (CI raw [−33,2k; −10,5k]), ΔmaxDD −2,5, Calmar22 1,650→1,377 |

## 6. Rank-IC offline (báo cáo; Spearman theo phút, 2022-01-01..2025-09-30, n = 1 971 360)
| chuỗi | IC vs nhãn 15' | IC vs nhãn 60' | IC 15' theo năm 22/23/24/25 |
|---|---|---|---|
| p15 gốc | 0,5133 | 0,4962 | 0,419 / 0,442 / 0,441 / 0,407 |
| RND | −0,0011 | −0,0017 | ≈ 0 |
| RULE | 0,3835 | 0,3725 | 0,263 / 0,241 / 0,244 / 0,229 |
| NOCAL | **0,5365** | **0,5180** | 0,439 / 0,458 / 0,439 / 0,408 |
| H60 | 0,5012 | 0,4929 | 0,412 / 0,421 / 0,435 / 0,403 |
| SEED7 | 0,5136 | 0,4963 | 0,419 / 0,442 / 0,442 / 0,407 |

Đọc: (a) IC không dự báo tiền: SEED7 cùng IC với gốc (0,5136 vs 0,5133) mà −5,3pp CAGR; RULE IC thấp hơn 0,13 mà CAGR không kém. Gate quota chỉ dùng **đuôi cực trên** (≈ 5e-5) của r — IC toàn phân phối không đo phần đó. (b) Bỏ cột lịch làm IC TĂNG ở cả 4 năm ⇒ 4 cột lịch không mang tín hiệu OOS, nhất quán với giả thuyết khớp regime. (c) Mô hình học nhãn 60' không xếp hạng nhãn 60' tốt hơn mô hình 15' (0,4929 vs 0,4962).

## 7. Lệch pre-reg / ghi chú
- Không đổi arm, luật, thước, biến đổi §3.1 sau khi thấy số. 0 arm thêm.
- "Phút gate-mở" = số phút phân biệt có ≥ 1 entry PREDICT_SYMBOL_TRADE (định nghĩa đã chốt §4 pre-reg). G-RND trượt chính tiêu chí này.
- MTM A1 lấy từ cache `n700` (md5 printDone d9abf35f khớp) — cùng hàm `run_mtm`.
- 420 phút cuối `pred.bin` (2026-01-01 00:00–06:59 +07) giữ p15 gốc (§3.2) — ngoài cửa sổ sim.
- Dòng trailer commit dùng model thật đang chạy (Opus 5.5), không dùng tên trong brief.

## 8. Rủi ro + đề xuất cho MASTER (không tự quyết)
**Rủi ro:**
1. **B0/A1 nằm trong band nhiễu seed ±5pp CAGR22** (1 seed khác ⇒ 2022 ROI từ +5,7 xuống −6,0). Mọi lever/so sánh gate sau này (K, pct, gs, feature, nhãn) có |Δ| < ~5pp đều không phân biệt được với đổi seed, dù CI bootstrap ngày hẹp hơn: bootstrap ngày KHÔNG đo phương sai retrain.
2. Thứ hạng arm do 1 quý (22Q2) quyết định ⇒ mẫu DEV hiệu dụng cho gate rất nhỏ.
3. Null ngẫu nhiên iid theo phút phá cấu trúc cụm (G2 trượt) ⇒ Q1 vẫn mở.
4. Đường chèn `pred_ds` mới, chưa có run "pred gốc qua đường chèn" (đã kiểm md5 base/used + Java md5 verified; sai khác chỉ có thể đến từ dữ liệu pred).
**Đề xuất:**
- (P1) Vòng **GATE_SEEDBAND**: retrain gate với ~5–8 seed (cùng recipe) → sim K24 ⇒ phân phối CAGR22/PnL theo seed; dùng làm band nhiễu chuẩn cho mọi vòng gate sau; cân nhắc **bagging seed** (TB p15 của N seed) làm gate deploy để giảm phương sai — cần pre-reg riêng.
- (P2) Q1 làm lại với null **giữ tự tương quan**: p15 gốc dịch vòng (circular shift) theo khối ≥ 30 ngày, hoặc hoán vị khối ngày — cùng biên + cùng cụm; G2 phải đạt trước khi diễn giải.
- (P3) Bỏ 4 cột lịch (luật đơn giản hoá ĐẠT; IC tăng 4/4 năm) — quyết định owner; nếu áp, retrain fold live theo 30 feature + parity ONNX.
- (P4) Giữ nhãn 15' (H60 NO-GO). Không theo đuổi G-RULE thay model (≈ nhưng CI ±20pp, 2023 −15 điểm).

## 9. Tái lập
`python3 research/analysis/gate_ablation_driver.py retrain G0|NOCAL|SEED7|H60` (xgb-env) · `label60 --workers 3` · `labelgate` · `gen ARM` · `g1` · `upload ARM` · `submit ARM --code-sha a629ff6f` · `fetch ARM` · `parity` · `score --workers 3` · `ic`. Artefact: `~/claude_master/1004/gabl/` (pred_*/pred.bin, p15_*.npy, label60.npz, retrain_*.json, labelgate.json, g1.json, ic.json, mtm.json); Kaggle out `~/kaggle_sim/out/gabl-{rnd,rule,nocal,h60,seed7}`; dataset `chuyendinh/gate-abl-*`.
