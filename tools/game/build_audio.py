"""Generate small original loopable ambience/motor WAVs; no paid assets."""
from pathlib import Path
import wave
import numpy as np

OUT=Path(__file__).resolve().parents[2]/'game/assets'
OUT.mkdir(parents=True,exist_ok=True)
rate=16000
rng=np.random.default_rng(1907)
t=np.arange(rate*12)/rate
frequencies=np.fft.rfftfreq(len(t),1/rate)
noise=np.fft.rfft(rng.normal(size=len(t)))
noise*=np.exp(-(frequencies/680)**2)*(1-np.exp(-(frequencies/45)**2))
wind=np.fft.irfft(noise,n=len(t))*(.75+.25*np.sin(t*np.pi/6))
wind=wind/max(abs(wind))*.52
# Sparse synthetic bird chirps; all audio is original procedural synthesis.
for start in [2.2,6.8,9.4]:
 phase=t-start
 mask=(phase>=0)&(phase<.22)
 wind[mask]+=.10*np.sin(2*np.pi*(2300*phase[mask]+900*phase[mask]**2))*np.sin(np.pi*phase[mask]/.22)**2
motor_t=np.arange(rate//2)/rate
motor=np.tanh(.7*np.sin(2*np.pi*72*motor_t)+.24*np.sin(2*np.pi*144*motor_t)+.14*np.sin(2*np.pi*216*motor_t))*.7
for name,data in [('wind',wind),('motor',motor)]:
 with wave.open(str(OUT/(name+'.wav')),'wb') as f:
  f.setnchannels(1);f.setsampwidth(2);f.setframerate(rate)
  f.writeframes((np.clip(data,-1,1)*32767).astype('<i2').tobytes())
 print('Generated',name,len(data)/rate,'seconds')
