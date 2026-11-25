# Counts dropouts in 16 bit stereo WAV files: gaps.py take.wav [more.wav ...]
# Loss = gap time / (time of audible signal outside gaps + gap time), sample accurate, windows of 10 ms, gaps removed first.
# The level (-50 dBFS) is measured on the right channel.
import wave,numpy as np,sys
for fn in sys.argv[1:]:
    w=wave.open(fn); assert (w.getnchannels(),w.getsampwidth())==(2,2),fn+': 16 bit stereo only'
    sr=w.getframerate(); a=np.frombuffer(w.readframes(w.getnframes()),dtype="<i2").reshape(-1,2).astype(float)/32768; R=a[:,1]; n=len(R)
    z=(np.abs(a).max(1)==0); b=np.flatnonzero(np.diff(np.r_[0,z.astype(int),0])); W=int(sr*.005)
    lv=lambda s: 20*np.log10(np.sqrt((s**2).mean())+1e-9) if len(s) else -180
    gap=np.zeros(n,bool); cnt=0
    for s,e in zip(b[::2],b[1::2]):
        if .001*sr<=e-s<=.35*sr and lv(R[max(0,s-W):s])>-50 and lv(R[e:e+W])>-50: gap[s:e]=1; cnt+=1
    H=sr//100; act=0
    for i in range(0,n-H,H):
        seg=R[i:i+H][~gap[i:i+H]]
        if len(seg)>H//4 and lv(seg)>-50: act+=len(seg)
    print(f"{fn:14s} {n/sr:6.1f}s gaps {cnt:5d} gap time {gap.sum()/sr:6.2f}s = {100*gap.sum()/n:5.1f}% of take; {100*gap.sum()/(act+gap.sum()):5.1f}% of audible time")
