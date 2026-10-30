# PREREG_HO2026_NOTF — ADDENDUM TECH-4 (2026-10-30)

Addendum **mới**, không sửa `PREREG_HO2026_NOTF_ADDENDUM_TECH.md` (T1–T5). Không đổi X, cấu hình, seed, thước,
luật D1–D5, không đổi kết luận nào. Hai nội dung: (T6) khai báo trung thực việc **định nghĩa lại V3**; (T7) **cổng
A0'(c)** — kiểm chain hạ nguồn với X = ∅ phải tái lập đúng pred md5 của `ho4p1-chain-y26`.

## T6. V3 đã được định nghĩa lại SAU khi kernel bị đánh fail — công bố đầy đủ

**Điều đã xảy ra (theo artefact, không suy đoán):**

1. Prereg §4 (96164b72) định nghĩa **V3 = "0 leg ∈ X trong printDone A1"** — đọc nguyên văn là **toàn bộ** file.
2. 24 kernel sim A1 được đẩy từ 10-28 10:20 (+07); `nt-k24-s-s42` COMPLETE lúc 10-28 10:20:59
   (`~/claude_master/ho_tradfi_wk/notf_state.json`). Mỗi file A1 có **2–5 leg X ở đoạn DEV** (DEFIUSDT/BTCDOMUSDT
   2021–2024). Theo định nghĩa nguyên văn ⇒ **V3 FAIL cho cả 24 kernel**; orchestrator đánh dấu `state=failed`.
3. **10-28 11:13:10** — `research/ho2026_notf/notf_orch.py` được sửa trong working tree
   (`stat`: mtime `2026-10-28 11:13:10.122203503 +0700`). Diff so bản đã commit `6b9ccd33`:
   - thêm `x_legs_2026` = số leg X có `start ≥ 20260101` **hoặc** `end ≥ 20260101`;
   - đổi điều kiện pass từ `x_legs == 0` → `x_legs_2026 == 0`;
   - thêm nhánh **REPOST**: chỉ chạy cho `state == "failed"`, `kstatus == "COMPLETE"`, tag `nt-*` — tức nhánh này
     **chỉ có nghĩa nếu trước đó đã có kernel bị fail**.
4. Cùng giây 11:13:10, 4 file `res/nt-*.json` đầu tiên được ghi lại: `pass=true`, `x_legs=3`, `x_legs_2026=0`
   (24/24 file có `x_legs` 2–5 và `x_legs_2026` 0). Tức **chấm lại bằng định nghĩa mới ngay sau khi sửa**.
5. **10-29 12:32** — commit `adf5bb57` (ADDENDUM_TECH-3) mới ghi lại: *"Diễn giải V3 (nêu rõ để MASTER biết, không
   đổi luật): V3 … được đọc là trong cửa sổ chấm A1 (2026)"*. `git blame` xác nhận dòng `x_legs_2026` vào repo ở
   commit này; trước đó nó chỉ tồn tại trong working tree.

**Đánh giá trung thực:**

- Việc đổi định nghĩa xảy ra **trước khi bất kỳ số A1 nào được chấm** (mọi `res/nt-*.json` đều ≥ 11:13:10 cùng ngày),
  nên **không** phải sửa luật sau khi thấy kết quả chiến lược. Nhưng nó **là** đổi luật sau khi thấy **cổng fail**,
  và **không có addendum commit trước** ở thời điểm đổi — chỉ được ghi lại 29 h sau (T5, 10-29) và công bố đầy đủ
  trong mục này (10-30).
- Vì vậy trạng thái V3 phải ghi **hai dòng**, không được chỉ ghi "PASS":
  - **V3 theo định nghĩa nguyên văn (prereg §4): FAIL** — 24/24 kernel có leg X trong printDone (đoạn DEV).
  - **V3 theo định nghĩa 2026 (định nghĩa lại 10-28 11:13): PASS** — 24/24 kernel có 0 leg X trong cửa sổ chấm.
- Lý do kỹ thuật của việc đọc theo 2026 là **có thật**: §2 buộc đoạn `start < 20251224` giữ **nguyên byte** như chuỗi
  gốc, mà chuỗi gốc có leg DEFI/BTCDOM (INDEX) 2021–2024 ⇒ đọc literal thì V3 **không thể** đạt với bất kỳ universe
  nào. Nhưng "không thể đạt" **không** tự động biến thành "được đổi định nghĩa": cần MASTER phê chuẩn cách đọc 2026.
- Không có log `orch.log` (file 0 byte) nên **không còn dòng `POST … pass=False`**; bằng chứng fail là: (i) diff có nhánh
  REPOST chỉ kích hoạt khi `state=failed`; (ii) mtime file sửa = giây đầu tiên res được ghi lại; (iii) dưới định nghĩa
  cũ (2–5 leg X/printDone) mọi kernel buộc phải fail. Đây là suy luận từ artefact, **không phải log gốc**.

## T7. Cổng A0'(c) — chain hạ nguồn với X = ∅ phải tái lập pred md5 gốc

**Mục đích.** Chứng minh bản chain đã sửa (thêm `X_IDS` vào `DUP_IDS`) **không có tác dụng phụ** khi X rỗng: đầu ra
phải **byte-identical** với `ho4p1-chain-y26` gốc.

**Thiết kế (chốt trước khi đọc kết quả).**

- Kernel `chuyendinh/a0p3-chain-y26nox`: copy nguyên `run.py` của `nt-chain-y26` (cùng `ho4p1_chain.py`, cùng model
  sha, cùng `pin_sha`), chỉ đổi:
  - `tag = a0p3-chain-y26nox`;
  - `exclude_syms = []`, `exclude_md5 = md5("\\n") = 68b329da9893e34099c7d8ad5cb9c940`;
  - `q_src` = **nguồn gốc** `ho4p1-x26-q1/q2/q3` (không dùng `nt-x26-*` đã loại X) để so đúng chuỗi gốc.
- Nguồn phụ thuộc: `ho4p1-code`, `funding-oi-percoin`, `sim-ho26a-bundle`, `ho26-pred-s*` (dataset);
  `ho4p1-oi-a`, `ho4p1-x26-q1..3` (kernel output) — đúng như lần chạy gốc.
- **PASS** ⇔ `steps.pred["42"].md5` == `b692f1346936a6368ccc1d19619bef4a` (giá trị trong
  `~/claude_master/1011/ho4p1/kaggle/out/ho4p1-chain-y26/result.json`); kiểm thêm seed 7
  (`bcf5689811bd2487cf14b29ced15654d`) và **toàn bộ `steps.pred[*].md5`** nếu rẻ (kernel tính cả 8 seed).
- **FAIL** ⇒ ghi rõ lệch bao nhiêu (số seed lệch, md5 nhận được) và **không** sửa kết luận `HO2026_NOTF` nào.
- Kiểm phụ (không thuộc tiêu chí): `MANIFEST.json` md5 từng file so với manifest gốc trong `result.json`.

**Trạng thái:** kernel đẩy 2026-10-30 (1 kernel, không dùng thêm quota ngoài 8). Kết quả ghi ở
`docs/result/HO2026_NOTF_A0PC.md` khi chạy xong; addendum này **không** chứa kết quả.
