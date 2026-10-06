# GATE_OFFLINE_ISON_CALIB — P0.a: hiệu chuẩn iso-n bằng đếm offline

Ngày 2026-10-06 (GMT+7). Pre-reg `docs/prereg/PREREG_GATE_K_FRONTIER.md` §4 Phase 0.a (commit `7b899e6e`). Brief MASTER `Claude outputs/BRIEF_GATE_K_FRONTIER_20261006.md` (commit `46a1dc36`).
Thuần offline, 0 PnL, 0 Java/sim/Kaggle. Seed 42 (A1). Script `research/analysis/gate_k_frontier_driver.py` (`calibrate`); JSON `docs/audit/GATE_OFFLINE_ISON_CALIB.json`.

## 1. Validate bộ đếm offline (trước khi dùng)

`gate_offline.py` mở rộng thêm `--topk K --pct P` (commit `8a99fd9c`), sửa 1 bug: pct thấp cần `J=1024` (TopTree) — pct=0.99985 vượt J=256 cũ.

| Run tham chiếu | Cấu hình | dev pass | dev seen | ≤2%? |
|---|---|---|---|---|
| n700-a1 | K24 pct 0.999950829 | **+0,062%** | 0,10% | ✓ |
| n700-a2 | K16 pct 0.99985 | **+0,134%** | 0,095% | ✓ |
| gqsf-a1 | K24 ON (skipFull) | **−0,186%** | 0,10% | ✓ |

Pass offline (toàn kỳ) khớp sim trong <0,2%. Bộ đếm đáng tin.

## 2. Quy đổi lệnh/pass

Offline đếm symbol-pass (PREDICT); không mô hình U_MAX/budget (lệnh thật ≤ pass tháng sập — GATE_QUOTA_DIAG §D1).
- Nền n700-a1 (K24 base): n/năm = 732,2; offline symbol_pass 2022–2025 = 2653.
- **ratio lệnh/pass = 1,103958** (dùng quy đổi mọi arm, khai trước trong brief).

## 3. Kết quả hiệu chuẩn pct (seed 42)

| arm | K | target n | pct | est n/năm | dev% |
|---|---|---|---|---|---|
| iso-740 | 12 | 740 | 0,999926 | 722,8 | −2,32 ✓ |
| iso-740 | 16 | 740 | 0,999938 | 732,5 | −1,02 ✓ |
| iso-740 | 32 | 740 | 0,999981 | 739,9 | −0,01 ✓ |
| iso-740 | 40 | 740 | 0,999999 | **779,7** | **+5,36 ✗** |
| iso-1000 | 16 | 1000 | 0,999922 | 1006,3 | +0,63 ✓ |
| iso-1000 | 24 | 1000 | 0,999940 | 1001,6 | +0,16 ✓ |
| iso-1000 | 32 | 1000 | 0,999972 | 1005,4 | +0,54 ✓ |
| iso-1000 | 40 | 1000 | 0,999994 | 974,0 | −2,60 ✓ |

## 4. Phát hiện: SÀN pass (floor) tăng theo K — gate "đều lệnh" thoái hóa ở pct→1

Sweep pass count theo pct (sp4 = symbol-pass 2022-2025, est_n = sp4·ratio/4):

| pct | K24 est_n | K40 est_n | K48 est_n |
|---|---|---|---|
| 0,9999 | 1956 | 3701 | 4960 |
| 0,99999 | 169 | 1127 | 1751 |
| 0,999999 | 63 | 780 | 1305 |
| 0,9999999 | 42 | **737** | **1227** |

- **K24** tiến về 0 khi siết pct (không có sàn trong vùng khả dụng).
- **K40 dừng ở ~737, K48 dừng ở ~1227** — có **sàn cứng**, không siết xuống thêm được.
- **Cơ chế:** `fac = max(DYN_MIN, sp/SCORE_BASE·DYN_MULT)` — các ứng viên có `sp < 0,0312` đều bị kẹp `fac = DYN_MIN` (hằng số). Vì p15 là market-level (chung mọi coin trong phút), **mọi symbol hạng thấp-sp trong cùng phút có r IDENTICAL**. Khi pct→1 (q_t→max r), 1 phút p15 cực trị mở gate cho **toàn bộ** nhóm floored-fac đó cùng lúc. Số symbol floored-fac tăng theo K ⇒ sàn tăng theo K.
- **Hệ quả 1 — K40 iso-740:** đạt được CHỈ ở pct ≈ 0,9999999 (kẹt ngay trên sàn ~737), nghĩa là gate gần đóng hẳn — mất ý nghĩa "đều lệnh". Trong vùng pct bình thường, K40 sinh thừa lệnh (dev +5,36% ở pct 0,999999).
- **Hệ quả 2 — K48 iso-1000:** KHÔNG đạt được (sàn 1227 > 1000). ⇒ **P0.b cấu hình "K48 @ n≈1000" là BẤT KHẢ THI như brief viết**; K48 chỉ chạy được ở n≈1227.
- **Ý nghĩa frontier:** đường iso-740 chỉ xác định tốt ở K12/16/32 (+ nền K24). Nới K lên 32-40 đã chạm tường cấu trúc: không giữ được iso-n, và ở pct cực trị gate thoái hóa thành "mua ồ ạt đúng lúc sập" — đúng rủi ro owner lo từ đầu ("tránh vào ồ ạt").

## 5. Ghi pct vào pre-reg (bắt buộc TRƯỚC Phase 1)

pct cuối cùng (làm tròn 6 chữ số) được chép vào pre-reg §4 amendment. K40 iso-740 giữ pct=0,999999 + ghi chú "chạm sàn ~737, chỉ đạt iso-740 ở pct≈0,9999999 (thoái hóa)" — không đổi arm sau khi thấy số. K48 KHÔNG đưa vào iso-1000 (sàn 1227 > 1000); đây là ghi nhận khai trước của hiện tượng.

## 6. Quyết định cần MASTER/owner (P0.b bị ảnh hưởng)

- Brief §4 P0.b: "K48, pct = iso-n cho n≈1000". Hiệu chuẩn offline cho thấy **K48 sàn ~1227 > 1000 ⇒ không có pct nào đạt n≈1000**. Cần chọn: (a) chạy P0.b K48 ở n≈1227 (sàn) và chỉ báo rank-band, hoặc (b) đổi P0.b sang K40 (đạt ~974 gần 1000), hoặc (c) hạ mục tiêu. KHÔNG tự quyết — chờ chốt.

## 7. Bước tiếp

Sau khi MASTER chốt hướng P0.b: RANKBAND sâu → Phase 1 (8 kernel frontier, seed 42) → Phase 2 (3 seed) → Phase 3 (H2 tách K_buffer, cần Java).
