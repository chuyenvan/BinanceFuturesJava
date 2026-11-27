# PARITY_DIAG - parity NEN f2b-nen-a1 / f2b-nen-s7 "error" (2026-11-27)
Chi doc. Khong push, khong sua driver/dataset/firewall.

## Lay log
- `kaggle kernels output` / KaggleApi.kernels_output (client 1.6.17) tai TOAN BO file output vao RAM (requests.get(url).content) TRUOC
  khi ghi log; output co a3_ds/funding.bin 4.4 GB (kernel chet truoc buoc don A3_CLEAN) => lenh treo / timeout => "thu muc rong".
  Da dung tien trinh tai (da keo ~1.9 GB vao RAM).
- Lay log dung cach: KaggleApi.kernel_output_with_http_info("chuyendinh","sim-<tag>") -> truong "log" (khong tai file).
  Log luu: ~/claude_master/w3/levz_kg/pdiag/f2b-nen-a1.log, f2b-nen-s7.log. kernels_status: failureMessage rong.
- File output A1: a3_ds/funding.bin, a3_ds/manifest.txt, a3_funding.json, a3_helpers/s3_funding.py, config.properties (S7 them wfo_ds_pred/manifest.txt).

## Buoc chet (ca 2 seed giong nhau)
- Bundle rut gon OK: jar sim-jar-tsx, A3 bins sha OK, s3_funding OK md5=50c4bc8d9a8238e89c0a99467adac100 (TRUNG r1-a3-a1 2026-11-10),
  "A3 dataset ok", S7 pred_ds md5 b737fb6d OK, ticker=1826, NOWRITE242 OK.
- Roi: WARNING PREFLIGHT mapper host 161.118.212.3:3222 lan 1/2/3 loi: timed out
  ERROR SYMBOL_MAPPER_PREFLIGHT_FAIL: khong toi duoc Aerospike Oracle 161.118.212.3:3222 -> DUNG TRUOC sim (khong chay sim, khong ghi gi).
  (A1 t=127.7 s, S7 t=138.8 s; S7 "chet muon" chi do hang doi / thoi gian bat dau.)

## Nguyen nhan (CHAC)
iptables tren Oracle (doc bang sudo -n iptables -S INPUT): bo quy tac comment "AS3222_CLOSE" - chi ACCEPT 3222 tu 127/8, 10.0.0.0/24,
172.16/12, 103.157.218.242/32, 161.118.212.3/32 roi DROP moi nguon khac. /etc/iptables/rules.v4 sua 2026-11-11 16:39
(backup rules.v4.bak_AS3222_CLOSE_20261111_163936) - SAU run r1-a3 thanh cong 2026-11-10. Kernel Kaggle (IP dong) bi DROP => timeout.
Listener 0.0.0.0:3222 van song; TCP tu chinh Oracle (127.0.0.1, IP public) OK.
Gia thuyet bi loai: (a) funding.bin bundle - khong can (A3 tao lai, md5 trung); (b) dataset_sources: 12/12 ton tai, du file
(ticker 1826, r1-a3-bins 16, moc21 2, jar+prof, gate-abl-seed7 pred.bin); (c) README / thieu sim.jar - kernel qua cac glob;
(d) config.properties - qua NOWRITE242 binh thuong; (e) Kaggle OOM/dia - khong, chet o preflight mang.
Smoke 2026-11-26 chet som hon (MISSING manifest) nen chua lo loi nay.

## De xuat (MASTER / owner quyet; dung cham bao mat AS3222_CLOSE)
1. Mo tam 3222 cho Kaggle trong thoi gian chay luoi (Kaggle khong co dai IP co dinh => thuc te la bo / noi DROP) roi dong lai.
   Day la thay doi bao mat tren may nghien cuu do owner quyet; doc ly do dong 11-11 truoc.
2. Hoac doi kernel khong can mapper qua mang (vd dong goi symbol mapper snapshot vao dataset) - can sua code kaggle_sim/Java, ngoai pham vi.
Khong can them lai funding.bin.

## Bo sung: loi DA BIET + loi giai DA KIEM CHUNG (docs/result/ho5_a3_2026/HO5_A3_2026_LOG.md)
- Dong 29-33: cung loi SYMBOL_MAPPER_PREFLIGHT_FAIL tu 2026-11-1x; luat AS3222_CLOSE do owner ap 11-11 (close_aerospike_3222.sh),
  script da canh bao kernel Kaggle mat mapper. Canh bao output co funding.bin 4.4 GB -> khong dung ks.fetch/kernels_output.
- Luot 2-3 (11-19): mapper snapshot (ds chuyendinh/ho5-a3-mapper-snap) + funding_data snapshot (ds chuyendinh/ho5-a3-funding-snap v2)
  + overlay classpath (jar sim cc0f9d11 KHONG doi), kernel gen ~/claude_master/w3/ho5/ho5_k3.py (import r1_a3_driver + patch).
  Kernel sim-ho5-a3-rep3-s123 tai lap r1-a3-s123 TRUNG BYTE (md5 printDone a11ce5f9, equity 144 003, funding -2 490,7257), 0 truy cap Aerospike.
  Chi mapper (khong funding snapshot) -> lech -3,42 % (funding = 0) => PHAI co ca hai snapshot.
- 3 dataset ho5-a3-mapper-snap / ho5-a3-funding-snap / ho5-a3-code: VAN TON TAI (kiem 2026-11-27).
## De xuat chot
A (khuyen): f2b_driver ap patch cua ho5_k3 (mapper + funding snapshot overlay) vao run.py NEN/luoi; them 2 dataset vao dataset_sources;
  check_f2b mo rong whitelist dataset/patch; A1 audit lai; parity NEN (md5 printDone r1-a3) la cong xac nhan. Khong mo firewall.
  Funding snapshot phu toi 2026-07-07 - du cho DEV <= 2025-12-31.
B: owner tam mo 3222 cho Kaggle (bo/doi luat DROP AS3222_CLOSE) trong thoi gian chay roi dong lai - doi chinh sach bao mat, owner quyet.
Khong can them lai funding.bin vao bundle.
