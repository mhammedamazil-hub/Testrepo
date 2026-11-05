"""Install a minimal CPU-only bpy runtime in this restricted Debian sandbox.

Normal workstations: install Blender 4.2 LTS or apt install libxrender1
libxxf86vm1 libxfixes3 libxi6 libxkbcommon0 libsm6 libice6 libgl1 instead.

This fallback creates *uncalled display API* link shims when Debian mirrors
are blocked. It MUST NOT be used for interactive Blender, Eevee, OpenGL or
GPU rendering. Cycles CPU does not use these display functions. No renderer,
Python API, shader, ray tracing or image output function is replaced.
"""
import os, pathlib, re, subprocess, sys

subprocess.run([sys.executable,'-m','pip','install','--break-system-packages','bpy==4.2.23','numpy','pillow','imageio-ffmpeg==0.8.1'],check=True)
# Find bpy without importing the binary extension.
import importlib.util
spec=importlib.util.find_spec('bpy')
so=pathlib.Path(spec.origin)
root=pathlib.Path.home()/'tools'/'headless-libs'
root.mkdir(parents=True,exist_ok=True)
result=subprocess.run(['ldd',str(so)],capture_output=True,text=True,check=True)
missing=re.findall(r'(\S+) => not found',result.stdout)
allowed={'libXrender.so.1','libXxf86vm.so.1','libXfixes.so.3','libXi.so.6','libxkbcommon.so.0','libSM.so.6','libICE.so.6','libGL.so.1'}
if set(missing)-allowed: raise RuntimeError('Non-display libraries missing: '+str(set(missing)-allowed))
(root/'empty.c').write_text('void arena_headless_display_unused(void){}\n')
for lib in missing:
    subprocess.run(['gcc','-shared','-fPIC',str(root/'empty.c'),'-o',str(root/lib)],check=True)
env={**os.environ,'LD_LIBRARY_PATH':str(root)}
p=subprocess.run(['ldd','-r',str(so)],env=env,capture_output=True,text=True)
symbols=sorted(set(re.findall(r'undefined symbol: (\w+)',p.stdout+p.stderr)))
# ldd does not have Python's symbol table. Never shim Py* symbols!
ui=[s for s in symbols if s.startswith(('X','_Xi','glX','gl','xkb_','Smc','Sms','Ice'))]
(root/'ui_stubs.c').write_text('\n'.join('long '+s+'(){return 0;}' for s in ui))
if missing: subprocess.run(['gcc','-shared','-fPIC',str(root/'ui_stubs.c'),'-o',str(root/missing[0])],check=True)
(root/'README.txt').write_text('Headless-only display linker stubs. CPU Cycles only. Never use for a UI or GPU.\n'+'\n'.join(ui))
print('Headless display symbols:',len(ui))
print('Run: LD_LIBRARY_PATH='+str(root)+' OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=2 python scripts/build_scene.py --preview')
subprocess.run([sys.executable,'-c','import bpy; assert bpy.app.background; print(bpy.app.version_string, "background mode verified")'],env=env,check=True)
