# PREREG_ISO_RISK — Tiêu ngân sách DD 40 % của owner: bơm size / thêm entry trên nền R1 (nghỉ sau đợt)

Ngày 2026-10-18. Owner (10-18): "hạn chế DD rồi thì tăng entry/size vì hệ chấp nhận maxDD tới 40 %"; chốt DD mục tiêu **~40 %**
(MASTER đã khuyến nghị ~22 % để chừa đệm cho sự kiện chưa thấy — owner chọn 40 %, ghi nhận). Kết quả chỉ là ứng viên **v1.1**;
pilot v1 và 242/shadow KHÔNG đổi. Commit TRƯỚC khi submit kernel nào.

## 1. Nền và dữ liệu (cố định)
- Jar `sim-jar-bcd` (branch feat/burst-cooldown 38a3e3e8, sha ở `~/claude_master/1016/bcd/jar.sha256`), profile + OV_BASE như
  BURST_COOLDOWN (K24 + GATE_QUOTA_SKIP_WHEN_FULL + B0OV, profile r4_kg0_k16_f015_g155), 8 seed A1 S7 S13 S21 S99 S123 S777 S2024,
  pred/bundle như gqsf. DEV tới 2025-12-31. Chi phí vào: mode cũ (jar bcd không có key bucket) — nhất quán với OFF.
- OFF = `gqsf-*` có sẵn (P0 parity jar bcd ↔ gqsf-a1 đã PASS 10-16). Tham chiếu R1-V1 size 1 = `bcd-v1-*` có sẵn (không chạy lại).

## 2. Arm (cố định, 5 arm × 8 seed = 40 kernel)
| arm | khác OFF |
|---|---|
| B15 | SIM_F_BASE 0,0225 (size ×1,5, KHÔNG nghỉ đợt) — đối chứng "bơm size không cần R1" |
| V1S2 | R1-V1 (SIM_BURST_COOLDOWN_N 13, _MIN 120) + SIM_F_BASE 0,03 (×2) |
| V1S3 | R1-V1 + SIM_F_BASE 0,045 (×3) |
| V1S4 | R1-V1 + SIM_F_BASE 0,06 (×4) |
| V1K32 | R1-V1 + SELECTOR_RANK_TOPK 32, size ×1 — "thêm entry dưới R1" |
Trần rủi ro sẵn có (CONC_CAP_PERCOIN 15 %, ngân sách gross, leverage 1) GIỮ NGUYÊN; nếu trần chặn bớt size thì đó là hành vi thật, báo số lệnh bị chặn.

## 3. Kiểm hợp lệ mỗi run (FAIL ⇒ run VOID, không thay bằng run khác)
jar sha đúng; result ok; prof_run có đúng key arm (F_BASE/TOPK/BURST) và B0OV; log `[BURST-COOLDOWN] N=.. MIN=..` với arm V1*.

## 4. Chỉ số (giống BURST_COOLDOWN, scorer `N.arm_metrics`, MTM phút legacy)
CAGR22, maxDD MTM 2022–25 và toàn kỳ, Calmar22, UW22, lệnh/năm, ΣPnL theo năm, 2022 riêng.

## 5. Luật (chốt trước)
- E (đủ điều kiện): maxDD MTM TOÀN KỲ ≤ 40 % ở **cả 8 seed**.
- GO: E VÀ ΔCAGR22 (ghép cặp với OFF) mean ≥ +3 pp VÀ cận dưới CI hai phía 99 % (t 0,995; df 7 = 3,4995 — Bonferroni 5 arm) > 0.
- Winner: arm GO có CAGR22 mean cao nhất (hoà ⇒ Calmar22). Không GO arm nào ⇒ giữ K24+skipFull, ghi nhận.
- Xác nhận MỘT lần trên HO4 2026 (Vision, cửa sổ W9) cho winner + OFF HO có sẵn (`ho4-k24-b-*`): xác nhận nếu ROI W9 mean ≥ OFF
  VÀ maxDD W9 ≤ 40 % mọi seed. Không xác nhận ⇒ không đề xuất v1.1.
- Không thêm arm/không đổi size sau khi thấy kết quả. Arm ×4 vượt E thì loại, không nội suy.

## 6. Rủi ro đã biết (ghi trước)
- DD DEV chi phối bởi 1 sự kiện (LUNA 05/2022); ngân sách 40 % trên DEV không chừa đệm cho sự kiện tệ hơn — quyết định của owner.
- R1 chưa từng kiểm 2026; cần port live + test + shadow trước tiền thật.
- Chi phí vào mode cũ (không bucket) — mức tuyệt đối CAGR lệch ECMEAS ~1 pp; so sánh ghép cặp không bị ảnh hưởng.

## 7. Sản phẩm
`research/analysis/iso_risk_driver.py`, `docs/result/ISO_RISK.md` + `iso_risk.json`, ledger.
