# R4 SIGNAL — PHA 0: chiến lược quyết định cho tín hiệu p15 nhiễu/tự tương quan (khảo sát + thiết kế, KHÔNG sim) — 2026-11-11

Nhãn: [NGUỒN] = đã mở trang/metadata; [META] = chỉ thấy metadata qua kết quả tìm kiếm, chưa đọc nội dung; [ĐO] = số đo thật; [MEM] = project memory / docs/result; [SUY ĐOÁN].
Bối cảnh: họ "làm mượt p15 / đa khung cho gate" ĐÓNG (R3_FUTILITY b61a26ff): MEAN60 iso-count ΔCAGR −21…−25 pp, leg −36…−39 %; MTF-OR dừng futility; MEAN15 loại quota 2 lần; LATCH loại quota; TIER-DOWN loại (S4 FALSE). Cơ chế đã đo: q chỉ cập nhật theo giờ + tín hiệu mượt dai dẳng ⇒ pass dồn cụm ⇒ va U_MAX/skipFull.
Artefact pha 0: `r4s_novelty_1111.py` → `novelty_1111.log` (proxy market-level, pred DEV `~/wfo_ds_x1_2021/pred.bin`, qua flock).

## 1. Khảo sát tài liệu → ánh xạ vào hệ

| # | Phương pháp | Nguồn | Ý chính | Trùng/gần hướng ĐÃ ĐÓNG | Khác ở đâu |
|---|---|---|---|---|---|
| L1 | CUSUM (Page) / tối ưu phát hiện đổi | Page 1954, *Biometrika* "Continuous inspection schemes" [META]; Moustakides 1986, *Ann. Statist.* 14(4):1379–1387 [NGUỒN] https://projecteuclid.org/journals/annals-of-statistics/volume-14/issue-4/Optimal-Stopping-Times-for-Detecting-Changes-in-Distributions/10.1214/aos/1176350164.full | Cộng dồn độ lệch so với mức chuẩn, báo khi tổng vượt h; Moustakides chứng minh stopping time của Page tối ưu (theo một nghĩa minimax trễ/báo động giả — chi tiết tiêu chí chưa kiểm). | CUSUM là bộ TÍCH PHÂN ⇒ gần họ MEAN (dai dẳng, trễ với stress vừa phải) — ĐÓNG | Có reset sau báo ⇒ tự khử cụm; vẫn trễ khi stress tăng dần ⇒ không đề xuất |
| L2 | CUSUM filter lấy mẫu sự kiện | López de Prado 2018, *Advances in Financial ML* (Wiley), Snippet 2.4 tr. 39 — mô tả qua mlfinpy [NGUỒN] https://mlfinpy.readthedocs.io/en/stable/Filtering.html | Chỉ lấy mẫu khi thay đổi cộng dồn từ mốc reset vượt ngưỡng; giá trị lảng vảng quanh ngưỡng KHÔNG kích hoạt lặp lại. | Không trùng trực tiếp; gần BURST_COOLDOWN (chặn theo THỜI GIAN sau burst, NO-GO Calmar 1,30) | Chặn theo TRẠNG THÁI tín hiệu (chỉ kích lại khi tín hiệu leo thêm) → ý tưởng cho C2 |
| L3 | Khử cụm vượt ngưỡng (EVT, extremal index) | Ferro & Segers 2003, *JRSS-B* 65(2):545–556 [NGUỒN] https://econpapers.repec.org/RePEc:bla:jorssb:v:65:y:2003:i:2:p:545-556 | Vượt ngưỡng cao trong chuỗi phụ thuộc đến theo cụm; khử cụm tự động dựa trên phân bố thời gian giữa các lần vượt; extremal index ước lượng trước khi khử cụm. | GATE_STAB/BX24 (S5 FALSE), skipFull (đã có) | Cho khung đo "đợt" và lý do tách cụm; dùng trong C2 + chỉ số sàng |
| L4 | Meta-labeling | López de Prado 2018 (sách trên); Joubert 2022, *JFDS* 4(3):31–44; Meyer, Barziy, Joubert 2023 *JFDS* 5(2):23–40 — qua Wikipedia [NGUỒN thứ cấp] https://en.wikipedia.org/wiki/Meta-Labeling | Mô hình chính quyết định "có tín hiệu/hướng", mô hình phụ (phân loại nhị phân) dự báo tín hiệu đó có lời không ⇒ lọc/size; tăng precision đổi lấy recall. | GATE_VZ (thêm feature vào model gate p15, NO-GO); S1/selector (xếp coin); MKT_UP (hướng thị trường) — ĐÓNG | Mức Ô (coin-phút) có ĐIỀU KIỆN đã qua gate, nhãn = kết quả giao dịch, không đổi model p15 → C3 |
| L5 | Regime switching / HMM (tầng chậm làm điều kiện) | Hamilton 1989, *Econometrica* 57(2):357–384 [META] https://econpapers.repec.org/RePEc:ecm:emetrp:v:57:y:1989:i:2:p:357-84 ; Ang & Timmermann 2012, *Annu. Rev. Financ. Econ.* 4:313–337 [META] https://econpapers.repec.org/RePEc:anr:refeco:v:4:y:2012:p:313-337 | Trạng thái ẩn đổi theo Markov; tham số/quyết định phụ thuộc regime. | MKT_UP/MKT_UP2/MD_STRAT/UP_TRIG, GATE_SMART V-b VOLN (S2 regime vol FALSE), REGIME gate T100/T170 — ĐÓNG | Không còn khác biệt đủ ⇒ không đề xuất |
| L6 | "Surprise"/innovation (thành phần mới của chuỗi bền) ; Kalman | Benhamou 2018, "Trend without hiccups: a Kalman filter approach", arXiv 1808.03297 [NGUỒN] https://econpapers.repec.org/RePEc:arx:papers:1808.03297 | Kalman làm mượt ít trễ hơn MA; mô hình tốt nhất kết hợp làm mượt + vị trí cực trị. Ý tổng quát (suy đoán, không phải trích dẫn): tín hiệu bền = mức nền + innovation; quyết định theo innovation tránh đếm lặp mức nền. | MEAN15/MEAN60/MTF-OR dùng phần THÔNG THẤP — ĐÓNG | Dùng phần THÔNG CAO (p15 − nền quá khứ), không trễ → C1 |
| L7 | Làm mượt thích nghi (KAMA, efficiency ratio) | Kaufman 1995, *Smarter Trading* (McGraw-Hill) — qua TA-Lib [NGUỒN] https://ta-lib.org/functions/er.html | Hệ số làm mượt theo tỉ lệ hiệu quả: chuỗi đi thẳng ⇒ bám nhanh, đi ngang ⇒ mượt mạnh. | Họ làm mượt — ĐÓNG (cùng cơ chế quota/q-giờ) | Không đề xuất |
| L8 | Vùng không giao dịch / giao dịch từng phần, trọng số theo tốc độ phân rã tín hiệu | Gârleanu & Pedersen 2013, *J. Finance* 68(6):2309–2340 [NGUỒN] https://econpapers.repec.org/RePEc:bla:jfinan:v:68:y:2013:i:6:p:2309-2340 ; Davis & Norman 1990, *Math. Oper. Res.* 15(4):676–713 (dẫn trong Guasoni & Muhle-Karbe, arXiv 1207.7330) [NGUỒN thứ cấp] https://arxiv.org/pdf/1207.7330 | Có phí ⇒ "nhắm trước mục tiêu, giao dịch từng phần về aim"; tín hiệu phân rã chậm được trọng số lớn hơn; có vùng không giao dịch. | Hysteresis = LATCH G4 (quota 1,37, loại); size theo mức = TIER-DOWN (S4 FALSE), CONF_SIZE (spearman −0,02), ISO_RISK — ĐÓNG | Bài học chuyển được: edge p15 phân rã NHANH (ACF 0,955/phút) ⇒ phải hành động ngay phút cực trị (khớp ENTRY_CONFIRM) — ủng hộ C1/C2 không trễ |
| L9 | Hysteresis/Schmitt trigger | Khái niệm kỹ thuật điện tử; KHÔNG tìm thấy bài tài chính đã kiểm (chưa kiểm) | Ngưỡng bật cao hơn ngưỡng tắt ⇒ chống rung. | LATCH G4 — ĐÓNG | — |
| L10 | Phân vị có điều kiện (ngưỡng động) | Engle & Manganelli 2004, CAViaR, *JBES* 22:367–381 [META] https://econpapers.repec.org/RePEc:bes:jnlbes:v:22:y:2004:p:367-381 | Phân vị mô hình tự hồi quy theo thời gian bằng hồi quy phân vị. | GATE_SMART V-a EWQ/V-b VOLN (S1/S2/S3 FALSE) — ĐÓNG | Chỉ dùng làm lý do cho cách giữ quota |
| L11 | Hawkes (sự kiện tự kích thích, dồn cụm) | Bacry, Mastromatteo, Muzy 2015, "Hawkes processes in finance", arXiv 1502.04592 [NGUỒN] https://arxiv.org/abs/1502.04592 (tạp chí: chưa kiểm) | Cường độ sự kiện tăng sau mỗi sự kiện ⇒ mô hình hoá cụm. | BURST_COOLDOWN NO-GO; GATE_STAB S5 FALSE; N_DEEP: lệnh >20/đợt LÃI NHẤT (giới hạn cụm là hại) — ĐÓNG | Chỉ dùng làm thước mô tả cụm |
| L12 | Stacking/ensemble đa khung | Wolpert 1992, "Stacked generalization", *Neural Networks* [META] https://cafri-labs.github.io/lab-manual/papers/wolpert1992.pdf | Mô hình tầng 2 học cách kết hợp dự báo tầng 1. | MTF-OR G3 (dừng), GATE_ABLATION (nhiễu retrain 5,3 pp), GATE_VZ — ĐÓNG | Nếu làm thì nằm trong C3 (meta) |

## 2. Số đo dùng cho thiết kế
- [MEM/ĐO] ACF p15 0,955 (1′), 0,83–0,84 (15′), 0,69 (60′); 576 phút pass / 121 đợt; trung vị r/q ô pass 1,15 (MASTER cấp).
- [ĐO proxy, market-level, top-k phút p15 DEV, k=625] 42 đợt, trung vị 5 phút/đợt; chỉ **22,7 %** phút top là "đỉnh mới 15′" (p15(t) > max p15[t−15′,t−1′]); mọi đợt (42/42) có ≥1 phút đỉnh mới, trung vị 2,5/đợt, nằm ở phút thứ 4 (p75 35) tính từ đầu đợt.
- [ĐO proxy] surprise u(t) = p15(t) − mean p15[t−60′,t−1′]: ACF 0,854 (1′) nhưng **0,303 (15′)** (p15: 0,83) ⇒ ít dai dẳng ở thang giờ; top-k của u trùng top-k p15 Jaccard 0,467; trải ra **90 đợt** (p15: 42) ⇒ ít dồn cụm hơn.
- [MEM] S4: near-miss r/q∈[0,85;1) vs pass_low r/q∈[1;1,1): fwd72 ròng −1,0 pp CI90 [−2,75;+0,70] ⇒ chất lượng ô quanh ngưỡng gần như phẳng. N_DEEP: lệnh thêm (ngưỡng thấp) ROI 1,87–2,78 % < lệnh bị đẩy 3,12–3,92 %. ENTRY_CONFIRM: trễ vào −27,7k/seed.

## 3. Ứng viên (≤3, cơ chế khác nhau, tham số cố định, KHÔNG quét lưới)
Chung: chỉ nhánh PREDICT_SYMBOL_TRADE (sp != null); BIG_DOWN/DCA_LEVEL1 giữ nguyên; held/skipFull/K24/X14/A1 giữ nguyên; key mới mặc định OFF (G0 byte-identical n4f-b0-a1, printDone md5 d03d320d); jar vá AS-FILE (r3_wt) + template orch R3.
**Iso-count chung:** pct của arm tìm nhị phân (float32) sao cho Σ8 seed số ô pass DEV 2022–25 (gate_offline, chỉ ĐẾM) = B0 ±5 %; ràng buộc thêm quota TỪNG NĂM ∈ [0,85;1,15] (chặt hơn R3 vì bài học MEAN15) — trượt ⇒ LOẠI, không chỉnh. **q theo giờ:** C1/C2 dùng nguyên GateRatioBuffer (cập nhật mỗi giờ) — chấp nhận vì thống kê của C1 ít dai dẳng (ACF15 0,30) và C2 chỉ pass ở phút leo thang; sàng §4 đo trực tiếp số ô/giờ tối đa và tỉ lệ ô rơi vào lúc sổ B0 bão hoà.

### C1 SURPRISE60 — gate trên phần innovation (thông cao), không trễ
- b(t) = trung bình p15 các phút s ∈ [t−60′, t−1′] theo thời gian thật (cần ≥48/60 giá trị, thiếu ⇒ coi như không có pred cho PREDICT); u(t) = p15(t) − b(t) (float32).
- r_u = u(t) / (max(DYN_MIN, sp/0,15·1,2876)·gs); nạp/tính q_u y GateRatioBuffer (90d, mỗi giờ, warm-up 7d); PASS ⇔ !(r_u < q_u) **và** p15(t) ≥ 0,008 (hằng `MIN_MOMENTUM_15M` sẵn có, đảm bảo stress tuyệt đối; không tune).
- W = 60′: ACF p15 lag60 = 0,69 ⇒ nền 60′ vẫn là "trạng thái hiện hành" nhưng đủ dài để tách cú nhảy; không thử W khác.
- Cơ chế: ENTRY_CONFIRM + R4_CADENCE cho thấy edge ở đúng phút dislocation; u đạt đỉnh tại phút nhảy (không trễ) và giảm khi stress thành "nền" ⇒ bớt pass lặp trên cao nguyên (nguồn dồn cụm/skipFull), trải sang nhiều đợt hơn (90 vs 42 proxy).
- Live: ring 60 giá trị p15 (~0,5 KB); khởi động lại phải rehydrate 60′ từ `storage/data/prediction` (chỉ đọc) nếu không mất 48–60′ gate; seed buffer gate dựng lại trên r_u; log [GATE-RATIO] thêm u, b. Parity: lỗ phút live (FAIL-CLOSED, tick chậm) phải áp đúng luật ≥48/60 như sim.
- Khác hướng đóng: MEAN/MTF dùng thông thấp (trễ 9–34′ proxy); C1 dùng thông cao, 0 trễ.

### C2 NOVELTY15 — luật sự kiện: chỉ pass ở phút tín hiệu LEO THANG
- PASS ⇔ !(r < q_N) (r, buffer, q như B0 nhưng pct_N iso-count) **và** p15(t) > max p15[t−15′, t−1′] (cần ≥12/15 giá trị, thiếu ⇒ KHÔNG pass — fail-closed).
- 15′ = chân trời nhãn gate và ACF 0,83 ⇒ cùng "nhịp" stress; không thử cửa sổ khác.
- Cơ chế (L2 CUSUM filter, L3 khử cụm): giữ thống kê MỨC của B0 (không đổi thứ hạng phút) nhưng bỏ phút "cao nguyên" — chỉ 22,7 % phút top là đỉnh mới, mọi đợt còn ≥1 phút ⇒ không bỏ đợt; quota trả lại cho ô r thấp hơn ở các phút leo thang. Không dùng đồng hồ (khác BURST_COOLDOWN/BX24); khác LATCH (LATCH NỚI sau pass, C2 SIẾT).
- Rủi ro biết trước: iso-count cần pct_N thấp hẳn ⇒ thêm ô r/q thấp (N_DEEP: thêm lệnh ngưỡng thấp ROI kém lệnh bị đẩy); bỏ phút cao nguyên có thể bỏ lệnh trong đợt lớn (L3: lệnh >20/đợt lãi nhất).
- Live: ring 15 giá trị; như C1 về rehydrate/parity; nhẹ nhất.

### C3 META60 — meta-labeling trên ô đã qua gate
- Chính: luật B0 với pct_M sao cho số ô = 1,5 × B0 (iso-count trên đếm); 1,5 cố định (giữ lại 2/3 — mức lọc vừa, theo tinh thần "precision đổi recall" của L4; không tune).
- Phụ: hồi quy logistic (không cây, hạn chế overfit), 7 feature cố định, causal: r/q, u(t) (C1), mean60 p15, số phút từ đầu đợt (đợt = cụm phút pass cách >60′, theo luật chính), số ô pass thị trường 60′ qua, hạng sp, log(1+số leg B0 đang mở theo printDone B0 — xấp xỉ U). Nhãn = 1{fwd72 ròng 0,2 % > 0}.
- WFO: quý, expanding từ 2021-07, purge 72h, mô hình quý Q chỉ thấy ô < Q−72h; ngưỡng giữ = phân vị (1−2/3) của xác suất dự báo trên ô chính 90 ngày trước (causal) ⇒ giữ ~2/3, iso-count với B0.
- Cơ chế: dùng tín hiệu mượt làm NGỮ CẢNH (feature) thay vì làm trigger — đúng điều owner nói "số mượt cần chiến lược khác"; trigger vẫn là p15 điểm.
- Live: phức tạp nhất — model theo quý (vài chục hệ số), tracker đợt, đếm 60′, U thật; parity cần replay feature; nhãn cần 72h ⇒ cập nhật chậm.
- Khác hướng đóng: GATE_VZ đổi model p15 mức thị trường; S1 xếp coin; C3 là bộ lọc mức ô có điều kiện + nhãn kết quả.

## 4. Sàng lọc rẻ (kiểu S4) — làm TRƯỚC mọi sim
- Tập ô mỗi arm (8 seed pred n4f-b0, bins, held = printDone n4f-b0-*), bằng `gate_offline` mở rộng (C1/C2 thêm key; C3 cần nhãn ⇒ chạy 2 bước). THÊM = arm \ B0, BỚT = B0 \ arm (theo (ts, sym, seed)), gộp 8 seed trọng số n_seed như S4.
- fwd: ret_H = close(t+1′+H)/close(t+1′) − 1 − 0,2 %, H = 72h (chính), 24h (phụ); nan72 bỏ và báo cáo.
- Bootstrap cụm NGÀY (+07), 2 000 lần, seed RNG 20261111. Tiêu chí QUA (khai trước): (a) cận dưới CI của mean(THÊM) − mean(BỚT) > 0, CI hai phía mức **1 − 0,10/3 ≈ 96,7 %** (Bonferroni cho 3 ứng viên; CI90 thuần nếu MASTER chỉ giữ 1 ứng viên); (b) cùng dấu ≥3/4 năm 2022–25; (c) cùng dấu khi bỏ ô lúc sổ B0 "bão hoà" (số leg B0 mở ≥ phân vị 95 % của chính nó — xấp xỉ U_MAX vì gate_offline không mô hình skipFull); (d) quota năm đạt §3. Thiếu 1 ⇒ không sim.
- Mô tả kèm (không chấm): Jaccard phút, số đợt trúng, ô/giờ tối đa, |THÊM|, |BỚT|.
- C3: trước sàng cần fwd72 cho TẬP CHÍNH (pct_M) để huấn luyện WFO ⇒ cùng kernel fwd tính cho tập hợp ô C1 ∪ C2 ∪ chính C3 ∪ B0 một lần.
- Dữ liệu: pred n4f-b0 8 seed (đã trên Oracle theo R3 P1), bins bundle, printDone n4f-b0-*, kline close 1m (Kaggle, như `gsm-s4-cells`/`s4k.py`).
- Compute: Oracle — gate_offline ~267 s/lượt 4 arm×8 seed (R3 P1) ⇒ C1+C2+chính C3 với 4–5 vòng nhị phân ≈ 20–30 phút, RSS ~4 GB; LR WFO < 5 phút; đĩa < 300 MB (còn 18 GB). Kaggle — 1 kernel fwd (dataset ô parquet ≤ 100 MB, tái dùng s4k.py, không mạng) ≈ 2–4 h; 2 kernel nếu tách C3. Tổng sàng ≈ nửa ngày wall.
- Chỉ ứng viên QUA sàng: sim 8 seed ghép cặp n4f-b0 (jar vá + key mới, G0 byte-identical), futility 4 seed như R3, MTM gvz_mtm missing=0; ~1,1 h/kernel ⇒ ~4,5 h wall/arm với 2 kernel + MTM.

## 5. Rủi ro + xác suất (thẳng)
- Đa kiểm định: họ gate đã thử ≥12 biến thể (G1–G5, B1–B2, GATE_SMART V-a..d qua S1–S5, GATE_VZ VA/VB, H60/RULE/NOCAL, GQSF, GKF). DEV 2022–25 và HO 2026 đều đã dùng nhiều lần ⇒ GO (nếu có) chỉ đủ để forward shadow paper, không đổi live; báo DSR; Holm theo arm thực chạy; HO chỉ cùng dấu.
- Sàng fwd72 không có exit/DCA/U_MAX thật ⇒ dương tính giả có thể (C2/C3 nhạy nhất). C3: số hiệu dụng ≈ số đợt (~121), feature r/q đã FALSE ở S1/S4 ⇒ overfit dễ.
- Live: mọi ứng viên cần p15 mỗi phút + rehydrate; seed buffer gate phải dựng lại; v1.2 KHÔNG đổi.
- Xác suất [SUY ĐOÁN]:
  - C1 SURPRISE60: qua sàng ~20 %, GO sim ~7 %. Lý do: khử cụm thật (ACF15 0,30, 90 đợt) và 0 trễ; nhưng phần bị bớt là ô cao nguyên trong đợt lớn (L3/N_DEEP: lãi nhất) và S4 cho thấy chất lượng ô quanh ngưỡng phẳng ⇒ hoán đổi ô khó tạo lợi.
  - C2 NOVELTY15: qua sàng ~15 %, GO ~5 %. Bỏ ~77 % phút pass (proxy) ⇒ iso-count phải thêm nhiều ô r thấp — đúng loại N_DEEP thấy kém.
  - C3 META60: qua sàng ~10 %, GO ~3 %. Feature yếu, N hiệu dụng nhỏ, phức tạp live cao.
  - ≥1 GO trong 3: ~13 %. Khuyến nghị: chạy SÀNG cả 3 (rẻ, nửa ngày), sim chỉ khi qua; nếu cả 3 trượt ⇒ đóng hẳn hướng "chiến lược quyết định trên p15", coi edge p15 điểm đã gần tối ưu.
