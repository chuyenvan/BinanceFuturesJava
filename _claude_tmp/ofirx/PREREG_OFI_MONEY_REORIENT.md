# PREREG_OFI_MONEY_REORIENT — chạy lại OFI_MONEY với **ĐÚNG CHIỀU ĐIỂM** (ORIENT = −1)

**Ngày:** 2026-09-28 · **Nhánh:** `module` · **Trạng thái:** CHỐT **TRƯỚC** khi tính bất kỳ số kết quả nào của vòng này.
**Nội dung tiêu chí:** do MASTER chốt (audit 09-28, `B_bugs` mục OFI_MONEY). Executor chỉ điền phần kỹ thuật (§6 đường dẫn/lệnh).
**Kế thừa:** `docs/prereg/PREREG_OFI_MONEY.md` (`4948795`) · `docs/result/RESULT_OFI_MONEY.md` (`96a08e5`) ·
`docs/result/RESULT_TAIL_ROBUST_RULERS.md` §2 (lỗi chiều điểm) · errata `RESULT_GROSS_ASYMMAP` (09-27).

---

## 0. LỖI ĐƯỢC SỬA (đã xác nhận bằng code + số, Bước 0)

Điểm trong `pred_ofi_candidate_v2 / pred_baseline_fresh / pred_ofi_noise_v2` (kernel `ofi-v3-ms-s43/44/45`) là
`score = −pred` (**THẤP = TỐT**; `research/pipeline/x1/kaggle_ofi_v3/ofi_train_eval_v3.py:153,177`), nhưng
`ofi_money_score.py:149,165` và `ofi_money_ext.py:106` chọn top-K bằng `argsort(−score)` ⇒ chọn nhầm coin **TỆ NHẤT**.
Pool B2 (`label_b_pnl_ext.parquet`) cũng dựng từ top-K sai chiều ⇒ phải dựng lại.

**Bước 0 (kiểm trước, KHÔNG phải kết quả tiền) — ĐÃ CHẠY, XÁC NHẬN LỖI** (`step0_orient.py`, pool P32, rank 0 = S1 tốt nhất):
Spearman TB/tick `(score, rank_pool)` = **+0,87…+0,94** (dương ⇒ score thấp = rank tốt) cho cả 3 đối tượng × 4 seed + ensemble;
mean-rank top-8: chiều CŨ `argsort(−score)` = **25,1…26,4** · chiều SỬA `argsort(+score)` = **3,89…4,32**
(ensemble 43/44/45: candidate 25,85 → 4,09 · baseline_fresh 26,41 → 3,89 · noise 26,35 → 3,89) — khớp kỳ vọng 3,5–4,5.

## 1. THIẾT KẾ — GIỮ NGUYÊN `PREREG_OFI_MONEY` (4948795)

- Đối tượng: `candidate` / `baseline_fresh` / `noise_ofi_check`; điểm **ensemble 3 seed 43/44/45** (+ báo từng seed).
- `K = 8` chính (báo thêm 16/32; lưới chấm vẫn `{8,10,12,16,32}` như cũ); `f ∈ {0 · 0,004 · 0,006 · 0,008}`.
- CI block-72h, `NREP 2000`, seed `20260905`, paired; `k = 5` chính (inflate **1,7941**), báo `k = 2`, `k = 10`.
- Pool: đường **RE `P32`** + **B2 mở rộng** — dựng lại nhãn luật thoát cho các cặp coin **MỚI** mà top-K **ĐÚNG CHIỀU**
  đòi hỏi (hợp top-8 của 3 đối tượng × 3 seed 43/44/45, trừ `P32`), bằng **đúng** kernel/engine cũ `ofi-ext-labelb-cpu`
  (`mr_label_build.py` + `exit_engine.py`, `KMAX=64`, `CHUNK_DAYS=90`, `TS_MAX_MS=1758992400000`), **tag MỚI**.

## 2. THAY ĐỔI DUY NHẤT

**`ORIENT = −1` cho cả 3 đối tượng** (chọn top-K theo score **THẤP** nhất). Mọi thứ khác giữ nguyên.

## 3. AMENDMENT kèm (lý do: errata `GROSS_ASYMMAP` 09-27)

Định nghĩa gross theo pool lệch 46×; trần 70 % **KHÔNG bind** ở `K=8` theo định nghĩa ledger ⇒ chỉ số **QUYẾT ĐỊNH**
(`dnet_gr1dv`) tính **KHÔNG áp trần**; bản áp trần theo cách cũ (A / B95 / Bmax) chỉ báo cáo **phụ**.
(`net_gr1dv` vốn bất biến size ⇒ amendment này không đổi con số quyết định, chỉ bỏ điều kiện "dưới trần 70 %" khỏi luật.)

## 4. LUẬT "CÓ GIÁ TRỊ TIỀN" (giữ nguyên)

Tại `f = 0,006`, `K = 8`: `dnet_gr1dv(candidate − baseline_fresh)` **VÀ** `dnet_gr1dv(candidate − noise_ofi_check)` đều
**NGOÀI CI cùng chiều DƯƠNG** (`k = 5`), **VÀ** dương ở **≥ 2/3 seed** riêng lẻ (43/44/45) — áp cho **từng** hiệu.
Luật được đánh giá trên **cả 2 đường** (RE `P32` và B2 mở rộng) và báo **cả hai**; executor **không** tự chọn đường
khi hai đường khác kết luận — báo nguyên trạng cho MASTER.

**Kiểm hợp lệ bắt buộc:**
1. `noise − candidate` **không** được dương ngoài CI (`k = 5`) — nếu có ⇒ HARNESS NGHI NGỜ, không công bố verdict.
2. `dnet_coin` **bất biến theo `f`** (lệch `0,00e+00` trên 4 mức phí).
3. `K = 32` trên `P32`: ba đối tượng **trùng khít** (Δ = 0 tuyệt đối).
4. **B1** (% global top-K ngoài `P32`) phải được báo. **DỰ BÁO ghi trước:** sau sửa B1 giảm mạnh (**< 10 %**).
5. **Tái lập:** chạy `v2 --orient +1` phải ra **LẠI ĐÚNG** số `RESULT_OFI_MONEY` cũ trên `P32` (`docs/result/ofi_money.json`)
   ⇒ chứng minh chỉ khác chiều. Tương tự builder B2 `--orient +1` phải dựng lại **đúng** file ứng viên cũ
   (`chuyendinh/ofi-money-ext-trades`, 166.080 cặp).

## 5. BÁO MÔ TẢ THÊM (KHÔNG dùng quyết định)

4 thước chuẩn `wl_ratio · tf_5 · loss_mean · conc_5` (định nghĩa `research/analysis/tail_robust_rulers.py`, `tick_agg`/`POINT`,
top-8, `f = 0,006`) cho 3 đối tượng (ensemble, ORIENT = −1), trên cả 2 pool.

**DỰ BÁO MASTER ghi trước:** Δ vẫn **nhiều khả năng TRONG CI** (OFI chỉ +0,0026 rank-IC ở tầng model), nhưng **không loại trừ dương**.

## 6. CÁCH CHẠY / ĐƯỜNG DẪN (kỹ thuật, không đổi tiêu chí)

- Điểm: tải lại output kernel `chuyendinh/ofi-v3-ms-s{42,43,44,45}` → `/home/ubuntu/claude_audit_0928/ofirx/kout{42..45}/`
  (3 `pred_*.parquet`, xoá sau khi xong).
- Code MỚI (bản cũ **không sửa**, giữ tái lập): `research/analysis/ofi_money_score_v2.py`, `research/analysis/ofi_money_ext_v2.py`
  (tham số `--orient`, mặc định −1: điểm xếp hạng = `ORIENT·score`), `research/analysis/ofi_ext_trades_build.py` (dựng file ứng viên
  B2), `research/analysis/ofi_reorient_rulers.py` (4 thước mô tả), `research/kaggle/ofi_money/make_ofi_ext_kernel_v2.py`
  (kernel cũ, chỉ đổi tag/dataset).
- Lệnh:
  1. Tái lập RE: `python3 research/analysis/ofi_money_score_v2.py --kdirs $W/kout42,$W/kout43,$W/kout44,$W/kout45 --orient 1 --out $W/ofi_money_orient_p1.json` → so với `docs/result/ofi_money.json`.
  2. RE đúng chiều: `... --orient -1 --out docs/result/ofi_money_reorient.json` (in B1).
  3. B2: `ofi_ext_trades_build.py --orient 1 --compare <file cũ>` (tái lập), rồi `--orient -1` → dataset `chuyendinh/ofi-money-ext-trades-reorient`
     → kernel `chuyendinh/ofi-ext-labelb-cpu-reorient` (Kaggle CPU; ước > 4 h ⇒ báo MASTER) → `/home/ubuntu/ofi_v3/ofimoney/label_b_pnl_ext_reorient.parquet`.
  4. `ofi_money_ext_v2.py --extra <nhãn mới> --orient -1 --out docs/result/ofi_money_ext_reorient.json`.
  5. Mô tả: `ofi_reorient_rulers.py` → `docs/result/ofi_reorient_rulers.json`.
- Kết quả: `docs/result/RESULT_OFI_MONEY_REORIENT.md` + các json trên. Commit, **KHÔNG push**.

---

**Đóng băng:** đối tượng · ensemble seed · pool · K · phí · chỉ số quyết định · k · luật (kể cả ≥2/3 seed) · kiểm hợp lệ ·
dự báo B1 < 10 % · amendment trần — chốt **TRƯỚC** khi tính số.
