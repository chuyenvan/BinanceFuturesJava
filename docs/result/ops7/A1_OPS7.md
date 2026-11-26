# A1_OPS7 - audit doc lap commit fd0a2718 (v1.2/ops-micro7, tu 082c10f5) - 2026-11-26
VERDICT: PASS-WITH-MINOR - DUOC dung tao cong G-PILOT hom nay (dieu kien muc 7). Khong co loi bat buoc.

## 1. Pham vi diff
- git diff 082c10f5..fd0a2718: DUNG 3 file (GOLIVE_MANIFEST.md5 1 dong md5 make_gate_pilot; golive_make_gate_pilot.sh: chu thich + dong NO=$(s242 ...) + dong echo + dong so_lenh_that_luc_tao; test_ops6.sh +16 = 4 ca #148-151).
- md5 tung file ops/c3live/* ops7 vs ops6: CHI khac GOLIVE_MANIFEST.md5 + golive_make_gate_pilot.sh. golive_lib.sh 5d0febd2..., golive_monitor.sh 20b92870... giong ops6 VA giong ban pin cron deploy/pinned/golive_monitor_d60882c1b872. pilot_on, wrapper c3_autodrain_prestart.sh, deadman, first_trade_check giong het.
- sha256 golive_make_gate_pilot.sh = fcc2e8dc...545f4 (khop DEV). Worktree ops6/ops7 sach.

## 2. Dinh nghia dem vs code jar (c3_hotfix, src khong doi tu 4fdda6f8)
- (a) c3- MARKET REST: C3LiveClient.newMarketOrder -> auditOk status=getRawStatus (FILLED khi khop, RESULT resp). DUNG.
- (b) user stream: FillAccounting:150-154 moi u.isTrade() (moi cid, ke ca khop mot phan) => status=FILL. DUNG.
- (c) c3s- = algo STOP_MARKET (/fapi/v1/algoOrder): REST chi NEW (new_stop) / CANCELED (cancel_stop) / ERROR; ALGO_UPDATE chi log [C3-LIVE-FILL], KHONG [C3-LIVE-ORDER] => khop chi de lai FILL. DUNG.
- (d) c3x- = MARKET reduceOnly qua newMarketOrder => REST FILLED (+ FILL stream). Ca hai deu duoc dem.
- OrderAuditLog.sanitize: khoang trang / '=' / ky tu dieu khien trong GIA TRI -> '_' => err/reason KHONG the tao token 'status=..' / 'cid=..' gia. Dem theo truong (awk), uniq cid, status so khop CHINH XAC (FILLING / PARTIALLY_FILLED / FILL_ khong tinh).
- N_VAO giu nguyen nghia cu (chi c3- FILLED; c3- FILL khong cong vao). Khop mot phan roi huy cua c3s- = co tinh: hop ly voi muc dich cong (duong thoat da chay tren san that).

## 3. An toan shell
- Escape: \$i, \", \\n dung; chuong trinh awk trong nhay don, khong chua nhay don; $A/$MS mo rong cuc bo nhu ban cu. RC_GREP=${PIPESTATUS[0]} van la grep (124 = timeout); END_NO van in sau cung. awk loi => khong co N_* => gl_gx_check "khong_co_so_dem_that" => TU CHOI (an toan).
- Chi doc tren 242 (grep/awk/stat/echo, khong ghi).
- Harness don vi: trich NGUYEN dong lenh tu script, chay bash -c voi mawk / gawk 5.1 / busybox awk: 15 nhom ca dong nhat 3 awk (tru CRLF: busybox dem, mawk/gawk khong - log Linux khong CRLF). gawk in canh bao 'Invalid multibyte' ra stderr khi byte khong hop le - khong lot vao $NO, so dem van dung; cid bi checkCid gioi han ASCII.
- Dong 300 KB, log rong (N=0/0 RC_GREP=1 END_NO), full.log.1 cu/moi: dung.

## 4. Ca pha (sandbox /tmp, khong 242): 15/15 dung ky vong
c1 FILL x3 cung cid=1; c2 c3s- NEW/CANCELED/ERROR=0; c3 c3x- FILLED=1; c4 c3- FILL/PARTIALLY_FILLED khong vao, khong thoat; c5 cid ngoai (autoclose-, web_, c3sx-, C3S-, xc3s-)=0; c6 FILLING/FILL_/PARTIALLY_FILLED/EXPIRED=0; c7 non-ASCII/byte rac=dem dung; c8 tag [LIVE-DRY]=0; c9 tiem reason (chi dang khong the co do sanitize) - xem m1; c10 'cid=' o prefix log -> lay cid that; c11 CRLF; c12 2 dong dinh nhau (lay truong cuoi); c13 rong; c14 dong dai; c15 xoay log.
Qua bo test (GL_TEST=1): n khai != dem => TU CHOI (#149), n=0 => TU CHOI (m-7 #8x), log chi c3- => thoat=0 TU CHOI (#150). So doi giua DRY va that: Q4_OWNER yeu cau n == dem => that TU CHOI (an toan, chay lai).

## 5. Bo test
- ops7 (fd0a2718): 177/181 FAIL #6 #7 #133 #166 (3 job song song). #166 (R2-m4, pilot_on - file GIONG HET ops6) = flake do tai: lock python giu 40 s het truoc khi kiem; ca nay PASS o mutant (cung pilot_on) va o DEV. Chay lai don le: xem phu luc.
- ops6 (082c10f5): 174/177 FAIL #6 #7 #133.
- #6/#7/#133 = do NGAY: make_gate dong 91-94 MD=(now-MS)/86400 >= 7 => M7L=DU tu 2026-11-26 09:31 +07; #6 ky vong TU CHOI micro<7 (nay chap nhan), #7 ky vong micro7=MIEN_OWNER (nay DU), #133 van TU CHOI rc1 (ly do MIEN_*) nhung thieu chuoi 'ke tu 2026-11-19'. Khong che loi that.
- Mutant (dong dem cu + manifest cap nhat, commit trong clone): #148 #149 FAIL (bat mutant), #150 #151 PASS (hoi quy - hanh vi khong doi). Tong 176/181.

## 6. Pin + chuoi hom nay
- golive_make_gate_pilot.sh / golive_pilot_on.sh / install_* deu kiem m1: HEAD worktree phai co trong /home/ubuntu/claude_master/deploy/gates/A1_APPROVED_OPS.commit + khong sua chua commit; roi gl_manifest_check (GOLIVE_MANIFEST.md5 canh lib).
- Neu KHONG them fd0a2718: make_gate_pilot ops7 => 'TU CHOI [m1]' exit 1 (chuoi dung o buoc MASTER); pilot_on ops7 cung bi chan; pilot_on ops6 khong anh huong.
- gl_gate_pilot (lib giong het ops6/ops7) KHONG kiem ops_head, chi 'by=MASTER golive_make_gate_pilot.sh'; parse 'so_lenh_that_luc_tao=vao_FILLED:N thoat_FILLED:N' - dinh dang giu nguyen => cong ops7 duoc pilot_on ops6 lan ops7 chap nhan.
- Cron monitor tro deploy/pinned/golive_monitor_d60882c1b872 = md5 monitor+lib cua ops7 => KHONG can doi. first_trade cron tro c3_ops6 (file giong het) - khong can doi.
Buoc:
 1) MASTER: cp -p A1_APPROVED_OPS.commit{,.bak_<ts>}; them dong: 'fd0a27185f3c6d6beb0c60884b6ad5d4694ab928  # v1.2/ops-micro7 fd0a2718 A1 PASS-WITH-MINOR 2026-11-26 (v12/A1_OPS7.md)'. KHONG them dong vao A1_APPROVED_MONITOR.md5 (d60882c1b872 da co).
 2) MASTER: DRY=1 bash ~/claude_master/w3/c3_ops7/ops/c3live/golive_make_gate_pilot.sh (tham so day du, KHONG GL_TEST) -> doc 'vao=.. thoat=..'; dat G_EXIT n = DUNG so thoat (Q4_OWNER) ; chay lai KHONG DRY ngay sau. Neu bot khop them stop giua 2 lan => TU CHOI mismatch => DRY lai.
 3) Owner: DRY=1 bash ~/claude_master/w3/c3_ops7/ops/c3live/golive_pilot_on.sh roi ban that. Khuyen ops7 (cung HEAD da ghi trong gate ops_head, 1 worktree duoc duyet); ops6 la phuong an du phong tuong duong (byte-giong).
 4) golive_monitor: giu cron hien tai.

## 7. MINOR / dieu kien / rui ro
- m1: awk lay token cid=/status= CUOI dong; an toan vi sanitize, chi sai neu 2 dong log bi dinh (logback khong lam). Khong can sua.
- m2 (co tu truoc): N_VAO chi tinh REST FILLED; lenh vao REST tra NEW/PARTIALLY roi khop qua stream se khong duoc tinh (dem thieu => G_EXEC Q4_OWNER phai khop so thap hon). Khong doi trong ops7.
- m3: ca test dung 'reason=stream_X=FILLED' (jar khong the sinh '='); vo hai.
- m4: nhan gate 'thoat_FILLED:' nay gom FILL - giu de tuong thich parser lib; doc gate can biet.
- m5: test #6/#7/#133 phu thuoc ngay - sua sau (dung moc tuong doi), khong chan hom nay.
- Rui ro owner: so N_THOAT that tren 242 chua kiem duoc (cam ssh 242), ky vong <= 24; uniq cid gia dinh moi lan dat stop co cid rieng (chua kiem cach sinh cid c3s-). Log xoay sau moc micro co the lam so giam -> chi anh huong viec khop n.
## Phu luc
- Sandbox: /tmp/a1o7.umROZ1 (r6 r7 rm clone; t7.out t6.out tm.out; u/ = harness don vi). Chay lai ops7 DON LE: /tmp/a1o7.umROZ1/t7b.out (dang chay luc ban giao; ky vong 'TEST FAIL #6 #7 #133 178/181'). Xong thi xoa: rm -rf /tmp/a1o7.umROZ1
- cid (C3LiveCids): c3-/c3x-/c3s- <token>-<phut>-<seq|lan|leg> => moi lan dat stop 1 cid rieng; non-ASCII symbol => token hash => cid ASCII.
- Guard ssh that (guardbin) : khong co guard_blocked.log o ca 3 lan chay => khong ssh that.
