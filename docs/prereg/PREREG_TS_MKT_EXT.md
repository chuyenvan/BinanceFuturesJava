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


---

## ADDENDUM 1 (2026-10-20) — xác nhận HOLDOUT 2026 (W9), viết TRƯỚC khi tính cờ 2026 và trước mọi run HO

Bối cảnh: arm X14 GO theo §luật trên DEV (result c1ab8eda) nhưng in-sample. Owner 10-20 duyệt chạy HO 2026 9 tháng, dùng lại dữ liệu/hạ tầng HO4.

1. **Luật đóng băng**: cờ y nguyên (ALT_EW cuối ngày d ≤ −30 % so max EOD d−30..d ⇒ cờ ngày d+1; ALT_EW = TB log-return 1m, trừ BTC/ETH, qv>0 cả hai nến, cắt ±0,5 — code `build_index`/`logret` của edge_attr_build.py), EXT_HOURS = 336. Không đổi ngưỡng, cửa sổ, giờ.
2. **Dữ liệu cờ 2026**: Kaggle `chuyendinh/vz-kline1m-2026` (+ `vz-kline1m-2025` để kiểm). Lookback đầu 2026 nối từ index DEV `edge_attr/index.npz`. Cờ chỉ lấy ngày 2026-01-01..2026-09-30 ⇒ đường đi trước 2026 trùng baseline.
3. **Baseline**: `ho4-k24-b-s{42,7,13,21,99,123,777,2024}` (phí gốc, HO4 có sẵn). Arm: `tsx-ho-x14-s<seed>` = cùng cấu hình/kernel HO4 (ho4p1_queue, unseal, end 20261001) + jar `sim-jar-tsx` (cc0f9d11) + 2 key TSX.
4. **Validate (fail ⇒ dừng, không chấm)**: V1 index Kaggle 2025-10..12 khớp index.npz (cùng ts, max|Δ| ≤ 1e-9). V2 P0 `tsx-ho-p0-s42` (jar tsx, không key) md5 printDone = ho4-k24-b-s42 `7cc8864c…`. V3 mỗi run X14: q.check đủ (jar override), có log `[TSX]`, các dòng printDone start < 20260101 trùng baseline. V4 scorer MTM HO (ecm_mtm_h / ho4_score_a, giá Vision) tái lập baseline.
5. **Không đủ sức**: nếu 2026 có 0 ngày cờ, hoặc < 6/8 seed có deferClusters > 0 ⇒ NON-INFORMATIVE (không chạy/không kết luận; trạng thái giữ "GO in-sample, HO chưa xác nhận").
6. **Chỉ số W9 (2026-01-01→10-01 +07, MTM)**: ΔPnL, ΔROI, ΔmaxDD theo seed (X14 − baseline cùng seed).
7. **Kết luận**:
   - CONFIRM: TB ΔPnL > 0 VÀ ≥ 6/8 seed ΔPnL ≥ 0 VÀ TB ΔmaxDD ≥ −1,0pp.
   - REJECT: (TB ΔPnL < 0 VÀ ≤ 3/8 seed ΔPnL > 0) HOẶC TB ΔmaxDD < −2,0pp.
   - Còn lại: INCONCLUSIVE.
8. Lưu ý trước: HO4 đã được chấm nhiều lần (không còn sạch hoàn toàn); sức thống kê thấp; kết quả không đổi được luật (không tune).
