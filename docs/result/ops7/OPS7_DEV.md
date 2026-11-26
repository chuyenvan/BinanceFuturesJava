# OPS7_DEV - sua dem N_THOAT trong golive_make_gate_pilot.sh (2026-11-26)

- Nhanh v1.2/ops-micro7, worktree ~/claude_master/w3/c3_ops7, tu 082c10f518e8a81e90dad0057bd459521303732b (ops6, KHONG doi c3_ops6/c3_ops5). KHONG push.
- Commit ops7: fd0a27185f3c6d6beb0c60884b6ad5d4694ab928
- sha256 golive_make_gate_pilot.sh moi: fcc2e8dc0991146eede2b0c0df8f01a8a86d36e73a0db50af508f4d4592545f4 (md5 894ad8a7417cb1e3d104621b8bd40a3d)
- git diff --stat 082c10f5..HEAD: GOLIVE_MANIFEST.md5 2+- ; golive_make_gate_pilot.sh 13 (+8 -5) ; test/test_ops6.sh +16. Tong 3 file, +25 -6.

## 1. Can cu tu code jar (c3_hotfix @ 4fdda6f8, chi doc; HEAD 76134a52 khong doi src/main)
- OrderAuditLog.java: chi format/ghi; status = gia tri caller truyen.
- C3LiveClient.newMarketOrder :152-171 (lenh vao c3- VA lenh dong c3x-, newOrderRespType=RESULT) -> auditOk :627-631: status = rawStatus REST cua san
  (thuong FILLED; co the NEW/PARTIALLY_FILLED/EXPIRED). Loi -> auditErr :634-639 status=ERROR.
- C3LiveClient.newStopMarket :175-203 (stop algo c3s-, POST /fapi/v1/algoOrder) -> status = algoStatus (parseAlgo :657-666) = NEW luc dat.
  cancelStop :223-237 -> CANCELED. Loi -> ERROR.
- FillAccounting.onOrderUpdateLocked :135-156: MOI su kien user stream x=TRADE (UserStreamEvents.isTrade :89-91), MOI cid (c3- / c3x- / c3s-),
  MOI lan khop (ke ca khop mot phan) -> 1 dong status=FILL (:151-153), reason "stream X=<FILLED|PARTIALLY_FILLED> ...".
- FillAccounting.onAlgoUpdate :292-294: ALGO_UPDATE (TRIGGERED/FINISHED...) CHI LOG.info [C3-LIVE-FILL], KHONG ghi [C3-LIVE-ORDER].
  => TRIGGERED / FINISHED / PARTIALLY_FILLED cua c3s- KHONG BAO GIO xuat hien trong [C3-LIVE-ORDER]; c3s- da khop that CHI co dong status=FILL.
- Khac: C3LiveEntry :273 status=SKIP (cid=-), C3MergedGuard :536 MERGED*/LOST_FOREIGN (cid=-) -> khong co cid c3, khong anh huong.
- Ket luan: thoat that = cid c3x-/c3s- co status=FILLED (REST c3x-) HOAC status=FILL (stream), uniq cid. Ban ops6 grep 'status=FILLED' => bo sot
  moi c3s- khop (TRAILING_STOP) => N_THOAT=0 (log 093027: vao=24 thoat=0).
- N_VAO GIU NGUYEN (c3- status=FILLED). Ly do: moi lenh c3- di qua REST auditOk; thong ke that chi co c3- FILLED 24 + c3- FILL 34 (khong co c3- NEW/
  PARTIALLY/ERROR) => 24 lenh vao deu FILLED o REST; dong FILL cua c3- la cac lan khop (nhieu trade/lenh) cua chinh cac cid do (suy luan, khong dem uniq cid tren 242).

## 2. Thay doi (golive_make_gate_pilot.sh)
- Dong dem (117->120): `| grep -a 'status=FILLED' | grep -aoE 'cid=c3[xs]?-[^ ]+' | sort -u | awk '/^cid=c3-/{e++} /^cid=c3[xs]-/{x++} END{...e, x}'`
  -> `| grep -a 'status=FILL' | awk '{tach cid=/status= theo truong} c3- && s=="FILLED" -> e[c]; c3[xs]- && (s=="FILLED"||s=="FILL") -> x[c]; END dem uniq'`.
  Giu nguyen: timeout 120 nice -n 19 $IO grep (test m-8), LOGS, RC_GREP=PIPESTATUS[0], END_NO.
- Dong in: "242 lenh that FILLED (log, uniq cid): vao=" -> "242 lenh that da khop: vao=c3- status=FILLED, thoat=c3x-/c3s- status=FILL|FILLED (log, uniq cid): vao="
  (giu duoi "FILLED (log, uniq cid): vao=" vi test m-8 parse).
- Gate: so_lenh_that_luc_tao=vao_FILLED:N thoat_FILLED:N GIU NHAN (gl_gate_pilot golive_lib.sh:428 parse dung nhan nay), chi them chu thich trong ngoac.
- Chu thich dau file dong 29-33.
- GOLIVE_MANIFEST.md5: dong golive_make_gate_pilot.sh 871f788a... -> 894ad8a7... (bat buoc: gl_manifest_check).
- KHONG doi: n>=1, n=DUNG so dem (Q4_OWNER), ref, MIEN_*, LEV_EV, han 48 h, body_sha256, logic khac.

## 3. Cac cho khac (khong sua)
- golive_lib.sh:428 (gl_gate_pilot) - CHI parse nhan vao_FILLED/thoat_FILLED tu gate, khong dem log => dung voi ops7.
- golive_lib.sh:871, :1138 AUDIT_C3 = moi dong [C3-LIVE-ORDER] tru SKIP -> khong phu thuoc FILL/FILLED. OK.
- golive_monitor.sh:94 FILL=$(cnt1h 'C3-LIVE-EXEC\] FILL') - tag [C3-LIVE-EXEC], chi in thong tin, khong chan. :103 chi bat status ERROR/REJECTED/EXPIRED. OK.
- golive_first_trade_check.sh, golive_pilot_down.sh, golive_pilot_on.sh: KHONG dem status=FILLED / [C3-LIVE-ORDER].
- canary/canary_report.sh:160 chi la nhan text. deploy_v12_dry*.sh / c3live_status.sh / canary_lib.sh dem tong dong [C3-LIVE-ORDER] (kiem 0 lenh that DRY) - khong lien quan.
- => Khong cho nao khac sai tuong tu, khong cho nao chan pilot_on/monitor hom nay. DE NGHI (khong lam): doi nhan gate thoat_FILLED -> thoat_FILL o dot sau (phai doi lib+test cung luc).

## 4. Pin
- pilot_on KHONG ghim ops_head/md5 make_gate_pilot: gl_gate_pilot khong doc dong by=...ops_head (chi kiem prefix 'by=MASTER golive_make_gate_pilot.sh').
  Gate do ops7 tao duoc pilot_on (ops7 hoac ops6) chap nhan neu cac truong khac dat.
- Pin DOI: (a) HEAD ops7 fd0a2718 phai duoc them vao deploy/gates/A1_APPROVED_OPS.commit (m1 cua MOI script golive_*) - A1/owner lam sau audit;
  (b) GOLIVE_MANIFEST.md5 dong make_gate_pilot (da cap nhat trong commit).
- Pin KHONG doi: golive_lib.sh 5d0febd2 (NJ_MD5 01cfbb4324fb4a10b615dc3c976ddc73, GL_AD_MD5 ddc97c2e3714c956ae2448d57a1940fc); md5(monitor+lib)[:12] d60882c1b872
  = ops6 (A1_APPROVED_MONITOR + thu muc PIN cron monitor khong doi); c3_autodrain_prestart.sh ddc97c2e (= boot guard wrapper 242, = GL_AD_MD5);
  c3_oracle_seen_242.sh f521c970, install_242_oracle_seen.sh 96c1fc3c, install_242_autodrain.sh 108064ff, golive_pilot_on.sh 8df22916 - deu khong doi.

## 5. Test (GL_TEST, 242 gia, tuan tu, tai fd0a2718)
- ops7 @ fd0a2718: test_ops6 178/181 (FAIL #6 #7 #133) | test_ops5 128/128 | test_swap_jar 36/36 | test_fake242 639/639 SKIP=1 (tong 640).
- 4 ca moi OPS7 (#148-#151) PASS: c3s- FILL 2 dong cung cid = 1, NEW/CANCELED/ERROR khong tinh, c3- chi FILL khong vao N_VAO (vao=3 thoat=4);
  G_EXIT n=2 != 4 => TU CHOI; log chi c3- => thoat=0 => TU CHOI; c3x- FILLED van tinh (thoat=1).
- BASELINE ops6 082c10f5 (clone --shared vao /tmp, chay HOM NAY sau fk): test_ops6 174/177 FAIL #6 #7 #133 - CUNG 3 ca.
  Nguyen nhan (theo test_ops6.sh:244-247, :614-615): 3 ca gia dinh moc micro THAT 2026-11-19 09:31 +07 chua du 7 ngay; tu 2026-11-26 09:31 +07 da du
  => ca du kien TU CHOI nay chap nhan. Phu thuoc NGAY, khong do ops7. (A1_OPS6_R3 truoc do: 177/177.)
- Thu cuc bo dong dem (bash -c, log mau 11 dong dung dinh dang jar): ops7 N_VAO=1 N_THOAT=2; ops6 N_VAO=1 N_THOAT=1 (bo sot c3s- FILL).

## 6. Lenh MASTER (chi doi OPS; sau khi A1 duyet va them HEAD vao A1_APPROVED_OPS.commit)
  OPS=~/claude_master/w3/c3_ops7/ops/c3live ; <cung bien nhu lan 093027> DRY=1 bash $OPS/golive_make_gate_pilot.sh
  G_EXIT phai la "Q4_OWNER n=<dung N_THOAT in ra> ref=<commit> ..." (Q4_OWNER: n = DUNG so dem).

## 7. A1 can soi
- Quoting cua awk trong chuoi s242 (\$i, \"\") - da thu bang bash cuc bo + test 242 gia; awk tren 242 (mawk/gawk) chua chay that.
- Lenh grep 'status=FILL' khop ca FILLED (chu y), awk so khop CHINH XAC.
- Ca thay doi G_EXIT: N_THOAT that luc tao co the TANG giua DRY va ghi that (bot dang chay) => Q4_OWNER n phai bang so luc ghi.
- 3 FAIL test_ops6 theo ngay (#6 #7 #133).

## 8. KHONG kiem duoc
- So N_THOAT that tren 242 (cam ssh 242): kyvong 1..24 (24 dong c3s- FILL; uniq cid <= 24; MASTER noi > 20 cum dong TRAILING_STOP) - suy luan.
- Hanh vi san: c3s- khop luon den qua ORDER_TRADE_UPDATE voi c = clientAlgoId (bang chung gian tiep: 24 dong c3s- FILL tren 242).
- Neu user stream mat su kien TRADE cua 1 stop, lenh do khong duoc dem (jar khong ghi [C3-LIVE-ORDER] cho ALGO_UPDATE).
