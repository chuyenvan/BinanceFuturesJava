cd ~/claude_master/res1109/r1_s1
echo "== orch"; grep -v Warning orch.log | tail -2 | cut -c1-200
echo "== t2a"; cat t2a.log
echo "== score"; grep -v Warning score1.log | tail -6 | cut -c1-300
echo "== lock"; pgrep -af 'oracle_heavy' | grep -v pgrep | cut -c1-120
free -m | sed -n 2p; df -h / | tail -1; date
