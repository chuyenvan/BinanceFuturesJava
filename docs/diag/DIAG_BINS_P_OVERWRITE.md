# DIAG_BINS_P_OVERWRITE — `predwf_t1_{f4,f4q,f72}`: trường `p` có bị **ĐÈ** không?

**Ngày:** 2026-09-25 · **Nhánh:** `module` · **Loại:** ĐIỀU TRA **THUẦN PYTHON OFFLINE** (đọc + đo byte-level; **KHÔNG** train · **KHÔNG** sim · **KHÔNG** job Oracle · **KHÔNG** sửa/xoá dữ liệu · **KHÔNG** claude-run)
**Nguồn câu hỏi:** `docs/diag/DIAG_SCORE72H.md` mục §2.4 + §4 (ý 4) — "`p_mean` của `f4`/`f4q`/`f72` gần trùng khít … ⇒ nghi 3 chân dùng chung một nguồn điểm (hoặc `build_map.py` đè `p`) … chưa lý giải".
**KHÔNG push.**

---

## 0. TRẢ LỜI NGẮN (4 câu)

| | câu hỏi | trả lời |
|---|---|---|
| **(a)** | Có đè thật không? | **CÓ "đè", nhưng KHÔNG phải lỗi writer/slot.** Chỉ **slot 0** (`p4h`) bị thay; giá trị mới lấy từ **pool giá trị của `claudedata/predwf_G015x26`**, **giữ nguyên multiset theo từng tick** (`87.547/87.547` tick = **100,0000 %**). Đó **đúng hợp đồng đã pre-reg** của `build_map.py`, không phải ghi sai nguồn/sai slot. |
| **(b)** | Nguyên nhân + `file:line` | `research/pipeline/build_map.py:28` (input G015x26) · `:36` (`SC = ledger/pred_{name}.parquet`) · `:37-42` (rank-map) · **`:44`** (`a2["p0"]=M.p_new…` — chỉ đè slot 0) · `:46` (comment "multiset → gate đồng ý hệt"). Người gọi: `docs/prereg/PREREG_T1.md` §3.2 — **đã khai báo trước**: "nguồn giá trị = **G015x26** … Gate giữ NGUYÊN multiset P(win) trong từng tick". |
| **(c)** | Phạm vi + kết quả cần đính chính | Cùng đường sinh: **cả họ `predwf_map_*`** (không riêng `t1_*`). **KHÔNG có kết quả nào phải sửa SỐ.** Cần **đính chính chữ**: `DIAG_SCORE72H.md` §2.4/§4 (đánh dấu "**đã lý giải — không phải lỗi**"), `T1_LABEL3.md` §4 (thêm con trỏ + câu "p_mean không phải calibration của chân"). |
| **(d)** | Chưa kết luận được gì | **Không còn ẩn số chặn kết luận.** Duy nhất một thứ **không kiểm chứng trực tiếp được**: **output thô của 3 model T1** (không được lưu ra đĩa) — nhưng chuỗi pipeline đã kiểm gián tiếp bằng `ledger/pred_t1_*.parquet` (xem §4, corr chéo chính = **−1.000000**). |

---

## 1. Định vị bins + xác nhận format bằng BYTE

| bộ | đường dẫn **thật** | số file | bản ghi | md5 file `predict_wf_20220101.bin` |
|---|---|---:|---:|---|
| chân `L_f4` | `/home/ubuntu/predwf_t1_f4` | 10 | 15.536.189 | `a2d3b1b807927281015cd28dc4dc3438` |
| chân `L_f4q` | `/home/ubuntu/predwf_t1_f4q` | 10 | 15.536.189 | `c112c6e24e60c0a7e11aa5f1023c4099` |
| chân `L_f72` | `/home/ubuntu/predwf_t1_f72` | 10 | 15.536.189 | `a1dee71424f7f652773c55991a4a74f8` |
| **chuẩn** (selector đang chạy) | `/home/ubuntu/predwf_map_s1a2_x1` | 16 | — | `a71cb93cfc580442418320eb0c9f8d04` |
| **nguồn giá trị** | `/home/ubuntu/claudedata/predwf_G015x26` | 16 | — | `1e95de99b51f46df6b81942bc54c834b` |

`md5` **4 bộ KHÁC nhau** ⇒ file không phải bản sao; `sha256` cũng khác (`DIAG_SCORE72H` §4 đã đúng).

Format **xác nhận lại bằng byte, không tin trí nhớ**: bản ghi **26 B**, `np.dtype([("ts",">i8"),("sym",">i2"),("p",">f4",4)])` = `>i8 ts` · `>i2 symId` · **4×`>f4`** = `p4h, p12h, p24h, p72h` (slot 0..3). `len(raw) % 26 == 0` đúng cho **mọi** file đã đọc; đo trực tiếp:

| bộ | %NaN slot 0/1/2/3 | mean slot 0 |
|---|---|---|
| `predwf_t1_f4` · `t1_f4q` · `t1_f72` | `0,0 / 100,0 / 100,0 / 100,0` | `0,41972` |
| `predwf_map_s1a2_x1` (chuẩn) | `0,0 / 100,0 / 100,0 / 100,0` | `0,41972` |
| `predwf_G015x26` (nguồn) | `0,0 / 100,0 / 100,0 / 100,0` | `0,41972` |

⇒ **chỉ slot 0 có dữ liệu**; slot 1-3 **NaN 100 % cả 5 bộ** (họ này chỉ có 1 đầu 4h — khớp `DIAG_SCORE72H` §2.4 "slot 3 vẫn NaN"). Vì vậy "slot 1-3 giống nhau" là **giống NaN**, không phải bằng chứng gì.

---

## 2. (a) BẰNG CHỨNG BYTE-LEVEL — **số đếm chính xác, KHÔNG ước lượng**

Toàn bộ **10 file** × **15.536.189** bản ghi × **87.547** tick của `t1_f4` (merge theo `(ts,symId)` 1-1, key trùng **100 %** ở mọi cặp):

| phép so | kết quả **chính xác** | % |
|---|---|---:|
| key `(ts,symId)` trùng, mọi cặp | `15.536.189 / 15.536.189` | **100,0000** |
| **multiset `p0` trong TỪNG tick** `t1_f4` vs `t1_f4q` | `87.547 / 87.547` | **100,0000** |
| **multiset `p0` trong TỪNG tick** `t1_f4` vs `t1_f72` | `87.547 / 87.547` | **100,0000** |
| **multiset `p0` trong TỪNG tick** `t1_f4` vs `map_s1a2_x1` | `87.547 / 87.547` | **100,0000** |
| **multiset `p0` trong TỪNG tick** `t1_f4` vs `G015x26` (nguồn) | `87.547 / 87.547` | **100,0000** |
| `p0` trùng **byte** theo bản ghi: `t1_f4` vs `t1_f4q` | `14.794.060 / 15.536.189` | 95,2232 |
| `p0` trùng byte: `t1_f4` vs `t1_f72` | `14.774.237 / 15.536.189` | 95,0956 |
| `p0` trùng byte: `t1_f4` vs `map_s1a2_x1` | `14.778.235 / 15.536.189` | 95,1214 |
| `p0` trùng byte: `t1_f4` vs `G015x26` | `14.771.087 / 15.536.189` | 95,0754 |
| `p0` trùng byte: `t1_f4q` vs `G015x26` | `14.772.246 / 15.536.189` | 95,0828 |
| `p0` trùng byte: `t1_f72` vs `G015x26` | `14.770.798 / 15.536.189` | 95,0735 |
| **dòng KHÔNG có score** (file 1): `p0` == `G015x26` | `1.000.903 / 1.000.903` | **100,0000** |

Đọc đúng 4 dòng cuối + 4 dòng giữa:
1. **multiset/tick TRÙNG TUYỆT ĐỐI** với nguồn ⇒ mọi bộ `predwf_map_*` và `predwf_t1_*` **dùng chung MỘT pool giá trị lấy từ `G015x26`** — nghi vấn của `DIAG_SCORE72H` là **ĐÚNG về sự kiện**.
2. **dòng không có score giữ nguyên `p` của nguồn 100 %** — đúng nguyên văn nhánh `M["p_new"]=M.p` + `has` của `build_map.py:37-42`.
3. Bản ghi khác nhau ở ~**4,9 %** ⇒ 3 chân **KHÁC nhau thật**, chỉ khác ở **hoán vị trong tick**.

### 2.1 Vì sao `p_mean` "gần trùng khít ≤1 ULP" — **hệ quả tất yếu, không phải lỗi**

Multiset giống nhau ⇒ tổng giống nhau ⇒ hiệu `p_mean` chỉ còn là **nhiễu thứ tự cộng float**. Đo lại (10 file, `float64`): **`0,400423424210` giống nhau tới 12 chữ số ở CẢ 5 bộ**. Cộng kiểu `float32` (đúng như script chấm hay làm):

| bộ | mean (cộng float64) | mean (cộng float32) |
|---|---:|---:|
| `predwf_t1_f4` / `f4q` / `f72` / `map_s1a2_x1` | 0,400423424210 | **0,40042344** |
| `predwf_G015x26` (nguồn) | 0,400423424210 | **0,40042338** |

⇒ con số `0,41971642 / 0,41971648 / 0,41971651` trong `DIAG_SCORE72H` §4 là **cùng một multiset, khác nhau ở chữ số cuối do thứ tự cộng** — **không** có nghĩa "3 nhãn khác nhau mà cùng phân bố". Câu "base rate 14,14 % / rel5 / **65,71 %** không thể cho cùng phân bố điểm" **đúng là nghịch lý** — và lời giải là: **điểm KHÔNG đến từ 3 model đó**, nó đến từ pool `G015x26` (§3).

---

## 3. (b) NGUYÊN NHÂN + `file:line` — và **vì sao không phải lỗi**

`research/pipeline/build_map.py` (nguyên văn, 4 dòng quyết định):

```python
28: for f in sorted(glob.glob("/home/ubuntu/claudedata/predwf_G015x26/predict_wf_*.bin")):   # <-- NGUỒN GIÁ TRỊ
36:     M=G.merge(SC,on=["ts","sym"],how="left")                                             # SC = /home/ubuntu/ledger/pred_{name}.parquet (build_map.py:26)
37:     has=M.score.notna(); M["p_new"]=M.p
39:     sub["r_score"]=sub.groupby("ts").score.rank(method="first")                           # 1 = score tốt nhất
40:     sub["p_sorted"]=sub.groupby("ts").p.rank(method="first",ascending=False)              # 1 = p cao nhất
41:     key=sub.set_index(["ts","p_sorted"]).p; sub["p_new"]=key.reindex(list(zip(sub.ts,sub.r_score))).values
44:     a2=a.copy(); a2["p0"]=M.p_new.astype(np.float32).values; a2.tofile(f"{out}/{b}")       # <-- ĐÈ **CHỈ** slot p0
46: # kiem: phan phoi p moi == p cu theo tick (multiset) -> gate dong y het
```

- `:44` ghi **đúng một slot** (`p0`), **giữ nguyên** `ts/sym/p1/p2/p3` của file nguồn ⇒ **không sai slot**.
- `:39-41` là **hoán vị có kiểm soát**: coin xếp thứ `k` theo `score` nhận **giá trị `p` xếp thứ `k`** trong cùng tick ⇒ **multiset bất biến** — đúng như bằng chứng §2.
- `:46` chính là **kiểm tra do tác giả cố ý** ghi ra: "gate đồng ý hệt".
- Người gọi: `docs/prereg/PREREG_T1.md` **§3.2** (viết TRƯỚC khi chạy, commit `26a45ee`): *"`build_map.py` với nguồn giá trị = **G015x26** … y hệt cách sinh `predwf_map_s1a2` … Gate giữ NGUYÊN multiset P(win) trong từng tick"*. Log thật: `/home/ubuntu/cov/T1_BINS.out` (3 khối `===== build_map t1_f4|f4q|f72 =====`, `MAP_OK`, `TOTAL rows 15536189 changed 765102/763943/765391 (0.049)`).

**⇒ Kết luận (b): KHÔNG có lỗi ghi sai nguồn / sai slot / ghi đè ngoài ý muốn.** `p` bị "đè" **theo đúng thiết kế**: đường ống selector C2b **cố ý** giữ phân phối gate P(win) của G015x26 và chỉ đổi **ai nhận giá trị nào** (thứ hạng). Vì thế **phân phối điểm của 3 chân buộc phải giống nhau tới mức nhiễu cộng** — đó là **định nghĩa** của phép map, không phải triệu chứng lỗi.

---

## 4. Kiểm tra KHÔNG lẫn nguồn giữa 3 chân (3 ranker có thật khác nhau)

Nếu có bug "copy nhầm `pred_t1_f4.parquet` cho cả 3", thì `p` của 3 chân phải giống **từng bản ghi**. Đo (file `predict_wf_20220101.bin`, tick có score):

| | `score` mean của `ledger/pred_t1_*.parquet` | **corr(rank `p0`, rank `score`) trong tick** |
|---|---:|---|
| `t1_f4` | **1,19153** | **−1,000000** (đúng chéo chính) · vs score `f4q` −0,888 · vs `f72` −0,506 |
| `t1_f4q` | **0,84148** | **−1,000000** (chéo chính) · vs `f4` −0,888 · vs `f72` −0,669 |
| `t1_f72` | **0,76409** | **−1,000000** (chéo chính) · vs `f4` −0,506 · vs `f4q` −0,669 |

- **Chéo chính = −1,000000 tuyệt đối** ⇒ `p0` của mỗi chân là **rank-map của đúng parquet score của chân đó** (`−1` vì `p` cao ⇔ rank score tốt).
- **Chéo phụ < 1** và **mean score khác nhau** (`1,19` / `0,84` / `0,76`) ⇒ **3 ranker khác nhau thật**, không lẫn nguồn.

---

## 5. (c) PHẠM VI ẢNH HƯỞNG

### 5.1 Cùng đường sinh (multiset bị "đè" y hệt `t1_*`) — **đúng thiết kế, không phải lỗi**

Bins nào đi qua `build_map`-family (`build_map.py` · `x1/x1_build_map.py` · `x1/c4_build_map.py` · `x1/s3_build_map.py` — 3 bản sau là **bản sao có tham số hoá env**, cùng dòng `a2["p0"]=…`):

`predwf_map_s1a2` · `predwf_map_s1a2_x1` · `predwf_map_s1a2_x1_2021` · `predwf_map_s1a2_x1_5m` · `predwf_map_s1a2_x1_oi12_2021` · `predwf_map_c4_parity` · `predwf_map_c4_regen` · `predwf_map_c4_maxfav30` · `kbak/predwf_map_s1a2` · **`predwf_t1_f4` · `predwf_t1_f4q` · `predwf_t1_f72`** (đã kiểm: `predwf_map_s1a2`, `_x1` multiset/tick = **100 %** khớp G015x26, y hệt `t1_*`).

Dataset đã đẩy lên Kaggle theo PREREG_T1 §3b: `chuyendinh/bins-t1-f4`, `bins-t1-f4q`, `bins-t1-f72` (3 dataset 386 MB) — nội dung là 3 bộ bins trên.

**Hệ quả phải nhớ (đã pre-reg, nhưng dễ đọc sai):** mọi bins `predwf_map_*` **KHÔNG** chứa calibration của model mới. `p` luôn là **P(win) 4h của G015x26**; thứ tự coin mới là thông tin của model mới. **Slot 1-3 NaN** ở cả họ này ⇒ **không bao giờ** được đọc slot 3 của bins `predwf_map_*` như "điểm 72h của chân nào đó".

### 5.2 Họ KHÁC — đây mới là "writer copy `p` vào cả 4 slot" (không liên quan `build_map`, đã có trong `DIAG_SCORE72H` §2.4)

`/home/ubuntu/claudedata/predict_wf_ev2` (14 file): `p0==p1==p2==p3` **100 %**, mean cả 4 slot `0,09442`, NaN 0 % ⇒ writer của họ này **nhân bản cùng một giá trị vào 4 slot**. Đây là **mẫu lỗi writer đúng nghĩa** — nhưng **không** phải `predwf_t1_*`, và **không** đi qua `build_map`.

### 5.3 Kết quả / doc **đã dựa** vào bins `predwf_t1_*` và verdict

| nơi | dùng gì | có phải sửa SỐ không? |
|---|---|---|
| `docs/experiment/T1_LABEL3.md` §4 (bảng 3 chân + `binsSha256`), §5 (rate/CI), §6 (ràng buộc cứng) | 3 bộ `predwf_t1_*` chạy sim Oracle | **KHÔNG.** Phép so là **so THỨ HẠNG qua cùng một gate**; multiset giá trị giống nhau ở **mọi** chân **kể cả chân neo `L_g1`** (`predwf_map_s1a2`) ⇒ so sánh vẫn "sạch", đúng như pre-reg. Cần thêm **1 câu** nêu rõ `p_mean` không phải calibration của chân. |
| `docs/prereg/PREREG_T1.md` §3.2 | hợp đồng sinh bins | **KHÔNG** — đã ghi đúng từ trước. |
| `docs/diag/DIAG_SCORE72H.md` §2.4 + §4 (ý 4) | kết luận "chưa lý giải" | **KHÔNG sửa số** — chỉ cần **errata**: ẩn số nay **đã lý giải**, và **không phải lỗi**. |
| 5 arm `model_ruler` / deploy (`RESULT_MODEL_RULER`, `DIAG_SCORE72H` §3) | bins arm (trainer `net015`) | **KHÔNG** — đường khác, không qua `build_map` (khớp `DIAG_SCORE72H` §2.4: "không ảnh hưởng 5 arm"). |

Kết luận **kinh tế** của T1 (`T1_f4` xấu hơn neo ở `TSloss%`/`win%`) **không bị đảo** bởi phát hiện này: nó đến từ **thứ hạng khác** (đo được: `t1_f4` vs `t1_f4q` khác **4,78 %** bản ghi; chéo chính corr `−1,000000` = đúng nguồn), không từ mức giá trị `p`.

---

## 6. (d) CÒN LẠI GÌ KHÔNG KẾT LUẬN ĐƯỢC

1. **Output thô của 3 model T1** (`s_{L_f4}`, `s_{L_f4q}`, `s_{L_f72}` **trước** khi vào bin) **không được lưu ra đĩa** ⇒ không so được "điểm model" vs "điểm trong bins" theo byte. Đã bù bằng **kiểm gián tiếp có sức mạnh tương đương**: `ledger/pred_t1_*.parquet` (đầu vào **duy nhất** khác nhau giữa 3 chân) + `corr(rank p0, rank score) = −1,000000` chéo chính (§4). Muốn **trực tiếp**: lưu `s_*` ra parquet ở lần chạy sau (`t1_label3.py:119-127` chỉ ghi `score`).
2. **Tỷ lệ "đổi" 4,9 %** (765.102 / 763.943 / 765.391 dòng) **không tách được** thành "khác thứ hạng thật" vs "nhiễu tie-break do `rank(method="first")` + sort không ổn định" — đây là **đặc tính đã biết** của `build_map.py`, đã ghi ở `docs/experiment/G4_RECIPE_C4.md` §0.2 / §4.3 ("`build_map.py` KHUẾCH ĐẠI sai số 1 ULP thành 0,37 … nợ kỹ thuật"). **Không đụng vào** (sửa `kind="stable"` sẽ ĐỔI bins deploy ⇒ cần pre-reg riêng — như G4 đã kết luận).
3. **`p0` có được dùng làm `symbolPred` đúng như giả định không** — đã khớp với ghi chép hạ tầng (`python3 build_map.py s1a2 $P | tail -2` → `WfoDataset.horizonIdx=0`), nhưng job này **không chạy sim** để xác nhận lần nữa (đúng ràng buộc: không sim).

---

## 7. Repro (lệnh đã chạy, thuần offline, output nhỏ)

```bash
# (i) 5 md5 khác nhau -> không phải bản sao
md5sum /home/ubuntu/predwf_t1_{f4,f4q,f72}/predict_wf_20220101.bin \
       /home/ubuntu/predwf_map_s1a2_x1/predict_wf_20220101.bin \
       /home/ubuntu/claudedata/predwf_G015x26/predict_wf_20220101.bin
# (ii) log thật của 3 lần build_map (nguồn + tỷ lệ đổi 0.049 + MAP_OK)
sed -n '1,49p' /home/ubuntu/cov/T1_BINS.out
# (iii) byte-level, tự chứa (đếm chính xác, in ra rất ít)
python3 - <<'PY'
import numpy as np, glob, os
dt = np.dtype([("ts",">i8"), ("sym",">i2"), ("p",">f4", 4)]); D = "/home/ubuntu"
DIR = {k: f"{D}/{v}" for k, v in dict(t1_f4="predwf_t1_f4", t1_f4q="predwf_t1_f4q",
        t1_f72="predwf_t1_f72", std="predwf_map_s1a2_x1", g015="claudedata/predwf_G015x26").items()}
files = sorted(os.path.basename(x) for x in glob.glob(DIR["t1_f4"] + "/predict_wf_*.bin"))
for ref in ("t1_f4q", "t1_f72", "std", "g015"):
    n = nk = nms = nt = np0 = 0
    for f in files:
        A = {k: np.fromfile(os.path.join(v, f), dtype=dt) for k, v in DIR.items()}
        b = A["t1_f4"]; c = A[ref]; N = len(b); n += N
        nk += int((b["ts"] == c["ts"]).all() and (b["sym"] == c["sym"]).all()) * N
        x = b["p"][:, 0].astype(np.float32); y = c["p"][:, 0].astype(np.float32)
        np0 += int((x.view(np.uint8).reshape(N, 4) == y.view(np.uint8).reshape(N, 4)).all(axis=1).sum())
        u, st = np.unique(b["ts"], return_index=True); bl = list(st) + [N]; nt += len(u)
        nms += sum(1 for i in range(len(u)) if np.array_equal(np.sort(x[bl[i]:bl[i+1]]), np.sort(y[bl[i]:bl[i+1]])))
    print(f"t1_f4 vs {ref:7s}: rec={n} keyEq={nk} p0byteEq={np0} ({100*np0/n:.4f}%) multisetTick={nms}/{nt} ({100*nms/nt:.4f}%)")
PY
```

Kết quả (iii) in ra đúng 4 dòng: `keyEq = 15.536.189` (mọi đối chiếu) · `multisetTick = 87.547/87.547` (**100,0000 %**) cho cả `f4q`/`f72`/`std`/`g015` · `p0byteEq` = 14.794.060 / 14.774.237 / 14.778.235 / 14.771.087.
Đối chiếu chéo nguồn (§4) dùng thêm `ledger/pred_t1_*.parquet` + `corrcoef` theo tick (đã chạy, số ở bảng §4).

**Kết luận 1 dòng:** `p` của `predwf_t1_{f4,f4q,f72}` **bị đè thật, nhưng theo đúng thiết kế `build_map.py:44`** (chỉ slot 0, pool giá trị G015x26, multiset/tick bất biến 100 %); **không có lỗi writer/slot**, **không kết quả nào phải sửa số**, chỉ cần **errata 2 doc** để ẩn số "chưa lý giải" ở `DIAG_SCORE72H` §2.4/§4 không còn bị đọc thành dấu hiệu lỗi.
