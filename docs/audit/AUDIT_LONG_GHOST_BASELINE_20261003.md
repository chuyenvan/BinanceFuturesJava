# AUDIT LONG_GHOST_BASELINE (2026-10-03) — L0 symbol ma + L5 chấm lại nền T170/R4/G2/B0

0-sim (không Kaggle, không Java, không sửa .java, không chạm 242/shadow). Chỉ đọc artifact có sẵn trên Oracle.
Script: `research/analysis/long_ghost_baseline.py` (stage `scan,ghost,label,pb,mtm,l5,extra`); số liệu: `docs/audit/AUDIT_LONG_GHOST_BASELINE_20261003.json`.
Lineage: `data/meta/symbol_lineage_v2.csv` (`last_real_ts`; mã còn sống tới hết DEV ⇒ `last_real` bị kiểm duyệt, KHÔNG tính ma).

## TL;DR
- **L0 — symbol ma không làm lệch kết luận.** 0 lệnh vào sau `last_real_ts` ở cả 5 cấu hình. B0: 6 leg đang giữ qua ngày chết (−688$, −0,71% ΣPnL), 7 leg vào trong 24h trước chết (−146$), 3 leg index (BLUEBIRD/DEFI/FOOTBALL, −102$). Tập train selector (cand_dev_x1, pred_s1a2x1, `.pb` ds_label15m, feature t1c) **0 dòng ma**; chỉ 0,45% nhãn 72h có cửa sổ cắt qua ngày chết. Bundle ticker THÌ có nến ma (vol=0) tăng dần: 0,97% → 3,1% → 4,0% → 8,0% symbol-phút (2022→2025), tối đa 19% universe/ngày — rủi ro cho feature toàn-universe (market.bin) **chưa audit**.
- **L5 — B0 KHÔNG tốt hơn T170-ở-0,11 một cách có ý nghĩa.** Mọi Δ (Calmar, CAGR, maxDD, Sharpe) B0 vs T170c đều có CI chứa 0. Điểm: B0 nhỉnh hơn (Calmar_MTM 1,94 vs 1,83; UW 87 vs 129 ngày; top-5 episode 36,6% vs 44,8%), T170c tốt hơn ở 2022 bear (+23,1% vs +11,1%, DD −14,8 vs −17,7).
- **Tiền đề "n×2,3 ⇒ slippage×2,3" sai:** Σnotional B0/T170 chỉ ×1,245 (B0 lệnh nhỏ $997 vs $1.851). Slippage tuyến tính theo notional: T170c chỉ vượt B0 khi s > **1,41%/vòng**; phí cố định/lệnh: > $4,87/lệnh; impact √size: **B0 thắng với mọi k**.
- **Luật "n primary" không hợp lệ:** R4 vs R0 ΔCAGR −5,4pp CI raw [−11,8; −0,4] (ngoài raw, trong infl k=3), không đổi được gì ở Calmar/Sharpe/DD. Chuỗi T170→R4 là bước lùi; R4→G2→B0 chỉ kéo lại ≈ mức T170c.
- **Không đề xuất BASELINE_REVERT** (điều kiện "T170/R4 hơn B0 ở Calmar cùng exposure ngoài CI" KHÔNG thỏa). B0 giữ làm nền vì không có gì hơn nó có ý nghĩa + lệnh nhỏ hơn (impact thấp), KHÔNG phải vì đã chứng minh hơn T170.

## Artifact (xác minh md5 printDone + profile result.json)

| tên | tag Kaggle | md5 printDone | profile / khác biệt | phí |
|---|---|---|---|---|
| T170 | `t170-x1-2021` | efb793e2 | x1_gs_t170 (DCA 1,1,3,8), n 1089 | 0,8%/vòng (cũ, implied median 0,00800) |
| T170c | = T170 | efb793e2 | hiệu chỉnh phí về 0,1116%: ΔPnL = Σnotional×(0,008−0,001116), tuyến tính, KHÔNG compound | 0,1116% |
| R0 | `p2-r0-base` | d297ce6b | x1_gs_t170 + override DCA **1,1,1,1** scale 6, cap 15%, K8 — **KHÔNG phải T170** | SIM_RATE_FEE 0,000982 (+slip 6,7e-5) |
| R4 | `p2-r4-base` | 06fd6e9a | R0 + K16, F_BASE 0,015, gate 1,55 | 0,000982 |
| G2 | `gdv2-g2` | 853aaa08 | r4_kg0_k16_f015_g155 + gate rolling 90d | 0,1116 (implied 0,00112) |
| B0 | `de-p1` | 650c386f | G2 + TS_MAX_GAP 0,03 / giveback 1,0 (FLAT3), jar 7368be46 | 0,1116 |

**Không có artifact T170 chạy ở cost 0,11** (grep 90+ run profile x1_gs_t170: chỉ `p2-r*` có SIM_RATE_FEE 0,000982 và đều override DCA 1,1,1,1). Nên T170 ở 0,11 = T170c (ước lượng phí tuyến tính). Sai số: bỏ qua compound phí tiết kiệm → **CAGR T170c bị đánh giá THẤP** (thiên vị có lợi cho B0). R0 (chạy thật ở 0,11, DCA phẳng) cho kết quả gần T170c (CAGR 32,97 vs 32,70) — kiểm chéo hợp lý.

## L0 — Symbol ma

### L0.1 Lệnh sim (printDone 5 cấu hình; nến quyết định khớp giá vào 100%: 2517/2517 B0, 0 nến vol=0)

| | n | vào SAU last_real | giữ QUA ngày chết (ΣPnL) | vào ≤24h trước chết (ΣPnL) | ≤7 ngày trước chết | leg index/stable (ΣPnL) |
|---|---|---|---|---|---|---|
| T170 | 1089 | **0** | 0 | 3 (+677) | 31 (+2.482) | 1 DEFI (+39) |
| R0 | 1086 | **0** | 6 ANC,FTT (−2.132; funding −719) | 2 (−5) | 29 | 1 DEFI (+41) |
| R4 | 2027 | **0** | 5 FTT,RAY,PERP (−742) | 4 (+322) | 38 | 4 BLUEBIRD,DEFI (+23) |
| G2 | 2509 | **0** | 6 LUNA,RAY,FTT,FLM (−684) | 7 (−160) | 43 | 3 (−101) |
| B0 | 2517 | **0** | 6 LUNA,RAY,FTT×3,FLM (−688; funding −232) | 7 (−146) | 43 (+760) | 3 BLUEBIRD,DEFI,FOOTBALL (−102) |

- Leg "giữ qua ngày chết" thoát bằng time-stop 7 ngày ở **giá đóng băng = giá settle** ⇒ PnL ≈ thực tế (Binance settle tại giá delist); sai lệch chỉ là (a) khoá slot 7 ngày, (b) funding trong giai đoạn ma (B0 tổng |232$| là CẬN TRÊN — chưa xác minh map funding Aerospike có kỳ sau delist).
- Không có key lọc universe entry: `SYMBOL_BLACKLIST|EXCLUDE_SYMBOLS` không tồn tại; `DIED_SYMBOLS=BTCDOM,USDC` chỉ dùng ở MarketBigChangeDetector/TickWeakBlock/MarketDataInline (feature thị trường), KHÔNG ở đường vào lệnh.
- **Đề xuất (chỉ đề xuất, ưu tiên thấp):** (a) lọc entry index (BTCDOM, BLUEBIRD, DEFI, FOOTBALL, PAXG/XAU/XAG, USDC) — ΔPnL B0 ≈ +102$ (+0,1%); (b) sim force-settle tại `last_real_ts` theo lineage — ΔPnL ≤ +232$ (funding) + giải phóng slot. Gộp (a)+(b) loại leg: B0 +790$ (+0,82% ΣPnL), R0 +2.091$ (+2,3%). Không đổi kết luận nào.

### L0.2 Bundle ticker (kaggle_data_hpo/daily = wfo-ticker-*, 1826 ngày 2021–2025, 627 symbol, 0 symbol thiếu lineage)

| năm | symbol-phút | ma (sau last_real) | % ma | ma có vol>0 | max symbol ma/phút | % universe ma/ngày TB / max |
|---|---|---|---|---|---|---|
| 2021 | 57,7M | 11 | 0,00% | 0 | 1 | 0,00 / 0,01 |
| 2022 | 72,7M | 0,70M | 0,97% | 0 | 5 | 0,93 / 3,40 |
| 2023 | 100,4M | 3,11M | 3,10% | 0 | 7 | 3,12 / 3,57 |
| 2024 | 149,4M | 5,99M | 4,01% | 0 | 22 | 3,94 / 6,20 |
| 2025 | 250,2M | 19,99M | 7,99% | 0 | 78 | 7,86 / 19,06 |

96 symbol có phút ma (lớn nhất SC, FTT, RAY, BTS, STRAX, DGB…); 100% phút ma có vol=0 (giá settle đóng băng). Sim không vào lệnh ma (L0.1) vì selector/pred không có dòng ma (L0.3). **Rủi ro còn mở:** mọi feature tính trên toàn universe từ ticker (breadth/rank trong `market.bin` Kernel A, gate p15) bị pha loãng tăng dần theo thời gian (2025: TB 7,9%, max 19% coin "phẳng") ⇒ phi dừng có hệ thống. Trong Java `MarketBigChangeDetector` dùng `TreeMap<Float,String>` key = rateChange nên mọi coin ma (rate=0) gộp thành ≤1 phần tử (giới hạn ngẫu nhiên tác động); đường Python sinh `market.bin` CHƯA audit trong phiên này.

### L0.3 Nhãn/feature train selector

| tập | dòng (DEV) | dòng ma (sau last_real) | cửa sổ nhãn cắt qua ngày chết |
|---|---|---|---|
| `ledger/cand_dev_x1.parquet` (nhãn 72h, 2021–2025) | 7.020.129 | **0** | 0 |
| `ledger/pred_s1a2x1.parquet` (pred S1, top-K8/16) | 6.573.909 | **0** | 0 |
| `.pb` ds_label15m (nguồn G015/S1, 19 file DEV) | 39.652.119 | **0** | 4h: 9.799 (0,025%); 72h: 177.109 (0,45%) |
| feature t1c ds_feat15m (2022Q4, 2025Q3, 2025Q4) | 9.841.118 | **0** (max ts = last_real: FTT 11-14 04:00, RAY 11-15 04:00, SRM 11-15 04:30) | — |

- `g015_net_train.py` inner-join feature×nhãn `.pb` ⇒ tập train **0 dòng ma**; OI merge_asof backward chỉ trên dòng feature (đã dừng tại last_real) ⇒ không đọc OI ma. Giả thuyết "model học phẳng = không pump" **không áp dụng**. **Không cần retrain.** Tuỳ chọn pre-reg (rẻ, kỳ vọng ~0): loại 0,45% dòng nhãn 72h có cửa sổ cắt ngày chết (nhãn hiện = return tới giá settle, vốn đã hợp lý).
- Riêng `CLOSES_1H.bin` v1 (dùng cho nghiên cứu, không train selector) chứa 319k dòng ma (9,27M vs 8,95M v2). IC S1-trend (rank, block-CI) v2−v1: 4h −0,0024 [−0,0035; −0,0014], 24h −0,0049 [−0,0074; −0,0024], 72h −0,0074 [−0,0116; −0,0030] ⇒ v1 làm |IC| co về 0 ~6–10% (lưu ý: 29k/35k snapshot đổi, có thể lẫn khác biệt v2 ngoài lọc ma).

### L0.4 Funding/OI sau last_real
- Funding sim lấy từ `FundingFeeManager` → map Aerospike (lịch sử settlement API Binance), cộng các kỳ trong (leg đầu, timeUpdate]. Chỉ 6 leg B0 giữ qua ngày chết ⇒ funding giai đoạn ma ≤ |232$| (0,24% ΣPnL) kể cả nếu có kỳ giả. Không có leg vào sau ngày chết ⇒ sim không đọc funding/pred ma cho quyết định vào.
- OI: chỉ vào qua feature selector (0 dòng ma). Gate/market.bin: xem rủi ro mở L0.2.

## L5 — Chấm lại nền ở CÙNG cost 0,11% bằng thước MTM

Cửa sổ 2021-07-01..2025-12-30 (1644 ngày), vốn 35.000$. maxDD/UW MTM = phút (ticker 1m, `reset_rule_score.run_mtm`, 0 leg thiếu giá). CAGR/Sharpe trên equity ngày (b+unP). Exposure = notional mở/eq (giờ → ngày).

### Bảng chính

| | n | ΣPnL | eq cuối | CAGR | maxDD MTM | Calmar_MTM | Calmar_MTM 2022+ | UW MTM (ngày) | Sharpe | expo TB | β BTC | top-5 episode | notional TB | Σnotional |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| T170 (phí 0,8) | 1089 | 76.070 | 111.070 | 29,27 | −19,96 | 1,47 | 1,49 | 144 | 1,80 | 2,4% | 0,00 | 48,4% | 1.851 | 2,016M |
| **T170c (0,11)** | 1089 | 89.948 | 124.948 | 32,70 | −17,85 | 1,83 | 1,83 | 129 | 2,05 | 2,2% | −0,00 | 44,8% | 1.851 | 2,016M |
| R0 | 1086 | 91.109 | 126.108 | 32,97 | −19,85 | 1,66 | 1,66 | 147 | 2,07 | 2,4% | 0,00 | 46,2% | 1.970 | 2,139M |
| R4 | 2027 | 69.490 | 104.489 | 27,53 | −16,42 | 1,68 | 1,75 | 165 | 2,05 | 2,7% | 0,00 | 46,7% | 930 | 1,885M |
| G2 | 2509 | 96.375 | 131.374 | 34,18 | −17,99 | 1,90 | 1,86 | 129 | 2,23 | 3,7% | 0,01 | 38,5% | 977 | 2,452M |
| **B0** | 2517 | 96.909 | 131.908 | 34,31 | −17,68 | 1,94 | 1,90 | 87 | 2,29 | 3,6% | 0,01 | 36,6% | 997 | 2,509M |

β BTC ≈ 0 (corr B0 0,05; B0 phẳng 61% số ngày) — hệ gần như trung tính BTC ở tần suất ngày. Top-5 episode = 5 cụm ngày đóng lệnh (khe ≤2 ngày) lớn nhất / ΣPnL.

### Theo năm — ROI % (maxDD MTM %)

| | 2021H2 | 2022 (bear) | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|
| T170 (0,8) | 12,2 (−11,0) | 19,6 (−15,4) | 35,0 (−6,2) | 32,1 (−12,2) | 32,7 (−20,0) |
| T170c | 15,1 (−10,7) | **23,1 (−14,8)** | 36,6 (−5,8) | 36,1 (−11,1) | 35,7 (−17,9) |
| R0 | 15,2 (−10,9) | 16,4 (−15,3) | 39,1 (−6,1) | 39,8 (−12,0) | 38,2 (−19,9) |
| R4 | 8,6 (−11,6) | 17,9 (−13,1) | 29,6 (−3,8) | 40,5 (−11,0) | 28,1 (−16,4) |
| G2 | 18,4 (−11,7) | 10,3 (−18,0) | 51,7 (−4,3) | 43,5 (−11,0) | 32,1 (−15,5) |
| B0 | 18,5 (−11,6) | **11,1 (−17,7)** | 54,1 (−4,3) | 43,4 (−10,7) | 29,5 (−15,6) |

B0 thắng nhờ 2023 (+54% vs +37%) và 2024; thua 2022 và 2025 (bear/chop). Tức lợi thế B0 tập trung ở các năm alt-pump, đúng loại năm mà mọi cấu hình đều đẹp.

### Paired bootstrap vs B0 (return NGÀY, circular block 10 ngày, NREP 2000, seed 20260905; X − B0; CI 95% raw / infl k=3 ×1,4823)

c chốt TRƯỚC khi so (= expo TB X / expo TB B0, `c_locked.json`): T170 0,671; T170c 0,628; R0 0,675; R4 0,764; G2 1,031.

| X | biến thể | ΔCalmar (eq ngày) | ΔCAGR pp | ΔmaxDD pp | ΔSharpe | ΔCalmar_MTM điểm |
|---|---|---|---|---|---|---|
| T170c | raw | −0,46 [−2,15; +6,61] / [−2,96; +10,02] | −1,61 [−10,20; +8,51] / [−14,35; +13,40] | −1,01 [−2,84; +7,49] / [−3,73; +11,59] | −0,24 [−0,76; +0,56] | −0,11 |
| T170c | B0×0,628 | −0,29 [−1,72; +6,88] / [−2,40; +10,33] | **+12,09 [+4,45; +22,40] / [+0,76; +27,37]** | −4,70 [−6,85; +3,14] / [−7,89; +6,92] | −0,24 | −0,01 |
| R0 | raw | −0,45 [−2,27; +4,24] / [−3,15; +6,50] | −1,34 [−9,56; +8,26] / [−13,53; +12,90] | −1,07 [−3,25; +6,34] | −0,22 [−0,74; +0,48] | −0,28 |
| R0 | B0×0,675 | −0,30 [−1,91; +4,46] | +10,72 [+2,86; +20,87] / [−0,93; +25,76] | −4,30 [−6,79; +2,35] | −0,22 | −0,20 |
| R4 | raw | −0,67 [−2,67; +4,51] / [−3,64; +7,01] | −6,78 [−13,84; +2,25] / [−17,25; +6,60] | +0,03 [−2,35; +7,42] | −0,24 [−0,78; +0,43] | −0,26 |
| R4 | B0×0,764 | −0,56 [−2,38; +4,65] | +2,05 [−4,29; +9,80] | −2,31 [−4,91; +4,41] | −0,24 | −0,20 |
| G2 | raw | −0,18 [−0,45; +0,17] / [−0,58; +0,34] | −0,12 [−1,69; +1,67] | −0,53 [−0,90; +0,25] | −0,06 [−0,17; +0,02] | −0,04 |
| T170 (0,8) | raw | −0,95 [−3,10; +4,60] | −5,04 [−13,54; +4,55] | −1,83 [−4,27; +6,81] | −0,50 [−1,03; +0,24] | −0,47 |

- Mọi ΔCalmar/ΔSharpe/ΔmaxDD chứa 0. CI ΔCalmar lệch và rất rộng (maxDD resample không ổn định) ⇒ Calmar paired gần như **không có sức phân biệt** ở n ngày này; không thể dùng làm luật chọn duy nhất.
- Duy nhất ngoài CI (cả infl): T170c vs B0×0,628 ΔCAGR +12,1 ⇒ trên mỗi đơn vị exposure, T170c sinh lời nhiều hơn; nhưng Calmar không đổi (B0 dùng thêm exposure mà DD không tăng tương ứng). Ràng buộc thật là DD ⇒ điểm này không đổi kết luận. (Exposure T170 tính bằng notional CUỐI trên cả [ts,te] ⇒ bị thổi phồng trước khi DCA khớp ⇒ c thật nhỏ hơn ⇒ Δ cùng-exposure còn lớn hơn.)

### Luật "n primary" (R4 vs R0, cùng thước)

| | ΔCalmar | ΔCAGR pp | ΔmaxDD pp | ΔSharpe |
|---|---|---|---|---|
| R4 − R0 raw | −0,22 [−2,74; +1,31] | **−5,44 [−11,75; −0,37]** (infl [−14,8; +2,1]) | +1,10 [−1,41; +2,58] | −0,02 [−0,42; +0,25] |
| R4 − R0×1,133 | −0,27 [−2,93; +1,22] | **−10,37 [−18,46; −4,20]** (infl [−22,4; −1,2]) | +2,55 [−0,55; +4,08] | −0,02 |
| T170c − R0 raw | −0,01 [−0,16; +2,70] | −0,27 [−2,90; +3,09] | +0,06 | −0,01 |

R4 đổi n×1,87 lấy −5,4pp CAGR (ngoài CI raw), không cải thiện Calmar/Sharpe/DD/UW (UW còn tệ hơn: 165 vs 147 ngày). "n nhiều hơn" chỉ tăng power thống kê cho phép so, nó không phải lợi ích kinh tế. Luật này đã chọn sai ở bước T170→R4.

### Độ nhạy slippage (ước lượng tuyến tính trên printDone; T170 dùng T170c)

ΣPnL − Σnotional × s (s = slippage/vòng, % notional):

| | Σnotional | s=0 | s=0,3% | s=0,7% | s=1,4% | s làm ΣPnL=0 | s* để X vượt B0 |
|---|---|---|---|---|---|---|---|
| T170c | 2,016M | 89.948 | 83.900 | 75.836 | 61.724 | 4,46% | **1,41%** |
| R0 | 2,139M | 91.109 | 84.691 | 76.133 | 61.157 | 4,26% | 1,57% |
| R4 | 1,885M | 69.490 | 63.834 | 56.294 | 43.098 | 3,69% | 4,39% |
| G2 | 2,452M | 96.375 | 89.018 | 79.210 | 62.045 | 3,93% | 0,94% |
| B0 | 2,509M | 96.909 | 89.382 | 79.345 | 61.781 | 3,86% | — |

- n B0/T170 = 2,31× nhưng **Σnotional chỉ 1,245×** (B0 chia nhỏ lệnh: TB $997 vs $1.851). Slippage tỉ lệ notional ⇒ T170c chỉ vượt B0 khi s > 1,41%/vòng (gấp ~12 lần phí; ngang crash-penalty P1 đo được 0,69–1,5%). Ở s=1,4% hai bên gần hoà (61,7k vs 61,8k).
- Mô hình phí CỐ ĐỊNH/lệnh: T170c vượt B0 khi > $4,87/lệnh (0,49% notional TB B0); R0: > $4,05.
- Mô hình impact √size (s_i = k·√(notional_i/1000)): Σnotional^1,5 của T170c (2,99M) > B0 (2,77M) ⇒ **B0 thắng với mọi k** (lệnh T170 to gấp 1,86×).
- Crash-penalty (leg vào trên nến −1%: 0,69% / 1,5%): B0 −8,5% / −18,4% ΣPnL; T170c −8,0% / −17,4% — gần như nhau.
- ⇒ Lập luận "B0 nhiều lệnh nên dễ tổn thương slippage" chỉ đúng khi chi phí cố định/lệnh ≳ $5; với chi phí tỉ lệ hoặc impact theo size thì ngược lại.

## Kết luận

1. **Luật "n primary": không hợp lý.** Nó chọn R4 (CAGR −5,4pp, CI raw ngoài 0) mà không mua được Calmar/Sharpe/UW nào. n chỉ nên là điều kiện power (n tối thiểu để CI đủ hẹp), không phải mục tiêu. Đề xuất thay bằng: primary = ΔCAGR ghép cặp ở cùng exposure + maxDD/UW MTM làm ràng buộc; ΔCalmar paired chỉ báo cáo (CI quá rộng để quyết).
2. **B0 vs T170-ở-0,11: hoà về thống kê.** Không có Δ nào ngoài CI. Điểm nghiêng B0 (Calmar_MTM +0,11, UW ngắn hơn 42 ngày, top-5 episode thấp hơn 8pp, Sharpe +0,24), nghiêng T170c ở 2022 bear (+12pp ROI, DD nông hơn 2,9pp) và hiệu suất trên exposure. Phần chênh "hiển thị" T170→B0 trước đây chủ yếu do đổi cost model (T170 cũ 0,8% phí: ΔPnL do phí = 13.878$ = 67% khoảng cách ΣPnL T170→B0).
3. **B0 có đáng là nền lên 242 không?** Có — nhưng với lý do đúng: không cấu hình nào hơn nó có ý nghĩa, lệnh nhỏ hơn (impact thấp hơn, ít tập trung episode hơn), UW ngắn hơn. KHÔNG được ghi là "B0 > T170". Rủi ro cần theo dõi live: bear-regime (2022 B0 thấp nhất 5 cấu hình) và chi phí cố định/lệnh (nếu > ~$5/lệnh thì lợi thế mất).
4. **BASELINE_REVERT: không đề xuất** — T170/T170c/R0/R4 không hơn B0 ở Calmar cùng exposure ngoài CI (ΔCalmar cùng-expo T170c −0,29, R4 −0,56, CI chứa 0).
5. **L0: không thay đổi kết luận nào ở trên.** Tác động ma lên PnL sim ≤ 0,8% ΣPnL (B0). Mở: audit đường sinh `market.bin`/feature gate toàn-universe từ ticker có nến ma (pha loãng tới 19%/ngày 2025).

## Hạn chế
- T170c là hiệu chỉnh phí tuyến tính (không compound) ⇒ thiên vị nhẹ có lợi cho B0; R0 (chạy thật 0,11, DCA khác) kiểm chéo cho CAGR gần bằng.
- Bootstrap Calmar/maxDD trên equity NGÀY (b+unP); Calmar_MTM chỉ có điểm (maxDD phút không bootstrap được rẻ). Không dùng ΔCalmar ledger-closed.
- Slippage là ước lượng tuyến tính tĩnh (không mô phỏng lại lệnh bị bỏ/khớp khác).
- Funding post-delist chưa đọc trực tiếp từ Aerospike: chỉ có cận trên.

## Tái lập
```
cd research/analysis
python3 long_ghost_baseline.py scan,ghost,mtm --workers 3     # ~28 + 12 phut, RAM < 4G
python3 long_ghost_baseline.py label,pb,l5,extra
```
Output trung gian: `~/claude_master/1003/lgb/{scan,ghost,mtm,label,pb,l5,extra,c_locked,feat_t1c}.json`.
