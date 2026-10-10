# HO26 LUCK AUDIT — kiểm "số may" holdout 2026H1 (K24+skipFull vs B0 K16)

Ngày 2026-10-10. Vai: agent AUDIT. Đối tượng: verdict `docs/result/ho26/HO26_VERDICT.md` (d0349248; scorer A b89575bf, B db4f3ce8). 0 sửa Java, 0 build, 0 Java sim trên Oracle, 0 chạm 242/shadow. Script `research/analysis/ho26_luck_audit.py`, JSON `docs/audit/HO26_LUCK_AUDIT.json`.

## PHẦN 1 — PRE-REG (commit TRƯỚC khi đo; không tune sau khi thấy số)

Đã biết trước khi viết (từ verdict, không phải đo mới): ΣPnL_S mean k24 10 229 / b0 9 590; tháng 6 ≈ 62% ΣPnL k24; T3–T4 gần như không lệnh. Không có số nào của A1–A6 đã được tính.

Chung: cửa sổ W = [2026-01-01 00:00, 2026-07-01 00:00) +07 (181 ngày). Run: `~/kaggle_sim/out/ho26-{k24,b0}-s-s<seed>` (stress in-sim 1,675%), seed ∈ {42,7,13,21,99,123,777,2024}. ΣPnL_S = Σ pnl printDone có `end` ∈ W (y scorer A). Ngày = ngày lịch +07. Cụm lệnh = nhóm dòng printDone cùng (sym, end); leg0 = dòng `start` nhỏ nhất của cụm.

### A1 — kiểm giá độc lập (Binance Vision)
- Nguồn: `data.binance.vision/data/futures/um/daily/klines/<SYM>USDT/1m/` (ĐỘC LẬP với ticker sim). Tải theo (sym, ngày UTC) cần, parse rồi xoá zip. 404 ⇒ thử tên trong `data/meta/symbol_lineage_v2.csv`; vẫn không có ⇒ "không có nguồn" (báo riêng, không tính khớp/lệch).
- Chân: mọi dòng printDone của `ho26-k24-s-s42` và `ho26-b0-s-s42` có `start` ∈ W (kiểm giá vào); có `end` ∈ W (kiểm giá thoát).
- Nến quyết định = kline Vision có open_time = `start` (đổi +07→UTC), lag 0 (CHÍNH). Chẩn đoán phụ lag −1/+1 phút (chỉ báo, không đổi chuẩn).
- Chân sập (theo Vision) ⇔ close/open − 1 ≤ −1% ở nến quyết định. Giá vào kỳ vọng = close × 1,01675 nếu sập, ngược lại close. KHỚP ⇔ |entry/kỳ vọng − 1| ≤ 1e-6. Báo % khớp, liệt kê lệch; đối chiếu cờ sập Vision với danh sách `[CRASH-PENALTY] leg sap` trong sim.out.
- Giá thoát = cột `tp` (kiểm trước: tp ≈ entry·(1+profit/100)). KHỚP ⇔ low·(1−1e-6) ≤ tp ≤ high·(1+1e-6) của kline open_time = `end`.
- Kiểm dữ liệu: (i) Vision: số phút thiếu/0/NaN trong các ngày đã tải; (ii) ticker sim (`~/kaggle_data_hpo/ticker_2026*.bin.gz`): số phút-chân thiếu giá hoặc giá 0 trong lúc chân mở (16 run stress); (iii) delist: với mọi symbol giao dịch trong W (16 run), ngày kline 1m Vision cuối cùng (S3 listing); delist trong W ⇔ ngày cuối < 2026-06-30; báo chân dính.

### A2 — phụ thuộc vài sự kiện (k24, b0; stress; 8 seed)
- Trên ΣPnL_S từng seed: (a) bỏ lần lượt từng tháng (theo tháng của `end`); (b) bỏ top-1/3/5 ngày có PnL realized (theo ngày `end`) lớn nhất; (c) bỏ đợt lớn nhất — đợt = cụm ngày có lệnh vào, tách khi ≥ 3 ngày liền không lệnh (EP_GAP 3 như scorer A), chân gán theo ngày `start`, bỏ đợt có ΣPnL lớn nhất. Báo mean, min, số seed > 0; kèm Δ k24−b0 ghép seed. Tỉ trọng tháng 6 = ΣPnL(end ∈ T6)/ΣPnL_S.

### A3 — bootstrap tuyệt đối
- r_d = return ngày MTM (181 giá trị) đúng thước scorer A (tái dùng `ho26_score_a` + cache U; tự kiểm: ROI tái lập = RESULT_A ≤ 1e-9 tương đối).
- Block bootstrap vòng (circular), block ∈ {5, 10} ngày, NREP 5000, `default_rng(20261010)`. ROI* = Π(1+r*) − 1; ΣPnL* = E0·ROI*. Từng seed; GỘP = mean 8 seed với CÙNG chỉ số block (giữ tương quan chéo seed). Báo P(ROI* ≤ 0), CI95 percentile, CI inflate (half-width × √(2 ln 2), k = 2 block).

### A4 — đối chứng ngẫu nhiên (tách thời điểm + chọn coin khỏi beta)
- Lịch: leg0 của 8 run `ho26-k24-s-*` có `start` ∈ W (mọi loại chân), giữ phút vào và notional = margin leg0. DCA KHÔNG mô phỏng (chỉ leg0).
- Tập ứng viên tại phút t: top-24 hạng S1 (bins `~/claude_master/1009/ho26/bins2026Ax/predict_wf_2026*.bin` = bins bundle sim-ho26a; sp = 1 − p0, bỏ NaN, sort tăng, mốc 15m gần nhất ≤ t và t − mốc ≤ 15'); không có ⇒ universe = symbol có close ticker sim tại t. Coin rút đều; nhiều leg0 cùng phút rút không lặp; coin không có close tại t ⇒ rút lại (≤ 50 lần). Không loại coin "đang giữ".
- Thoát = proxy `qsleeve_q0` (hàm `seg`: arm +7%, trail GAP 3%/STEP 0,5%, time-stop 168h, không DCA/funding/SL cứng), vào ở close ticker sim của nến quyết định; chi phí 0,1116% notional + 1,675pp nếu nến quyết định close/open−1 ≤ −1%. Chân chưa thoát tới 2026-06-30 23:59 +07 ⇒ đánh dấu theo close phút đó. PnL = notional × (px/E − 1 − phí).
- Thống kê CHÍNH: S_real = Σ_8seed Σ_leg0 PnL proxy với COIN THẬT (cùng proxy ⇒ cùng mô hình thoát). Đối chứng C1 "cùng phút, coin ngẫu nhiên": 1000 lần; C2 "phút ngẫu nhiên": cùng số leg0 mỗi seed, phút rút từ pool 4000 phút đều trong W (cố định, seed 20261010), coin ngẫu nhiên top-24, notional = hoán vị notional thật; 1000 lần. p một phía = (1 + #{S_ctrl ≥ S_real})/1001; k = 2 đối chứng (báo cả ngưỡng Bonferroni 0,025). Kèm: p từng seed; ΣPnL_S thật (sim, có DCA) chỉ để tham chiếu.
- Phân rã: beta ≈ mean C2; giá trị thời điểm ≈ mean C1 − mean C2; giá trị chọn coin ≈ S_real − mean C1.
- Hiệu chuẩn proxy 2026: pearson + lệch TB (pp) giữa proxy gross và `profit` printDone trên leg0 KHÔNG-DCA (cụm 1 chân) của 8 run k24-s.

### A5 — độ nhạy phí in-sim
- 8 kernel `aud26-k24-p267-s<seed>`: override y hệt `ho26-k24-s-*` trừ SIM_CRASH_ENTRY_PENALTY=0.0267; bundle sim-ho26a-bundle, jar sim-jar-nsel (b7c89f09), SIM_END_DATE=20260701, kernel = template `tools/kaggle_sim.py` HEAD (guard NOWRITE). Orchestrator `~/claude_master/1010/aud26/aud26_queue.py` (≤ 2 kernel toàn tài khoản, kiểm API trước mỗi lần đẩy). Parity tự động như ho26_queue (ok, jar, override, t26 181/181, pred md5, `[CRASH-PENALTY] SUMMARY penalty=0.0267`).
- Chấm: ΣPnL_S cửa sổ (end ∈ W), n, số seed > 0; Δ ghép seed vs `ho26-k24-s` (1,675%). Lưu ý: penalty áp từ 2021 ⇒ vốn đầu 2026 khác; báo kèm ROI realized = ΣPnL_S / (equity_start + Σ pnl end < T0).

### A6 — bối cảnh thị trường (Vision)
- Nguồn: `futures/um/monthly/klines/<SYM>/1h/` 2022-01 → 2026-06 (+ `1mo` để xếp hạng khối lượng). Top-50: mỗi tháng M, 50 symbol USDT-perp (loại stable: USDC, BUSD, TUSD, FDUSD, USDP, DAI) quote volume lớn nhất tháng M−1. Chỉ số EW: return giờ = mean return giờ các thành phần có giá ở cả 2 giờ.
- Cho BTC, ETH, EW50: return, maxDD (trên chuỗi giờ), số ngày (+07) return ≤ −5%, số giờ return ≤ −3% và số "đợt sập" = cụm giờ ≤ −3% gộp khi cách nhau < 24h — theo tháng. So 2026H1 với từng nửa năm DEV 2022H1…2025H2 (hạng 2026H1 trong 9 nửa năm) và mật độ /30 ngày.

### A7 — luật kết luận (khai trước)
- (a) EDGE vượt đối chứng: p(C1) < 0,025 VÀ p(C2) < 0,025.
- (b) PHỤ THUỘC SỰ KIỆN nếu bất kỳ: bỏ tháng 6 ⇒ mean ΣPnL_S(k24) ≤ 0 hoặc < 6/8 seed > 0; bỏ top-3 ngày ⇒ mean ≤ 0.
- (c) BETA: mean C2 > 0 và S_real − mean C2 < 50% S_real.
- Mức tin cậy: CAO nếu (a) và không (b), A3 gộp P(ROI ≤ 0) < 5% (block 10), A1 ≥ 99% khớp, A5 ≥ 6/8 seed > 0; THẤP nếu không (a) hoặc (b); còn lại TRUNG BÌNH.
