#!/usr/bin/env bash
# =============================================================================
# close_aerospike_3222.sh — DONG cong Aerospike Oracle (TCP 3222) voi Internet. Owner chay bang sudo.
#   sudo bash ~/claude_master/deploy/close_aerospike_3222.sh             # DRY (mac dinh): trang thai + luat se them, khong doi gi
#   sudo bash ~/claude_master/deploy/close_aerospike_3222.sh --apply     # go YES => them luat + luu rules.v4 + cat ket noi la
#   sudo bash ~/claude_master/deploy/close_aerospike_3222.sh --rollback  # go DUNG cac luat comment AS3222_CLOSE (live + rules.v4)
# Hien trang (kiem 11-11, chi doc): asd chay trong container docker NHUNG network=host (khong docker-proxy, docker0 DOWN,
#   asd nghe 0.0.0.0:3222 tren host; 3225/3226 chi 127.0.0.1) => goi tin di qua chain INPUT (khong qua DOCKER-USER).
#   Luat ben: netfilter-persistent (enabled) + /etc/iptables/rules.v4. ufw: ENABLED=no.
# Luat (chen DAU chain INPUT, comment AS3222_CLOSE, chi khop dport 3222 => KHONG dung ssh 22 hay luat khac):
#   ACCEPT tu 127.0.0.0/8, 10.0.0.0/24 (VCN/IP rieng Oracle), 172.16.0.0/12 (docker noi bo), 103.157.218.242 (242: collectData/v_t_m
#   doc cum Oracle), 161.118.212.3 (IP public Oracle: tool local dung AEROSPIKE_HOST_226=161.118.212.3, vd res1109 t2a) ; con lai DROP.
#   Neu listener la docker-proxy (publish -p) => them luat tuong tu vao DOCKER-USER (--ctorigdstport).
# !! CANH BAO (11-11): kernel Kaggle sim (R1/R3, kaggle_sim/*/run.py) doc symbol_mapper qua AEROSPIKE_HOST_226=161.118.212.3:3222
#   tu IP GCP dong (34.40.185.188, 35.241.236.214 ...). Dong cong => cac kernel do mat mapper. Chi --apply khi R1/R3 da xong
#   hoac bundle da kem mapper / doi nguon (MASTER quyet). Muon mo them dai IP: AS_ALLOW="... <cidr>".
# [A1_AS3222 sua] Oracle KHONG co conntrack => cat ket noi IP la bang 'ss -K'; khong cat duoc (kernel khong ho tro) => socket cu
#   treo nhung goi bi DROP = CANH BAO (in thoi gian tu het); CHI FAIL khi co ket noi MOI tu IP la sau khi ap luat (dem lai sau 30 s).
#   Kiem 242 chay ssh bang 'sudo -u $SUDO_USER' (key + known_hosts cua ubuntu); thieu SUDO_USER => DUNG truoc moi thay doi.
#   Chen ACCEPT loi => go lai luat da chen, KHONG chen DROP, KHONG ghi rules.v4, exit 1. rules.v4 da co AS3222_CLOSE => khong them trung.
# Bien (test/sandbox): IPT IPT_RESTORE RULES_V4 SS_CMD SS_KILL SSH_242 AS_RUNAS AS_WAIT_S AS_PORTS AS_ALLOW AS_PUB_IP NO_ROOT_OK=1 AS_LOGDIR
# =============================================================================
set -uo pipefail
MODE=dry
case "${1:-}" in --apply) MODE=apply;; --rollback) MODE=rollback;; ""|--dry) MODE=dry;; *) echo "Dung: $0 [--apply|--rollback]"; exit 1;; esac
TAG=AS3222_CLOSE
PORTS=${AS_PORTS:-3222}
PUB=${AS_PUB_IP:-161.118.212.3}
ALLOW=${AS_ALLOW:-"127.0.0.0/8 10.0.0.0/24 172.16.0.0/12 103.157.218.242/32 $PUB/32"}
IPT=${IPT:-iptables}; IPT_RESTORE=${IPT_RESTORE:-iptables-restore}
RULES=${RULES_V4:-/etc/iptables/rules.v4}; SS=${SS_CMD:-ss}; SSK=${SS_KILL:-$SS -K}; WAIT_S=${AS_WAIT_S:-30}
SSH_242=${SSH_242:-"ssh -p 2222 -o BatchMode=yes -o ConnectTimeout=20 -i /home/ubuntu/.ssh/id_rsa_chuyennd root@103.157.218.242"}
TS=$(date +%Y%m%d_%H%M%S); LOGDIR=${AS_LOGDIR:-/home/ubuntu/claude_master/deploy}; mkdir -p "$LOGDIR" 2>/dev/null || LOGDIR=/tmp
LOG=$LOGDIR/close_aerospike_3222_${TS}_${MODE}.log
exec > >(tee -a "$LOG") 2>&1
say() { echo "[$(date '+%F %T')] $*"; }
NF=0; NW=0; ok() { say "OK   $*"; }; bad() { say "FAIL $*"; NF=$((NF + 1)); }; warn() { say "WARN $*"; NW=$((NW + 1)); }
die() { say "DUNG: $*"; exit 1; }
if [ "$MODE" = apply ]; then   # [MAJ-1b] kiem 242 phai chay ssh bang user goc (key + known_hosts cua ubuntu)
  [ -n "${SUDO_USER:-}" ] && [ "${SUDO_USER}" != root ] || die "thieu SUDO_USER (chay bang 'sudo bash $0 --apply' tu user ubuntu) — chua doi gi"
  if [ -n "${AS_RUNAS+x}" ]; then read -r -a RUNAS <<< "$AS_RUNAS"; else RUNAS=(sudo -u "$SUDO_USER"); fi
fi
[ "$(id -u)" = 0 ] || [ "${NO_ROOT_OK:-0}" = 1 ] || { [ "$MODE" = dry ] && say "!! khong phai root: DRY chi in ke hoach (khong doc duoc iptables/rules.v4) — chay lai bang sudo de DRY day du"; } 
ROOT=0; { [ "$(id -u)" = 0 ] || [ "${NO_ROOT_OK:-0}" = 1 ]; } && ROOT=1
for p in $PORTS; do [ "$p" = 22 ] && die "PORTS chua 22 — khong bao gio"; done
# ---------------------------------------------------------------- spec luat (dung dinh dang iptables -S de -C/-D khop)
specs() {   # $1 chain => in tung spec theo thu tu (ACCEPT truoc, DROP cuoi)
  local m="-p tcp -m multiport --dports ${PORTS// /,}"
  [ "$1" = DOCKER-USER ] && m="-p tcp -m conntrack --ctorigdstport ${PORTS%% *}"
  for s in $ALLOW; do echo "-s $s $m -m comment --comment $TAG -j ACCEPT"; done
  echo "$m -m comment --comment $TAG -j DROP"
}
listener() { $SS -tlnpH "( sport = :${PORTS%% *} )" 2>/dev/null | grep -oE 'users:\(\("[^"]+"' | head -1 | sed 's/.*"//'; }
cur_rules() { $IPT -S "$1" 2>/dev/null | grep -- "--comment $TAG" || true; }
in_allow() { python3 - "$1" $ALLOW <<'PY'
import ipaddress, sys
ip = ipaddress.ip_address(sys.argv[1].split('%')[0].replace('::ffff:', ''))
sys.exit(0 if any(ip in ipaddress.ip_network(n, strict=False) for n in sys.argv[2:]) else 1)
PY
}
peersp() { $SS -tnH state established "( sport = :${PORTS%% *} )" 2>/dev/null | awk '{print $NF}' | sed -E 's/^\[?(::ffff:)?//; s/\]?:([0-9]+)$/ \1/' | sort -u; }   # "ip port"
peers() { peersp | awk '{print $1}' | sort -u; }
foreign() { peersp | while read -r ip pt; do [ -n "$ip" ] && ! in_allow "$ip" && echo "$ip $pt"; done; true; }
state() {
  say "--- trang thai ($1)"
  echo "   listener cong ${PORTS%% *}: $(listener || true) | $($SS -tlnH "( sport = :${PORTS%% *} )" 2>/dev/null | awk '{print $4}' | tr '\n' ' ')"
  echo "   client dang noi: $(peers | tr '\n' ' ')"
  if [ "$ROOT" = 1 ]; then echo "   luat $TAG trong INPUT: $(cur_rules INPUT | grep -c .) | DOCKER-USER: $(cur_rules DOCKER-USER | grep -c .)"
    echo "   rules.v4: $([ -r "$RULES" ] && grep -c -- "$TAG" "$RULES" || echo 'khong doc duoc') dong $TAG"; fi
  echo "   phien ssh hien tai: ${SSH_CONNECTION:-khong qua ssh} (cong 22 KHONG nam trong luat)"
}
CHAINS=(INPUT)
LS=$(listener || true)
[ "$LS" = docker-proxy ] && CHAINS+=(DOCKER-USER)
say "=== close_aerospike_3222 MODE=$MODE ports=[$PORTS] allow=[$ALLOW] chain=[${CHAINS[*]}] ==="
state TRUOC
# ---------------------------------------------------------------- rules.v4 (ben qua reboot)
v4_new() {   # in rules.v4 moi: chen spec INPUT truoc dong '-A INPUT' dau tien cua *filter (hoac truoc COMMIT neu khong co)
  local ins; ins=$(specs INPUT | sed 's/^/-A INPUT /')
  awk -v ins="$ins" '
    /^\*filter/ {f=1} 
    f && !done && (/^-A INPUT / || /^COMMIT/) { print ins; done=1 }
    /^COMMIT/ {f=0} {print}
    END { if (!done) exit 3 }' "$RULES"
}
v4_del() { grep -v -- "--comment $TAG" "$RULES"; }
v4_install() {   # $1 file moi
  $IPT_RESTORE --test < "$1" || { bad "iptables-restore --test tu choi file moi — KHONG ghi rules.v4"; return 1; }
  cp -p "$RULES" "$RULES.bak_${TAG}_$TS" && cat "$1" > "$RULES" && ok "rules.v4 da cap nhat (backup $RULES.bak_${TAG}_$TS)"
}
if [ "$MODE" = dry ]; then
  say "--- ke hoach:"; for c in "${CHAINS[@]}"; do specs "$c" | sed "s/^/   + iptables -I $c <dau chain> /"; done
  echo "   + luu ben: chen cac dong tren vao $RULES (*filter, truoc -A INPUT dau tien), kiem bang iptables-restore --test"
  echo "   + ss -K: cat ket noi ${PORTS%% *} tu IP NGOAI danh sach cho phep (242 giu nguyen); dem lai sau ${WAIT_S}s"
  [ "$ROOT" = 1 ] && [ -r "$RULES" ] && grep -q -- "--comment $TAG" "$RULES" && echo "   = rules.v4 DA co $TAG — se khong them trung"
  if [ "$ROOT" = 1 ]; then
    if [ -r "$RULES" ] && ! grep -q -- "--comment $TAG" "$RULES"; then T=$(mktemp); if v4_new > "$T" && $IPT_RESTORE --test < "$T"; then ok "DRY: rules.v4 moi hop le (iptables-restore --test)"; else bad "DRY: rules.v4 moi KHONG hop le"; fi; rm -f "$T"; fi
    for c in "${CHAINS[@]}"; do while IFS= read -r s; do $IPT -C "$c" $s 2>/dev/null && echo "   (da co) $c $s"; done < <(specs "$c"); done
  fi
  echo "   + client hien tai se bi cat: $(for ip in $(peers); do in_allow "$ip" || printf '%s ' "$ip"; done)"
  say "DRY: khong doi gi. (DRY PASS)"; echo; echo "OCI: nen go them rule ingress TCP 3222 trong Security List / NSG cua VCN (console OCI: Networking > VCN > Security Lists) — script KHONG lam."; exit 0
fi
[ "$ROOT" = 1 ] || die "can root (sudo)"
if [ "$MODE" = rollback ]; then
  say ">>> Go YES de GO cac luat $TAG (mo lai cong ${PORTS%% *} nhu truoc):"; read -r ANS || ANS=""; [ "$ANS" = YES ] || { say "Huy."; exit 0; }
  for c in "${CHAINS[@]}" DOCKER-USER; do cur_rules "$c" | sed 's/^-A /-D /' | while IFS= read -r r; do $IPT $r && echo "   go: $r"; done; done
  [ -z "$(cur_rules INPUT)$(cur_rules DOCKER-USER)" ] && ok "live: 0 luat $TAG" || bad "live: con luat $TAG"
  if [ -r "$RULES" ] && grep -q -- "$TAG" "$RULES"; then T=$(mktemp); v4_del > "$T" && v4_install "$T"; rm -f "$T"; fi
  grep -q -- "$TAG" "$RULES" 2>/dev/null && bad "rules.v4 con $TAG" || ok "rules.v4: 0 dong $TAG"
  [ "$NF" = 0 ] && { say "=== ROLLBACK XONG. Log: $LOG"; exit 0; } || { say "=== ROLLBACK FAIL ($NF). Log: $LOG"; exit 1; }
fi
# ---------------------------------------------------------------- APPLY
[ -n "$(cur_rules INPUT)" ] && die "da co luat $TAG trong INPUT — chay --rollback truoc neu muon ap lai"
[ -r "$RULES" ] || die "khong doc duoc $RULES (netfilter-persistent?)"
V4HAS=0; grep -q -- "--comment $TAG" "$RULES" && V4HAS=1   # [MIN] da co trong rules.v4 => khong them trung
T=$(mktemp)
if [ "$V4HAS" = 0 ]; then
  v4_new > "$T" || { rm -f "$T"; die "khong chen duoc vao $RULES (khong thay *filter)"; }
  $IPT_RESTORE --test < "$T" || { rm -f "$T"; die "rules.v4 moi khong hop le — khong lam gi"; }
fi
say ">>> Go YES de DONG cong ${PORTS%% *} (tru: $ALLOW):"; read -r ANS || ANS=""; [ "$ANS" = YES ] || { rm -f "$T"; say "Huy. Khong doi gi."; exit 0; }
ADDED=()
undo_added() { local a; for a in "${ADDED[@]}"; do $IPT -D ${a%%|*} ${a#*|} && echo "   go lai: ${a%%|*} ${a#*|}"; done; }
for c in "${CHAINS[@]}"; do   # specs: moi ACCEPT truoc, DROP cuoi => loi o ACCEPT thi DROP chua bao gio duoc chen
  i=1
  while IFS= read -r s; do
    if $IPT -I "$c" "$i" $s; then ADDED+=("$c|$s"); i=$((i + 1))
    else undo_added; rm -f "$T"; die "chen luat LOI: $c $s => da go ${#ADDED[@]} luat vua chen, KHONG chen DROP, KHONG ghi rules.v4"; fi
  done < <(specs "$c")
done
ok "da chen ${#ADDED[@]} luat $TAG (${CHAINS[*]})"
if [ "$V4HAS" = 1 ]; then ok "rules.v4 da co luat $TAG tu truoc — khong them trung"; else v4_install "$T"; fi
rm -f "$T"
# [MAJ-1a] cat ket noi IP la bang ss -K (Oracle khong co conntrack)
for ip in $(foreign | awk '{print $1}' | sort -u); do
  $SSK -tn state established "( sport = :${PORTS%% *} and dst $ip )" >/dev/null 2>&1 && echo "   ss -K: $ip"
done
sleep 1; F0=$(foreign); eval "${AS_AFTER_SNAP:-:}"; say "dem lai client la sau ${WAIT_S}s ..."; sleep "$WAIT_S"; F1=$(foreign)
state SAU
for c in "${CHAINS[@]}"; do while IFS= read -r s; do $IPT -C "$c" $s 2>/dev/null || bad "thieu luat $c $s"; done < <(specs "$c"); done; [ "$NF" = 0 ] && ok "du luat $TAG (${CHAINS[*]})"
grep -q -- "$TAG" "$RULES" && ok "rules.v4 co luat $TAG (ben qua reboot)" || bad "rules.v4 khong co $TAG"
timeout 5 bash -c "</dev/tcp/127.0.0.1/${PORTS%% *}" 2>/dev/null && ok "Oracle -> 127.0.0.1:${PORTS%% *} noi duoc" || bad "Oracle -> 127.0.0.1:${PORTS%% *} KHONG noi duoc"
R=$(timeout 40 "${RUNAS[@]}" $SSH_242 "timeout 8 bash -c '</dev/tcp/$PUB/${PORTS%% *}' && echo NC_OK || echo NC_FAIL" 2>/dev/null)
[ "$R" = NC_OK ] && ok "242 -> $PUB:${PORTS%% *} noi duoc (ssh bang ${RUNAS[*]:-user hien tai})" || bad "242 -> $PUB:${PORTS%% *}: ${R:-ssh loi}"
NEWC=$(comm -13 <(sort <<< "$F0") <(sort <<< "$F1") | grep . || true)
OLDC=$(comm -12 <(sort <<< "$F0") <(sort <<< "$F1") | grep . || true)
[ -z "$NEWC" ] || bad "co ket noi MOI tu IP la SAU khi ap luat (luat khong chan duoc?): $(tr '\n' ' ' <<< "$NEWC")"
if [ -n "$OLDC" ]; then
  r2=$(cat /proc/sys/net/ipv4/tcp_retries2 2>/dev/null || echo 15)
  warn "socket CU tu IP la con treo (ss -K khong cat duoc — kernel khong ho tro sock_destroy?) nhung goi da bi DROP: $(tr '\n' ' ' <<< "$OLDC")— tu het sau ~15 phut (tcp_retries2=$r2, khi asd gui) hoac khi client/asd dong ket noi"
elif [ -z "$NEWC" ]; then ok "client Aerospike chi con IP cho phep: $(peers | tr '\n' ' ')"; fi
[ -n "${SSH_CONNECTION:-}" ] && ok "phien ssh hien tai van song (${SSH_CONNECTION%% *} -> cong ${SSH_CONNECTION##* })"
echo "Rollback 1 lenh: sudo bash $0 --rollback"
echo "OCI: nen go them rule ingress TCP 3222 trong Security List / NSG cua VCN (console OCI: Networking > VCN > Security Lists)."
[ "$NF" = 0 ] && { say "=== XONG: cong ${PORTS%% *} da dong voi Internet ($NW canh bao). Log: $LOG"; exit 0; } || { say "=== FAIL ($NF muc, $NW canh bao). Log: $LOG"; exit 1; }
