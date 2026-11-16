#!/usr/bin/env bash
# =============================================================================
# dry_prep_micro_restart.sh - [PREP-MICRO 16/11, NHAP cho prereg ADD23 - CHUA DUOC A1 DUYET] 1 lan restart v_t_m DRY gop 2 viec.
#   KHONG doi jar, KHONG doi conf/env.sh. Chi sua 2 file trang thai khi JVM DUNG:
#   (A) so giay c3 ($SHADOW_DIR/open_positions.csv): xoa dong rank=-1 co symbol thuoc run/legacy_symbols.csv (cum giay mo boi
#       LEGACY-DCA truoc co, AUDIT_LEGACY_DCA_1116 Q3/Q5). Moi dong bi xoa PHAI thuoc PURGE_SYMS (danh sach dong bang trong ADD23).
#       Giu header, #realized, moi cum rank>=0 (HANAUSDT, AIOUSDT du cung thuoc legacy_symbols). rank=-1 ngoai danh sach => TU CHOI.
#   (B) buffer gate p15 (run/gate_ratio_live.bin): bo ban ghi r co ts trong [EXCL_FROM, EXCL_TO) +07 (mac dinh 2026-10-30 03:40-04:10,
#       242 bi ban -1003, AUDIT_GOLIVE_1116_D D-02). Dung EXP_EXCL_N ban ghi (mac dinh 720), khac => TU CHOI.
#       Cach (242 KHONG co python): truoc stop, Oracle keo ban chep (chi doc), python3+snappy tinh B = cuoi chunk hoan chinh, md5(B byte
#       dau) va PREFIX' = cac ban ghi [0,B) da loc ghi 1 chunk GRR1 (nhu GateRatioPersist.writeFresh). Sau stop tren 242: md5(head -c B)
#       PHAI = md5 tien tinh (file append-only) roi file moi = PREFIX' + tail -c +B+1 (coreutils). Hau kiem: Oracle keo file moi, giai
#       ma doc lap: 0 chunk hong, 0 ban ghi trong cua so, so ban ghi = log "LIVE nap buffer: size=", q_t gio ke trong [Q_LO, Q_HI].
#   Owner chay tren ORACLE ($OPS = thu muc chua script nay = worktree A1 duyet (HEAD co trong deploy/gates/A1_APPROVED_OPS.commit),
#     vd ~/claude_master/fin1114/c3_ops/ops/c3live):
#     DRY=1 bash $OPS/dry_prep_micro_restart.sh   # CHI DOC 242 (ssh doc + scp VE Oracle), in ke hoach, KHONG ghi 242
#     bash $OPS/dry_prep_micro_restart.sh         # go YES (khung :10-:44, tranh 07/19h, 00:50-01:20, 12:50-13:20)
#   Thu tu: kiem truoc (chi doc) -> ke hoach so giay + buffer (Oracle) -> khung gio -> YES -> chep PREFIX' len 242 (file .prep_prefix_TS)
#     -> chup so giay cho harness (book_snap.sh, chi doc) -> PAUSE watchdog -> stop -> backup 2 file (.bak_prep_TS + .md5) -> sua 2 file
#     -> start -> hau kiem POST_ROUNDS x POST_WAIT_S -> Oracle kiem buffer moi -> DAT: go PAUSE, START_MS, smoke_start_ms gmicro_target.
#   Sua file loi sau stop => khoi phuc 2 file tu backup ngay, start lai (trang thai cu). Hau kiem TRUOT => ROLLBACK TU DONG: stop ->
#     2 file ve backup (kiem md5) -> start -> kiem adapter=DRY; rollback loi => dat run/KILL_SWITCH, KHAN exit 2.
#   Ma thoat: 0 XONG | 1 DUNG (khong doi gi) hoac da khoi phuc/rollback OK | 2 KHAN.
#   Ngay chay = XAM (ADD23). Rollback MUON (sau khi script da XONG) KHONG co trong ban nhap nay (backup .bak_prep_TS giu tren 242).
# Bien (test): nhu golive_lib.sh + SCP_242 RHOST SHADOW_DIR PURGE_SYMS EXCL_FROM EXCL_TO EXP_EXCL_N Q_LO Q_HI U_TOL PAPER_EQ PREP_PY
#   BOOK_SNAP_SH BOOK_DIR GMICRO_TARGET TG_SHA8 TARGET_TAG CALM_H FORCE_CALM
# =============================================================================
set -uo pipefail
# [WAVE1c m1] pin NGOAI repo, kiem TRUOC khi source lib (lib khong tu chung nhan): HEAD repo chua script = 1 commit A1/MASTER
#   duyet trong A1_APPROVED_OPS (deploy/gates/A1_APPROVED_OPS.commit, 1 dong/commit, script CHI DOC) + thu muc script KHONG co sua chua commit.
_OPS=$(cd "$(dirname "$0")" && pwd); _APO=${A1_APPROVED_OPS:-/home/ubuntu/claude_master/deploy/gates/A1_APPROVED_OPS.commit}; _PW=""
_HC=$(git -C "$_OPS" rev-parse --verify -q HEAD 2>/dev/null) || _PW="$_OPS khong phai repo git"
[ -n "$_PW" ] || { [ -f "$_APO" ] && grep -qE "^$_HC([[:space:]]|\$)" "$_APO"; } || _PW="HEAD $_HC CHUA duoc A1 duyet (khong co trong $_APO)"
[ -n "$_PW" ] || git -C "$_OPS" diff --quiet HEAD -- . 2>/dev/null || _PW="$_OPS co sua CHUA commit (git diff HEAD)"
[ -z "$_PW" ] || { echo "TU CHOI [m1]: $_PW - KHONG lam gi."; exit 1; }
. "$(cd "$(dirname "$0")" && pwd)/golive_lib.sh"
gl_manifest_check "$0" || exit 1
SCP_242=${SCP_242:-"scp -q -P 2222 -o BatchMode=yes -o ConnectTimeout=20 -i /home/ubuntu/.ssh/id_rsa_chuyennd"}
RHOST=${RHOST-root@103.157.218.242:}
SHADOW_DIR=${SHADOW_DIR:-/home/chuyennd/java/shadow_c3}
PURGE_SYMS=${PURGE_SYMS:-REUSDT,BREVUSDT,ZBTUSDT,VELVETUSDT,PEOPLEUSDT,SAHARAUSDT,ZORAUSDT,PRLUSDT,BANKUSDT,TRUMPUSDT,AVAAIUSDT,XPINUSDT,LABUSDT,TRUSTUSDT,1000RATSUSDT,YBUSDT,ETCUSDT,BOMEUSDT,MELANIAUSDT,YGGUSDT,BLUAIUSDT,HUSDT,GALAUSDT,BEATUSDT,TRIAUSDT,TOWNSUSDT,GPSUSDT,HEIUSDT,APTUSDT,MIRAUSDT,SNXUSDT,ROBOUSDT,FUSDT}
EXCL_FROM=${EXCL_FROM:-2026-10-30T03:40}   # +07, bao gom
EXCL_TO=${EXCL_TO:-2026-10-30T04:10}       # +07, khong bao gom
EXP_EXCL_N=${EXP_EXCL_N:-720}
Q_LO=${Q_LO:-0.0075}; Q_HI=${Q_HI:-0.0083}   # ADD23: q_t sau sua (tinh 16/11 15:00 = 0.0079078)
U_TOL=${U_TOL:-0.003}
PAPER_EQ=${PAPER_EQ:-35000}
PREP_PY=${PREP_PY:-python3}
BOOK_SNAP_SH=${BOOK_SNAP_SH:-/home/ubuntu/claude_master/vz_e1_wt/research/parity_v12/sh/book_snap.sh}
BOOK_DIR=${BOOK_DIR:-/home/ubuntu/claude_master/parity_v12w/shadow_book}
GMICRO_TARGET=${GMICRO_TARGET:-/home/ubuntu/claude_master/parity_v12w/gmicro_target.json}
TARGET_TAG=${TARGET_TAG:-r4u3fin}
TG_SHA8=${TG_SHA8:-bdee1480}
CALM_H=${CALM_H:-6}; FORCE_CALM=${FORCE_CALM:-0}
gl_init dry_prep_micro_restart
WD=$LOGDIR/prep_micro_$TS; mkdir -p "$WD"
# ---------------------------------------------------------------- python (Oracle) : ke hoach / kiem buffer GRR1 + ke hoach so giay
cat > "$WD/prep_grr.py" <<'PYEOF'
import sys, struct, zlib, hashlib, time, datetime as dt
import numpy as np, snappy
MAGIC = 0x47525231; DAY = 86400000; HOUR = 3600000
PCT = float(np.float32(0.999950829)); DAYS = 90
REC = np.dtype([('t', '>i8'), ('r', '>f4')])
def ms7(s): return int((dt.datetime.fromisoformat(s) - dt.timedelta(hours=7)).replace(tzinfo=dt.timezone.utc).timestamp() * 1000)
def walk(b):
    i, n, out = 0, len(b), []
    while i + 12 <= n:
        mg, ln, crc = struct.unpack('>IiI', b[i:i + 12])
        if mg != MAGIC or ln < 0: return out, i, 'magic_sai@%d' % i
        if i + 12 + ln > n: return out, i, 'chunk_do_dang@%d' % i
        comp = b[i + 12:i + 12 + ln]
        if zlib.crc32(comp) & 0xffffffff != crc: return out, i, 'crc@%d' % i
        raw = snappy.uncompress(comp)
        if len(raw) % 12: return out, i, 'raw_le@%d' % i
        out.append(np.frombuffer(raw, REC)); i += 12 + ln
    return out, i, ('' if i == n else 'du_%d_byte' % (n - i))
def cat(ch): return np.concatenate(ch) if ch else np.zeros(0, REC)
def q_at(rec, h):
    m = (rec['t'] >= h - DAYS * DAY) & (rec['t'] < h); x = np.sort(rec['r'][m].astype(np.float32)); k = len(x)
    if k == 0: return float('nan'), 0
    return float(x[min(k - 1, max(0, int(np.floor(PCT * (k - 1)))))]), k
def enc(rec):
    raw = rec.astype(REC).tobytes(); comp = snappy.compress(raw)
    return struct.pack('>IiI', MAGIC, len(comp), zlib.crc32(comp) & 0xffffffff) + comp
md5 = lambda b: hashlib.md5(b).hexdigest()
h7 = lambda ms: (dt.datetime.utcfromtimestamp(ms / 1000) + dt.timedelta(hours=7)).strftime('%Y-%m-%d_%H:%M')
mode = sys.argv[1]
if mode == 'plan':   # plan <file> <from> <to> <out_prefix>
    b = open(sys.argv[2], 'rb').read(); ch, B, err = walk(b)
    if err and not err.startswith(('chunk_do_dang', 'du_')): print('FAIL buffer_hong ' + err); sys.exit(1)
    rec = cat(ch); t = rec['t']
    if len(t) == 0 or np.any(np.diff(t) < 0): print('FAIL buffer_rong_hoac_khong_tang'); sys.exit(1)
    a, z = ms7(sys.argv[3]), ms7(sys.argv[4]); w = (t >= a) & (t < z)
    new = rec[~w]; px = enc(new); open(sys.argv[5], 'wb').write(px)
    h = (int(time.time() * 1000) // HOUR + 1) * HOUR
    q0, m0 = q_at(rec, h); q1, m1 = q_at(new, h)
    print('B=%d' % B); print('PFX_MD5=%s' % md5(b[:B])); print('FILE_SZ=%d' % len(b)); print('TAIL_NOTE=%s' % (err or 'none'))
    print('N_PFX=%d' % len(rec)); print('N_EXCL=%d' % int(w.sum())); print('N_PFX_NEW=%d' % len(new))
    print('PX_MD5=%s' % md5(px)); print('PX_SZ=%d' % len(px)); print('PFX_FIRST=%s' % h7(t[0])); print('PFX_LAST=%s' % h7(t[-1]))
    print('Q_HOUR=%s' % h7(h)); print('Q_NOW=%.11f' % q0); print('Q_EXP=%.11f' % q1)
elif mode == 'verify':   # verify <file> <from> <to> <prefix_file> <log_size> <restart_ms>
    b = open(sys.argv[2], 'rb').read(); px = open(sys.argv[5], 'rb').read(); ch, B, err = walk(b)
    rec = cat(ch); t = rec['t']; a, z = ms7(sys.argv[3]), ms7(sys.argv[4]); ls, rms = int(sys.argv[6]), int(sys.argv[7])
    h = (int(time.time() * 1000) // HOUR + 1) * HOUR; q, m = q_at(rec, h)
    nw = int(((t >= a) & (t < z)).sum()); extra = t[ls:] if len(t) > ls else t[:0]
    print('V_N=%d V_IN_WIN=%d V_ERR=%s V_HEAD_OK=%s' % (len(t), nw, err or 'none', b[:len(px)] == px))
    print('Q_HOUR=%s' % h7(h)); print('Q_EXP=%.11f' % q)
    why = []
    if err: why.append('buffer_hong_' + err)
    if nw: why.append('con_%d_ban_ghi_trong_cua_so' % nw)
    if b[:len(px)] != px: why.append('dau_file_khac_PREFIX')
    if len(t) < ls or (len(extra) and extra.min() < rms - 600000): why.append('so_ban_ghi_%d_khac_log_%d' % (len(t), ls))
    if np.any(np.diff(t) < 0): why.append('ts_khong_tang')
    print('VERIFY=' + ('OK' if not why else 'FAIL ' + ','.join(why)))
elif mode == 'book':   # book <open_positions> <legacy_symbols> <purge_csv> <paper_eq>
    L = [x for x in open(sys.argv[2]).read().splitlines() if x.strip()]
    leg = {x.split(',')[0].strip() for x in open(sys.argv[3]).read().splitlines() if x.strip()}
    pu = set(sys.argv[4].split(',')); eq = float(sys.argv[5]); rz = 0.0; d, k, bad = [], [], []
    for x in L:
        p = x.split(',')
        if p[0] == 'sym': continue
        if p[0] == '#realized': rz = float(p[1]); continue
        if len(p) < 8: bad.append('dong_le:' + p[0]); continue
        if p[4] == '-1' and p[0] in leg: (d if p[0] in pu else bad).append(p[0])
        elif p[4] == '-1': bad.append('rank-1_ngoai_legacy:' + p[0])
        else: k.append((p[0], float(p[2]) * float(p[3])))
    kn = sum(v for _, v in k)
    print('N_ROWS=%d' % (len(d) + len(k) + len(bad))); print('N_DEL=%d' % len(d)); print('DEL=%s' % ','.join(sorted(d)))
    print('N_KEEP=%d' % len(k)); print('KEEP=%s' % ','.join(sorted(s for s, _ in k))); print('REALIZED=%s' % rz)
    print('KEEP_NOTIONAL=%.4f' % kn); print('U_EXP=%.5f' % (kn / (eq + rz))); print('PURGE_DA_DONG=%s' % ','.join(sorted(pu - set(d))))
    print('BAD=%s' % ','.join(bad))
PYEOF
pv() { echo "$1" | sed -n "s/^$2=//p" | head -1; }
gl_read_state
echo "$ST" | grep -v '^END_STATE$' | grep -v '^KEYS_' | sed 's/^/   242: /'
F=0; chk() { if eval "$2"; then say "OK   $1"; else say "FAIL $1"; F=1; fi; }
chk "1 process bot" "[ '$(sv NPROC)' = 1 ]"
chk "jar dang chay = pin $NJ_MD5" "[ '$(sv JAR_MD5)' = '$NJ_MD5' ]"
chk "dang chay c3_live DRY (process + env.sh) - script nay CHI cho DRY" "[ '$(sv ENV_LIVE_PROFILE)' = c3_live ] && [ '$(sv ENV_LIVE_ADAPTER)' = dry ] && [ '$(sv ENVSH_LIVE_ADAPTER)' = dry ]"
chk "2 co sizing/DCA grid = true (process + env.sh, ADD22)" "[ '$(sv ENV_LIVE_APPLY_GRID_RATIO)' = true ] && [ '$(sv ENV_LIVE_DCA_GRID_ENABLED)' = true ] && [ '$(sv ENVSH_LIVE_APPLY_GRID_RATIO)' = true ] && [ '$(sv ENVSH_LIVE_DCA_GRID_ENABLED)' = true ]"
chk "KHONG co GATE_BUFFER_SEED trong process (seed se ghi de buffer)" "[ -z '$(sv ENV_GATE_BUFFER_SEED)' ]"
chk "khong co co micro/pilot ($GL_MON_FLAG)" "[ ! -e '$GL_MON_FLAG' ]"
chk "latch kill-switch NONE" "[ '$(sv LATCH)' = NONE ] || [ '$(sv LATCH)' = NOFILE ]"
chk "khong PAUSE watchdog" "[ '$(sv PAUSE | cut -c1)' = 0 ]"
chk "khong canary/soak" "[ '$(sv CANARY_SOAK)' = 0 ]"
chk "MemAvailable $(sv MEM) >= $MIN_MEM_MB MB" "[ '$(sv MEM)' -ge $MIN_MEM_MB ] 2>/dev/null"
chk "dia trong >= 1 GB" "[ '$(sv DISK_K)' -gt 1048576 ] 2>/dev/null"
L0=$(sv LEGACY_N)
chk "LEGACY managed doc duoc ($L0), moi ($(sv LEGACY_AGE) s <= 600)" "[ -n '$L0' ] && [ '$(sv LEGACY_AGE)' -ge 0 ] && [ '$(sv LEGACY_AGE)' -le 600 ] 2>/dev/null"
CAP=$(sv ENV_C3_CAPITAL); CAP=${CAP:-$(sv ENVSH_C3_CAPITAL)}
chk "C3_CAPITAL process ($(sv ENV_C3_CAPITAL)) = env.sh ($(sv ENVSH_C3_CAPITAL))" "[ -n '$CAP' ] && [ '$(sv ENV_C3_CAPITAL)' = '$(sv ENVSH_C3_CAPITAL)' ]"
TGS=$(s242 "cd $A && P=\$(pgrep -f '$(gl_rx "$PROC_PAT")' | head -1); echo TGP=\$(tr '\0' '\n' < /proc/\$P/environ 2>/dev/null | sed -n 's/^TELEGRAM_BOT_TOKEN=//p' | tail -1 | tr -d '\n' | sha256sum | cut -c1-8); echo TGE=\$(bash -c '. conf/env.sh >/dev/null 2>&1; printf %s \"\$TELEGRAM_BOT_TOKEN\"' | sha256sum | cut -c1-8)")
TGP=$(echo "$TGS" | sed -n 's/^TGP=//p' | head -1); TGE=$(echo "$TGS" | sed -n 's/^TGE=//p' | head -1)
chk "token Telegram sha8: process $TGP + env.sh $TGE = $TG_SHA8 (khong in token)" "[ '$TGP' = '$TG_SHA8' ] && [ '$TGE' = '$TG_SHA8' ]"
# --- yen: khong co dot sap dang dien ra (ADD6 muc 2): 0 pass trong CALM_H dong [GATE-RATIO] q_t gan nhat; khong seed treo
CS=$(s242 "cd $A && echo GSEEDENV=\$(grep -c '^export GATE_BUFFER_SEED=' conf/env.sh); [ -e run/gate_ratio_live.bin.seeded ] && echo SEEDED=1 || echo SEEDED=0; echo PASSH=\$(tail -c 20000000 logs/full.log | grep -a '\[GATE-RATIO\] q_t=' | tail -n $CALM_H | grep -aoE 'pass=[0-9]+' | awk -F= '{s+=\$2} END{print s+0}')")
chk "env.sh KHONG co GATE_BUFFER_SEED" "[ '$(pv "$CS" GSEEDENV)' = 0 ]"
chk "khong co run/gate_ratio_live.bin.seeded" "[ '$(pv "$CS" SEEDED)' = 0 ]"
chk "gate pass = $(pv "$CS" PASSH) trong $CALM_H gio gan nhat (0 = khong co dot sap dang dien ra)" "[ '$(pv "$CS" PASSH)' = 0 ] || [ '$FORCE_CALM' = 1 ]"
# --- (A) ke hoach so giay (chi doc)
s242 "cat $SHADOW_DIR/open_positions.csv" > "$WD/open_positions.csv" && s242 "cat $A/run/legacy_symbols.csv" > "$WD/legacy_symbols.csv" || die "doc so giay / legacy_symbols tu 242 loi"
BK=$($PREP_PY -E "$WD/prep_grr.py" book "$WD/open_positions.csv" "$WD/legacy_symbols.csv" "$PURGE_SYMS" "$PAPER_EQ" 2>&1)
say "--- (A) so giay: $(pv "$BK" N_ROWS) cum mo; XOA $(pv "$BK" N_DEL): $(pv "$BK" DEL)"
say "    GIU $(pv "$BK" N_KEEP): $(pv "$BK" KEEP) | realized=$(pv "$BK" REALIZED) | U giay du kien sau ~ $(pv "$BK" U_EXP) (notional giu $(pv "$BK" KEEP_NOTIONAL) / ($PAPER_EQ + realized))"
say "    PURGE_SYMS da tu dong (time-stop/trailing) truoc khi chay: $(pv "$BK" PURGE_DA_DONG)"
chk "so giay: 0 dong rank=-1 ngoai legacy/PURGE_SYMS (BAD='$(pv "$BK" BAD)')" "[ -z '$(pv "$BK" BAD)' ] && [ -n '$(pv "$BK" N_ROWS)' ]"
chk "so giay: co >= 1 dong can xoa" "[ '$(pv "$BK" N_DEL)' -ge 1 ] 2>/dev/null"
# --- (B) ke hoach buffer (scp VE Oracle = chi doc 242)
$SCP_242 "${RHOST}$A/run/gate_ratio_live.bin" "$WD/before.bin" || die "keo ban chep gate_ratio_live.bin loi"
PL=$($PREP_PY -E "$WD/prep_grr.py" plan "$WD/before.bin" "$EXCL_FROM" "$EXCL_TO" "$WD/prefix_new.bin" 2>&1); echo "$PL" | sed 's/^/   (B) /'
P_B=$(pv "$PL" B); P_PFXMD5=$(pv "$PL" PFX_MD5); P_PXMD5=$(pv "$PL" PX_MD5); P_PXSZ=$(pv "$PL" PX_SZ); QE=$(pv "$PL" Q_EXP)
chk "buffer doc sach (khong FAIL)" "! echo \"\$PL\" | grep -q '^FAIL' && [ -n '$P_B' ] && [ -s '$WD/prefix_new.bin' ]"
chk "so ban ghi bo = $(pv "$PL" N_EXCL) = EXP_EXCL_N $EXP_EXCL_N ([$EXCL_FROM, $EXCL_TO) +07)" "[ '$(pv "$PL" N_EXCL)' = '$EXP_EXCL_N' ]"
chk "q_t du kien sau sua $QE trong [$Q_LO, $Q_HI] (truoc: $(pv "$PL" Q_NOW))" "awk -v q='$QE' -v a='$Q_LO' -v b='$Q_HI' 'BEGIN{exit !(q+0>=a+0 && q+0<=b+0)}'"
BS=$(ls -1t "$BOOK_DIR"/snap_*.txt 2>/dev/null | head -1)
say "INFO anh chup so giay harness moi nhat: ${BS:-khong_co} (script se chup them 1 anh truoc stop)"
[ "$F" = 0 ] || die "kiem truoc co muc FAIL (xem tren)"
say "--- se: chep PREFIX' ($P_PXSZ byte, md5 $P_PXMD5) len $A/run/gate_ratio_live.bin.prep_prefix_$TS -> book_snap -> PAUSE watchdog -> stop"
say "    -> backup .bak_prep_$TS (+.md5) 2 file -> buffer: kiem md5(head -c $P_B)=$P_PFXMD5, ghep PREFIX' + duoi -> so giay: xoa $(pv "$BK" N_DEL) dong"
say "    -> start -> hau kiem ${POST_ROUNDS}x${POST_WAIT_S}s: open=$(pv "$BK" N_KEEP) realized=$(pv "$BK" REALIZED), u~$(pv "$BK" U_EXP)+-$U_TOL, 0 [GATE-SEED], adapter=DRY, 2 co, LEGACY, token"
[ "$DRY" = 1 ] && { say "DRY=1: dung o day, KHONG ghi gi len 242 (chi doc + ban chep o $WD). (DRY PASS)"; exit 0; }
gl_time
gl_yes "Restart v_t_m DRY 1 lan: xoa $(pv "$BK" N_DEL) cum giay LEGACY-DCA + bo $EXP_EXCL_N ban ghi buffer gate 30/10. LEGACY (that, cung JVM) ngung quan ly ~30-60 s."
gl_time
$SCP_242 "$WD/prefix_new.bin" "${RHOST}$A/run/gate_ratio_live.bin.prep_prefix_$TS" || die "chep PREFIX' len 242 loi"
[ "$(s242 "md5sum < $A/run/gate_ratio_live.bin.prep_prefix_$TS | cut -c1-32")" = "$P_PXMD5" ] || die "md5 PREFIX' tren 242 lech"
if [ -f "$BOOK_SNAP_SH" ]; then timeout 120 bash "$BOOK_SNAP_SH" > "$WD/book_snap.txt" 2>&1 && say "OK book_snap truoc stop: $(tail -1 "$WD/book_snap.txt")" || say "WARN book_snap loi (harness: ngay hom nay XAM)"; else say "WARN khong co $BOOK_SNAP_SH"; fi
PAUSE_TOK="C3GOLIVE_${GL_NAME} TS=$TS pid=$$"
trap 'say "BI DUNG (tin hieu) - kiem: bash $GL_HERE/c3live_status.sh ; backup $A/run/gate_ratio_live.bin.bak_prep_$TS + $SHADOW_DIR/open_positions.csv.bak_prep_$TS"; gl_pause_clear >/dev/null 2>&1; exit 130' INT TERM HUP
# ---------------------------------------------------------------- restart co sua 2 file (IDEMPOTENT theo marker pha)
_prep_restart_rx() {
  s242in_once "PP='$PROC_PAT' bash -s -- $A $TS $WD_PAUSE $WD_PAUSE_MAX_S $$ $GL_NAME $SHADOW_DIR $PURGE_SYMS $P_B $P_PFXMD5 $P_PXMD5 $P_PXSZ" <<'EOF'
A=$1; TS=$2; PAUSE=$3; MAXS=$4; JP=$5; NM=$6; SHD=$7; PURGE=$8; B=$9; PFXMD5=${10}; PXMD5=${11}; PXSZ=${12}
cd "$A" || { echo "FAIL cd"; echo END_RS; exit 0; }
PH=run/.golive_${NM}_$TS.phase; GR=run/gate_ratio_live.bin; PX=$GR.prep_prefix_$TS; GB=$GR.bak_prep_$TS; OP=$SHD/open_positions.csv; OB=$OP.bak_prep_$TS
ph() { grep -qx "$1" "$PH" 2>/dev/null; }
mark() { echo "$1" >> "$PH"; }
m5() { md5sum < "$1" | cut -c1-32; }
restore() {
  local ok=1
  if [ -f "$GB.md5" ]; then \cp -fp "$GB" "$GR"; [ "$(m5 "$GR")" = "$(cat "$GB.md5")" ] || ok=0; fi
  if [ -f "$OB.md5" ]; then \cp -fp "$OB" "$OP"; [ "$(m5 "$OP")" = "$(cat "$OB.md5")" ] || ok=0; fi
  [ $ok = 1 ] && echo "OK khoi_phuc_2_file_tu_backup" || echo "FAIL khoi_phuc_md5_lech"
}
startbot() {
  ph "START_LINE=.*" || mark "START_LINE=$(( $(wc -l < logs/full.log 2>/dev/null || echo 0) + 1 ))"
  echo "START_LINE=$(sed -n 's/^START_LINE=//p' "$PH" | tail -1)"
  pgrep -f "$PP" >/dev/null || bin/daemon.sh start
  mark started; sleep 8
  P=$(pgrep -f "$PP" | head -1); [ -n "$P" ] && echo "OK started pid=$P lstart=$(ps -o lstart= -p $P)" || echo "FAIL khong_thay_process_sau_start"
}
info() { grep -E '^(DEL|KEEP_N|KEEP_NOTIONAL|REALIZED|GR_NEW_MD5|GR_OLD_SZ|GB_MD5|OB_MD5)=' "$PH" 2>/dev/null; }
if ph started; then
  echo "INFO pha_da_xong_truoc (chay lai sau ssh dut): KHONG stop/start lai"; echo "OK da_stop"
  ph edit_failed && echo "FAIL sua_file (lan truoc) - da khoi phuc"; ph edited && echo "OK sua_2_file (lan truoc)"; info
  echo "START_LINE=$(sed -n 's/^START_LINE=//p' "$PH" | tail -1)"
  P=$(pgrep -f "$PP" | head -1); [ -n "$P" ] && echo "OK started pid=$P" || echo "FAIL khong_thay_process_sau_start"
  echo END_RS; exit 0
fi
if ! ph stopped; then
  [ -f "$PX" ] && [ "$(m5 "$PX")" = "$PXMD5" ] && [ "$(stat -c %s "$PX")" = "$PXSZ" ] || { echo "FAIL prefix_staging_lech (bot KHONG dung)"; echo END_RS; exit 0; }
  [ -f "$OP" ] && [ -f run/legacy_symbols.csv ] && [ -f "$GR" ] || { echo "FAIL thieu_file_trang_thai (bot KHONG dung)"; echo END_RS; exit 0; }
fi
TOK="C3GOLIVE_${NM} TS=$TS pid=$JP"
mkdir -p "$(dirname "$PAUSE")" 2>/dev/null; echo "$TOK t=$(date +%s)" > "$PAUSE" && echo "OK watchdog_PAUSE token='$TOK'" || echo "WARN khong_tao_duoc_PAUSE"
if ! ph pause_timer; then setsid nohup bash -c "sleep $MAXS; grep -q '^$TOK ' '$PAUSE' 2>/dev/null && rm -f '$PAUSE'" > /dev/null 2>&1 < /dev/null & mark pause_timer; fi
if ! ph stopped; then
  echo "LEGACY_TRUOC_STOP=$(tail -c 20000000 logs/full.log 2>/dev/null | grep -a '\[LEGACY\] managed' | tail -1 | grep -aoE 'managed [0-9]+' | awk '{print $2}')"
  bin/daemon.sh stop
  for i in $(seq 1 30); do pgrep -f "$PP" >/dev/null || break; sleep 2; done
  if pgrep -f "$PP" >/dev/null; then echo "FAIL van_con_process_sau_stop (KHONG sua file)"; echo END_RS; exit 0; fi
  mark stopped
fi
echo "OK da_stop"
if ! ph edited && ! ph edit_failed; then
  E=""
  [ -f "$GB.md5" ] || { \cp -p "$GR" "$GB" && m5 "$GB" > "$GB.md5"; } || E="backup_gate_loi"
  [ -n "$E" ] || [ -f "$OB.md5" ] || { \cp -p "$OP" "$OB" && m5 "$OB" > "$OB.md5"; } || E="backup_so_giay_loi"
  [ -n "$E" ] || { mark "GB_MD5=$(cat "$GB.md5")"; mark "OB_MD5=$(cat "$OB.md5")"; echo "OK backup gate=$(cat "$GB.md5") so_giay=$(cat "$OB.md5")"; }
  if [ -z "$E" ]; then   # (B) buffer: luon tu BACKUP (idempotent)
    SZ=$(stat -c %s "$GB")
    if [ "$SZ" -lt "$B" ]; then E="buffer_ngan_hon_B($SZ<$B)"
    elif [ "$(head -c "$B" "$GB" | md5sum | cut -c1-32)" != "$PFXMD5" ]; then E="prefix_buffer_doi_tu_luc_tinh"
    else
      { cat "$PX"; tail -c +$((B + 1)) "$GB"; } > "$GR.new_$TS" && [ "$(stat -c %s "$GR.new_$TS")" = "$((PXSZ + SZ - B))" ] && mv -f "$GR.new_$TS" "$GR" || E="ghep_buffer_loi"
    fi
  fi
  if [ -z "$E" ]; then   # (A) so giay: tu BACKUP
    LEG=$(cut -d, -f1 run/legacy_symbols.csv | tr -d '\r ' | grep -v '^$' | tr '\n' ' ')
    DL=run/.prep_del_$TS; BD=run/.prep_bad_$TS; : > "$DL"; : > "$BD"
    awk -F, -v L="$LEG" -v P="$PURGE" -v DL="$DL" -v BD="$BD" 'BEGIN{n=split(L,a," ");for(i=1;i<=n;i++)lg[a[i]]=1;m=split(P,b,",");for(i=1;i<=m;i++)pu[b[i]]=1}
      NR==1 || /^#/ {print; next}
      $5=="-1" && ($1 in lg) {print $1 >> DL; if (!($1 in pu)) print $1 >> BD; next}
      $5=="-1" {print $1 >> BD}
      {print}' "$OB" > "$OP.new_$TS" || E="awk_loi"
    ND=$(wc -l < "$DL"); NB=$(wc -l < "$BD"); NK=$(grep -vcE '^(#|sym,)' "$OP.new_$TS"); NO=$(grep -vcE '^(#|sym,)' "$OB")
    [ -n "$E" ] || [ "$NB" = 0 ] || E="rank-1_ngoai_danh_sach:$(tr '\n' ' ' < "$BD")"
    [ -n "$E" ] || { [ "$ND" -ge 1 ] && [ $((NK + ND)) = "$NO" ]; } || E="dem_dong_lech(xoa=$ND giu=$NK goc=$NO)"
    [ -n "$E" ] || { [ "$(head -1 "$OB")" = "$(head -1 "$OP.new_$TS")" ] && [ "$(grep '^#realized,' "$OB")" = "$(grep '^#realized,' "$OP.new_$TS")" ]; } || E="header_hoac_realized_lech"
    [ -n "$E" ] || mv -f "$OP.new_$TS" "$OP" || E="mv_so_giay_loi"
  fi
  if [ -n "$E" ]; then
    echo "FAIL sua_file: $E"; restore; rm -f "$GR.new_$TS" "$OP.new_$TS"; mark edit_failed
  else
    mark edited; mark "DEL=$(tr '\n' ',' < run/.prep_del_$TS | sed 's/,$//')"; mark "KEEP_N=$NK"
    mark "KEEP_NOTIONAL=$(awk -F, 'NR>1 && !/^#/ {s+=$3*$4} END{printf "%.4f", s}' "$OP")"
    mark "REALIZED=$(sed -n 's/^#realized,\([^,]*\),.*/\1/p' "$OP" | head -1)"; mark "GR_NEW_MD5=$(m5 "$GR")"; mark "GR_OLD_SZ=$SZ"
    echo "OK sua_2_file"
  fi
fi
ph edit_failed && echo "FAIL sua_file - da khoi phuc 2 file, start lai trang thai cu"
info
startbot
echo END_RS
EOF
}
gl_once_resume restart _prep_restart_rx RS END_RS
RS=$(printf '%s\n' "$RS" | grep -vx END_RS); echo "$RS"
SL=$(pv "$RS" START_LINE); SL=${SL:-1}
LB=$(pv "$RS" LEGACY_TRUOC_STOP); [ -n "$LB" ] && L0=$LB
# ---------------------------------------------------------------- rollback (stop -> 2 file ve backup, kiem md5 -> start -> adapter=DRY)
_prep_rb_rx() {
  s242in_once "PP='$PROC_PAT' bash -s -- $A $TS $WD_PAUSE $GL_NAME $SHADOW_DIR $RB_LOG_WAIT_S $RB_LOG_POLL_S" <<'EOF'
A=$1; TS=$2; PAUSE=$3; NM=$4; SHD=$5; LW=$6; LP=$7; cd "$A" || { echo "FAIL cd"; echo END_RB; exit 0; }
RP=run/.golive_${NM}_$TS.rbphase; GR=run/gate_ratio_live.bin; GB=$GR.bak_prep_$TS; OP=$SHD/open_positions.csv; OB=$OP.bak_prep_$TS
ph() { grep -qx "$1" "$RP" 2>/dev/null; }
mark() { echo "$1" >> "$RP"; }
m5() { md5sum < "$1" | cut -c1-32; }
if ! ph rb_started; then
  bin/daemon.sh stop
  for i in $(seq 1 30); do pgrep -f "$PP" >/dev/null || break; sleep 2; done
  pgrep -f "$PP" >/dev/null && { echo "FAIL van_con_process"; echo END_RB; exit 0; }
  [ -f "$GB.md5" ] && \cp -fp "$GB" "$GR"; [ -f "$OB.md5" ] && \cp -fp "$OB" "$OP"
  ph "RB_START_LINE=.*" || mark "RB_START_LINE=$(( $(wc -l < logs/full.log 2>/dev/null || echo 0) + 1 ))"
  bin/daemon.sh start; mark rb_started; sleep 8
else
  echo "INFO rollback da start o lan truoc - chi KIEM"; pgrep -f "$PP" >/dev/null || { bin/daemon.sh start; sleep 8; }
fi
if [ -f "$GB.md5" ]; then [ "$(m5 "$GR")" = "$(cat "$GB.md5")" ] && echo "OK gate_ratio_ve_backup md5=$(cat "$GB.md5")" || echo "FAIL gate_ratio_md5_lech"; else echo "INFO chua_co_backup_gate"; fi
if [ -f "$OB.md5" ]; then [ "$(m5 "$OP")" = "$(cat "$OB.md5")" ] && echo "OK so_giay_ve_backup md5=$(cat "$OB.md5")" || echo "FAIL so_giay_md5_lech"; else echo "INFO chua_co_backup_so_giay"; fi
SL=$(sed -n 's/^RB_START_LINE=//p' "$RP" | tail -1); SL=${SL:-1}; P=$(pgrep -f "$PP" | head -1)
[ -n "$P" ] && echo "OK started pid=$P" || echo "FAIL khong_thay_process"
PA=$(tr '\0' '\n' < /proc/$P/environ 2>/dev/null | sed -n 's/^LIVE_ADAPTER=//p' | tail -1)
W=0; AL=""
while :; do AL=$(tail -n +$SL logs/full.log 2>/dev/null | grep -a 'khoi dong adapter=' | tail -1 | grep -aoE 'adapter=(LIVE|DRY)' | cut -d= -f2); [ -n "$AL" ] || [ "$W" -ge "$LW" ] && break; sleep "$LP"; W=$((W + LP)); done
if [ -n "$P" ] && [ "$PA" = dry ] && [ "$AL" = DRY ]; then echo "OK adapter_sau_rollback=dry"
else [ -e run/KILL_SWITCH ] || echo "${NM} $TS rollback_adapter_sai: dung mo moi" > run/KILL_SWITCH; echo "FAIL adapter_sau_rollback (process=$PA log=${AL:-?}) - run/KILL_SWITCH dat"; fi
grep -q "^C3GOLIVE_${NM} TS=$TS " "$PAUSE" 2>/dev/null && rm -f "$PAUSE"
echo END_RB
EOF
}
do_rollback() {
  gl_once_resume rollback _prep_rb_rx RB END_RB; echo "$RB"
  echo "$RB" | grep -qx END_RB && ! echo "$RB" | grep -q '^FAIL'
}
if echo "$RS" | grep -q '^FAIL ssh_restart_loi_trang_thai_khong_ro'; then
  M="restart: ssh dut, KHONG doc duoc trang thai that => KHONG ket luan. Kiem: bash $GL_HERE/c3live_status.sh ; backup *.bak_prep_$TS"
  say "KHAN: $M"; tg "[prep micro] KHAN TS=$TS: $M | log $LOG"; exit 2
fi
if ! echo "$RS" | grep -q '^OK da_stop'; then
  gl_pause_clear >/dev/null 2>&1
  say "DUNG: FAIL TRUOC khi dung bot: $(echo "$RS" | grep '^FAIL' | head -2 | tr '\n' ' ')"; say "KET QUA: TU_CHOI - bot KHONG bi dung, khong doi gi. Log: $LOG"; exit 1
fi
KN=$(pv "$RS" KEEP_N); RZ=$(pv "$RS" REALIZED); KNT=$(pv "$RS" KEEP_NOTIONAL)
UEXP=$(awk -v n="${KNT:-0}" -v e="$PAPER_EQ" -v r="${RZ:-0}" 'BEGIN{printf "%.5f", n/(e+r)}')
TG_CHK='
S8=$(echo "$E" | sed -n "s/^TELEGRAM_BOT_TOKEN=//p" | tail -1 | tr -d "\n" | sha256sum | cut -c1-8); [ "$S8" = "'"$TG_SHA8"'" ] && echo "OK process_env_telegram_sha8=$S8" || echo "FAIL process_env_telegram_sha8=$S8"
'
XBASE='
envk LIVE_ADAPTER=dry
envk C3_CAPITAL='"$CAP"'
envk LIVE_APPLY_GRID_RATIO=true
envk LIVE_DCA_GRID_ENABLED=true
[ "$(md5sum < target/binance-java-sdk-1.2.4.jar | cut -c1-32)" = "'"$NJ_MD5"'" ] && echo "OK jar_khong_doi" || echo "FAIL jar_md5_doi"
[ "$(T "khoi dong adapter=DRY")" -ge 1 ] && echo "OK adapter_DRY" || echo "WAIT adapter_DRY"
[ "$(T "khoi dong adapter=LIVE")" = 0 ] || echo "FAIL adapter_LIVE_trong_log"
[ "$(T "\[MINUTE-FIN\] BAT")" -ge 1 ] && echo "OK MINUTE-FIN_BAT" || echo "WAIT MINUTE-FIN_BAT"
[ "$(T "\[LIVE-SIZING\] LIVE_APPLY_GRID_RATIO=true")" -ge 1 ] && echo "OK LIVE-SIZING_BAT" || echo "WAIT LIVE-SIZING_BAT"
[ "$(T "\[LIVE-DCA-GRID\] LIVE_DCA_GRID_ENABLED=true")" -ge 1 ] && echo "OK LIVE-DCA-GRID_BAT" || echo "WAIT LIVE-DCA-GRID_BAT"
NE=$(tail -n +$SL $L 2>/dev/null | grep -ac " ERROR "); [ "$NE" = 0 ] && echo "OK 0_ERROR" || echo "FAIL ${NE}_dong_ERROR: $(tail -n +$SL $L | grep -a " ERROR " | head -1 | cut -c1-140)"
'"$TG_CHK"
XEDIT='
SH=$(tail -n +$SL $L 2>/dev/null | grep -a "\[SHADOW\] so vi the giay khoi tao" | tail -1)
if [ -z "$SH" ]; then echo "WAIT SHADOW_khoi_tao"; else
  ON=$(echo "$SH" | grep -aoE " open=[0-9]+" | cut -d= -f2); RL=$(echo "$SH" | grep -aoE "realized=[-0-9.E]+" | cut -d= -f2)
  [ "$ON" = "'"$KN"'" ] && echo "OK SHADOW_open=$ON" || echo "FAIL SHADOW_open=$ON (ky vong '"$KN"')"
  awk -v a="$RL" -v b="'"$RZ"'" "BEGIN{d=a-b; if(d<0)d=-d; exit !(d<1e-6)}" && echo "OK SHADOW_realized=$RL" || echo "FAIL SHADOW_realized=$RL (ky vong '"$RZ"')"
fi
[ "$(T "\[GATE-SEED\]")" = 0 ] && echo "OK 0_GATE-SEED" || echo "FAIL co_dong_GATE-SEED"
[ "$(T "\[GATE-RATIO\] persist hong")" = 0 ] && [ "$(T "khong nap duoc persist")" = 0 ] && echo "OK persist_doc_sach" || echo "FAIL persist_hong_hoac_khong_nap"
GS=$(tail -n +$SL $L 2>/dev/null | grep -a "\[GATE-RATIO\] LIVE n[^ ]* buffer: size=" | tail -1 | grep -aoE "size=[0-9]+" | cut -d= -f2)
[ -n "$GS" ] && echo "OK GR_LOAD_SIZE=$GS" || echo "WAIT GR_LOAD_SIZE"
UL=$(tail -n +$SL $L 2>/dev/null | grep -a "\[GATE\] scale=" | grep -aoE " u=[0-9.]+" | tail -1 | cut -d= -f2)
if [ -z "$UL" ]; then echo "INFO u_giay_chua_co_dong_GATE"; else awk -v u="$UL" -v e="'"$UEXP"'" -v t="'"$U_TOL"'" "BEGIN{d=u-e; if(d<0)d=-d; exit !(d<=t)}" && echo "OK U_giay=$UL (ky vong '"$UEXP"')" || echo "FAIL U_giay=$UL (ky vong '"$UEXP"' +- '"$U_TOL"')"; fi
'
if echo "$RS" | grep -q '^FAIL sua_file'; then
  say "SUA FILE LOI sau stop => 2 file da khoi phuc tu backup, bot start lai trang thai CU. Kiem bot..."
  CHK() { gl_chk_common "$SL" "$L0" "$XBASE"; }
  if echo "$RS" | grep -q '^OK khoi_phuc_2_file_tu_backup' && gl_postloop CHK; then
    gl_pause_clear >/dev/null 2>&1; say "KET QUA: TU_CHOI sau stop - trang thai CU, bot chay lai OK. Ngay hom nay XAM (co restart). Log: $LOG"
    tg "[prep micro] TU CHOI TS=$TS: sua file loi, da khoi phuc + restart OK"; exit 1
  fi
  s242 "cd $A && { [ -e run/KILL_SWITCH ] || echo '$GL_NAME $TS khoi_phuc_loi' > run/KILL_SWITCH; }" >/dev/null 2>&1
  say "KHAN: sua file loi VA khoi phuc/khoi dong lai khong dat - KILL_SWITCH dat; kiem tay c3live_status.sh"; tg "[prep micro] KHAN TS=$TS khoi phuc loi | log $LOG"; exit 2
fi
CHK() { gl_chk_common "$SL" "$L0" "$XBASE$XEDIT"; }
WHY=""; VF=""; QV=""; GS=""; STMS=""
if gl_postloop CHK; then
  GS=$(echo "$RESULT" | sed -n 's/^OK GR_LOAD_SIZE=//p' | tail -1)
  STMS=$(s242 "P=\$(pgrep -f '$(gl_rx "$PROC_PAT")' | head -1); [ -n \"\$P\" ] && echo \$(( (\$(date +%s) - \$(ps -o etimes= -p \$P | tr -d ' ')) * 1000 ))")
  if $SCP_242 "${RHOST}$A/run/gate_ratio_live.bin" "$WD/after.bin"; then
    VF=$($PREP_PY -E "$WD/prep_grr.py" verify "$WD/after.bin" "$EXCL_FROM" "$EXCL_TO" "$WD/prefix_new.bin" "${GS:-0}" "${STMS:-0}" 2>&1); echo "$VF" | sed 's/^/   (B kiem) /'
    QV=$(pv "$VF" Q_EXP)
    echo "$VF" | grep -qx 'VERIFY=OK' || WHY="buffer_moi: $(pv "$VF" VERIFY)"
    [ -n "$WHY" ] || awk -v q="$QV" -v a="$Q_LO" -v b="$Q_HI" 'BEGIN{exit !(q+0>=a+0 && q+0<=b+0)}' || WHY="q_t_du_kien $QV ngoai [$Q_LO,$Q_HI]"
  else WHY="khong_keo_duoc_buffer_moi_ve_Oracle"; fi
else
  WHY=$(echo "${RESULT:-}" | grep '^FAIL\|^WAIT' | tr '\n' ' ' | cut -c1-240)
fi
if [ -z "$WHY" ]; then
  trap - INT TERM HUP
  gl_pause_clear >/dev/null || say "PAUSE con (ssh?) - tu go sau ${WD_PAUSE_MAX_S}s"
  if [[ "$STMS" =~ ^[0-9]{13}$ ]]; then
    { echo "ts=$TS start_ms=$STMS start=$(TZ=Asia/Ho_Chi_Minh date -d @$((STMS / 1000)) '+%F %T')"; echo "del=$(pv "$RS" DEL)"; echo "keep_n=$KN realized=$RZ u_exp=$UEXP"
      echo "gate_old_md5=$(pv "$RS" GB_MD5) gate_new_md5=$(pv "$RS" GR_NEW_MD5) book_old_md5=$(pv "$RS" OB_MD5) excl=[$EXCL_FROM,$EXCL_TO) n=$EXP_EXCL_N"
      echo "gr_load_size=$GS q_exp_hour=$(pv "$VF" Q_HOUR) q_exp=$QV"; } > "$LOGDIR/prep_micro_start_${TS}.txt"
    GM=$(python3 -I - "$GMICRO_TARGET" "$TARGET_TAG" "$NJ_MD5" "$STMS" <<'PYEOF'
import json, os, shutil, sys, time
p, tag, md5, ms = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
if not os.path.exists(p): print('WARN khong co %s - khong ghi' % p); sys.exit(0)
try: cur = json.load(open(p))
except Exception as e: print('WARN file hong %s' % type(e).__name__); sys.exit(0)
if cur.get('target_jar') != tag or cur.get('target_md5') != md5:
    print('WARN file tro target khac - KHONG ghi; MASTER dien smoke_start_ms=%d' % ms); sys.exit(0)
shutil.copy2(p, '%s.bak_%d' % (p, int(time.time())))
cur['smoke_start_ms'] = ms; cur['smoke_note'] = 'dry_prep_micro_restart: don so giay LEGACY-DCA + bo r 30/10 03:40-04:10 (jar/env khong doi)'
json.dump(cur, open(p + '.tmp', 'w')); os.replace(p + '.tmp', p); print('OK smoke_start_ms=%d' % ms)
PYEOF
)
    say "START_MS JVM moi = $STMS - luu $LOGDIR/prep_micro_start_${TS}.txt | gmicro_target: $GM"
  else say "WARN khong lay duoc START_MS - MASTER dien smoke_start_ms tay"; fi
  say "=== XONG: so giay xoa $(pv "$RS" DEL | tr ',' '\n' | grep -c .) cum (con $KN), buffer bo $EXP_EXCL_N ban ghi. KIEM TIEP (MASTER): dong [GATE-RATIO] q_t9 dau tien luc $(pv "$VF" Q_HOUR) PHAI = $QV. Ngay hom nay XAM. Log: $LOG"
  tg "[prep micro] XONG TS=$TS: so giay con $KN cum, buffer sach 30/10, q_t9 ky vong $QV luc $(pv "$VF" Q_HOUR). Log $LOG"
  exit 0
fi
say "hau kiem TRUOT ($WHY) => ROLLBACK: 2 file ve backup .bak_prep_$TS + restart"
if do_rollback; then say "Da ROLLBACK xong (trang thai cu, adapter=dry)."; tg "[prep micro] TRUOT TS=$TS: $WHY => ROLLBACK XONG. Log $LOG"; exit 1; fi
s242 "cd $A && { [ -e run/KILL_SWITCH ] || echo '$GL_NAME $TS rollback_loi' > run/KILL_SWITCH; }" >/dev/null 2>&1
M="hau kiem TRUOT ($WHY) VA ROLLBACK LOI ($(echo "$RB" | grep '^FAIL' | head -2 | tr '\n' ' ')) - kiem tay c3live_status.sh; backup *.bak_prep_$TS"
say "KHAN: $M"; tg "[prep micro] KHAN TS=$TS: $M | log $LOG"; exit 2
