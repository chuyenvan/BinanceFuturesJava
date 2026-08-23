# TRẠNG THÁI DỮ LIỆU WFO

> 🟢 **SECTION 0 = BẢN MỚI NHẤT (08/08 ~22:30 ICT, sau pivot Kaggle + dọn Kaggle).** Đo thật qua
> `kaggle datasets list -m` + `kaggle kernels status`. Phần "06:25" bên dưới giữ làm lịch sử.
> Liên quan: `claude/wfo_rerun_2026-08-08_ce.md` (mục 9 = label sharded), `claude/wfo_kaggle_parallel_plan_2026-08-08.md`.

## 0. TRẠNG THÁI TỪNG DỮ LIỆU (đo 08/08 22:30, Kaggle dùng ~61/100 GB sau dọn)

| Dữ liệu | Dataset Kaggle | Trạng thái | Cần làm / validate |
|---|---|---|---|
| **Label 1m** | (per-quarter cũ ĐÃ XOÁ vì hỏng) | 🔴 **ĐANG RE-EXPORT** 6 shard năm | Xong shard → gộp → push `funding-label-full-1m`. Verify: exit0 / không `.partN.pb` / 22 file quý / ~636M dòng |
| **tool1 features** | `funding-tool1-1m-*` **22/22 quý** (40.8GB) | 🟢 ĐỦ | ⚠️ 2024Q2/Q3 là **T1C1** (3 cột f20/f24/f26 sai ~1e-2); nguồn 2024Q2 đã xoá → sửa phải re-export Aerospike. Validate: per-cell + NaN vs nguồn |
| **OI per-coin** | `funding-oi-percoin` 3.2GB | 🟢 CÓ | 🟠 **coverage CHƯA verify** per-coin/khoảng (merge_asof tol 2h có thể lấp giá trị cũ âm thầm) |
| **symbol_map** | trong `funding-oi-percoin` | 🟢 XONG | — |
| **Gate pred** | `funding-gate-wfo-pred` 30MB + `gate-dataset-full` 361MB | 🟢 XONG | — |
| **Ticker 2021→2025** | `hpo-ticker-daily` 10.68GB | 🟢 XONG | — |
| **Ticker 2026-H1** | `hpo-ticker-2026` 2.72GB (mới có 08/08 02:17) | 🟢 **ĐÃ CÓ** (trước lo thiếu) | verify là full 2026H1 (đủ cho sim 2026) |
| **predict_wf (STAGE 1)** | chỉ có `funding-predict-1m-v1` 982MB (CŨ 22/06) | 🔴 **CHƯA CÓ bản mới** | regenerate SAU khi có label mới |
| **Built WFO ds (pred sẵn)** | chưa có `wfo_ds_LF_1m_..._h4h_v1` | 🔴 **CHƯA BUILD** | build_ds trên Oracle sau predict_wf (kẹt `code_sha=unknown`, xem dưới) |
| **jar** | `label-export-jar` (label), `java-run-lc`/`wfo-jar-1m` (sim file-mode) | 🟢 | — |

### Shard label lúc 22:30 (chi tiết ở `wfo_rerun` mục 9.5)
RUNNING (3, đúng cap Oracle=3 đồng thời): `label-export-2021/2022/2025`.
Cần chạy lại: `-2023`, `-2024` (fail vì Oracle drop connection khi >3 kernel — EOFException, KHÔNG phải
lỗi threads). Chưa push: `-2026h1`. Có launcher tự thả nốt (cron mỗi giờ :17) + trigger verify+gộp 07:00.

## 0b. CHUỖI CÒN PHẢI CHẠY (thứ tự bắt buộc — cái gì chặn cái gì)

1. 🔴 **Label** (đang chạy) → gộp `funding-label-full-1m` + verify bằng SỐ.
2. 🔴 **STAGE 1 selector-predict-1m**: regenerate `predict_wf` (cần label MỚI + tool1 + OI + map, tất cả file Kaggle).
3. 🔴 **build_ds** trên Oracle (đọc Aerospike live + gate + predict_wf) → `wfo_ds_LF_1m_h4h_v1`. SERIAL.
4. 🔴 **validate_canonical_wfo.py** + gate_sign (người).
5. 🔴 **WFO fanout** STAGE 2 (5 kernel Kaggle, pred sẵn trong pred.bin).

## 0c. VALIDATE CÒN THIẾU (chất lượng dữ liệu, làm trước khi tin kết quả)

- **Label**: đếm dòng thực từng shard (~636M tổng), không quý 0-byte, không `.partN.pb` (verify tự động khi shard xong).
- **Label 2026Q2 rỗng?** rủi ro `SymbolLifecycleManager.isAlive` chặn nếu lifecycle build trước 04/2026 → kiểm 2026Q2 có dòng không khi shard 2026h1 xong.
- **tool1 2024Q2/Q3 T1C1** sai ~1e-2 → nếu nằm trong OOS window thì nhiễm; sửa = re-export Aerospike.
- **OI coverage** per-coin chưa verify.
- **symbol_mapper** đối chiếu 242.

## 0d. 3 BLOCKER cho STAGE build_ds/WFO (chưa xử, KHÔNG chặn label — chi tiết `wfo_rerun` mục 5)

1. `ExportFundingLabel` exit 0 khi BLOCKED (latent, chưa kích hoạt vì lifecycle nạp OK).
2. WFO jobstore bẩn + trỏ box `226:3222` đã RETIRE → phải reset + quyết repoint `WFO_STATE_HOST`=Oracle.
3. Oracle repo không phải git → `code_sha=unknown` → `WfoDataset.export()` throw ở build_ds → truyền code_sha tường minh.

## 0e. DỌN KAGGLE (đã làm 08/08 22:30)

**ĐÃ XOÁ 23 dataset (~7 GB), 0 lỗi:** 17 label per-quarter cũ HỎNG (2021Q1→2025Q1) + `funding-label-1m-y2022`
+ `qtest-gz` + `qtest-dat` + `ticker-probe-1783948469` + 2 jar label trùng (`wfo-label-jar`, `wfo-label-jar-20260808`).
Kaggle: 68.4 → ~61 GB dùng.

**Ứng viên dọn TIẾP (chưa xoá, chờ Uni xác nhận vì mơ hồ hơn):**
- `funding-label-full` 2.44GB (label CŨ 21/06, trước thời 1m) — nhiều khả năng superseded.
- `funding-tool1-features` 4.86GB + `funding-tool1-features-unfiltered` 2.19GB (tool1 consolidated CŨ, đã có per-quarter thay) — cần chắc STAGE 1 không đọc tên này.
- `funding-predict-1m-v1` 982MB, `funding-predict-v1` 66MB, `funding-model-v1` (predict/model CŨ 21-22/06).
- `wfo-dataset-wf-v3`, `wfo-dataset-wf-leakfree`, `wfo-ds-ret2-4h-ff`, `wfo-oizgate`, `ablation-4h-ds` (artifact thí nghiệm cũ).
- Output các kernel cũ (`recovery-*`, `mae-dist`, `kv-*`, `wfo-selrank-*`, `wfo-verify*`, `wfo-label-y2021..2026h1`, `wfo-label-probe-1m`, `label-export-probe`) cũng ăn quota — có thể xoá kernel/output.

---

# (LỊCH SỬ) TRẠNG THÁI DỮ LIỆU WFO — bản 2026-08-08 06:25 ICT

> ⚠️ Bản này TRƯỚC pivot Kaggle. Label khi đó chưa chạy lại; nhiều số đã lỗi thời. Giữ để truy vết.

## 1. Tóm tắt một dòng

**Label phải EXPORT LẠI TOÀN BỘ** (2 lỗi ghi/gộp đã sửa xong, build OK, chưa chạy).
**tool1 đã xuất đủ 22/22 quý** nhưng đang nằm trên đĩa dạng cũ; dây chuyền convert sang `.t1c.gz`
+ push Kaggle + xoá local **đang chạy** để giải phóng đĩa (đĩa chỉ còn 7.4 GB — mức nguy hiểm).

## 3. 🔴 Label: hai lỗi cộng hưởng (ĐÃ SỬA)

**Lỗi A — mở lại file quý bằng GHI ĐÈ thay vì APPEND**: anchor "đến muộn" thuộc quý đã đóng ⇒ mở lại
⇒ truncate, mất phần đã ghi. **Lỗi B — bộ đếm gộp đếm SỐ LẦN ĐÓNG** thay vì số partition phân biệt ⇒
gộp sớm ⇒ file mồ côi. **Hệ quả C** — partition rỗng trong quý ⇒ quý không bao giờ được gộp.
Thiệt hại: 2024Q4 −29.37%, 2025Q1 −28.48%, 2025Q2 −28.69%; 2025Q3/Q4/2026Q1 chưa gộp; 2026Q2 chưa mở.
Đã sửa: gộp một lượt cuối (`mergeAllQuarters`), mở lại APPEND, kiểm hậu-export `countRowsInPb` (lệch ⇒
giữ `.partN` + exit 2). Test race: cũ mất 83.38% / mới mất 0. → jar `binance-label-1.2.4.jar` (đang dùng
trên Kaggle) CÓ bản vá này (đã xác nhận qua probe merge sạch).

## 4. tool1: format T1C2 (đã nâng từ T1C1)

T1C2 = magic + `wideMask` int64; cột `range/IQR>640` lưu int32 (4 stream byte-split). 3 cột wide về
4.5e-7, nén 3.78×, reader đọc được cả `.bin.gz`/T1C1/T1C2. ⚠️ 2024Q2/Q3 trên Kaggle vẫn T1C1 (nguồn
2024Q2 đã xoá → re-export Aerospike nếu muốn sửa).

## 5. Bài học verify

So size local vs Kaggle chỉ chứng minh upload không hỏng, KHÔNG chứng minh đủ dòng. Phải đối chiếu
số dòng thực với kỳ vọng; tool1 đối chiếu từng ô + vị trí NaN với nguồn.
