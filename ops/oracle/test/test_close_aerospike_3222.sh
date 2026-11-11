#!/usr/bin/env bash
# test_close_aerospike_3222.sh — test GIA (iptables/ss/conntrack/iptables-restore gia, rules.v4 tam; KHONG dung firewall that).
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
  -I) c=\$2; n=\$3; shift 3; l="-A \$c \$*"; awk -v c="\$c" -v n="\$n" -v l="\$l" '{ if (index(\$0, "-A " c " ") == 1) { k++; if (k == n) { print l; d = 1 } } print } END { if (!d) print l }' \$F > \$F.t && mv \$F.t \$F;;
  -D) c=\$2; shift 2; grep -vxF -- "-A \$c \$*" \$F > \$F.t; mv \$F.t \$F;;
esac
EOF
printf '#!/bin/bash\n[ "$1" = --test ] || exit 2; d=$(cat); grep -q "^\\*filter" <<< "$d" && grep -q "^COMMIT" <<< "$d"\n' > $W/bin/iptr
cat > $W/bin/ss <<EOF
#!/bin/bash
case "\$*" in
  *-tlnpH*|*-tlnH*) echo 'LISTEN 0 4096 0.0.0.0:3222 0.0.0.0:* users:(("asd",pid=1563,fd=30))';;
  *established*) awk '{print "0 0 10.0.0.236:3222 " \$1 ":" \$2}' $W/estab;;
esac
EOF
cat > $W/bin/ct <<EOF
#!/bin/bash
case "\$1" in
  -L) awk '{print "tcp 6 431999 ESTABLISHED src=" \$1 " dst=10.0.0.236 sport=" \$2 " dport=3222"}' $W/estab;;
  -D) ip=\$(echo "\$*" | grep -oE -- '--orig-src [0-9.]+' | cut -d' ' -f2); grep -v "^\$ip " $W/estab > $W/estab.t; mv $W/estab.t $W/estab; echo "\$ip" >> $W/ct_deleted;;
esac
EOF
chmod +x $W/bin/*
reset() {
  printf '%s\n' '-A INPUT -m state --state RELATED,ESTABLISHED -j ACCEPT' '-A INPUT -p tcp -m state --state NEW -m tcp --dport 22 -j ACCEPT' \
    '-A INPUT -p tcp -m tcp --dport 3222 -j ACCEPT' '-A INPUT -j REJECT --reject-with icmp-host-prohibited' > $W/ipt; cp $W/ipt $W/ipt.orig
  printf '%s\n' '*filter' ':INPUT ACCEPT [0:0]' ':FORWARD ACCEPT [0:0]' '-A INPUT -m state --state RELATED,ESTABLISHED -j ACCEPT' \
    '-A INPUT -p tcp -m state --state NEW -m tcp --dport 22 -j ACCEPT' '-A INPUT -p tcp -m tcp --dport 3222 -j ACCEPT' '-A INPUT -j REJECT' 'COMMIT' > $W/rules.v4
  cp $W/rules.v4 $W/rules.v4.orig; printf '103.157.218.242 54534\n34.40.185.188 38364\n' > $W/estab; rm -f $W/ct_deleted $W/rules.v4.bak_*
}
E() { env IPT="$W/bin/ipt" IPT_RESTORE="$W/bin/iptr" CONNTRACK="$W/bin/ct" SS_CMD="$W/bin/ss" RULES_V4=$W/rules.v4 AS_LOGDIR=$W/log \
  SSH_242="bash -c" AS_PUB_IP=127.0.0.1 NO_ROOT_OK=1 "$@"; }
echo "== close_aerospike_3222 (gia)"
reset
OUT=$(E bash $S 2>&1); RC=$?
chk "DRY (mac dinh): ke hoach 5 ACCEPT + 1 DROP, rules.v4 moi hop le, bao se cat 34.40.185.188; KHONG doi iptables/rules.v4" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'DRY PASS' && [ \$(echo \"\$OUT\" | grep -c 'iptables -I INPUT') = 6 ] && echo \"\$OUT\" | grep -q 'OK   DRY: rules.v4 moi hop le' && echo \"\$OUT\" | grep -q 'se bi cat: 34.40.185.188' && cmp -s $W/ipt $W/ipt.orig && cmp -s $W/rules.v4 $W/rules.v4.orig && echo \"\$OUT\" | grep -q 'Security List'"
OUT=$(echo NO | E bash $S --apply 2>&1); RC=$?
chk "--apply khong go YES => huy, khong doi gi" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'Huy' && cmp -s $W/ipt $W/ipt.orig && cmp -s $W/rules.v4 $W/rules.v4.orig"
OUT=$(echo YES | E bash $S --apply 2>&1); RC=$?
chk "--apply YES: 6 luat AS3222_CLOSE o DAU INPUT (ACCEPT truoc, DROP thu 6), luat ssh 22 + luat cu giu nguyen thu tu" "[ $RC = 0 ] && [ \"\$(head -6 $W/ipt | grep -c AS3222_CLOSE)\" = 6 ] && sed -n 6p $W/ipt | grep -q 'j DROP' && sed -n 1p $W/ipt | grep -q 's 127.0.0.0/8' && [ \"\$(tail -n +7 $W/ipt)\" = \"\$(cat $W/ipt.orig)\" ]"
chk "--apply: rules.v4 co 6 dong AS3222_CLOSE truoc -A INPUT dau tien + backup; conntrack cat 34.40.185.188, KHONG cat 242" "[ \"\$(grep -c AS3222_CLOSE $W/rules.v4)\" = 6 ] && [ \"\$(grep -n -m1 '^-A INPUT' $W/rules.v4 | grep -c AS3222_CLOSE)\" = 1 ] && ls $W/rules.v4.bak_AS3222_CLOSE_* >/dev/null 2>&1 && grep -qx 34.40.185.188 $W/ct_deleted && ! grep -q 103.157 $W/ct_deleted"
chk "--apply hau kiem: localhost 3222 OK, 242 OK, client chi con IP cho phep, XONG" "echo \"\$OUT\" | grep -q 'OK   Oracle -> 127.0.0.1:3222' && echo \"\$OUT\" | grep -q 'OK   242 -> ' && echo \"\$OUT\" | grep -q 'OK   client Aerospike chi con IP cho phep: 103.157.218.242' && echo \"\$OUT\" | grep -q '=== XONG'"
OUT=$(echo YES | E bash $S --apply 2>&1); RC=$?
chk "--apply lan 2: da co luat => DUNG, khong them trung" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'da co luat AS3222_CLOSE' && [ \"\$(grep -c AS3222_CLOSE $W/ipt)\" = 6 ]"
OUT=$(echo YES | E bash $S --rollback 2>&1); RC=$?
chk "--rollback YES: go DUNG 6 luat (iptables + rules.v4 tro ve y nguyen ban dau)" "[ $RC = 0 ] && cmp -s $W/ipt $W/ipt.orig && cmp -s $W/rules.v4 $W/rules.v4.orig && echo \"\$OUT\" | grep -q 'ROLLBACK XONG'"
OUT=$(E AS_PORTS="22" bash $S 2>&1); RC=$?
chk "AS_PORTS=22 => DUNG (khong bao gio dung ssh)" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'PORTS chua 22'"
echo "TEST $( [ $FAILN = 0 ] && echo PASS || echo FAIL ) $PASS/$((PASS+FAILN))"
[ $FAILN = 0 ]
