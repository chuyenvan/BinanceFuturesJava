# E2E_REPLAY_V12 — chạy thử trên FIXTURE PHÁT TRIỂN 10-30 (KHÔNG phải kết quả chấm)

- Ngày 2026-11-16. Fixture `~/claude_master/e2e1105/fx` (10-29 07:00 → 11-01 07:00 +07, 3 ngày). Jar r4u3fin2 md5 6418035…;
  env = danh sách trắng 242 (`~/claude_master/e2e_v12/env242_whitelist.raw`, 161 tên cụ thể, lấy 16-11; 242 đã có
  LIVE_APPLY_GRID_RATIO=true, LIVE_DCA_GRID_ENABLED=true). Lệnh: `flock -w 3600 ~/claude_master/locks/oracle_heavy.lock nice -n 10
  tools/e2e/run_all.sh` → `~/claude_master/e2e_v12/out/{R0,R0-DRY,R-OLD,S-DCA,FIN-INJ,R-1000,R-4000,_ref}`, `check_v12.{txt,json}`.
  Mỗi lượt ~7 s. Moc: SDCA_AT = START+12 h (luật chọn cụm kích ở 10-30 03:47: AIN, JCT), FIN_INJ_AT = START (AIN 03:45).
- `prep_fixture.py` mới (tham số hoá) chạy lại cửa sổ 10-30 vào thư mục tạm: nội dung sel/klines/bigdown/buffer/exinfo TRÙNG từng byte
  (md5 sau giải nén) với fixture dev ⇒ tham số hoá không đổi đầu vào. CHƯA chạy cho 11-05.

| Tiêu chí | 10-30 (dev) | Ghi chú |
|---|---|---|
| C1 | PASS | 6 lượt cờ bật: md5 đúng, 10/10 class từ jar, 4 banner, env thiếu = ∅, khác = ∅ (ngoài override). R-OLD: banner SIZING/DCA-GRID vắng như kỳ vọng |
| E1 R0 / R0-DRY | PASS / PASS | 25 leg PREDICT (+1 BIG_DOWN), dãy (phút, symbol) ≡ REF 100 % |
| S1 R0 / R0-DRY | PASS / PASS | 26 SUBMIT, sai số tương đối lớn nhất 0,0; qty = floor đúng; 3 giá trị tay 225 / 216,5625 / 208,44 |
| D1 tự nhiên | KHÔNG XẢY RA | không có DCA tự nhiên (REF cũng không) |
| D1 S-DCA | FAIL | 2 cụm × legIdx 1,2,3, đúng phút ≡ REF, không leg 5, không leg trước bậc; FAIL vì budget thấp hơn công thức prereg 4,8–14,1 % (NGHI VẤN N4: code dùng capital = min(C3_CAPITAL, equity c3)) |
| X1 R0 | KHÔNG ĐỦ MẪU | 22 cụm thoát, toàn TRAIL (3 ngày ⇒ không có time-stop 168 h); lý do 1-leg 100 %; cùng phút 18/22 (82 %), 4 cụm −1' (N5); Δgiá TB −0,44 %; 1 cụm −1,51 % (QUSDT) |
| F1 FIN-INJ | PASS | AIN 03:45 không gửi, FIN_EXCL + dòng [MINUTE-FIN-EXCL], leg khác phút đó = R0 (JCT), không thế chỗ |
| K1 R0 / R0-DRY | PASS / PASS | 0 ERROR, 0 latch, 0 KHAN |
| E2 | CHƯA ÁP DỤNG | chỉ fixture 11-05; code đã thử bằng dữ liệu giả (không phải 11-05) |
| §6 vốn micro (báo cáo) | 26/26 leg R0 vẫn đặt được ở 1 000 ⇒ "micro = 1 000" (dev) | R-1000 / R-4000 thực: 26/26 SUBMITTED |

Kết luận dev: harness + REF chạy được, cấu hình đi đúng đường production. Hai điểm sẽ quyết định lượt 11-05 là N4 (vốn sizing) và N5 (phút
thoát) — cần MASTER quyết trước lượt chính thức (không nới tiêu chí trong nhánh này). Chi tiết đặc tả/NGHI VẤN: `E2E_REPLAY_V12_SPEC.md`.
