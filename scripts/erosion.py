"""Seeded CPU hydraulic erosion for the hero terrain (Numba, no GPU)."""
import numpy as np
from numba import njit

@njit(cache=True)
def height_gradient(h, x, y):
    ix=int(x); iy=int(y); u=x-ix; v=y-iy
    a=h[iy,ix]; b=h[iy,ix+1]; c=h[iy+1,ix]; d=h[iy+1,ix+1]
    val=a*(1-u)*(1-v)+b*u*(1-v)+c*(1-u)*v+d*u*v
    gx=(b-a)*(1-v)+(d-c)*v; gy=(c-a)*(1-u)+(d-b)*u
    return val,gx,gy

@njit(cache=True)
def hydraulic_erosion(h, drops=360000, seed=9417):
    np.random.seed(seed)
    ny,nx=h.shape
    for droplet in range(drops):
        x=np.random.uniform(3,nx-4); y=np.random.uniform(3,ny-4)
        dx=0.; dy=0.; speed=1.; water=1.; sediment=0.
        for age in range(70):
            ix=int(x); iy=int(y); u=x-ix; v=y-iy
            old,gx,gy=height_gradient(h,x,y)
            dx=dx*.08-gx*.92; dy=dy*.08-gy*.92
            length=(dx*dx+dy*dy)**.5
            if length<1e-8:
                ang=np.random.uniform(0,6.283185307); dx=np.cos(ang); dy=np.sin(ang)
            else: dx/=length; dy/=length
            xx=x+dx; yy=y+dy
            if xx<3 or xx>=nx-4 or yy<3 or yy>=ny-4: break
            new,_,_=height_gradient(h,xx,yy); delta=new-old
            capacity=max(-delta,.015)*speed*water*5.
            if sediment>capacity or delta>0:
                amount=min(delta,sediment) if delta>0 else (sediment-capacity)*.24
                sediment-=amount
                h[iy,ix]+=amount*(1-u)*(1-v); h[iy,ix+1]+=amount*u*(1-v)
                h[iy+1,ix]+=amount*(1-u)*v; h[iy+1,ix+1]+=amount*u*v
            else:
                amount=min((capacity-sediment)*.27,-delta)
                weight=0.
                for oy in range(-2,3):
                    for ox in range(-2,3):
                        weight+=max(0.,2.5-(ox*ox+oy*oy)**.5)
                removed=0.
                for oy in range(-2,3):
                    for ox in range(-2,3):
                        w=max(0.,2.5-(ox*ox+oy*oy)**.5)/weight
                        take=min(h[iy+oy,ix+ox],amount*w)
                        h[iy+oy,ix+ox]-=take; removed+=take
                sediment+=removed
            speed=max(.01,speed*speed-delta*4.)**.5
            water*=.985; x=xx; y=yy
    return h
