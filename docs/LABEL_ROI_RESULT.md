# LABEL_ROI_RESULT — nhan nao KHOP voi ROI THAT: dong lo hong A11 (ho 4h chua tung duoc do)

Chay 2026-09-04 tren Oracle: `python3 /home/ubuntu/java/fsrun/label_align.py C2b`.
Script **da co san** tu truoc (khong viet moi), chi la **chua tung chay tren C2b**.
**MO TA**, khong phai kiem gia thuyet. CHI DEV.

Tap: **970 lenh** `PREDICT_SYMBOL_TRADE` cua run `C2b`, join label **100.0%**.
`ret = pnl / margin` (ROI THAT cua sim, sau chi phi). `ret` TB = +2.77%, winrate 85.2%.
Da xu ly bay mui gio: `ts = ((ms_GMT7 - 7h) // 900000) * 900000`.

## 0. VI SAO LAM

`AUDIT A11` la phep so da dung de ket luan **"khong can doi nhan"**:
`g1lite 0.584 > maxFav_72h 0.574 > g1_replay 0.507` (tuong quan voi ROI that, n=2263, ledger v3).
Nhung no **CHUA TUNG bao gom ho 4h** — tuc chua ai do `maxFav_4h` (nhan ruot cua G015) khop bao
nhieu voi ROI that. `C4H_RESULT` do duoc `%bat` o 4h **cao hon** 72h (25.8% vs 17.5%), nen phai
biet nhan 4h co dang theo duoi hay khong.

## 1. TUONG QUAN VOI ROI THAT — 14 nhan, xep giam

| nhan | spearman vs ROI that | AUC | ret Q1..Q5 |
|---|---|---|---|
| **`maxFav_72h`** | **+0.472** | 0.923 | -8.8 +2.9 +5.2 +7.0 +7.5% |
| `maxFav_72h / abs(maxAdv_72h)` (path quality) | **+0.452** | 0.900 | -8.7 ... +7.4% |
| `maxFav_72h - median(univ)` | +0.394 | 0.829 | |
| `maxFav_24h` | +0.379 | 0.858 | |
| `retEnd_72h` | +0.373 | 0.807 | |
| rank pct `maxFav_72h` trong tick | +0.365 | 0.806 | |
| `retEnd_24h` | +0.322 | 0.791 | |
| `maxFav_24h - median(univ)` | +0.317 | 0.783 | |
| `retEnd_72h - median(univ)` | +0.297 | 0.737 | |
| triple-barrier 72h: +6% truoc -5% | +0.227 | 0.732 | |
| **`maxFav_4h` (lien tuc)** | **+0.222** | 0.729 | -0.8 +1.5 +2.4 +3.9 +6.9% |
| **`maxFav_4h >= 6%`** — **NHAN THAT CUA G015** | **+0.175** | 0.658 | +0.2 +3.3 **-0.2** +4.7 +5.9% |
| triple-barrier 72h: +3% (arm) truoc -5% | +0.078 | 0.583 | |
| **`-pNoPump`** = **diem G015 dang deploy** (`symbolPred`) | **-0.019** | **0.518** | +2.9 +3.2 +3.0 +2.4 +2.4% |

## 2. WITHIN-TICK (dung vai tro SELECTOR) — 115 tick co >= 4 lenh

| nhan | rho TB trong tick | %tick rho>0 |
|---|---|---|
| **`maxFav_72h`** | **+0.354** | **79%** |
| rank `maxFav_72h` / `maxFav_72h - median` | +0.354 | 79% |
| `pathq72 = fav/abs(adv)` | +0.351 | 77% |
| `maxFav_24h` | +0.287 | 73% |
| `retEnd_72h` | +0.282 | 69% |
| **`maxFav_4h`** | **+0.192** | 65% |
| **`-pNoPump`** (model dang chay) | **+0.004** | **47%** |

## 3. BON KET LUAN

1. **Nhan 4h la mot trong nhung nhan YEU NHAT, khong phai manh nhat.**
   `maxFav_4h >= 6%` (**dung nhan G015 duoc train**) chi **+0.175** — **thu 12/14**, chi hon
   triple-barrier +3%. `maxFav_72h` **+0.472** = **manh hon 2.7 lan**. Trong tick: +0.192 vs
   +0.354 = **kem 1.8 lan**, va chi 65% tick duong so voi 79%.
   ⇒ **Lo hong A11 da dong: chan troi 4h KEM HON HAN 72h lam muc tieu.** Viec S1 dung nhan 72h
   la **dung**; mat yeu la **nhan cua G015**.
2. **Nhi phan hoa lam MAT thong tin.** `maxFav_4h` lien tuc **+0.222** > ban nguong `>= 6%`
   **+0.175**. Va o 72h: `maxFav_72h` **+0.472** > triple-barrier `+6% truoc -5%` **+0.227**.
   Nhung `pathq72 = fav/abs(adv)` (**ban LIEN TUC** cua cung y tuong up/down) giu duoc **+0.452**.
   ⇒ Thong tin ve phia sut **co gia tri**, chi la **dung nhi phan hoa no**.
3. **`%bat` cao tren mot nhan TE thi vo gia tri.** `C4H_RESULT` do `%bat` o 4h la **25.8%**, cao
   hon 72h (17.5%). Nhung nhan 4h khop ROI that kem 2.7 lan. ⇒ **`%bat` noi ve MODEL; tuong quan
   voi ROI that noi ve NHAN.** Phai co ca hai, va cau hoi **nhan** ap dao. Day la ly do cu the
   phai giu canh bao "khong so `%bat` giua cac nhan khac nhau".
4. ⚠️ **Diem G015 dang deploy khong phan biet duoc khoi nhieu TRONG tap da admit**:
   spearman **-0.019**, AUC **0.518**, trong tick **+0.004 / 47% tick duong**.
   **PHAI doc dung**: day la tap **da bi loc** boi chinh diem do (top-8), nen co
   **range restriction** — dung ket luan "G015 vo gia tri toan cuc"
   (`selector_edge_evidence §3` da ghi dung bay nay cho `CONF_SIZE`). Ket luan dung la:
   **trong tap duoc admit, diem G015 khong con mang thong tin xep hang nao them.**
   Ma chinh diem do dang: (a) dat nguong gate (`dyn_thr`), (b) chia nhanh exit STRONG/WEAK o
   `symbolPred > 0.29`. Hai co che nay dang dieu khien boi mot dai luong khong co thu tu trong
   vung van hanh.

## 4. Doi chieu voi A11 — khong so truc tiep duoc

A11: `maxFav_72h 0.574` tren **n=2263** (ledger v3, nhieu run). Day: **+0.472** tren **n=970**
(chi C2b). Hai tap lenh khac nhau nen **gia tri tuyet doi khong so duoc**; cai dung duoc la
**THU TU giua cac nhan trong cung mot lan chay**, va thu tu do la ket qua o muc 1-2.
`g1lite` **khong** co trong lan chay nay (`label_align.py` khong tinh no).

## 5. Cai job nay KHONG lam

Khong train, khong chay java, khong sinh bins, khong cham VALIDATION/HOLDOUT. Khong doi nhan
nao — muon doi nhan train cua S1 phai pre-reg va phai do lai ca chuoi (nhan doi => train lai =>
bins doi => moi so C2b doi).
⚠️ `label_align.py` dung ham in san co thay vi `logging` — trai luat repo; khong sua trong job
nay de giu nguyen ban da chay.
