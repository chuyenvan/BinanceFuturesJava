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

> **ĐÍNH CHÍNH 2026-10-30:** con số "7 leg/ngày" trong mục này **bị bỏ** (xem §6.4). Số liệu còn lại của mục (49 leg, 2 batch) đúng.

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

## 6. ĐÍNH CHÍNH (2026-10-30) — nguồn trùng, 4 leg no_book, công cụ, nhịp leg

### 6.1 Nguồn trùng là **full.log không rotate**, không phải "archive chồng lấn"

§5 câu 2 viết "Log pull theo ngày chứa archive chồng lấn" — **sai cơ chế**. Kiểm lại 15 file
`~/claude_master/pull242/2026-10-2*/logs/full.log@<ts>_<hash>.gz`: **mỗi lần pull là MỘT bản đầy đủ** của cùng
một file log trên 242, bắt đầu từ dòng đầu tiên `18/10/2026 07:44:06.239` và tăng dần theo thời gian:

| file pull | kích thước | dòng `[EXEC-PROBE] 1,` |
|---|---|---|
| 2026-10-21 | 4,5 MB | 31 |
| 2026-10-28 | 8,2 MB | — |
| 2026-10-29 (mới nhất) | 9,0 MB | 76 |

⇒ 581 dòng thô = **cùng 76 event được chép lại qua 15 bản pull**, không phải các đoạn log nối tiếp nhau.
Hệ quả thực hành **không đổi**: mọi script chấm phải khử trùng theo toàn bộ 38 cột CSV trước khi đếm.
(Nếu log 242 được rotate theo ngày trong tương lai, cách đọc phải xem lại.)

### 6.2 Bốn leg `no_book` đều là TF — log nói gì

4/53 leg vào có `status=no_book` (không phải `ok/short`), **tất cả là TradFi**: ABBVUSDT, STMUSDT, MELIUSDT, EWZSUSDT,
cùng batch 10-30 03:47 (+07). Bằng chứng trong log (không có dòng WARN/ERROR nào cho 4 symbol này):

- `[SHADOW] open ABBVUSDT entry=291.96 qty=0.41 ...` @03:47:08.012 (STM 08.377, MELI 09.139, EWZS 14.348):
  shadow book **vẫn mở lệnh** bình thường;
- dòng probe tương ứng có `lat_snap_ms` = 8 012 / 8 377 / 9 139 / 14 348 ms và **toàn bộ cột book rỗng**
  (bid/ask/mid/spread_bps/l1_*/n_lvl/side_ntl/walk_vwap/fill_frac/slip_bps/... đều trống) ⇒ snapshot order book
  **không trả về gì** cho các TF perp này tại thời điểm đó (chậm 8–14 s rồi rỗng).
- **CHƯA GIẢI THÍCH nguyên nhân gốc** (feed depth của TF chưa warm / mapper cấp id mới cùng lúc — log có
  `cap id moi ABBVUSDT …` nhưng không có thông báo lỗi book). Không suy đoán thêm.

Vì vậy V1 = 49/53 = 92,5 % tính trên leg **đo được** là đúng, nhưng phải ghi rõ 4 leg mất đo **không ngẫu nhiên**:
chúng tập trung đúng vào nhóm TF — nhóm đang là chủ đề của HO2026_NOTF. Không dùng 49 leg để suy rộng cho TF.

### 6.3 `xp_slip_extra.py` nay khử trùng nội bộ

Trước 10-30, `rows()` chỉ đọc và **không** khử trùng: truyền 15 file pull thô sẽ ra 657 dòng (E=~400), sai hoàn toàn.
Đã sửa: `rows()` giữ `seen` theo **nguyên dòng 38 cột** và chỉ nhận lần xuất hiện đầu. Kiểm lại trên 15 file
(giải nén tạm): **76 event / 53 ENTRY / 4 no_book**, khớp bảng §1. Docstring ghi rõ full.log không rotate.

### 6.4 Bỏ "7 leg/ngày" — nhịp thực tế là **2 đợt**

49 leg hợp lệ không rải đều 7 ngày: **25 leg @ 10-24 02:25** và **28 leg @ 10-30 (26 @ 03:47, 2 @ 07:19)** (+07).
Không có leg nào trong 10-25..10-29. Vì vậy:

- **Bỏ** câu "7 leg/ngày" và ước "~7 ngày ⇒ 2026-11-06" — đó là chia trung bình trên khoảng có 2 đợt, không phải nhịp.
- Ước còn lại (2 batch nữa ⇒ 11-05..11-11) vẫn là **suy đoán từ 2 quan sát**, không phải dự báo; mốc đúng để chấm
  là **|E| ≥ 100**, kiểm sau mỗi batch.
