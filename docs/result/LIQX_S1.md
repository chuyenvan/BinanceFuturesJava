# LIQX_S1 — Bước 1: pattern "cascade thanh lý → cạn" (P2) và pha vào lệnh

Prereg `docs/prereg/PREREG_LIQX_S1.md` (ad10cc97, sha256 991cd816…ffdf7) + AMEND1 `PREREG_LIQX_S1_AMEND1.md` (ec025a37, sha256 edcced42…13a1, commit TRƯỚC mọi return). Code `research/liqx_s1/`. Artefact `docs/result/liqx_s1/`. Agent liqx1, 2026-10-24.

## VERDICT: **NO-GO** (cấp MKT trượt C1, C2, C3 ở cả A và B; C4 đạt — đủ mẫu). Cấp COIN cũng trượt C1, C2 (chỉ đạt C3).
- Vào lúc "cạn" (EXH) **TỆ HƠN** vào lúc ONSET, có ý nghĩa thống kê ở cả hai kỳ: chênh ret 24h EXH − ON = **−0,25 % [−0,47; −0,03]** (A) và **−0,33 % [−0,60; −0,05]** (B). Mọi biến thể nhạy (θ p98/p99,5; cạn /3, /6) đều âm.
- EXH không hơn điểm vào ngẫu nhiên trong 6h đầu đợt (rank 0,525 | 0,534 < 0,6), trong khi chính ONSET có rank 0,552 | 0,597.
- MAE 24h của EXH tệ hơn ON (−3,55 % vs −3,44 % A; −3,86 % vs −3,41 % B).
- ⇒ "đợi cạn rồi mới vào" không có giá trị ở độ phân giải 5′ của proxy P2. Không sang Bước 2 với luật EXH.

## 1. Bảng chính — cấp MKT (rổ EW alt top-24, giá close 1m, log return; net = gross − 0,20 %)
| chỉ số | A 2022–23 | B 2024–25 |
|---|---|---|
| đợt / có EXH / đánh giá được (C4 ≥ 15) | 184 / 184 / 184 ✅ | 155 / 155 / 155 ✅ |
| ON ret 24h gross mean [CI đợt] | −0,33 % [−1,52; +0,79] | **+1,52 % [+0,41; +2,63]** |
| ON ret 24h net | −0,53 % | +1,32 % |
| EXH ret 24h gross mean [CI] | −0,58 % [−1,77; +0,53] | +1,19 % [+0,09; +2,27] |
| EXH ret 24h net | −0,78 % | +0,99 % |
| control (200 điểm/đợt) ret 24h mean | −0,56 % | +1,07 % |
| **C1** EXH − ON 24h mean [CI 95 % bootstrap đợt] | **−0,25 % [−0,47; −0,03] ❌** | **−0,33 % [−0,60; −0,05] ❌** |
| **C2** rank EXH mean (median; % ≥ 0,5) | **0,525 ❌** (0,516; 52,7 %) | **0,534 ❌** (0,550; 53,5 %) |
| rank ON mean (tham khảo) | 0,552 | 0,597 |
| **C3** median MAE24 EXH vs ON | **−3,55 % vs −3,44 % ❌** | **−3,86 % vs −3,41 % ❌** |
| median MFE24 EXH vs ON | 3,41 % vs 3,67 % | 4,33 % vs 5,20 % |
| ON ret 1h / 4h / 72h gross | +0,06 / +0,16 / −1,51 % | +0,32 / +0,39 / +2,58 % |
| EXH ret 1h / 4h / 72h gross | −0,05 / −0,13 / −1,81 % | +0,01 / +0,12 / +2,22 % |

Cấp COIN (167 coin có θ; CI bootstrap theo ngày ONSET):
| chỉ số | A | B |
|---|---|---|
| đợt (ngày) | 6 591 (493) | 2 944 (333) |
| C1 EXH − ON 24h | −0,35 % [−0,63; −0,08] ❌ | +0,05 % [−0,71; +0,84] ❌ |
| C2 rank EXH mean | 0,530 ❌ | 0,545 ❌ |
| C3 MAE24 EXH vs ON | −4,65 vs −4,76 % ✅ | −4,92 vs −5,52 % ✅ |
| ON / EXH / control ret 24h gross | −0,37 / −0,72 / −0,82 % | +1,28 / +1,32 / +1,13 % |

Nhạy (mô tả, MKT, EXH − ON 24h [CI]; rank EXH): p98 A −0,16 [−0,38; +0,07] 0,522 | B −0,23 [−0,45; +0,01] 0,546; p99,5 A −0,23 [−0,50; +0,04] 0,546 | B −0,37 [−0,73; +0,05] 0,522; cạn /3 A −0,23 [−0,44; −0,00] | B −0,33 [−0,60; −0,03]; cạn /6 A −0,25 [−0,48; −0,03] | B −0,33 [−0,61; −0,05]. COIN: mọi biến thể A âm (CI < 0), B ≈ 0. Đủ số: `score.json`.

Theo năm (MKT, ON ret 24h mean | EXH − ON): 2022 −1,36 % | −0,24 %; 2023 +1,69 % | −0,27 %; 2024 +2,18 % | −0,25 %; 2025 +0,44 % | −0,45 % — EXH thua ON ở CẢ 4 năm; ON tự thân phụ thuộc regime (2022 âm).

## 2. Pattern trông như thế nào
- θ_MKT (p99 I_mkt kỳ A) = **0,00649** (0,65 % OI USD bị "thanh lý" trong 5′); p98 0,00448, p99,5 0,00915. Kỳ B chỉ 0,51 % bucket vượt θ (A: 1 %). I_mkt max A 0,136 (2023-08-17 21:45), B 0,071.
- Số đợt MKT: 2022 **122**, 2023 **62**, 2024 **96**, 2025 **59** (COIN: 3 932 / 2 659 / 2 143 / 801; median 51 đợt/coin trong 4 năm).
- **Cascade là MỘT nhịp 5′**: PEAK trùng ONSET ở ≥ 75 % đợt (p90 trễ 25′); độ dài ONSET→END quartile 15 / 25 / 47,5′, p90 96′, max 285′ (15′ = tối thiểu của luật kết thúc); 11–21 % đợt/năm là gộp nhiều nhịp (< 2h).
- **Cạn tới ngay**: EXH trễ sau ONSET median **10′** (= tối thiểu khả dĩ: 2 bucket sau đỉnh), p75 15′, p90 25′, max 70′ (COIN giống hệt). ⇒ phép thử EXH vs ON thực chất là "vào trễ 10′". 11,8 % đợt có EXH TRƯỚC PEAK (sóng thứ hai lớn hơn đến sau tín hiệu cạn) — ví dụ 2025-10-10: ONSET 21:00 (I 0,025), EXH 21:10, rồi bucket 21:20 r_mkt EW alt **−66,9 %**/5′, I 0,047 (V4).
- Top đợt theo độ sâu (EW alt, log): 2025-10-10 21:00 −0,84; 2022-05-11 11:05 −0,27; 2024-04-13 17:40 −0,26; 2025-02-02 22:45 −0,25; 2024-01-03 12:00 −0,25; 2022-11-08 17:45 −0,24 … (đủ 20: `top20_mkt.csv`; mọi đợt: `episodes_mkt_main.csv`).

## 3. X14 trên pha — CHỈ KỲ A (B/2026 không đọc PnL)
10 927 leg (8 seed), PnL A trung bình 37,2k USD/seed. 87/184 đợt MKT A có ≥ 1 leg; leg ĐẦU của đợt rơi vào: TRƯỚC 56, TRONG_TRƯỚC_EXH 21, SAU_EXH 10.
| pha (đợt MKT) | n leg | n cụm | n đợt | roi/leg mean [CI đợt] | median | PnL/leg USD [CI] | tỉ trọng PnL A (TB 8 seed) | win | trễ vs ONSET / EXH (median, h) |
|---|---|---|---|---|---|---|---|---|---|
| TRƯỚC [ONSET−6h, ONSET) | 3 917 | 3 623 | 56 | 4,59 % [1,35; 7,10] | 5,39 % | 28,5 [9,7; 43,6] | **37,4 %** | 87,0 % | **−0,07** / −0,32 |
| TRONG_TRƯỚC_EXH | 3 425 | 3 352 | 38 | 3,56 % [1,23; 5,70] | 5,46 % | 22,9 [7,3; 36,9] | 26,5 % | 81,2 % | +0,08 / −0,23 |
| SAU_EXH [EXH, EXH+24h) | 2 426 | 2 233 | 35 | 2,94 % [−1,33; 5,74] | 5,41 % | 12,6 [−10,5; 28,4] | 10,3 % | 84,9 % | +1,50 / +1,23 |
| NGOÀI | 1 159 | 1 135 | — | 7,30 % [0,22; 16,8] | 5,89 % | 66,3 [1,2; 152] | 25,9 % | 82,3 % | — |
- Đọc: X14 vào **ngay trong nhịp cascade** — leg "TRƯỚC" có trễ median −4′ so với mốc đóng bucket ONSET, tức nằm TRONG bucket 5′ cascade (crash-buy nổ trước khi bucket 5′ đóng). 67 % leg / 64 % PnL A nằm trong [ONSET−6h, EXH). Leg SAU_EXH có roi thấp nhất và CI chứa 0.
- Theo đợt COIN của chính symbol: NGOÀI 52,5 % PnL, không có θ 20,7 %, TRƯỚC 10,9 %, TRONG 12,0 %, SAU_EXH 3,8 % (`x14A_phase.json`).
- Mô tả post-hoc (không chấm): đợt MKT A **không** có leg X14 (97 đợt) có ON ret 24h −1,22 %, 72h −3,08 %; đợt có leg (87) +0,66 % / +0,23 % ⇒ gate X14 đã lọc đúng các đợt tệ.

## 4. Quy ước create_time Vision metrics (phát hiện theo (sym, ngày), không hardcode)
- 145 678 (sym, ngày) top-100: theo AMEND1 AMBIG 757 (0,52 %), bucket coin hợp lệ 99,09 %; theo luật gốc (run 1) AMBIG 7 424, hợp lệ 94,54 % (2022-01…05 chỉ 52,6 % — `taker_ls_vol` NaN ~96 % ngày 2022-01; AMEND1 ⇒ 96,4 %).
- Theo tháng (`conv_month.csv`): 2022-01…2024-02 ≈ toàn OLD; **2024-03: OLD 300 (03-01…03-03) / NEW 2 800 — đúng 100/100 symbol top-100 chuyển ngày 2024-03-04**; 2024-04…2025-12 ≈ toàn NEW. AMBIG/tháng 0–127 (cao nhất 2022-02: 127, 2025-12: 87).
- Ngoại lệ đo được (lý do cấm hardcode): **BNXUSDT NEW trước switch** 48 sym-ngày 2022-07-01…2023-01-31 (err_new 2,7e-4 vs err_old 0,62); **OLD sau switch**: AIAUSDT 42 sym-ngày 2025-10-31…2025-12-11, MAVIAUSDT 2024-09-01.
- Hàng create_time lệch lưới 5′: 32 021 / 41,9 M (0,08 %; BNXUSDT 2022-06…2023-01, TLMUSDT 2022-06) ⇒ không khớp cửa sổ/bucket ⇒ ngày toàn lệch lưới = AMBIG ⇒ NaN.

## 5. Validation
- **V1 look-ahead PASS 3/3** (2025-10-10, 2022-05-11, 2024-04-13; T* = EXH): nhân ×3 close/volume/taker (bar ≥ T*) và OI (ts hiệu lực > T*) ⇒ mọi giá trị coin + MKT với T ≤ T* giống hệt (2 151–2 270 bucket), 304–377 bucket sau T* thay đổi, ONSET/EXH không đổi; bản dựng lại không nhiễu = mkt.parquet (Δ 0) — `v1.json`.
- **V2**: ts int64 assert ở mọi bảng; lưới 288 bucket/(sym, ngày) assert ở mọi tháng. Lỗ dữ liệu (bucket MKT không hợp lệ 1 780 = 0,42 %): kline **2022-02-26/27/28** (~38 symbol không bar — MỚI phát hiện, ngoài 2 lỗ đã biết), 2022-03-07 (~8,5h n_valid ≈ 1), 2022-04-01/02 (~38 symbol), metrics **2024-02-16** (~10,5h mọi symbol); còn lại lẻ tẻ. 2022-03-01 chỉ 1 bucket MKT. Nguồn gốc các lỗ: CHƯA GIẢI THÍCH.
- **V3 tái lập độc lập**: run 1 (`v3_run1.json`) 2022-05-12, 2022-06-13 PASS (|ΔI_mkt| ≤ 2,4e-17) nhưng **2022-11-09 TRƯỢT** (|ΔI| 2,4e-8 > 1e-9; 1 bucket n_valid lệch 1): nguyên nhân = BNXUSDT 2022-11-07 toàn hàng create_time lệch lưới; pipeline coi là AMBIG ⇒ bỏ hàng biên 00:00 ngày sau, V3 làm tròn phút ⇒ OLD. Đưa quy tắc "hàng lệch lưới không dùng; ngày toàn lệch lưới = AMBIG" vào V3 (chi tiết spec, pipeline không đổi) ⇒ **V3b PASS 3/3**: |ΔI_mkt| ≤ 2,4e-17, |Δr_mkt| ≤ 2,8e-17, |Δcum60| ≤ 8,3e-17, n_valid trùng, universe tự tính từ kline thô trùng, mọi (ONSET, EXH) của pipeline trong cửa sổ có trong bản độc lập — `v3.json`.
- **V4** kiểm tay 2025-10-10 (`v4_series.csv`, `v45.json`): ΣP2 tại PEAK tính lại từ bảng coin Δ 0; top đóng góp BTC 378 M, ETH 174 M, SOL 130 M USD; nhiều alt r5 < −50 %/5′ (DOGE −0,58, ENA −1,02, ADA −0,66 log).
- **V5** Tardis ngày-01: 174 đợt có ONSET ngày-01 (166 COIN, 8 MKT). Spearman(I, LIQ_long/OIV) theo bucket trong đợt: median **0,62** (COIN) / **0,75** (MKT); ΣP2/ΣLIQ_long median ~50× (Tardis đếm thiếu ≤ 1 lệnh/symbol/giây + OI đóng tự nguyện). Mô tả.
- **V6 (thêm, ngoài prereg)**: tính lại độc lập ret 24h/4h, MAE24 và control của 5 đợt sâu nhất (code dựa V3, không import pipeline): |Δ| ≤ 4e-16 — `v6.json`.
- Tài nguyên (max RSS): build 2,49 / 2,57 GB (2 tiến trình song song), mkt 1,19, episodes 2,71, returns 1,70, score 0,54, x14 0,24, keep 1,78, V1 1,66, V3 0,98, V45 0,79 GB — đều ≤ 5 GB.

## 6. Lệch thiết kế
- Đã khai trong prereg §13 (EXCL stable/index; median 30d ngày thiếu = 0; phép phụ giá ngầm; luật hợp lệ MKT 0,85 × median 7d; cum60 log và ln(1−D); EXH trong (ONSET, ONSET+6h]; C2 = mean rank ≥ 0,6; MFE/MAE trên close 1m; cửa sổ pha X14).
- **AMEND1** (trước mọi return): phép phụ giá ngầm 10× → 3× với ≥ 144 cặp (hiệu chuẩn 0 sai / 134 109 sym-ngày mà phép taker đã kết luận).
- Sau kết quả (không đổi số pipeline): V3b thêm quy tắc hàng lệch lưới (§5); V3 chạy không `-I` (numpy ở user site); bảng mô tả post-hoc `desc.json` (theo năm, đợt có/không X14) — không dùng cho verdict.
- Lúc kiểm schema, lệnh `head` vô tình in 2 dòng printDone 2025-11-21 (kỳ B) — không dùng, đã ghi trong prereg.

## 7. Rủi ro / nghi ngờ của agent
1. **Độ phân giải 5′ là giới hạn cứng**: cascade thường gói trong 1 bucket nên "cạn" = "trễ 10′". Kết luận NO-GO là về luật EXH ở 5′, không bác bỏ khái niệm "cạn" ở 1′/giây (Vision không có OI 1′).
2. Rổ EW top-24 là giá rổ, không phải lệnh: vào ONSET là lúc thanh khoản tệ nhất (spread/impact cao hơn EXH) — lợi thế gross 0,25–0,33 % của ON có thể bị trượt giá thật ăn mất; không làm EXH thành tốt hơn nhưng làm "ON sleeve" kém hấp dẫn hơn số gross.
3. ON tự thân phụ thuộc regime (2022 −1,36 %/24h, 2023–24 dương); B dương có thể là beta thị trường tăng.
4. Đợt trong ngày cùng đợt lớn không độc lập hoàn toàn (n hiệu dụng < n đợt); CI theo đợt có thể hẹp hơn thật. Kết luận EXH < ON vững vì dấu âm ở mọi năm/biến thể.
5. ffill giá coin delist trong rổ (ít); 72h của đợt cuối B thiếu.
6. 3 lỗ dữ liệu kline + 1 lỗ metrics (CHƯA GIẢI THÍCH) ảnh hưởng mọi task dùng `~/vz_e1/raw` và `~/vz/out/metrics5m`.
7. Proxy P2 ≈ 50× thanh lý Tardis (V5) — P2 đo "giảm OI có taker bán", không riêng thanh lý.

## 8. Đề xuất cho Bước 2 (chỉ đề xuất — MASTER quyết)
- **Không** dùng luật EXH (đợi cạn) để trì hoãn/lọc vào lệnh; nếu có thì vào trong nhịp cascade (≈ thời điểm X14 đang vào) tốt hơn đợi.
- Không ưu tiên "sleeve ONSET MKT" để bù độ thưa: 97 đợt A mà X14 không vào có ON 24h −1,2 %, 72h −3,1 % (mô tả) ⇒ phần "lệnh mới" ngoài X14 là phần tệ.
- Nếu muốn thử 1 luật (prereg mới, chấm trên B mù, A chỉ dùng thiết kế): **R1 "X14 không mở leg mới trong [T_exh + 1′, T_exh + 24h) của đợt MKT"** (A: SAU_EXH roi 2,9 % CI chứa 0, 10 % PnL) — kỳ vọng cải thiện nhỏ, có thể mất PnL; **R2** proxy cạn ở 1′ chỉ bằng taker flow kline 1m (TSX 1′, không OI) để kiểm khái niệm ở độ phân giải đủ mịn.
- Dữ liệu giữ cho Bước 2: `~/claude_master/liqx_wk/s1/{mkt.parquet, episodes.parquet, ret_entries.parquet, thresholds.json, uni/, keep/icoin_YYYY.parquet (sym,T,I,r5; 413 MB)}`.
