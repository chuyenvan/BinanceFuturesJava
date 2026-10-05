# PREREG_SHORT_V3_R1D — CONFIRMATION ENTRY (chờ W phút không đỉnh mới +0,7% rồi mới short TAKER)

Ngày 2026-10-02 · chốt TRƯỚC đo · Program `docs/research/PROGRAM_SHORT_V3.md` ADDENDUM 3 (`75dddd89`) · nguồn giả thuyết: R1c `e7c3e09d` · trigger: R1 `3fea4f50`.
Trạng thái lúc chốt: CHƯA có dòng code R1d nào chạy trên dữ liệu. Số duy nhất đã biết liên quan = số R1c (tập no-fill 2 703 lệnh, entry t+1, TAKER-24h ≈ +1,52%/lệnh;
tập fill −0,272%) — chính là nguồn POST-HOC của giả thuyết. Mọi tham số (δ = 0,7%, W ∈ {15, 30}, nhánh B, TS 24h, phí, CI) KHÓA từ ADDENDUM 3; không tune.

## 1. ADDENDUM 3 — chép nguyên văn từ `PROGRAM_SHORT_V3.md` @ `75dddd89` (kể cả dòng "nguồn giả thuyết POST-HOC")

## ADDENDUM 3 (2026-10-02, sau R1c) — R1d: CONFIRMATION ENTRY (chờ 15' không đỉnh mới rồi mới vào)
Nguồn giả thuyết (POST-HOC, ghi rõ): R1c `e7c3e09d` cho thấy tập trigger mà high[t+1..t+15] < close_t×1,007 (limit không fill, 2 703 lệnh)
có TAKER net ≈ +1,5%/lệnh, còn tập fill −0,27%. Tức edge của fade nằm ở lệnh ĐẢO CHIỀU NGAY sau spike; thông tin đó không có tại t
nhưng CÓ tại t+15 (causal). Vì giả thuyết sinh ra sau khi thấy số, bar cao hơn: bắt buộc qua CI inflate, k=2, và báo cả stress.
### R1d — 2 ô KHÓA (k=2, inflate 1,18), cùng trigger R1 (tập 10 977 của R1c), exit nhánh B (arm 5%, gap 3%, SL +10%, TS 24h tính từ entry)
Điều kiện xác nhận tại t+W: `max(high[t+1..t+W]) < close_t × (1+δ)`, δ = 0,7% (giữ nguyên R1c, KHÔNG tune); W ∈ {15, 30} phút.
Entry: short TAKER tại close t+W+1 (phí vào 0,056%, ra 0,056%); funding exact; cooldown như R1. Không điều kiện ⇒ không lệnh (ghi tỉ lệ vào lệnh).
Báo: 2 ô (net mean/median, CI raw & inflate, theo năm, SL-rate, win, n, tail, stress −0,10%); đối chứng (a) LONG mirror cùng điều kiện (low không thủng close_t×(1−δ) ⇒ long tại t+W+1) phải ≤ 0; (b) tập BỊ LOẠI (có đỉnh mới) short tại t+W+1 — kỳ vọng xấu hơn rõ; (c) "no-fill" R1c vào tại t+1 (+1,5%) để thấy phần edge mất đi do vào trễ W phút.
GO-R1d ⇔ ≥1 ô: net > 0 ngoài CI raw VÀ inflate; ≥3/4 năm; n ≥ 1500; SL-rate ≤ 25%; stress −0,10% > 0; LONG mirror ≤ 0; tập bị loại < ô chính.
GO ⇒ Pha kế: sim SỔ (vốn/size/đồng thời/MTM) + slippage từ volume 1m; sau đó engine Java (PLAN_SHORT_ENGINE). NO-GO ⇒ đóng short trên dữ liệu hiện có.

## 2. Quy ước thực thi (KHÓA)

### 2.1 Tập trigger
- Đúng **10 977** trigger của R1c (R1 10 991 bỏ 14 trigger 2025-12-30 vì t+15+2880 > 2025-12-31 23:59), lấy bằng `load_trig()` của `short_v3_r1c_exec.py`
  (nguồn `r1_cache/trades_r1.csv` + `cand_*.parquet`). Không đổi, không lọc thêm, không tính lại trigger.
- Ràng buộc DEV R1d: cửa sổ t+W+1+1440 ≤ 2025-12-31 23:59 UTC. Vì R1c đã cắt t ≤ DEV_M1 − 2895 nên mọi trigger thỏa với W ≤ 30 (t+31+1440 < t+2895)
  ⇒ dự kiến loại **0**; script assert và ghi số loại. 2026 không đọc (buffer stream ≤ DEV_M1, assert).
- Cooldown R1 áp theo trigger (tập không đổi); KHÔNG tính lại cooldown theo entry trễ. Lệnh cùng coin có thể chồng lấn tối đa ~31' (24h cooldown vs giữ ≤ 24h + 31');
  ghi số cặp chồng, không xử lý.

### 2.2 Dữ liệu
- Cache R1c (`r1c_cache/r1c_*.parquet`, `trades_r1c.csv`) chỉ có per-trade + chuỗi high/low t+1..t+15, KHÔNG có H/L/C từng phút cho t+16..t+W+1+1440
  ⇒ stream lại Aerospike `test.kline_1m_opt` bằng `stream_sel` của R1c (giá ≤ 0 → NaN), theo tháng của t, buffer [t_lo − 2, t_hi + 31 + 1440 + 1] ≤ DEV_M1.
  Cache mới `~/claude_master/1002/r1d_cache/` (ngoài repo). Funding `/tmp/fund_cache.npz` (như R1c). `trades_r1c.csv` chỉ dùng cho sanity (i)(ii).

### 2.3 Điều kiện xác nhận & entry — ô chính S_W15, S_W30
- `Lp = close_t × (1 + 0,007)` (close_t float32 từ stream, assert khớp `c_t` cache R1 ≤ 1e-6 tương đối; công thức giống hệt `lpS` của R1c).
- Điều kiện tại t+W: KHÔNG có phút j ∈ [t+1, t+W] nào có high_j hữu hạn và high_j ≥ Lp (⇔ max(high[t+1..t+W]) < Lp; W phút, KHÔNG gồm t).
  Phút thiếu dữ liệu (NaN) coi như không vượt — đúng quy ước fill của R1c ⇒ tập W=15 phải trùng tập no-fill R1c.
- Entry e = t+W+1, short TAKER giá P = close phút e. Nếu close e NaN ⇒ dùng close ffill gần nhất ≤ e (ghi số ca; dự kiến ≈ 0).
- Exit nhánh B (arm 5%, gap 3%, SL +10%) tính TỪ GIÁ ENTRY P, first-hit 1m trên H/L phút e+1..e+1440 (phút e trung hòa như chế độ "tk" R1/R1c);
  mức stop phút k tính từ dữ liệu đến k−1; cùng nến SL ưu tiên (bảo thủ: kiểm stop trước khi cập nhật min); fill gap = max(level, open phút k);
  TS 24h tính từ entry: không chạm ⇒ thoát tại close (ffill) phút e+1440. Hàm exit = `exit_vec` R1c chép nguyên logic với TS duy nhất 1440.
- Phí 0,056% vào + 0,056% ra (= 0,112% RT). Funding exact: Σ rate các sự kiện fundingTime ∈ ((e+1)·60000 − 1, (k+1)·60000 − 1] ms; short nhận +rate, long trả.
- Không điều kiện ⇒ không lệnh; tỉ lệ vào lệnh = n_ô / 10 977 (toàn bộ và theo năm).

### 2.4 Đối chứng
- (a) LONG mirror L_W15, L_W30: `Lp_L = close_t × 0,993`; điều kiện: không phút j ∈ [t+1, t+W] có low_j hữu hạn ≤ Lp_L; long TAKER tại close t+W+1;
  exit B mirror (arm +5%, gap 3%, SL −10%), TS 24h, cùng phí/funding. Phải có mean ≤ 0.
- (b) Tập BỊ LOẠI X_W15, X_W30: trigger CÓ ít nhất 1 phút high ≥ Lp trong [t+1, t+W], short TAKER tại close t+W+1, cùng exit/phí. GO cần mean X_W < mean S_W.
- (c) C_15: tập no-fill R1c (= tập điều kiện W=15) short TAKER tại close t+1 (exit B TS 24h = S_TK24 R1c) — tái lập +1,52%.
  Bổ sung CHỈ BÁO CÁO: C_30 = tập điều kiện W=30 short tại t+1. Phân rã "edge mất do vào trễ" = C_W − S_W (cùng tập lệnh, chỉ khác giờ vào).
- Tham chiếu: T_ALL = toàn 10 977 short tại t+1 (= S_TK24 R1c, +0,1697%).

### 2.5 Chấm (ô chính S_W15, S_W30; k = 2)
- net/lệnh = gross − 0,112% + funding. Báo: n, tỉ lệ vào lệnh, mean, median, win (net > 0), SL-rate (lý do SL trước TS), TRAIL, TIME, tail (min, p1, p5),
  gross, funding, held (h), theo năm (mean, n, SL), stress −0,10%/lệnh (mean + số năm dương sau stress).
- CI block 72h: khóa block = ms entry // 72h; NREP 2000; seed 20260905 (rng khởi tạo lại cho mỗi ô); percentile 2,5/97,5 của mean bootstrap;
  inflate: nửa-độ-rộng mỗi phía × **1,18** (k = 2, √(2 ln 2)). Năm = năm UTC của phút entry e.
- **GO-R1d ⇔ ≥ 1 ô S_W (W ∈ {15, 30}) đạt ĐỦ 7 điều kiện:**
  G1 mean > 0 VÀ CI raw lo > 0 VÀ CI inflate lo > 0; G2 ≥ 3/4 năm (2022–2025) mean > 0; G3 n ≥ 1 500; G4 SL-rate ≤ 25%; G5 stress −0,10% mean > 0;
  G6 LONG mirror L_W cùng W mean ≤ 0; G7 mean X_W (tập bị loại) < mean S_W. Thiếu 1 ⇒ ô gãy. Không ô nào đạt ⇒ **NO-GO ⇒ đóng short trên dữ liệu hiện có**.
- GO ⇒ (theo ADDENDUM 3) Pha kế sim SỔ + slippage từ volume 1m; KHÔNG engine trước khi có sổ.
- Cấm: thêm W/δ/TS/ô, lọc thêm, chọn ô ngoài luật trên, đổi quy ước sau khi thấy số. Nếu cả hai ô GO, "ô báo cáo" = mean cao hơn (chỉ báo cáo).

### 2.6 Sanity (bắt buộc; phải PASS trước khi báo verdict)
- (i) Tập lệnh S_W15 phải trùng tập no-fill R1c (`f_S = −1` trong `trades_r1c.csv`, 2 703). Kỳ vọng trùng 100% (cùng dữ liệu, cùng công thức Lp, cùng xử lý NaN).
  Lệch ⇒ liệt kê từng trigger + nguyên nhân (biên float H ≈ Lp / dữ liệu); lệch > 5 trigger ⇒ DỪNG, không báo verdict.
- (ii) C_15 tính lại từ stream mới phải tái lập R1c: per-trade |Δnet| vs `S_TK24_net` < 1e-6, phút/lý do exit trùng 100%, mean ≈ +1,52%;
  thêm T_ALL tái lập S_TK24 R1c (+0,1697%) trên 10 977.
- (iii) Causal assert (mỗi trigger): nhiễu O/H/L/C từ phút t+W+1 trở đi ⇒ điều kiện xác nhận không đổi; nhiễu từ phút t+W+2 ⇒ P = close t+W+1 không đổi;
  nhiễu từ phút e+1441 ⇒ kết quả exit (pnl, phút, lý do) không đổi. Mọi lỗi = 0. Thêm vec vs loop thuần (như S4 R1c): |Δpnl| < 1e-9, phút/lý do trùng 100%.
- (iv) 10 lệnh S_W15 mẫu (rng seed 20260905): in high t+1..t+15, max, Lp, P; kiểm tay max < Lp. Thêm 5 mẫu tập loại X_W15: phút đầu tiên high ≥ Lp.
- Chạy tháng thử 2024-03 (1 proc) trước; full 3 proc dưới lock `~/claude_master/1002/oracle_heavy.lock`. float32 buffer, RAM ≤ 8G.

### 2.7 Giới hạn biết trước (ghi trước khi đo)
- Nguồn giả thuyết POST-HOC (từ R1c); không có holdout ngoài DEV 2022–2025 (2026 niêm phong) ⇒ kể cả GO cũng chỉ là ứng viên, bar = CI inflate.
- Slippage TAKER chỉ có cột stress −0,10%; không mô hình vốn/size/đồng thời; 2025 chiếm > 50% trigger.
- W=15 vs W=30 lồng nhau (tập W=30 ⊂ tập W=15) ⇒ 2 ô tương quan cao; inflate k = 2 là cận dưới cho số phép thử thực tế của chuỗi R1→R1d.

### 2.8 Tái lập
`python3 research/analysis/short_v3_r1d_confirm.py scan --months 202403 --procs 1` → `scan --months all --procs 3` → `report`
⇒ `docs/result/RESULT_SHORT_V3_R1D.json` + `docs/result/RESULT_SHORT_V3_R1D.md`.
