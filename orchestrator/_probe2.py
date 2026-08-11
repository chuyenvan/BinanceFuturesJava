import struct
f=open('/home/ubuntu/claudedata/wfo_ds_ret2wf_4h_ff/funding.bin','rb')
cnt=struct.unpack('>i',f.read(4))[0]
# skip 80000 records to mid-file
for _ in range(80000):
    struct.unpack('>q',f.read(8)); ln=struct.unpack('>i',f.read(4))[0]; f.read(8*ln)
prev=None; changes=[]; rows=[]
for i in range(300):
    ts=struct.unpack('>q',f.read(8))[0]; ln=struct.unpack('>i',f.read(4))[0]
    arr=f.read(8*ln); first=arr[:8]
    rows.append((ts,ln)); 
    if prev is not None and first!=prev: changes.append(ts)
    prev=first
print('count',cnt)
print('sample ts mod900000:',[r[0]%900000 for r in rows[:6]])
print('snapshot-CHANGE ts mod900000:',[c%900000 for c in changes[:12]])
print('snapshot-CHANGE gap_min:',[(changes[i+1]-changes[i])//60000 for i in range(min(10,len(changes)-1))])
print('arraylens:',[r[1] for r in rows[:20]])
