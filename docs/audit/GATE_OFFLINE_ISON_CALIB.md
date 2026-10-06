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

## 4. Phát hiện: K40 KHÔNG đạt được iso-740

- K40 iso-740 hội tụ về pct→0,999999 (kẹt trần bisect [0,99980; 0,999999]) mà est_n vẫn **779,7** (dev +5,36%).
- **Diễn giải:** ở K40, số pass tối thiểu (khi q_t → max r của cửa sổ 90 ngày) vẫn cho ~780 lệnh/năm > 740. Tức K40 **không thể** đưa về iso-740 bằng cách siết pct — nó sinh thừa lệnh ngay cả ở gate gần đóng, vì nhiều ứng viên hơn/phút ⇒ nhiều sự kiện r cực trị hơn.
- **Hệ quả cho frontier:** đường iso-740 chỉ xác định tốt ở K12/16/32 (+ nền K24). K40 nằm **trên** đường iso-740 (đã bị đẩy lên ~iso-780) — bản thân đây là 1 điểm dữ liệu: nới K lên 40 không còn giữ được iso-n, phù hợp prior H1(b) "chất lượng sau hạng 24 rơi".
- K40 iso-1000 thì ổn (974, dev −2,6%) vì target cao hơn nằm trong khả năng.

## 5. Ghi pct vào pre-reg (bắt buộc TRƯỚC Phase 1)

pct cuối cùng (làm tròn 6 chữ số) được chép vào pre-reg §4 amendment. K40 iso-740 giữ pct=0,999999 + ghi chú "floor ~780, không iso-740" (không đổi arm sau khi thấy số; đây là ghi nhận khai trước của hiện tượng).

## 6. Bước tiếp

P0.b (RANKBAND K48, 1 kernel Kaggle) → Phase 1 (8 kernel frontier, seed 42) → Phase 2 (3 seed) → Phase 3 (H2 tách K_buffer, cần Java).
