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

## Vòng 2 (ERRATA1, HEAD sau 5f7dbf82) — fixture PHÁT TRIỂN 10-30 (`~/claude_master/e2e_v12/fx1030`), KHÔNG phải kết quả chấm
Lệnh: `tools/e2e/build_v12.sh; flock -w 3600 ~/claude_master/locks/oracle_heavy.lock nice -n 10 env E2E_OUT=~/claude_master/e2e_v12/out_v2 tools/e2e/run_all.sh`
→ `~/claude_master/e2e_v12/out_v2/check_v12.{txt,json}`; thử tiêm: `python3 tools/e2e/inject_v12.py --runs …/out_v2 --ref …/out_v2/_ref --fx …/fx1030 --env …`.

| Tiêu chí | 10-30 (dev) | Ghi chú |
|---|---|---|
| C1 (8 lượt cờ bật + S-TS) | PASS | tập override = khai báo + `LIVE_TS_MKT_EXT=0`; config replay có nhãn; died jar = {BTCDOMUSDT, USDCUSDT} |
| E1 R0 / R0-DRY | PASS / PASS | 26 leg PREDICT, legs R0 trùng byte (phút, symbol, outcome, budget) với `fa9b4cac` |
| S1 R0 / R0-DRY (+E) | PASS / PASS | budget rel 0; E rel ≤ 1,8e-16; `eq_at − b` = 60 s ở 100 % leg |
| S1 S-DCA (+E) | PASS | C_eff min 9 238,22 (E < C3_CAPITAL) — budget khớp 0 với C_eff_REF |
| D1 tự nhiên R0 | KHÔNG XẢY RA | 0 DCA đến hạn trong R0 |
| D1 S-DCA | PASS | AIN + JCT: legIdx 1,2,3 ở st+3 / st+12 / st+22 = thiết kế = REF; st+2 GATE_REJECT (p15 = 0); mỗi leg có isDcaAlt (dip) + p15 ok |
| X1 R0 | KHÔNG ĐỦ MẪU | 22 TRAIL, 0 TIME_STOP; tạm: phút OK (17/17 cùng phút + 5 ARM_CUNG_NEN, 4 lệch −1′), giá FAIL 1 cụm (N11) |
| X1 S-TS (tổng hợp dev) | FAIL | 26 cụm (22 TRAIL + 4 TIME_STOP); TIME_STOP 4/4 đúng phút REF (b0 + 168 h + 1′, jar cắt ở +75 s) + giá ∈ [L,H]; lý do OK; giá: QUSDT#2 +244 tick (N11) |
| F1 / K1 | PASS / PASS | |
| Điều kiện thị trường rig vs REF (R0) | 0/4 319 phút lệch | BIG_DOWN 1 phút (= phút BIG_DOWN của log live), isDcaAlt 33; REF `all` (không lọc A1) lệch `a1` ở 14 phút (N7) |
| §6 vốn micro | micro = 1 000 | 26/26 leg R0 đặt được ở 1 000 (dev) |
| Thử tiêm | 6/6 FAIL | stopPrice +3 tick (S-TS gốc đã FAIL do N11: px_bad 1→2); TIME_STOP +1′ (ok_phut True→False); DCA dời sang phút không điều kiện; REF bỏ cờ thị trường; REF p15 < 0,008; E × (1+2e-6) |

## Vòng 3 (ERRATA2 593e7f45, code 84a7cb6d + SPEC §7 443db31d) — fixture PHÁT TRIỂN 10-30 (`fx1030`), KHÔNG phải kết quả chấm
Lệnh: `/tmp/e2e3_run.sh` = `tools/e2e/build_v12.sh` (RC=0) + `flock -w 3600 ~/claude_master/locks/oracle_heavy.lock nice -n 10 env
E2E_OUT=~/claude_master/e2e_v12/out_v3 tools/e2e/run_all.sh` + `inject_v12.py` → `~/claude_master/e2e_v12/out_v3/{check_v12.txt,json, inject_v12.txt}`.
Rig/jar không đổi (không sửa `src/main`, `src/test`); 8 lượt RC=0; REF 5 lượt rc=0.

| Tiêu chí | 10-30 (dev) | Ghi chú |
|---|---|---|
| C1 | PASS | như vòng 2 |
| E1 R0 / R0-DRY | PASS / PASS | 26 leg PREDICT ≡ REF |
| S1 R0 / R0-DRY / S-DCA / S-TS (+E) | PASS ×4 | E rel ≤ 2e-16; S-DCA C_eff min < C3 |
| D1 tự nhiên R0 / S-DCA | KHÔNG XẢY RA / PASS | |
| X1 R0 | KHÔNG ĐỦ MẪU (tạm: đạt) | 22 TRAIL, 0 TIME_STOP; nhãn REF-nhịp 5 = arm-cùng-nến jar 5 (0 lệch nhãn); 5/5 cụm có nhãn cùng phút REF-nhịp, stop jar − SL REF-nhịp ∈ [−0,70; −0,34] tick; 17/17 cụm không nhãn cùng phút REF-nến; \|Δstop\| max 0,99 tick |
| **X1 S-TS (tổng hợp dev)** | **PASS** (vòng 2: FAIL) | 26 cụm (22 TRAIL + 4 TIME_STOP 0 lệch phút, giá ∈ [L,H]); ok lý do/phút/giá/nhãn |
| F1 / K1 | PASS / PASS | |
| Thử tiêm | 9/9 FAIL | T1 stop +3 tick; T2 TIME_STOP +1′; **T7 cụm có nhãn stop +3 tick; T8 bỏ nhãn REF-nhịp; T9 gắn nhãn cụm không nhãn**; T3–T6 như vòng 2 |

**Báo cáo riêng cụm `ARM_CUNG_NEN` (REF-nhịp so REF-nến = mức lệch live↔sim do nhịp trong nến, dưới quy ước O→H/L→C):**

| Cụm (b0 UTC ms) | sự kiện REF-nhịp trong phút thoát | Δphút nhịp−nến | ΔSL nhịp−nến | stop jar − SL nhịp |
|---|---|---|---|---|
| AGTUSDT 1793306760000 | nhịp 1 ARM | −1 | 0 tick | −0,70 tick |
| IDOLUSDT 1793306760000 | nhịp 2 ARM | −1 | 0 | −0,56 |
| PARTIUSDT 1793306760000 | nhịp 2 ARM | −1 | 0 | −0,34 |
| PARTIUSDT 1793319960000 | nhịp 2 ARM | −1 | 0 | −0,49 |
| **QUSDT 1793319960000** | nhịp 1 dời SL | 0 | **+244,4 tick (+0,45 %)** | −0,35 |

⇒ QUSDT (N11 vòng 2): REF-nhịp viết theo đặc tả tự ra đúng SL jar đặt (−0,35 tick) ⇒ không còn trượt. 4 cụm còn lại: arm trong nến rồi
thoát ngay cùng nến ⇒ sớm 1′ so sim, SL không đổi.

**E8:** N7 — `a1` ≠ `all` ở 14/4 319 phút (R0 và S-DCA; `alt` a1 33 vs all 47); rig ↔ REF `a1` 0/4 319 phút lệch. N8 — 13 key
(`[HA_TANG]` 11, `[CHIEN_LUOC_242]` DIED_SYMBOLS = BTCDOM,USDC, `[KHONG_AI_DOC]` SPECIAL_SYMBOLS); DIED_SYMBOLS không thuộc danh sách
trắng env 242 ⇒ chờ A1. N10 — `eq_at` REF (mô hình cache 60 s) ≡ `eq_at` jar ở 26/26 (R0), 32/32 (S-DCA), 26/26 (S-TS); chủ đích cache
cho sizing: A1 phân xử. Vốn micro: 1 000 (26/26). Kết luận (iii) dev = FAIL chỉ vì X1 R0 KHÔNG ĐỦ MẪU + E2 CHƯA ÁP DỤNG (đúng thiết kế fixture dev).
