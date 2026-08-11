import struct
D="/home/ubuntu/claudedata/wfo_ds_ret2wf_4h_ff/"
def rd(path, kind, n=10, skip=0):
    with open(path,'rb') as f:
        cnt=struct.unpack('>i',f.read(4))[0]
        for _ in range(skip):
            f.read(8)
            if kind=='market': f.read(12)
            elif kind=='pred': f.read(8)
            else:
                ln=struct.unpack('>i',f.read(4))[0]; f.read(8*ln)
        out=[]
        for _ in range(n):
            ts=struct.unpack('>q',f.read(8))[0]
            if kind=='market': f.read(12); out.append((ts,None))
            elif kind=='pred': f.read(8); out.append((ts,None))
            else:
                ln=struct.unpack('>i',f.read(4))[0]; f.read(8*ln); out.append((ts,ln))
    return cnt,out
for name,fn,kind,skip in [("MARKET","market.bin","market",1000000),("PRED_GATE","pred.bin","pred",1000000),("FUNDING_SEL","funding.bin","fund",80000)]:
    cnt,ts=rd(D+fn,kind,10,skip)
    tss=[t[0] for t in ts]
    print("==",name,"count=",cnt)
    print("  ts[0..3]:",tss[:4])
    print("  mod900000(15m):",[t%900000 for t in tss[:8]])
    print("  mod60000(1m):",[t%60000 for t in tss[:8]])
    unit = 60000 if kind!='fund' else 60000
    print("  diffs_min:",[(tss[i+1]-tss[i])//60000 for i in range(len(tss)-1)])
    if kind=='fund':
        print("  arraylens:",[t[1] for t in ts])
