# PREREG_K_DENSITY -- GIAN top-K (SELECTOR_RANK_TOPK 8->12->16) tren gate T170 / DEV 2021

Viet va commit TRUOC khi chay bat ky sim nao. Khong sua sau khi thay ket qua.

Pre-reg lien quan: `docs/PREREG_K12.md` (K=8->12 tren C3_FULL 48-thang, dataset wfo_ds_x1,
KHONG gate T170) -- KHAC nen/khac cua so, va khong co ban RESULT trong tree. Pre-reg NAY chay
tren nen T170 (baseline THANG cua readjudicate) + dataset wfo_ds_x1_2021 (18 fold 2021Q3..2025Q4),
va them truc MAT DO (density) + them K=16. Muc tieu do user dat ra la MAT DO entry, khong chi chat luong.

## 0. Vi sao mo nhanh nay
Gate T170 (SIM_GATE_DYN_SCALE=1.70) la baseline THANG cua readjudicate: chat luong + rui ro tot hon
(UW 92 vs 248, maxDD -11.84 vs -16.13) danh doi CAGR. NHUNG gate chat lam entry THUA / bursty (n=1089
so voi 2559 cua baseline scale 1.00). User muon MAT DO entry DEU hon / nhieu hon ma khong lam xau
chat luong / rui ro dang ke. Bien re nhat de gian mat do la top-K selector (SELECTOR_RANK_TOPK): moi
tick chon top-K coin theo rank S1 thay vi top-8. K lon hon => nhieu ung vien vao gate T170 hon => co the
day n len va lap khoang trong thoi gian.

## 1. Thiet ke -- CHI doi MOT bien
`profiles/x1_gs_t170_k12.properties` = ban sao NGUYEN VAN `profiles/x1_gs_t170.properties`, doi DUY NHAT
`SELECTOR_RANK_TOPK=8` -> `SELECTOR_RANK_TOPK=12`. Tuong tu `x1_gs_t170_k16.properties` -> `=16`.
KHONG doi gate (SIM_GATE_DYN_SCALE=1.70 giu), KHONG doi S1 9-feat, KHONG doi net015, KHONG doi
DCA/exit/sizing/bins. Bang chung 1-dong-diff se ghi trong RESULT.

Dataset dung CHUNG `wfo_ds_x1_2021` cho ca 3 arm: SELECTOR_RANK_TOPK duoc ap o SIM-time (top-K per tick
trong SimulatorMarketLevelTicker1MStopLoss + DetectEntrySignal2TradeNormal), KHONG bake vao ExportWfoDataset
(xac nhan boi PREREG_K12 muc 2 + F1_FLOW dung chung 1 dataset cho K=8/16/24/32). => KHONG rebuild dataset.

Bien: K=8 (baseline), K=12, K=16. Multiplicity k=2 variant => sqrt(2 ln 2)=1.177 < 1.21 (CI_INFLATE
built-in cua c3_rates block-72h). => KHONG noi rong CI them; 1.21 da bao mult.

## 2. Cong (gates) -- PASS truoc khi doc variant
(a) REPRODUCTION: re-run K=8 (profile x1_gs_t170.properties, dataset wfo_ds_x1_2021, jar hien) ->
    printDone md5 phai = **efb793e2** (n=1089). Sai lech bat ky byte nao => DUNG, dieu tra (bins troi/
    jar khac/code-sha khac), KHONG doc K12/K16.
(b) CHI doi K: diff profile clone vs goc = DUNG 1 dong (SELECTOR_RANK_TOPK). Sai => DUNG.

## 3. Cham diem -- HAI MAT (bao ca hai cho master/user can trade-off)
### (i) CHAT LUONG -- rate + CI khoi 72h x1.21 (variant - baseline), moi K vs X1_GS_T170_2021
`python3 research/analysis/x1_rates.py X1_GS_T170_2021 <variant>`. Rate chat luong: win%, TSloss%,
meanP, mP|SL. Luat THANG chat luong (nhu readjudicate): **>=2 rate CHAT LUONG ngoai CI CUNG huong TOT**
+ PASS rang buoc cung. `n`, `mMargin` la bien KIEM SOAT (khong lam bang chung chat luong).
Rang buoc cung tung nam (tuyet doi, nhu readjudicate): maxDD<=15, UW<=120, nam>=0, quy>=-5. Bao them
so RELATIVE so voi K8 (maxDD/UW co xau di khong).

### (ii) MAT DO -- do tu printDone.csv (cot `start` = entry time)
- `n` lenh; lenh/ngay trung binh (n / so ngay span DEV 2021-07-01..2025-12-31).
- Do DEU theo thoi gian: std / CV so lenh moi TUAN (CV = std/mean, thap = deu hon).
- Khoang trong dai nhat giua 2 lenh lien tiep (max gap, ngay).
So sanh K8 vs K12 vs K16. Muc tieu user = mat do DEU/nhieu hon => CV giam va/hoac max gap giam
va/hoac lenh/ngay tang la HUONG TOT ve density.

## 4. Quy tac phan quyet -- chot TRUOC khi thay so
Day KHONG phai bai toan accept/reject don. User muon density; nen bao cao SONG SONG:
- Verdict CHAT LUONG moi K (WIN >=2 rate tot ngoai CI + hard-PASS / NULL / HAI).
- Verdict MAT DO moi K (deu hon / nhieu hon bao nhieu).
- Trade-off: K nao cho density DEU hon (CV thap hon / gap ngan hon / lenh nhieu hon) MA quality khong
  xau dang ke (khong sinh rate tot ngoai CI theo huong XAU, khong pha hard-constraint so voi K8).
KHONG tune K khac sau khi thay so (K co dinh pre-reg 8/12/16). Null/hai co tinh thong tin -> bao that.

## 5. Pham vi
DEV only (SIM_END_DATE=20251231). KHONG dung holdout 2026 (HoldoutSeal). KHONG cham 242. KHONG deploy.
KHONG sua code Java / rebuild jar. Chi them 2 file profile + 1 pre-reg + 1 result + chay sim.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_011zpgT8SsGrmcqzxbC93PQT
