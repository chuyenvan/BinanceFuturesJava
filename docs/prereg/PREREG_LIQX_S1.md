# PREREG LIQX_S1 — Bước 1: pattern "cascade thanh lý → cạn" (proxy P2) và pha vào lệnh

Ngày: 2026-10-24. Agent: liqx1 (Opus). Thiết kế: MASTER (giao việc LIQX_S1). Bước 0: `docs/prereg/PREREG_LIQX_S0.md`, `docs/result/LIQX_S0.md` (71be80f4).
File này được commit TRƯỚC khi tính bất kỳ return sau sự kiện, PnL hay IC nào. Trước commit agent chỉ xem: schema, độ phủ, danh sách symbol, header/khoảng thời gian của printDone (không phân tích PnL; lệnh `head` vô tình in 2 dòng printDone 2025-11-21 — không dùng).
Mọi ngưỡng dưới đây CHỐT; không chỉnh sau khi thấy kết quả. Bug phát hiện sau kết quả ⇒ sửa + ADDENDUM + báo số trước/sau.

## 1. Dữ liệu
- Kline 1m `~/vz_e1/raw/kline1m-YYYY-MM.parquet` 2021-12…2025-12: `ts` = open_time ms int64, close, volume (base), quote_volume (USD), taker_buy_base, taker_buy_quote; có hàng cho phút không giao dịch; PIT gồm symbol delist. Lỗ đã biết: 2022-03-01 (~34 symbol thiếu ~18 bucket), 2022-04-01/02 (~35 symbol không có bar) ⇒ bucket thiếu bị loại (mục 4), MKT có luật hợp lệ (mục 5).
- Vision metrics 5m `~/vz/out/metrics5m/YYYY/YYYY-MM.parquet`: `ts` = create_time ms int64 (thô, KHÔNG dịch), `oi` (hợp đồng), `oi_value` (USD), `taker_ls_vol` (= sum_taker_long_short_vol_ratio = buyVol/sellVol). Chỉ đọc 2021-12-31 (warm-up) … 2025-12-31.
- Daily quote volume `~/claude_master/liqx_wk/daily_qv.parquet` (do LIQX_S0 `daily_qv.py` dựng từ kline 1m; ghi sha256 vào result).
- Tardis thanh lý ngày-01 `~/claude_master/liqx_wk/tardis/` (chỉ V5, mô tả).
- X14 printDone `~/kaggle_sim/out/tsx-x14-{a1,s7,s13,s21,s99,s123,s777,s2024}/storage/printDone.csv` (8 seed như liq_proxy/fundneg_t1). `start` giờ +07 ⇒ UTC = start − 7h. CHỈ kỳ A.
- Không dùng 2020, 2021H1, 2026 (metrics 2026-01 KHÔNG đọc ⇒ bucket 2026-01-01 00:00 của symbol quy ước OLD có thể thiếu).

## 2. Quy ước create_time của metrics — phát hiện THEO TỪNG (symbol, ngày), KHÔNG hardcode ngày
- Nhóm = (sym, ngày UTC của create_time c). Từ kline 1m dựng cửa sổ 5m bắt đầu w: tb = Σ taker_buy_base, v = Σ volume của 5 bar open w…w+4′ (đủ 5 bar), r(w) = tb/(v − tb) (chỉ khi tb > 0 và v − tb > 0).
- err_old = median_c |x(c)/r(c − 5′) − 1| (cửa sổ [c−5′, c), create_time = CUỐI kỳ); err_new = median_c |x(c)/r(c) − 1| (cửa sổ [c, c+5′), create_time = ĐẦU kỳ); x = taker_ls_vol; cần ≥ 12 cặp hợp lệ mỗi phía.
- err_new < err_old/10 ⇒ NEW; err_old < err_new/10 ⇒ OLD. Không kết luận (hoặc < 12 cặp) ⇒ phép phụ theo OI_FIX_LOG mục 5 bước 2: giá ngầm p = oi_value/oi so close bar open c−1′ (OLD: snapshot tại c) vs close bar open c+4′ (NEW: snapshot tại c+5′), cùng luật 10×, ≥ 12 cặp. Vẫn không kết luận ⇒ AMBIG ⇒ metrics của (sym, ngày) đó = NaN (bucket không hợp lệ). Không đoán theo ngày.
- ts hiệu lực: NEW ⇒ create_time + 5′; OLD ⇒ create_time.
- Hàng biên c ≡ 00:00 (c mod 1 ngày = 0): file OLD chạy 00:05…24:00, file NEW 00:00…23:55 ⇒ hàng 00:00 thuộc file ngày trước nếu ngày trước OLD, ngược lại thuộc file ngày hiện tại. Nếu ngày trước OLD và ngày hiện tại NEW (2 file cùng có 00:00, packer giữ 1) ⇒ bỏ hàng đó. Nếu quy ước gán là AMBIG ⇒ bỏ.
- Sau dịch, (sym, ts hiệu lực) trùng ⇒ bỏ mọi bản trùng (đếm). Phát hiện chạy cho ngày M−1 … M_next (ngày đầu tháng sau chỉ để gán hàng biên; không dùng giá trị tương lai).
- Báo: số (sym, ngày) NEW / OLD / AMBIG (và số giải bằng phép giá) theo tháng.

## 3. Universe (PIT, tái lập đầu mỗi tháng M)
- Ứng viên: symbol có ≥ 1 ngày trong daily_qv trong [M − 30 ngày, M), trừ EXCL = {USDCUSDT, BTCDOMUSDT, DEFIUSDT, FOOTBALLUSDT, BLUEBIRDUSDT, PAXGUSDT, XAUUSDT} (stablecoin/chỉ số/kim loại — không phải coin crypto).
- Điểm = median của 30 giá trị daily quote volume ngày M−30…M−1 (ngày không có dữ liệu = 0). U(M) = top-100 theo điểm (gồm symbol sau này delist). ALT(M) = U(M) \ {BTCUSDT, ETHUSDT}. BASKET24(M) = top-24 của ALT(M) theo cùng điểm.

## 4. Bucket cấp COIN (sym ∈ U(tháng của ngày D))
- T = D + k·300 000 ms, k = 1…288 (cửa sổ [T−5′, T)). Mọi ts int64 ms UTC. Assert 288 bucket/(sym, ngày) trên lưới; hợp lệ đếm riêng.
- oiv0 = oi_value hiệu lực tại T−5′, oiv1 tại T. OIdrop_usd = max(0, oiv0 − oiv1).
- c(T) = close bar open T−1′; c(T−5′) = close bar open T−6′; c(T−60′) = close bar open T−61′. r5 = ln c(T)/c(T−5′). cum60 = ln c(T)/c(T−60′) (NaN nếu thiếu).
- TSX = max(0, Σ taker_sell_quote − Σ taker_buy_quote) = max(0, Σ quote_volume − 2·Σ taker_buy_quote) trên 5 bar open T−5′…T−1′ (đủ 5 bar).
- P2 = min(OIdrop_usd, TSX) nếu r5 < 0, ngược lại 0. Hợp lệ ⇔ oiv0 > 0, oiv1, c(T), c(T−5′) có và đủ 5 bar. I_coin = P2/oiv0 (NaN nếu không hợp lệ).

## 5. Bucket cấp MKT
- Trên coin của U hợp lệ tại T: I_mkt = Σ P2 / Σ oiv0; r_mkt = mean r5 (EW) trên ALT hợp lệ; cum60_mkt = mean cum60 trên ALT có cum60; báo riêng r5/cum60 BTC; n_valid = số coin hợp lệ.
- MKT hợp lệ ⇔ n_valid(T) ≥ 0,85 × median n_valid của 2 016 bucket gần nhất ≤ T (7 ngày, causal). Không hợp lệ ⇒ I_mkt, r_mkt, cum60_mkt = NaN.

## 6. Ngưỡng (CHỐT, tính từ kỳ A, dùng nguyên cho B)
- A = bucket T ∈ (2022-01-01, 2024-01-01]; B = T ∈ (2024-01-01, 2026-01-01] (đợt gán kỳ theo ONSET).
- θ_MKT = np.percentile(I_mkt trên mọi bucket MKT hợp lệ của A, 99) (linear). D_MKT: cum60_mkt ≤ ln(0,97).
- θ_coin(s) = percentile 99 của I_coin(s) trên mọi bucket hợp lệ của s trong A (khi s ∈ U); cần ≥ 90 ngày UTC khác nhau có bucket hợp lệ trong A và θ > 0, ngược lại coin bị loại khỏi cấp COIN (cả A và B). D_COIN: cum60 ≤ ln(0,95).

## 7. Đợt (episode) — từng chuỗi (MKT; mỗi coin)
- Rảnh: bắt đầu tại bucket hợp lệ đầu tiên có I ≥ θ VÀ cum60 ≤ ln(1 − D) (ONSET).
- Đang chạy: kết thúc tại bucket b đầu tiên sao cho b−2, b−1, b là 3 bucket liên tiếp (cách 5′, hợp lệ) có I < θ/4, hoặc tại bucket T ≥ T_onset + 6h (bucket NaN cắt chuỗi đếm). Sau khi kết thúc, rảnh từ bucket kế.
- Gộp: ONSET đợt sau − END đợt trước < 2h ⇒ gộp (ONSET sớm, END muộn; gộp nối tiếp được).
- Báo: số đợt theo năm, độ dài (ONSET→END), top 20 đợt MKT (ngày, độ sâu, I đỉnh). Độ sâu = min_{b∈[ONSET, END]} Σ r_mkt từ bucket ONSET−60′ (exclusive) tới b (log, EW alt; kèm BTC).

## 8. Pha
- ONSET: bucket bắt đầu. PEAK: argmax I trên [ONSET, END] (chỉ mô tả).
- EXH (causal): duyệt b trong (ONSET, ONSET + 6h]; M_b = max I trên [ONSET, b], j_b = bucket đạt M_b (sớm nhất). EXH = b đầu tiên với b−1 > j_b, b−1 và b liên tiếp & hợp lệ, I(b−1) < M_b/4, I(b) < M_b/4, và r5(b) ≥ −0,005 (log; MKT dùng r_mkt, COIN dùng r5 coin). Không có ⇒ EXH thiếu (đếm, loại khỏi C1–C3, báo riêng).
- Vào: ENTRY_ON = close bar 1m open_time T_onset (đóng lúc T_onset + 1′); ENTRY_EXH = close bar open T_exh. Mọi tín hiệu chỉ dùng dữ liệu ≤ T.

## 9. Đo sau vào (gross; net = gross − 0,002)
- MKT: rổ BASKET24(tháng ONSET), giá trị V(t) = mean_i P_i(t)/P_i(t_e) trên coin có bar tại t_e; P_i(t) = close bar open ≤ t gần nhất (ffill, kể cả delist). COIN: chính coin, ffill như trên.
- ret_h = ln V(t_e + h), h ∈ {60′, 240′, 1440′, 4320′}. MFE24 = max_{1≤k≤1440} ln V(t_e+k′), MAE24 = min tương ứng (trên đường close 1m). Thiếu dữ liệu tương lai (sau 2025-12-31 23:59) ⇒ NaN. Báo kèm return BTC (mô tả).

## 10. Control và tiêu chí
- Control: mỗi đợt 200 điểm vào, bar open T_onset + j·1′, j ~ đều {0…360} có hoàn lại, numpy default_rng(20261024) cố định thứ tự đợt. rank_EXH = (#ctrl < x + 0,5·#ctrl = x)/n_ctrl, x = ret_1440 EXH. Báo kèm rank_ON.
- C1: diff = ret_1440(EXH) − ret_1440(ON) theo đợt; mean; CI 95 % bootstrap percentile 10 000 lần (seed 7) theo ĐỢT (COIN: theo ngày UTC của ONSET, lấy cả cụm) ⇒ cận dưới > 0 ở CẢ A và B.
- C2: mean rank_EXH ≥ 0,6 ở cả A và B (bao hàm "≥ 0,5 trung bình"); báo kèm median rank và % đợt rank ≥ 0,5.
- C3: median MAE24(EXH) ≥ median MAE24(ON) (không tệ hơn) ở cả A và B.
- C4: ≥ 15 đợt MKT ĐÁNH GIÁ ĐƯỢC (có EXH và ret_1440 của ON và EXH) mỗi kỳ; ít hơn ⇒ KHÔNG ĐỦ MẪU (không phải trượt).
- Verdict: MKT đạt C4 và C1–C3 ⇒ GO Bước 2. MKT trượt/không đủ mẫu nhưng COIN đạt C1–C3 ⇒ ỨNG VIÊN COIN (MASTER quyết). Còn lại NO-GO. Báo cả gross và net (diff EXH−ON không đổi theo phí).
- Nhạy (mô tả, KHÔNG dùng chọn): θ = p98, p99,5 (khởi đầu và kết thúc đợt); ngưỡng cạn M_b/3, M_b/6.

## 11. X14 trên pha — CHỈ KỲ A (B/2026 mù)
- Đọc printDone, tính start_u = start − 7h, LỌC start_u ∈ [2022-01-01, 2024-01-01) TRƯỚC khi chạm cột pnl; bỏ entry ≤ 0/NaN (như liq_proxy). sym thiếu "USDT" ⇒ thêm.
- Pha theo đợt MKT (đợt gần nhất có ONSET − 6h ≤ t): TRƯỚC = [ONSET − 6h, ONSET); TRONG_TRƯỚC_EXH = [ONSET, T_exh + 1′) (không EXH: [ONSET, ONSET + 6h)); SAU_EXH = [T_exh + 1′, T_exh + 24h) (không EXH: SAU_NOEXH = [ONSET + 6h, ONSET + 24h)); NGOÀI = còn lại. Phép phụ cùng định nghĩa trên đợt COIN của chính symbol.
- Cụm leg = (seed, sym, đợt) (NGOÀI: (seed, sym, ngày UTC)). Báo theo pha: n leg, n cụm, độ trễ so ONSET/EXH (giờ), PnL leg (USD) và roi = pnl/margin: mean, median, CI 95 % bootstrap theo đợt (NGOÀI: theo ngày); tỉ trọng PnL A theo pha (trung bình 8 seed). Chỉ mô tả.

## 12. Validation
- V1 look-ahead: 3 đợt MKT (độ sâu lớn nhất), T* = T_exh (không EXH: ONSET + 30′). Dựng lại bucket từ dữ liệu thô của [ngày ONSET − 1, ngày ONSET + 1] với close/volume/quote_volume/taker_buy_* (bar open ≥ T*) và oi/oi_value (ts hiệu lực > T*) nhân ×3 (quy ước create_time lấy từ bản gốc; ×3 giữ nguyên tỉ lệ taker) ⇒ mọi giá trị bucket T ≤ T* giống hệt, ONSET/EXH không đổi.
- V2: ts int64 mọi bảng; 288 bucket/(sym, ngày) trên lưới; liệt kê (sym, ngày) thiếu bucket hợp lệ (gồm 2022-03-01, 2022-04-01/02).
- V3: script độc lập tối giản (không import pipeline; đọc thô; tự tính universe từ kline thô, quy ước create_time, I_mkt, r_mkt, cum60, ONSET/EXH với θ_MKT của pipeline) cho 3 đợt lớn (2022-05-12, 2022-06-13, 2022-11-09 nếu là đợt; thiếu ⇒ đợt độ sâu lớn nhất kế tiếp) ⇒ |Δ I_mkt| < 1e-9, ONSET/EXH trùng.
- V4: in tay 1 đợt lớn: chuỗi I_mkt, r_mkt, cum60, Σ oiv0, Σ OIdrop, Σ TSX, n_valid theo bucket.
- V5: đợt có ONSET rơi vào ngày-01 (nếu có): so I_coin với LIQ_long Tardis/oiv0 theo bucket (Spearman, tổng) — mô tả.
- Tài nguyên: max RSS mỗi tiến trình (resource.getrusage) ≤ 5 GB, ghi lại; trung gian ở `~/claude_master/liqx_wk/s1/` ≤ 3 GB.

## 13. Lệch thiết kế (so với giao việc MASTER) — chi tiết kỹ thuật
1. Loại EXCL (stablecoin/chỉ số/kim loại) khỏi U trước khi xếp hạng.
2. Median 30 ngày với ngày thiếu = 0 (symbol mới < 15 ngày không vào U).
3. Phát hiện quy ước có phép phụ giá ngầm (OI_FIX_LOG mục 5 bước 2) trước khi đặt NaN; nhóm theo ngày của create_time + luật hàng biên 00:00.
4. Luật hợp lệ MKT (0,85 × median 7 ngày trượt, causal) để loại bucket lỗ kline.
5. "Return tích luỹ 60′" = log close(T)/close(T−60′) (MKT: trung bình EW alt); D chuyển thành ln(1 − D).
6. EXH chỉ tìm trong (ONSET, ONSET + 6h] (= cửa sổ control); không có ⇒ loại khỏi C1–C3 (đếm riêng). r5 ≥ −0,5 % hiểu là log.
7. C2 = mean rank ≥ 0,6 (đã bao hàm ≥ 0,5); C4 đếm đợt đánh giá được.
8. MFE/MAE trên đường close 1m (không high/low) cho khớp "giá close 1m".
9. Return 72h của đợt cuối A có thể dùng giá tháng 1/2024 (chỉ giá, không PnL X14 của B). Đợt cuối B thiếu horizon dài ⇒ NaN.
10. Định nghĩa cửa sổ pha X14 (mục 11) do agent chốt.
