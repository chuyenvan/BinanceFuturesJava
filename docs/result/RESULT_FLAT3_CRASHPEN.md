# RESULT_FLAT3_CRASHPEN — Kỳ vọng của B0 (G2 + FLAT3) khi PHẠT giá vào leg "sập"

Ngày: **2026-10-02**. Pre-reg: **`docs/prereg/PREREG_FLAT3_CRASHPEN.md`** (commit **`6362bd18`**, chốt TRƯỚC khi đẩy kernel; KHÔNG sửa thiết kế sau khi thấy số). Driver: `research/analysis/flat3_crashpen_driver.py`. JSON: `docs/result/flat3_crashpen.json`.
**Tuân thủ:** sim trên **Kaggle** (jar `sim-jar-crashpen` sha256 `d944bea5…` cho cả 3 arm, bundle `sim-x1-2021-bundle`, `TICKER_SOURCE=file`, `sim_end_date=20251231`, xmx 22g) · 0 sim Oracle · 0 sửa `.java`/build · không chạm 242/shadow · DEV ≤ 2025-12-30 · chấm Python offline (`nice -n 10`). Nhãn: [ĐO] = số từ artifact; [SUY LUẬN] = diễn giải.

## 0. KẾT LUẬN

> **[ĐO] Không kích cảnh báo.** Ở mức điểm **+0,69 %/chân (P1)**: Calmar_MTM 2022+ **1,735** (ngưỡng 1,2), ΣPnL **83 924 = 86,6 % B0** (ngưỡng 60 %). Kỳ vọng hạ của B0: equity 131 908 → **118 924 (−9,8 %)**, CAGR 34,31 → **31,25 %**, Calmar_MTM toàn kỳ 1,940 → **1,758 (−9,4 %)**, UW 87 → **117 ngày**. ΔPnL ghép cặp size-neutral **−7,0k, CI raw [−10,5k; −3,8k], inflate [−11,1k; −3,2k]** — âm ngoài 0, **âm cả 5/5 năm**. P1 vẫn PASS T1–T4 vs B0 nhưng **T4 sát nút** (1,758 vs 1,746; 1,735 vs 1,708).
> Ở **2× (+1,38 %, P2)**: eq 108 815 (−17,5 %), Calmar 1,610 / 2022+ 1,590 ⇒ **FAIL T4**; ΔPnL **−13,0k [−18,6k; −7,9k]**.
> **FLAT3 KHÔNG nhạy hơn G2 với phạt** (ΔCalmar −9,4 % vs −9,3 % của G2 ở cùng 0,69 %); giả thuyết "42 % ΣPnL ở lệnh 0h ⇒ nhạy hơn" **không được xác nhận**: phần 0h giảm **cùng tỉ lệ** phần còn lại (42,3 % → 42,2 %).
> Đây là stress giả định quanh mức điểm có CI [−0,19; +1,50] trên n=27 — **không** phải đo chi phí thật; không chọn/tune gì.

## 1. Cổng parity P0 — PASS

| kiểm | yêu cầu | đo `flat3-cp-p0` | kết |
|---|---|---|---|
| md5 `printDone.csv` | `650c386f0d0dfea334af9d55ca2f21d4` | `650c386f0d0dfea334af9d55ca2f21d4` | PASS |
| n / equity | 2517 / 131 908 | 2517 / 131 908 | PASS |
| jar / mapper | `d944bea5…` / ≥ 800 | `d944bea5…` / 863 | PASS |
| `prof_run.properties` vs `de-p1` | giống | `diff` = 0 dòng | PASS |

⇒ Jar E2 (khác jar B0 `7368be46` ở 2 class) với key phạt vắng tái lập B0 **byte-identical**; mọi khác biệt P1/P2 chỉ do key phạt. (`[GATE-RATIO] pct=0.99995083` trong log là định dạng in — `de-p1` in y hệt.)

## 2. Bảng chính [ĐO] — as-is (phí base 0,1116 % + phạt nằm trong artifact)

Calmar_MTM = CAGR / |maxDD MTM phút|. Toàn kỳ 2021-07-01→2025-12-30; 2022+ = CAGR từ equity 2021-12-31, DD/UW MTM reset 2022-01-01 UTC. Ngưỡng T4 = 0,90×B0: **1,746** (toàn kỳ) / **1,708** (2022+).

| arm | phạt | n | equity | ΣPnL | % B0 | CAGR % | ddMTM % | UW ngày | **Calmar** | CAGR22 % | ddMTM22 % | **Calmar22** | #leg phạt | T1 | T2 | T3 | T4 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **B0 = P0** | — | 2 517 | 131 908 | 96 909 | 100 | 34,31 | −17,68 | 87,1 | **1,940** | 33,56 | −17,68 | **1,898** | 0 | PASS | PASS | ref | ref |
| **P1** | 0,0069 | 2 494 | 118 924 | 83 924 | **86,6** | 31,25 | −17,77 | 117,3 | **1,758** | 30,85 | −17,77 | **1,735** | 1 096 | PASS | PASS | PASS | PASS (sát) |
| **P2** | 0,0138 | 2 491 | 108 815 | 73 816 | 76,2 | 28,68 | −17,82 | 117,3 | **1,610** | 28,33 | −17,82 | **1,590** | 1 089 | PASS | PASS | PASS | **FAIL** |

Chi tiết tầng: T1 — maxDD MTM/năm xấu nhất −17,68/−17,77/−17,82 % (≤ 40), qmin −0,77/−0,97/−1,69 %, 0 năm âm, conc 4,09/4,01/3,98 %. T2 — q* 26,4/24,0/21,8 % (≥ 15), top-1 % 14,97/15,76/16,54 (≤ 25). T3 (vs B0, inflate 1,1774) — Δwin% −0,73/−1,43 pp (≥ −2), ΔTSloss% +0,93/+1,63 pp (≤ +2,5), mP|SM Δ −0,02/−0,01 (CI chứa 0), mP|SL Δ +0,00/−0,39 (CI [−0,93; +0,17]) ⇒ không xấu có ý nghĩa. T4 — P1 1,758 ≥ 1,746 và 1,735 ≥ 1,708 (biên **+0,7 % / +1,6 %**); P2 1,610 < 1,746, 1,590 < 1,708 ⇒ FAIL; conc ≤ B0 cả hai.
maxDD MTM gần như không đổi (−17,68 → −17,82 %): phạt ăn vào **lợi nhuận** (CAGR −3,1/−5,6 pp), không làm sâu đáy. UW tăng 87 → 117 ngày ở cả P1/P2.

## 3. ΔPnL ghép cặp theo lệnh vs B0 [ĐO] — PRIMARY

Khoá `sym|start|level`; size-neutral (Δprofit × notional_B0; lệnh lệch ± chính nó); CI block-72h theo giờ vào, 2000 rep, seed 20260905; inflate √(2 ln 2) = 1,1774 quanh điểm.

| arm | ΔPnL | CI raw | CI inflate | khớp / chỉ B0 / chỉ arm | Δ khớp | % lệnh khớp đổi |
|---|---|---|---|---|---|---|
| P1 | **−6 996** | [−10 477; −3 781] | **[−11 095; −3 210]** | 2 414 / 103 / 80 | −4 598 | 44,5 % |
| P2 | **−13 000** | [−18 592; −7 898] | **[−19 585; −6 993]** | 2 310 / 207 / 181 | −10 495 | 44,5 % |

Cả hai CI inflate **nằm hẳn dưới 0** ⇒ phạt làm giảm PnL có ý nghĩa; độ dốc ≈ tuyến tính (−7,0k mỗi +0,69 %). [SUY LUẬN] ΣPnL thực giảm nhiều hơn ΔPnL size-neutral (−13,0k vs −7,0k ở P1) vì lãi kép: equity thấp hơn ⇒ size các lệnh sau nhỏ hơn.

## 4. Theo năm [ĐO]

ROI = return equity năm (b+unP); ddMTM = maxDD MTM phút trong năm; ΔPnL = ghép cặp size-neutral theo năm VÀO; #phạt = log `[CRASH-PENALTY] byYear`.

| năm | ROI B0 / P1 / P2 % | ddMTM B0 / P1 / P2 % | ΔPnL P1 | ΔPnL P2 | #phạt P1 / P2 |
|---|---|---|---|---|---|
| 2021 (H2) | 18,53 / 16,01 / 14,70 | −11,58 / −11,67 / −11,75 | −828 | −1 309 | 166 / 165 |
| **2022** | 11,11 / **10,19** / **7,72** | −17,68 / −17,77 / −17,82 | −377 | −1 424 | 202 / 201 |
| 2023 | 54,14 / 49,69 / 46,00 | −4,28 / −4,51 / −5,10 | −1 693 | −3 021 | 226 / 229 |
| 2024 | 43,35 / 39,93 / 36,55 | −10,69 / −11,11 / −11,21 | −1 888 | −4 052 | 267 / 261 |
| 2025 | 29,51 / 26,90 / 26,22 | −15,56 / −16,06 / −16,64 | −2 210 | −3 194 | 235 / 233 |

| năm VÀO | n B0 / P1 / P2 | ΣPnL B0 / P1 / P2 | TSloss% B0 / P1 / P2 |
|---|---|---|---|
| 2021 | 434 / 426 / 421 | 6 486 / 5 603 / 5 145 | 16,59 / 17,37 / 18,29 |
| 2022 | 423 / 423 / 418 | 4 609 / 4 138 / 3 100 | 20,33 / 21,04 / 21,77 |
| 2023 | 527 / 525 / 528 | 24 918 / 22 223 / 19 972 | 17,27 / 18,67 / 19,32 |
| 2024 | 599 / 590 / 589 | 30 842 / 26 753 / 22 995 | 11,19 / 12,20 / 12,73 |
| 2025 | 534 / 530 / 535 | 30 054 / 25 206 / 22 604 | 8,24 / 8,87 / 9,72 |

- ΔPnL **âm 5/5 năm** ở cả P1 và P2; 0 năm âm về ROI ở mọi arm.
- **2022 (bear) vẫn là năm yếu nhất** và mỏng hơn nữa: ΣPnL lệnh vào 2022 4,6k → 4,1k → **3,1k**; ROI 2022 11,1 → 10,2 → **7,7 %**. [SUY LUẬN] biên an toàn năm bear của B0 vốn đã hẹp (AUDIT_G2FLAT3 F7) thu hẹp thêm ~1/3 ở 2× phạt.
- Năm có nhiều leg phạt nhất = 2024 (267/261), nhưng ΔPnL lớn nhất theo năm rơi vào 2024–2025 — khớp E2.
- #leg phạt ≈ **44 %** số lệnh (1 096/2 494) — cùng tỉ lệ G2/R4 ở E2.

## 5. Lệnh "đóng trong giờ vào" (`time_order = 0`) [ĐO]

| arm | n 0h | ΣPnL 0h | % ΣPnL | ΣPnL phần còn lại | ΔPnL ghép cặp: lệnh B0 0h / >0h / chỉ arm |
|---|---|---|---|---|---|
| B0 | 521 | 41 000 | **42,3** | 55 909 | — |
| P1 | 475 | 35 394 (−13,7 %) | **42,2** | 48 530 (−13,2 %) | −2 030 / −6 853 / +1 888 |
| P2 | 441 | 30 722 (−25,1 %) | **41,6** | 43 094 (−22,9 %) | −6 421 / −13 798 / +7 220 |

[ĐO] Phần 0h giảm **cùng tỉ lệ** phần còn lại; tỉ trọng 42 % **giữ nguyên**. Theo lệnh B0: 0h −3,9 USDT/lệnh vs >0h −3,4 USDT/lệnh (P1) — chênh nhỏ. n 0h giảm 521 → 475 → 441 vì vào đắt hơn ⇒ một số lệnh cần lâu hơn để chạm TS. [SUY LUẬN] Phạt đều 1 mức trên giá vào **không** đặc biệt đánh vào nhóm "bắt nhịp hồi"; nhưng phạt đều là xấp xỉ — nếu trượt thật **tăng theo độ sâu cú sập** thì nhóm 0h (vào giữa cú sập) có thể chịu nặng hơn mức đo ở đây.

## 6. Top-5 episode (cụm ngày đóng lệnh, khoảng trống ≤ 2 ngày) [ĐO]

| arm | #episode | top-5 share | top-1 |
|---|---|---|---|
| B0 | 123 | **36,6 %** | 2025-10-10→23: 13 599 (14,0 %) |
| P1 | 125 | **39,0 %** | 2025-10-10→23: 12 565 (15,0 %) |
| P2 | 120 | **38,8 %** | 2025-10-10→23: 11 241 (15,2 %) |

Phạt làm đuôi tập trung hơn một chút (+2,4 pp): episode lớn giảm ít hơn phần "bánh mì" — [SUY LUẬN] lệnh lãi lớn ít nhạy với +0,69 % giá vào hơn lệnh lãi 4–8 %.

## 7. Cảnh báo theo ngưỡng khai trước (§6 pre-reg)

| điều kiện (ở P1) | ngưỡng | đo | kích? |
|---|---|---|---|
| Calmar_MTM(2022+) | < 1,2 | **1,735** | KHÔNG |
| ΣPnL / ΣPnL B0 | < 60 % | **86,6 %** | KHÔNG |

⇒ **"B0 KHÔNG đủ bền với giá khớp thật" — KHÔNG kích.** Không kích ≠ đã chứng minh bền: P1 chỉ còn biên **+0,7 %** trên sàn T4 toàn kỳ và ở 2× phạt đã FAIL T4.

## 8. So kỳ vọng ghi trước (§5 pre-reg)

| đại lượng | kỳ vọng P1 | đo P1 | kỳ vọng P2 | đo P2 |
|---|---|---|---|---|
| equity | 117–120k | **118,9k** ✓ | 104–108k | **108,8k** (nhỉnh hơn) |
| ΣPnL | 82–86k | **83,9k** ✓ | 69–73k | **73,8k** (nhỉnh hơn) |
| Calmar_MTM toàn kỳ | 1,70–1,78 | **1,758** ✓ | 1,50–1,60 | **1,610** (nhỉnh hơn) |

Ngoại suy từ G2 (E2) đúng ở P1; ở P2 thực tế nhẹ hơn ngoại suy một chút. Giả thuyết phụ "FLAT3 nhạy hơn G2 vì 42 % ΣPnL ở 0h" **bác bỏ** (xem §5).

## 9. Sự cố hạ tầng, rủi ro phát hiện, giới hạn

1. **P1 lần 1 = ERROR (hạ tầng, đã chạy lại cùng tag theo §7 pre-reg).** Kernel `flat3-cp-p1` (push 21:35) không nối được Aerospike Oracle lúc 21:37:49 ⇒ `SYMBOL_MAPPER_FAIL n=0` ⇒ guard `exit 2` (đúng thiết kế). Artifact lỗi (n 2110, eq 65 158, id symbol tự sinh — SAI) được **chuyển** sang `~/kaggle_sim/out/flat3-cp-p1-VOID-mapper` (không xoá, không dùng). P2 cùng lúc (21:42) nạp mapper 863 bình thường; Aerospike `:3222` LISTEN khi kiểm. Lần 2 (push 22:07) COMPLETE, mapper 863, jar `d944bea5`.
2. **Rủi ro phát hiện [ĐO]:** khi mapper rỗng, sim cố **GHI** 624 mapping symbol vào `AEROSPIKE_HOST=103.157.218.242` (host trong `config.properties` của bundle) — tất cả thất bại `NoRouteToHost` ⇒ **0 ghi**. [SUY LUẬN] nếu host đó là Aerospike của 242 và có route, một kernel mapper-lỗi có thể ghi mapping rác vào hệ live ⇒ đề xuất (task riêng, không làm ở đây): bundle Kaggle đặt `AEROSPIKE_HOST` về host không ghi được / chặn đường ghi mapping khi `TICKER_SOURCE=file`.
3. Phạt **đều 1 mức** cho mọi leg sập (không theo độ sâu `bar_ret`); mức phạt có CI [−0,19; +1,50] trên n=27 ⇒ stress giả định, không đo lại chi phí thật.
4. `quantity = budget/entry` giảm khi vào đắt ⇒ hiệu ứng bậc 2 (n và đường equity dịch: 2517 → 2494 → 2491) nằm trong artifact.
5. MTM phút dùng close 1m (cận dưới DD thật); 1 quan sát lịch sử, Calmar không có CI (ΔCalmar bootstrap đã biết là vô lực — AUDIT_G2FLAT3 F4) ⇒ dùng ΔPnL ghép cặp làm PRIMARY.
6. Kết quả chỉ cho B0 DEV (`pred.bin` WFO); **không** trả lời câu hỏi chuyển giao sang p15 của model live (AUDIT_G2FLAT3 F1).

## 10. Tái lập

```bash
# kernel (Kaggle): python3 ~/claude_master/1002/fcp_submit.py p0 | p1 | p2   (jar_ds=sim-jar-crashpen, bundle sim-x1-2021-bundle)
python3 research/analysis/flat3_crashpen_driver.py --parity-only   # -> PARITY P0 PASS
python3 research/analysis/flat3_crashpen_driver.py --workers 3      # -> docs/result/flat3_crashpen.json
```
Artefact: `/home/ubuntu/kaggle_sim/out/flat3-cp-{p0,p1,p2}/{storage/printDone.csv, logs/sim.out, result.json}`; md5 printDone P0 `650c386f…`, P1 `b3eaf921…`, P2 `7ca57976…`.
