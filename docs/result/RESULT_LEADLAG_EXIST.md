# RESULT_LEADLAG_EXIST — tồn tại lead-lag BTC→alt (giá-only, DEV 2022–2025, không sim)

Ngày **2026-10-13**. Pre-reg `docs/prereg/PREREG_LEADLAG_EXIST.md` commit **`e0e7bd54`**. Scorer
`research/analysis/leadlag_exist.py` commit **`9e63a754`** (commit TRƯỚC lần chấm; sau đó không sửa). Lần chấm:
`python3 research/analysis/leadlag_exist.py full leadlag_exist.json`, 87 s, Oracle ARM. Output `docs/result/leadlag_exist.json`
**md5 `ea16fd5cf8237ba3edd32aa22379c1d3`**. Trước lần chấm có 2 lần smoke t ∈ 2022-01 **chỉ để debug** (lần 1 phát hiện lỗi
placebo: log-giá gốc BTC hàng 0 là NaN nên mọi giá placebo NaN; đã sửa trước khi commit scorer). Kết quả smoke không dùng.

0 sim, 0 Java, 0 Binance REST, 0 dữ liệu 2026, 0 kho backcast, 0 chạm 242/shadow/systemd/Kaggle.

Dữ liệu: `CLOSES_1H.bin` md5 `6c7548801136655065edfd8e6cd7c0af` (10 322 386 bản ghi, 0 lệch lưới giờ, 0 trùng, 0 close ≤ 0),
`symbol_map.csv` md5 `c4439c3f8edc42de568d0d1ddd68f726`. Bỏ 590 bản ghi ts = 2026-01-01 00:00. Bị loại khỏi universe (có dữ liệu):
BTCUSDT, ETHUSDT, BTCDOMUSDT, USDCUSDT.

## 0. Kết luận theo luật §4

| Điều kiện GO | Giá trị | Đạt |
|---|---|---|
| H1 chính (k=3h, h=4h) mean IC > 0 | 0,01658 | CÓ |
| H1 chính CI nở cận dưới > 0 | 0,01285 | CÓ |
| ≥ 3/4 năm mean IC > 0 | 4/4 | CÓ |
| H2 Δ > +0,30 % và CI95 dưới > 0 | **KHÔNG ĐO ĐƯỢC** (§3) | — |
| V1 / V2 / V3 | PASS / PASS / KHÔNG CHẠY | — |

**Kết luận: GO KHÔNG được tuyên bố; chưa ĐÓNG.** H1 đạt đủ 3 điều kiện. GO còn cần H2, mà H2 không chạy được vì ledger chân
thiếu `close_M` (§3). Trạng thái: **CHƯA KẾT LUẬN, treo chờ H2**. Đọc §4 theo nghĩa đen ("ngược lại: ĐÓNG") thì nếu không khôi
phục được ledger, hướng này ĐÓNG. MASTER quyết định.

## 1. H1 — IC Spearman cắt ngang (g⊥, idio fwd), toàn thị trường

Block bootstrap theo ngày (khối 10 ngày, NREP 2000, seed 20261013). CI95 = mean ± 1,96·sd_boot. CI nở = mean ± 1,665·1,96·sd.
Cận dưới quyết định = min(cận nở chuẩn, cận nở percentile).

| Biến thể | mean IC | CI95 | CI nở 1,665 | cận dưới QĐ | giờ | ngày | coin/giờ TB (min) | coin phân biệt | coin-giờ | % giờ IC>0 |
|---|---|---|---|---|---|---|---|---|---|---|
| k=1h, h=1h | 0,01714 | [0,01532; 0,01897] | [0,01410; 0,02018] | 0,01409 | 34 969 | 1 459 | 245,4 (35) | 606 | 8 581 742 | 55,4 % |
| k=1h, h=4h | 0,01283 | [0,01122; 0,01444] | [0,01015; 0,01552] | 0,01015 | 34 970 | 1 459 | 245,4 (35) | 606 | 8 582 032 | 53,8 % |
| k=3h, h=1h | 0,01734 | [0,01558; 0,01911] | [0,01441; 0,02028] | 0,01441 | 34 973 | 1 459 | 245,4 (35) | 606 | 8 582 248 | 55,7 % |
| **k=3h, h=4h (CHÍNH)** | **0,01658** | [0,01434; 0,01882] | **[0,01285; 0,02031]** | **0,01285** | 34 974 | 1 459 | 245,4 (35) | 606 | 8 582 538 | 54,9 % |

Theo năm (UTC của t). Mỗi năm bootstrap riêng, cùng thiết lập. Cột: mean IC [CI nở 1,665].

| Biến thể | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|
| k=1h, h=1h | 0,02201 [0,01648; 0,02755] | 0,02013 [0,01449; 0,02576] | 0,01288 [0,00724; 0,01852] | 0,01353 [0,00755; 0,01950] |
| k=1h, h=4h | 0,01633 [0,01119; 0,02147] | 0,01353 [0,00770; 0,01937] | 0,01347 [0,00858; 0,01836] | 0,00795 [0,00318; 0,01271] |
| k=3h, h=1h | 0,02202 [0,01605; 0,02800] | 0,01702 [0,01096; 0,02308] | 0,01580 [0,01053; 0,02107] | 0,01450 [0,00984; 0,01917] |
| **k=3h, h=4h** | **0,01852** [0,01041; 0,02662] | **0,01641** [0,01015; 0,02267] | **0,01751** [0,01098; 0,02404] | **0,01384** [0,00667; 0,02100] |
| giờ (k3h4) | 8 758 | 8 756 | 8 781 | 8 679 |
| coin/giờ TB | 132,7 | 175,5 | 260,4 | 414,5 |

## 2. Kiểm hợp lệ

**V1 — tái tạo tay: PASS.** Lấy 3 điểm (coin, t) cho mỗi biến thể (12 điểm), chọn ngẫu nhiên với seed 20261013+100k+h trong các
ô được dùng tính IC. Tính lại β, g, y bằng vòng lặp Python trên bản ghi thô (dict ts→close, OLS dạng trung tâm,
`statistics.stdev`), không dùng lưới/cumsum. Sai lệch tuyệt đối lớn nhất: β 1,9e-13, g 1,4e-13, y 2,3e-15 (ngưỡng 1e-6).
Biến thể chính: (2024-01-21 19:00, id 7) β 1,100085, g −0,213283, y −0,010958; (2023-03-11 00:00, id 137) β 2,057765,
g −0,661987, y −0,046062; (2024-01-15 12:00, id 195) β 1,074820, g 0,212262, y −0,008901. n_β = 717, n_σ = 168.

**V2 — placebo xáo r_BTC: PASS (4/4).** Hoán vị 1 826 ngày (2021–2025) của chuỗi r_BTC 1h,
`default_rng(20261013).permutation` (perm md5 `6fe141aff3f2e22b055565c00cf36ff9`). Dựng lại log-giá BTC placebo, tính lại toàn bộ
β, g, y, g⊥, IC và bootstrap. PASS = |mean placebo| < |mean thật|/3 HOẶC cả CI95 chuẩn lẫn percentile (không nở) chứa 0.

| Biến thể | mean thật | mean placebo | CI95 placebo | tỷ lệ \|plc\|/\|thật\| | < 1/3 | CI chứa 0 | V2 |
|---|---|---|---|---|---|---|---|
| k1 h1 | 0,01714 | −0,00017 | [−0,00129; 0,00095] | 0,010 | có | có | PASS |
| k1 h4 | 0,01283 | 0,00076 | [−0,00034; 0,00185] | 0,059 | có | có | PASS |
| k3 h1 | 0,01734 | 0,00030 | [−0,00066; 0,00127] | 0,017 | có | có | PASS |
| k3 h4 | 0,01658 | 0,00156 | [0,00002; 0,00310] | 0,094 | có | không | PASS |

**V3 — phủ chân H2: KHÔNG CHẠY** (§3).

## 3. H2 — không chạy được

Ledger chân mà EXEC dùng là `~/claude_master/1012/exec/legs.pkl` (md5 `c55224e7…`, 23 654 chân, 5 284 sự kiện; tạo bởi
`exec_legs.py`). `close_M` của nó lấy từ kline 1m Vision (`exec_measure.py`: `cM = kx[im, 3]`). Theo EXEC_RESULT §8, cache
`exec/{agg,kl}/*.npz` cùng các `*.pkl` đã bị **xoá**, chỉ giữ manifest md5. Tìm trên Oracle: không có `legs.pkl`/`sim.pkl` nào còn
lại, không có nguồn kline 1m nào khác. `printDone.csv` (8 seed `nsel-nen-s*`) vẫn còn, nhưng cột `entry` = close_M·(1+0,01675·sập)
và cờ sập cần open_M (1m), nên không suy ngược ra `close_M` được. Theo lệnh MASTER, scorer không tự dựng ledger khác.

Cách khôi phục (cần MASTER duyệt; có tải từ data.binance.vision): chạy `exec_legs.py` (đọc printDone, tất định), kiểm 23 654 chân /
5 284 sự kiện, rồi `exec_fetch.py kl` cho danh sách (sym, tháng) trong `exec/need.json` để lấy close_M. Sau đó chạy H2 + V3 với
scorer bổ sung đã commit trước.

## 4. Các chỗ mơ hồ đã chọn (chốt trong scorer trước lần chấm)

1. **Cửa sổ:** t ∈ [2022-01-01 00:00; 2025-12-31 19:00] UTC (t+4h ≤ 23:00). Lookback được dùng dữ liệu 2021 (file bắt đầu
   2021-01-01 01:00) cho β/σ/lịch sử. Không đọc ts > 2025-12-31 23:00, kể cả 590 bản ghi ts = 2026-01-01 00:00 (đọc pre-reg theo
   nghĩa đen).
2. **β:** r 1h có điểm cuối s ∈ [t−719h, t−k], tức nằm trọn trong [t−30d, t−k]. OLS có hằng số. Cần ≥ 500 cặp (alt, BTC) cùng hợp lệ.
3. **σ_i 1h 7 ngày:** std ddof=1 của r_i 1h với s ∈ [t−167h, t] (gồm cả cửa sổ gap, causal ≤ t). Cần ≥ 120 điểm (pre-reg không ghi
   ngưỡng).
4. **Universe:** đủ 78 close t−73h…t+4h. Cùng một universe cho cả h=1 và h=4. Lịch sử ≥ 30 ngày nghĩa là close đầu tiên trong
   file ≤ t−720h. BTC phải có close tại t−k, t, t+h. Giờ cần ≥ 30 coin sau mọi lọc.
5. **Loại stable:** tên kết thúc bằng {USDC, FDUSD, TUSD, BUSD}+"USDT" (gồm cả cặp xxxUSDCUSDT). TUSDT (token T) và BUSDT (token B)
   được giữ. Trong file chỉ USDCUSDT bị loại thêm. ETHBTCUSDT và token cổ phiếu/kim loại được giữ vì pre-reg không loại.
6. **g⊥:** phần dư OLS cắt ngang g ~ 1 + rev tại mỗi t. Spearman = Pearson trên rank trung bình.
7. **Bootstrap:** moving block bootstrap. Khối 10 ngày liên tiếp, điểm bắt đầu đều trên [0, D−10], ghép rồi cắt còn D ngày.
   Thống kê = ΣIC/Σgiờ. CI95 tính 2 cách (chuẩn ±1,96·sd và percentile). CI nở = mean ± 1,665·(nửa-rộng). Cận dưới quyết định =
   min của 2 cách nở. Theo năm: bootstrap riêng trong năm.
8. **V2:** hoán vị toàn ngày trên cả lưới 2021–2025, tính lại cả 4 biến thể. V2 PASS = cả 4 PASS. Nhánh "CI chứa 0" dùng CI không
   nở, đòi cả chuẩn lẫn percentile cùng chứa 0. Ghi chú: hoán vị theo ngày giữ nguyên cấu trúc trong ngày của r_BTC.
9. **Năm:** theo UTC của t.
10. Chuỗi `decision.why` trong json in "%%" thay vì "%" (lỗi hiển thị, không ảnh hưởng số liệu). Không sửa sau lần chấm.

## 5. Tái lập

```bash
cd ~/src/BinanceFuturesJava            # nhánh research/leadlag-exist
python3 research/analysis/leadlag_exist.py full /tmp/leadlag_exist.json   # ~90 s
```
json có trường `runtime_s`, nên md5 của lần chạy lại sẽ khác. So số bằng các trường `h1` / `v1` / `v2` / `decision`.
