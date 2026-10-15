# VZ-CAND-2024 — tập ỨNG VIÊN của hệ, năm 2024 (QUEUE_1015 P4, MASTER 10-15 14:19)

Nguồn: kernel Kaggle **`chuyendinh/sim-vz-cand-2024`** (chạy 2026-10-15), jar **`68057d25…`**
(branch `feat/sim-export-candidates`, key `SIM_EXPORT_CANDIDATES`). Output: dataset PRIVATE
**`chuyendinh/vz-cand-2024`**.

## 1. Cấu hình kernel (1 kernel, KHÔNG chạy năm xác nhận 2025)
- Profile `r4_kg0_k16_f015_g155` + `B0OV` + `SELECTOR_RANK_TOPK=24` + `GATE_QUOTA_SKIP_WHEN_FULL=true`
  (đúng cấu hình K24+skipFull = shadow #2, theo `SHADOW2_K24_SKIPFULL_PLAN.md` §1c; tương ứng run `gqsf-a1`).
- `SIM_EXPORT_CANDIDATES=cands.csv` (khai trong **profile**, không qua env — key tiền tố `SIM_` bị `Cfg` chặn khi có `TRADING_PROFILE`).
- `SIM_END_DATE=20241231`, bundle `sim-x1-2021-bundle`, 7×`wfo-ticker-*`, `xmx=22g`.
- dataset_sources: `sim-x1-2021-bundle` + 7×`wfo-ticker-*` + **`sim-jar-cand`** (xem §3).

## 2. Kết quả kernel
| trường | giá trị |
|---|---|
| status | COMPLETE |
| date_first → date_last | **20210701 → 20241230** |
| n_trades | **2799** |
| equity 35000 → | **110626** (b_final 110626) |
| jar_sha256 | `68057d25a96adadef47edf3f452fbda2b038960fa27ad75b31089e4ac97cd2b3` ✓ |
| symbol_mapper | 863 |
| secs | 1237,5 |
| `[CAND-EXPORT] closed rows=` | **42 939 428** |

`cands.csv` thô: **5 710 317 857 B**, 42 939 428 dòng (header `ts,symbol,bar_ret,p15,thr_base,q_t,gate_pass,gate_reason,s1,rank,topk,entered`), ts 2021-07-01 → 2024-12-30.

## 3. Vì sao phải tạo dataset jar MỚI (`sim-jar-cand`)
`chuyendinh/sim-jar-nsel` (owner đẩy lại 10-15 07:23) = jar **cũ** sha `b7c89f09…` — **KHÔNG có** key
`SIM_EXPORT_CANDIDATES`. Bản build P4 là sha `68057d25…` ⇒ đẩy dataset PRIVATE `chuyendinh/sim-jar-cand`
(jar + `prof_r4_kg0_k16_f015_g155.properties`, md5 `0e0caef09e47931b706c696d587a5184`) rồi kernel lấy
jar qua `jar_ds=sim-jar-cand`. Không ghi đè `sim-jar-nsel` (dataset dùng chung bởi `ho4p1_queue.py`,
`bcast_sim.py`, ho3b/ho4 — ghi đè sẽ đổi jar âm thầm cho các pipeline đó).

## 4. Blocker đã gặp & cách xử lý
1. **Jar module HEAD fail-fast symbol-mapper** (lần chạy 1, ERROR sau 93 s):
   `IllegalStateException: symbol_mapper [init] co 8 id dung chung {843=[MUUUSDT,XBIUSDT], … 850=[PANWUSDT,SKHYUSDT]}`
   (`SymbolIdRules.assertUniqueIds`, commit `d5c48dd9`). Đây là 8 id trùng do 2 JVM cùng cấp id tháng 07/2026
   (`docs/audit/MAPPER_AUDIT_20261011.md`). Sửa mapper = GHI vào Aerospike 242 ⇒ **không làm** (luật: không đụng 242).
   Xử lý: đặt env hạ tầng **`SYMBOL_MAPPER_DUP_POLICY=WARN`** (có sẵn trong `Cfg.INFRA_KEYS`, không phải tham số giao dịch).
   **An toàn cho run này:** 16 symbol đó chỉ có kline từ **2026-07-16** (audit §M1/M2) ⇒ **không tồn tại** trong dữ liệu ≤2024.
2. **Tải output bị cắt:** `kaggle kernels output` / API dừng ở **5 224 357 600 B** (39,4 M dòng, hết 2024-09-16).
   File thật **5 710 317 857 B**. Tải tiếp bằng HTTP `Range: bytes=5224357600-` (206) ⇒ đủ **42 939 428 dòng**, hết 2024-12-30.

## 5. Dataset `chuyendinh/vz-cand-2024` (PRIVATE)
- `cands_2024.csv.gz` (188,8 MB): lọc `ts ∈ 2024-01-01…2024-12-31 UTC` từ `cands.csv`.
- **12 247 316 dòng**; `gate_pass=1` **766**; `entered=1` **766**; 265 symbol khác nhau đã vào lệnh.
- ts range 2024-01-01 00:00 → **2024-12-30 23:59**.
- Ghi chú phương pháp: `entered` = có vị thế mới ngay sau lời gọi tạo lệnh; ứng viên bị bỏ **trước** gate
  (đang giữ / thiếu ticker) vẫn được ghi với `gate_reason=ALREADY_OPEN/NO_TICKER`. **KHÔNG** tính outcome.

## 6. Việc còn lại (không thuộc P4 này)
- Join layer E1 causal: `research/vz/e1/e1_cand.py` (đã có, smoke PASS) — cần wire `bar_provider` đọc lake VZ.
- Không chạy năm xác nhận (2025) ở bước này.
