#!/bin/bash
# GOLIVE_QUARTERLY: MTM DEV roi HO, tuan tu (RAM)
cd ~/claude_master/vz_e1_wt/research/golive_quarterly
WK=~/claude_master/golive_quarterly_wk
python3 mtm_dev.py > $WK/mtm_dev.log 2>&1; echo "dev rc=$?" >> $WK/pipe.log
python3 mtm_ho.py > $WK/mtm_ho.log 2>&1; echo "ho rc=$?" >> $WK/pipe.log
