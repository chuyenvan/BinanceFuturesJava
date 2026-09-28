# RESULT_TAIL25 — ĐO LẠI RÀO (b′) ĐÚNG MỨC **BỎ TOP-25 %** + TỔNG HỢP PASS/FAIL (a)+(b′)

**Ngày:** 2026-09-28 · **Nhánh:** `module` · **Trạng thái:** ĐO XONG
**Pre-reg:** `docs/prereg/PREREG_TAIL25.md` (commit `2e34bf7`) — chốt **TRƯỚC** khi đọc số (không đổi).
**Code:** `research/analysis/tail25_ruler.py` · **Số:** `docs/result/TAIL25_RULER.json` (35 KB) · thô `/tmp/t25/`.
**KHÔNG** train, **KHÔNG** sim/Java, **KHÔNG** chạm `242`/ONNX/LIVE. DEV only (`start <= 2025-12-31`, không đọc 2026).
**Nguồn leg:** `storage/printDone.csv` của từng biến thể — **đúng artifact đã sinh `76cc051`**.
*(`P32 = label_b_pnl.parquet` là pool 32 leg/tick **không mã hoá gate** của 8 biến thể ⇒ không tái lập được `76cc051` ⇒ không dùng làm nguồn; ghi rõ.)*

---

## 1. SANITY — BẮT BUỘC (tái lập `76cc051`)

**`sanity_all_match = TRUE`, `sanity_mismatch = []`** — `TF(20 %)` và `TF(30 %)` **khớp tuyệt đối** số `76cc051`
(`rate_redundancy`: TF20 `q995 +772 · q998 +4180 · q999 +2901 · q998-15m +5848`, `KEEPLEG0 −1575 · T170 −1723 ·
GD92 −61183 · T100 −76850`; TF30 `q998-15m +2328` + 7 mức âm). **Số 25 % vì vậy đáng tin.**

## 2. ĐƯỜNG CONG `TF(x %)` — bỏ top-`x`% leg, PnL còn lại (USDT, toàn kỳ)

| biến thể | 0 % | 5 % | 10 % | 15 % | **20 %** | **25 %** | **30 %** |
|---|---:|---:|---:|---:|---:|---:|---:|
| KEEPLEG0 | 68083 | 30416 | 16360 | 6447 | −1575 | **−8535** | −14532 |
| T170 | 76070 | 32922 | 17650 | 6781 | −1723 | **−9120** | −15529 |
| T100 | 86770 | 2771 | −31294 | −56411 | −76850 | **−94423** | −109754 |
| GD92 | 98944 | 14794 | −18167 | −41770 | −61183 | **−77389** | −91761 |
| kg0-q995 | 64531 | 31099 | 17918 | 8519 | +772 | **−5792** | −11554 |
| kg0-q998 | 62674 | 32292 | 19999 | 11284 | +4180 | **−2064** | −7515 |
| kg0-q999 | 55699 | 28379 | 17449 | 9358 | +2901 | **−2706** | −7726 |
| kg0-q998-15m | 21149 | 14043 | 10512 | 7911 | +5848 | **+4002** | +2328 |

⇒ **(b′) bỏ-25 % = 1/8 dương (`kg0-q998-15m`)** — đúng giữa 20 % (4/8) và 30 % (1/8).

**Từng năm ở mức 25 %** (`TF25 > 0`): **CHỈ `kg0-q998-15m`** dương **cả 5/5 năm** (2021 +680 · 2022 +1565 ·
2023 +850 · 2024 +346 · 2025 +634). Các biến thể khác dương 2021/2023/2024 nhưng **âm ở 2022 và 2025**
(ví dụ `kg0-q998`: 2022 −946, 2025 −4889).

## 3. BẢNG TỔNG HỢP PASS/FAIL 8 BIẾN THỂ

Rào **(a)** = `%PnL top-1 % ≤ 15 %` · rào **(b′)** = `TF(25 %) > 0`.
CI `TF(25 %)`: bootstrap **khối 72 h · 2000 rep · seed 20260905 · `inflate(8)=2,0393`**.
**"ngoài CI"** ⟺ ngoài **cả** `raw95` **và** `inflate(8)`.

| biến thể | (a) %top-1 | **(a)** | `TF25` | CI raw95 | CI inflate8 | **ngoài CI** | **`q*`** | **(b′) 25 %** |
|---|---:|:--:|---:|:--:|:--:|:--:|---:|:--:|
| KEEPLEG0 | 23,74 | ❌ | −8535 | [−28568, +6738] | [−49388, +22613] | ✗ (chứa 0) | 19,0 % | ❌ |
| T170 | 25,90 | ❌ | −9120 | [−30246, +8711] | [−52204, +27243] | ✗ (chứa 0) | 19,0 % | ❌ |
| T100 | 40,85 | ❌ | −94423 | [−127526, −62304] | [−161930, −28922] | ✅ (âm chắc) | 5,5 % | ❌ |
| GD92 | 37,75 | ❌ | −77389 | [−108912, −48823] | [−141674, −19133] | ✅ (âm chắc) | 7,0 % | ❌ |
| kg0-q995 | 21,58 | ❌ | −5792 | [−23464, +9056] | [−41831, +24488] | ✗ (chứa 0) | 21,0 % | ❌ |
| kg0-q998 | 20,70 | ❌ | −2064 | [−20525, +11761] | [−39712, +26131] | ✗ (chứa 0) | 23,5 % | ❌ |
| kg0-q999 | 21,04 | ❌ | −2706 | [−19495, +11132] | [−36943, +25514] | ✗ (chứa 0) | 22,5 % | ❌ |
| kg0-q998-15m | **12,91** | ✅ | **+4002** | [−2140, +9199] | [−8523, +14600] | ✗ (chứa 0) | 38,0 % | **✅** |

- **(a): 1/8 PASS** (`kg0-q998-15m` 12,91 %). Các arm `kg0-q99x` = 20,70–21,58 % (**sát ngưỡng** nhưng **FAIL**);
  `KEEPLEG0` 23,74 · `T170` 25,90 · `GD92` 37,75 · `T100` 40,85.
- **`q*`** (bỏ bao nhiêu % thì PnL = 0) — **ai sát 25 % nhất:** `kg0-q998` **23,5 %** · `kg0-q999` 22,5 % ·
  `kg0-q995` 21,0 % (nhóm kg0-q99x) ; `KEEPLEG0`/`T170` 19,0 % · `GD92` 7,0 % · `T100` 5,5 % · `kg0-q998-15m` 38,0 %.
  ⇒ **25 % vượt `q*` của 7/8 biến thể** (chỉ `15m` có `q*=38 %>25`).

## 4. KẾT LUẬN — CÓ BIẾN THỂ NÀO PASS CẢ HAI?

**Duy nhất 1/8: `kg0-q998-15m`** (a 12,91 % ✅ · TF25 +4002 ✅). **7/8 còn lại fail CẢ HAI hoặc ít nhất một.**

⚠️ **Nhưng `kg0-q998-15m` VẪN KHÔNG DEPLOY ĐƯỢC** vì **2 lý do đã biết, đo lại vẫn đúng:**
1. **Trượt bài kiểm nhịp** — nó chạy nhịp **15′**, **không** tái lập được nhịp **live 1′**:
   **0,255 vs 0,660 entry/ngày ⇒ tỷ lệ `0,440 < 0,60`**, `CAGR 11,08 %` vs `27,14 %` (`8ddc173`). ⇒ mô phỏng
   **không** phản ánh vận hành live.
2. **CI `TF25` CHỨA 0** (`raw95 [−2140, +9199]`, `inflate8 [−8523, +14600]`) ⇒ **dương nhưng KHÔNG ý nghĩa**
   ở mức 25 % (khác hẳn 7 biến thể kia còn **âm cả 2 đầu** hoặc bao 0).

⇒ **Dưới (a)=15 % + (b′)=25 %: KHÔNG cấu hình nào deploy được** (PASS cả hai duy nhất là `15m`, mà nó trượt
bài kiểm nhịp + CI chứa 0). Đây là **kết luận bằng số**, không suy diễn.

## 5. HAI LỰA CHỌN (số cụ thể, đo sẵn)

1. **Nâng (a) + hạ lại (b′) — "cứu" nhóm `kg0-q99x`:** nâng **(a) lên ≈ 24 %** (đủ phủ `q995` 21,58 · `q998` 20,70 ·
   `q999` 21,04 · `KEEPLEG0` 23,74; **KHÔNG** phủ `T170` 25,90) **VÀ** trả **(b′) về 20 %** (mức 25 % vẫn giết
   `q995/q998/q999`: TF25 −5792/−2064/−2706). Kết quả đo sẵn: **(a)=24 % + (b′)=20 % ⇒ 4/8 PASS cả hai**
   (`q995`+772 · `q998`+4180 · `q999`+2901 · `15m`+5848). **Đánh đổi:** đi ngược quyết định owner (25 %).
2. **Giữ (a)=15 % + (b′)=25 %, ĐỔI HỌ CHIẾN LƯỢC Ở PHÍA TÍN HIỆU** (không chỉnh ngưỡng `q`): mắt xích phải
   đổi = **mất cân xứng độ lớn** (`|loss|/win = 2,9–3,6×`, `76cc051` §4). Chỉnh ngưỡng `q` **không** tạo được
   cấu hình nào (đã quét: **PASS cả hai = 0 nếu loại `15m`**).

**Đề xuất:** chọn **LỰA CHỌN 2** làm hướng chính (giữ đúng quyết định owner), **LỰA CHỌN 1** chỉ là phương án
"tạm mở" nếu chấp nhận lùi `(b′)` — vì nó chỉ cứu được nhóm `kg0-q99x` **và** phải hy sinh ngưỡng 25 %.
