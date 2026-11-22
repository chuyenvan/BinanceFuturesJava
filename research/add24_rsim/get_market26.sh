#!/bin/bash
S=/dev/shm/add24/b
cd $S/kg_chain2 && ~/.local/bin/kaggle kernels output chuyendinh/ho4p1-chain-y26 -p $S/kg_chain2 > /dev/null 2>&1
md5sum $S/kg_chain2/out/market.bin
python3 - <<'PY'
import struct, numpy as np
from datetime import datetime, timezone, timedelta
TZ7=timezone(timedelta(hours=7))
raw=open('/dev/shm/add24/b/kg_chain2/out/market.bin','rb').read(); n=struct.unpack('>i',raw[:4])[0]
a=np.frombuffer(raw[4:4+n*20],dtype=np.dtype([('ts','>i8'),('d','>f4'),('u','>f4'),('d15','>f4')]))
lo=int(datetime(2025,12,25,tzinfo=TZ7).timestamp()*1000); hi=int(datetime(2026,9,30,23,59,tzinfo=TZ7).timestamp()*1000)
b=a[(a['ts']>=lo)&(a['ts']<=hi)]
np.save('/dev/shm/add24/b/l5/market26.npy', np.array(b))
print('kept',len(b), int(b['ts'].min()), int(b['ts'].max()))
PY
rm -rf $S/kg_chain2
