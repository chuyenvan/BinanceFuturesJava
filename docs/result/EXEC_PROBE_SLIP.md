# EXEC_PROBE_SLIP — đếm leg exec-probe và trạng thái chấm trượt giá (2026-10-30)

Nguồn: log app 242 đã pull về Oracle `~/claude_master/pull242/2026-10-21..2026-10-29/logs/full.log@*.gz`
(bản 10-29 pull lúc 08:23 +07 nên chứa cả log tới 10-30 08:22), dòng `[EXEC-PROBE] 1,...`.
Probe bật 2026-10-24 02:25 +07. Chỉ đọc, không ssh/ghi 242. Không Binance API.

## 1. Đếm (đã khử trùng lặp log archive)

| đại lượng | số | ghi chú |
|---|---|---|
| dòng `[EXEC-PROBE] 1,...` thô | **581** | 9 ngày pull; archive các ngày chồng lấn nên lặp |
| **event duy nhất** (khóa = toàn bộ 38 cột CSV) | **76** | 581 − 76 = 505 dòng trùng |
| leg vào duy nhất (`ENTRY`/`DCA`) | **53** | 25 @ 10-24 02:25, 26 @ 10-30 03:xx, 2 @ 10-30 07:19 (+07) |
| leg vào **hợp lệ để chấm** (`status∈{ok,short}`, `src=ws`) | **49** | 4 leg status khác (đo thất bại) ⇒ V1 = 49/53 = 92,5 % (≥90 %, đạt) |
| leg ra duy nhất (`EXIT`) | **23** | `TRAILING_STOP`; < 30 nên không báo cáo thống kê chân ra |

Bằng chứng khử trùng: 25 dòng `ENTRY` ngày 10-24 có cùng `t_dec`/`t_snap`/`t_bar_close`/giá/slip ở mọi ngày pull;
ví dụ `IRYSUSDT` xuất hiện 26 lần nhưng chỉ 1 dòng duy nhất. Vì vậy **không** dùng 581 (hay 325/180) để chấm.

## 2. Chấm theo prereg

`docs/prereg/PREREG_EXEC_PROBE.md` §3: chỉ chấm MỘT lần khi |E| ≥ **100**; X chỉ báo cáo khi ≥ 30.
Hiện |E| = **49 < 100**, |X| = 23 < 30 ⇒ **KHÔNG chấm, KHÔNG verdict**. `xp_score.py` trên file đã khử trùng:

```
verdict=NO_VERDICT col=slip_x025 n_E=49 n_X=23
validity_ok={V1:true, V2:true, V3:true, V4:true, V5:true} W={}
```

V1–V4 đạt (V5 không có `legs.csv` để đối chiếu). Không dùng p50/p90/p99 để kết luận; không đổi ngưỡng.

## 3. Ước ngày đủ 100 leg vào

- 49 leg hợp lệ trong 7 ngày (10-24..10-30) ⇒ **7 leg/ngày**; cần thêm 51 leg.
- Nhịp thực tế là **theo batch**: 25 leg (10-24), 26 leg (10-30 03:xx), 2 leg (10-30 07:19). Nếu mỗi 3–6 ngày
  có 1 batch ~25 leg ⇒ cần **2 batch** ⇒ khoảng **2026-11-05 .. 2026-11-11**.
- Nếu nhịp 7 leg/ngày đều ⇒ **~7 ngày** ⇒ khoảng **2026-11-06**.
- Mốc "đủ 100" nên kiểm sau mỗi batch; batch có thể làm |E| nhảy +25.

## 4. Chuẩn bị cho lần chấm đủ 100 (chưa dùng)

- `research/exec_probe/xp_score.py` (prereg): p50/p90/p99, excess vs ECMEAS, bootstrap CI, W1–W6.
- `research/exec_probe/xp_slip_extra.py` (mô tả bổ sung, KHÔNG đổi verdict): p50/p90/p99 theo giờ +07 và
  theo quintile L24 (quote volume ngày UTC trước, Vision daily 1d — file tĩnh), cùng phân rã bucket.
- Giả định sim để so: `xp_score.py:19-21` — ECMEAS "thực" NC 7 / C1 18 / C2 19 / C4 32 bps; stress
  23/33/41/101 bps; chân ra `SIM_SLIPPAGE_RATE` 0,67 bps (`Configs.java:956`); bucket theo
  `EntryCost.bucketOf` (`EntryCost.java:51-57`). Cột dùng: `slip_x025` vì `PAPER_EQUITY=35000 ≥ 20000`
  (prereg §3; log `[LIVE_PROFILE=c3_shadow] ... paperEquity=35000.0`).

## 5. Bất thường / giới hạn

- **CHƯA GIẢI THÍCH**: 4/53 leg vào có `status` không thuộc {ok, short} (đo thất bại) — chưa truy nguyên
  no_book/empty_book/rate_capped theo từng leg; không suy đoán.
- Log pull theo ngày chứa archive chồng lấn ⇒ mọi script chấm PHẢI khử trùng theo toàn bộ dòng CSV trước khi đếm.
  Số 325/180 (đếm thô không khử) là **sai** và sẽ cho verdict giả (RED_SIZE).
- Không chấm L24/giờ trong báo cáo này vì |E| < 100 (đúng luật task); script đã sẵn cho lần sau.
