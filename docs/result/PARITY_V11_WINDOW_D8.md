# PARITY_V11_WINDOW_D8 — lượt chấm 2026-10-25 .. 2026-10-29

Ngày 2026-10-30 (+07). Prereg: `docs/prereg/PREREG_PARITY_V11_WINDOW.md` (481701b2) + ADDENDUM1/2/3
(fea9fb97, 4eef2788, 67ce404a). Kết quả trước: `PARITY_V11_WINDOW_D3.md` (c632f4b1). Watcher `aa84f195`.
Nguồn live: `~/claude_master/pull242/2026-10-25..29` (chỉ đọc 242, không ssh trong lượt này). Nguồn offline:
Vision UM 1m daily + funding monthly; KHÔNG Binance API, KHÔNG Aerospike 242.

## 0. TL;DR

| ngày | trạng thái | lý do chính |
|---|---|---|
| 2026-10-25 | **XÁM** | mọi ngưỡng đo được ĐẠT; K5=1 (phút 11:31) + chỉ có 277/1440 phút feat_dump |
| 2026-10-26 | **KHÔNG ĐO ĐƯỢC (XÁM)** | feat_dump=0, sel_dump=0; chỉ P3/S1-m/TSX/CTL đo được |
| **2026-10-27** | **TRƯỢT** | P1 91,27 % phút ≤1e-3 (<98 %), 92 phút lệch; K5=0 (toàn bộ nhãn K2b/K3′), P3 thiếu 7 giờ |
| 2026-10-28 | **KHÔNG ĐO ĐƯỢC (XÁM)** | Vision daily 10-28 chưa phát hành (404 toàn bộ 746 symbol); phần không-Vision ĐẠT |
| 2026-10-29 | **KHÔNG ĐO ĐƯỢC (XÁM)** | Vision daily 10-29 chưa phát hành; TSX NA vì thiếu S 10-28; phần không-Vision ĐẠT |

Không có ngày ĐẠT trong lượt này. 10-27 là ngày TRƯỢT đầu tiên của cửa sổ; 92 phút lệch đều có nhãn cơ học
K2b/K3′ (K5=0) nhưng prereg §5 không loại phút để cứu ngưỡng.

## 1. Phủ dữ liệu

| ngày | pull242 | feat/1440 | sel/1440 | s1/1440 | psym | log phút | GATE-RATIO giờ | restart trong ngày |
|---|---|---|---|---|---|---|---|---|
| 10-25 | INCOMPLETE (feat 277) | 277 | 276 | 1440 | 1440 | 1440 | 24 | 0 |
| 10-26 | INCOMPLETE (feat 0) | 0 | 0 | 1440 | 1440 | 1440 | 24 | 0 |
| 10-27 | INCOMPLETE (feat 1054) | 1054 | 941 | 1001 | 1001 | 1440 | 19 | 2 (11:43:53, 13:26:35) |
| 10-28 | OK | 1440 | 1440 | 1440 | 1440 | 1440 | 24 | 0 |
| 10-29 | OK | 1440 | 1440 | 1440 | 1440 | 1440 | 24 | 0 |

## 2. Khoảng thiếu / sự cố — bằng chứng log (giờ +07)

| # | khoảng | bằng chứng | diễn giải |
|---|---|---|---|
| G1 | **10-25 11:37:06 → 10-27 13:27:07** | `LIVE_FEAT_DUMP ... DU TICK (3000 dong) -> DONG file feat_dump_20261025_112900.csv.gz` @25/10 11:37:06.331; `mo file feat_dump/feat_dump_20261027_132600.csv.gz` @27/10 13:27:07.277 | feat_dump + sel_dump ngừng ghi 2 ngày 1 giờ 50 phút. Giữa hai mốc KHÔNG có restart (MainClass gần nhất 23/10 09:37:31, kế tiếp 27/10 11:43:53) và không có ERROR/WARN của LiveFeatureDump ⇒ **CHƯA GIẢI THÍCH** nguyên nhân writer dừng |
| G2 | **10-27 11:43:59 → 13:26** | `MainClass` @27/10 11:43:53.647; `Failed to initialize AI System` @11:43:59.466; `MainClass` @13:26:35.508; feat_dump mở lại @13:27:07.277 | AI init fail đúng như mô tả; khôi phục bằng restart 13:26:35 |
| G3 | **10-27 08:37:06 → 15:19:06** | `[OI-GUARD-2] oi_feat pipeline STALE age=121m > 120m ... -> GATE entries tick ...` (1284 dòng, dòng đầu 08:37:06.148, cuối 15:19:06.194) | OI stale ⇒ gate bỏ entry. Đo được 08:37–15:19, **không khớp** mốc "~09:09–15:33" trong task; không suy đoán mốc kia |
| G4 | **10-27 07:03:06 → 15:19:06** | `[S1] skip tick ? khong phai C3 (chua co score S1)` (878 dòng) | S1 thiếu score trong 8h16m; P3 thiếu 7 giờ (01:00–07:00 UTC = 08:00–14:00 +07) |
| G5 | **10-27 11:44:07 → 13:26:06** | `symbol_mapper [init] co 1 id dung chung: {1=[BTCUSDT, XUSDT]}` (396 tick lỗi; `SYMBOL_MAPPER_DUP_POLICY=WARN` nên chạy tiếp) | Lỗi mapper trùng id trong cửa sổ AI fail; chưa xác định quan hệ nhân quả ⇒ **CHƯA GIẢI THÍCH** |

## 3. Kết quả từng ngày

| ngày | P1 | P1-m | S1-I | S1-m | GV-I | P2 | P3 | TSX | CTL | NET | K5 | kết luận |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 10-25 | **ĐẠT** n=277, med 9,18e-8, 99,64 % ≤1e-3 (1 phút 11:31) | ĐẠT | ĐẠT 276/276 | ĐẠT 100 % | ĐẠT 100 % | ĐẠT (yếu: 0 cặp r/q≥0,9; max 0,596) | ĐẠT 24/24, max rel 6,72e-10 | ĐẠT (OFF) | ĐẠT | 99,979 % ≤1e-6; 1 phút xấu 11:31 | **1** (11:31) | **XÁM** |
| 10-26 | KĐ | KĐ | KĐ (sel_dump=0) | ĐẠT 975.703 dòng 100 % | KĐ | KĐ | ĐẠT 24/24, max 6,72e-10 | ĐẠT (OFF) | ĐẠT (gate 1440, fund 47.964 dòng) | KĐ | — | **KHÔNG ĐO ĐƯỢC (XÁM)** |
| 10-27 | **TRƯỢT** n=1054, med 7,31e-8, **91,27 %** ≤1e-3, 92 phút lệch, max 2,63e-2 | ĐẠT | ĐẠT 941/941 | ĐẠT 100 % | ĐẠT 941 phút | ĐẠT (yếu: 0 cặp r/q≥0,9; max 0,623) | KĐ (thiếu 7 giờ) | ĐẠT (OFF) | ĐẠT | 86,60 % ≤1e-6; 41,66 % phút all-ok | **0** | **TRƯỢT** |
| 10-28 | KĐ (Vision) | ĐẠT 100 % | ĐẠT 1440/1440 | ĐẠT 980.327 dòng 100 % | ĐẠT 34.560/1440 100 % | KĐ (off); live 34.560 cặp, 0 pass, max r/q 0,679 | ĐẠT 24/24, max 4,96e-10 | ĐẠT (OFF) | KĐ (Vision) | KĐ | — | **KHÔNG ĐO ĐƯỢC (XÁM)** |
| 10-29 | KĐ (Vision) | ĐẠT 100 % | ĐẠT 1440/1440 | ĐẠT 999.075 dòng 100 % | ĐẠT 34.560/1440 100 % | KĐ (off); live 34.560 cặp, **93 pass**, **107 cặp r/q≥0,9**, max 2,186 | ĐẠT 24/24, max 5,73e-10 | KĐ (Vision 10-28 thiếu) | KĐ (Vision) | KĐ | — | **KHÔNG ĐO ĐƯỢC (XÁM)** |

Ghi chú:
- 10-25 K5=1 tại phút **11:31**; NET cũng xấu đúng phút này. Log `[LIVE-KLINE]` 11:41:06 có
  `decided_on_unsettled=74/7410`, `reread_overwritten=74` (cửa sổ 11:31–11:41), nhưng dev lan sang nhiều feature
  ngoài kênh r15 (advanceDecline, percentAboveMA20, volumeRatioUpDown, basket…) ⇒ `r15_channel=false`, nên K1″
  không áp; giữ K5. **CHƯA GIẢI THÍCH** nguyên nhân 74 dòng bị ghi đè ở phút này.
- 10-27 K5=0: 92 phút lệch P1 nằm trong 13:27–19:59, tất cả được gán K2b (Vision/store thiếu symbol) hoặc K3′;
  K2b phủ 1114 phút, K3′ 6 phút, K6′ 156 phút. Vì prereg §5 không loại phút khỏi ngưỡng, ngày vẫn TRƯỢT.
- 10-28/10-29: `data.binance.vision` daily kline 1m trả **404 cho toàn bộ 746/752 symbol** tại 09:05–09:10 +07
  ngày 10-30 (BTCUSDT-1m-2026-10-28/29 cũng 404). Vì vậy P1/P2-off/CTL **KHÔNG ĐO ĐƯỢC**, không phải ĐẠT.
  Watcher `aa84f195` sẽ chấm lại khi Vision phát hành (chờ tối đa 36 h) vì các ngày này chưa có `WATCH_DONE`.
- 10-29 TSX: Vision thiếu S 10-28 ⇒ cờ Vision = NA, live = OFF. Scorer cũ ghi TRUOT; đã sửa để NA ⇒
  **KHÔNG ĐO ĐƯỢC** (đúng prereg "NA ghi sổ"), xem §5.

## 4. Tích luỹ cửa sổ (10-21 .. 10-29)

- P2 cặp đo **cả hai phía** (ngày có Vision): **166.152** cặp; **28/28** cặp r/q≥0,9; 52 cặp ≥0,8; max off 1,657.
- P2 phía live (mọi ngày, kể cả 10-26/28/29): **235.272** cặp; **135** cặp r/q≥0,9; 190 cặp ≥0,8; max live 2,186.
- **0 lật nặng** ở mọi ngày đo được (10-25..27; 10-28/29 chưa có phía offline).
- Số ngày: ĐẠT 0 · XÁM 1 (10-25) · KHÔNG ĐO ĐƯỢC 3 (10-26/28/29) · **TRƯỢT 1 (10-27)** trong lượt D8.

## 5. Thay đổi code chấm (chỉ guard dữ liệu thiếu, KHÔNG đổi ngưỡng/định nghĩa)

1. `research/parity_v11/py/day_prep.py`: thêm `PV_ALLOW_INCOMPLETE=1` để chấm ngày pull INCOMPLETE trên các phút
   có dữ liệu; mặc định vẫn exit 2. Có cờ này ngày thiếu **không** được coi là ĐẠT.
2. `research/parity_v11/py/day_eval.py`: nếu `sel_dump` rỗng, vẫn ghi S1-m từ `s1_dump`; S1-I = KHÔNG ĐO ĐƯỢC
   thay vì crash `zero-size array`.
3. `research/parity_v11/py/day_tsx.py`: Vision flag `NaN` (State.NA) ⇒ KHÔNG ĐO ĐƯỢC, không ghi TRUOT.
4. `research/parity_v11/py/day_report.py`: S1-I có `frac=None` ⇒ KHÔNG ĐO ĐƯỢC, không ghi XÁM.

Artefact: `docs/result/parity_v11_d8/parity_v11_d8.json` + JSON từng ngày. Không xoá dữ liệu live/work của
các ngày (prereg §7 cần cho lượt M khi Vision monthly phát hành).
