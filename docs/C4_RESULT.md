# C4_RESULT — no ve sinh: parity c2b_min / c2c_round + va 3 script tro sai profile

Chay 2026-09-04 (Oracle, `njava=0`, dia 16G). Khong pham vi moi: day la buoc **XAC NHAN LAI +
COMMIT** hai thay doi da duoc chung minh truoc do, khong phai thi nghiem moi. Chi DEV.

## 1. Loi SONG da tim ra va va — 3 script tro vao profile CHET

`research/runs/dev_br.sh:9`, `research/runs/dev_k.sh:10`, `tools/parity_clean.sh:12` deu tro
`P=/home/ubuntu/java/profiles`. Do dac:

- `/home/ubuntu/java/profiles/c2b.properties` la ban **2026-09-03 09:50**, tuc **TRUOC** khi pin
  bins (`19b976d`, 18:39). **KHONG mot file nao** trong dir do co `WFO_FUNDING_PRED_DIR`
  (`grep` tra ve rong tren ca 18 file).
- Dir do con giu doan comment cong thuc gate **SAI** (ban "clamp co tran => nguong hang 1.713%")
  da bi rut o `ce66cf0`/`b3181fd`.
- Dir do con co `c2b_min.properties` **ban cu 1950 B** trong khi ban git la 3119 B => **hai phien
  ban c2b_min**. Con so "15 key / PROFILE_HASH 531b4ae7b4b64885" trong `AUDIT_APPLIED` Bang 2 #2
  la cua **ban cu**; ban git la **16 key / `a2f859b2463108fe`**.

Hau qua: moi run phong qua 3 script nay **hom nay se throw rc=1** o buoc build (sau `19b976d`
thi thieu bins => `ExportWfoDataset` fail cung). **Truoc** `19b976d` thi te hon: thieu key =>
`WfoDataset` chi `LOG.warn` roi **fallback Aerospike** => ra so KHAC ma khong bao loi. Day dung la
lop loi "bay baseline" da mac mot lan (`dev_h1.sh` dung nen C2a thay vi C2b).

**Da va:** tro ca 3 ve `$R/profiles/` (trong git) + chen guard fail-fast ngay sau dong `P=`:
`grep -q '^WFO_FUNDING_PRED_DIR=' $P/c2b.properties || exit 4`. Ban goc giu o `*.bak_c4`.

## 2. Parity — build dataset 1 lan, 2 sim tuan tu

Build `rc=0`, provenance khop: `bins.dir=/home/ubuntu/predwf_map_s1a2`, `bins.files=10`,
`bins.sha256_16=0f8721558fbd87ef`, `foldCount=10`, dataset 1.8G (da `rm -rf` sau khi xong).

| run | profile | keys | PROFILE_HASH | equity | lenh | maxDD | underwater | byte-identity vs C2b |
|---|---|---|---|---|---|---|---|---|
| C2b (moc) | `c2b` | 23 | `7fd2895a1e7fefe0` | 60,390 | 970 | -13.1 | 93d | (moc) |
| **C4_C2BMIN** | `c2b_min` | 16 | `a2f859b2463108fe` | **60,390** | 970 | -13.1 | 93d | **PASS** |
| C4_ROUND | `c2c_round` | 19 | `b66e2773811f4fda` | 59,846 | 948 | -13.2 | 95d | KHAC (dung thiet ke) |

- `C4_C2BMIN`: `printDone.csv` md5 **`8f7afdfb27b15f5b6d4c886700def93c`** — trung moc byte-identity
  cu. `qret.py` trung tung o: nam 11.6/45.4/6.3, maxDD nam -13.1/-1.9/-6.4, quy>=5% **6/10**,
  underwater 93d. => **bo 7 key la TRO, xac nhan lai lan hai.**
- `C4_ROUND`: ra **dung 59,846** = moc RND2 => **3 key `SIM_AI_DYNAMIC_*` DUOC doc tu profile
  that**, khong co bug wiring. nam 10.4/46.4/5.8, maxDD -13.2, quy>=5% 6/10, khong nam am.
  Theo `CI_REAUDIT`: hieu C2b-RND2 = +0.45pp, CI **[-0.63, +1.46]** => **khong phan biet duoc**.

## 3. CONFIG_STRICT — do truc tiep bang DumpConfig (khong can dataset)

| profile | keys | ket qua `CONFIG_STRICT=1` |
|---|---|---|
| `c2b` | 23 | **DUNG** — 5 key KHONG AI DOC: `DISABLE_PREDICT_SYMBOL, HARD_STOP_LOSS_RATE, TIME_STOP_HOURS, TS_GAP_CONST, TS_MIN_GAP` |
| `c2b_min` | 16 | **OK, ca 16 key deu duoc doc** |
| `c2c_round` | 19 | **OK, ca 19 key deu duoc doc** |

Phan biet quan trong: `c2b_min` bo **7** key so voi `c2b`, trong do **5 la khong ai doc** (go sai
ten / da chet) va **2 la duoc doc nhung TRO ve hanh vi** (`NUMBER_ORDER_BUDGET`,
`DCA_GRID_LEVELS` — byte-identity chung minh).

⚠️ **"Duoc doc" KHAC "co tac dung".** `c2c_round` khai `SIM_AI_DYNAMIC_MAX=2.0` va key do **duoc
doc**, nhung nhanh `Math.min(..., AI_DYNAMIC_MAX)` **da bi xoa khoi code**; `AI_DYNAMIC_MAX` chi
con la tran UNG VIEN o gate tang 1, ma tang 1 **bi bo qua** khi `SELECTOR_RANK_TOPK>0`. Vay chi
`MULTIPLIER` va `MIN` doi hanh vi.

⚠️ `CONFIG_HASH` hien tai la **`f79ddd824eafb978`** (c2b/c2b_min) va **`4499f72932023a39`**
(c2c_round). Ban ghi cu `6f5ba81442f7e80c` **da lac hau** (code doi sau do) — dung so cu de doi
chieu se sai.

## 4. Da apply trong commit nay

1. Va 3 script tro sai profile + guard bins-pin (muc 1).
2. **`tools/run_c2b_dev.sh`: default profile `c2b.properties` -> `c2b_min.properties`.**
   Ly do: byte-identical da chung minh 2 lan, va day la dieu kien de bat duoc `CONFIG_STRICT`.
   **Anh xa hash phai nho:** baseline C2b tu nay khai `PROFILE_HASH=a2f859b2463108fe` (16 key);
   moi ban ghi cu ghi `7fd2895a1e7fefe0` (23 key) la **CUNG MOT hanh vi**, chi khac 7 key tro.
3. `profiles/c2b.properties` **GIU NGUYEN** lam ban ghi lich su (khong sua de khong pha lien ket
   voi cac ban ghi cu). Nhung no **se truot** `CONFIG_STRICT=1`.

## 5. CHUA apply — de Uni quyet

- **`CONFIG_STRICT=1` lam gate mac dinh trong runner**: chua bat. Ly do: runner nhan profile lam
  tham so, va `run_ticklog_gate.sh` truyen `c2b.properties` + `c2b_ticklog.properties` — hai file
  nay se **exit 2** neu bat STRICT toan cuc. Muon bat thi phai don 5 key chet khoi ca hai truoc.
- **Chuyen baseline sang `c2c_round`** (so tron): `PREREG_RND` da chot TRUOC rang hanh dong la
  "thay bang so tron", RND2 PASS het 4 tieu chi, va dieu kien khoa cua chinh `c2c_round`
  ("de SAU khi GS wave-1 ket thuc") **da thoa** — wave-1 chot (b) luc 2026-09-04 02:06.
  Chi phi: -544 USDT equity, **nam hoan toan trong nhieu** (CI [-0.63,+1.46]pp). Doi lai: bo dau
  vet HPO 5 chu so. Day la quyet dinh gia tri, khong phai quyet dinh so lieu.

## 6. Ghi nhan ha tang — bay moi

**Sim exit code KHONG dung duoc lam tin hieu thanh cong.** Ca hai sim in `rc=1` trong khi run
hoan tat day du (`done:147/970/970`, `printDone.csv` byte-identical moc). Nghia la moi script
gate tren `$?` cua sim se bao dong gia — va nguoc lai, mot lan sim CHET THAT se **giong y** nhu
vay. Tieu chi thanh cong phai la `done:` + `b:` + byte-identity/`qret.py`, **khong** phai rc.
