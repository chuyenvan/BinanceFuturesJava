# RESULT_GATE_QUOTA_SKIPFULL — quota gate G2 bỏ qua khi sổ đầy (Pha E chương trình GATE)

Ngày 2026-10-05 (GMT+7). Pre-reg `docs/prereg/PREREG_GATE_QUOTA_SKIPFULL.md` **19072857** (chốt trước code/số) + bổ sung định danh **5fcfcc92** (trước kernel P0). Cổng offline **dbc435ef**. Code branch `feat/gate-quota-skipfull` **128290af** (push branch, KHÔNG merge). Số máy: `docs/result/gate_skipfull.json`; driver `research/analysis/gate_skipfull_driver.py`.
Ràng buộc đã giữ: 0 Java sim trên Oracle (chỉ `mvn -o test` + build), 0 chạm 242/shadow_c3, 0 merge, DEV ≤ 2025-12-30, Kaggle ≤ 2 kernel song song (9 kernel), RAM đỉnh chấm điểm 0,58 GB.

## 0. KẾT LUẬN (rủi ro trước)
1. **Luật GO pre-reg: ĐẠT cả 5** (C1–C5) trên 8/8 cặp PASS parity. Δ CAGR22 trung bình **+2,81 pp**, CI 95% paired t (df 7) **[+0,78; +4,83]**; sd CAGR22 **3,58 → 1,37**; Calmar22 TB **1,529 → 1,649**; maxDD không đổi ở mọi seed; ex-2022 ΔCAGR23 TB **+0,33 pp**.
2. **Cơ chế đúng chỗ, đúng hướng:** ON giống hệt OFF tới **12/05/2022** (lệnh đầu tiên khác), pass 2022Q2 giảm (S21 405 → 293), pass 2022Q3 tăng (S21 15 → 83, S7 43 → 81, S13 45 → 83); lợi suất năm 2022 của 6 seed xấu đổi dấu (−9,9…−2,8% → +3,9…+8,2%); 2023–2025 gần như trùng (trừ S21 2023 +9,3 pp do lệch sổ kéo tới 10/2023). Seed tốt gần như không đổi (S777 0 lượt skip ⇒ byte-identical; S99 +0,14; A1 +0,26 pp).
3. **Rủi ro chính:** (a) n = 8 seed, 1 sự kiện (05/2022) quyết định toàn bộ lợi ích — CI từng cặp (bootstrap khối 10 ngày, inflate 2,039) đều chứa 0; (b) maxDD/UW đáy không đổi vì cú sập xảy ra TRƯỚC khi ON tách khỏi OFF ⇒ lever này không giảm rủi ro đuôi, chỉ hồi phục nhanh hơn (UW22 TB 247 → 116 ngày); (c) cổng offline pre-reg **không đo được** (xấp xỉ U gắn 0 phút full) — bằng chứng cơ chế q_t chỉ là hậu kiểm + số pass/quý trong sim, q_t trong sim không log; (d) **live**: 242 có 48–62 vị thế legacy ⇒ U live có thể sát/vượt U_MAX dài ⇒ khi bật, buffer live có thể ngừng nạp (q_t "đứng") — chưa đo U live (không được chạm 242).

## 1. Định danh + parity
| mục | giá trị |
|---|---|
| key | `GATE_QUOTA_SKIP_WHEN_FULL` (Cfg/Configs, default false); check_cfg_gateway OK |
| test | `mvn -o test` 217 test 0 fail (GateQuotaSkipFullTest 7/7: ON+full không nạp/không pass; OFF ≡ bản 3 tham số; ON+!full ≡ OFF trên chuỗi 10 ngày; r cực trị lúc full không vào q; leg không-PREDICT không đổi; biên U_MAX = managerBudget null) |
| class diff (19072857 → 128290af) | đúng 6 file: AIRejectFilter, GateRollingRatio, SimulatorMarketLevelTicker1MStopLoss, Configs, DetectEntrySignal2TradeNormal (+`$TickGate` chỉ LineNumberTable) |
| jar | sha256 `0944841ca1b3ac444caa17ac144a0a89e44b6f2270a525cd545f32b95469ad7f`, dataset `sim-jar-gqsf` (+ prof md5 0e0caef0) |
| P0 OFF (B0@K16, `gqsf-p0`) | md5 printDone **ff3ce513edf2316088a4b5ac464f76dc**, n 2517, eq 131 908 ⇒ **byte-identical OFF PASS** |
| 8 ON (`gqsf-*`, K24) | parity 8/8 PASS: jar sha, TOPK=24, key=true + B0OV trong prof_run, log `[GATE-QUOTA] SKIP_WHEN_FULL=ON`, pred md5 (7 seed qua pred_ds; A1 = dòng Java `LOAD offline OK … (md5 verified)` trùng n700-a1), result.ok |

## 2. Cổng offline (§4) — KHÔNG đo được; hậu kiểm
- **Theo pre-reg** (U = margin printDone / E ngày b+unP của run OFF, full ⇔ U ≥ 0,60): **0 phút full** ở mọi seed (U max tháng 5/2022: S21 0,585, S7 0,569); 0/255 (S21) và 0/115 (S7) pass lãng phí bị gắn full ⇒ q_h T6–T9 ON = OFF (S21 0,011177; S7 0,008399), pass T6–T9 ON = OFF (S21 33/33, S7 80/80). Kỳ vọng "q giảm, pass ≥ ×1,30" **không kiểm được** — lỗi dụng cụ (E ngày lúc 07:00 bỏ lỗ chưa thực hiện trong ngày sập; margin printDone ≠ marginRunning), không phải bằng chứng ngược giả thuyết. Theo §4: vẫn sim.
- **Hậu kiểm (viết SAU khi thấy cổng, không phải cổng):** proxy full = phút có ≥ 1 pass OFF không vào lệnh (D2: 100% do managerBudget null). q_h T6–T9: S21 **0,01118 → 0,00990**, S7 **0,00840 → 0,00792**; pass T6–T9: S21 **33 → 367**, S7 **80 → 251**; 6 seed còn lại cùng hướng, S777 không đổi (0 phút full 2022). Proxy phóng đại (đếm offline không có phản hồi sổ lệnh): sim thật cho pass 22Q3 S21 15 → 83.

## 3. 8 seed ON vs OFF (K24; OFF = n700-a1 / gabl-seed7 / gsb-*, jar 7368be46; ON jar 0944841c)
| seed | CAGR22 OFF→ON (Δ) | maxDD22 | Calmar22 | UW22 (ngày) | n/năm | phút vào 2022 | skipFull | ΔCAGR23 | ΔCAGR boot [infl] |
|---|---|---|---|---|---|---|---|---|---|
| S21 | 29,24 → 35,88 (**+6,63**) | −24,67 (=) | 1,185 → 1,454 | 349 → 136 | 657 → 742 | 106 → 165 | 942 | +2,83 | [−3,23; +19,17] |
| S7 | 31,34 → 35,64 (**+4,30**) | −22,75 (=) | 1,377 → 1,566 | 334 → 116 | 705 → 741 | 138 → 164 | 147 | +0,00 | [−1,70; +12,77] |
| S123 | 31,56 → 35,61 (**+4,05**) | −23,17 (=) | 1,362 → 1,537 | 334 → 117 | 708 → 747 | 131 → 167 | 179 | −0,02 | [−2,46; +13,72] |
| S2024 | 32,98 → 36,48 (+3,49) | −23,19 (=) | 1,422 → 1,573 | 322 → 117 | 704 → 736 | 126 → 159 | 237 | −0,01 | [−1,87; +10,79] |
| S13 | 34,10 → 37,67 (+3,57) | −22,92 (=) | 1,488 → 1,644 | 301 → 106 | 693 → 738 | 137 → 172 | 179 | −0,12 | [−2,71; +12,85] |
| A1 | 36,65 → 36,90 (+0,26) | −22,21 (=) | 1,650 → 1,662 | 117 → 117 | 732 → 736 | 170 → 170 | 14 | +0,00 | [−0,33; +1,07] |
| S99 | 38,23 → 38,36 (+0,14) | −21,41 (=) | 1,785 → 1,792 | 117 → 117 | 760 → 764 | 163 → 168 | 14 | −0,01 | [−0,71; +1,27] |
| S777 | 39,34 → 39,34 (0,00) | −20,05 (=) | 1,962 (=) | 101 (=) | 729 (=) | 160 (=) | 0 | 0,00 | [0; 0] |
| **mean ± sd** | **34,18 ± 3,58 → 36,98 ± 1,37** | −22,55 (=) | **1,529 → 1,649** | 247 → 116 | 711 → 742 | 141 → 166 | — | **+0,33** | — |

maxDD toàn kỳ cũng không đổi ở mọi seed (đáy MTM nằm trong cú sập tháng 5, trước điểm tách 12/05/2022). Lợi suất năm 2022 OFF → ON: S21 −9,94 → +3,85; S7 −5,98 → +6,93; S123 −5,93 → +6,24; S2024 −5,24 → +5,13; S13 −2,81 → +8,21; A1 5,71 → 6,51; S99 7,29 → 7,72; S777 22,64 (=). Tập lệnh khác OFF (chỉ-OFF / chỉ-ON): S21 146/488, S13 102/282, S7 63/207, S123 45/201, S2024 45/173, S99 21/33, A1 13/28, S777 0/0.

## 4. Luật GO (cố định trong pre-reg)
| luật | số | kết quả |
|---|---|---|
| C1 mean ΔCAGR22 > 0 và CI 95% paired t không chứa 0 | +2,81 [+0,78; +4,83] (t 2,3646, df 7) | ĐẠT |
| C2 sd CAGR22 ON < 3,58 | 1,37 (OFF tính lại 3,58) | ĐẠT |
| C3 mọi seed \|maxDD\| ≤ 40% (toàn kỳ + 2022+) | xấu nhất −24,67 (S21) | ĐẠT |
| C4 mean Calmar22 ON ≥ 0,9 × 1,529 = 1,376 | 1,649 | ĐẠT |
| C5 mean ΔCAGR23 ≥ −1,0 pp | +0,33 | ĐẠT |
| **GO** | 8/8 cặp hợp lệ | **ĐẠT (đề xuất, không tự quyết)** |
So kỳ vọng khai trước: mean Δ +2…+4 pp → **+2,81 (trong dải)**; sd giảm ~30% → **giảm 62% (vượt)**; seed tốt ±1 pp → **0 / +0,14 / +0,26 (đúng)**. Δn/năm +31 (+4%).
Lưu ý thước: CI ghép cặp từng seed (bootstrap ngày MTM khối 10 ngày, inflate √(2 ln 8)) đều chứa 0 — luật GO dựa vào paired t qua 8 seed, không dựa CI từng cặp.

## 5. Lệch pre-reg (khai đủ)
1. Cổng offline §4: dụng cụ U xấp xỉ gắn 0 phút full ⇒ cổng không kiểm được. Hậu kiểm proxy viết SAU khi thấy cổng (ghi rõ "không phải cổng") — commit dbc435ef.
2. Checker parity A1 (`pred`): lần chấm đầu VOID do checker tìm md5 trong dòng Java vốn chỉ in số dòng; sửa checker so NGUYÊN dòng `LOAD offline OK … (md5 verified)` với run OFF n700-a1 cùng bundle (pred.bin gốc 5dd6bb4c). Run không chạy lại, không đổi số.
3. Không có lệch nào khác: không đổi key/thiết kế/luật/seed sau khi thấy số; không thêm biến thể.

## 6. Rủi ro + đề xuất cho MASTER (không tự quyết)
**Rủi ro:** (1) lợi ích = 1 sự kiện (05/2022) × 8 seed; DEV không có cú sập thứ hai cùng kiểu để kiểm ngoài mẫu — 2026 niêm phong. (2) Không giảm maxDD/đáy; chỉ giảm "đói" sau sập ⇒ không thay lever rủi ro đuôi. (3) Live: điều kiện full dùng U của sổ live (242: BudgetManager thật; shadow: ShadowBookC3). 48–62 vị thế legacy trên 242 có thể giữ U ≥ U_MAX lâu ⇒ buffer live ngừng nạp, q_t cũ dần (giới hạn: không có hạn mức thời gian "đứng"). Ở `c3_shadow` khi bật, mỗi ứng viên PREDICT gọi thêm 1 lần lấy giá Aerospike cho sổ giấy (chi phí độ trễ, chưa đo). (4) Sim ON dùng sổ lệnh khác OFF tới 10/2023 (S21) ⇒ ΔCAGR23 S21 +2,83 là hệ quả sổ, không phải lợi ích độc lập.
**Đề xuất:** (P1) coi GATE_QUOTA_SKIP_WHEN_FULL là ứng viên B0 mới cho sim (K24 band); nếu MASTER chấp nhận, chạy thêm @K16 (cấu hình deploy) 1 kernel pre-reg trước khi xét live. (P2) Trước khi xét live: đo U của 242/shadow theo phút trong 2–4 tuần (đọc-only) + log `skipFull`/giờ; thêm cảnh báo khi U ≥ U_MAX liên tục > N giờ (N chốt trước). (P3) Thêm counter `skipFull` theo quý vào log cuối sim (đang chỉ tổng) để đo q_t/pass trực tiếp ở vòng sau. (P4) Không dùng lại dụng cụ U offline của §4 (E ngày + margin printDone) — sai số quá lớn ở ngày sập.

## 7. Tái lập
`python3 research/analysis/gate_skipfull_offline.py` (cổng) → `… posthoc`; `python3 research/analysis/gate_skipfull_driver.py jards | p0 --code-sha 128290af | submit <seed> --code-sha 128290af | fetch | parity | score --workers 3`; điểm tách/tập lệnh: `research/analysis/gate_skipfull_div.py`.
