# AUDIT_CHAIN_AND_N_20261003 — B0 (G2+FLAT3) từng mắt xích + mọi đường TĂNG SỐ LỆNH

- **Ngày:** 2026-10-03 (GMT+7). **Vai:** quant auditor, CHỈ ĐỌC + 0-sim nhẹ. 0 sim Java, 0 Kaggle, 0 sửa `.java`, 0 chạm 242/shadow, DEV ≤ 2025-12-31.
- **Script:** `research/analysis/chain_n_audit.py` (stage `ticks,pairs,gatelog,proxy,dip,gaterep`; 1 lần chạy 89 s, RSS 1,39 GB, `flock oracle_heavy.lock`, `nice 10`). **JSON:** `docs/audit/AUDIT_CHAIN_AND_N_20261003.json` (md5 `ab3e2dcb…`; chạy lại cho cùng số — đã chạy 2 lần, các dòng in trùng khớp).
- **Nguồn (assert md5):** B0 = `~/kaggle_sim/out/de-p1` printDone `650c386f…` (n 2517); `p15_dev.csv` (2,50 M phút); bins S1 `predwf_map_s1a2_x1` + `s3moc21` (18 file); `CLOSES_1H_v2.bin` `58f56069…`; printDone các run đã có: `de-p2/p3/p5` (`6802c08e/5e60998e/eb752ffb`), `gdv2-g0/g1/g2` (`06fd6e9a/9169997a/853aaa08`), `gd92-r4-d1/d2` (`f76bc27f/9d53df1d`), `kg0-g170/g140/g100` (`99e42b75/…/fa0dc7eb`); dòng `[GATE-RATIO]` trong `sim.out`.
- **Kiểm đầu vào (bắt buộc, PASS):** `pred15m` trong printDone == `p15_dev.csv` tại phút vào **2223/2223** (|Δ| trung vị 4e-10; lệch ±1' thì sai) và `symbolPred` == score `1−p0` trong bins (floorEntry 15') **2223/2223** (Δ 0). ⇒ đầu vào gate tái lập được chính xác; cái KHÔNG tái lập được là **khoá symbol** (xem §3).
- **Nhãn:** [ĐO] = số từ artifact/script; [SUY LUẬN] = diễn giải; [ƯỚC] = ước lượng thô, không phải sim. Mọi lát ở đây là hậu kiểm trên DEV đã dùng 30+ lần ⇒ chỉ để định cỡ/sinh giả thuyết, không để chọn tham số.

## KẾT LUẬN (rủi ro trước)

1. **n của B0 = số ngày-có-lệnh × ~16 lệnh/ngày.** [ĐO] 2517 lệnh rơi vào **152 ngày / 1644 (9,2 %)**, 686 phút-vào, 234 đợt (gom ≤ 60'); trung vị **16 lệnh/ngày-có-lệnh** (p90 30, max 200). Vốn **rảnh 66 % thời gian** (≥ 1 lệnh mở chỉ 34,4 % số phút). ~2000 lệnh/năm ở 16 lệnh/ngày ⇒ cần **~125 ngày-có-lệnh/năm** (hiện ~34). Không lever cấu hình nào đã đo đưa số ngày lên quá ~54/năm.
2. **G2 là gate QUOTA, không phải ngưỡng tín hiệu.** [ĐO] pass = ρ × luồng ứng viên với ρ ≈ 6,2–6,3e-5 **không đổi** khi K 16→24→32 (seen/phút 14,9→22,2→29,4 ⇒ pass 2223→3231→4414). `SIM_GATE_DYN_SCALE` **triệt tiêu** (r = p15/(factor·gs), q cùng đơn vị) — chỉ còn tác dụng trong 7 ngày warm-up. ⇒ "tăng K" và "hạ pct" là **cùng một lever** (nới quota); và "gate binding, không phải slot" là hệ quả thiết kế, không phải phát hiện về thị trường.
3. **Nới quota cho n tăng DƯỚI tuyến tính, lệnh thêm dồn vào ngày đã có lệnh và kém hơn.** [ĐO, tái lập gate cấp ứng viên, §3] pct ×2/×3/×5 quota ⇒ lệnh **+31 % / +48 % / +76 %**, ngày-có-lệnh 141→178/206/241; **85–89 % lệnh thêm rơi vào ngày B0 đã có lệnh**. [ĐO, run có sẵn] lệnh "chỉ-arm" khi mở rộng có ROI/lệnh **1,5–3,4 %** vs B0 4,48 %; K24/K32: **99 % lệnh thêm cùng ngày B0** (thêm coin vào cùng cú sập), 2022 âm ở K32 (−5,2 %/lệnh). Trần cấu hình đo được ≈ **×1,8 n (~1000/năm)**, không tới ~2000/năm.
4. **Không có "nguồn sự kiện thứ hai" nào đã đo mà dương:** OFI V3 (293 sự kiện mới/4 năm, net −1,94 %), BIG_DOWN nới ngưỡng (−0,025: +130 leg, ΣPnL leg BD 16,3k→11,4k ⇒ lệnh biên **âm**), breadth 9 vòng NULL, coin-dip −8 %/1h [ĐO mới, thô]: **7 266 sự kiện (~1 600/năm, 856 ngày)** nhưng excess 72h vs EW **+0,02 % [−0,73; +0,83]** — số lượng có, edge vô điều kiện = 0 (≈ beta hồi, khớp R3: hồi +4,5 %/3d nhưng excess ≈ 0).
5. **Lỗ hổng CHẶN-TIỀN-THẬT lớn nhất không nằm ở n:** (a) live W90 đang **ramp từ 7 ngày** (buffer 242 bắt đầu 2026-09-30, arm ~10-07, đủ 90 ngày ~12-29) ⇒ 3 tháng đầu gate live là **cửa sổ ngắn ≈ G1/W30** — G1 trên DEV: n +27 %, lệnh thêm 1,47 %/lệnh [−0,27; +2,95], 2022 âm, UW 473 ngày; (b) p15 live ≠ p15 DEV (mở từ AUDIT_G2FLAT3 F1); (c) giá khớp phút sập (42 % ΣPnL từ lệnh đóng trong giờ vào; crash-pen +0,69 %/chân ⇒ −9,8 % equity, T4 sát nút).
6. ⇒ **Xếp hạng đường tăng n (§5):** không đường nào vừa ×3–4 n vừa giữ chất lượng trên bằng chứng hiện có. Đường "rẻ" nhất để có thêm ~+40–50 % n là nới quota (pct ≈ 0,99985 hoặc K24) với giá đã đo ≈ −0,3 Calmar; đạt ~2000/năm **chỉ có thể** bằng một nguồn sự kiện độc lập (ngày mới) có edge sau phí — hiện **0 ứng viên đã qua tầng tiền**. GEOM không bù được về mặt đo lường (ΔCalmar +0,83 CI [−0,05; +1,78] — chưa qua; và nó cải thiện ROI/lệnh, không tạo ngày mới).

## 1. BẢN ĐỒ MẮT XÍCH

Mức: **CHẶN** = CHẶN-TIỀN-THẬT (có thể làm kỳ vọng live sai dấu/sai cỡ trước khi bỏ tiền) · **RR** = RỦI-RO-KỲ-VỌNG (lệch cỡ ~10–30 %) · **NHỎ**.

| # | mắt xích | cơ chế hiện tại (code/số) | giả định ngầm | bằng chứng đã có | lỗ hổng / rủi ro (DEV & live) — mức | đã thử / verdict | còn chưa thử |
|---|---|---|---|---|---|---|---|
| 1 | dữ liệu vào | kline 1m Aerospike, ticker bundle file; OI/funding (funding mark bật, Σ −1,42k = 1,5 % ΣPnL); universe = mọi USDT-M có ticker (863 mapper), lineage v2 | nến 1m = giá khớp được; universe không thiên vị sống sót | GHOST: 0 lệnh sau `last_real`; 6 leg giữ qua ngày chết −688 $ (0,7 %); BIG_DOWN = TB 100 coin giảm mạnh nhất **1 nến** | **RR** nến ma vol=0 trong bundle tăng 0,97 %→8,0 % symbol-phút (2022→2025), tới 19 % universe/ngày — **chưa audit** ảnh hưởng tới `rateDownAvg` (BIG_DOWN) và feature toàn-universe (gate33). **NHỎ** ghost leg. | GHOST_BASELINE (OK), DATA_AUDIT_20261003 | đo `rateDownAvg` có/không nến vol=0 (0-sim, 1 script) |
| 2 | feature market-level → p15 | XGB 33 feature → `predReturn15M` (p15) mỗi phút; **[ĐO]** p15 printDone == `p15_dev` 2223/2223 | p15 DEV = p15 live; model trễ 2 quý (fold cut) | AUDIT_G2FLAT3 F1 (p15 live ≠ DEV mở); readiness: đổi model r_new/r_old trung vị 1,000 | **CHẶN** p15 live ≠ DEV chưa đóng (B0_LIVEMODEL chưa chạy); `ai_pred_1m` 242 bị trộn p15 242/shadow (|Δ| ≤ 0,17 pp) ⇒ mọi phân tích "p15 live" nhiễm | FEAT_CUT/ADD_V1 (FAIL), GATE_RECAL | B0_LIVEMODEL (đã nháp) |
| 3 | gate GDV2 | pass ⇔ r = p15/max(0,268; 8,584·sp) ≥ q_t; q_t = phân vị **0,99995083** của r mọi ứng viên **chưa giữ** trong [t−90d, t), tính lại mỗi giờ; warm-up 7d fallback 0,008×factor×1,55; **gs triệt tiêu** | "p15 = dự báo market 15'"; ngưỡng tương đối = ổn định qua regime | GDV2_EVEN: pct = 1−ρ(R4); ρ thực 6,3e-5 (> 4,9e-5 vì q trễ trong episode); **[ĐO] proxy chỉ-p15: recall ngày 30 %** ⇒ gate KHÔNG phải market-level thuần: **S1 score là nửa còn lại của gate** (factor) | **CHẶN** live W90 ramp 7→90 ngày (≈ W30 trong ~3 tháng đầu; G1 = W30 kém rõ). **RR** q_t phụ thuộc **sổ lệnh**: tái lập KHÔNG trừ coin đang giữ ⇒ chỉ 43 ngày-mở / 4,5 năm (vs 141 khi trừ) ⇒ khác biệt nhỏ trong cách đếm ứng viên live (seed không trừ held-symbol, tick thiếu) đổi mạnh n. **RR** "p15 dự báo gì": p15 là hồi quy return 15' cấp thị trường; ở B0 nó được dùng như **đo độ quá bán** (B0 vào ở top 0,1 % p15 [p90 0,5 %] của 90 ngày) | GATESCALE×3, GDV2 (→G2), GD92, BREADTH×9, REGIME | đo q_t live vs sim cùng giờ sau khi buffer đủ 90d; seed live có trừ held-symbol |
| 4 | selector S1 + G015 + map | XGBRanker rel5 g1lite, KEEP9, top-16 score thấp nhất (score = 1−P(win 4h)), floorEntry 15'→phút; G015 chỉ vào qua factor | thứ tự top-16 có giá trị; G015 nối PnL | SELECTOR_ABLATION_R50: xáo trong top-50 mất 60–79 % khoảng cách (thứ tự CÓ giá trị); retrain-noise: B0 CAGR bình thường, Calmar may mắn (+2,8 sd); GEOM/FIRSTHIT/OFI NO-GO | **RR** Calmar 3,35 của B0 là realization may mắn (mốc recipe ~2,9) ⇒ kỳ vọng live thấp hơn; **NHỎ** live dùng fold cut2025 (sim 2025Q4 dùng cut khác) | 6+ vòng feature/nhãn: đóng hướng feature S1 | không đề xuất |
| 5 | BIG_DOWN | `rateDownAvg` (TB 100 coin giảm mạnh nhất trong **1 nến 1'**) < −3,157 % ⇒ mua **2** coin top S1 chưa giữ, **bỏ qua gate AI**; [ĐO] 248 lệnh, 124 phút, 54 ngày, 4,82 %/lệnh | ngưỡng cố định ổn qua regime | BD_THRESHOLD_FRAGILITY (T170): −0,025 ⇒ 378 leg nhưng ΣPnL BD 16,3k→11,4k; BD_SIZE_ADAPT ≈ 0; SEL_BIGDOWN NULL | **RR** 1 nến 1' + 2 lệnh/tín hiệu ⇒ nhạy giá khớp phút sập (crash-pen); BD đi qua cùng nến ma (#1) | 5 vòng BD: NULL/BLOCKED | không |
| 6 | sizing | margin 1 leg = equity×0,015×6/4×throttle (2,25 %×throttle, median 1,42 % eq); U_MAX 0,60 (max 51 %); CONC 15 % (0 chặn); DCA grid 4 leg **không bao giờ khớp leg 2+** | compound theo equity | P6 (F 0,010) = cùng n, CAGR −7,8 pp; DOUBLE_ENTRIES: size không tạo n ở K16 | **NHỎ** grid DCA nhiều bậc không bắn (AUDIT_LONG_LEVERS: `lastentry ≡ entry` 2517/2517); 46 leg `DCA_LEVEL1` (8 ngày, +40,7 %/leg, 8,5 % ΣPnL) là đuôi hiếm, không phải nguồn n. Size nhỏ **không tăng n** (n do quota gate) | SIZE_COUNT, DCA×7, VOLTARGET | — |
| 7 | entry execution | vào giá close 1m của phút tín hiệu; phí 0,1116 %/vòng; slippage 6,7e-5 | khớp được tại close phút sập | 42 % ΣPnL từ lệnh đóng trong giờ vào; LATENCY_FILL median 7 s | **CHẶN** crash-pen +0,69 %/chân ⇒ eq −9,8 %, Calmar 1,758 (T4 sát), ×2 ⇒ FAIL T4; n=27 điểm ước, CI [−0,19; +1,50] | FLAT3_CRASHPEN, LIMIT_ENTRY (NULL), MAKER | đo slippage thật từ shadow (forward) |
| 8 | exit FLAT3 | arm +7 %, TS giveback 1,0 / max gap 3 %; time-stop 168h; SL cứng ban đầu | trailing đủ | thước ghép cặp: FLAT3 ≈ T0/LAD/PROP (±5 %); EXIT_TIME_B0 NO-GO (+1,8k CI [−8,8; +13,9]) | **NHỎ** 339 time-stop ăn −55,9k (36 % lãi gộp) — đã thử cắt 72h: đổi lỗ chậm lấy thắng muộn | TRAIL×2, EXIT_TIME, HOLDTODIE | đóng tầng exit |
| 9 | risk/portfolio | 55 lệnh đồng thời max, exposure max 51 %, TB 3,7 % | episode độc lập đủ | top-5 episode 36,6 %, top-10 52,3 %; CI ΣPnL [62,7k; 134,7k]; **[ĐO]** top-10 % ngày (15 ngày) = 31,6 % lệnh, 33,9 % ΣPnL | **RR** n hiệu dụng ≈ 123 episode, không phải 2517 lệnh ⇒ mọi "tăng n" trong cùng episode **không** tăng số cược độc lập | DD_THROTTLE, HEDGE, VOL_TARGET | — |
| 10 | vòng live | nhịp 1' (`LIVE_ENTRY_GRID_MIN=1`), buffer gate persist + seed; JVM restart 4h; model gate/selector cut 2025 | live = sim | PARITY_242_VS_G2FLAT3; DEPLOY_SHADOW_2A (seed kẹt, ai_pred_1m trộn) | **CHẶN** (= #3) ramp W; **RR** seed không trừ held-symbol (`LiveGateRollingRatio.seedHistory` tự khai); **RR** model trễ 2 quý trên forward | 2a/2a-bis shadow | so `[GATE-RATIO] q_t` 242 vs sim-replay cùng chuỗi r |
| 11 | đánh giá / §9 | 4 tầng T1–T4; ghép cặp size-neutral cho exit; block-72h | DEV đủ lực cho tầng gate | power wall: 152 ngày, 123 episode; MDE80 CAGR 2,3–3,3 pp; retrain-noise sd 0,83 pp CAGR, Calmar ±0,4 | **RR** T4 "Calmar_MTM ≥ 0,9×B0" neo vào một realization **thuận lợi về DD** (retrain cùng recipe: maxDD MTM 2022 −19,1/−19,5 % vs B0 −17,7 %; Calmar ngày 2,78–3,03 vs 3,35) ⇒ T4 thiên về REJECT biến thể có cùng kỳ vọng; **RR** n là MỤC TIÊU (§9.3) nhưng thước n không phân biệt lệnh cùng episode | RULERS, RESET_RULE | đo n theo **ngày/đợt độc lập** cạnh n lệnh |

## 2. NHỊP VÀO LỆNH B0 (0-sim, printDone `650c386f`) [ĐO]

| tập | n | phút-vào | ngày | đợt (≤60') | lệnh/phút TB | lệnh/ngày-có-lệnh p50/p90/max | khoảng cách phút-vào (h) p50/p75/p90/p99/max | khoảng cách đợt (h) p50/p90 | khoảng cách ngày-có-lệnh (d) p50/p90/max | ROI/lệnh |
|---|---|---|---|---|---|---|---|---|---|---|
| tất cả | 2517 | 686 | **152** | 234 | 3,7 | **16** / 30 / 200 | 0,22 / 4,2 / **162** / 781 / 1691 | 37,8 / 512 | **6** / 25 / **70** | 4,48 % |
| selector | 2223 | 562 | 138 | 215 | 4,0 | 16 / 29 / 126 | 0,42 / 6,1 / 214 / 1041 / 1691 | 29,1 / 514 | 7 / 29 / 70 | 3,69 % |
| BIG_DOWN | 248 | 124 | 54 | 57 | 2,0 | 2 / 8 / 56 | 0,18 / 383 / 925 / — / 4618 | 442 / 1256 | 19 / 54 / 192 | 4,82 % |
| DCA_LEVEL1 | 46 | 32 | 8 | 17 | 1,4 | 2,5 / 12 / 18 | — | — | — | 40,7 % |

- Theo năm (tất cả): ngày-có-lệnh **2021H2 20 · 2022 26 · 2023 42 · 2024 40 · 2025 24**; lệnh/ngày-có-lệnh 21,7 / 16,3 / 12,6 / 15,0 / 22,3.
- ≥ 1 lệnh mở: **34,4 % số phút**, 38,9 % số ngày ⇒ vốn rảnh ~2/3 thời gian (exposure TB 3,7 %).
- Top-10 % ngày theo số lệnh (15 ngày): 31,6 % lệnh, 33,9 % ΣPnL. Độ đông trong cùng phút: 1 lệnh/phút 5,5 %/lệnh · 8–15 lệnh/phút 3,6 % (SL 16 %) · >15: 5,3 % — không đơn điệu (không có lever "cắt phút đông").
- **Đọc:** phân phối khoảng cách lưỡng cực — trong đợt các phút-vào cách nhau vài phút–vài giờ, giữa đợt trung vị ~1,5–8 ngày, p90 ~7–21 ngày, dài nhất 70 ngày. n ≈ (ngày-có-lệnh ≈ 34/năm) × (~16 lệnh/ngày).

## 3. GATE: tái lập cấp ứng viên + "mở gate gấp 3 thì lệnh thêm rơi vào ngày nào" [ĐO, 0-sim]

**Cách làm (stage `gaterep`):** r = p15/max(0,26787; sp/0,15×1,2876) cho top-16 score mỗi phút (floorEntry 15', đúng `forwardFillToGrid`); **loại coin đang giữ trong B0** (mọi level, (start, end)); q_t = phân vị pct của r trong [h−90d, h) tính lại mỗi giờ (lõi y hệt `GateRatioBuffer`), warm-up 7d fallback r ≥ 0,0124; pass ⇒ "vào" và khoá coin **10h** (median giữ lệnh selector B0) để không đếm lặp. pct = 1 − m·ρ, ρ = 4,9171e-5, m ∈ {1,2,3,5}.
**Giới hạn:** khoá dùng sổ lệnh B0 (biến thể nới gate có sổ dày hơn ⇒ n thật có thể thấp hơn nữa); khoá tổng hợp 10h < thời gian giữ thật của lệnh lỗ (tới 168h) ⇒ n ước **lạc quan**; bỏ BIG_DOWN/DCA (294 lệnh, không qua gate).
**Kiểm tái lập ở m=1:** 1916 lệnh vs 2223 thật (86 %), trùng (phút, coin) **80,3 %**, trùng ngày **99,3 %** ⇒ đủ để định cỡ; **không** dùng cho PnL.
**Đối chứng phương pháp (stage `proxy`, chỉ-p15 cấp phút, không S1, không khoá):** recall ngày 30 % (m=1) ⇒ **p15 một mình không mô tả được gate**; tái lập không trừ coin đang giữ: chỉ 43 ngày-mở (§1 #3).

| quota | pct | lệnh (tái lập) | ×m=1 | ngày-mở | tuần-mở / 234 | ngày theo năm 21H2/22/23/24/25 | lệnh thêm vs m=1 | % lệnh thêm rơi vào **ngày B0 đã có lệnh** | ngày MỚI (không phải ngày B0) | khoảng cách phút-pass (h) p50/p75/p90/max | khoảng cách đợt (h) p50/p90 | lệnh/ngày-mở p50/p90 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ×1 (= B0) | 0,99995083 | 1 916 | 1,00 | 141 | 93 | 20/25/36/36/24 | — | — | — | 1,5 / 58 / 334 / 1691 | 40,7 / 515 | 15 / 24 |
| ×2 | 0,99990166 | 2 511 | **1,31** | 178 | 107 | 24/31/46/46/31 | 1 302 | **89,4 %** | 35 (4/7/8/8/8) | 1,0 / 42 / 250 / 1602 | 40,8 / 398 | 15,5 / 24 |
| ×3 | 0,99985249 | 2 845 | **1,48** | 206 | 116 | 25/35/51/55/40 | 1 871 | **85,0 %** | 63 (5/11/13/17/17) | 1,0 / 35 / 185 / 1443 | 34,7 / 369 | 15 / 24 |
| ×5 | 0,99975415 | 3 365 | **1,76** | 241 | 130 | 33/41/59/62/46 | 2 627 | **78,8 %** | 94 (13/16/18/24/23) | 1,0 / 27 / 162 / 1192 | 28,2 / 302 | 15 / 26 |

**Đọc:** (i) nới quota ×3 ⇒ lệnh selector chỉ **×1,48** (≈ 2 223×1,48 + 294 ≈ **3 600 lệnh / 4,5 năm ≈ 800/năm** [ƯỚC]); ×5 ⇒ ~930/năm. (ii) **85 % lệnh thêm ở ×3 rơi vào ngày B0 đã giao dịch** — tức thêm coin vào cùng cú sập (cùng episode), không phải cơ hội độc lập mới; ngày mới chỉ +63 (~14/năm). (iii) Lệnh/ngày-mở giữ ~15 ở mọi mức ⇒ n tăng chủ yếu qua thêm ngày, nhưng thêm rất chậm. (iv) Khớp hướng với run thật: K24 (cũng là nới quota, §4) 99 % lệnh thêm cùng ngày B0; GD92-D2/scale 1,00 (nới mạnh hơn, đổi cả ngưỡng tuyệt đối) mới có 33–42 % lệnh thêm ở ngày mới.

## 4. "LỆNH THÊM" TRÊN CÁC RUN ĐÃ CÓ — chất lượng và rơi vào ngày nào [ĐO, stage `pairs`]

Khớp `sym|start|level` (#thứ tự trùng). "Chỉ-arm" = lệnh có ở arm mà không có ở nền (gồm cả lệnh lệch do đường đi đổi ⇒ không phải đúng Δn). ROI = cột `profit` (%/lệnh, size-neutral). CI = bootstrap cụm NGÀY (2000 rep, seed 20260905), **raw, chưa inflate**. Hai dòng `kg0-*` chạy **phí LEGACY 0,8 %/vòng** ⇒ chỉ so nội bộ.

| nền → arm | n nền→arm | chỉ-arm | ROI chỉ-arm [CI ngày] | SL % chỉ-arm | ROI nền | % chỉ-arm ở ngày nền đã có lệnh | ngày mới | ROI chỉ-arm: ngày-cũ / ngày-mới | ΣPnL chỉ-arm / chỉ-nền (k$) |
|---|---|---|---|---|---|---|---|---|---|
| B0 → K24 (P2) | 2517→3526 | 1663 | **3,43 [1,44; 4,82]** | 17,1 | 4,48 | **99,0 %** | 12 | 3,47 / −0,03 (n 17) | +34,0 / +17,9 |
| B0 → K32 (P3) | 2517→4092 | 2638 | 2,57 [0,62; 4,05]; 2022 **−5,20** | 19,6 | 4,48 | 99,1 % | 10 | 2,56 / 3,15 (n 24) | +32,2 / +31,3 |
| B0 → K32 F0,0075 (P5) | 2517→4604 | 3055 | 3,06 [1,49; 4,25] | 18,7 | 4,48 | 98,5 % | 20 | 3,04 / 3,99 (n 47) | +32,3 / +30,8 |
| G2 → G1 (W90→W30) | 2509→3199 | 1917 | **1,47 [−0,27; 2,95]**; 2022 −1,51 | 23,1 | 4,46 | 69,6 % | 70 | 1,11 / 2,30 | +24,4 / +42,5 |
| R4 → G2 | 2027→2509 | 1335 | 3,74 [2,17; 5,00] | 15,9 | 4,50 | 77,5 % | 33 | 3,49 / **4,60** | +40,2 / +19,6 |
| R4 → D1 (q0,92) | 2027→2141 | 756 | 4,32 [2,77; 5,62] | 14,4 | 4,50 | 88,8 % | 11 | 4,18 / 5,43 | +27,4 / +21,3 |
| R4 → D2 (x1,00+q0,92) | 2027→4287 | 3644 | 2,44 [1,53; 3,37] | 19,6 | 4,50 | 67,2 % | **136** | **1,80** / **3,77 [2,64; 4,80]** | +74,5 / +47,1 |
| kg0 1,70 → 1,40 (legacy) | 1085→1411 | 760 | 3,32 [1,99; 4,57] | 13,3 | 5,15 | 83,0 % | 39 | 3,68 / 1,61 | +31,4 / +28,5 |
| kg0 1,70 → 1,00 (legacy) | 1085→2549 | 2202 | 2,46 [1,57; 3,36] | 16,2 | 5,15 | 58,2 % | 158 | 2,88 / 1,87 | +50,6 / +40,4 |

**Đọc [SUY LUẬN, mô tả]:** (i) mọi lệnh thêm có ROI dương nhưng **thấp hơn nền 1–3 pp/lệnh** và SL% cao hơn 2–9 pp — đúng "n tăng, chất lượng/lệnh giảm"; (ii) K tăng ⇒ lệnh thêm **gần như 100 % cùng ngày** (bench sâu hơn trong cùng cú sập) ⇒ không thêm cược độc lập, tăng tập trung (conc 4,09→6,48 % ở K24), Calmar 1,94→1,67; (iii) nới ngưỡng tuyệt đối (D2/scale 1,00) mới mở **ngày mới** (+136/+158 ngày ≈ +30–35 ngày/năm), và ở D2 lệnh ngày-mới **không tệ hơn** lệnh ngày-cũ (3,77 vs 1,80) — phần xấu là lệnh dồn thêm vào ngày đã đông; (iv) cửa sổ ngắn (W30) là biến thể xấu nhất (CI chạm 0, 2022 âm) — đúng kịch bản live đang ramp (§1 #3); (v) G2 so với R4 là bước nới **rẻ** nhất đã đo (lệnh thêm 3,74 %, ngày mới 4,60 %).

## 5. ĐƯỜNG TĂNG SỐ LỆNH — xếp hạng (kỳ vọng n × khả năng giữ chất lượng × chi phí)

n/năm = n/4,5 năm DEV. "đã đo" = có run Kaggle; [ƯỚC] = suy từ bảng §3/§4, không sim. Calmar = Calmar_MTM toàn kỳ (B0 1,94).

| hạng | đường | cơ chế | n/năm (B0 ≈ 560) | chất lượng kỳ vọng | phải code | rủi ro | trạng thái / nhận định |
|---|---|---|---|---|---|---|---|
| 1 | **nới quota pct** (0,99995 → 0,99985 ≈ ×3 quota) | hạ ngưỡng phân vị; K giữ 16 | **~800** [ƯỚC: ×1,48 selector + BD/DCA] | [ƯỚC từ K24/W90-tương-đương] ROI lệnh thêm ~3 %, Calmar ~1,6–1,7 (≈ K24) — **chưa đo** | 0 (1 key) | 85 % lệnh thêm cùng ngày ⇒ tăng tập trung episode; T4 (≥ 1,746) gần như chắc FAIL | chưa chạy; tương đương K24 về cơ chế (quota) nhưng giữ bench top-16 ⇒ **có thể** đỡ hơn K24 ở conc — đáng 1 vòng nếu owner chấp nhận Calmar ~1,7 |
| 2 | **K24** (± GEOM) | thêm 8 ứng viên/phút ⇒ quota ×1,45 | **780** (đã đo) | Calmar 1,67, SL +1,7 pp, conc 6,48, 2022 4,6k→2,4k | 0 | FAIL T4 (cần amendment) | đã đo. **GEOM không bù được về đo lường**: GEOM vs CTRL ΔCalmar +0,83 CI [−0,05; +1,78] chưa qua; ΔCalmar(K24) = −0,27 ⇒ "GEOM+K24 ≈ B0" là **phép cộng 2 điểm ước lượng, 1 cái CI chứa 0** — [ƯỚC] không phải bằng chứng |
| 3 | **nới ngưỡng tuyệt đối (D2-kiểu)** | scale 1,00 + rolling q0,92 (nền R4) | **950** (đã đo, TS0,5 exit) | Calmar 1,40, win 82 %, SL 18,7 %, UW 278 | 0 (key có) | DD −24 %; mở **ngày mới** (+30/năm) | đã đo trên nền R4 cũ; trên FLAT3 chưa — đường duy nhất đã đo **thêm ngày độc lập**; lệnh ngày-mới 3,77 % [2,64; 4,80] |
| 4 | K32 + F nhỏ (P5) | quota ×1,9, size ×0,5 | **1 020** (đã đo) | Calmar 1,26, win −2,6 pp (FAIL T3) | 0 | T3 FAIL; 2022 lệnh thêm âm ở K32 | trần cấu hình đã đo = ×1,83 |
| 5 | multi-timeframe gate (p15 + p60) | thêm điều kiện/nguồn pass | **không ước được** | — | model p60 mới + gate | thêm 1 model ⇒ thêm 1 rủi ro parity live | **chưa có run nào**; với quota-gate, thêm điều kiện AND làm **giảm** n; OR (2 quota) ≈ nới quota (hạng 1) + 1 model ⇒ prior thấp |
| 6 | **nguồn entry thứ hai: dip theo coin** (−8 %/1h, cooldown 24h) | trigger cấp coin, độc lập gate market | tiềm năng **~1 600 sự kiện/năm** [ĐO số sự kiện], 47 % ở ngày B0 **không** có lệnh | [ĐO, thô, trước phí] excess 72h vs EW **+0,02 % [−0,73; +0,83]**; idio +0,04 [−1,51; +1,67]; market +0,18 [−0,25; +0,75]; median −1,8 %, p5 −27 % | detector mới + exit + sim | edge vô điều kiện = 0; cần selector mới tại trigger (như R1b) ⇒ 1 chương trình nghiên cứu, không phải 1 vòng | **chỉ đường này có thể chạm ~2000/năm**, nhưng bằng chứng hiện có cho **beta, không edge** (khớp SHORT_V3 R3: hồi +4,5 %/3d, excess ≈ 0) |
| 7 | BIG_DOWN mở rộng | ngưỡng −3,157 % → −2,5 % | +~30/năm leg BD | [ĐO, T170] +130 leg nhưng ΣPnL BD −4,8k (lệnh biên **âm**) | 0 | — | **chết** |
| 8 | OFI V3 | S1 + 2 cột OFI | +~65/năm [ĐO: 293 cặp/4 năm] | net −1,94 %/lệnh; 99,95 % pick trùng S1 | ONNX 47 cột | — | **chết** |
| 9 | breadth-crash 1' / regime | gate theo breadth | — | 9 vòng NULL (power wall) | — | — | **đừng lặp** |
| 10 | tăng universe (spot, listing mới) | thêm coin | ≈ 0 với quota-gate (quota theo luồng ứng viên top-16, không theo số coin) | listing <30 ngày tuổi ở B0 **lãi hơn** (loại = −23,9k) nhưng là lát hậu kiểm | data spot + map | — | [SUY LUẬN] không tăng n trừ khi đổi K/pct |
| — | time-stop ngắn / quay vòng vốn | giải phóng slot | **0** (vốn không binding: NO_BUDGET 0, rảnh 66 % thời gian) | EXIT_TIME_B0 NO-GO | — | — | **không tăng n** |
| — | chia nhỏ size | — | **0** ở K16 (P6 2519 ≈ 2517) | CAGR 34,3→26,5 | — | — | **không tăng n**; chỉ hạ rủi ro/lệnh |
| — | hạ cost giả định | — | **0** | trần lợi ích ≈ tổng phí 2,8k (2,9 % ΣPnL) | — | — | **không tăng n** |

**Cái nào chỉ là beta/nhiễu:** dip theo coin (excess ≈ 0 ⇒ beta hồi thị trường); breadth/regime (power wall); lệnh thêm của K24/K32 cùng ngày (tăng phơi nhiễm episode, không thêm cược độc lập ⇒ về bản chất là **đòn bẩy trong episode**). Thứ duy nhất trong bảng **tạo ngày độc lập mới** với ROI dương đo được là nới ngưỡng tuyệt đối (D2/scale 1,00) — đổi lại DD/UW xấu hơn rõ.
**Khoảng cách tới mục tiêu:** ~2000/năm ≈ 9 000 lệnh/4,5 năm ≈ **3,6× B0**. Tổ hợp mạnh nhất đã đo ×1,83 (P5, FAIL T3); nới quota ×5 [ƯỚC] ×1,76. K và pct là **cùng một lever** (quota, §3) nên chồng chúng không phải cơ chế mới. Đường tái lập khớp xấp xỉ n ∝ quota^0,36 (×2→1,31, ×3→1,48, ×5→1,76) ⇒ ×3,9 lệnh selector cần quota cỡ **×40 (pct ≈ 0,998)** [ƯỚC ngoại suy, ngoài vùng đo] — ở vùng đó gate gần như "luôn mở trong episode" và chất lượng lệnh biên đã đo đi về ~1,5–2,5 %/lệnh trước khi tới đó. **Không có đường cấu hình nào tới ×3,6 trên DEV.**

## 6. TOP LỖ HỔNG (xếp theo mức)

1. **CHẶN — gate live đang ramp cửa sổ 7→90 ngày** (buffer 242 từ 2026-09-30; arm ~10-07; đủ 90d ~12-29). DEV chưa có run "W tăng dần"; gần nhất là G1/W30: lệnh thêm 1,47 %/lệnh [−0,27; +2,95], 2022 âm, UW 473. ⇒ 3 tháng forward đầu **không** so được với B0 W90, và có thể vào nhiều lệnh kém hơn. Việc cần: replay sim với buffer bắt đầu rỗng tại một mốc DEV (đo hiệu ứng ramp) hoặc seed 90d có trừ held-symbol trước khi bỏ tiền.
2. **CHẶN — giá khớp phút sập** (42 % ΣPnL ở lệnh đóng trong giờ vào; +0,69 %/chân ⇒ −9,8 % equity, T4 sát; ×2 ⇒ FAIL). Chưa có số slippage thật nào từ live.
3. **CHẶN — p15 live ≠ p15 DEV** (F1 mở; `ai_pred_1m` 242 trộn nguồn). Gate là phân vị của p15/score ⇒ lệch phân phối p15 đổi trực tiếp n và tập ngày.
4. **RR — q_t phụ thuộc sổ lệnh** (ứng viên đang giữ bị loại khỏi buffer): tái lập không trừ coin đang giữ cho 43 ngày-mở thay vì 141 ⇒ mọi khác biệt sim/live trong tập "ứng viên được đếm" (seed không trừ held-symbol, tick thiếu, restart) khuếch đại thành khác biệt n. Không có test parity nào đo q_t live vs sim-replay cùng chuỗi.
5. **RR — n không phải số cược độc lập:** 2517 lệnh = 152 ngày = 123 episode; mọi lever K/quota thêm 85–99 % lệnh vào ngày đã có ⇒ T4 "n là mục tiêu chính" (§9.3) thưởng cho đòn bẩy trong episode. Đề xuất báo kèm **n_ngày / n_đợt** ở mọi vòng tăng n.
6. **RR — nến ma vol=0** (tới 8 % symbol-phút 2025) chưa audit trên `rateDownAvg`/feature toàn-universe.
7. **RR — B0 là realization thuận lợi về DD** ⇒ ngưỡng T4 0,9×B0 khắt hơn danh nghĩa.

## 7. GIỚI HẠN

- Tái lập gate (§3) dùng sổ lệnh B0 cho khoá và khoá tổng hợp 10h cho lệnh mới ⇒ n ở ×2/×3/×5 là **cận trên thô**; không có PnL. Không mô hình BIG_DOWN/DCA dưới gate mới.
- §4 là so sánh **run có sẵn**, khác nhau cả đường đi (lệnh lệch do vốn/khoá) ⇒ "chỉ-arm" ≠ "lệnh thêm thuần"; CI raw, chưa inflate, chưa trừ lịch sử chọn (DEV đã dùng 30+ lần).
- Dip theo coin: close 1h (không high/low), không phí (0,11 %/vòng sẽ trừ thêm), không exit/SL, không lọc lineage/stable; chỉ để định cỡ số sự kiện và kiểm "có edge vô điều kiện không".
- Không đọc 2026; không chạy sim; ước lượng Calmar ở §5 là suy từ run lân cận, không phải đo.
