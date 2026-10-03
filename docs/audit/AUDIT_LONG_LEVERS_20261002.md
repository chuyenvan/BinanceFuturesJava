# AUDIT_LONG_LEVERS_20261002 — Bản đồ lever LONG trên B0 (G2+FLAT3): còn gì đáng chạy trên DEV?

- **Ngày:** 2026-10-02 (GMT+7). **Vai:** auditor nghiên cứu, CHỈ ĐỌC. 0 sim Java, 0 Kaggle, 0 sửa `.java`, 0 chạm 242/shadow, 0 dữ liệu 2026.
- **Nền:** B0 = `profiles/g2_flat3.properties`, printDone `~/kaggle_sim/out/de-p1` (md5 `650c386f…`, n 2517, eq 131 908; CAGR 2022+ 33,56, Calmar_MTM 1,898/1,940).
- **Script 0-sim (mới, research/analysis/):** `long_levers_b0_anatomy.py` (giải phẫu PnL + đường giá 1h trước/sau thoát + counterfactual tuyến tính) · `long_levers_paired_ruler.py` (hiệu chuẩn thước ghép cặp trên 9 arm exit ĐÃ chạy) · `long_levers_oi_check.py` (OI lúc vào) · `long_levers_pyramid.py` (pyramid/partial-TP tại arm). JSON: `docs/audit/AUDIT_LONG_LEVERS_20261002_{anatomy,paired,oi,pyramid}.json`.
- **Cảnh báo phương pháp (đọc trước):** (1) mọi counterfactual ở đây là **tuyến tính trên notional gốc**, dùng **close 1h** (`CLOSES_1H.bin`, không có high/low) ⇒ thời điểm arm là ước lượng (close ≥ +7 % là cận trên thời gian arm thật); (2) giờ printDone là UTC+7 (chọn offset −7h theo luật khoá trước: sai lệch entry/close nhỏ nhất; kiểm ở exit cho thấy ±1h còn mơ hồ — không ảnh hưởng horizon ≥24h); (3) phủ đường giá 85,8 % số lệnh; (4) **mọi phân rã ở §2 là MÔ TẢ hậu kiểm trên DEV** — không được dùng để chọn tham số; cái gì muốn thành lever phải pre-reg và chịu luật §9.

## KẾT LUẬN (rủi ro trước)

1. **Không còn lever LONG nào hứa hẹn cải thiện lớn (≥ +3 pp CAGR) mà đo được trên DEV.** Lever tầng gate/regime/portfolio nằm sau **power wall**: 2 517 lệnh nhưng chỉ **686 tick vào, 152 ngày vào, 123 episode**; top-5 episode = **36,6 %**, top-10 = **52,3 %** ΣPnL; CI block-72h của chính ΣPnL B0 = **[62,7k; 134,7k]** (±37 %) ⇒ một thay đổi gate phải dịch ~40 % ΣPnL mới tách được nhiễu. Không có cơ chế nào hứa hẹn cỡ đó.
2. **Phát hiện phương pháp quan trọng nhất:** với lever **chỉ đổi luật thoát/size trên CÙNG tập entry**, thước **ghép cặp theo lệnh** (size-neutral ΔPnL, CI block-72h) có nửa-độ-rộng **±2,4k…±5,4k (2,5–5,5 % ΣPnL)** cho các biến thể trailing lân cận — trong khi thước ΔCalmar block-72h đã dùng ở TRAIL/TRAIL2/VOLTARGET có CI **±25…±100 điểm Calmar** (Calmar ≈ 1,9) ⇒ **vô lực hoàn toàn**. Tức là tầng exit **KHÔNG bị power wall** nếu đo đúng; power wall chỉ áp cho tầng gate.
3. Chấm lại 9 arm exit đã chạy bằng thước ghép cặp (hiệu chuẩn, KHÔNG để chọn): kết luận chọn FLAT3 **đứng vững và nay có nghĩa** (~~FLAT3 − T0 = +1,06k~~ → **T0 − FLAT3 = +1,06k [−3,4k; +6,2k] (FLAT3 ≈ T0)** [sửa 2026-10-03, nguồn: `REAUDIT_FLAT3_20261003` 69b3cf07 — script tính arm − B0, B0 = FLAT3 nên dấu ngược; phần "nay có nghĩa" là nói quá, đúng là khác biệt ±1k nằm trong nhiễu ±5k]); A5 **−14,7k [−26,8; −3,1]**, A5LAD **−13,0k [−25,2; −0,8]**, GV3 **−2,4k [−4,9; −0,06]** (CI raw, chưa inflate k=9). Trailing là **đã khai thác xong**, không phải "chưa đủ lực".
4. **Lever duy nhất còn đáng một vòng DEV:** thời gian sống của lệnh **CHƯA arm** (loser time-stop 168h → 72h / conditional exit 72h×MFE<5 %). Cơ chế thấy rõ trong dữ liệu: 339 lệnh time-stop (13,5 % n) ăn **−55,9k** (= 36 % lãi gộp của lệnh thắng), giá trung vị trôi đơn điệu −5,5 % @24h → −9,9 % @72h → −13,6 % lúc cắt. Counterfactual 72h (close 1h) = **+11,3k [+3,5; +21,2]** nếu lệnh "arm bằng high" không bị cắt, **+1,5k [−7,8; +12,0]** nếu bị cắt hết ⇒ kỳ vọng **+1…+11 % ΣPnL**, xấp xỉ MDE; 2 nền cũ cho tín hiệu **ngược chiều** (C2b: ΣPnL +9,9 % ở X72; T170: equity −7 % ở fixed-96). Hai vòng cũ bị chấm bằng **rate lệch cơ học** (xem §3) ⇒ NULL cũ không đáng tin. Chi phí: 0 code, 2–3 kernel Kaggle.
5. **Mọi lever "chưa chạm" khác đo được 0-sim ở đây đều DƯỚI MDE hoặc ÂM:** time-decay arm +0,4…+1,8k (n.s.); pyramid tại arm +0,9k [−6,5; +11,5] (64 % lệnh lỗ, toàn bộ nhờ ~27 lệnh đuôi); partial-TP 50 % tại arm −1,8k; arm 9 % ước lượng âm nặng (§4); re-entry sau TS: hệ đã tự vào lại 549 lần (+18,7k), excess sau thoát ≈ 0; funding cả kỳ chỉ −1,4k (1,5 % ΣPnL); tổng phí 2,8k (2,9 % ΣPnL) ⇒ maker/funding timing có trần < MDE; size theo conviction (p15, symbolPred, dow15m, ΔOI, volume) CI chứa 0 sau khi bỏ episode top-1.
6. **Rủi ro lớn hơn mọi lever:** **42 % ΣPnL (41,0k, 521 lệnh) đến từ lệnh đóng TRONG GIỜ VÀO** (bắt nhịp hồi trong cú sập) ⇒ độ thật của giá khớp ở phút sập quyết định kỳ vọng (crash-penalty +0,69 %/chân đã làm G2 −10 % equity). Hai test **kiểm định tính chuyển giao** đã nháp ở `AUDIT_G2FLAT3_20261002` (B0_LIVEMODEL, FLAT3 + crash penalty) **ưu tiên hơn** vòng lever ở điểm 4.
7. ⇒ **Khuyến nghị:** chạy tối đa **1 vòng lever** (EXIT_TIME_B0, §5) và chỉ khi owner chấp nhận trước rằng T3 (`TSloss%`/`win%`) bị lệch cơ học với lever thời gian; còn lại **đóng DEV cho LONG**, dồn bằng chứng vào forward shadow (B0 đang PAPER trên 242).

## 1. BẢN ĐỒ LEVER THEO TẦNG

Cột "tin được?" = kết luận có đứng với power/thước/cách đo không. "MDE" ở cột này là MDE của thước ĐÃ dùng.

| tầng | đã thử (RESULT → verdict, số chính) | tin được? | còn gì chưa thử / nhận xét |
|---|---|---|---|
| **data / universe** | OI_STUDY (H1 NO-GO; H3 ΔOI-thấp tại MOM15 +5,0 % vs −0,5 %, vừa trên MDE), S1_OI12 (NULL, eq 104k vs 111k), LS_TAKER, DEVEXPORT audit, CONC cap 15 % (no-op, conc 4,09 %) | CÓ (OI H3 là cấp-coin, vừa qua MDE) | listing-age/delist chưa đo (không có trong printDone). **Thanh khoản lúc vào KHÔNG phân biệt**: quintile volume mean profit 5,2/4,4/4,5/4,3/3,9 % ⇒ lọc universe theo tier không có đòn bẩy. ΔOI lúc vào trên lệnh B0: tercile thấp 6,7 % vs 3,45 % nhưng sizing ΔPnL +4,0k [−5,4; +17,6] (n.s.), bỏ tercile cao mất 23,5k ⇒ không lọc |
| **feature** | FEAT_CUT_RVOL15M (dừng ở cổng model: |IC| −3,9 %), FEAT_ADD_V1 (FAIL T1: UW 353, 2022 âm, eq −15 %), ARM44, STAGE3, PRESCREEN, G015ABL, S1_HPO_BAG_FEATGRP | **MỘT PHẦN** — xem §3.2 (đo ở tầng G015 không nối với PnL) | không đáng đầu tư thêm vào G015: `symbolPred` gần như 0 thông tin về kết quả lệnh B0 (Spearman +0,014; trong-tick −0,021; quintile không đơn điệu) |
| **label** | LABEL_NETTHR (dừng ở cổng; M_010 qua ΔIC nhưng lift@8 kém), LABELH, LABEL_ROI1-3, S1_MAXFAV (NULL thước tiền), H72 | CÓ cho câu "đổi nhãn có đổi tiền?" (MAXFAV đo thước tiền) | multi-horizon ensemble chưa thử — nhưng cùng tầng S1/G015, thước tiền đã NULL 3 nhãn ⇒ kỳ vọng thấp |
| **model / selector** | MODEL_RULER (pairwise acc 0,482 ⇒ G015 là công cụ GATE, không xếp hạng), PNL_RULER (0 Δ ngoài CI), MONEY_RANKER, S1_RANK_QUALITY/CORRECT, K_SWEEP, K_DENSITY, DOUBLE_ENTRIES (K24 Calmar 1,673 FAIL T4) | CÓ | retrain cadence/online update chưa thử — tác động đi qua gate+tập đủ điều kiện ⇒ power wall |
| **gate (market)** | GATESCALE×3, GATEDYN/2, GD92 (đóng tạm), GDV2 (→ G2, ΔCAGR +6,7 CI [+3,4; +10,2] vs R4), GATE_RECAL, GATE_TOPK_LABEL_SIM (XẤU), BREADTH ×9 vòng (NULL), REGIME_GATE, REGIME_UPDOWN, TICK_BLOCK, FLATGATE | CÓ (NULL ở đây là đúng — power wall) | **đừng lặp breadth/regime** (§3.4). Rủi ro mở: p15 live ≠ p15 DEV (AUDIT_G2FLAT3 F1) |
| **ranking / TopK** | K 8→12→16→24, RANGE4H_TOPK, FUNDING_TOPK ×3, E1_CUT_TOPDECILE | CÓ | gate là ràng buộc binding (CAPACITY_DIAG: 0,0047 % ứng viên pass), không phải slot ⇒ TopK hết đòn bẩy |
| **sizing / DCA / conc** | F_BASE 0,03→0,015, 2X_HALFSIZE, SIZE_COUNT, DCA_* ×7 (NULL), FLATGRID, BD_SIZE_ADAPT (NULL), VOLTARGET_G2 (VT_COIN = hạ size ×0,72, Calmar ≈; VT_PORT BLOCKED hằng số 25 % cứng) | CÓ | **DCA grid của B0 không bao giờ khớp leg 2+** (`lastentry ≡ entry` 2517/2517, margin ≈ 1 leg) ⇒ "pyramid thay DCA" thực chất là THÊM cơ chế: CF +0,9k [−6,5; +11,5] ⇒ chết. Size theo conviction: CI chứa 0 (§2.6) |
| **exit: arm / trailing** | TRAIL_G2 (5 arm), TRAIL2_G2 (5 arm) → FLAT3; TRAIL_HINGE, TRAIL_LADDER (NO-GO), TRAIL_CAP_1030, GIVEBACK_RATIO, PEAK_CLOSE, CLOSE_BIGGAP, ARM3, SL_7_TO_3, SL_ADAPTIVE | **CÓ — sau khi chấm lại bằng thước ghép cặp** (§3.1) | arm 8–10 %: ước lượng ÂM (§4c). Partial-TP tại arm −1,8k; trailing đã khai thác xong |
| **exit: SL / time-stop** | E1 (X168→72: ΣPnL +9,9 %, chọn theo rate), F2 cond-exit (ΣPnL +5,8/+7,6 % nhưng NULL vì rate + UW 156), B_FOLLOWUP (T170: fixed-96 eq −7 %), HOLDTODIE (bỏ TS: paired −29,4k [−47,0; −11,9]), SHAPE1 (SL sớm thảm hoạ), FAMILY2 TP nhỏ (thảm hoạ), GRAVEYARD | **KHÔNG** cho E1/F2 (thước rate lệch cơ học, §3.3); CÓ cho HOLDTODIE/SHAPE1 | **time-stop 72–96h / cond-exit trên B0 CHƯA thử** ⇒ ứng viên duy nhất (§5). Time-decay arm: CF +0,4…+1,8k ⇒ dưới MDE |
| **cadence / latency** | R4_CADENCE, SIM_CADENCE_MATCH, LATENCY_FILL (median 7 s, không bias), PASS_SPEED ×3 | CÓ | không còn |
| **cost / execution** | COST_TRUTH (0,1116 %/vòng), EXECUTION_MAKER (maker cần ~100 % khớp mới hoà), LIMIT_ENTRY (NULL, 2022/2025 âm), CRASH_PENALTY (G2 −10 % eq ở +0,69 %/chân), BOOK_COST ×2 | CÓ | **trần lợi ích**: tổng phí B0 = **2,8k (2,9 % ΣPnL)** ⇒ maker rebate tối đa ~2,5k < MDE và dip-buy limit chịu adverse selection. **FLAT3 + crash penalty chưa chạy** (kỳ vọng, không phải lever) |
| **funding** | FUNDING_FACTOR (NO-GO), FUNDING_SIGN, FUNDING_TOPK ×3 | CÓ | Σfunding B0 = **−1,42k (1,5 % ΣPnL)** ⇒ vào-sau-settle có trần ~1k ⇒ chết |
| **portfolio** | HEDGE_OVERLAY_A (NULL), VOL_TARGET/VOLTARGET_G2, DD_THROTTLE (NULL), PACING_BIGDOWN, BOOKCAP | CÓ | vol-target port. chưa chạy được (hằng 25 %), nhưng là đòn bẩy/thời điểm ⇒ power wall |
| **risk / tail** | CRASH_PENALTY, TAIL_LEVER, BLACKSWAN_2510, CONC cap, COLLAPSE_PROBE, PUMPDUMP ×2 (NULL) | CÓ | không phải lever lợi nhuận |

## 2. GIẢI PHẪU PnL B0 (printDone `de-p1`, 0-sim; ΣPnL 96 909 USDT; Σnotional 2,51M)

### 2.1 Theo lý do thoát — toàn bộ lãi đến từ trailing, time-stop ăn 36 % lãi gộp

| lớp thoát | n | ΣPnL | % ΣPnL | mean / med profit % | win |
|---|---|---|---|---|---|
| TS armed (`STOP_MARKET_DONE`) | 2 157 | +153 645 | +158,5 % | 7,6 / 6,0 | 98,4 % |
| time-stop 168h (`STOP_LOSS_DONE`, giữ ≥167h) | 339 | **−55 914** | −57,7 % | **−15,7 / −13,6** | 6,8 % |
| SL khác (<167h) | 21 | −822 | −0,8 % | — | — |

Theo level: selector 2 223 lệnh +77,0k (79 %) · BIG_DOWN 248 +11,7k (12 %) · DCA_LEVEL1 **46 lệnh +8,3k (8,5 %, mean +40,7 %)**.

### 2.2 Theo thời gian giữ và ROI — "bánh mì" là lãi nhỏ 4–8 %, nhanh

| giữ | n | ΣPnL | % | | ROI lúc thoát | n | ΣPnL | % |
|---|---|---|---|---|---|---|---|---|
| **0h (đóng trong giờ vào)** | **521** | **+41 000** | **42,3 %** | | ≤ −30 % | 49 | −25 308 | −26 % |
| 1h | 185 | +14 783 | 15,3 % | | (−30; −15] | 127 | −27 579 | −28 % |
| 2–4h | 270 | +19 165 | 19,8 % | | (−15; −7] | 103 | −10 159 | −10 % |
| 5–12h | 451 | +29 328 | 30,3 % | | (−7; 0] | 77 | −2 717 | −3 % |
| 13–24h | 278 | +18 202 | 18,8 % | | (0; 4] | 205 | +7 201 | 7 % |
| 25–48h | 245 | +17 671 | 18,2 % | | **(4; 6]** | **874** | **+44 269** | **46 %** |
| 49–96h | 144 | +7 956 | 8,2 % | | (6; 8] | 509 | +35 961 | 37 % |
| 97–166h | 84 | +4 717 | 4,9 % | | (8; 12] | 373 | +35 102 | 36 % |
| 167h+ (time-stop) | 339 | −55 914 | −57,7 % | | (12; 50] | 173 | +27 497 | 28 % |
| | | | | | > 50 % | 27 | +12 642 | 13 % |

### 2.3 Theo năm / quý / giờ / thứ
- Năm: 2021H2 +6,5k · **2022 +4,6k (4,8 %)** · 2023 +24,9k · 2024 +30,8k · 2025 +30,1k. Quý âm: 2022Q2 −0,33k, 2025Q3 −0,28k; 2022Q4 chỉ +0,2k ⇒ B0 gần như không kiếm được trong năm bear duy nhất (khớp AUDIT_G2FLAT3 F7).
- Giờ vào (UTC+7): 24 ô, mean profit từ −1,5 % (22h) tới +11,4 % (4h) — **không cấu trúc** (24 phép so, n/ô 31–163, phụ thuộc vài episode) ⇒ không lever. Chủ nhật chỉ 53 lệnh (ΣPnL ≈ 0).

### 2.4 Cụm và episode — vì sao DEV hết lực cho tầng gate
- 2 517 lệnh ⇒ **686 tick vào**, **152 ngày vào**, **123 episode** đóng lệnh (khoảng trống ≤ 2 ngày). **55 % lệnh (1 391)** vào ở tick có ≥ 8 lệnh cùng lúc.
- Top episode: 2025-10-10→23 **+13,6k (14,0 %)** · 2025-02-03 +6,8k · 2024-02-27→03-09 +5,9k · 2023-04-05 +5,3k · 2024-12-19→27 +3,8k ⇒ top-5 **36,6 %**, top-10 **52,3 %**. Đáy: 2025-03-09 −3,7k, 2025-11-10 −3,4k, 2025-09-29 −2,4k, 2024-06-15 −2,3k, 2022-05-10 −2,1k.
- **CI block-72h của ΣPnL B0 = [62,7k; 134,7k]**. Đây là sàn nhiễu cho mọi so sánh KHÔNG ghép cặp.

### 2.5 "Để trên bàn" — giá sau khi thoát (close 1h; excess = trừ trung bình EW toàn universe cùng cửa sổ)

| nhóm | horizon | ret sau thoát med / mean | excess vs EW: med / mean [CI block-mean] | MFE sau thoát med |
|---|---|---|---|---|
| TS armed (2 157) | 24h | −0,2 % / +2,3 % | −0,5 % / +2,6 % [−0,6; +1,6]* | +6,1 % |
| | 72h | −0,7 % / +3,0 % | **−1,6 % / +2,0 % [−2,3; +4,1]** | +10,7 % |
| | 168h | −1,6 % / +4,1 % | −2,9 % / +3,1 % [−3,1; +12,4] | +14,7 % |
| time-stop (339) | 72h | −1,0 % / +0,6 % | −0,8 % / −0,2 % [−1,2; +1,4] | +5,6 % |
| | 168h | −1,3 % / +1,9 % | −2,3 % / +0,7 % [−3,5; +2,1] | +8,4 % |

\*CI là của trung bình theo khối, có thể lệch so với mean toàn mẫu do trọng số khối.
Đọc: **trung vị âm, trung bình dương nhờ đuôi** — đúng hình dạng alt ngẫu nhiên; MFE sau thoát lớn chỉ phản ánh biến động alt, không phải tiền bỏ quên. Hệ **đã tự vào lại cùng coin trong 72h sau TS 549 lần** (PnL các lệnh vào lại +18,7k). Time-stop **không** cắt ngay trước cú hồi (excess ≈ 0) ⇒ không có lever "SL rồi hồi".

### 2.6 Đường giá của 339 lệnh time-stop + counterfactual (tuyến tính, close 1h, CI block-72h raw 2000 rep seed 20260905)

- Close/entry − 1 (trung vị): **24h −5,5 % · 48h −8,5 % · 72h −9,9 % · 96h −11,1 % · 120h −12,3 % · lúc cắt −13,6 %**; tỉ lệ < −10 %: 32 % → 44 % → 50 % → 54 % → 59 %. Trước khi chết, **40 %** từng có close ≥ +3 %, **12 %** ≥ +5 % (close ⇒ cận dưới của high).
- **Time-stop sớm hơn** (cắt lệnh chưa arm tại close giờ H; "lệnh arm bằng high mà close chưa tới 7 %" là mơ hồ ⇒ báo 2 cận):

| H | lệnh bị ảnh hưởng | ΔPnL (giữ nguyên lệnh mơ hồ) | ΔPnL (cắt cả lệnh mơ hồ) | theo năm 21/22/23/24/25 (cận trên) |
|---|---|---|---|---|
| 48h | 435 (+129 mơ hồ) | +12,2k [+2,4; +23,2] | −3,8k [−15,7; +9,5] | +0,7/+3,2/+0,2/+2,3/+5,8k |
| **72h** | 395 (+79) | **+11,3k [+3,5; +21,2]** | **+1,5k [−7,8; +12,0]** | +2,3/+2,2/+0,4/+1,8/+4,5k |
| 96h | 370 (+52) | +4,0k [−3,6; +12,7] | −3,1k [−11,7; +5,9] | +1,7/+2,1/+0,2/−3,0/+2,9k |
| 120h | 361 (+31) | +2,0k [−4,3; +9,1] | −1,6k [−8,6; +6,2] | |

  Bỏ qua: tái sử dụng vốn (CAPACITY_DIAG: vốn không binding ⇒ nhỏ), khoá symbol, funding. **Kết luận mô tả:** dấu phụ thuộc vào số lệnh "thắng muộn" bị cắt — đúng thứ chỉ sim 1' mới phân xử được.
- **Time-decay arm** (chưa arm sau X giờ ⇒ arm hạ còn +3 %, rồi FLAT3): X=24 **+0,4k [−2,7; +4,1]**, X=48 **+1,8k [−0,4; +4,6]**, X=72 +1,3k [−0,3; +3,3] — loser hiếm khi quay lại +3 % sau 48h (chỉ ~54 lệnh) ⇒ **dưới MDE, bỏ**.
- **Pyramid tại arm** (thêm 1 leg cùng notional tại entry×1,07): **+0,9k [−6,5; +11,5]**, 64 % lệnh lỗ phần thêm (median exit 6,0 % < 7 % + phí). **Partial-TP 50 % tại arm:** **−1,8k [−7,3; +2,1]**. ⇒ cả hai chết; armed exit phân vị 10/25/50/75/90/95/99 = 4,0/5,0/6,0/8,5/11,5/14,4/53,3 %.
- **Size theo conviction** (trọng số 0,5×…1,5× theo hạng, giữ tổng notional): p15 **+4,9k [−4,2; +16,1]** (bỏ episode top-1: +0,6k [−6,6; +8,6]); symbolPred +1,1k [−9,4; +13,4]; volume +2,2k [−6,2; +13,2]; ΔOI24h +4,0k [−5,4; +17,6]; **dow15m (độ sâu cú giảm lúc vào) +7,8k [+0,5; +16,3]** nhưng bỏ episode 10/10/2025 còn **+4,9k [−1,1; +11,7]** (4/5 năm dương). Mean profit theo quintile dow15m (sâu→nông) bỏ top episode: 6,1/4,7/4,4/2,3/3,1 %. ⇒ **gợi ý có thật nhưng dưới ngưỡng, và đã bị chính audit này nhìn ⇒ KHÔNG còn sạch để pre-reg trên DEV** (chỉ đáng log forward).

## 3. THỬ SAI CÁCH? — từng vòng NULL/STOP quan trọng

### 3.1 TRAIL_G2 + TRAIL2_G2 (+ VOLTARGET, HOLDTODIE): **thước primary vô lực, nhưng kết luận đứng khi đo lại đúng**
- Primary = ΔCalmar bootstrap block-72h trên ledger resample: CI **±25…±100 điểm Calmar** khi Calmar thật ≈ 1,9 (episode-cluster ±5…±18). Thước này không phát hiện nổi kể cả thay đổi Calmar gấp 5–10 lần ⇒ mọi "≈ G2" ở đó là **tất yếu toán học**, không phải bằng chứng (AUDIT_G2FLAT3 F4 đã nêu).
- Lever exit **không đổi entry** ⇒ khớp lệnh (sym+start+level, 76–96 % lệnh khớp) và lấy ΔPnL size-neutral = Δprofit × notional_B0 (lệnh lệch: cộng/trừ chính nó). Chấm lại arm ĐÃ chạy vs B0 (CI raw; **hiệu chuẩn, không chọn** — k=9 ⇒ inflate 2,10):

| arm vs B0 | khớp / chỉ-B0 / chỉ-arm | ΔPnL size-neutral | CI95 raw | nửa-độ-rộng | ΔCalmar CI đã công bố |
|---|---|---|---|---|---|
| T0 (=G2) | 2335/182/174 | +1,06k | [−3,38; +6,22] | 4,8k | (gốc) |
| GV3 | 2408/109/93 | −2,40k | [−4,87; −0,06] | 2,4k | [−57,9; +33,1] |
| LAD | 2331/186/163 | −0,72k | [−4,73; +3,64] | 4,2k | [−60,8; +60,5] |
| PROP30 | 2393/124/110 | −2,16k | [−5,29; +0,68] | 3,0k | [−53,9; +33,6] |
| FLAT5 | 2291/226/200 | −0,21k | [−5,32; +5,40] | 5,4k | [−36,5; +21,8] |
| PROP50 | 2235/282/253 | +0,71k | [−9,22; +12,42] | 10,8k | [−26,4; +23,6] |
| A5 | 1949/568/615 | **−14,70k** | [−26,77; −3,07] | 11,8k | [−99,1; +77,4] |
| A5LAD | 1902/615/681 | **−13,03k** | [−25,21; −0,85] | 12,2k | [−83,2; +126,2] |
| HTD-H1 (bỏ time-stop) | 1912/605/402 | **−29,41k** | [−47,04; −11,91] | 17,6k | (FAIL T1) |

  Σ(profit × notional) B0 = 98,3k. **Nửa-độ-rộng tỉ lệ với số lệnh bị đổi/lệch**: 2,4–5,4k (2,5–5,5 %) cho biến thể gần, 11–18k khi đổi arm/bỏ time-stop. ⇒ Kết luận trailing **đáng tin**: FLAT3 không kém T0/LAD/PROP ngoài ~±5 %; hạ arm thì kém rõ. Tầng này **đã khai thác xong**.

### 3.2 FEAT_CUT_RVOL15M / FEAT_ADD_V1 / LABEL_NETTHR: **đo ở tầng không nối với PnL của B0**
- Cổng tầng model đo rank-IC/lift@8 của G015 (45 cột) theo `retEnd_4h` cross-section. Trong B0, G015 **không xếp hạng** (thứ tự coin = S1); nó chỉ vào **ngưỡng gate từng coin** qua `symbolPred` (RESULT_ARM44 §3). Đo trực tiếp trên 2 517 lệnh B0: `symbolPred` vs profit Spearman **+0,014**, trong cùng tick (≥3 lệnh) **−0,021**; quintile 4,0/2,7/4,8/3,4/3,6 % (không đơn điệu); MODEL_RULER: pairwise accuracy 0,482.
- ⇒ "Dừng ở cổng model" đúng **về hướng** (không nên đổi) nhưng **sai lý do**: dù G015 tốt/xấu hơn ở rank-IC, đường truyền duy nhất sang PnL là **số lượng lệnh qua gate** (kênh hiệu chuẩn) — tức tầng gate, nơi power wall áp. FEAT_ADD_V1 sim (−15 % equity, FAIL T1) chính là hiệu ứng kênh đó. **Đừng đầu tư thêm vào chất lượng G015 như một lever LONG.**
- Governance: LABEL_NETTHR — M_010 **qua** luật ΔrankIC đã pre-reg nhưng bị chặn bởi điều kiện lift@8 thêm ngày 09-30 (sau pre-reg). Không đổi kết luận (do điểm trên) nhưng là tiền lệ đổi luật giữa vòng.

### 3.3 E1 (time-stop 168→72) / F2 (cond-exit) / B_FOLLOWUP: **thước rate lệch cơ học ⇒ NULL không đáng tin cả hai chiều**
- E1 (nền C2b): ΣPnL tăng **đơn điệu** khi cắt sớm: 25,4k → 25,8k (120h) → 27,4k (96h) → **27,9k (72h, +9,9 %)**; F2: 25,4k → **26,9k / 27,3k (+5,8 / +7,6 %)**, `mean(profit|SL)` −18,9 → −14,0 %, `mean(profit|SM)` gần như không đổi. Cả hai bị phán bằng `win%`/`TSloss%` — mà lệnh bị cắt sớm **mang nhãn STOP_LOSS_DONE theo định nghĩa** ⇒ 2 rate này xấu đi **cơ học** (F2 tự ghi trong pre-reg) — cộng UW 156 > 120 (luật cũ; luật hiện hành UW ≤ 250).
- B_FOLLOWUP (nền T170): fixed-96 equity 111,1k → 103,1k (−7 %), adaptive-120 −1,5 %. Cũng chấm bằng rate, không ghép cặp.
- ⇒ Bằng chứng về lever "thời gian sống lệnh chưa arm" là **mâu thuẫn và chưa từng đo bằng thước tiền ghép cặp**, và **chưa từng chạy trên B0**. Đây là lỗ hổng phương pháp thật duy nhất còn lại ở tầng exit ⇒ ứng viên §5.

### 3.4 BREADTH ×9 vòng (+REGIME_GATE, REGIME_UPDOWN, DD_THROTTLE): **NULL là đúng — đừng lặp**
- Breadth/regime là biến **chậm**: số lần chuyển chế độ trên DEV cỡ vài chục (ALT_REGIME_WAVES: 20–24 cửa sổ), còn kết quả quyết định bởi ~10 episode (top-10 = 52 % ΣPnL). Mọi biến thể chỉ đổi **episode nào được giao dịch** ⇒ phán quyết xoay quanh UW/2025 của 1–2 đợt. Không thước nào (ghép cặp cũng không — entry đổi) vượt được giới hạn này trên DEV. Lặp lại = tăng multiplicity, không tăng thông tin. Chỉ forward thêm thời gian mới giải được.

### 3.5 Các điểm phụ
- **BD_SIZE_ADAPT** (size leg BIG_DOWN theo severity): PRIMARY đòi ≥ 2/3 **rate chất lượng** ngoài CI — rate (win%, meanP, TSloss%) **bất biến với size theo định nghĩa** ⇒ luật không thể PASS dù lever có lợi. Lever size chưa từng được chấm bằng PnL. (Không đổi khuyến nghị: §2.6 cho thấy hiệu ứng size theo conviction dưới MDE.)
- **VOLTARGET_G2:** VT_PORT **không chạy** (hằng `PORTFOLIO_TARGET_ANNUAL_VOL=0.25f` cứng) ⇒ là "chưa thử", không phải NULL; nhưng là lever đòn bẩy/thời điểm ⇒ power wall.
- **GDV2/G2:** chọn đúng trong DEV; rủi ro chuyển giao p15 live (AUDIT_G2FLAT3 F1) chưa đóng.

## 4. LEVER "CHƯA CHẠM" (danh sách gợi ý (a)–(m) + 1) — kiểm từng cái

| # | lever | kiểm được gì (0-sim) | phán |
|---|---|---|---|
| a | entry timing / limit vs taker cho dip-buy | 42 % ΣPnL từ lệnh đóng trong giờ vào ⇒ limit dưới giá sẽ **bỏ lỡ đúng các cú hồi nhanh nhất** (adverse selection); LIMIT_ENTRY NULL (2022/2025 âm); trần phí 2,8k | **chết** |
| b | size theo conviction (p15 / symbolPred / dow15m / ΔOI / volume) | CF §2.6: mọi CI chứa 0 sau khi bỏ episode top-1; dow15m mạnh nhất +4,9k [−1,1; +11,7] | **dưới MDE + đã bị nhìn** ⇒ chỉ log forward |
| c | pyramiding thay DCA | DCA grid B0 **không khớp leg 2+ lần nào**; pyramid tại arm +0,9k [−6,5; +11,5], 64 % lệnh lỗ phần thêm | **chết** |
| d | time-decay arm | +0,4…+1,8k, CI chứa 0 | **chết** |
| e | partial take-profit | 50 % tại arm −1,8k [−7,3; +2,1] (FAMILY2 TP nhỏ: thảm hoạ) | **chết** |
| f | re-entry sau SL/TS | hệ đã tự vào lại 549 lần/72h (+18,7k); excess sau TS ≈ 0 (median −1,6 %/72h); sau time-stop ≈ 0 | **chết** (đã có sẵn) |
| g | universe filter (tier/listing-age/delist) | volume quintile phẳng; ΔOI-cao vẫn lãi (+23,5k) ⇒ lọc mất tiền; listing-age chưa có dữ liệu trong printDone | **chết** (tier); listing-age chưa đo, prior thấp |
| h | gate breadth 1' thay p15 | §3.4 | **đừng lặp** |
| i | multi-horizon label ensemble | tầng S1/G015; MAXFAV NULL trên thước tiền (3 nhãn); G015 không nối PnL (§3.2) | **không đáng** |
| j | retrain cadence / online update | tác động đi qua tập ứng viên + gate ⇒ power wall; chi phí retrain 16–18 fold | **không đáng trên DEV** |
| k | neutralize score theo tier | không có lệch theo tier để khử (volume quintile phẳng) | **chết** |
| l | funding-aware entry (vào sau settle) | Σfunding B0 = −1,42k (1,5 % ΣPnL) ⇒ trần < MDE | **chết** |
| m | maker rebate thật | trần ≈ tổng phí 2,8k; EXECUTION_MAKER cần ~100 % khớp | **chết** |
| + | arm 8–10 % + FLAT3 (AUDIT_G2FLAT3 Q10) | 874 lệnh thoát ở 4–6 % (= 46 % ΣPnL) có đỉnh ≈ 7–9 %; với arm 9 % chúng không được bảo vệ, ~25 % (theo MFE sau thoát) trôi về time-stop (≈ −15 %) ⇒ ước lượng thô **−10…−30k**; đường cong arm 3 % (xấu) → 5 % (−14,7k) → 7 % gợi ý 7 % gần cực đại | **không đáng** |
| + | time-stop 72h / cond-exit trên B0 | §2.6 + §3.3 | **ứng viên duy nhất** |

## 5. ỨNG VIÊN XẾP HẠNG (≤ 3) — theo (kỳ vọng cải thiện × khả năng đo trên DEV)

**Thẳng thắn:** chỉ có **1 lever** vượt được ngưỡng "đáng chạy", và cả nó cũng chỉ **sát MDE**. Hai mục kiểm-chuyển-giao (không phải lever) đứng **trên** nó về giá trị thông tin.

| hạng | việc | tầng | đo ở đâu | kỳ vọng | MDE (thước) | chi phí |
|---|---|---|---|---|---|---|
| (0, không phải lever) | `B0_LIVEMODEL` + `FLAT3 × crash-penalty 0,69/1,50` (đã nháp, AUDIT_G2FLAT3 §3–4) | chuyển giao / kỳ vọng | sim Kaggle | trả lời "DEV có mô tả 242 không" và "−10…−20 % do giá khớp phút sập" | — | 3–4 kernel, 0 code (penalty jar `d944bea5` có sẵn) |
| **1** | **EXIT_TIME_B0**: loser time-stop 168→72h **và** cond-exit 72h × MFE<5 % | exit (thời gian sống lệnh chưa arm) | sim Kaggle, chấm **ghép cặp** | **+1,5…+11,3k (≈ +1,5…+11 % ΣPnL; CAGR +0,4…+2,5 pp)**; dấu chưa chắc (C2b +, T170 −) | nửa-độ-rộng dự kiến 5–8k ⇒ MDE80 ≈ 8–13k (×1,177, k=2) ⇒ **power ≈ 15–45 %** | 3 kernel (parity + 2), **0 code** (key `SIM_LOSER_TIME_STOP_HOURS`, `SIM_COND_EXIT_HOURS/_MIN_FAV` đã có) |
| 2 | **Log forward** conviction `dow15m` / ΔOI (không chạy DEV) | sizing | forward shadow | +5 % ΣPnL nếu thật | cần ≥ 1–2 năm forward | 0 DEV; chỉ cần pre-reg giả thuyết + đảm bảo cột có trong log shadow |
| — | mọi lever khác | — | — | dưới MDE hoặc âm (§4) | — | — |

### 5.1 Pre-reg NHÁP `EXIT_TIME_B0` (chưa chốt — chờ MASTER/owner)

- **Câu hỏi:** cắt sớm lệnh **chưa arm** (flat 72h, hoặc 72h có điều kiện MFE < 5 %) có tăng PnL của **cùng tập entry** B0 không?
- **Nền:** `profiles/g2_flat3.properties` nguyên vẹn; bundle `sim-x1-2021-bundle`; jar `sim-jar-gdv2` (`7368be46…`); `SIM_END_DATE=20251231`. **Cổng 0:** parity md5 printDone `650c386f…` (sai ⇒ DỪNG). **Cổng 1:** xác nhận key được đọc (log/DumpConfig) và jar có nhánh COND_EXIT (nếu không ⇒ chỉ chạy A1, k=1).
- **Arm (k=2, khoá):** A1 `SIM_LOSER_TIME_STOP_HOURS=72` · A2 `SIM_COND_EXIT_HOURS=72`, `SIM_COND_EXIT_MIN_FAV=0.05` (giữ LOSER_TS 168). Không arm thứ 3, không quét H.
- **Thước PRIMARY (khoá):** ΔPnL size-neutral ghép cặp theo `sym|start|level` (logic `research/analysis/long_levers_paired_ruler.py`), CI block-72h theo giờ vào, 2000 rep, seed 20260905, **inflate √(2 ln 2) = 1,177**.
- **Luật GO (cố định, theo §9):** GO ⇔ (i) cận dưới CI-inflate của ΔPnL > 0 **và** (ii) T1 §9 PASS (maxDD MTM phút ≤ 40 %/năm, UW ≤ 250, quý xấu ≥ −20 %, 0 năm âm, conc ≤ 15 %) **và** (iii) T4: Calmar_MTM (báo cả toàn kỳ và 2022+) ≥ 0,90 × 1,940 = 1,746, conc ≤ 4,09 **và** (iv) ΔPnL ≥ 0 ở ≥ 3/4 năm 2022–2025 **và** (v) n ∈ [0,95; 1,10] × 2 517. Cả hai GO ⇒ chọn arm có **cận dưới CI cao hơn**.
- **T3 (`win%` ≥ −2 pp, `TSloss%` ≤ +2,5 pp): owner phải quyết TRƯỚC khi chạy.** Lever này đổi nhãn lệnh bị cắt thành STOP_LOSS_DONE ⇒ 2 rate xấu đi **cơ học** (E1/F2: TSloss +2,4…+3,9 pp). Đề xuất: báo T3 nhưng thay bằng ràng buộc "ΔPnL nhóm lệnh thắng (khớp, armed ở B0) ≥ −3k". Nếu owner giữ T3 nguyên ⇒ **không nên chạy** (FAIL gần như chắc chắn theo cấu trúc).
- **Báo kèm:** số lệnh bị cắt, mean profit nhóm bị cắt vs trên B0, số "thắng muộn" bị cắt, UW, năm/quý (`qstat_r4.py`), Δ theo năm.
- **Cấm:** đổi H/MIN_FAV sau khi thấy số; dùng 2026; chạy lại arm. Rủi ro ghi trước: dấu có thể âm (T170 −7 %); hiệu ứng tối đa ước lượng ~11 % ΣPnL.

## 6. CÂU TRẢ LỜI CHO OWNER

**"Còn hướng nào cải tiến LONG tiếp không?"** — Trên DEV: **gần như KHÔNG.** Lý do:
1. Tầng gate/regime/portfolio (nơi có thể có cải thiện lớn) bị **power wall**: 152 ngày vào, ~10 episode quyết định 52 % ΣPnL, CI ΣPnL ±37 %. 9 vòng breadth + regime + DD-throttle NULL là **đúng**, lặp thêm chỉ tăng multiplicity.
2. Tầng exit/size (đo được ghép cặp, MDE ~5–10 % ΣPnL) **đã được khai thác**: trailing xong (FLAT3 đứng vững khi chấm lại), pyramid/partial-TP/time-decay arm/re-entry/arm cao đều dưới MDE hoặc âm. Chỉ còn **một** lỗ hổng phương pháp thật — thời gian sống của lệnh chưa arm — với kỳ vọng tối đa ~+11 % ΣPnL và power ~15–45 %.
3. Tầng model/feature/label (G015) **không nối** với PnL B0 ngoài kênh đếm gate (`symbolPred` ≈ 0 thông tin về kết quả lệnh) ⇒ không phải lever.
4. Phí và funding cộng lại chỉ ~4,4 % ΣPnL ⇒ trần lợi ích của mọi lever thực thi/funding thấp hơn MDE.

**Khuyến nghị thứ tự:** (1) chạy 2 test chuyển giao/kỳ vọng đã nháp (B0_LIVEMODEL, FLAT3 × crash-penalty) — chúng có thể **giảm** kỳ vọng 10–20 %, lớn hơn mọi lever; (2) tuỳ owner, 1 vòng `EXIT_TIME_B0` với điều kiện T3 nêu trên; (3) sau đó **đóng DEV cho LONG**, coi forward shadow trên 242 (đang PAPER, gate hết warm-up ~2026-10-07) là nguồn bằng chứng duy nhất còn tăng được thông tin; log sẵn `dow15m`/ΔOI lúc vào cho giả thuyết conviction forward.

## 7. GIỚI HẠN (khai rõ)
- Counterfactual tuyến tính, close 1h, không tái phân bổ vốn/khoá symbol/funding ⇒ chỉ để **định cỡ** lever, không thay sim.
- Thước ghép cặp: lệnh lệch (4–24 %) cộng/trừ nguyên PnL ⇒ CI rộng hơn khi lever đổi nhiều entry; không phù hợp cho lever tầng gate.
- Múi giờ printDone suy từ căn chỉnh giá (offset −7h; ±1h mơ hồ ở exit). Phủ đường giá 85,8 %; OI 83,4 %.
- Mọi phân rã §2 là hậu kiểm trên DEV đã dùng ~30+ lần (GDV2_P3 đếm ~27) ⇒ chỉ sinh giả thuyết.
- Không đọc được project memory `audit_dev_exhausted`/`power_wall` (ngoài repo) — dùng số trong docs và số đo lại ở đây.
