# PARITY v1.1 — lượt D3 (ngày UTC 2026-10-24)

- **Thước:** prereg `481701b2`, ADDENDUM1 `fea9fb97`, ADDENDUM2 `4eef2788`, **ADDENDUM3 `67ce404a`**. Từ ngày này, nhãn chính thức theo ADD2 + ADD3.
- **Dữ liệu:**
  - `pull242/2026-10-24`: COMPLETE. SUMMARY: `STATUS=OK feat=1440/1440 sel=1440/1440 s1_h=24/24 psym=1440,1440/1440 log_min=1440 gap=0 gate_B=5849143 files=3171 MB=186.5`.
  - Vision daily 10-24: 741/741 symbol, 100 %, phát hành khoảng 14:48 (+07) ngày 10-25.
- **Chạy:**
  - Lần 1 (`watch_1024b`) lúc 15:05: rc = 3, vì Vision chưa đủ 99 % symbol nên chỉ chấm phần không cần Vision.
  - Lần 2 (MASTER chạy lại) xong 19:26, kết quả ở `report_d3b`.
  - Lần 3 sau khi sửa scorer (`a3391b9c`): chạy lại từ bước `s1v`.
- **An toàn:** không chạm 242, không gọi Aerospike, không gọi Binance REST. strace mọi JVM: 0 connect tới 242.

## 0. Kết luận (risk-first)

**Verdict 10-24 (ADD2 + ADD3): XÁM.**
- P1, P2 (yếu), P3, TSX, S1-I, GV-I, CTL đều **ĐẠT**.
- **K5 = 1 phút** (10-25 05:59 +07), **CHƯA GIẢI THÍCH**.

Rủi ro, xếp theo mức độ:

1. **K5 = 89 của lần chấm 2 là lỗi scorer, không phải lệch live.** Nhóm 88 phút S1-V lệch đều vì một lỗi trong bản cài lại offline `hrs_since_high_7d` (f3).
   - Cơ chế: ba symbol niêm yết 10-21 09:00 UTC là BAC, CEG, IBKR. Đúng 10-24 21:00 UTC chúng có đủ 84 mốc giờ. Live tính f3 trên cửa sổ 168 mốc giờ, trong đó các mốc trước niêm yết là NaN và chỉ cần ≥ 84 mốc có giá. Bản offline lại đòi ≥ 168 phần tử, nên trả NaN.
   - Hệ quả: lệch f3 (110 dòng: IBKR 61, BAC 39, CEG 10), lệch score, và 19 phút top-24 khác thứ tự.
   - Phân bố: 100 % nằm trong 10-25 04:00–06:59 (+07), tức 21:00–23:59 UTC.
   - Đã sửa ở `a3391b9c`. **K5: 89 → 1.**
2. **TSX "KHÔNG ĐO ĐƯỢC (vision=OFF, live=[])" cũng là lỗi scorer**, không phải pipeline tắt và không phải ngày không có sự kiện X14.
   - Live chỉ in `flag day=D … final=false` (src=aero:1d) lúc 07:03. Dòng `final=true` chỉ xuất hiện khi restart, mà 10-24 không có restart.
   - Scorer cũ chỉ đọc dòng `final=true`.
   - Bằng chứng live: dòng `flag day=2026-10-24 flag=OFF dd=-0.167771`, cùng 23 dòng `[TS-EXT] status … flagToday=OFF` (01:00–23:00 UTC).
   - Sau sửa: cờ OFF = OFF ⇒ **ĐẠT**. ΔS_10-24 = 2,1e-10 (days64) / 1,6e-17 (days32).
3. **P2 không được thử ở 10-24.** 34 560 cặp; max r/q 0,842; 0 cặp ≥ 0,9; 5 cặp ≥ 0,8; 0 pass; 0 lật.
4. **K5 còn lại (05:59) cùng mẫu với các ngày trước.**
   - 8 feature breadth/1′ lệch: momentum1M, advanceDeclineRatio, percentAboveMA20, volumeRatioUpDown, marketBreadthStrength, btcDominance, basketRsi14, basketVolSpike. P1 rel 4,6e-3 (1 phút).
   - Phút này nằm trong cửa sổ `[LIVE-KLINE]` 05:51–06:01 với `reread_overwritten=204`; cửa sổ kế (06:11) có `decided_on_unsettled=201/7407`. Log in `symbols:596` (05:59) so với 606 / 634 ở hai phút kề.
   - K1″ (b) không chứng minh được, vì lệch không đi qua kênh momentum15M và log không nêu tên symbol ⇒ CHƯA GIẢI THÍCH.
   - Đây là sự kiện ghi đè lớn khoảng 1–3 lần/ngày, xem bảng §3.
5. **Các giả thuyết coordinator nêu, đã kiểm và loại trừ:**
   - Restart: không có `MainClass` từ 10-23 09:37:31.
   - Lỗ log: không có khoảng trống > 90 s trong 10-24; 1440/1440 tick `[GATE]`; 24/24 `[GATE-RATIO]`.
   - ERROR: 0 dòng.
   - KILLSW HOURLY: C1–C6 = 0; miss = 0/741.
   - TradFi / IBKR: chỉ góp vào nhóm S1-V lỗi scorer ở mục 1; không có lệch gate hay Tool1 nào theo symbol IBKR.
   - Vision ↔ live: 0 lỗ Vision (K2a = 0).

## 1. Bảng chính 10-24 (sau sửa)

| mã | ngưỡng | 10-24 |
|---|---|---|
| **P1** | median ≤ 1e-4 **và** ≥ 98 % phút ≤ 1e-3 | median 6,6e-8; 99,931 % (1439/1440); max 4,6e-3 (05:59) ⇒ **ĐẠT** |
| P1-m | 100 % | 100 % (max 4,7e-7) |
| P1-F / MD | báo cáo | 1439/1440 / 99,93 · 99,93 · 100 % |
| FUND / NET | báo cáo | 99,953 % dòng (42 791) / 99,965 %, max \|Δ\| 0,0059 |
| **S1-I** / S1-m | 100 % | 1440/1440 / max \|Δ\| 0 |
| S1-V | báo cáo | f0/f1/f3/f4/f6 100 %; f2 99,975 %; f5 99,948 %; score 99,997 %; **top-24 trùng thứ tự 1440/1440** |
| **GV-I** / GV-O | 100 % / báo cáo | 34 560/34 560 / 99,974 % (9 dòng, phút 05:59) |
| **P2** | lật nặng = 0 | 34 560 cặp; 0 pass / 0 pass; 0 lật; max r/q 0,842 ⇒ **ĐẠT (yếu)** |
| `[GATE] n_pass` | báo cáo | 1440/1440 (Σ 0 = 0) |
| **P3** | mọi giờ ≤ 1e-6 | 24/24 (max 5,9e-10) ⇒ **ĐẠT** |
| **TSX** | cờ trùng | OFF = OFF ⇒ **ĐẠT** (sau sửa) |
| **CTL** | 100 % | gate 1440/1440 bit-identical; Tool1 dung sai 100 % (f3 lệch bit cuối 2248 dòng); `cand_flag_diff` POWRUSDT 162 dòng (symbol DIED, như 10-23) ⇒ **ĐẠT** |
| K5 (ADD2 + ADD3) | — | **1** ⇒ **XÁM** |

## 2. Lỗi scorer và sửa (`a3391b9c`): trước / sau

| | lần chấm 2 (trước sửa) | sau sửa |
|---|---|---|
| S1-V f3 | 0,99988 | 1,0 |
| S1-V top-24 trùng thứ tự | 0,98681 | 1,0 |
| phút lệch (labels) | 383 | 295 |
| K5 chính thức (ADD2 + ADD3) | **89** (88 S1-V: 69 `feature_khac` + 19 `top24_khac`; 1 thị trường) | **1** (05:59) |
| K5 theo ADD1 (mô tả) | 269 | 181 |
| TSX | KHÔNG ĐO ĐƯỢC | ĐẠT |
| verdict | KHÔNG ĐO ĐƯỢC (một phần) + XÁM | **XÁM** |

**Regression:**
- S1-V của D1, 10-22, 10-23: JSON **trùng hệt** bản đã commit. `s1v_rows` của D1 trùng md5.
- TSX 10-22 và 10-23 vẫn ĐẠT (cờ live OFF ở cả dòng `flag` lẫn dòng `status`).
- Ngưỡng và tiêu chí prereg không đổi.

## 3. Mẫu "phút ghi đè lớn" (K5 thị trường còn lại, mọi ngày)

| ngày | phút (+07) | cửa sổ `reread_overwritten` |
|---|---|---|
| 10-21 | 11:59, 17:04, 23:59 | 199, 253, 215 |
| 10-22 | 08:10, 05:14 (10-23) | 258, 287 |
| 10-23 | 07:59, 12:48, 22:14 | 226, 67, 241 |
| 10-24 | 05:59 (10-25) | 204 |

Đặc điểm chung:
- Mỗi lần là một phút lệch nhiều feature breadth cùng lúc, ngay trong cửa sổ có hàng trăm nến bị ghi đè.
- Thường kèm một chuỗi phút chỉ lệch tham chiếu 15′ ngay sau đó. Chuỗi này được K1″ giải thích được một phần, nhưng không định danh được symbol.

Chỉ chẩn đoán được khi live log danh sách symbol bị ghi đè (ADD2 mục 3, việc C14 của v1.2).

## 4. Tích luỹ cửa sổ 10-21 → 10-24

| | 10-21 | 10-22 | 10-23 | 10-24 | tổng |
|---|---|---|---|---|---|
| verdict trong sổ | ĐẠT | XÁM | XÁM | **XÁM** | 0 ngày TRƯỢT |
| luật K5 | ADD1 (ADD2 chỉ relabel) | ADD1 (ADD2 chỉ relabel) | ADD2 | ADD2 + ADD3 | |
| K5 chính thức (relabel ADD2 đúng chữ) | (67) | (164) | 3 | 1 | |
| P2 cặp | 33 264 | 34 560 | 34 560 | 34 560 | **136 944** |
| cặp r/q ≥ 0,9 (live / off) | 0 / 0 | 0 / 0 | 28 / 28 | 0 / 0 | **28 / 28** |
| cặp r/q ≥ 0,8 (live / off) | 6 / 6 | 0 / 0 | 41 / 41 | 5 / 5 | **52 / 52** |
| lật / lật nặng | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | **0 / 0** |
| P3 giờ | 24/24 | 24/24 | 24/24 | 24/24 | 96/96 |
| TSX cờ | OFF = OFF | OFF = OFF | OFF = OFF | OFF = OFF | 4/4 |
| CTL | ĐẠT | ĐẠT | ĐẠT | ĐẠT | 4/4 |

## 5. Artefact

- `docs/result/parity_v11_d3/parity_v11_d3.json`: verdict sau sửa.
- `docs/result/parity_v11_d3/2026-10-24/`: các JSON của ngày.
- `docs/result/parity_v11_d3/2026-10-24/prefix_d3/`: kết quả trước sửa (`kpp`, `labels`, `kprime`, `s1v`, `tsx`, `report_d3b.txt`).
- `docs/result/parity_v11_d3/ops_1024.txt`: kiểm vận hành 242 (MainClass, ERROR, KILLSW, EXEC-PROBE).
