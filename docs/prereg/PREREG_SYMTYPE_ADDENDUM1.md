# PREREG_SYMTYPE — ADDENDUM ADD-1 (2026-10-30)

Addendum **mới**; không sửa `PREREG_SYMTYPE.md` (3d890188) hay `SYMTYPE.md` (e63fb0d8). Không đổi luật quyết.
Ba nội dung: (A) khai lệch định nghĩa B1 + thời điểm chốt; (B) khai bug chuẩn hoá `base()` và bản R2;
(C) hệ quả của (A) lên con số "B1 = 0 leg DEV".

## A. Lệch định nghĩa B1 và thời điểm chốt — khai trung thực

- Prereg (15:42:04 +07, 10-28) ghi B1 = *"contractType TRADIFI_PERPETUAL **hoặc underlyingType≠COIN**"*.
  Đọc nguyên văn, **INDEX** (BTCDOM/DEFI/…) cũng ≠ COIN ⇒ rơi vào B1, và B2 (INDEX/hàng hoá/stable) **rỗng** —
  mâu thuẫn ngay trong prereg.
- Bản đã dùng (15:52:44, cùng commit với kết quả) thay bằng **`TradFiClassifier`** của `HO2026_TRADFI_AUDIT`:
  `ct` chứa TRADIFI/TRADFI **hoặc** `ut ∈ {EQUITY, HK_EQUITY, KR_EQUITY, CN_EQUITY, COMMODITY, FX}`;
  INDEX/PREMARKET xử lý như audit (INDEX → B2, PREMARKET → crypto).
- **Thời điểm:** định nghĩa thay thế chỉ xuất hiện trong **doc kết quả** (15:52), **không có addendum prereg trước khi đo**
  (prereg 15:42 → kết quả 15:52, cách nhau 10 phút). Vì vậy **không thể chứng minh** nó được chốt trước khi thấy số.
  Đây là khai báo trung thực: **chốt SAU prereg, cùng lúc với kết quả**, không phải "trước kết quả".
- Yếu tố giảm nhẹ (không thay đổi việc phải khai): classifier đã tồn tại từ `HO2026_TRADFI_AUDIT` (10-23) và là định
  nghĩa **hẹp hơn** (loại INDEX khỏi B1) — tức nó **không** được chọn theo hướng có lợi cho kết luận "giữ": xem §C,
  đọc literal thì B1 vẫn không đủ điều kiện loại.

## B. Bug chuẩn hoá `base()` và bản R2

- `symtype_wk/prep_legs.py` (bản 10-28) cắt tiền tố `1000`/`1000000` **vô điều kiện**:
  `1000SATSUSDT → SATS`, `1000CATUSDT → CAT`, `1000CHEEMSUSDT → CHEEMS`. Ba tên này **là spot thật** trên Binance
  ⇒ tra spot theo `SATSUSDT/CATUSDT/CHEEMSUSDT` (không tồn tại) ⇒ gán **B3 sai**.
- Sửa (R2): ưu tiên **tên spot khớp nguyên văn** (đọc từ `spot_out/spot_sym_months.csv`), chỉ khi không có mới bỏ tiền tố.
  Đồng thời sửa lỗi thứ hai: `legs_all.parquet` được ghi **trước** khi thêm cột `base` ⇒ chuyển ghi xuống sau.
- **Không chạy lại kernel spot**: `spot_sym_months.csv` đã phủ 755 symbol spot gồm cả 3 tên 1000X; chỉ cách tra là sai.
- Kết quả R2: `symtype_metrics_r2.json`, `validate_r2.json`, `tables_vi_r2.md`, doc `docs/result/SYMTYPE_R2.md`.
  Bản R1 giữ nguyên (`symtype_metrics_r1.json`, `validate_r1.json`, `tables_vi_r1.md`, doc `SYMTYPE.md`).

## C. Hệ quả của định nghĩa B1 lên "B1 = 0 leg ở DEV"

Đọc **literal** prereg (`ut ≠ COIN`), DEV sẽ có **17 leg B1** (DEFIUSDT 2022–2024, PnL −66,9; MDTUSDT 35 leg bị
PIT-guard loại nhãn vì ticker tái sử dụng) và **B2 rỗng**. 17 < 300 ⇒ điều kiện (ii) **vẫn không đạt**, kết luận
"GIỮ, chỉ theo dõi" cho B1 **không đổi**. Nhưng câu "DEV B1 = 0 leg" trong `SYMTYPE.md` §0/§3/§6.2 **chỉ đúng dưới
định nghĩa classifier**; ghi rõ ở đây để không ai trích "B1 chưa từng tồn tại trong DEV" như sự thật tuyệt đối.

Không đổi luật, ngưỡng, universe hay bất kỳ kết luận nào khác.
