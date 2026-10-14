# VZ EXPLORE 2024 — bộ đo sự kiện E1 (khám phá)

Ngày 2026-10-14 · `research/vz-e1` · dữ liệu `vz-*-2024` (Vision), net sau chi phí bucket EXEC + 2 chân phí (0,000982) + bản stress. Bootstrap block 5 ngày, NREP 2000, seed 20261014.

**KHÔNG gọi GO.** Mọi kết luận là khám phá trên 1 năm (2024); xác nhận phải qua `docs/prereg/PREREG_VZ_*` + `e1_confirm.py`.

## 0. Cổng T1-V
| mục | kết quả |
|---|---|
| V-a causal | PASS 120/120 |
| **V-b1 giá** (open time = s_ms, Vision) | 6709/6709 = **1.0000** → PASS |
| **V-b2 timing** (bar_ret <= -1% ⇒ trùng sự kiện E1) | trùng đúng phút 1089/3081 = **0.3535**; trùng hoặc cùng cụm 30' = **1.0000** | lý do trượt: {'quote_volume': 0, 'merge_30m_direct': 1486, 'merge_30m_chain': 506, 'other': 0} |
| V-c determinism | xem `e1_t1v_c_determinism.json` |
| V-d đếm | PASS — 66 058 sự kiện, NC 0 |

`close_M` nguồn: Vision kline 1m (open time == s_ms) via ll_h2/exec_fetch.py kl/*.npz (leadlag_add1.load_cm); ledger t_star = hour floor of t_dec, NOT the event minute

## 1. Số phép thử

**Tổng số phép thử đã tính outcome (từ sổ `docs/research/VZ_EXPLORE_LEDGER.md`): 38** (30 của T2–T6 + 8 của T9). (T2 mô tả thuần = 0; (c) H-E T9 bổ sung thống kê trên cùng dữ liệu T6 = 0 phép thử mới.) Hệ số nở CI khi xác nhận (k = 30): sqrt(2 ln 30) = 2.608; nếu tính cả k = 38: 2.696. **Cập nhật 10-14 (Q1–Q4):** + Q2 4 phép thử + Q4 8 phép thử (Q1 tính lại chi phí = 0; Q3 BLOCKED = 0) ⇒ **tổng 50** (xem §6c).

## 2. H-A (T2) — profile quanh phút sập (0 phép thử)

n = 66058 sự kiện; bảng median theo offset trong `~/vz_e1/reports/e1_t2_profile.md`.
Đọc: taker_sell_share nhảy lên mức cao ở phút sập rồi giảm dần; volume z đạt đỉnh trong ±5′; prem thường âm quanh sập; ΔOI tích luỹ. Chia C1/C2/C4 và BTC-cùng-sập.

## 3. H-B (T3) — hồi có điều kiện trên SỰ KIỆN E1

| biến thể | n | mono net60 | spread net60 [CI95] | spread stress60 |
|---|---|---|---|---|
| V1_tss_event_q5 | 66058 | 0.20 | -0.00010 [-0.00289, 0.00236] | -0.00023 |
| V2_tss_reversal_q5 | 66015 | -0.70 | -0.00235 [-0.00482, 0.00009] | -0.00239 |
| V3_doi15_q5 | 65946 | -0.30 | -0.00031 [-0.00282, 0.00238] | -0.00017 |
| V4_doi60_q5 | 65906 | -0.60 | -0.00249 [-0.00490, 0.00004] | -0.00237 |
| V5_premz7_q5 | 64590 | -0.90 | -0.00076 [-0.00343, 0.00201] | -0.00051 |
| V6_funding_q5 | 65878 | 0.10 | 0.00030 [-0.00392, 0.00407] | 0.00025 |
| V7_combo_tsshigh_doi15low_t3 | 65946 | 0.03 | 0.00078 [-0.00284, 0.00394] | 0.00057 |
| V8_combo_premlow_doi15low_t3 | 64587 | -0.32 | 0.00129 [-0.00230, 0.00479] | 0.00100 |

Ổn định theo quý (net60 spread) — 3 biến thể mạnh nhất:

| biến thể | Q1 | Q2 | Q3 | Q4 |
|---|---|---|---|---|
| V4_doi60_q5 | -0.00613 | 0.00204 | -0.00148 | -0.00348 |
| V2_tss_reversal_q5 | -0.00379 | 0.00205 | -0.00041 | -0.00510 |
| V8_combo_premlow_doi15low_t3 | 0.00511 | -0.00547 | 0.00413 | 0.00232 |

## 4. H-C (T4) — quanh giờ chốt funding

n = 367940 mốc chốt. Chi phí NC (0,0007 + 2 chân phí).
- **V1_rate_q5**: n=367940 mono=-0.50 spread(net60)=-0.00009 CI=[-0.00075, 0.00057]
- **V2_absrate_top5**: n=367940 mono=nan spread(net60)=0.00020 CI=[-0.00110, 0.00121]
- **V4_interval**: n=367940 mono=nan spread(net60)=-0.00015 CI=[-0.00046, 0.00018]
- **V3_sign_x_btcregime** net60 theo nhóm: 11=-0.00285, 12=-0.00243, 21=-0.00262, 22=-0.00284

## 5. H-D (T5) — basis lệch cực đoan

n = 426790 sự kiện |prem z7| > 3 (gộp 60′/symbol).

| biến thể | n | net60 mean [CI95] | hit | dprem15 | dprem60 |
|---|---|---|---|---|---|
| V1_absz_gt3 | 426790 | -0.00250 [-0.00283, -0.00218] | 0.383 | 0.00013 | 0.00015 |
| V2_z_neg | 240556 | -0.00236 [-0.00278, -0.00195] | 0.392 | 0.00159 | 0.00167 |
| V3_z_pos | 186234 | -0.00268 [-0.00298, -0.00239] | 0.372 | -0.00175 | -0.00181 |
| V4_liq_low | 142255 | -0.00263 [-0.00283, -0.00242] | 0.350 | 0.00049 | 0.00052 |
| V5_liq_mid | 142270 | -0.00276 [-0.00310, -0.00243] | 0.388 | 0.00003 | 0.00004 |
| V6_liq_high | 142265 | -0.00211 [-0.00266, -0.00159] | 0.411 | -0.00011 | -0.00010 |
| V7_on_crash | 6020 | 0.00109 [-0.00263, 0.00441] | 0.543 | 0.00360 | 0.00368 |
| V8_off_crash | 420770 | -0.00255 [-0.00286, -0.00225] | 0.381 | 0.00008 | 0.00010 |

## 6. H-E (T6) — tuổi symbol

| nhóm tuổi | n | net60 mean [CI95] | net240 mean |
|---|---|---|---|
| 0-7d | 5206 | -0.00199 [-0.00309, -0.00098] | -0.00308 |
| 8-30d | 4987 | -0.00181 [-0.00299, -0.00053] | -0.00037 |
| 31-90d | 5779 | -0.00244 [-0.00407, -0.00080] | -0.00106 |
| >90d | 5713 | -0.00098 [-0.00319, 0.00112] | 0.00162 |
| age_unknown | 44335 | -0.00240 | — |

Drift sau niêm yết 2024 (n symbol=131): 1d mean=0.00194, 3d mean=0.03815, 7d mean=0.00618, 30d mean=0.04086

Trước khi bị gỡ (~30 ngày, 14 symbol): median 0.00000, tỉ lệ âm 0.286. **Cảnh báo survivorship.**

## 6b. T9 (MASTER 10-14) — chân EXEC × sự kiện E1 + chân trời 4h/24h

Ngày 2026-10-14 · pre-reg `research/vz/e1/configs/t9_config.json` (commit `c63031a4` **trước** khi đo) + code `research/vz/e1/e1_t9.py`. Edges quintile/tercile **lấy nguyên** từ `configs/t3_thresholds.json`. Net = `log(P_exit/P_entry) − (bucket EXEC + 2×0,000982)`, bản stress bucket 0,0023/0,0033/0,0041/0,0101. Bootstrap block 5 ngày, NREP 2000, seed 20261014.

### 6b.0 Ghép mẫu (a) — 6 709 chân EXEC chỉ ghép được 3 081

Luật pre-reg: cụm 30′ của các **phút ứng viên crash** (`e1_core.candidates`), đại diện cụm = phút đầu; chân `s_ms` thuộc cụm của nó ⇒ lấy feature của sự kiện đại diện. Kết quả **3 081/6 709** chân khớp 100 % (đúng bằng V-b2: 1 089 trùng đúng phút + 1 486 gộp trực tiếp + 506 gộp dây chuyền).

**Phát hiện (chỉ là số ghép mẫu, không phải outcome):** 3 628 chân còn lại vào lệnh ở phút có `bar_ret > −1 %` (trung vị bar_ret của 6 709 chân = **−0,91 %**) ⇒ **không phải sự kiện crash E1**. Không quy tắc cụm 30′ nào phủ đủ 6 709:

| quy tắc ghép | số chân khớp |
|---|---|
| thành viên ứng viên crash (pre-reg, đại diện cụm) | **3 081** |
| sự kiện đại diện ≤ 30′ trước `s_ms` (cửa sổ cụm) | 3 314 |
| sự kiện E1 gần nhất ≤ 30′ | 4 810 |
| sự kiện E1 gần nhất ≤ 60′ | 5 610 |

⇒ (a) chạy trên **n = 3 012–3 067** chân (sau khi bỏ NaN feature), không phải 6 709; **power còn thấp hơn** mức ±0,8 % đã dự liệu ⇒ chỉ **sinh giả thuyết**. Em **không** tự đổi quy tắc ghép sau khi thấy số.

### 6b.1 (a) 4 biến thể trên chân EXEC (feature của sự kiện E1, net đo trên chính chân)

| biến thể | n chân | mono 60′ | spread net 60′ [CI95] | spread net 240′ [CI95] | spread net **hold-to-exit** [CI95] |
|---|---|---|---|---|---|
| A1_doi60_q5 | 3 062 | −0,20 | −0,00982 [−0,04040, +0,01921] | −0,00266 [−0,02836, +0,01616] | −0,01911 [−0,10540, +0,04070] |
| A2_tss_reversal_q5 | 3 067 | **+1,00** | +0,01913 [−0,00017, +0,04262] | +0,01387 [−0,01195, +0,03963] | −0,02405 [−0,08937, +0,02691] |
| A3_premz7_q5 | 3 012 | −0,60 | −0,00848 [−0,03740, +0,02816] | −0,03402 [−0,06535, +0,00487] | −0,00007 [−0,03583, +0,03061] |
| A4_combo_doi15low_premlow_t3 | 3 012 | −0,40 | +0,01066 [−0,03281, +0,04868] | +0,02899 [−0,02667, +0,06365] | +0,00787 [−0,03735, +0,10941] |

Bản stress (bucket stress) — đổi rất ít, không đổi kết luận:

| biến thể | stress 60′ | stress 240′ | stress hold-to-exit |
|---|---|---|---|
| A1_doi60_q5 | −0,00946 [−0,04012, +0,02010] | −0,00231 [−0,02817, +0,01662] | −0,01875 [−0,10510, +0,04105] |
| A2_tss_reversal_q5 | +0,01757 [−0,00165, +0,04096] | +0,01231 [−0,01320, +0,03783] | −0,02560 [−0,09012, +0,02488] |
| A3_premz7_q5 | −0,00750 [−0,03629, +0,02859] | −0,03303 [−0,06430, +0,00569] | +0,00091 [−0,03538, +0,03202] |
| A4_combo_doi15low_premlow_t3 | +0,01010 [−0,03281, +0,04827] | +0,02843 [−0,02768, +0,06316] | +0,00731 [−0,03773, +0,10929] |

**Không biến thể (a) nào tách khỏi 0** (A2 có cận dưới −0,00017 ≈ 0). Ghi nhận duy nhất: **A2 đảo chiều taker đơn điệu +1,00 ở 60′ và +0,90 ở 240′** (cao = taker bán tăng vọt ⇒ net tốt hơn) — cùng dấu với T3 (T3 V2 spread60 = −0,00235 với edge quintile trên toàn sự kiện ⇒ khác mẫu, khác dấu ⇒ KHÔNG nhất quán, chỉ ghi nhận).

**Hold-to-exit: CÓ giá thoát thật (kèm cảnh báo nguồn).** Ledger `ll_h2` **không có cột giá thoát** (`cM`/`oM` là nến vào; `relclose` = kiểm chứng `vz_c` vs `cM`). Thời điểm thoát thật lấy từ `ll_h2/legs.pkl` cột `e_ms` (join theo `seed,row` với `leadlag_h2_legs.csv.gz`); **giá thoát lấy = Vision kline1m close tại `e_ms`**. Kiểm chứng trên 1 403 chân tháng 12: giá thoát suy từ pnl (`entry + pnl/qty`, đã trừ phí/funding) vs Vision close(`e_ms`) lệch **trung vị −0,19 %**, 89 % trong ±1 % ⇒ `e_ms` là thời điểm thoát thật. Trung vị thời gian giữ = **12,05 h**; cả 6 709 chân thoát trong 2024. Mọi chân đều đo được ở cả 3 mốc (n = 6 709/6 709/6 709 về giá); chỉ 3 012–3 067 dùng được cho chia nhóm vì feature.

### 6b.2 (b) 4 biến thể trên sự kiện E1 — 4h (240′) và 24h (1 440′)

`net_1440` tính mới đúng công thức `e1_core` (log close `ts+1 440′`/close `ts` − cost); 65 886/66 058 sự kiện có 24h (172 sự kiện 31/12 vượt sang 2025 — **không đọc 2025**, để NaN).

| biến thể | n sự kiện | mono | spread net [CI95] | spread stress |
|---|---|---|---|---|
| B1_doi60_h4 | 65 906 | −0,70 | **−0,00542 [−0,00960, −0,00136]** | −0,00530 [−0,00955, −0,00111] |
| B2_doi60_h24 | 65 906 | −0,30 | −0,00566 [−0,01282, +0,00141] | −0,00554 [−0,01277, +0,00167] |
| B3_tssrev_h4 | 66 015 | −0,30 | **−0,00399 [−0,00758, −0,00049]** | −0,00403 [−0,00767, −0,00048] |
| B4_tssrev_h24 | 66 015 | **−1,00** | **−0,01306 [−0,02254, −0,00364]** | −0,01310 [−0,02261, −0,00365] |

Đọc: **ΔOI60 cao** và **đảo chiều taker mạnh** ⇒ net 4h **xấu hơn** (CI95 không chứa 0); tại 24h tín hiệu **mạnh hơn và đơn điệu hoàn hảo** cho đảo chiều taker (mono −1,00, spread −1,31 %), còn ΔOI60 mất ý nghĩa (CI chứa 0). Chiều **âm** này nhất quán với T3 (V4_doi60 V2_tss_reversal đều âm ở 60′). **Cảnh báo k = 8**: hệ số nở CI khi xác nhận √(2 ln 8) = 2,04 ⇒ biên 4h (−0,14 % / −0,05 %) sẽ **không sống sót**; chỉ B4 (−1,31 %) là đáng để sinh giả thuyết.

### 6b.3 (c) H-E — drift sau niêm yết: thêm median, CI95, tỉ lệ dương (0 phép thử mới)

| mốc | n | mean [CI95] | **median [CI95]** | **tỉ lệ dương [CI95]** |
|---|---|---|---|---|
| 1 ngày | 131 | +0,00194 [−0,0286, +0,0318] | **−0,0493 [−0,0778, −0,0201]** | 0,340 [0,26, 0,41] |
| 3 ngày | 129 | +0,0381 [−0,0504, +0,1365] | **−0,0716 [−0,1171, −0,0293]** | 0,380 [0,29, 0,47] |
| 7 ngày | 129 | +0,0062 [−0,0717, +0,0834] | **−0,1055 [−0,1651, −0,0208]** | 0,388 [0,30, 0,47] |
| 30 ngày | 105 | +0,0409 [−0,0718, +0,1669] | **−0,1010 [−0,1866, +0,00005]** | 0,400 [0,29, 0,50] |

Đọc: **mean dương là do đuôi phải** (vài listing tăng mạnh) — nhưng **median âm và CI95 của median không chứa 0 ở 1/3/7 ngày**, chỉ **≈ 34–40 %** listing có ret dương. Bức tranh: **đa số listing 2024 trượt giá, thiểu số tăng mạnh kéo mean**. Cảnh báo survivorship như T6 vẫn giữ.

### 6b.4 Nhận xét (KHÔNG gọi GO)

- **Đáng sinh giả thuyết:** (i) **B4** — đảo chiều taker quintile cao ⇒ net 24h −1,31 % [−2,25, −0,36], đơn điệu −1,00 (sự kiện E1, n lớn); (ii) **B1/B3** cùng chiều ở 4h nhưng biên mỏng, sẽ chết sau nở CI k=8; (iii) **(a) A2** — mono +1,00/+0,90 ở 60′/240′ trên chân thật, spread +1,9 % nhưng CI chứa 0 (n chỉ ~3 067) ⇒ chỉ là gợi ý.
- **Không hỗ trợ:** A1 (ΔOI60) trên chân; A3 (prem z7) tuy 240′ −3,4 % nhưng CI chứa 0; hold-to-exit (trung vị 12 h) **không** cho thấy edge nào tách 0 ở bất kỳ biến thể (a).
- **Giới hạn mẫu (a):** 3 628/6 709 chân vào lệnh ngoài định nghĩa sự kiện crash E1 ⇒ mẫu thật chỉ ~3,0 nghìn chân, **power thấp hơn cả dự liệu ±0,8 %**.
- **KHÔNG gọi GO**, không đề xuất pre-reg xác nhận.

## 6c. Q1–Q4 (MASTER 10-14) — phí, tuổi symbol trên chân hệ, chi phí vào theo phút, H-F imbalance

### 6c.1 Q1 — giả định phí (0 phép thử mới; tính lại mọi bảng net T3–T9)
`SIM_RATE_FEE = 0,000982` là phí **KHỨ HỒI (2 chân)** và sim trừ **ĐÚNG MỘT LẦN** trên notional: `OrderTargetInfoTest.calTp`
dòng 282–283 (BUY) / 285–286 (SELL) trừ `quantity·priceEntry·RATE_FEE` một lần; `tradecore/Configs.java:103`
("đã sửa thành 2 chân"), `:185`; `docs/result/RESULT_AUDIT_PNL.md:126` ("2× mốc taker thật 0,05 %/chân × 2 = 0,001").
⇒ E1 cũ cộng `2 × 0,000982` là **đếm gấp đôi**: đã sửa (`e1_common.FEE_ROUNDTRIP`, `cost_of` cộng **một lần**), tính lại T3–T9
(`e1_recompute_costs.py`, `reports/fee_recompute.json`). **Spread nhóm bất biến** (max |Δ| ≤ 2,8e-17 ≤ 1e-9) — không đổi thước nào,
chỉ **mức** net dịch đều **+0,000982**. Thêm "Addendum 1" vào `docs/prereg/PREREG_VZ_B4.md`; **luật GO không đổi** (dựa trên spread).

Bảng kịch bản phí — net TB **sự kiện crash 2024** (đã trừ bucket EXEC thực; chỉ mô tả):

| kịch bản khứ hồi | phí | net 60′ | net 240′ | net 24h |
|---|---|---|---|---|
| sim `SIM_RATE_FEE` (đang dùng) | 0,0982 % | −0,122 % | +0,043 % | +0,251 % |
| taker/taker | 0,100 % | −0,124 % | +0,041 % | +0,249 % |
| taker/taker BNB (−10 %) | 0,090 % | −0,114 % | +0,051 % | +0,259 % |
| maker vào + taker ra | 0,070 % | −0,094 % | +0,071 % | +0,279 % |
| maker vào + taker ra BNB | 0,063 % | −0,087 % | +0,078 % | +0,286 % |
| *(bản cũ, SAI)* 2 × 0,000982 | 0,1964 % | −0,220 % | −0,055 % | +0,152 % |

### 6c.2 Q2 — lọc tuổi symbol trên 6 709 chân hệ (4 biến thể)
Tuổi lúc vào: chân khớp sự kiện E1 lấy tuổi chính xác (`sym_age_days`); chân không khớp lấy proxy (s_ms − sự kiện đầu của symbol trong 2024).
Nhóm: 0–7 = 616, 8–30 = 437, 31–90 = 669, >90 = 570, **không rõ = 4 417** (2 292 chân có tuổi).
net hold-to-exit TB: 0–7 **+3,99 %**, 8–30 +4,03 %, 31–90 +4,72 %, >90 **+6,56 %**, không rõ +3,03 %.
net 240′ TB **giảm dần theo tuổi**: 0–7 **+4,22 %** → 8–30 +3,53 % → 31–90 +2,25 % → >90 **+1,31 %**.
Loại chân ≤30 ngày (1 053 chân = 15,7 %) bỏ **17,2 %** Σ net_exit; ≤7 ngày (616 = 9,2 %) bỏ **10,0 %**; mean/leg phần bị loại
**không xấu hơn** (+4,01 % vs +3,59 %). ⇒ hệ **phụ thuộc đáng kể vào coin mới** (17 % ΣPnL) nhưng các chân đó không kém ⇒ **không GO**.

### 6c.3 Q3 — chi phí vào theo phút-trong-giờ: **BLOCKED**
File per-leg EXEC `~/claude_master/1012/exec/legs.pkl` (`exec_legs.py`) **đã bị xoá**; chỉ còn `need.json`, log và `docs/result/exec_result.json` (aggregate); cache agg/kl đã xoá. Theo yêu cầu **KHÔNG tải lại aggTrades** (Phase 2 chưa mở) ⇒ không dựng được bảng chi phí vào theo phút-trong-giờ.

### 6c.4 Q4 — H-F: imbalance tại mốc 15′ → return 4h/12h (8 biến thể)
Sự kiện: phút :00/:15/:30/:45 (active, `quote_volume ≥ 50 000`); `imb = 2·taker_buy_quote/quote_volume − 1`; `imb_dev15 = imb − TB 15′ trước`.
Outcome: log return close→+4h/+12h (bỏ nếu vượt 2024). Thước: IC Spearman cắt ngang mỗi mốc (TB) + spread quintile trên−dưới; CI bootstrap ngày (block 5, NREP 2000, seed 20261014).

| biến thể | n/mốc | IC TB [CI95] | spread quintile [CI95] |
|---|---|---|---|
| M00 4h imb | 8 778 | −0,0032 [−0,0060, −0,0002] | +0,00006 [−0,00015, +0,00027] |
| M00 4h imb_dev15 | 8 766 | −0,0034 [−0,0060, −0,0006] | −0,00010 [−0,00030, +0,00011] |
| M00 12h imb | 8 770 | −0,0006 [−0,0036, +0,0026] | −0,00000 [−0,00035, +0,00038] |
| M00 12h imb_dev15 | 8 758 | +0,0007 [−0,0022, +0,0038] | +0,00001 [−0,00038, +0,00041] |
| M15 4h imb | 35 114 | −0,0064 [−0,0083, −0,0047] | −0,00019 [−0,00030, −0,00007] |
| M15 4h imb_dev15 | 35 102 | −0,0054 [−0,0071, −0,0038] | −0,00022 [−0,00034, −0,00010] |
| M15 12h imb | 35 082 | −0,0043 [−0,0059, −0,0026] | −0,00021 [−0,00043, +0,00001] |
| M15 12h imb_dev15 | 35 070 | −0,0033 [−0,0049, −0,0016] | −0,00026 [−0,00047, −0,00004] |

Đọc: ở nhóm M15 (mẫu lớn) imbalance **có** IC âm tách khỏi 0 (nghiêng taker mua ⇒ return tới hơi giảm, mean-reversion) nhưng **độ lớn không đáng kể kinh tế**:
spread quintile chỉ **−2 đến −2,6 bps**, nhỏ hơn chi phí khứ hồi (~10 bps) một bậc; nhóm chỉ mốc :00 (M00) gần 0.
Bản gốc dùng 10 giây đầu từ trade; ở đây xấp xỉ **bar 1 phút** (giới hạn đã ghi). **Không GO**.

### 6c.5 Tổng kết Q1–Q4
- Phép thử mới: **Q2 = 4, Q4 = 8** (Q1 = 0 tính lại chi phí; Q3 = 0, BLOCKED) ⇒ sổ **38 → 50**.
- Ứng viên mới (≤2, **không GO**): (i) **tuổi symbol** — hệ lấy **17,2 %** ΣPnL từ coin ≤30 ngày và chân non **không tệ hơn** ⇒ yếu tố "listing mới" đáng mô tả, chưa phải alpha đã chứng minh; (ii) **H-F imbalance** — IC tồn tại nhưng **quá nhỏ so với chi phí** ⇒ loại.
- **B4** (đảo chiều taker → net 24h) **vẫn là ứng viên chính**, chờ xác nhận 2022/2023/2025 (Q6 — WAITING).

## 7. Xếp hạng ≤ 3 ứng viên (KHÔNG gọi GO)

*T2–T6: không ứng viên nào có hiệu ứng net (thực + stress) tách khỏi 0.*

**Cập nhật T9:** 3/4 biến thể (b) **tách khỏi 0** ở mốc 4h/24h trên sự kiện E1 (B1 −0,54 %; B3 −0,40 %; B4 −1,31 %), chiều **âm** và cùng dấu với T3. Nhưng: (i) đây là khám phá 1 năm (2024); (ii) biên 4h sẽ chết sau nở CI k = 8 (2,04); (iii) (a) trên chân EXEC **không** tái lập được hiệu ứng với power thấp. ⇒ vẫn **KHÔNG gọi GO**; chỉ **B4 (đảo chiều taker → net 24h âm)** là ứng viên để sinh giả thuyết.

## 8. Giới hạn

- 1 năm (2024) — không dùng để chốt GO; chưa có 2022/2023/2025 trong lake.
- **Không có dữ liệu thanh lý thật** (Vision không có liquidationSnapshot cho UM) ⇒ ΔOI chỉ là proxy.
- metrics 5′ (không phải tick); giá là kline khớp lệnh Vision.
- `vz-symbols` chưa upload ⇒ tuổi symbol suy từ 2024 (cột `age_known`); symbol niêm yết trước 2024 không đo được tuổi chính xác.
- Không có lookback 30 ngày cuối 2023 (`vz-basis1m-2023` chưa có) ⇒ `prem_z7` NaN ~1 ngày đầu tháng 1.
- **Liên kết với chân của hệ**: đã xác minh ở mức GIÁ (V-b1 = 100% khớp 1e-6) và CẤU TRÚC (V-b2: 100% phút sập của chân nằm trong cùng cụm 30' của một sự kiện E1). Tuy vậy mọi hiệu ứng ở trên đo trên SỰ KIỆN E1, KHÔNG dùng chân EXEC làm mẫu.
- **T9 — mẫu (a) chỉ 3 081/6 709 chân**: 3 628 chân vào lệnh ở phút `bar_ret > -1 %` (trung vị -0,91 %) nên KHÔNG phải sự kiện crash E1; không quy tắc cụm 30′ nào phủ đủ (tối đa 3 314 với cửa sổ 30′, 4 810 với "gần nhất ≤30′"). ⇒ (a) có n = 3 012–3 067 chân.
- **T9 — hold-to-exit**: ledger `ll_h2` **không có cột giá thoát**; đã dùng thời điểm thật `e_ms` (ll_h2/legs.pkl) + Vision close(`e_ms`), kiểm chứng lệch trung vị -0,19 % (đã trừ phí/funding). Vẫn là bước suy diễn thêm, không phải giá thoát ghi sẵn trong ledger.
- **T9 — 24h**: 172/66 058 sự kiện (31/12) không có 24h vì `ts+1440′` rơi vào 2025 (KHÔNG đọc 2025) ⇒ n = 65 886.

## 9. Tệp

- `~/vz_e1/out/`: `e1_events_2024.parquet`, `e1_panel_2024.parquet`, `e1_dayvol_2024.parquet`, `e1_t4_funding_events.parquet`, `e1_t5_basis_events.parquet`, `e1_listing_drift.parquet`, `e1_month_snap.parquet`, `e1_sym_life_2024.parquet`, **`e1_t9_legs_2024.parquet` (6 709 chân × feature/net), `e1_t9_events_net1440.parquet`**.
- `~/vz_e1/reports/`: các JSON ở trên + **`e1_t9.json`, `e1_t9_measure.json`**.
- Log: `~/vz_e1/logs/e1_t9.log`; log chạy: `/tmp/t9_measure.log`.
