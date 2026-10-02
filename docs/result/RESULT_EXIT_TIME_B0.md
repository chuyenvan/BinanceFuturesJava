# RESULT_EXIT_TIME_B0 — NO-GO: cắt sớm lệnh chưa arm (72h) chỉ là "đổi lỗ chậm lấy thắng muộn" trên thước ghép cặp

- **Pre-reg:** `docs/prereg/PREREG_EXIT_TIME_B0.md`, commit **`b4b22ddb`** (chốt và push TRƯỚC kernel đầu 00:37 GMT+7). Không đổi gì sau khi thấy số.
- **Chạy:** Kaggle `sim-exit-time-{p0,a1,a2}`, kernel `tools/kaggle_sim.py` bản **NOWRITE242** (`git show fix/no-write-242:tools/kaggle_sim.py`, commit `302bc211`, đóng băng ở `~/claude_master/1003/ksnw/`, md5 `8b60b00a…`); jar **B0 `7368be46…`** (`sim-jar-gdv2`) cả 3 arm; bundle `sim-x1-2021-bundle`; `sim_end_date=20251231`. Log kernel P0: `NOWRITE242 AEROSPIKE_HOST 103.157.218.242 -> 127.0.0.1`, `PREFLIGHT … TCP OK`; `sim.out` P0: **0** dòng `103.157`/`Error saving`.
- **Chấm:** `research/analysis/exit_time_b0_driver.py` (khung `flat3_crashpen_driver.py`), JSON `docs/result/exit_time_b0.json`. Script vận hành: `~/claude_master/1003/et_{submit,pipeline,fetch}.py`, log `et_pipeline.log`, `et_fetch.log`.
- **Sự cố hạ tầng (không ảnh hưởng số):** fetch A2 lần 1 lỗi mạng `ConnectTimeout kaggleusercontent.com` ⇒ fetch lại (`et_fetch.py`), kernel KHÔNG chạy lại. 0 sim Java Oracle, 0 chạm 242/shadow, 0 sửa `.java`, 0 build.

## KẾT LUẬN (rủi ro trước)
1. **VERDICT: NO-GO cho cả A1 và A2** theo luật §5 đã khoá: ΔPnL ghép cặp dương nhưng **CI chứa 0 rộng** — A1 **+1,76k [−7,2k; +12,1k] raw / [−8,8k; +13,9k] inflate**, A2 **+1,17k [−6,2k; +10,3k] / [−7,5k; +11,9k]**; theo năm vào chỉ **2/4** năm 2022–2025 dương (2023, 2024 âm cả hai arm). Điều kiện (3) Calmar ≥ B0 và (4) T1 PASS **đạt** nhưng không đủ.
2. **Cơ chế đo được (A1, 454 lệnh khớp bị cắt):** cắt 328 lệnh mà B0 để chết ở 168h ⇒ **+14,6k**; nhưng cắt luôn **126 "thắng muộn"** (B0 về arm và thoát TS sau 72h) ⇒ **−14,3k**. Hai khối **triệt tiêu gần đúng** (khớp: +0,2k); phần dương còn lại đến từ lệnh mới sinh do slot/vốn giải phóng (only_arm − only_b0 = +1,5k). A2 cùng hình: +10,7k / −9,3k. ⇒ Điểm ước lượng rơi đúng **cận dưới** counterfactual audit (+1,5k "cắt cả lệnh mơ hồ"), không phải cận trên +11,3k.
3. **Bẫy diễn giải — đừng đọc bảng equity như bằng chứng:** equity **+6,7 %** (131,9k → 140,8k), ΣPnL **+9,2 %**, Calmar_MTM **1,940 → 2,331**, maxDD MTM **−17,7 → −15,6 %**, UW **87 → 71** ngày trông rất đẹp, nhưng ~80 % chênh ΣPnL (+8,9k vs +1,8k size-neutral) là phần **không size-neutral** (trôi size/lãi kép — [suy luận]) (lãi 2021H2–2022 sớm hơn ⇒ lệnh sau to hơn), không phải hiệu ứng lever trên cùng lệnh. Calmar là 1 đường lịch sử (thước ΔCalmar vô lực, AUDIT §3.1). Đây cũng là lời giải thích hợp lý cho "+9,9 % ΣPnL" của E1 cũ.
4. **Điểm có thể có thật nhưng KHÔNG được phép kết luận:** maxDD MTM năm 2022 **−17,7 → −14,2 %** (A1) / −14,4 % (A2) — cắt lệnh chết sớm giảm phơi nhiễm trong bear. Đây là 1 quan sát, không có thước có lực; ghi để theo dõi forward, không làm lý do apply.
5. **T3 (chỉ thông tin):** A1 **FAIL** (Δwin −3,45 pp, ΔTSloss +4,75 pp), A2 **FAIL** (Δwin −2,32 pp; ΔTSloss +2,48 pp sát nút) — đúng dự báo cơ học. mP|SM không xấu (A1 7,64 vs 7,61 %), mP|SL **tốt lên** (−14,27 → −9,70 %). T4 FAIL **chỉ vì conc 4,0859 vs 4,0853 (+0,0005 pp, nhiễu)**; phần Calmar của T4 PASS.
6. ⇒ **Đóng lever "thời gian sống lệnh chưa arm" trên DEV.** Cùng với AUDIT_LONG_LEVERS: không còn lever exit LONG nào đáng một vòng DEV. Nửa-độ-rộng CI đo được **9,7k (A1) / 8,2k (A2)** — lớn hơn dự kiến 5–8k ⇒ MDE80 thực ≈ 16–19k (inflate), lever thời gian sống không thể chứng minh trên DEV ngay cả khi hiệu ứng thật cỡ +5–10k.

## 1. Cổng
| cổng | kết quả |
|---|---|
| **0 — parity P0** | md5 `650c386f0d0dfea334af9d55ca2f21d4` = neo; n **2517**; eq **131908**; jar `7368be46…`; mapper 863; profile_hash `c47b73f3133521a1` (= `de-p1`) ⇒ **PASS** |
| **1 — key hiệu lực A1** | profile_hash `58ab40b46f4e64cb` ≠ P0; md5 `ff434051…` ≠ P0; max `time_order` của SL = **72h**, 0 lệnh SL > 73h ⇒ **PASS** |
| **1 — key hiệu lực A2** | profile_hash `ddc71006f05217d2` ≠ P0; md5 `7f585b7f…` ≠ P0 (124 lệnh SL > 73h còn lại = lệnh đã chạm MFE ≥ 5 %, đúng thiết kế) ⇒ **PASS** |

## 2. Bảng chính (AS-IS, MTM phút; toàn kỳ 2021-07-01→2025-12-30)
| arm | n | ΣPnL | equity | CAGR % | maxDD MTM % | Calmar_MTM | UW (ngày) | CAGR 2022+ | Calmar 2022+ | win % | TSloss % | T1 | T2 | T3 | T4 | GO |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **B0 (P0)** | 2517 | 96 909 | 131 908 | 34,31 | −17,68 | 1,940 | 87,1 | 33,56 | 1,898 | 85,86 | 14,30 | PASS | PASS | ref | ref | ref |
| **A1** LOSER 72h | 2540 | 105 807 | 140 807 | 36,27 | −15,56 | 2,331 | 70,5 | 34,19 | 2,197 | 82,40 | 19,06 | PASS | PASS | FAIL | FAIL* | **NO** |
| **A2** COND 72h×MFE<5 % | 2527 | 105 009 | 140 008 | 36,10 | −15,56 | 2,320 | 84,4 | 34,33 | 2,207 | 83,54 | 16,78 | PASS | PASS | FAIL | FAIL* | **NO** |

\*T4 FAIL chỉ do conc ≤ B0 (4,0859 / 4,0869 vs 4,0853). q* 26,4 / 27,6 / 27,1; top-1 % 14,97 / 14,65 / 14,78; qmin −0,77 / −0,13 / +0,43; 0 năm âm cả 3.

## 3. PRIMARY — ΔPnL ghép cặp (size-neutral, `sym|start|level`, block-72h, 2000 rep, seed 20260905, inflate 1,1774)
| arm | khớp / chỉ-B0 / chỉ-arm | ΔPnL | CI95 raw | CI inflate | nửa-độ-rộng raw | Δ khớp | nhóm B0=SL | nhóm B0=SM | only_arm | only_b0 |
|---|---|---|---|---|---|---|---|---|---|---|
| A1 | 2365 / 152 / 175 | **+1 763** | [−7 232; +12 079] | [−8 828; +13 909] | 9,7k | +227 | +14 693 | −14 466 | +4 246 | −2 710 |
| A2 | 2417 / 100 / 110 | **+1 171** | [−6 161; +10 280] | [−7 462; +11 896] | 8,2k | +1 290 | +10 803 | −9 513 | +2 651 | −2 771 |

Σ(profit × notional) B0 = 98,3k ⇒ ΔPnL = **+1,8 % / +1,2 %** của B0.

**Lệnh bị luật mới cắt** (SL có `time_order` < 167h): A1 **484** (454 khớp B0: 328 vốn là time-stop 168h, **126 vốn là thắng armed**), mean profit −9,70 % (cùng lệnh ở B0 −9,06 %); A2 **304** (296 khớp: 225 time-stop, **71 thắng**), −11,03 % (B0 −10,55 %). "Thắng muộn bị cắt": A1 −14,3k, A2 −9,3k; "lỗ 168h cắt sớm": A1 +14,6k, A2 +10,7k.

## 4. Theo năm
| năm (vào) | ΔPnL ghép cặp A1 | A2 | ΣPnL B0 | ΣPnL A1 | ΣPnL A2 | ROI % B0 / A1 / A2 | maxDD MTM năm % B0 / A1 / A2 |
|---|---|---|---|---|---|---|---|
| 2021H2 | +1 536 | +1 068 | 6 486 | 8 461 | 8 029 | 18,5 / 24,2 / 22,9 | −11,6 / −11,6 / −11,6 |
| 2022 | +1 465 | +1 546 | 4 609 | 6 696 | 6 828 | 11,1 / 15,4 / 15,9 | −17,7 / **−14,2** / −14,4 |
| 2023 | **−2 518** | **−1 768** | 24 918 | 24 061 | 24 775 | 54,1 / 48,0 / 49,8 | −4,3 / −4,5 / −4,1 |
| 2024 | **−672** | **−200** | 30 842 | 32 831 | 32 998 | 43,4 / 44,2 / 44,1 | −10,7 / −9,9 / −10,1 |
| 2025 | +1 952 | +524 | 30 054 | 33 757 | 32 379 | 29,5 / 31,5 / 30,1 | −15,6 / −15,6 / −15,6 |
| **2022–25 dương** | **2/4** | **2/4** | | | | | |

ΣPnL thô theo năm A1 − B0: 3/4 năm 2022–25 dương — **chênh với thước ghép cặp chính là phần trôi size** (§KẾT LUẬN 3).

## 5. Luật GO (§5 pre-reg)
| điều kiện | A1 | A2 |
|---|---|---|
| (1) ΔPnL > 0 ngoài CI raw và inflate | **FAIL** | **FAIL** |
| (2) ≥ 3/4 năm 2022–25 dương (ghép cặp) | **FAIL** (2/4) | **FAIL** (2/4) |
| (3) Calmar_MTM ≥ B0 toàn kỳ và 2022+ | PASS (2,331/2,197) | PASS (2,320/2,207) |
| (4) T1 PASS | PASS | PASS |
| **GO-nghiên-cứu** | **NO** | **NO** |

## 6. So với kỳ vọng khai trước
Khai trước: A1 +1,5…+11,3k; nửa-độ-rộng 5–8k; power 15–45 %; T3 xấu cơ học +2…+4 pp TSloss. Thực tế: A1 +1,8k (đáy dải), nửa-độ-rộng **9,7k** (rộng hơn), TSloss +4,75 pp (A1) / +2,48 pp (A2). Không có gì ngoài dải đã ghi; dấu dương nhưng hiệu ứng không tách khỏi nhiễu.

## 7. Giới hạn
- 1 đường lịch sử DEV; MTM phút dùng close 1m. Thước ghép cặp tính lệnh lệch ± nguyên PnL ⇒ phần only_arm/only_b0 (≈ +1,5k) mang nhiễu entry.
- Quan sát DD 2022 (§KẾT LUẬN 4) là hậu kiểm, không được dùng để chọn arm hay mở vòng mới trên DEV.
