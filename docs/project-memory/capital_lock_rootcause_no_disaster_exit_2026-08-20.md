# Root-cause TOO_MUCH_CAPITAL_LOCK: thiếu disaster-exit, KHÔNG phải chỉ arm (2026-08-20)

## Câu hỏi user
"Phải sửa TOO_MUCH_CAPITAL_LOCK trước để fitness ok thì mọi thứ khác mới có nghĩa/chuẩn, đúng không?"

## Trả lời ngắn
Đúng hướng, nhưng gốc không phải arm. Capital-lock do **thiếu disaster-exit** (không hard-SL, không time-stop) → lệnh không pump đủ arm thì KHÔNG có đường thoát → nuôi vô hạn. Arm chỉ là 1 phần (phía winner/sideways); **losers không thể fix bằng arm** (arm chỉ trigger phía lãi). Fix thật = bật time-stop/hard-SL — đều env-settable, không rebuild jar.

## Chuỗi nhân-quả (bằng chứng code)
1. Constraint fitness (`HPOFitnessCalculatorV4`): `pctHeldOver7d = (#lệnh giữ >7 ngày)/#lệnh`; reject nếu `> MAX_PCT_HELD_OVER_7D = 0.02` (2%). Mức khoẻ tham chiếu: 0.31%.
2. Giải mã IS_fit K8 (`IS_fit = -100000 - pctHeldOver7d×100`): win0 −100037.9 → **37.9%**; win1 −100017.6 → 17.6%; win2 → 19.2%... In-sample **17–38% lệnh giữ >7 ngày** (gấp 50–120x mức khoẻ). Đây là constraint DUY NHẤT trip → mọi genome reject → IS_fit≈−100000 → HPO degenerate (mọi gene đứng default, min==max).
3. Vì sao giữ lâu vậy: canonical config `HARD_STOP_LOSS_RATE=0` (properties không set → fallback 0), `HARD_SL_PCT=0` (env SIM_HARD_SL_PCT không set), `TIME_STOP_HOURS=0` (không set). → **Exit duy nhất = trailing**. Trailing chỉ arm khi lãi ≥ arm (26%); 84% entry không chạm. Lệnh không pump ≥26% (losers, sideways, small-winner) **không có exit** → ride tới hết window (mark-to-market). Khớp comment `TrailingStopSweepProbe:101` "(HARD_STOP=0, TIME_STOP=0) => mark-to-market cuối kỳ" và Configs:242 "tránh nuôi vô hạn, 0=tắt mặc định".

## Arm sweep có còn ý nghĩa không?
CÓ, như **diagnostic**: giải mã IS_fit theo từng arm cho biết bao nhiêu capital-lock là arm-fixable (winner-side) vs cấu trúc (loser-side cần hard-SL/time-stop). Nhưng arm KHÔNG fix được loser-ride → arm sweep đơn thuần khó thoát reject region.

## Fix ứng viên (đều env, không rebuild)
- `TIME_STOP_HOURS` (Configs:249, env): cắt lệnh chưa-arm theo thời gian ("thesis-expiry"). Thử {off, 72, 120, 168}h.
- `SIM_HARD_SL_PCT` (Configs:670, env): hard stop-loss theo độ sâu lỗ trên giá entry đầu. Thử {off, 0.15, 0.20}.
Đo: pctHeldOver7d có xuống <2% không? IS_fit có thoát −100000 → SUCCESS (note đổi từ TOO_MUCH_CAPITAL_LOCK) không? Nếu có → capital-lock được unlock, HPO/fitness mới có nghĩa.

## Đề xuất thứ tự (sửa lại so với "arm trước")
1. Để anchor arm=26 (đang chạy) hoàn tất — validate cơ chế pin WFO_TSMULT_LO/HI + reconcile K-grid + đo baseline pctHeldOver7d.
2. Pivot sang **disaster-exit sweep** (TIME_STOP_HOURS / SIM_HARD_SL_PCT) — đây mới là capital-lock fix + unlock fitness. Cùng cơ chế run_worker env, cùng harness, không rebuild.
3. Sau khi fitness thoát reject → arm/gap sweep mới cho số "sạch" (không confound capital-lock).

## Trạng thái infra: java-run-lc = pristine Aug2 (sạch), run_worker=K5, anchor arm=26 đang chạy (kgarm2.sh).
