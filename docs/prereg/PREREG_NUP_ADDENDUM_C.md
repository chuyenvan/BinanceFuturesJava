# PREREG_NUP — ADDENDUM C (A7: cache q2 theo giờ) — 2026-10-26

## C.1 Bug hiệu năng phát hiện khi chạy A7

Run `nup-a7-a1` (jar 66740305, code 39c98525) bị Kaggle kill ở 7200 s: `java_rc=-9`,
`n_trades=0`, `date_last=20210823` — chỉ xử lý 54 ngày trong 2 h (B0: 4,5 năm/35 phút).
Nguyên nhân: `tier2Pass` gọi `buffer.queryPctExcludingLast` cho **mỗi candidate bị reject**;
hàm này copy toàn bộ buffer (~2,7 triệu mẫu) và quickselect O(m). Với ~20 candidate/tick,
chi phí ~100×. **Không có số A7 nào được tạo** (n_trades=0), nên không có thay đổi dựa trên kết quả.

## C.2 Sửa (không đổi logic arm)

- `GateRatioBuffer.addAndQuery2`: khi **qua giờ mới**, tính q1 (pct) và q2 (pct2) **một lần**
  trên cùng cửa sổ trước-add; các candidate cùng giờ dùng cache.
- `GateRollingRatio.threshold`: nếu tier2 bật, gọi `addAndQuery2`; lưu `currentTier2Q` theo giờ.
- `tier2Pass`: chỉ so `p15` với `currentTier2Q × factor × gs` (O(1)); không đụng buffer/quota.
- Cờ TẮT: nhánh `else` gọi đúng `buffer.addAndQuery` cũ ⇒ byte-identical.

Semantics giữ nguyên: cùng buffer r, cùng cửa sổ, cùng phép q, chỉ đổi phân vị; q2 tính trên
trạng thái trước-add như q1. Unit test 8/8 PASS. Jar mới sha256 `ce4bcc17…`. Cổng A7-off chạy lại
B0 seed a1: md5 printDone phải = `dc62609b…`.

## C.3 Hệ quả

A7 (nếu sim xong) vẫn là arm §1.2, không đổi ngưỡng/seed/kỳ. Các arm A1–A6 không bị ảnh hưởng
(jar cũ cc0f9d11). Nếu A7-on vẫn không xong trong 7200 s, ghi "A7 KHÔNG CÓ SỐ" và không dùng A7
trong bảng quyết định; A1–A6 vẫn hợp lệ.
