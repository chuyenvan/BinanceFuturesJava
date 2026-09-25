# PREREG_YCONT_4H — ĐO 5 ARM BẰNG **NHÃN LIÊN TỤC** (`maxFav_4h`, `retEnd_4h`) + THƯỚC TIỀN

**Ngày:** 2026-09-25 · **Trạng thái:** CHỐT **TRƯỚC** khi đọc số của vòng này · **KHÔNG push** · DEV only.
Bổ sung cho `PREREG_MODEL_RULER.md` (§12/§12.10) — **KHÔNG** thay luật cũ.

## 1. LÝ DO (câu mở, chưa có số)
`RESULT_MODEL_RULER.md` §11.4 mục 2 + §11.7 mục 1: `pacc`/`dec_mono` hiện đo trên `y = retEnd_4h`
**liên tục** nên **giống hệt** ở 2 nhãn (Δ = 0,000000) ⇒ *"biết coin nào CHẠM ngưỡng"* ≠ *"biết coin nào
LÊN NHIỀU NHẤT"*. Vòng này đo `y = maxFav_4h` **liên tục** để chốt câu đó bằng số, và đọc **thước TIỀN**
(`retEnd` net) cho `A44` vs `A45`.

## 2. NGUỒN + THAM SỐ (cố định)
- 6 arm, bins RAW đã có: `45deploy` (`claudedata/predwf_G015x26`), `A45`,`A44`
  (`ruler_bins/g015p2-arm44-gpu/stage2/`), `V0`,`V1`,`V5` (`ruler_bins/g015p2-stage2-featvar-gpu/stage2/`).
- Nhãn: `/home/ubuntu/label_15m/*.pb` (cột `maxFav_h`, `retEnd_h`, `nBars_h` **đã có sẵn**, KHÔNG tính lại từ giá 1m).
- `h = 4h` (slot 0) · `K_SEL = 8` · `K_LIFTS = 8,12,16` · `FEE_RT = 0,002 + 2×0,003 = 0,008` · `THR = 0,015` · `TOUCH = 0,07`.
- CI: block-72h, `c3_rates` NREP/SEED, `inflate(k=2)` (2 ứng viên vòng này: `A44`, `V0`) · "ngoài CI" = ngoài **CẢ HAI** độ rộng.
- Chỉ đọc artifact ĐÃ CÓ ⇒ **KHÔNG** train, **KHÔNG** sim, **KHÔNG** job, **KHÔNG** chạm 2026/`HoldoutSeal`.

## 3. HAI THƯỚC — ĐỊNH NGHĨA + LUẬT QUYẾT ĐỊNH (chốt trước)
| thước | `y` | chỉ số QUYẾT ĐỊNH |
|---|---|---|
| **NHÃN** | `maxFav_4h` liên tục | `ic` (rank-IC), `pacc`, `dec_mono`, `lift8`, `dec_rho` (+ `decile gộp` trên `maxFav`) |
| **TIỀN** | `retEnd_4h` liên tục (net = `y − 0,008`) | `pacc`, `dec_mono`, `glift8`, `netm8` |

- **`A44` THUA `A45` trên thước X** ⇔ **MỌI** chỉ số quyết định của X có `Δ = A44 − A45 < 0` **và** `out_both`
  (CI cả hai độ rộng nằm dưới 0).
- **`A44` ≈ `A45` trên thước TIỀN** ⇔ **KHÔNG** chỉ số TIỀN nào có `Δ < 0` `out_both`.
- **Trộn** (một phần âm ngoài CI) ⇒ **báo TRỘN**, KHÔNG kết luận "thua"/"≈".
- **BƯỚC SAI** (kết luận bắt buộc):
  - (a) NHÃN thua **và** TIỀN ≈ ⇒ *"44 thua 45" chỉ đúng ở TẦNG ĐOÁN NHÃN* ⇒ **bước sai = MỤC TIÊU (nhãn)**.
  - (b) TIỀN **cũng** thua ⇒ bước sai **KHÔNG** phải nhãn (là mô hình/đặc trưng) ⇒ `rvol15m` có giá trị cả về tiền.
- Đối chứng: **retrain** = `A45 − 45deploy`, **nhiễu** = `V5 − V1`; cả hai phải **không** `out_both` dương ở
  chỉ số chính, nếu không thì **2 đối chứng mất chức năng** và phải báo.

## 4. DỰ ĐOÁN KHOÁ TRƯỚC (ghi TRƯỚC khi chạy; đối chiếu ở RESULT)
| # | dự đoán |
|---|---|
| **Q18** | `A44 < A45` trên thước NHÃN (`maxFav` liên tục, `Δic/Δpacc` âm `out_both`) — tiếp nối §11 (`Y1`). |
| **Q19** | `A44 ≈ A45` trên thước TIỀN (không chỉ số nào `Δ<0` `out_both`) ⇒ kết luận (a). |
| **Q20** | `pacc ≈ 0,48` (< 0,5) ở **MỌI** arm trên **CẢ HAI** nhãn liên tục ⇒ "biết lên nhiều nhất" **không** có kỹ năng. |
| **Q21** | `A45 − 45deploy` và `V5 − V1` ≈ 0 (không `out_both`) trên thước TIỀN ⇒ 2 đối chứng còn đúng chức năng. |

## 5. MULTIPLICITY (đếm, không nới ngưỡng)
6 arm × 2 nhãn × ~6 chỉ số = ~72 số; **4 phép so là QUYẾT ĐỊNH** (`A44−A45` × 2 thước). Không đổi nhãn,
không đổi `K`, không đổi `h` sau khi thấy số. `h=72h` **N/A** với artifact hiện có (§12.7 G-2, `z` NaN 100 %) — không chạy.

## 6. LỆNH ĐÃ CHỐT
```
python3 -u research/analysis/model_ruler.py validate --k 2 --horizon 4h --reuse \
    --out /home/ubuntu/.cache/ruler_bins_ycont_money_4h.json                 # thước TIỀN (y=retEnd, cache cũ)
python3 -u research/analysis/model_ruler.py validate --k 2 --horizon 4h --label-kind y1 --y-kind maxfav \
    --skip-selftest --out /home/ubuntu/.cache/ruler_bins_ycont_maxfav_4h.json # thước NHÃN (y=maxFav liên tục)
```
Công cụ đã sửa **tối thiểu**: thêm `--y-kind {retend,maxfav}` (đổi NGUỒN cột `y`; mặc định `retend` ⇒
byte-identical) + thêm `pacc`/`dec_mono`/`dec_rho`/`ic`/`gross8`/`net8` vào danh sách Δ (chỉ THÊM số).
