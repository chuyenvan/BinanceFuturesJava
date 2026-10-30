# PREREG_PARITY_V12_DRY — ADDENDUM 2: buffer seed 90 ngày cho gate (2026-10-30, viết TRƯỚC khi tính)

- Gốc: `PREREG_PARITY_V12_DRY.md` (3c7dae05) + ADDENDUM1 (7788cce9). MASTER gọi file này là "ADD1"; ADDENDUM1 đã có (implementer) ⇒ đánh số 2.
- Bối cảnh: GATE_STAB Pha 1 (prereg 29beac99, M 026bb92c): live v1.1 nạp r của coin đang giữ giấy (lệch sim); buffer live mới 30 ngày.
- Chưa tính bất kỳ số nào dưới đây.

## 1. Quy ước nạp r (= R4h, ADDENDUM1 §1.2; = sim)
K24 cap-then-skip theo hạng selector; symbol A1-loại (`UniverseA1Classifier`: TRADFI hoặc INDEX) bỏ hẳn; coin đang giữ trong sổ c3 (sim `isSymbolRunning`, dry = sổ giấy twin) đếm hạng nhưng KHÔNG nạp; LEGACY đếm hạng và nạp (chỉ live); sổ đầy (skipFull) ⇒ không nạp. r = p15/(max(0,26787, sp/0,15·1,2876)·1,55) float32.

## 2. Nguồn seed
- (A) sim-path: replay offline thuật toán `gate_offline` (đã kiểm DEV) trên đầu vào HO 2026 của run `nt-x14-s42`: `~/claude_master/1009/ho26/bins2026Ax` (sp = 1−p0), `stage_root/ds/market.bin` (lưới phút), p15 `stage_root/gate/pred_s42/pred.bin`, held = printDone `nt-x14-s42`, A1 theo exchangeInfo `v12/fixtures/exchangeInfo_20261027_1140.json.gz` (PIT gần đúng: symbol không có trong snapshot ⇒ giữ, ghi số). Cửa sổ [2026-07-03 00:00, 2026-10-01 00:00) +07 (dữ liệu sim hết 09-30).
- (B) live-path làm sạch: `gate_ratio_live.bin` 242 (md5 4e29c20c), ghép từng record với `sel_dump` theo (ts, r float32 tính lại); bỏ record A1-loại và coin đang giữ trong ShadowBookC3 (sự kiện open/closed trong full.log); record không ghép được ⇒ giữ, báo số.

## 3. Cổng chấp nhận (không nới)
- V-A (công cụ sim-path): recall lệnh PREDICT `nt-x14-s42` trong cửa sổ (A) ≥ 0,97 VÀ |số pass offline − số lệnh PREDICT sim| / sim ≤ 3 %.
- V-OVL (chồng lấn sim-path ↔ live, sau áp §1 cho cả hai, ghép theo (ts, symbol)): tập ô trùng ≥ 99 %; ≥ 99 % cặp |Δr|/r ≤ 1e-9; q từng giờ trùng |Δq| ≤ 1e-9 ở ≥ 99 % giờ. Lệch ⇒ chỉ ra nguồn (p15 live ≠ replay, sp net015 ≠ bins, held, universe), KHÔNG nới.
- Seed (A) chỉ được dùng cho dry khi V-A VÀ V-OVL đều ĐẠT. Nếu V-OVL chưa đo được (không có đầu vào sim tháng 10) ⇒ (A) chỉ là ứng viên; implementer KHÔNG nạp (A).
- Ghép (B) ≥ 99 % record; tỉ lệ ghép thấp hơn ⇒ (B) không đạt.
- M3 (chỉ đo): số và tỉ lệ record r của live buffer là TRADFI/INDEX; q từng giờ 10-30 khi bỏ TF/INDEX; khi bỏ thêm coin giữ giấy.

## 4. Đầu ra `~/claude_master/gst1030/seed/`
Định dạng y `GateRatioPersist`: chuỗi chunk [MAGIC 0x47525231 int32 BE][len int32 BE][crc32 của bytes nén, int32 BE][snappy(bản ghi BE {ts int64 ms UTC, r float32})], ts tăng dần; kèm md5, SPEC.txt, manifest.json. Không deploy, không ghi 242.
