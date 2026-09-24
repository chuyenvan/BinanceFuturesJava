# TASK B2 Bước 2 — Regime-adaptive gate (breadth ở uptrend, phòng thủ ở bear) — thiết kế MASTER 2026-09-21

Người soạn: MASTER. Thực thi: agent Sonnet. Chủ quyết định: Uni ("theo đuổi breadth").
Tiền đề: `docs/diag/DIAG_UW_SOURCE.md` (`9b10742`) — nguồn UW = phơi nhiễm đồng thời cao trong bear-multi-week (LUNA 2022), KHÔNG phải flash-crash/lệnh-biên-tệ/giữ-lệnh-lỗ. Cơ chế đúng = giảm SỐ lệnh đồng thời theo regime bear, KHÔNG phải size (TASK B NULL) / exit (đã nhanh sẵn).

## 0. LUẬT — như TASK B/B2 (không nới)
An toàn (HOLDOUT/242/push/thư mục bảo vệ/index.lock); **1 job nặng/lần** (`free -g`≥12G, `pgrep java` rỗng → **dừng shadow-c3 trước chuỗi sim, bật lại ngay sau, ghi mốc**); PREREG commit trước; cổng tái lập T170 md5 `efb793e2468ca3a7318da0f0ad23d4fc`; **cổng OFF byte-identical** mỗi flag mới; khẩu vị hiện hành qua `x1_rates.py --appetite current --k <k>`; logging chuẩn.

## 1. GIẢ THUYẾT
H: Gate **regime-adaptive** — lỏng (1.0, lấy breadth) khi BTC uptrend, chặt (1.70, phòng thủ) khi bear-multi-week — cho n_eff_total toàn kỳ ≥1.5× T170 (vì phần lớn thời gian là up/sideway) mà UW ≤ 200 (vì trong bear hệ thu phơi nhiễm về mức T170, không đào chuỗi dưới-nước dài). Nghĩa là tách được breadth (ở up) khỏi UW-risk (ở bear).
H0 (NULL): hoặc UW vẫn vỡ >200 dù cắt trong bear; hoặc n_eff không đạt 1.5× (breadth-chỉ-ở-up không đủ); hoặc đối chứng "giảm đều" (R0) đạt ngang biến thể regime (phần thắng chỉ do giảm chung, không do nhắm bear).

⚠️ **Rủi ro overfit phải kiểm soát (điểm review của MASTER)**: cơ chế + regime chọn SAU khi biết bear 2022 gây UW ⇒ nguy cơ curve-fit 1 sự kiện. Kiểm soát bắt buộc trong PREREG:
- Ngưỡng regime theo CHUẨN NGÀNH, không tinh chỉnh: MA200 (chuẩn trend-following) và/hoặc dd_from_peak365 ≤ −25% (định nghĩa "bear" phổ biến). Chọn 1 định nghĩa chính + tối đa 1 phụ để kiểm robustness, KHÔNG quét nhiều ngưỡng.
- Một cặp mức gate up/not-up (dùng sẵn `REGIME_SCALE_UP=1.00`/`REGIME_SCALE_NOTUP=1.70` của hạ tầng), KHÔNG quét.
- **Chấm PER-YEAR** (2021-2025) + per-quarter: chứng minh không chỉ cứu 2022 mà không phá năm khác (đặc biệt uptrend 2023-2024 phải giữ được breadth/CAGR).
- Đối chứng R0 bắt buộc (tách nhắm-bear khỏi giảm-chung).

## 2. RECON ĐẦU (0-sim, trong cùng agent, trước PREREG)
Đọc `EntryGate.java` (`GATE_REGIME_ADAPTIVE`, `REGIME_SCALE_UP/NOTUP`) + `RegimeSchedule.java`:
1. Định nghĩa regime HIỆN TẠI của `RegimeSchedule` là gì? **Causal/trailing hay lookahead/hardcoded-schedule?** Nếu lookahead (biết trước ngày bear) → KHÔNG dùng được, phải thay bằng định nghĩa trailing MA200/dd ở §3.
2. `GATE_REGIME_ADAPTIVE` bật thì gate = SCALE_UP khi regime=up, SCALE_NOTUP khi not-up — xác nhận đúng cơ chế này, và OFF (mặc định) có byte-identical T170 không (chắc có vì đang tắt — verify).
3. Nguồn dữ liệu regime online: engine đọc BTC close ở đâu để tính MA200 trailing được không lookahead (khớp `CLOSES_1H.bin`/ticker Aerospike). Nếu `RegimeSchedule` hiện hardcode lịch → thêm chế độ tính MA200 trailing causal.
Ghi kết quả recon vào PREREG.

## 3. ĐỊNH NGHĨA REGIME (khoá trước)
`not_up(t)` (causal, tính đến ngày t−1) = **BTC daily close < MA200(trailing)**. (Chính; MA200 chuẩn ngành, không tinh chỉnh.) Robustness phụ (báo cáo, không đổi phán quyết): `dd_from_peak365(t) ≤ −25%`. `up(t)` = phủ định. Gate(t) = 1.0 nếu up, 1.70 nếu not_up. Regime cập nhật theo ngày, causal tuyệt đối (không dùng dữ liệu ≥ t).

## 4. BIẾN THỂ (k khai báo trong PREREG)
Baseline (không tính k): **T170** (gate 1.70 đều) + **gate-1.0** (đều lỏng, = T100). Cả hai đã có sim.
- **R (chính)**: `GATE_REGIME_ADAPTIVE` bật, up→1.0 / not_up→1.70, regime = MA200-trailing §3.
- **R0 (đối chứng)**: gate cố định ĐỀU ở một mức sao cho **tổng số lệnh toàn kỳ ≈ R** (agent tính mức gate cho khớp, chốt trước khi chấm metric). Mục đích: nếu R0 đạt UW ngang R thì phần thắng chỉ là "ít lệnh hơn nói chung", không phải "nhắm bear". (Nếu khó khớp bằng gate đều, dùng size-scale đều khớp exposure — ghi rõ cách chọn.)
Mỗi biến thể = profile mới copy `x1_gs_t170.properties`, `git diff` chỉ các khoá khai báo.

## 5. TIÊU CHÍ (khoá trước; UW là tiêu chí CHÍNH)
- **u1 breadth**: n_eff_total(R) ≥ 1.5 × n_eff_total(T170) (script `bigdown_struct.py`).
- **u2 khẩu vị**: PASS toàn bộ hiện hành, **đặc biệt UW ≤ 200** + CAGR ≥ cận dưới CI-72h(k) của T170.
- **u3 vs incumbent**: maxDD ≤ −14.8% VÀ UW ≤ 115 (không thua T170 quá 25%).
- **u4 nhắm-bear đúng**: UW(R) < UW(R0) VÀ chuỗi UW dài nhất của R rơi vào bear ngắn hơn của R0 — bằng chứng cơ chế nhắm regime, không phải giảm chung.
- **u5 không phá uptrend** (chống overfit): CAGR per-year 2023 & 2024 của R ≥ 90% CAGR các năm đó của gate-1.0 (breadth ở up được giữ, không bị regime cắt nhầm).
- THẮNG = R đạt u1-u4 VÀ u5; NULL = u2 vỡ (UW>200) hoặc R0 ngang R (u4 fail); HỖN HỢP = còn lại.

## 6. ĐO — như B2: metric tổng hợp/phân phối, KHÔNG khoá (sym,start). Cùng cửa sổ 2021-07-01..2025-12-31, Oracle ARM64.

## 7. QUY TRÌNH
PREREG `docs/prereg/PREREG_REGIME_GATE.md` (recon §2 + regime §3 + biến thể + u1-u5 + phán quyết) commit trước → code (bật/hiệu chỉnh `GATE_REGIME_ADAPTIVE` + regime MA200-trailing causal, giữ OFF byte-identical) → cổng OFF T170 md5 → dừng shadow-c3 → sim tuần tự (T170 verify, R, R0; gate-1.0 dùng lại nếu còn) → bật shadow-c3 → tính u1-u5 (`bigdown_struct.py` + `x1_rates.py --appetite current --k`) → `docs/result/RESULT_REGIME_GATE.md` verdict → commit branch `module` (KHÔNG push) → dọn wfo_ds tạm, giữ printDone/sim.out.
Nếu OFF không byte-identical hoặc regime chỉ tính được lookahead → DỪNG, báo MASTER, không ép.

## 8. Ý nghĩa
THẮNG ⇒ shadow paper song song ≥1 tháng trước khi bàn đổi incumbent. NULL/HỖN HỢP ⇒ ghi `power_wall.md`: regime-adaptive gate không cứu được UW-trong-bear mà giữ breadth ⇒ breadth long-only đóng; chuyển alpha mới (TASK D) hoặc timing-exit.

## 9. Sau khi xong: cập nhật project memory (`round_2026-09-20...md` + `MEMORY.md`), báo MASTER: bảng T170/gate-1.0/R/R0 (n_eff_total, ICC, maxDD, UW, CAGR+CI, per-year), u1-u5 ✅/❌, verdict, cổng OFF PASS, mốc shadow, diff Java, và định nghĩa regime hiện tại của RegimeSchedule (causal hay không).
