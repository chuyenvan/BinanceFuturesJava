# ROADMAP — pipeline chống-leak, thực thi TUẦN TỰ (sống, cập nhật mỗi phiên)

> **Đọc file này ĐẦU TIÊN mỗi phiên.** Nó là bản đồ + luật thực thi. Luật gốc: `DATA_GOVERNANCE_PROTOCOL.md`.
> Mốc data: `configs/data_tiers.json`. Không hành động nào được làm nếu không map vào một STEP-ID dưới đây.

## 📍 VỊ TRÍ HIỆN TẠI (cập nhật: 2026-08-24)
- Pha 0 dựng tường: ✅ · Pha 1 đóng băng công thức: ✅ (FROZEN v1, sha256 738772ff…, author chuyennd).
- Pha 2 (validate máy): 🔵 MỞ — bước kế **2.0** code hoá công thức đã đóng băng.

---

## 🚧 5 GUARDRAIL (kiểm trước MỌI hành động — chống 4 kiểu hỏng)
1. **Chống lan man:** mỗi hành động phải gắn 1 STEP-ID. Không có ID → KHÔNG làm; thêm step vào bảng trước, hoặc từ chối.
2. **Chống quên:** cuối mỗi phiên cập nhật cột Trạng thái + dòng "VỊ TRÍ HIỆN TẠI". Memory `data_governance` trỏ về đây.
3. **Chống trọc sâu:** mỗi step có ô PHẠM VI + deliverable hẹp. Nếu đang lún sâu >1 tầng vào 1 file mà chưa ra deliverable → dừng, hỏi "step này còn đúng mục tiêu không?".
4. **Chống đâm xuyên pha:** artifact của pha N+1 KHÔNG được sinh khi pha N chưa đạt DoD. (VD: CpcvBatchRunner = pha 2, CẤM viết khi công thức pha 1 chưa hash.)
5. **Chống phá spec:** công thức pha 1 có sha256. Mọi lần chạy phải verify hash khớp trước khi chạy. Đổi spec = 1 dòng pre-register mới (ngày+lý do), KHÔNG sửa lén.

## Ai làm: 👤 người (Uni) · 🧭 Claude-hỗ-trợ (đọc/soi/viết công cụ, KHÔNG quyết mô hình) · 🤖 máy (chạy tự động)

---

## PHA 0 — DỰNG TƯỜNG  ✅ DoD: mốc chốt + holdout niêm phong + máy-đọc-được
| ID | Việc | Ai | Trạng thái |
|----|------|----|-----------|
| 0.1 | Chốt mốc 3 tầng | 👤 | ✅ |
| 0.2 | `configs/data_tiers.json` (nguồn chân lý) | 🧭 | ✅ |
| 0.3 | HOLDOUT 2026 sealed-by-declaration (chưa hash vì chưa build) | 👤 | ✅ |

## PHA 1 — ĐÓNG BĂNG CÔNG THỨC (trên DEV)  🔒 DoD: Phụ lục A điền đủ + sha256 + xác nhận chỉ-DEV
| ID | Việc | Ai | Trạng thái |
|----|------|----|-----------|
| 1.1 | Đọc 3 file gốc → bảng quyết định cụ thể `docs/PHASE1_DECISION_SURFACE.md` (giá trị hiện tại + 7 chỗ nhiễm/chưa-chốt) | 🧭 | ✅ |
| 1.2 | QUYẾT từng dòng (đã xong: label · 14 gene range · fitness v2 · budget mới · trailing per-coin) | 👤 | ✅ |
| 1.3 | `docs/PHASE1_RECIPE_FROZEN_v1.md` → sha256 738772ff… → KÝ chuyennd 2026-08-24 | 👤 | ✅ |
| 1.4 | Soi xong: 2 gene chết bỏ, ranh giới nhiễm nới rộng, hạn chế đã pre-register | 🧭 | ✅ |

## PHA 2 — VALIDATE TỰ ĐỘNG (chỉ máy chạm VALIDATION)  🔒 DoD: verdict PASS/FAIL + DSR + PBO, người KHÔNG thấy số per-config
| ID | Việc | Ai | Trạng thái |
|----|------|----|-----------|
| 2.0a | fitness v2 evaluateDetailedV2 (Calmar_mtm, cap 0.85, bỏ 3 phạt IS, guard <5 lệnh) | 🧭 | ✅ |
| 2.0b | trailing per-coin (TradeUtils+updateTPSL), bỏ TS_DYNAMIC_K/weak/floor | 🧭 | ✅ |
| 2.0c | budget throttle mới (managerBudget) + F_BASE/U_MAX vào Configs | 🧭 | ✅ |
| 2.0d | GENOME 14 gene + backtest→evaluateDetailedV2 + helper public | 🧭 | ✅ |
| 2.1 | CpcvBatchRunner.java + run_cpcv_validation.py (self-test PASS) | 🧭 | ✅ |
| 2.2 | Build jar (mvn, compile+package SUCCESS) → scp Oracle (jar+scripts+config) | 🧭 | ✅ |
| 2.3 | BLOCKED: build dataset VALIDATION (selector cutoff ≤2024-07-15) rồi CpcvBatchRunner+driver | 🤖 | ⬜ |
| 2.4 | Tính DSR/PBO → verdict. Report ghi rõ "VALIDATION = CẬN TRÊN (đã bị nhìn)" | 🤖 | 🔒 |
| 2.5 | PASS → mở Pha 3. FAIL → về 1.2 (giả thuyết mới); ledger cộng dồn n_trials, cửa DSR cao lên. CẤM vặn-rồi-chạy-lại trên VALIDATION | 👤 | 🔒 |

## PHA 3 — HOLDOUT, MỘT LẦN  🔒 DoD: 1 số thật trên 2026, không vặn sau đó
| ID | Việc | Ai | Trạng thái |
|----|------|----|-----------|
| 3.1 | Build pred 2026 bằng pipeline ĐÓNG BĂNG (selector cutoff ≤2025-12) | 🤖 | 🔒 |
| 3.2 | Hash-seal HOLDOUT + verify khớp §6 governance | 🧭 | 🔒 |
| 3.3 | Chạy ĐÚNG 1 config thắng trên HOLDOUT 2026, đúng 1 lần | 🤖 | 🔒 |
| 3.4 | Báo số ra sao ghi vậy. Hết. Muốn thử lại → holdout cháy, chờ data mới (rolling) | 👤 | 🔒 |

---

## 🛑 ĐIỀU KIỆN DỪNG-HỎI (gặp là dừng, không tự quyết)
- Một step cần người quyết mô hình (mọi ô 👤 ở 1.2/1.3) → Claude dừng, KHÔNG tự điền.
- Muốn làm gì đó không có STEP-ID → dừng, thêm step trước.
- Phát hiện phải sửa công thức đã hash → dừng, pre-register mới (ngày+lý do), không sửa lén.
- Kết quả VALIDATION lỡ bị người nhìn per-config → ghi nhận leak, ledger đếm, không giả vờ chưa thấy.

## DoD tóm tắt (cổng mở pha sau)
- Pha 0 → 1: có `data_tiers.json` + mốc chốt. ✅
- Pha 1 → 2: Phụ lục A đủ + sha256 + Claude soi sạch (1.4).
- Pha 2 → 3: verdict PASS (DSR>ngưỡng, PBO<ngưỡng) trên VALIDATION.
- Pha 3 → xong: 1 số HOLDOUT, đóng sổ.
