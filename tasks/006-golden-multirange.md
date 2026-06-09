# TASK-006: Golden multi-range — thư viện range theo regime (giai đoạn 2 của golden)

- **status:** todo (làm sau khi baseline FAST gốc chốt)
- **Milestone:** Hiện thực hóa ADR-0006 (fast = thư viện range). Mở rộng tool `GoldenBacktest` (TASK-003 done).
- **Thực thi bởi:** Claude Code (**Java**, chạy trên 226).
- **Quyết định nền:** ADR-0006 (quy trình + 3 range + quy tắc chọn).

## Mục tiêu (1 câu)
Thêm thư viện 3 range regime vào `GoldenBacktest` (Crash/Bull/Recent), xác định mốc Crash/Bull bằng SỐ + user duyệt, chụp baseline riêng mỗi range.

## Scope
**Trong scope:** Java; mở rộng `GoldenBacktest` thêm profile range; phân tích để đề xuất mốc; chụp/promote baseline mỗi range.
**Ngoài scope:** KHÔNG sửa engine core; KHÔNG đổi logic backtest.

## Các bước
1. **Tìm range bằng SỐ (CỔNG DỪNG — chờ user duyệt mốc):** phân tích theo quý 2021→2026: return + maxDD (+ mật độ delist nếu lấy được) → đề xuất:
   - **Crash:** quý/cụm maxDD sâu nhất quanh 2022 (vùng LUNA tháng 5/2022, FTT tháng 11/2022).
   - **Bull:** quý/cụm return cao nhất 2023–2024.
   - **Recent:** cố định `20251001→20260430`.
   In 3 mốc đề xuất (start/end cụ thể) + DỪNG, chờ user duyệt/sửa.
2. Sau duyệt: thêm 3 profile (`FAST_CRASH / FAST_BULL / FAST_RECENT`) vào tool. Determinism check mỗi range (chạy 2 lần khớp hệt).
3. Chụp fingerprint mỗi range → `outputs/golden/`; promote `docs/golden/baseline-{range}.json` trên commit sạch (chờ user duyệt từng cái).
4. Ghi cách dùng: thay đổi vùng nào → chạy range phủ vùng đó (theo ADR-0006). Đặc biệt: **baseline Crash chụp TRƯỚC backfill** = trạng thái thiếu coin chết; sau backfill (005) chạy lại Crash → diff = impact survivorship.

## Acceptance criteria
- [ ] Mốc Crash/Bull tìm bằng số (không cảm tính) + user duyệt trước khi khóa.
- [ ] Determinism PASS cho từng range (2 lần khớp).
- [ ] Mỗi range có baseline commit trong `docs/golden/` (commit sạch, dirty=false).
- [ ] Java, SLF4J, KHÔNG System.out.
- [ ] Khác giả định → BÁO LẠI, KHÔNG bịa.

---
## (Code điền) Kết quả

## (Code điền) Phát hiện ngoài scope

## (Code điền) Quyết định phát sinh
