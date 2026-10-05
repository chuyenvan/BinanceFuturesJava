# RESULT_SHORT_V3_R1C — lớp EXECUTION của fade (TAKER vs LIMIT +0,7% maker × TS 24h/48h)

Pre-reg: `docs/prereg/PREREG_SHORT_V3_R1C.md` (`41760f10`, chốt TRƯỚC đo) · Program: `PROGRAM_SHORT_V3.md` ADDENDUM 2 (`985044ba`) · trigger: R1 `3fea4f50`
Script: `research/analysis/short_v3_r1c_exec.py` (`scan` → `report`) · Số: `docs/result/RESULT_SHORT_V3_R1C.json` · per-trade: `~/claude_master/1002/r1c_cache/trades_r1c.csv` (ngoài repo).
DEV 2022–2025 (mọi cửa sổ ≤ 2025-12-31 23:59 UTC; 2026 không đọc). 0 Java, 0 sửa .java, 0 chạm 242. Stream 48 tháng 3 proc ≈ 25 phút (Σ 4 487 s), lock `oracle_heavy.lock` = R1c.

## Kết luận: **NO-GO** — cả 4 ô gãy G1 (CI raw chứa 0) và G4 (SL-rate 27,6–31,0% > 25%); S_TK48 gãy thêm G2.
LIMIT +0,7% KHÔNG cứu được fade: giá vào tốt hơn (+0,35% gross) bị ăn hết bởi **adverse selection** (−0,44%): lệnh fill chính là lệnh giá còn chạy tiếp.
TS 48h không thêm gì (mean giảm, SL tăng). ⇒ Theo PROGRAM: ĐÓNG short trên dữ liệu hiện có; R1 giữ làm "tín hiệu mỏng có thật" chờ fill thật/L2.

| ô (k=4) | G1 net>0 ngoài CI raw & infl | G2 ≥3/4 năm + | G3 n ≥ 1500 | G4 SL ≤ 25% | G5 stress −0,10% > 0 | G6 LONG ≤ 0 | GO |
|---|---|---|---|---|---|---|---|
| S_TK24 | ✘ raw [−0,030; +0,369] | ✔ 4/4 | ✔ 10 977 | ✘ 27,6% | ✔ +0,070% | ✔ −0,446% | ✘ |
| S_TK48 | ✘ raw [−0,028; +0,337] | ✘ 2/4 | ✔ 10 977 | ✘ 29,5% | ✔ +0,052% | ✔ −0,415% | ✘ |
| S_LM24 | ✘ raw [−0,085; +0,303] | ✔ 3/4 | ✔ 8 274 | ✘ 29,6% | ✔ +0,011% | ✔ −0,314% | ✘ |
| S_LM48 | ✘ raw [−0,090; +0,296] | ✔ 3/4 | ✔ 8 274 | ✘ 31,0% | ✔ +0,002% | ✔ −0,320% | ✘ |

## 0. Tập trigger
R1 n = 10 991 → giữ **10 977** (loại **14** trigger 2025-12-30 00:00…16:24 UTC vì t + 15 + 2880 > 2025-12-31 23:59; trigger cuối giữ ≤ 2025-12-29 23:44).
Cùng tập cho cả 4 ô short, 2 ô tập-con, 4 ô LONG. R1 S_B24 trên 10 991 = +0,1699%; trên 10 977 = +0,1697%.

## 1. Bảng ô (net/lệnh, %; CI block 72h NREP 2000 seed 20260905; inflate nửa-độ-rộng × 1,67)
| ô | n | net mean | median | CI raw | CI inflate | 2022 / 2023 / 2024 / 2025 | SL | SL phút fill | TRAIL | TIME | win | gross | funding | held h | min | p1 | stress −0,10% |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **S_TK24** | 10 977 | +0,170 | +2,75 | [−0,030; +0,369] | [−0,163; +0,502] | +0,54 / +0,04 / +0,04 / +0,19 | 27,6% | — | 60,2% | 12,2% | 66,9% | +0,317 | −0,036 | 7,3 | −15,8 | −10,4 | +0,070 |
| **S_TK48** | 10 977 | +0,152 | +2,83 | [−0,028; +0,337] | [−0,148; +0,461] | +0,49 / −0,01 / −0,01 / +0,20 | 29,5% | — | 65,5% | 5,0% | 67,7% | +0,300 | −0,036 | 9,1 | −17,4 | −10,5 | +0,052 |
| **S_LM24** | 8 274 | +0,111 | +2,82 | [−0,085; +0,303] | [−0,217; +0,431] | +0,46 / −0,04 / +0,07 / +0,10 | 29,6% | 1,1% | 61,3% | 9,2% | 66,4% | +0,222 | −0,036 | 6,1 | −12,3 | −10,4 | +0,011 |
| **S_LM48** | 8 274 | +0,102 | +2,89 | [−0,090; +0,296] | [−0,219; +0,426] | +0,44 / −0,06 / +0,05 / +0,10 | 31,0% | 1,1% | 65,5% | 3,5% | 67,0% | +0,215 | −0,036 | 7,4 | −12,3 | −10,4 | +0,002 |
| S_TKsub24 (tập fill LIMIT) | 8 274 | −0,272 | +2,64 | [−0,479; −0,066] | [−0,618; +0,071] | +0,11 / −0,47 / −0,39 / −0,25 | 31,3% | — | 58,4% | 10,3% | 64,2% | −0,123 | −0,037 | 6,5 | −15,8 | −10,5 | −0,372 |
| S_TKsub48 (tập fill LIMIT) | 8 274 | −0,284 | +2,73 | [−0,482; −0,088] | [−0,614; +0,043] | +0,09 / −0,47 / −0,42 / −0,25 | 32,8% | — | 63,1% | 4,1% | 64,8% | −0,135 | −0,037 | 8,0 | −15,8 | −10,5 | −0,384 |

Phí: TAKER 0,056 + 0,056 = 0,112% RT; LIMIT 0,02 (maker) + 0,056 = 0,076% RT. Năm = năm UTC của entry (LIMIT: phút fill). 100% lệnh có coin trong funding store.
n theo năm (TK / LM): 2022 1 135 / 871 · 2023 1 555 / 1 137 · 2024 2 468 / 1 829 · 2025 5 819 / 4 437 (2025 = 53% lệnh).
SL-rate theo năm S_TK24: 25,5 / 27,9 / 27,6 / 28,0%; S_LM24: 27,7 / 30,0 / 28,7 / 30,2% — không năm nào ≤ 25% ở ô LIMIT.

## 2. Đối chứng LONG (mirror; G6)
| ô | n | net mean | median | CI raw | CI inflate | 2022 / 2023 / 2024 / 2025 | SL | win | gross | funding |
|---|---|---|---|---|---|---|---|---|---|---|
| L_TK24 | 10 977 | −0,446 | +2,11 | [−0,641; −0,250] | [−0,773; −0,119] | −0,76 / −0,40 / −0,33 / −0,44 | 24,4% | 58,1% | −0,370 | +0,036 |
| L_TK48 | 10 977 | −0,415 | +2,31 | [−0,623; −0,212] | [−0,762; −0,075] | −0,74 / −0,40 / −0,37 / −0,38 | 30,3% | 61,2% | −0,339 | +0,036 |
| L_LM24 (buy limit ×0,993) | 9 297 | −0,314 | +2,16 | [−0,519; −0,103] | [−0,656; +0,039] | −0,94 / −0,40 / −0,26 / −0,20 | 23,8% | 58,3% | −0,271 | +0,033 |
| L_LM48 | 9 297 | −0,320 | +2,33 | [−0,539; −0,092] | [−0,686; +0,061] | −0,93 / −0,39 / −0,27 / −0,21 | 29,7% | 61,1% | −0,277 | +0,033 |
LONG âm 0/4 năm ở cả 4 ô ⇒ G6 đạt mọi ô; hướng sau trigger vẫn nghiêng xuống (như R1). Thứ gãy là độ lớn + đuôi continuation, không phải dấu.

## 3. Fill-rate LIMIT
| | SHORT sell limit close_t × 1,007 | LONG buy limit close_t × 0,993 |
|---|---|---|
| fill / trigger | **8 274 / 10 977 = 75,4%** | 9 297 / 10 977 = 84,7% |
| theo năm 2022 / 23 / 24 / 25 | 76,7 / 73,1 / 74,1 / 76,3% | 81,7 / 82,6 / 84,0 / 86,1% |
| fill ở phút t+1 | 57,0% (4 716) | 55,9% |
| fill phút t+2 / t+3 / t+4..t+15 | 1 210 / 602 / 1 746 | 1 413 / 681 / 2 009 |
| open phút fill đã vượt Lp (gap; vẫn fill tại Lp) | 0,12% | 0,10% |
Cả hai phía đều fill > 75% trong 15': biên độ 1m sau spike ≥ ±0,7% là bình thường ⇒ δ = 0,7% không đủ xa để "chọn" mà chủ yếu là lọc bỏ lệnh đảo chiều ngay.
6 629 trigger fill CẢ hai phía (60%) — dao động hai chiều quanh close_t.

## 4. "Chọn lệnh vs giá vào" (ô 24h; 48h gần như y hệt)
LIMIT − TAKER(toàn tập) = **−0,059%** = chọn lệnh **−0,442%** (TKsub − TK) + giá vào & phí **+0,383%** (LM − TKsub; gồm gross +0,346, phí +0,036, funding +0,001).
- Tập KHÔNG fill (2 703 trigger, 24,6%) — giá không lên nổi +0,7% trong 15' — có TAKER-24h net ≈ **+1,52%/lệnh** (suy từ 10 977 × 0,1697 − 8 274 × (−0,272));
  tập fill có TAKER-24h **−0,272%** (CI raw [−0,479; −0,066], 1/4 năm dương). Toàn bộ edge của R1 nằm ở lệnh đảo chiều NGAY sau trigger.
- Giá vào +0,7% kéo tập fill từ −0,27% lên +0,11% nhưng không bù được việc mất nhóm +1,5%. 48h: −0,050 = −0,436 + 0,386.
- ⇒ LIMIT trên đỉnh là **adverse selection thuần**: nó khớp đúng những lệnh momentum còn chạy (continuation), là thứ R1b cũng không tách được bằng feature tại t.

## 5. Adverse selection — SL-rate
| | TAKER toàn tập | TAKER tập fill (TKsub) | LIMIT (giá +0,7%) |
|---|---|---|---|
| SL-rate 24h | 27,6% | **31,3%** | 29,6% (trong đó 1,1% SL ngay phút fill) |
| SL-rate 48h | 29,5% | **32,8%** | 31,0% |
Tập fill có SL-rate cao hơn toàn tập +3,7 điểm (24h); giá vào tốt hơn 0,7% chỉ kéo lại 1,7 điểm. Tail min LIMIT −12,3% vs TKsub −15,8% trên CÙNG tập (entry cao hơn 0,7%, SL đặt theo giá fill) — không đổi kết luận.

## 6. TS 48h có thêm gì? — Không.
TAKER: 24h +0,170 → 48h +0,152 (2023/2024 thành âm nhẹ, 4/4 → 2/4 năm), SL 27,6 → 29,5%, TIME 12,2 → 5,0%. LIMIT: +0,111 → +0,102, SL 29,6 → 31,0%.
Đơn điệu tăng theo TS ở R1 (4h → 12h → 24h: +0,03 → +0,10 → +0,17) DỪNG ở 24h: giữ thêm 24h chỉ chuyển lệnh TIME thành SL/TRAIL, không thêm drift.

## 7. Theo năm — ô tốt nhất S_TK24 (không ô nào GO ⇒ "tốt nhất" = mean short chính cao nhất; chỉ báo cáo)
| năm | n | S_TK24 | L_TK24 | S_LM24 (n) | S_TKsub24 | SL S_TK24 |
|---|---|---|---|---|---|---|
| 2022 | 1 135 | +0,54% | −0,76% | +0,46% (871) | +0,11% | 25,5% |
| 2023 | 1 555 | +0,04% | −0,40% | −0,04% (1 137) | −0,47% | 27,9% |
| 2024 | 2 468 | +0,04% | −0,33% | +0,07% (1 829) | −0,39% | 27,6% |
| 2025 | 5 819 | +0,19% | −0,44% | +0,10% (4 437) | −0,25% | 28,0% |
2023–2024 ≈ 0 ở mọi ô; sau stress −0,10% chỉ 2/4 năm dương (S_TK24), 1/4 (S_LM24).

## 8. Sanity (PASS cả 4)
- **S1 tái lập R1:** S_TK24 trên 10 977 = +0,16971% vs R1 S_B24 cùng tập +0,16971% (Δ mean 1e-17; |Δnet| per-trade max 1e-16 < 1e-6); phút exit & lý do exit trùng
  **100%**; L_TK24 vs R1 L_B24: −0,44583% = −0,44583%, phút/lý do trùng 100%. (Phí 0,056 + 0,056 = 0,112 R1 ⇒ khớp đúng như kỳ vọng.)
- **S2 10 lệnh SHORT-LIMIT mẫu (seed 20260905), kiểm tay fill:** H phút t+1..t+15 vs Lp — cả 10 phút fill = phút ĐẦU TIÊN có H ≥ Lp (vd HOTUSDT 2022-11-22 20:21:
  Lp 0,00161321, H t+3 = 0,0016130 < Lp, t+4 = 0,001618 ≥ ⇒ fill t+4 ✔; LEVERUSDT 2024-08-18 16:42: max H t+1..t+7 = 0,0019144 < Lp 0,0019198, t+8 = 0,0019468 ⇒ fill t+8 ✔;
  LPTUSDT 2024-03-08 16:20 fill t+4 rồi SL đúng −10,00% gross ✔). open phút fill < Lp ở cả 10.
| sym | t UTC | close t | Lp | phút fill | lý do S_LM24 | gross S_LM24 | gross S_TK24 |
|---|---|---|---|---|---|---|---|
| HOTUSDT | 2022-11-22 20:21 | 0,001602 | 0,00161321 | t+4 | TIME | −0,30% | −0,56% |
| LPTUSDT | 2024-03-08 16:20 | 17,573 | 17,69601 | t+4 | SL | −10,00% | −10,00% |
| 1INCHUSDT | 2024-05-30 19:34 | 0,5223 | 0,525956 | t+1 | TRAIL | +3,36% | +3,35% |
| LEVERUSDT | 2024-08-18 16:42 | 0,0019065 | 0,00191985 | t+8 | TRAIL | +7,27% | +5,71% |
| ONTUSDT | 2024-12-03 23:25 | 0,3855 | 0,388199 | t+1 | TRAIL | +3,87% | +4,14% |
| BROCCOLIF3BUSDT | 2025-09-20 05:55 | 0,013501 | 0,0135955 | t+2 | TRAIL | +3,31% | +3,04% |
| COTIUSDT | 2025-11-09 18:10 | 0,04116 | 0,0414481 | t+1 | TRAIL | +2,16% | +2,45% |
| NILUSDT | 2025-11-16 19:57 | 0,2263 | 0,227884 | t+2 | TRAIL | +3,50% | +3,17% |
| IPUSDT | 2025-11-30 16:39 | 2,629 | 2,647403 | t+1 | TRAIL | +3,55% | +3,46% |
| REDUSDT | 2025-12-07 03:36 | 0,2856 | 0,287599 | t+2 | TRAIL | +8,28% | +7,93% |
- **S3 causal:** Lp chỉ từ close t (assert = `c_t` cache R1, P = close t+1 R1); nhiễu dữ liệu > t (10 977 trigger) ⇒ Lp không đổi 10 977/10 977; nhiễu > t+15 ⇒ phút fill & P
  không đổi 10 977/10 977; nhiễu > e+TS cho từng chân/TS (79 050 phép) ⇒ kết quả exit không đổi 79 050/79 050. Assert fill ∈ [t+1, t+15], exit ∈ [e, e+TS], exit ≤ 2025-12-31 23:59.
- **S4 vectorized vs loop thuần:** 79 050 phép (mọi trigger × 8 cấu hình có entry, cả 48 tháng — rộng hơn mức tháng thử pre-reg): |Δpnl| < 1e-9, phút/lý do trùng 100%.
- Tháng thử 2024-03 (415 trigger, 98 s 1 proc) chạy trước full; nsym tối đa/tháng 377 (chỉ giữ symbol có trigger).

## 9. Giới hạn
- **Queue position maker CHƯA mô hình:** fill khi H_1m chạm đúng Lp là LẠC QUAN. Thực tế lệnh chạm-vừa-đủ (H − Lp nhỏ) thường không khớp hết; fill-rate 75% và
  net LIMIT là CẬN TRÊN. Chiều lệch: lệnh "chạm nhẹ rồi quay đầu" (tốt cho short) là lệnh dễ KHÔNG khớp nhất ⇒ adverse selection thực tế còn nặng hơn số ở đây.
- SL phút fill tính tại đúng Lp × 1,10 (không dùng open — open trước fill); L phút fill không dùng để arm (bảo thủ). 1,1% lệnh LIMIT dính SL ngay phút fill.
- Funding: 41% sự kiện trong store có fundingTime lệch ms khỏi mốc phút (vd 23:00:00.001) ⇒ với LIMIT fill đúng phút settle, sự kiện được tính là đã giữ (lệch ≤ 1 sự kiện,
  chỉ ảnh hưởng lệnh fill trúng phút settle; funding mean LM = TKsub ± 0,001% ⇒ không đáng kể). TAKER entry tại :59.999 không bị ảnh hưởng.
- Slippage TAKER tại spike chỉ có cột stress −0,10%; ô TAKER cần entry ở close t+1 — đúng phút spike — thực tế xấu hơn. Không giới hạn vốn/đồng thời.
- 2025 chiếm 53% lệnh; 2023–2024 ≈ 0 ở mọi ô.

## 10. Ý nghĩa cho chương trình (không chạy thêm gì trong vòng này)
- 3 lớp đã thử trên cùng trigger R1: exit (R1, 6 ô), selector tại t (R1b, 13 feature), execution (R1c, 2×2) — đều NO-GO với cùng một điều kiện gãy: continuation
  ~28–31% lệnh chạm SL +10% và CI raw chứa 0. Phí và giá vào KHÔNG phải nút thắt: bỏ 0,036% phí + vào giá tốt hơn 0,7% vẫn không qua G1.
- Quan sát duy nhất có cấu trúc: edge nằm ở nhóm "không lên thêm 0,7% trong 15'" (+1,5%/lệnh, n 2 703) — nhưng đây là điều kiện TƯƠNG LAI (t+1..t+15), không phải
  tín hiệu tại t; dùng nó như filter = vào lệnh sau 15' với thông tin mới ⇒ là thiết kế khác (entry trễ có điều kiện), cần pre-reg mới + holdout. Ghi lại, không chạy.
- Theo ADDENDUM 2: NO-GO ⇒ ĐÓNG short trên dữ liệu hiện có (20 vòng pre-reg); giữ R1 như tín hiệu mỏng có thật (long âm 0/4 năm mọi ô) để kiểm forward khi có fill thật/L2.

## 11. Tái lập
`python3 research/analysis/short_v3_r1c_exec.py scan --months 202403 --procs 1` → `scan --months all --procs 3` → `report`
(nguồn trigger `~/claude_master/1002/r1_cache/trades_r1.csv` + `cand_*.parquet`; cache tháng `~/claude_master/1002/r1c_cache/r1c_YYYYMM.parquet` + `meta_*.json`;
funding `/tmp/fund_cache.npz`; Aerospike `test.kline_1m_opt` 127.0.0.1:3222).
