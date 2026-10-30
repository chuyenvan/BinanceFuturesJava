# HO2026_NOTF_A0PC — cổng A0'(c): chain hạ nguồn với X = ∅ phải tái lập `ho4p1-chain-y26` (2026-10-30)

Thiết kế chốt trước khi đọc kết quả: `docs/prereg/PREREG_HO2026_NOTF_ADDENDUM_TECH-4.md` §T7.
Kernel: `chuyendinh/a0p3-chain-y26nox` (1 kernel; chain y26, `exclude_syms=[]`, `exclude_md5=md5("\n")`,
`q_src = ho4p1-x26-q1/q2/q3` gốc). Chạy 594 s, `CHAIN_RC 0`.

## KẾT QUẢ: **PASS**

| seed | pred md5 (A0'(c)) | pred md5 (`ho4p1-chain-y26`) | khớp |
|---|---|---|---|
| **42** | `b692f1346936a6368ccc1d19619bef4a` | `b692f1346936a6368ccc1d19619bef4a` | ✔ |
| 7 | `bcf5689811bd2487cf14b29ced15654d` | `bcf5689811bd2487cf14b29ced15654d` | ✔ |
| 13 | `1a2a910b29422c17052308cff7479e83` | `1a2a910b29422c17052308cff7479e83` | ✔ |
| 21 | `8445683e2b4de722a3f4c6afe375cf91` | `8445683e2b4de722a3f4c6afe375cf91` | ✔ |
| 99 | `812e3a123c55e7d69e0d9067162ef4e9` | `812e3a123c55e7d69e0d9067162ef4e9` | ✔ |
| 123 | `abeb61138a2974c05ff0d3b76ce73866` | `abeb61138a2974c05ff0d3b76ce73866` | ✔ |
| 777 | `39018410013f9797dc6c1981d4498092` | `39018410013f9797dc6c1981d4498092` | ✔ |
| 2024 | `85e6f5d621e87a5900af36d9ea78a687` | `85e6f5d621e87a5900af36d9ea78a687` | ✔ |

- **0/8 seed lệch.** Tiêu chí chính (seed 42) PASS; 7 seed còn lại miễn phí vì kernel tính cả 8 seed.
- **MANIFEST: 17/17 file trùng md5** với `ho4p1-chain-y26` gốc (bins ×3, net015 ×3, feat_v2, market, s1, pred ×8, …).
- `dup_ids` giống hệt bản gốc (843–850, 8 id trùng); `exclude_ids_n = 0` (đúng: X rỗng).
- `result.json` mới: `/tmp/a0pc/result.json` (6,9 KB) — đã xoá sau khi chép số; script so sánh
  `research/ho2026_notf/a0pc_check.py`, bản gốc
  `~/claude_master/1011/ho4p1/kaggle/out/ho4p1-chain-y26/result.json`.

## Ý nghĩa

Bản `ho4p1_chain.py` đã chèn khối NOTF (`X_IDS` hợp vào `DUP_IDS`, assert id không dùng chung, `exclude_ids_n`) là
**pass-through tuyệt đối khi X = ∅**: mọi md5 đầu ra (pred từng seed + toàn bộ manifest) trùng bản gốc. Vì vậy
chênh lệch A1 vs A0 **không** đến từ thay đổi code chain, mà từ universe X bị loại — đúng giả định của
`HO2026_NOTF`. Cổng này **không** làm thay đổi (và không cần thay đổi) bất kỳ kết luận nào.

## Tài nguyên

- 1 kernel Kaggle (tổng dùng trong task: 1/8), CPU 594 s + ~40 s cài đặt.
- Tải về Oracle: **chỉ `result.json` 6,9 KB** (không tải 19 file output ≈ vài trăm MB; lấy qua URL từng file).
  Không có lần tải nào > 200 MB.
- Không ssh 242, không Binance REST/API, không sudo.
