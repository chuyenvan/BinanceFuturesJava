# PREREG_TS_MKT_EXT — gia hạn time-stop 168h khi CẢ thị trường alt đang sập (K24+skipFull)

Ngày 2026-10-19 (owner "thử đi xem sao"). Commit TRƯỚC khi build jar / chạy kernel. Chỉ sim DEV; không đổi 242/shadow; không REST.

## 0. Giả thuyết và ghi nhận trung thực
- Owner: cắt 168h là chốt lỗ đúng đáy; giữ thì còn cửa cứu. Bằng chứng cũ: giữ VÔ ĐIỀU KIỆN chết (HOLDDCA, HOLDTODIE, EXIT_STRUCT).
- Chẩn đoán TS_AFTER (a684602b, hậu kiểm): chỉ khi cắt lúc ALT_EW ≤ −30 % so đỉnh 30 ngày (T1) thì giữ thêm 14 ngày có lãi thô
  +8,8k/seed (chưa tính vốn khoá). Ngưỡng −30 % và 14 ngày được chọn SAU khi xem chẩn đoán ⇒ đây là kiểm định xác nhận một giả thuyết
  sinh từ chính DEV; kể cả GO cũng chỉ là ứng viên, cần HO4 2026 trước v1.1. Kỳ vọng P(GO) ~15–20 % (hiệu ứng < MDE DEV ~16–19k).

## 1. Cơ chế (key mới, mặc định tắt ⇒ byte-identical)
- `SIM_LOSER_TS_EXT_HOURS` (int, 0 = tắt) và `SIM_LOSER_TS_EXT_DAYS` (danh sách khoảng ngày UTC `yyyyMMdd-yyyyMMdd,...`).
- Tại chỗ LOSER_TIME_STOP: cụm chưa arm, tuổi > 168h. Nếu EXT_HOURS > 0 VÀ ngày UTC của tick hiện tại thuộc EXT_DAYS VÀ tuổi ≤ 168h + EXT_HOURS
  ⇒ KHÔNG cắt ở tick này (xét lại mỗi tick). Ngược lại cắt như cũ tại min(open, close). Trailing/DCA giữ nguyên.
- Arm duy nhất **X14**: EXT_HOURS = 336 (tối đa +14 ngày).
- EXT_DAYS (nhân quả): ngày d+1 có cờ nếu chỉ số ALT_EW (cumsum log-return, `edge_attr/index.npz`) cuối ngày d thấp hơn đỉnh cuối-ngày
  của 31 ngày d−30..d từ 30 % trở lên. Kết quả: 214 ngày, 42 khoảng (2021 14 · 2022 78 · 2023 4 · 2024 51 · 2025 67),
  sha256 chuỗi khoảng `c79ef302…` (`~/claude_master/tsx/flags.json`).

## 2. Chạy
- Jar mới từ `feat/burst-cooldown` (4e4bbd37) + patch; PrivateConfig stub. Dataset `sim-jar-tsx`.
- P0: key vắng, seed A1 ⇒ md5 printDone PHẢI = `gqsf-a1`. FAIL ⇒ dừng.
- X14 × 8 seed (A1 S7 S13 S21 S99 S123 S777 S2024), profile như gqsf (B0OV + TOPK 24 + skipFull). OFF = 8 run `gqsf-*` có sẵn.
- Parity mỗi run: jar sha, key có trong profile, dòng log `[TSX]` có, B0OV đúng.
- Chấm: MTM nguồn Vision (`gvz_mtm.py`, missing = 0), `n700_driver.arm_metrics` như ISO_RISK.

## 3. Luật GO (chốt trước)
- G1: ΔCAGR22 trung bình 8 seed > 0 VÀ cận dưới CI99 (t df7, 3,4995) > 0.
- G2: ΔmaxDD22 trung bình ≥ −3pp (không sâu hơn quá 3pp) VÀ mọi seed |maxDD toàn kỳ| ≤ 40 %.
- G3: ΔΣPnL theo năm đóng lệnh (trung bình seed) dương ở ≥ 3/4 năm 2022–2025.
- G4: số lệnh/năm không giảm quá 5 %.
- GO ⟺ G1 ∧ G2 ∧ G3 ∧ G4. NO-GO ⇒ đóng hướng "giữ lệnh khi thị trường sập" trên DEV, không thử ngưỡng/giờ khác.
- Mô tả kèm: số cụm được gia hạn, PnL các cụm đó so với nếu cắt, vốn khoá thêm, UW, Calmar.
