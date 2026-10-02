# PREREG_SHORT_V3_R1C — lớp EXECUTION của fade (TAKER vs LIMIT +0,7% maker × TS 24h/48h)

Ngày 2026-10-02 · research engineer (agent) dưới MASTER Claude · nguồn: `docs/research/PROGRAM_SHORT_V3.md` ADDENDUM 2 (commit `985044ba`).
Chốt TRƯỚC khi đo. Trigger, exit nhánh B, luật GO chép NGUYÊN từ PROGRAM; phần "quy ước" chỉ cụ thể hoá cách tính (fill, funding, CI, cửa sổ DEV).
Không thêm ô, không thêm δ, không lọc thêm. Sau khi thấy số: KHÔNG đổi gì trong file này.

## 1. Chép nguyên PROGRAM ADDENDUM 2
> ## ADDENDUM 2 (2026-10-02, sau R1b/R2b NO-GO) — R1c: lớp EXECUTION của fade (vòng cuối trên dữ liệu hiện có)
> R1b `f4bfba27`: 13 feature tại t không tách continuation (SL-rate ~28% mọi tercile, IC OOS 0,019). R2b `53a2479f`: listing NO-GO dưới chuẩn 1m.
> Phần còn lại chưa chạm ở R1: (i) phí taker 0,112% RT ăn 35% gross; (ii) entry tại close t+1 = đúng điểm spike; (iii) mean nhánh B tăng theo TS (4h→24h).
> ### R1c — 2×2 ô KHÓA (k=4, inflate √(2 ln 4)=1,67), cùng trigger R1 (n=10 991), cùng exit nhánh B (arm 5%, gap 3%, SL +10%)
> Entry E ∈ {TAKER: short tại close t+1, phí vào 0,056% (nửa RT R1) ; LIMIT: đặt sell limit tại close_t × (1+δ), δ = 0,7%, hiệu lực 15 phút (t+1..t+15), fill khi high_1m ≥ giá limit (fill tại giá limit), phí vào MAKER 0,02%; không fill ⇒ không lệnh (ghi fill-rate)}.
> Time-stop TS ∈ {24h, 48h}. Phí ra taker 0,056% mọi ô. Funding exact. Slippage: cột stress −0,10%/lệnh (ghi cả raw & stress).
> Lưu ý so sánh: ô LIMIT có tập lệnh con (chỉ lệnh fill) ⇒ báo thêm ô TAKER trên ĐÚNG tập con fill để tách "chọn lệnh" khỏi "giá vào".
> GO-R1c ⇔ ≥1 ô: net > 0 ngoài CI raw & inflate; ≥3/4 năm; n ≥ 1500; SL-rate ≤ 25%; stress −0,10% > 0; đối chứng LONG cùng ô ≤ 0.
> NO-GO ⇒ ĐÓNG short trên dữ liệu hiện có (20 vòng pre-reg); giữ R1 như "tín hiệu mỏng có thật" để kiểm forward khi có fill thật/L2.

## 2. Tập trigger + cửa sổ DEV
- Trigger = đúng tập R1 sau cooldown (`~/claude_master/1002/r1_cache/trades_r1.csv`, n = 10 991; R1 `3fea4f50`, prereg R1 `a58f9929` §3). KHÔNG tính lại trigger.
- Cửa sổ 48h + 15' phải kết thúc ≤ 2025-12-31 23:59 UTC (2026 không đọc): giữ trigger có t + 15 + 2880 ≤ phút 2025-12-31 23:59 UTC
  (⇒ trigger cuối ≤ 2025-12-29 23:44 UTC). Áp dụng CHUNG cho cả 4 ô short, 2 ô tập-con, 4 ô LONG (cùng tập). Báo số trigger bị loại so với R1.
- Dữ liệu: Aerospike `test.kline_1m_opt` [O,H,L,C,V] (như R1 §2), stream theo tháng của t, buffer [đầu tháng − 2, cuối tháng + 2896] ∩ DEV,
  chỉ giữ cột các symbol có trigger trong tháng. Phút thiếu = NaN; `Cf` = close forward-fill trong buffer. 3 proc như R1. Lock `oracle_heavy.lock`.
- Funding: `/tmp/fund_cache.npz` như R1 (fundingTime thật, kỳ 8h/4h/1h).

## 3. Quy ước (bổ sung, khoá)
Exit nhánh B: a = 5%, g = 3%, s = 10%; thuật toán first-hit 1m y hệt R1 prereg §3 (mức stop phút j tính từ dữ liệu đến j−1; chạm khi H_j ≥ level
(short) / L_j ≤ level (long); fill = max(level, O_j) (short) / min(level, O_j) (long); runmin/runmax cập nhật SAU kiểm tra; phút thiếu bỏ qua).
### Entry TAKER (short)
P = C[t+1] (assert = P của R1). Đường giá exit j = t+2 … t+1+TS; không chạm ⇒ TIME tại Cf[t+1+TS]. entry_ms = (t+2)·60000 − 1.
Phí vào 0,056% + phí ra 0,056% (= 0,112% RT như R1 ⇒ ô TAKER-24h PHẢI tái lập R1 S_B24 trên cùng tập).
### Entry LIMIT (short)
Giá limit Lp = C[t] × 1,007 (chỉ dùng close phút t, assert C[t] = `c_t` cache R1). Kiểm fill từ phút f = t+1 đến t+15 theo thứ tự: fill tại phút đầu tiên
có H_f ≥ Lp (H hữu hạn). Giá fill = Lp kể cả khi O_f ≥ Lp (maker không được giá tốt hơn). Không phút nào chạm ⇒ không lệnh.
Sau fill: P = Lp; exit nhánh B tính từ phút fill:
- phút f (phút fill): CHỈ kiểm SL cứng: nếu H_f ≥ Lp·(1+s) ⇒ thoát SL tại đúng mức Lp·(1+s) (vì giá phải qua Lp trước khi lên H_f nên đỉnh xảy ra
  SAU fill ⇒ SL chắc chắn chạm; không dùng O_f vì open trước fill). L_f KHÔNG dùng để cập nhật runmin (low có thể xảy ra trước fill ⇒ bảo thủ).
- phút j = f+1 … f+TS: thuật toán R1 với runmin₀ = Lp; không chạm ⇒ TIME tại Cf[f+TS]. TS tính từ phút fill.
- entry_ms = f·60000 (đầu phút fill; khoảng funding mở bên trái ⇒ sự kiện settle đúng mốc đầu phút fill KHÔNG tính, vì fill xảy ra sau mốc).
Phí vào MAKER 0,02% + phí ra taker 0,056% = 0,076% RT.
### Đối chứng LONG (mirror, 4 ô)
LONG-TAKER: long tại C[t+1], exit B đối xứng như R1 (arm khi runmax ≥ P(1+a) ⇒ level = runmax(1−g), ngược lại P(1−s)), phí 0,056+0,056.
LONG-LIMIT: buy limit Lp = C[t] × 0,993, fill phút đầu tiên f ∈ [t+1, t+15] có L_f ≤ Lp, giá fill = Lp; phút fill chỉ kiểm SL L_f ≤ Lp(1−s)
(fill tại mức), H_f không dùng cập nhật runmax; từ f+1 thuật toán đối xứng; phí 0,02+0,056. Tập lệnh LONG-LIMIT = tập fill của buy limit (khác tập short).
### Funding + net
F = Σ rate các sự kiện funding của coin có fundingTime ∈ (entry_ms, exit_ms], exit_ms = (j_exit+1)·60000 − 1; short nhận +F (rate>0 ⇒ short nhận), long −F.
Coin không có trong store ⇒ F = 0 (báo tỉ lệ). net = gross − phí_vào − phí_ra + F_side. Stress = net − 0,10% mỗi lệnh.
### Ô
Chính (k = 4, GO-eligible): S_TK24, S_TK48, S_LM24, S_LM48. Tập-con (CHỈ báo cáo, không GO): S_TKsub24, S_TKsub48 = ô TAKER tính trên đúng các trigger mà
SHORT-LIMIT fill. LONG: L_TK24, L_TK48, L_LM24, L_LM48 (đối chứng G6 của ô short cùng tên).

## 4. Thống kê + luật GO
- Theo ô: n, net mean/median, win% (net>0), SL-rate (lý do SL = chạm SL cứng khi chưa arm, kể cả SL phút fill), TRAIL/TIME rate, held mean,
  gross mean, funding mean, tail (min, p1), stress mean (net − 0,10%), theo năm UTC của entry_ms (mean, n, số năm dương 2022..2025).
- CI: block bootstrap theo lệnh, block = floor(entry_ms / 72h), lấy lại block có hoàn lại, thống kê Σsum/Σcount, NREP 2000, seed 20260905, phân vị
  2,5/97,5 = CI raw. CI inflate: nửa-độ-rộng mỗi phía × 1,67 (= √(2 ln 4), k = 4) quanh mean (cùng cách R1 dùng 1,89).
- Fill-rate LIMIT = n fill / n trigger (tổng + theo năm), phân phối phút fill (f − t), tỉ lệ fill tại phút có O_f ≥ Lp.
- GO-R1c ⇔ ≥1 ô CHÍNH thoả TẤT CẢ: (G1) mean > 0 VÀ CI raw lo > 0 VÀ CI inflate lo > 0; (G2) ≥3/4 năm mean dương; (G3) n ≥ 1500;
  (G4) SL-rate ≤ 25%; (G5) stress mean (net − 0,10%) > 0; (G6) LONG cùng ô (cùng E, cùng TS) mean net ≤ 0.
- "Ô tốt nhất" (báo theo năm) = ô đạt GO có mean cao nhất; không ô nào đạt ⇒ ô chính có mean cao nhất (chỉ báo cáo).
- Đọc "chọn lệnh vs giá vào" (chỉ báo cáo): LIMIT − TAKER(toàn tập) = [TAKERsub − TAKER] (chọn lệnh) + [LIMIT − TAKERsub] (giá vào + phí;
  phần phí cố định = 0,112 − 0,076 = +0,036%). Adverse selection: so SL-rate LIMIT và TAKERsub với TAKER toàn tập.

## 5. Sanity bắt buộc (PASS trước khi báo cáo)
(S1) Tái lập R1: trên tập sau khi loại trigger cuối 2025, S_TK24 mean khớp R1 S_B24 mean cùng tập ±0,005%; thêm: per-trade |Δnet| < 1e-6, phút exit
     và lý do exit trùng 100% với `S_B24_k/_r` R1; tương tự L_TK24 vs R1 `L_B24`.
(S2) 10 lệnh SHORT-LIMIT mẫu (seed 20260905): in sym, t UTC, C[t], Lp, H các phút t+1..t+15, phút fill, O_f, kết quả S_LM24 — kiểm tay fill.
(S3) Causal: assert Lp chỉ từ C[t]; vòng fill chỉ đọc phút ≥ t+1 và ≤ t+15; exit chỉ đọc phút ≥ f; test nhiễu: thay dữ liệu > t bằng rác cho ≥ 200
     trigger ⇒ Lp không đổi; thay dữ liệu > f+TS bằng rác ⇒ kết quả exit không đổi.
(S4) Vectorized vs loop thuần (tháng thử): exit 8 cấu hình (4 short + 4 long) trên mọi trigger tháng thử ⇒ |Δpnl| < 1e-9, phút/lý do trùng.
Chạy thử 1 tháng (2024-03) trước (thời gian + sanity), rồi full 48 tháng (3 proc).

## 6. Giới hạn đã biết (ghi trước)
- Queue position maker CHƯA mô hình: fill khi H_1m chạm đúng Lp là LẠC QUAN (thực tế cần giá xuyên qua Lp/đủ volume ở mức đó; lệnh chạm-vừa-đủ thường
  không khớp hết). Fill-rate và net LIMIT là CẬN TRÊN. Không có L2/trade data để kiểm.
- Slippage TAKER tại spike chưa mô hình ngoài cột stress −0,10%. Không giới hạn vốn/đồng thời.
- Script: `research/analysis/short_v3_r1c_exec.py` → `docs/result/RESULT_SHORT_V3_R1C.json` + `.md`; per-trade CSV ở `~/claude_master/1002/r1c_cache/` (ngoài repo).
