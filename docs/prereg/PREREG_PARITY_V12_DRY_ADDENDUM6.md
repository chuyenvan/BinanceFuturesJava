# PREREG_PARITY_V12_DRY — ADDENDUM 6: deploy dry KHÔNG seed, re-seed bằng 1 lần restart (2026-11-02, trước mọi số seed)

Gốc: PREREG_PARITY_V12_DRY (3c7dae05) + ADD1 (7788cce9) … ADD5 (5ffb3402). MASTER chốt 11-02: deploy dry 11-03 không `GATE_BUFFER_SEED`
(buffer khởi đầu = `gate_ratio_live.bin` v1.1: ~9,9 % TRADFI + ~11,6 % coin giữ sổ giấy; q cao hơn bản sạch ~5 % median, tới ~28 % sau burst —
5f3de773). Chưa có seed A nào (Kaggle Q4 trượt hạ tầng: Vision không có klines daily 10-28). Không có số seed nào khi viết.

## 1. Pha trước re-seed (từ deploy tới giờ restart re-seed)
- P1, P1-m, MD, FUND, NET, S1-I, S1-m, S1-V, GV-I, GV-O, P2, P3, TSX, CTL: **chấm bình thường**. Lý do: P2/P3 replay q causal trên CHÍNH
  buffer live đọc từ 242 (v1.1 §4 P3; ADD1 §P3), nên buffer bẩn không tạo lệch giữa live và replay.
- **KPI dry và T-BOOK (so với dải backtest A1): ghi "KHÔNG SO ĐƯỢC (buffer v1.1 chưa sạch)"**, không chấm ĐẠT/TRƯỢT, chỉ mô tả.
- T-DEC chấm theo P2 (cùng q live).

## 2. Re-seed
- Chỉ dùng **seed A ∪ C đã ĐẠT V-OVL (ADD4 (i) và (ii))**, dựng bằng `build_seed.sh` sát giờ restart; md5 seed ghi trong sổ C. **Seed C′/B
  (buffer live làm sạch không có A) vẫn CẤM.**
- Cơ chế: env `GATE_BUFFER_SEED` (+ md5, max lag) → 1 restart; `applySeedFile` nạp seed + persist có ts > bản ghi cuối seed (lần đầu, chưa
  có marker). Log `[GATE-SEED]` phải có; thiếu ⇒ re-seed coi như KHÔNG xảy ra.
- **Khung giờ:** phút :10–:44, tránh 07h/19h và 12:50–13:20, 00:50–01:20 (+07); KHÔNG re-seed trong ngày có đợt sập đang diễn ra (BIG_DOWN
  hoặc GATE-RATIO pass > 0 trong 6 h trước) — dời sang khung kế tiếp.
- **P3 sau re-seed:** buffer tham chiếu đổi ĐÚNG tại giờ restart: giờ < restart dùng buffer cũ (persist trước restart), giờ ≥ restart dùng
  seed + r live sau đó (đọc file sau restart). Giờ chứa restart: chỉ chấm các giờ đủ (giờ bắt đầu sau restart).
- **Ngày restart = XÁM** (không ĐẠT, không TRƯỢT), như luật ngày restart của bản gốc.

## 3. Cửa sổ "7 ngày sạch" — tách 2 nhóm chỉ tiêu
- **Nhóm H (hạ tầng/parity: P1–P3, GV, S1, TSX, CTL, vận hành):** tính từ ngày đầu sau deploy (ngày deploy XÁM). Lý do: các chỉ tiêu này
  không phụ thuộc buffer sạch (replay theo buffer live), không cần chờ re-seed để đếm.
- **Nhóm K (KPI dry, T-BOOK, so dải backtest A1):** tính từ **ngày đầu tiên SAU ngày re-seed**. Lý do: trước re-seed q lệch có hệ thống
  so với backtest, đếm sẽ trộn hai chế độ ngưỡng.
- Dry "7 ngày sạch" ⇔ Nhóm H ≥ 7 ngày sạch VÀ Nhóm K ≥ 7 ngày sạch. Nếu seed A không có trước 11-10 ⇒ MASTER quyết (kéo dài dry hay
  chấp nhận Nhóm K mô tả) bằng addendum mới.
