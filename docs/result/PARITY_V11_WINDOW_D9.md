# PARITY_V11_WINDOW_D9 — guard ngày INCOMPLETE, nhãn lại 10-25, trạng thái chấm lại 10-28/10-29
(2026-10-30, +07)

Prereg: `docs/prereg/PREREG_PARITY_V11_WINDOW.md` (481701b2) + ADDENDUM1/2/3 (fea9fb97, 4eef2788, 67ce404a).
Kết quả trước: `PARITY_V11_WINDOW_D8.md` (b78b02e8). Không đổi ngưỡng/định nghĩa nào; chỉ sửa **guard dữ liệu thiếu**
và **nhãn** theo đúng prereg §7.

## 0. TL;DR

| ngày | D8 | **D9** | lý do |
|---|---|---|---|
| 2026-10-22 | XÁM | XÁM | K5=164 (không đổi) |
| 2026-10-23 | XÁM | XÁM | K5=3 |
| 2026-10-24 | XÁM | XÁM | K5=1 |
| **2026-10-25** | **XÁM** | **KHÔNG ĐO ĐƯỢC (một phần) + XÁM** | pull242 INCOMPLETE (feat 277/1440) — guard mới |
| 2026-10-26 | KHÔNG ĐO ĐƯỢC (một phần) | KHÔNG ĐO ĐƯỢC (một phần) | không đổi |
| 2026-10-27 | TRƯỢT | **TRƯỢT** | P1 91,27 %; TRUOT xấu hơn XÁM nên guard không nâng |
| 2026-10-28 | KHÔNG ĐO ĐƯỢC (XÁM) | **KHÔNG ĐO ĐƯỢC (một phần)** | Vision daily 10-28 **vẫn chưa phát hành** (kiểm 10-30 10:59 +07) |
| 2026-10-29 | KHÔNG ĐO ĐƯỢC (XÁM) | **KHÔNG ĐO ĐƯỢC (một phần)** | Vision daily 10-29 chưa phát hành |

Tích luỹ (10-21..10-29, tính lại bằng cùng đầu vào): **166 152 cặp P2 đo cả hai phía; 28/28 cặp r/q ≥ 0,9; 0 lật nặng**
— **trùng khít D8**, xác nhận D9 chỉ đổi nhãn/guard, không đổi số.

## 1. Lỗi và cách sửa

`research/parity_v11/py/day_report.py::day_status()` trước đây **không đọc** `coverage_<tag>.json` ⇒ một ngày
`pull_incomplete=true` nhưng mọi ngưỡng đo được đều ĐẠT vẫn bị ghi **ĐẠT/ XÁM**, trái prereg §7:
*"Thiếu file của 1 ngày ⇒ ngày đó = KHÔNG ĐO ĐƯỢC (ghi rõ, không coi là ĐẠT)"*.

Sửa (chỉ guard, không đổi ngưỡng):

```python
cov = J("coverage")                     # them vao day_status()
...
inc = bool(cov is not None and cov.get("pull_incomplete"))
st["pull_incomplete"] = inc
if inc and tot.startswith(("DAT", "XAM")):
    st["giam_do_truoc_guard"] = tot     # luu nhan cu de audit
    tot = "KHONG DO DUOC (mot phan) + XAM"
```

- `TRUOT` **không** bị đổi (xấu hơn XÁM; nâng một ngày TRƯỢT lên "không đo được" sẽ che mất fail thật).
- `KHONG DO DUOC (mot phan)` đã có sẵn thì giữ nguyên.
- Ngoài ra `day_status()`/phần main được tách thành `main()` để **import được** cho unit test (hành vi khi chạy CLI
  không đổi: `python3 day_report.py <round> <ngày...>`).

## 2. Unit test

`research/parity_v11/py/test_day_report_guard.py` — dựng work/run giả trong tmp, gọi thẳng `day_status()`:

```
PASS ca1 INCOMPLETE + DAT                   -> KHONG DO DUOC   (assert thêm: giam_do_truoc_guard == "DAT")
PASS ca2 INCOMPLETE + P1 TRUOT              -> TRUOT
PASS ca3 COMPLETE + DAT                     -> DAT
ALL 3 CASES PASS
```

(2 ca theo yêu cầu + 1 ca đối chứng để chống regression.)

## 3. Nhãn lại 10-25

- `coverage_20261025.json`: `pull_incomplete=true` (pull242 10-25 và 10-26 đều **không** có `COMPLETE`),
  `feat_minutes=277/1440`, `sel_minutes=276/1440`, log phủ 1440 phút, 0 restart trong ngày.
- Trước D9, ngày này được ghi **XÁM** vì K5 = 1 phút (11:31) và mọi ngưỡng đo được đều ĐẠT — tức nhãn XÁM ngụ ý
  "đo được, chỉ có 1 phút nghi ngờ". Sai: **79 % số phút không có feature/selection** (do writer feat_dump dừng
  10-25 11:37 → 10-27 13:27, xem D8 §2 G1). D9 ghi **"KHÔNG ĐO ĐƯỢC (một phần) + XÁM"**.
- Không suy diễn gì thêm: các ngưỡng trên 277 phút vẫn được ghi trong JSON (P1 ĐẠT n=277, med 9,18e-8, 99,64 % ≤1e-3;
  P2 yếu 0 cặp r/q≥0,9; K5=1) nhưng **không** dùng để kết luận ngày ĐẠT.

## 4. Chấm lại 10-28 / 10-29 — **chưa làm được**, có bằng chứng

Điều kiện để chấm phần cần Vision: `data.binance.vision` daily kline 1m của ngày D phải tồn tại. Kiểm trực tiếp
S3 listing (phân trang đầy đủ) lúc **2026-10-30 03:59Z = 10:59 +07**:

| symbol | file mới nhất | có 10-28? | có 10-29? |
|---|---|---|---|
| BTCUSDT | `BTCUSDT-1m-2026-10-27.zip` | không | không |
| ETHUSDT | `ETHUSDT-1m-2026-10-27.zip` | không | không |
| SOLUSDT | `SOLUSDT-1m-2026-10-27.zip` | không | không |

⇒ **Vision chậm hơn 1,4–1,6 ngày như giả định**: tính đến 10-30 11:00 (+07) mới có tới 10-27. Vì vậy **không thể**
chấm lại 10-28/10-29 trong lượt này; trạng thái của hai ngày **giữ nguyên KHÔNG ĐO ĐƯỢC**.

Phía live **đã sẵn sàng**: `pull242/2026-10-28` và `pull242/2026-10-29` đều `COMPLETE` + `STATUS=OK`, đủ
1440/1440 phút feat/sel/s1. Thiếu **duy nhất** phía offline.

**Đường hoàn tất (đã có, không tạo thêm tiến trình):** watcher `parity_v11w/watch_daily.sh` (PID 1130614, chạy từ
10-25) tự chấm mỗi ngày khi Vision phát hành, ghi `WATCH_DONE` + `docs/result/parity_v11_daily_<tag>/`; nó gọi đúng
`day_report.py` **đã vá guard** nên kết quả sẽ mang nhãn D9. Hiện watcher còn kẹt ở 10-25/10-26/10-27 (pull
INCOMPLETE nên chờ hết 48 h mỗi ngày) và sẽ tới 10-28 muộn nhất ~10-31 13:30Z, rồi chờ Vision tối đa 36 h/ngày.
Khi Vision 10-28/10-29 xuất hiện, cần **một lượt D10** ghi lại số P1/P2-off/CTL và cập nhật bảng §0.

## 5. Artefact

- `docs/result/parity_v11_d9/parity_v11_d9.json` + mỗi ngày một thư mục JSON nhỏ (coverage/gate/s1/gv_p2/p3/tsx/
  kprime/kpp/live_only, cmp_ctl_*, restarts/segs/kprime_groups) — sinh bằng chính script đã vá, **round mới**,
  không sửa `parity_v11_d8/`.
- Lệnh sinh: `python3 research/parity_v11/py/day_report.py d9 2026-10-22 … 2026-10-29` (chạy tại `~/claude_master/parity_v11w`).
- Không xoá dữ liệu live/work của bất kỳ ngày nào (prereg §7 cần cho lượt M khi Vision monthly phát hành).
- Không tải dữ liệu lớn, không ssh 242 trong lượt này, không Binance REST/API.
