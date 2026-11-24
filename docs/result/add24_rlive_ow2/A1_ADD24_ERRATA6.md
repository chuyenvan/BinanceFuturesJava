# A1 ADD24 ERRATA6 - audit doc lap delta 3e6da6eb..274f55eb (2026-11-24 ~09:35-10:10 +07)
VERDICT: DUYET HEAD 274f55ebfb0c1dbe7e9d073fe398eb6d6831ad80 - PASS-WITH-MINOR cho DELTA CODE.
LUOT #2 KHONG duoc chay NGAY: (a) Vision 2026-11-23 chua phat hanh (HTTP 404); (b) MASTER phai quyet M1 (buffer-day) va sua errata (M2, m1-m3) truoc.

## 1. Delta (git diff 3e6da6eb 274f55eb: 2 file, +27/-2)
- Chi cham khoi `if official` cua run_rlive.sh (dong 33-43) + rlive_fixture.py (chi official goi). dev1105 khong doi. Khong doi nguong/nhan/logic cham/OW2/T_cut/EXINFO/stub.
- P1 THAT: tai hien bang tcut() that: read cu => A=[2026-11-24] B=[07:00 2026-11-23]; khop rlive_1124_run.log (ValueError '07:00 2026-11-23').
  Ban sua: TCUT=[2026-11-24 07:00] TDAY=[2026-11-23] DAYS=11-19..11-23; ca 3 assert + 2 case deu qua. `date -d "2026-11-23 +1 day"` = 11-24 (TZ host +07 va UTC deu dung).
  Assert exit 15 KHONG chan nham fallback prereg dong 90-91: tcut() chi tra TDAY in 11-19..11-23, TCUT=TDAY+1 07:00 in 11-20..11-24 => deu khop regex; khong ngay COMPLETE => python in rong => exit 15 (dung).
- P2 THAT: EXINFO byte dau '{"' ; gzip.open(EXINFO) => BadGzipFile. Dev khong lo vi dev1105 dung fx1105 co san (prep khong chay; exinfo mac dinh FIXT *.json.gz).
  Ban sua: tu chay exinfo_gz + 2 dong prep (gzip.open->copyfileobj) trong sandbox: sha fx/exinfo.json = dcfa03c7...1684; gz tat dinh (2 lan byte-identical); gz passthrough dung. prep chi nhan duong dan khac, moi hanh vi khac giu nguyen; rlive_fixture dong 102 van doc EXINFO goc (json tho) - dung.
  Ghi chu nho: manifest.json (prep) inputs.exinfo ghi sha cua BAN GZ; sha goc nam o manifest_ow2.json - chap nhan.
- Worktree sach, HEAD 40 ky tu dung, nhanh v1.2/add24-harness. Hooks: .git/hooks chi *.sample, khong core.hooksPath => bo qua hook KHONG ne kiem tra nao.
- Commit message chi neu "tach chuoi T_cut" o dong tieu de (than co P2) - nit.

## 2. Loi / rui ro (theo muc)
BLOCKER-van-hanh B1 (khong phai code): Vision UM daily 2026-11-23 CHUA co. HEAD luc ~09:40 +07: klines BTCUSDT/ETHUSDT 11-21=200, 11-22=200, 11-23=404; markPriceKlines tuong tu 11-23=404.
  Lich phat hanh 11-22: klines 08:55:52-08:57:55 UTC, markPrice 09:11:05-09:13:08 UTC (1000PEPE..ZRX) => 11-23 du kien ~16:00-16:20 +07 hom nay.
  Harness: fetch() 404 => None, KHONG fail-closed: liet ke 'missing', V2 ok=True (chi liet ke), klines/mkt/mark cua ca ngay UTC 11-23 (11-23 07:00 -> T_cut) trong => rig thieu nen + dieu kien thi truong DCA/BIG_DOWN sai => lech gia "khong giai thich"/INSUFFICIENT hang loat, luot E6 bi dot. Chay trong cua so dang phat hanh => thieu 1 phan symbol, im lang.
  => CHO; chi chay khi preflight Vision (muc 6) dat.
MAJOR M1 (fidelity, co tu truoc E6 - A1 cu khong neu): --buffer-day 2026-11-19 doc pull242/2026-11-19/run/gate_ratio_live.bin.gz. pull242_daily.sh ghi ro "anh chup buffer luc keo"; file 11-19 keo luc 2026-11-22 08:23:07 (ngay 11-19 keo lai, INCOMPLETE), cung kich thuoc voi file 11-21 keo 24 s sau. LIVE_GATE_ROLLING_DAYS=90, PCT=0.999950829 (env242). Buffer persist da cat dau theo cua so 90 ngay luc 11-22 => rig (chi lay ts < START) thieu ~2,9 ngay dau cua cua so 90 ngay o cac gio OW2 truoc ~11-22 08:00 => q (phan vi 0,99995 - rat nhay voi vai gia tri cuc tri) co the khac live => lech gate (L-E/L-N) gia, ghi la KHONG GIAI THICH => FAIL gia. Khong kiem duoc muc do neu khong doc buffer OW2 (cam).
  De xuat (MASTER quyet TRUOC luot #2): (a) errata E6b: seed = pull242/2026-11-18/run (anh chup 2026-11-19 08:23, 68' truoc START) + ban ghi [08:23, 09:31) cua anh 11-19 => trung trang thai live tai START; can sua rlive_fixture/prep + A1 delta; hoac (b) giu nguyen, ghi vao errata la gioi han da biet TRUOC khi chay (moi lech gate gan nguong q trong 11-19..11-22 phai qua A1 phan xu). Dev1105 co cung tinh chat (anh 25 h sau START) nen dev khong bao ve diem nay.
MAJOR M2 (thu tuc, co tu truoc): exit 14 cua run_rlive.sh dong 88-89 la NHANH CHET. rlive_gates.py dong 119-121: V10a co 'ok' => nam trong g['ok'] => V10a truot => GRC=1 => dong 86 exit 13 ("sua dau vao bang errata"), khong bao gio toi exit 14 / khong chep V10*.json ve a/. Trai ERRATA5 B(ii).
  De xuat KHONG doi code luc nay: errata E6 ghi ro "exit 13 ma gates.json chi V10a ok=false => ap thu tuc ERRATA5 B(ii) (A1 phan xu tu $OUT/V10_diag.json trong /dev/shm), tinh rieng". Neu sua code: rlive_gates.py dong 121 loai V10a khoi g['ok'] (1 dong) => can A1 delta.
MINOR m1: errata D "exit 2/8/9/11/12/15" => phan biet: exit 2/8 va exit 9 (stub, dong 14-15) xay ra TRUOC dong ghi khoa (khong tieu luot); chi loi SAU khi dong "errata=E6" da ghi moi tinh la luot #2 hong. Them exit 13 do loi ky thuat (lane khong chay: flock -w 3600 het han, java crash => thieu legs.csv => rlive_gates traceback => exit 13).
MINOR m2: errata E "khong co loi plumbing nao khac" - sua thanh liet ke M1, M2, B1.
MINOR m3: errata nen them dieu kien tien quyet: Vision 11-23 (klines + markPriceKlines) da phat hanh day du (preflight muc 6); log luot #2 la file MOI (khong ghi de rlive_1124_run.log da ghi sha).
MINOR m4: disk / con 15 577 MB vs nguong 15 300 (bien ~270 MB) - exit 8 xay ra truoc khoa (vo hai) nhung gay tre.
MINOR m5: watcher parity watch_daily_v12.sh (pid 936196) moi 30' chay run_day.sh qua oracle_heavy.lock; ngay khi Vision 11-23 len no se chay run_day 11-23 => trung gio voi R-LIVE. Lane java dung flock -w 3600: neu lock bi giu > 1 h => lane khong chay => exit 13. Chay R-LIVE SAU khi watcher da cham xong 11-23 (log 'DAY 2026-11-23 verdict') hoac khi lock ranh.

## 3. Official khac dev1105 (moi diem = nghi pham)
| Diem | Dev | Official | Ket luan |
| TCUT/TDAY/DAYS | hardcode | tcut() + assert | AN TOAN (P1 sua, tu kiem) |
| khoa + E2E_ERRATA | khong | dong 28-31 | AN TOAN: lock co "errata= " => grep "errata=E6 " khong khop; dong moi co dau cach sau E6 |
| build_wt.sh | khong | co (flock rieng) | AN TOAN (luot #1 RC=0); CAM boc flock ngoai |
| rlive_fixture.py (Vision fetch) | khong chay | chay | URL dung mau (HEAD 200 voi 11-22); 404 => missing khong fail-closed => B1 |
| prep_fixture qua rlive_fixture | fx1105 co san | chay moi | exinfo P2 sua; buffer-day 11-19 => M1; SIM_CFG ton tai; VIS override dung global; klines khong loc thoi gian nhung VDAYS 11-19..11-23 UTC nam trong [START-1d, END) => V3 qua |
| mark.csv.gz + --mark | khong | co | rd() doc gz; cot symbol,t,o,h,l,c khop Bars | 
| sel/submit cid parse | V2 da chay dev | rlive_fixture dong 89 giong V2 dong 55 | AN TOAN (cid c3-SYM-barMin-leg) |
| lane L0 FAKE cap1000 flags on | R-OLD DRY off | L0, L0-DRY, L-10K | V5/V8 truot o dev do flags off (banner LIVE-SIZING/DCA-GRID); V8_test flags on PASS, C0b PASS - chua chay tren OW2 |
| L0-DRY score khong --follow/--v10, conclude --score-dry | khong | co | doc ma: argparse khop, v10b checked=False; chua tung chay that |
| V10a truot | in ra | exit 13 (khong phai 14) | M2 |
| E2E_OFFICIAL=1 | khong | co | chi mo khoa fixture != dev o run_lane_stub |
Ton tai: pull242 11-19..11-23 sel_dump 119/132/132/132/132, full.log@*.gz 3/1/1/1/1, run/gate_ratio_live.bin.gz du; 11-19 INCOMPLETE (khong COMPLETE) - tcut khong can 11-19; 11-23 COMPLETE (08:23) => T_cut 2026-11-24 07:00. C0B.json, banner V8, env242, overrides, grr_lib, SIM_CFG, stub manifest ton tai. /dev/shm con 8,6 GB.
test_score.py: 41/41 OK.

## 4. Errata ERRATA6_PROPOSED.md
Dung: thoi gian 09:02:35-09:02:51, EXIT 11; sha log b59141db...53d6 (tu sha256sum khop); dong khoa khop nguyen van; sha khoa 3956d04f...f009 khop (truoc luot #2); output rong khop (0 file); diff trong errata == git diff that (cmp byte-identical). Khong cau nao noi nguong/doi pham vi. E6 hop co che dong 29-31.
Can sua: m1, m2, m3, M2 (cau thu tuc exit 13-chi-V10a), M1 (quyet dinh MASTER ghi vao errata), them HEAD A1 duyet = file nay.

## 5. Y kien 4 diem DEV
(i) Dong y rui ro; xu ly bang preflight sha256 EXINFO == dcfa03c7... trong cau lenh (muc 6), khong can doi code. rlive_fixture moi da assert fx/exinfo == sha EXINFO goc (khong so voi hang).
(ii) Dong y MASTER: KHONG doi thu tu (giu diff toi thieu, khoa-truoc la thiet ke "moi lan thu deu tinh"); bu bang preflight chay tcut() + assert NGOAI script truoc khi goi (muc 6).
(iii) Dat E2E_OFFICIAL_LOCK=$HOME/claude_master/w3/add24/a/OFFICIAL_ADD24_RLIVE.lock: chi la metadata (ReplayMain res + env_used.sh), khong anh huong logic - nen dat.
(iv) Xem B1: CHO Vision.

## 6. Cau lenh luot #2 (DEV KHONG dua cau lenh nguyen van; day la ban A1 da kiem tung bien). KHONG boc flock. Chay sau khi errata E6 commit + Vision dat.
```
W=$HOME/claude_master/w3/add24_wt; A=$HOME/claude_master/w3/add24/a; EX=$HOME/claude_master/w3/add24/exinfo/c3live_exchangeInfo_242_20261122_195538.json; L=$HOME/claude_master/v12/rlive_1124_run2.log
[ "$(git -C $W rev-parse HEAD)" = 274f55ebfb0c1dbe7e9d073fe398eb6d6831ad80 ] && [ -z "$(git -C $W status --porcelain --untracked-files=no)" ] \
 && [ "$(sha256sum < $EX | cut -c1-64)" = dcfa03c72c38a658e7de7df812e876bbca903f9e0dfd81ab02b1aeb61f3a1684 ] && [ -f $HOME/claude_master/pull242/2026-11-23/COMPLETE ] \
 && ! grep -q 'errata=E6 ' $A/OFFICIAL_ADD24_RLIVE.lock && [ ! -e $L ] && flock -n $HOME/claude_master/locks/oracle_heavy.lock true \
 && [ "$(python3 -c "import sys; sys.path.insert(0,'$W/tools/add24/rlive'); import rlive_fixture as F; print('|'.join(F.tcut()))")" = '2026-11-24 07:00|2026-11-23' ] \
 && python3 - "$EX" <<'PY' || { echo PREFLIGHT_FAIL; exit 1; }
import json, sys, urllib.request
B = 'https://data.binance.vision/data/futures/um/daily'
ex = json.load(open(sys.argv[1]))
syms = sorted(x['symbol'] for x in ex['symbols'] if x.get('contractType') == 'PERPETUAL' and x.get('quoteAsset') == 'USDT' and x.get('status') == 'TRADING')
chk = ['BTCUSDT'] + syms[-5:]
def code(u):
    try:
        return urllib.request.urlopen(urllib.request.Request(u, method='HEAD'), timeout=30).status
    except urllib.error.HTTPError as e:
        return e.code
bad = [(k, s) for k in ('klines', 'markPriceKlines') for s in chk if code('%s/%s/%s/1m/%s-1m-2026-11-23.zip' % (B, k, s, s)) != 200]
print('VISION_1123_BAD', bad); sys.exit(1 if bad else 0)
PY
nohup env ADD24_P1_APPROVED=e451154e A1_APPROVED=274f55ebfb0c1dbe7e9d073fe398eb6d6831ad80 E2E_ERRATA=E6 E2E_OFFICIAL_LOCK=$A/OFFICIAL_ADD24_RLIVE.lock EXINFO=$EX \
  bash -c 'bash "$0" official; echo "EXIT_CODE=$? END $(date -Is)"' $W/tools/add24/rlive/run_rlive.sh > $L 2>&1 &
```
Ghi chu: chi kiem 6 symbol cuoi + BTC vi Vision phat hanh theo thu tu chu cai (1000PEPE -> ZRX); nen doi them >= 15' sau khi ZRX/ZK markPrice 200. Kiem df / >= 15300 MB. Khong ghi de rlive_1124_run.log.

## 7. Phan KHONG bao dam duoc neu khong doc OW2
Parse log OW2 that (ti le khop quy tac, V4/V4b), so luong/ten symbol tai Vision, prep tren sel_dump OW2 (11-19 thieu phut), 4 lane java tren fixture OW2 (RAM -Xmx3g, thoi gian, V5 banner flags on, V6 du phut), v10_buffer voi LIVEBUF 11-23, rlive_score --mark / L0-DRY, conclude --score-dry (chua tung chay that), anh huong M1.
Uoc luong A1: xac suat luot #2 dung vi loi ky thuat/van hanh SAU khoa (khong tinh "V-gate truot that"): ~15-20 % neu tuan thu preflight + cho Vision + tranh watcher; > 50 % neu chay ngay bay gio (Vision 404 => fixture hong im lang). Them ~10-25 % kha nang V10a/V-gate truot hoac FAIL gia do M1 (khong phai plumbing, khong uoc luong chat duoc).

# DELTA VONG 2 - 274f55eb..2671cb769b8bf93cb6096dd2b469533733b4b689 (A1, 2026-11-24 ~10:00-10:40 +07)
VERDICT: KHONG DUYET 2671cb76 (FAIL) - 1 MAJOR do chinh delta gay ra (U1, symbol unicode), sua ~5 dong roi A1 duyet lai delta nho. Phan con lai cua delta DAT.

## M1 - PHAN XU: RUT LAI
- Tu kiem byte (cmp tren zcat, khong in gia tri): 11-18->11-19, 11-20->21, 21->22, 22->23, 11-19->11-23: anh truoc la TIEN TO byte cua anh sau; 11-19->11-20 khong (11-19 chup 11-22, muon hon 11-20) - dung voi append-only theo thoi diem keo.
- buf_check pre that (fx=anh 11-19, live=anh 11-23, START 11-19 09:31): same_n_pre, same_sha_pre, no_bad_chunk, monotone, no_wallclock_trim deu true (rc 0). Doi chung anh 11-18: truot (rc 3) - cong co phan biet.
- min_ts < 2026-10-02 va > now-90d (chi in boolean).
- Doc code: GateRatioPersist append-only; LiveGateRollingRatio.loadPersistedAndSeed chi viet lai khi seed (persist < 7 ngay) / chunk hong; CrashDayRig:255-275 nap ts < START -> E2eGateSupport.startProduction -> writeFresh + LiveGateRollingRatio.init() THAT. Gia dinh "persist bi cat dau 90 ngay" cua A1 vong 1 SAI => M1 rut lai.
- Buffer chua du 90 ngay (~49-54 ngay): computeQ cat [h-90d) khong cat gi, lay het; WARMUP 7 ngay tu firstTs (10-01) da qua; rig va live chay CUNG ham jar tren CUNG tap ban ghi => cung hanh vi.
- init() cat theo dong ho that (now-90d = ~08-26 < 10-01): hom nay vo hai; cong no_wallclock_trim (min_ts >= now-89d) bat neu chay sau ~12-29. Rui ro con lai (khong thuoc M1): live restart trong OW2 lam mat ban ghi chua flush => V10a, da co cong.

## U1 (MAJOR, do delta B1(iii)) - 5 symbol khong ASCII
- 5 symbol PERPETUAL USDT TRADING ten chu Han (onboard 2025-10-20 .. 2026-09-06). Vision 11-22: ca 522 symbol x 2 loai = 200 (gom 5 symbol nay, URL ma hoa %).
- Production KHONG BAO GIO co du lieu cac symbol nay: ingestor live TickerIngestor2AerospikeNew.java:134, :517, :557 chi nhan symbol khop ^[A-Z0-9]+$ (+USDT, - died) => symbol2LastTickers cua DetectEntrySignal2TradeNormal (vong market level :270-300) khong co chung; UNIVERSE_A1=1 => c3Idx null. SymbolUniverseLive buyable: NON_ASCII.
- Rig MarketReplay.at (dong ~105-115) duyet MOI symbol trong mkt.csv.gz, chi bo diedSymbol + a1Excluded (CrashDayRig:899-905: TradFi/INDEX/PREMARKET) - KHONG bo non-ASCII.
- => dua 5 symbol vao mkt.csv.gz lam universe market level cua rig != live (rateDown/rateUp ranking, n, n15, BIG_DOWN/isDcaAlt) => co the sinh lech DCA/BIG_DOWN "khong giai thich" => FAIL gia. Truoc delta (274f55eb) chung bi loai NGAU NHIEN (UnicodeEncodeError) - dung ve ket qua; fx1105 (parity Vision) cung khong co chung (0 dong). Java doc UTF-8 duoc (ReplayData:152,227 StandardCharsets.UTF_8) - khong phai van de.
- ERRATA1 N6 = dieu kien thi truong theo DUNG vong live => universe phai = universe ingest cua live. Cau "dung dac ta moi symbol PERPETUAL USDT TRADING" (errata B(iii), C) SAI.
- Sua de nghi (rlive_fixture.py ngay sau dong `allsym |= {...}` ~dong 119), giu quote (vo hai):
    import re   # = TickerIngestor2AerospikeNew:134/517/557
    noingest = sorted(s for s in allsym | cand if not (s.endswith('USDT') and re.fullmatch('[A-Z0-9]+', s)))
    allsym -= set(noingest); cand -= set(noingest)
  + ghi 'excluded_not_live_ingest': noingest vao manifest_ow2.json. Khong tai => khong vao miss => khong exit 12. Test: 5 symbol bi loai, mkt.csv.gz khong co dong non-ASCII.

## Delta khac
- (a) buf_check.py + exit 17: dung, fail-closed (thieu result.json => traceback rc 1 => exit 17), khong cham logic; pre DAT tren du lieu that; post: dev R-OLD/L0-FOLLOW buffer_init_records == buffer_after_load (1 168 714). Can `import snappy` (chi co o ~/.local, python3 -I KHONG thay) - run_rlive goi khong -I nen OK; MINOR: preflight them `python3 -c "import snappy"`.
- (b) Khoi TCUT/DAYS + HEAD Vision BTC (exit 16) nay TRUOC khoa - dung; truoc khoa con: exit 2 (P1/EXINFO/khoa), 8, 9 stub, 15, 16. Sau khoa: 9 build, 11, 12 (gom Vision thieu khong giai thich), 17, 13, 14. vision_explained chi dua EXINFO; chan nham kha nang thap (symbol trong sel_dump khong co trong EXINFO 956 symbol; file Vision bi Binance bo sot) nhung neu xay ra = exit 12 SAU khoa => giam bang preflight HEAD day du (duoi).
- (d) Khong doi nguong/nhan/logic cham/OW2; dev1105 chi them 2 file vao cp (2>/dev/null).

## run_rlive_e6.sh
Doc tung dong: du muc vong 1 (HEAD 40, nhanh, sach, EXINFO sha, stub md5, COMPLETE, tcut, khoa chua E6, errata da commit + nhac HEAD, log moi, lock ranh, khong run_day/cleanup, dia, RAM, Vision); khong flock long; E2E_OFFICIAL_LOCK dat; FAIL => exit 1 truoc nohup; khong `go` => exit 0. Chay preflight that 10:03: TRUOT dung 2 muc (ERRATA6 chua commit; Vision 11-23 404 ca 12 URL). Khong de lai file tam.
De xuat them (MINOR): (1) HEAD DAY DU 522 symbol ASCII-ingest x 2 loai x 5 ngay UTC 11-19..11-23 (5 220 request, -P 16: ~75 s; do that 1 044 request = 15 s) thay cho 6 symbol; (2) `python3 -c "import snappy"`; (3) /dev/shm/add24/vision khong ton tai (cache fetch duoc dung lai khong kiem); (4) watcher parity co the bat run_day ngay sau preflight - chap nhan (lane cho <= 3600 s) hoac chay sau khi watcher cham xong 11-23.

## ERRATA6_PROPOSED (vong 2)
Diff trong errata == git diff 3e6da6eb..2671cb76 (cmp byte-identical). Su kien A, D (truoc/sau khoa), M2 quy tac may kiem: DAT. Can sua:
- B(iii) dong 31-34 va C dong 58-59: thay "nay CO 5 symbol nay dung nhu dac ta" bang "5 symbol khong khop ^[A-Z0-9]+$ bi LOAI khoi universe rig (= ingest live TickerIngestor2AerospikeNew:134/517/557), liet ke trong manifest_ow2.json".
- M1 dong 35-50: giu ket luan KHONG THAT (A1 xac nhan doc lap).
- D dong 66-67: thay "HEAD BTCUSDT + 5 symbol ... doi them >= 15 phut" bang preflight HEAD day du (muc tren).
- Cap nhat HEAD moi sau khi sua U1.

## Vision (10:03 +07): klines + markPriceKlines BTCUSDT 2026-11-23 = 404. Du kien ~16:00-16:20 +07.

# DELTA VONG 3 - 2671cb76..a66109c12220de59ed8d5b065d33d0eb8875d5bf (A1, 2026-11-24 ~10:10-10:30 +07)
VERDICT: DUYET a66109c12220de59ed8d5b065d33d0eb8875d5bf (PASS). Errata duyet: ERRATA6_PROPOSED.md sha256 4d0ad85bfd8f9e5d2a39aa9d261ffc1d97e819960caa92ca5ac605eeaf348903.

1. Diff chi rlive_fixture.py (+13/-2): live_ingest_ok = upper + endswith USDT + fullmatch [A-Z0-9]+ (= TickerIngestor2AerospikeNew:134; :517 endsWithIgnoreCase sau upper - tuong duong; :557 chi regex - tap rong hon nhung :134/:517 quyet dinh tap ingest). Loc allsym|cand TRUOC fetch. EXINFO: 522 -> 517, loai dung 5 symbol non-ASCII, 0 symbol ASCII bi loai; manifest ghi excluded_not_live_ingest. diedSymbol de rig tu loai (MarketReplay:107) - dung. Worktree sach.
2. run_rlive_e6.sh: doc het; danh sach HEAD = TRADING PERPETUAL USDT loc ingest + BTC, 2 loai, udays tu tcut() (= superset cua fixture tru symbol chi co trong sel_dump); non-200 qua vision_explained giong fixture; FAIL => exit 1 truoc nohup; go: kiem lai lock + log; khong flock long; E2E_OFFICIAL_LOCK dat. Chay that 10:2x (37 s): TRUOT dung 2 muc - ERRATA6 chua commit; Vision 1034 non-200 = 517 x 2 tat ca ngay 2026-11-23, 0 o 11-19..11-22. Canh bao watcher hien dung.
3. Errata v3: diff trong errata == git diff 3e6da6eb..a66109c1 (cmp byte-identical, 267 dong). B(iii)/(iv), C, D, E-M1, HEAD da dung yeu cau. Khong cau nao noi nguong. Nit: dong 5-6 "HEAD moi" lap - khong can sua.
4. Khac biet universe co tu truoc E6:
 (a) isQuarantined thieu o rig: log 11-18..11-23 co 0 dong "bi CACH LY", 0 "MAPPER-DUP", 0 "MAPPER-CAP" (chi dem marker) => khong co symbol cach ly trong OW2 => KHONG kich hoat. Chua co trong bang K (co ghi o SPEC MarketReplay). De nghi: ghi vao bao cao ket qua 1 dong "kiem: 0 dong CACH LY trong OW2"; khong can sua.
 (b) 245 TRADIFI_PERPETUAL: UniverseA1Classifier.isTradFiContract (contractType chua TRADIFI) => live (DetectEntrySignal:252 UniverseA1Filter.filter) va rig (a1Excluded) deu loai; sel_dump dev 11-10/12/14: 0 symbol TradFi. KHONG anh huong. Chay nhu hien tai.
 (c) 137 SETTLING + 1 PENDING: EXINFO cho 0 symbol non-TRADING co deliveryDate trong [START-1d, T_cut], 0 symbol onboard trong OW2; GAIBUSDT PENDING (khong giao dich). => khong symbol nao co nen thuc trong OW2 ma fixture bo sot => KHONG kich hoat. Chay nhu hien tai.
5. Symbol chi co trong sel_dump: theo (c) moi symbol co the vao sel_dump trong OW2 deu TRADING trong EXINFO 11-22 (dev: sel 11-10/12/14 0 symbol ngoai tap TRADING) => xac suat exit 12 vi ly do nay < 1 %. Khong can doc sel_dump truoc luot.
Dieu kien luot #2: commit errata sha 4d0ad85b...; Vision 11-23 len (10:2x: BTCUSDT klines/markPrice = 404; du kien ~16:00-16:20 +07); preflight DAT tron (5170 HEAD); chay sau khi watcher parity cham xong 11-23. Uoc luong hong ky thuat sau khoa: ~6-10 %.
