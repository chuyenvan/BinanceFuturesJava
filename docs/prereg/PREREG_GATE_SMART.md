# PREREG_GATE_SMART — gate "thông minh hơn" cho crash-buy (ứng viên v1.3) — MASTER duyệt 11-03 (2026-11-03)

Trạng thái: PRE-REG (MASTER duyệt 11-03), commit TRƯỚC mọi phép đo. Không đổi gì trên v1.1/v1.2 trước go-live D (~11-26). Mọi biến thể là ứng viên v1.3.
Người viết: agent Opus. Code (nếu tới Pha 1): Opus viết, có unit test + key OFF byte-identical; claw KHÔNG viết code (chỉ được giao đẩy/chờ kernel nếu MASTER muốn).

## 0. Những gì ĐÃ BIẾT khi viết (khai báo trung thực — prereg viết SAU khi thấy dữ liệu)
- Cơ chế: r = p15/(max(0,26787, sp/0,15·1,2876)·1,55); q_h = phần tử k=floor(0,999950829·(m−1)) của r trong [h−90d, h), tính đầu mỗi giờ
  (`GateRatioBuffer.computeQ:72-82`), sim = live (cùng lớp). K24 + skipFull; coin giữ không nạp (sim; live sửa ở 4h).
- Gate p15 = edge: null theo khối 30d CAGR ~12,7 vs ~34 (gate_1004); RULE/NOCAL/H60/bagging/K-frontier/K32/GATE_VZ/ENTRY_CONFIRM/MKT_UP/UP_TRIG đều NO-GO.
- 2022 ≈ 0 và là nguồn phương sai seed (quota tiêu khi sổ đầy 05/2022 → skipFull sửa); EDGE_ATTR: β alt 0,85, α +2,35 %/lệnh, điểm yếu = regime.
- GATE_STAB M (026bb92c, DEV 8 seed nt-x14): 83–92 đợt burst/seed; q sau burst ×1,023–1,029 median, p90 ×1,07–1,11; 143–193 lệnh mới bị
  chặn/seed/4 năm (51 % trong 5 đợt ở A1); lệnh vào trong 24h sau burst PnL/leg 13–28 vs trong burst 29–37 ⇒ KHÔNG có bằng chứng "miss đẹp".
- Shadow 10-30: q +31 % do buffer live bẩn (coin giữ giấy + TradFi + buffer 30 ngày) — lỗi parity, không phải thiết kế.
- NUP: lệnh thêm chen chỗ lệnh nền (mới 1,4–1,9 % vs mất 3,5–3,9 %). MDE GQSF ~1,4–3,3 pp CAGR22.
- GATE_STAB V1–V3 (29beac99) đã prereg, chưa chạy (MASTER hoãn).
- Hệ quả: prior là gate hiện tại gần tối ưu theo N_eff có được; prereg này phải cho phép kết luận "đóng" sớm và rẻ.

## 1. Câu hỏi
Q0: gate hiện tại có CHỌN SAI có hệ thống không (lấy lệnh xấu hoặc bỏ lệnh tốt) theo r/q, regime vol, khoảng cách tới burst, hạng, độ cũ của ngưỡng, năm?
Q1: nếu có, một biến thể ngưỡng (tham số cố định) có chọn tốt hơn ở CÙNG số lệnh (iso-count) không? native chỉ là phụ.
Giả thuyết owner "gate chưa tối ưu nên NUP ảnh hưởng nhiều": chỉ trả lời gián tiếp — iso-count không thêm lệnh nên không đụng crowd-out; native thêm lệnh
thì phải qua kiểm crowd-out §4.5. Không chạy lại NUP trong prereg này.

## 2. Pha 0 — CHỈ ĐO (Oracle, dữ liệu có sẵn, chưa đổi gate)
### 2.1 Dữ liệu
- Ứng viên: `gate_offline.build/run_g2` (cand_base.npz, pred.bin 8 seed, held = printDone `nt-x14-s*`), DEV 2022-01-01..2025-12-31 (+07).
- Lệnh: printDone `nt-x14-s*` level PREDICT_SYMBOL_TRADE, PnL leg = cột `pnl` (ròng phí sim). Ghép (phút, symbol) → ô offline (recall đã biết 0,92–0,99).
- Regime: `edge_attr/index.npz` (ALT_EW và BTC log-return theo phút) — kiểm phủ DEV trước khi đo, thiếu ⇒ ghi.
- Seed chính A1/S99/S777 (recall ≥ 0,97); 5 seed còn lại phụ.
### 2.2 Biến mô tả mỗi leg (tính tại phút vào, causal)
- B1 `r/q` (bucket: [1;1,1) [1,1;1,25) [1,25;1,5) [1,5;2) [2;∞)).
- B2 vol thị trường: RV 24h của ALT_EW và của BTC (σ log-return 1m × √1440), tercile theo phân phối DEV.
- B3 khoảng cách tới burst trước (BH = giờ ≥ 10 pass, như GATE_STAB): trong BH / (0;24h] / (24h;7d] / > 7d.
- B4 hạng selector trong phút (1–4 / 5–12 / 13–24).
- B5 độ cũ ngưỡng: tuổi của bản ghi đang quyết định q (ts của phần tử thứ k) — < 7d / 7–30d / 30–60d / 60–90d.
- B6 năm.
### 2.3 Phía "lệnh bỏ lỡ" (Pha 0b, Kaggle 1 kernel, không phải sim)
Ô hợp lệ không pass với 0,8 ≤ r/q < 1 (near-miss) và ô pass: forward return 24h và 72h từ close phút sau, trừ phí 0,2 % round-trip, kline1m Vision
(dataset `vz-kline1m-*`). Chỉ mô tả; không có exit/DCA nên KHÔNG so trực tiếp với PnL leg — so near-miss vs pass CÙNG thước forward return.
### 2.4 Thống kê
PnL/leg trung bình + trung vị; CI 90 % bootstrap theo CỤM đợt (episode = chuỗi phút pass cách nhau ≤ 3h), 2000 lần, gộp 8 seed (seed là lặp, không độc lập).
### 2.5 Dấu hiệu (signature) — quyết định Pha 1 (ghi TRƯỚC khi đo)
- S1 (ngưỡng quá thấp/cao): PnL/leg bucket [1;1,1) < 0 với CI không chứa 0, HOẶC đơn điệu tăng mạnh: PnL/leg [2;∞) − [1;1,1) có CI > 0 và ≥ 50 % mức trung bình.
- S2 (regime vol): hiệu PnL/leg tercile vol cao − thấp có CI không chứa 0 VÀ cùng dấu ở ≥ 3/4 năm.
- S3 (ngưỡng cũ): hiệu PnL/leg B5 60–90d − < 7d có CI không chứa 0.
- S4 (bỏ lỡ tốt): forward return 72h ròng của near-miss ≥ của ô pass bucket [1;1,1), CI hiệu không chứa 0 về phía near-miss tốt hơn.
- S5 (sau burst): đã đo ở GATE_STAB — KHÔNG đạt (post-burst kém hơn) ⇒ coi như S5 = FALSE.
- Không signature nào ⇒ ĐÓNG hướng, báo "gate không chọn sai có hệ thống phát hiện được với N_eff hiện có". Không chạy Pha 1.

## 3. Pha 1 — tối đa 4 biến thể, tham số CỐ ĐỊNH (chỉ chạy biến thể có signature tương ứng ĐẠT)
| Biến thể | Định nghĩa | Tham số cố định (lý do) | Signature |
|---|---|---|---|
| V-a EWQ | phân vị CÓ TRỌNG SỐ thời gian của r: w = 0,5^(tuổi/HL), q = ngưỡng mà Σw phía trên = (1−pct)·Σw; cửa sổ cắt 90d | HL = 21 ngày (≈ ¼ cửa sổ; ~6 đợt burst/HL theo GATE_STAB) | S3 hoặc S1 |
| V-b VOLN | r' = r / σ_mkt, σ_mkt = RV 24h ALT_EW (causal, cập nhật mỗi giờ, sàn = phân vị 5 % RV DEV); q trên r' | thị trường (không per-symbol) để parity đơn giản | S2 |
| V-c SEP | tách: phút đạt nếu p15 ≥ phân vị pct_m của p15 phút 90d (thời điểm), RỒI chọn hạng 1..K theo sp với factor cũ; | pct_m iso-count | S1 hoặc S4 |
| V-d BX24 | GATE_STAB V1 (29beac99) nguyên văn | đã prereg | S5 (= FALSE ⇒ KHÔNG chạy) |

Ghi chú: "z-score cross-section trong phút" (đề bài c) bị loại: trong 1 phút p15 là MỘT số chung (model market-level) nên mọi chuẩn hoá cross-section
chỉ còn thứ tự sp ⇒ bỏ hẳn thông tin thời điểm p15 = bỏ edge (null gate CAGR ~12,7). V-c SEP là phiên bản giữ thời điểm.
- **iso-count (CHÍNH) — luật cố định TRƯỚC khi xem PnL (MASTER 11-03):**
  - Hiệu chỉnh **THEO TỪNG SEED** (không dùng median): mỗi seed s có pct_s (hoặc pct_m,s) riêng sao cho tổng symbol-pass DEV 2022–2025 offline
    của biến thể = số pass DEV của B0 cùng seed (dòng `GATE-RATIO on … | YYYYQn:pass/seen` trong log sim `nt-x14-s<seed>`, cộng 2022Q1..2025Q4) ± 1 %.
    Lý do: số pass B0 khác nhau giữa seed (2 646–2 776 offline) do pred.bin; khớp từng seed giữ so sánh ghép cặp sạch.
  - Thuật toán: tìm nhị phân trên pct ∈ (0,9999; 0,99999), tối đa 40 vòng, dừng khi |Δ| ≤ 1 %; không hội tụ ⇒ ghi, biến thể đó KHÔNG chạy.
  - Chỉ dùng: gate_offline (cand_base, pred.bin), log sim (số pass), và printDone đọc `usecols=[sym,start,end,level]` (để khoá coin đang giữ).
    **Cấm mở cột pnl/profit/equity hay file MTM ở bước này.** Ghi pct_s + số pass vào `iso_pct.json` và commit TRƯỚC khi push sim.
  - Sau sim báo số pass thật; lệch > 3 % ⇒ ghi, KHÔNG hiệu chỉnh lại.
- **native (PHỤ):** pct = 0,999950829 giữ nguyên.
- Cài đặt: trong `GateRatioBuffer` dùng chung sim/live, key mặc định OFF ⇒ byte-identical (test bắt buộc); causal theo giờ như hiện tại.

## 4. Cổng GO (mỗi biến thể chạy, iso-count, so V0 = nt-x14 cùng seed)
1. Đa kiểm định: Holm trên họ = các biến thể THỰC SỰ chạy (≤ 3), α = 0,05, chỉ tiêu chính ΔCalmar MTM DEV (gvz_mtm, missing = 0).
2. ΔCalmar (hoặc ΔCAGR22) CI t ghép cặp (mức Holm) không chứa 0 VÀ ≥ 7/8 seed cùng dấu.
3. maxDD MTM median không sâu hơn V0 > 2 pp; seed tệ nhất > 3 pp ⇒ trượt.
4. HO 2026 (W9, 8 seed): mean ΔROI cùng dấu với DEV; không seed nào DD sâu hơn > 2 pp (HO chỉ 1–2 đợt sập ⇒ chỉ chặn).
5. Crowd-out (như GATE_STAB G5): ghép leg V0↔Vk theo (sym, phút); ΣPnL leg chung ≥ 0,98×V0; PnL/leg leg mới ≥ 0,75× nền; báo leg mất.
6. Khả thi live: causal theo giờ; bộ nhớ ≤ +50 MB (V-a cần top-J theo giờ có trọng số; V-b cần chuỗi RV 24h; V-c cần buffer p15 phút);
   parity: harness replay q từ buffer + đầu vào live khớp ≤ 1e-6 trên ≥ 7 ngày shadow trước khi bật.
- native: chỉ báo cáo; GO native cần thêm 4.5 nghiêm ngặt và KHÔNG thay iso-count.
- Nhiều GO ⇒ chọn ΔCalmar lớn nhất. Không thêm biến thể, không đổi HL/sàn sau khi thấy số; mọi đổi ⇒ addendum có hash TRƯỚC khi chạy lại.

## 5. Sức thống kê (nói thẳng)
N_eff ≈ 83–92 đợt/seed/4 năm; sd Δ ghép cặp tham chiếu 1–2,4 pp ⇒ MDE80 ≈ 1,4–3,3 pp CAGR22. Biến thể ngưỡng thường đổi < 10 % lệnh ở iso-count
⇒ hiệu ứng kỳ vọng < MDE là khả năng CAO. Prior: Pha 0 dừng ở "không signature" hoặc Pha 1 NO-GO.

## 6. Tài nguyên (ước)
- Pha 0a: Oracle, flock `oracle_heavy.lock`, RSS ~4 GB, ~10–20 s/seed + ghép ⇒ < 1 h máy; 1 phiên Opus viết script (~2–3 h).
- Pha 0b: 1 kernel Kaggle forward-return (kline1m Vision 2022–2025), ~2–4 h; tải về chỉ bảng tổng hợp (< 50 MB).
- Pha 1 (nếu có): code Java V-a/V-b/V-c + test ~1–2 phiên Opus; build Oracle `LIVE_IS_SHADOW_HOST=true mvn -o`, jar STUB + sec check.
  Kaggle: ≤ 3 biến thể × 8 seed DEV (iso-count) = 24 run × ~44′ / 2 slot ≈ 9 h; native thêm 24 run ≈ 9 h (tùy MASTER);
  HO 2026 chỉ biến thể qua DEV: 8 run/biến thể × ~65–110′ ≈ 4–7 h; MTM kernel ~2 h. Tổng tối đa ≈ 30 h Kaggle.
- **Ưu tiên Kaggle (MASTER 11-03): seed gate (gst_orch) > NUP4 (M2 chạy lại) > GATE_SMART.** Kernel Pha 0b chỉ push khi account < 2 kernel
  đang chạy VÀ không có `~/claude_master/locks/kaggle_priority`; GATE_SMART KHÔNG tạo cờ ưu tiên.
- Pha 0a (Oracle, < 1 h) chạy từ 11-04 qua flock. Xong Pha 0 ⇒ DỪNG, báo MASTER; Pha 1 cần MASTER duyệt riêng. Không đổi gì live trước D.

## 7. Rủi ro
Underpowered (§5); HARKing (viết sau khi thấy dữ liệu — §0); iso-count là 1 bậc tự do hiệu chỉnh; regime 2022 chi phối; mỗi biến thể là thay đổi
parity mới cho live (vừa trả giá ở 4h); xung đột lịch với NUP4/seed Kaggle.
