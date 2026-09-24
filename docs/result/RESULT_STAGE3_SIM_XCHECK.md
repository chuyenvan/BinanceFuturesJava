# RESULT_STAGE3_SIM_XCHECK — đối chiếu ĐỘC LẬP 3 kênh sim Stage 3 (đường Java export trên Kaggle)

**Ngày:** 2026-09-25 · **Nhánh:** `module` · **Trạng thái:** ĐO XONG — **KHÔNG dùng làm bằng chứng quyết định**
**Liên quan:** `docs/result/RESULT_STAGE3_SIM.md` (kết quả CHÍNH, commit `d94b61d`) ·
`docs/prereg/PREREG_STAGE2_FEATVAR.md` (commit `dd27c6c`)
**Mục đích:** đối chiếu **độc lập** kết quả sim đã công bố bằng một đường hạ tầng KHÁC, để phát hiện
lỗi cài đặt. Đây là **kiểm tra chéo**, không phải một vòng thí nghiệm mới; **không** đổi tiêu chí/luật nào.

---

## 0. Đã chạy gì

| | |
|---|---|
| Kernel | `chuyendinh/g015p2-s3sim-v0` · `-v1` · `-v5` (Kaggle **CPU**, không tính quota) |
| Đường | 2 bước Java TRONG kernel: `ExportWfoDataset` (đọc market+gate pred từ Aerospike 226, đọc bins từ `WFO_FUNDING_PRED_DIR`) → `SimulatorMarketLevelTicker1MStopLoss` |
| Profile | `profiles/t170_flat_keepleg0.properties` **NGUYÊN VĂN**, chỉ đổi dòng `WFO_FUNDING_PRED_DIR` |
| Bins | 18 bin: 16 fold `20220101..20251001` (kernel `g015p2-stage2-featvar-gpu`) + 2 fold `20210701/20211001` (kernel `g015p2-stage3-y21fold-gpu`), map sang thứ tự S1 bằng `c4_build_map.py s1a2x1` (+ `s1a2x1_y21`) với `ledger/pred_s1a2x1.parquet` |
| Cửa sổ | `SIM_END_DATE=20251231` ⇒ dataset `leakFreeFrom=2021-07-01`, `foldCount=18` ✓ | 
| jar | sha256 `2c2f8aef…` (= jar của bundle) · mapper 863 ✓ |

## 1. ⚠️ CỔNG PARITY: đường này **KHÔNG** qua được cổng `99e42b75` — và vì sao (đã truy nguyên)

Chân đối chứng `PARITY` (export từ **bins của chính bundle**) cho
**equity 91.871 · n=936 · md5 `810ed30e187d21a9687790dfc873f602`** ⇒ **KHÁC** mốc
`99e42b75…` / 1.085 / 103.083.

Nguyên nhân đo được, **không** phải lỗi export: kernel log/manifest cho thấy
`WRONG_SOURCE` — `sim-x1-2021-bundle` **chỉ ship 16 bin (2022+)**; 2 bin `20210701/20211001` **không có**
trong bundle (xem `docs/runbooks/KAGGLE_SIM.md` §3: mục `predict_wf_*.bin` của bundle).
⇒ export lại từ bundle sinh dataset `leakFreeFrom=2022-01-01`, `foldCount=16` — **thiếu 2021H2**, nên sim
khác mốc. (Dataset **đóng băng** `funding.bin` 4 GB trong bundle thì vẫn phủ 18 fold, do dựng từ
`predwf_map_s1a2_x1_2021` — tức bundle **tự không nhất quán** giữa `funding.bin` và bộ bins kèm theo.)

**Hệ quả quy trình:** đường "đổi bins" trên Kaggle **bắt buộc** phải tự cấp **đủ 18 bin**; không thể
lấy 16 bin của bundle. Cổng parity `99e42b75` vì vậy **chỉ** kiểm được bằng đường đã công bố
(`d94b61d`: funding dựng lại byte-faithful + bins 18 fold của MOC) — đường đó **PASS**.

## 2. Bảng đối chiếu (cùng profile, cùng cửa sổ, cùng 18 fold; khác đường cài đặt)

| kênh | **đã công bố** (`d94b61d`) n / equity | **đối chiếu độc lập** (tài liệu này) n / equity | lệch equity |
|---|---|---|---|
| MỐC 45 feat | 1.085 / 103.083 | — (không chạy lại; xem §1) | — |
| **V0** (21 keeper) | 1.200 / 88.146 | **1.247 / 84.852** | −3,7 % |
| **V1** (21+5 thật) | 1.268 / 95.405 | **1.262 / 97.202** | +1,9 % |
| **V5** (21+5+5 nhiễu) | 1.239 / 93.632 | **1.236 / 95.976** | +2,5 % |

- **Thứ tự khớp:** cả hai đường đều cho `V1 > V5 > V0` theo equity, và **V0 có nhiều lệnh nhất**
  (1.247 / 1.200) — cùng dấu với kết luận "V0 xấu hơn ở tầng chất lượng lệnh" của `d94b61d`.
- **Mức lệch 1,9–3,7 %** (không byte-identical) ⇒ **kết luận:** đường đối chiếu này **chưa qua cổng parity**
  nên số của nó **KHÔNG** được dùng làm bằng chứng; chỉ **thứ tự/dấu** là thông tin hữu ích.
- Sai khác còn lại (ngoài §1) chưa truy nguyên hết — nghi vấn: khác bản đồ S1 và/hoặc khác cách dựng
  chuỗi funding; **ghi rõ là CHƯA XÁC ĐỊNH**, không suy diễn.

## 3. Việc CÒN LẠI (không làm trong vòng này)

1. **V2/V3/V4 CHƯA có sim.** Bảng sim hiện có **4 kênh** (MỐC + V0/V1/V5). Muốn hoàn tất 6 biến thể
   phải **pre-reg RIÊNG** (thêm chân sau khi đã xem số = vi phạm multiplicity; `k` phải tính lại), dùng
   **đường ĐÃ QUA CỔNG** (`s3_kernel.py`/`s3_build_map.py`, commit `1b28afa`).
2. Nếu muốn tài liệu hoá vì sao bundle thiếu 2 bin 2021H2: sửa `docs/runbooks/KAGGLE_SIM.md` §3 (kèm
   bằng chứng manifest `foldCount=16` ở trên) — **chưa làm**.

*Sinh trong vòng mở rộng Stage 3; các script chạy chưa commit của vòng này đã bị dọn khỏi cây làm việc
(untracked), nên tài liệu này giữ lại phần kết luận + số liệu.*
