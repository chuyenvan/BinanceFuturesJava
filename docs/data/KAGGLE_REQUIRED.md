# KAGGLE_REQUIRED — dataset PHẢI còn (kiểm sau khi owner tự xoá; P1, MASTER 10-15)

Kiểm 2026-10-15 (nguồn: `kaggle datasets list -m`; còn **150** dataset, P1 lúc đầu ghi 140).

P1-RESIDUAL (2026-10-15, sau P1 lõi): đã xác minh nốt 3 hạng mục treo ⇒ **2 dataset jar đã bị xoá, nhưng jar ĐÚNG sha còn nguyên trên đĩa Oracle ⇒ KHÔI PHỤC ĐƯỢC, KHÔNG BLOCKED**. Chi tiết §P1-RESIDUAL.

## PHẢI CÒN — ĐÃ KIỂM: CÒN ĐỦ ✓
| slug | ai dùng |
|---|---|
| `vz-kline1m-2023` `vz-kline1m-2024` `vz-kline1m-2025` | VZ lake (E1) |
| `vz-basis1m-2023` `vz-basis1m-2024` `vz-basis1m-2025` | VZ lake (E1) |
| `vz-metrics5m` `vz-funding` | VZ lake (E1) |
| `vz-pilot-202408` | pilot lake |
| `vz-marketdata` | dump Aerospike (B4 parity f=0) |
| `bcast-2020-2021h1-p1` | backcast 2020 (B1) |
| `sim-ho26-bundle` `sim-ho26a-bundle` | sim HO26 |
| `ho4p1-code` `ho4p1-jar-exp` | HO4-P1 |
| `sim-jar-ecost` (sha 246087fb) | ECMEAS entry-cost |
| `wfo-ticker-2021/2022/2023/2024h1/2024h2/2025h1/2025h2` | WFO sim |

## P1-RESIDUAL — KẾT QUẢ XÁC MINH 3 HẠNG MỤC TREO (2026-10-15)

### 1. Jar nền ECMEAS/HO4 (`b7c89f09…`, `0944841c…`) — ĐÃ XOÁ TRÊN KAGGLE, CÒN NGUYÊN TRÊN ĐĨA ⇒ KHÔI PHỤC ĐƯỢC
Map slug (nguồn: driver trong repo):

| sha256 đầu | slug Kaggle | driver dùng | commit build (docs) | trạng thái Kaggle | jar local (sha256 tái tính) |
|---|---|---|---|---|---|
| `b7c89f097241763b…` | `sim-jar-nsel` | `ho4p1_queue.py`, `bcast_sim.py`, ho3b/ho4 kernels | `df021437` (cây sạch) — `NSEL_IMPL_JOINTS.md:10` | **THIẾU (đã bị xoá)** | `~/src_wt_nsel/target/binance-java-sdk-1.2.4.jar` ⇒ sha **`b7c89f09…de62c2` TRÙNG** ✓ |
| `0944841ca1b3ac44…` | `sim-jar-gqsf` | `gate_skipfull_driver.py` (gqsf-*) | `128290af` — `PREREG_GATE_QUOTA_SKIPFULL.md:69` | **THIẾU (đã bị xoá)** | `~/src_wt_gqsf/target/binance-java-sdk-1.2.4.jar` ⇒ sha **`0944841c…69ad7f` TRÙNG** ✓ |
| `246087fb606c5307…` | `sim-jar-ecost` | `ecm_q.py`, `ec_parity.py` | `b58e05c9` | CÒN ✓ | `~/claude_master/1012/ecost/jar/…jar` (+ `ecost_wt/target/…`) sha TRÙNG ✓ |

⇒ **KHÔNG BLOCKED**: 2 jar mất có bản đúng sha trên đĩa, chỉ cần đẩy lại Kaggle PRIVATE khi cần chạy (không cần build lại, không thay thế). KHÔNG tự đẩy lại trong P1-RESIDUAL (owner vừa dọn dung lượng Kaggle — cần owner xác nhận).

### 2. "bundle Vision A/B" (dataset HO4) — CÒN ĐỦ
= cặp bundle HO26 mà pipeline Vision (HO4) khai: **A = `sim-ho26-bundle`** + **B = `sim-ho26a-bundle`**. Đã kiểm nội dung qua `kaggle datasets files`: **cả hai đủ file** (funding.bin 5 GB, market.bin 54 MB, pred.bin 42 MB, predict_wf_*.bin, MANIFEST_HO1.json, exchange_info_pin.json…). (Cột size `0B` của `sim-ho26-bundle` trong `datasets list` chỉ là hiển thị sai — thực tế đủ file.) Bundle DEV `sim-x1-2021-bundle` (613 MB) cũng CÒN ✓.

### 3. Dataset mà template sim hiện hành (K24 + skipFull, `PARITY["ho4p1-c2"]`) khai — THIẾU `sim-jar-nsel`
Nguồn khai: `research/analysis/ho4p1_queue.py:27,82-85` — `BUNDLE="sim-ho26a-bundle"`, `JAR_DS="sim-jar-nsel"`, `ks.TICKER_DS` (`tools/kaggle_sim.py:40`). Kernel-metadata không nằm sẵn trong repo: nó được **sinh tại runtime** bởi `ho4p1_queue.push()` (`dataset_sources`/`kernel_sources` dựng bằng code), nên không có file `kernel-metadata.json` chứa `skipFull`/`ho4p1-c2` để grep.

| loại | slug | còn/thiếu |
|---|---|---|
| dataset_sources | `chuyendinh/sim-ho26a-bundle` | CÒN ✓ |
| dataset_sources | `chuyendinh/wfo-ticker-2021`, `-2022`, `-2023`, `-2024h1`, `-2024h2`, `-2025h1`, `-2025h2` (7) | CÒN ✓ (7/7) |
| dataset_sources | `chuyendinh/sim-jar-nsel` | **THIẾU** ✗ (xem §1 — khôi phục được) |
| kernel_sources | `CHAIN` + `TKK` (từ `~/claude_master/1011/ho4p1/arts.json`) | kernel, không phải dataset |

**Hệ quả:** template `ho4p1-c2` (và `bcast_sim.py`) **chưa chạy được** cho tới khi `sim-jar-nsel` được đẩy lại Kaggle. `ec_parity.py`/`ecm_q.py` dùng `sim-jar-ecost` (CÒN) + `sim-ho26a-bundle` (CÒN) ⇒ không bị chặn. Ghi chú: `ec_parity.py` còn tham chiếu profile trong `~/claude_master/1008/nsel_impl/ds_sim-jar-nsel/` (còn `prof_r4_kg0_k16_f015_g155.properties`, nhưng `sim.jar` đã bị xoá ở đó).
