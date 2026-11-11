#!/usr/bin/env bash
# test_close_aerospike_3222.sh — test GIA (iptables/ss/iptables-restore gia, rules.v4 tam; KHONG dung firewall that).
#   bash ops/oracle/test/test_close_aerospike_3222.sh /tmp/t_as
HERE=$(cd "$(dirname "$0")/.." && pwd); S=$HERE/close_aerospike_3222.sh
W=${1:?thu muc tam}; rm -rf "$W"; mkdir -p "$W/bin" "$W/log"; PASS=0; FAILN=0
chk() { if eval "$2"; then PASS=$((PASS+1)); echo "  [PASS] $1"; else FAILN=$((FAILN+1)); echo "  [FAIL] $1"; fi; }
cat > $W/bin/ipt <<EOF
#!/bin/bash
F=$W/ipt
case "\$1" in
  -S) [ "\$2" = DOCKER-USER ] && exit 1; grep -- "^-A \$2 " \$F; exit 0;;
  -C) c=\$2; shift 2; grep -qxF -- "-A \$c \$*" \$F;;
  -I) c=\$2; n=\$3; shift 3; l="-A \$c \$*"
      [ -f $W/FAIL_ON ] && [[ "\$l" == *"\$(cat $W/FAIL_ON)"* ]] && { echo "iptables: loi gia" >&2; exit 1; }
      awk -v c="\$c" -v n="\$n" -v l="\$l" '{ if (index(\$0, "-A " c " ") == 1) { k++; if (k == n) { print l; d = 1 } } print } END { if (!d) print l }' \$F > \$F.t && mv \$F.t \$F;;
  -D) c=\$2; shift 2; grep -vxF -- "-A \$c \$*" \$F > \$F.t; mv \$F.t \$F;;
esac
EOF
printf '#!/bin/bash\n[ "$1" = --test ] || exit 2; d=$(cat); grep -q "^\\*filter" <<< "$d" && grep -q "^COMMIT" <<< "$d"\n' > $W/bin/iptr
cat > $W/bin/ss <<EOF
#!/bin/bash
if [ "\$1" = -K ]; then   # ss -K ... dst IP: cat socket (tru khi NO_KILL = kernel khong ho tro)
  [ -f $W/NO_KILL ] && exit 0; ip=\$(echo "\$*" | grep -oE 'dst [0-9.]+' | cut -d' ' -f2); grep -v "^\$ip " $W/estab > $W/estab.t; mv $W/estab.t $W/estab; echo "\$ip" >> $W/killed; exit 0
fi
case "\$*" in
  *-tlnpH*|*-tlnH*) echo 'LISTEN 0 4096 0.0.0.0:3222 0.0.0.0:* users:(("asd",pid=1563,fd=30))';;
  *established*) awk '{print "0 0 10.0.0.236:3222 " \$1 ":" \$2}' $W/estab;;
esac
EOF
chmod +x $W/bin/*
reset() {
  printf '%s\n' '-A INPUT -m state --state RELATED,ESTABLISHED -j ACCEPT' '-A INPUT -p tcp -m state --state NEW -m tcp --dport 22 -j ACCEPT' \
    '-A INPUT -p tcp -m tcp --dport 3222 -j ACCEPT' '-A INPUT -j REJECT --reject-with icmp-host-prohibited' > $W/ipt; cp $W/ipt $W/ipt.orig
  printf '%s\n' '*filter' ':INPUT ACCEPT [0:0]' ':FORWARD ACCEPT [0:0]' '-A INPUT -m state --state RELATED,ESTABLISHED -j ACCEPT' \
    '-A INPUT -p tcp -m state --state NEW -m tcp --dport 22 -j ACCEPT' '-A INPUT -p tcp -m tcp --dport 3222 -j ACCEPT' '-A INPUT -j REJECT' 'COMMIT' > $W/rules.v4
  cp $W/rules.v4 $W/rules.v4.orig; printf '103.157.218.242 54534\n35.241.236.214 47880\n' > $W/estab; rm -f $W/killed $W/rules.v4.bak_* $W/NO_KILL $W/FAIL_ON
}
E() { env IPT="$W/bin/ipt" IPT_RESTORE="$W/bin/iptr" SS_CMD="$W/bin/ss" SS_KILL="$W/bin/ss -K" RULES_V4=$W/rules.v4 AS_LOGDIR=$W/log \
  SSH_242="bash -c" AS_PUB_IP=127.0.0.1 AS_UID=0 SUDO_USER=ubuntu AS_RUNAS=env AS_WAIT_S=1 "$@"; }
echo "== close_aerospike_3222 (gia)"
reset
OUT=$(E bash $S 2>&1); RC=$?
chk "DRY (mac dinh): ke hoach 5 ACCEPT + 1 DROP, rules.v4 moi hop le, bao se cat 35.241.236.214, nhac ss -K; KHONG doi iptables/rules.v4" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'DRY PASS' && [ \$(echo \"\$OUT\" | grep -c 'iptables -I INPUT') = 6 ] && echo \"\$OUT\" | grep -q 'OK   DRY: rules.v4 moi hop le' && echo \"\$OUT\" | grep -q 'se bi cat: 35.241.236.214' && echo \"\$OUT\" | grep -q 'ss -K' && cmp -s $W/ipt $W/ipt.orig && cmp -s $W/rules.v4 $W/rules.v4.orig && echo \"\$OUT\" | grep -q 'Security List'"
OUT=$(echo YES | E AS_UID=1001 bash $S --apply 2>&1); RC=$?
chk "khong root (AS_UID=1001) --apply => DUNG 'Chay lai bang: sudo bash <script> --apply', khong doi gi" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'Chay lai bang: sudo bash .*close_aerospike_3222.sh --apply' && ! echo \"\$OUT\" | grep -q 'Go YES' && cmp -s $W/ipt $W/ipt.orig && cmp -s $W/rules.v4 $W/rules.v4.orig"
OUT=$(echo YES | E SUDO_USER=nobody bash $S --apply 2>&1); RC=$?
chk "user ssh khong co ~/.ssh/known_hosts (SUDO_USER=nobody) => DUNG truoc moi thay doi" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q \"user 'nobody' (SUDO_USER) khong co\" && cmp -s $W/ipt $W/ipt.orig && cmp -s $W/rules.v4 $W/rules.v4.orig"
OUT=$(echo NO | E bash $S --apply 2>&1); RC=$?
chk "--apply khong go YES => huy, khong doi gi" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'Huy' && cmp -s $W/ipt $W/ipt.orig && cmp -s $W/rules.v4 $W/rules.v4.orig"
OUT=$(echo YES | E bash $S --apply 2>&1); RC=$?
chk "--apply YES (root + SUDO_USER=ubuntu => ssh bang ubuntu): 6 luat AS3222_CLOSE o DAU INPUT (ACCEPT truoc, DROP thu 6), luat ssh 22 + luat cu giu nguyen thu tu" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q \"ssh sang 242 bang user 'ubuntu' (theo SUDO_USER)\" && [ \"\$(head -6 $W/ipt | grep -c AS3222_CLOSE)\" = 6 ] && sed -n 6p $W/ipt | grep -q 'j DROP' && sed -n 1p $W/ipt | grep -q 's 127.0.0.0/8' && [ \"\$(tail -n +7 $W/ipt)\" = \"\$(cat $W/ipt.orig)\" ]"
chk "--apply: rules.v4 co 6 dong AS3222_CLOSE truoc -A INPUT dau tien + backup" "[ \"\$(grep -c AS3222_CLOSE $W/rules.v4)\" = 6 ] && [ \"\$(grep -n -m1 '^-A INPUT' $W/rules.v4 | grep -c AS3222_CLOSE)\" = 1 ] && ls $W/rules.v4.bak_AS3222_CLOSE_* >/dev/null 2>&1"
chk "MAJ-1a: ss -K cat 35.241.236.214, KHONG cat 242; hau kiem localhost OK, 242 OK (ssh qua RUNAS), client chi con IP cho phep, XONG 0 canh bao" "grep -qx 35.241.236.214 $W/killed && ! grep -q 103.157 $W/killed && echo \"\$OUT\" | grep -q 'OK   Oracle -> 127.0.0.1:3222' && echo \"\$OUT\" | grep -q 'OK   242 -> .*ssh bang env' && echo \"\$OUT\" | grep -q 'OK   client Aerospike chi con IP cho phep: 103.157.218.242' && echo \"\$OUT\" | grep -q 'XONG: .*(0 canh bao)'"
OUT=$(echo YES | E bash $S --apply 2>&1); RC=$?
chk "--apply lan 2: da co luat live => DUNG, khong them trung" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'da co luat AS3222_CLOSE' && [ \"\$(grep -c AS3222_CLOSE $W/ipt)\" = 6 ]"
OUT=$(echo YES | E bash $S --rollback 2>&1); RC=$?
chk "--rollback YES: go DUNG 6 luat (iptables + rules.v4 tro ve y nguyen ban dau)" "[ $RC = 0 ] && cmp -s $W/ipt $W/ipt.orig && cmp -s $W/rules.v4 $W/rules.v4.orig && echo \"\$OUT\" | grep -q 'ROLLBACK XONG'"
reset
OUT=$(echo YES | E SUDO_USER= bash $S --apply 2>&1); RC=$?
chk "root KHONG co SUDO_USER (sudo -i / su) => ssh bang chu thu muc script ($(stat -c %U $HERE)), ap luat XONG" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q \"ssh sang 242 bang user '$(stat -c %U $HERE)' (theo chu thu muc\" && [ \"\$(grep -c AS3222_CLOSE $W/ipt)\" = 6 ] && echo \"\$OUT\" | grep -q '=== XONG'"
reset; touch $W/NO_KILL
OUT=$(echo YES | E bash $S --apply 2>&1); RC=$?
chk "MAJ-1a: kernel khong ho tro ss -K => socket CU con treo = WARN (kem thoi gian tu het), KHONG FAIL, rc 0" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'WARN socket CU tu IP la con treo.*35.241.236.214' && echo \"\$OUT\" | grep -q 'tu het sau ~15 phut' && echo \"\$OUT\" | grep -q '(1 canh bao)' && ! echo \"\$OUT\" | grep -q '^.*FAIL '"
reset; touch $W/NO_KILL
OUT=$(echo YES | E AS_AFTER_SNAP="echo '34.1.2.3 40001' >> $W/estab" bash $S --apply 2>&1); RC=$?
chk "MAJ-1a: co ket noi MOI tu IP la sau khi ap luat (dem lai sau AS_WAIT_S) => FAIL, rc 1" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'FAIL co ket noi MOI tu IP la SAU khi ap luat.*34.1.2.3'"
reset; echo '172.16.0.0/12' > $W/FAIL_ON
OUT=$(echo YES | E bash $S --apply 2>&1); RC=$?
chk "MIN: chen ACCEPT thu 3 loi => go lai 2 luat da chen, KHONG chen DROP, KHONG ghi rules.v4, rc 1" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'chen luat LOI' && cmp -s $W/ipt $W/ipt.orig && cmp -s $W/rules.v4 $W/rules.v4.orig && ! grep -q 'j DROP.*AS3222\|AS3222.*DROP' $W/ipt && [ \"\$(echo \"\$OUT\" | grep -c 'go lai:')\" = 2 ]"
reset; sed -i '0,/^-A INPUT/s//-A INPUT -s 127.0.0.0\/8 -p tcp -m multiport --dports 3222 -m comment --comment AS3222_CLOSE -j ACCEPT\n-A INPUT/' $W/rules.v4; cp $W/rules.v4 $W/rules.v4.pre
OUT=$(echo YES | E bash $S --apply 2>&1); RC=$?
chk "MIN: rules.v4 da co AS3222_CLOSE => khong them trung (rules.v4 khong doi), luat live van duoc chen" "[ $RC = 0 ] && cmp -s $W/rules.v4 $W/rules.v4.pre && echo \"\$OUT\" | grep -q 'khong them trung' && [ \"\$(grep -c AS3222_CLOSE $W/ipt)\" = 6 ]"
OUT=$(E AS_PORTS="22" bash $S 2>&1); RC=$?
chk "AS_PORTS=22 => DUNG (khong bao gio dung ssh)" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'PORTS chua 22'"
echo "TEST $( [ $FAILN = 0 ] && echo PASS || echo FAIL ) $PASS/$((PASS+FAILN))"
[ $FAILN = 0 ]
