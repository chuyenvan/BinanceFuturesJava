B=/home/ubuntu/java/devrun
printf "%-22s %9s %8s %-46s %s\n" RUN EQUITY LENH BINS MTIME
for d in $(ls -d $B/*/ 2>/dev/null); do
  T=$(basename $d)
  L=$d/logs/sim.out
  [ -f "$L" ] || continue
  EQ=$(grep -a 'done:' $L 2>/dev/null | tail -1 | grep -oE 'b:[0-9-]+' | tr -d 'b:')
  N=$(grep -a 'done:' $L 2>/dev/null | tail -1 | grep -oE 'done:[0-9]+/[0-9]+' | cut -d/ -f2)
  BI=$(grep -aoE 'bins\.dir=[^ ]+' $L 2>/dev/null | head -1 | cut -d= -f2)
  [ -z "$BI" ] && BI=$(grep -aoE 'fundingPredDir=[^ ]+' $d/logs/*.out 2>/dev/null | head -1 | cut -d= -f2)
  [ -z "$BI" ] && BI="(khong ghi trong log)"
  M=$(stat -c %y $L | cut -c1-16)
  printf "%-22s %9s %8s %-46s %s\n" "$T" "${EQ:--}" "${N:--}" "$(basename $BI)" "$M"
done | sort -k2 -n -r
