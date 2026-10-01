# RESEARCH_GRID_TRADING — tong hop ho luoi (GRID) + doi chieu he thong nay

Ngay: 2026-10-01. Pre-reg: `docs/prereg/PREREG_GRID_RESEARCH.md`. Ket qua: `docs/result/RESULT_GRID_RESEARCH.md`.
Muc dich: **khao sat phuong phap** (khong tu bia — tong hop tu cac ho grid da biet) + doi chieu voi
du lieu/phi/he thong hien co de quyet dinh co dang do tiep khong.

---

## 1. CAC HO LUOI (moi ho: co che phi · rui ro chinh · dieu kien co lai)

| ho | co che | phi (maker/taker) | rui ro chinh | dieu kien co lai |
|---|---|---|---|---|
| **Arithmetic grid** (buoc % co dinh) | munh muc cach deu theo GIA | dat limit ⇒ **maker** 2 dau | treo hang khi gia trend xuong (khep kin o bien duoi) | gia **dao dong trong dai** (range-bound) |
| **Geometric grid** (buoc % tuong doi) | muc cach deu theo **log-gia** | maker | nhu tren, nhung phan bo deu hon khi gia bien dong manh | range-bound, dai gia rong |
| **Neutral grid** (khong dat cuoc huong) | mua duoi / ban tren, ton kho 0 quanh neo | maker | **ton kho lech** khi trend; lo MTM | dao dong doc lap huong |
| **Long grid / Short grid** (dinh huong) | luoi chi 1 phia (vd chi mua tut) | maker | trend nguoc chieu = lo khong gioi han | dung chieu **+** range |
| **Infinite / unbounded grid** | luon co lenh cho MOI muc, khong bien | maker | **vo han ton kho** khi trend 1 chieu — pha san tai khoan | can **tran ton kho** hoac trend filter |
| **Range-detection + grid** (chi chay khi phat hien range) | do range (Donchian/BB/ADX/VR) roi moi dat luoi | maker | phat hien TRE (range vo) -> luoi an trend | **phat hien dung** + range that |
| **Vol-scaled spacing** (ATR/σ-scaled) | buoc luoi = k·ATR; bien noi theo vol | maker | vol no ra -> buoc qua rong -> it khop; vol co lai -> luoi day | vol on dinh, co **mean-revert** |
| **Grid + trend filter** | luoi + tat/khoa 1 phia khi co trend (MA/ADX) | maker | filter tre => van om hang nguoc 1 phan | trend filter dung |
| **Inventory-capped / martingale-ish** (DCA grid, 1-1-3-8) | tang size theo bac khi gia di nguoc | **taker** (vao theo tin hieu) | **bậc nang = rui ro tap trung**; cuu duoc cu nhung phong to lenh | trend **co hoi phuc** sau do |
| **Spot grid vs Futures grid** | spot: mua/ban coin that. futures: **perpetual + funding** | maker ca hai; futures them **funding** | futures: **funding am/duong** an vao ton kho; don bay ⇒ thanh ly | spot: range; futures: range **+ funding ≤ 0 cho long** |
| **Rebalancing / MA band** | giu ty trong, mua khi lech duoi band | maker | trend = rebalance nguoc lien tuc (bleed) | mean-reverting |

**Tong hop 1 cau:** grid khong phai "alpha huong" — no **ban bien dong thuc hien (realized vol)**
trong mot dai, doi lay **rui ro ton kho khi gia di ra khoi dai**. Lai gop = `Σ(buoc luoi) × so chu ky`
tru `phi × so lan khop` tru `lo MTM cua ton kho cuoi`. Vi vay: **phi quyet dinh nguong**, **trend quyet
dinh song/con**, **range-bound la dieu kien tien quyet**.

## 2. DOI CHIEU VOI HE THONG NAY

**2.1 Ho nao hop du lieu 1m + 627 coin + phi hien co?**
- Du lieu 1m (OHLCV) **du** cho: arithmetic/geometric, neutral, bounded, vol-scaled spacing,
  range-detection + grid, inventory cap. **Khong du** cho: maker fill that (can **orderbook/queue** —
  repo chi co 991 chan **taker** do slip ≈ 0, `RESULT_COST_TRUTH`).
- ⇒ bat buoc bao **2 muc phi**: maker (can tren) vs taker (can duoi). Grid truyen thong song nho
  maker 0,02%/chan; he thong **dang tinh taker** `base 0,112%/vong`.
- Ho **da CAN** (khong de xuat lai): config K×size · gate features/label · OFI · regime/breadth gate ·
  pump-detect · money-ranker · liquidity · reversal · exit TS · cross-section/Track B · short.
  Phan luoi **da co san trong he**: `DCA_GRID_WEIGHTS=1,1,1,1` + `DCA_GRID_SCALE=6.0` (luoi DCA **trong
  vi the**, `RESULT_FLATGRID`: luoi phang lam giam tap trung 1 coin 58,5%->18% nhung **UW 92->147 ngay**
  vi **mat chuc nang cuu cum FTT 11/2022** — bai hoc: "luoi sau cuu cu" la 1 dang grid + martingale-ish).

**2.2 Chon COIN** — chi so do duoc tu 1m, khong look-ahead: `ADR%`, `vol_ann`, **`ER` (efficiency ratio)`,
`VR(k)` (variance ratio: <1 mean-revert), `%time in band`, thanh khoan (tu `fs` parquet: `fs_dvol_7d`,
`fs_amihud_7d`). Coin "hop grid" = **ER thap / VR<1 / ADR vua phai** (du bien dong de co chu ky, khong
trend manh). Do thu ER/VR tren DEV trong `RESULT_GRID_RESEARCH`.

**2.3 Chon THOI DIEM (regime range-bound)** — co lien he `RESULT_ALT_REGIME_WAVES` (che do ALT/MAJOR,
breadth) va `RESULT_BREADTH_*`: breadth/regime **do duoc**. Nhung canh bao: (i) phat hien regime la
**tre** (range vo -> an trend); (ii) `RESULT_RANGE4H_TOPK` cho thay **luat "chon bien dong nhat" THUA
ca basket ngau nhien** (anti-signal) — nen "chon thoi diem" phai do bang **CI**, khong suy dien.

**2.4 RUI RO grid trong TREND — chan duoc khong?** 3 lop chan, do duoc tu du lieu nay:
① **tran ton kho** (bounded grid) — chan lo vo han nhung **khong** chan lo MTM trong dai;
② **trend filter** (ER/MA) — tat luoi khi trend; ③ **phi maker** — giam chi phi moi chu ky.
⇒ Danh gia dinh luong o `RESULT_GRID_RESEARCH` (ton kho max, maxDD MTM, net khi |ret| lon vs nho).

## 3. KET LUAN KHA THI (dien sau khi do)
→ xem `docs/result/RESULT_GRID_RESEARCH.md` muc "TRA LOI".
