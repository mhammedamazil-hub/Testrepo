"""Audit a real CPU software OpenGL stack, not a physical or CUDA GPU.

Uses a checksummed cache of official Debian packages fetched by the user's
other project's Debian-bookworm CI job. Packages are extracted under .cache,
not installed globally or committed into this repository. No stubs are used.
Optional Python dependencies: moderngl glcontext Pillow.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / '.cache' / 'software-graphics'
RUNTIME = CACHE / 'runtime'
OUT = ROOT / 'docs' / 'research-assets'
SOURCE_REPOSITORY = 'mhammedamazil-hub/3D'
SOURCE_COMMIT = '99f7f1dd0e46ad15e7455a8cc5dfaad0271890bd'


def gh_json(endpoint):
    return json.loads(subprocess.check_output(['gh', 'api', endpoint]))


def raw(item):
    return subprocess.check_output(['gh', 'api', item['url'], '-H', 'Accept: application/vnd.github.raw+json'])


def bootstrap():
    CACHE.mkdir(parents=True, exist_ok=True)
    items = gh_json(f'repos/{SOURCE_REPOSITORY}/contents/vendor/debs?ref={SOURCE_COMMIT}')
    checksums = raw(next(i for i in items if i['name'] == 'SHA256SUMS')).decode()
    expected = {line.split()[1].removeprefix('./'): line.split()[0]
                for line in checksums.splitlines() if line.strip()}
    packages = [i for i in items if i['name'].endswith('.deb')]
    if not packages or any(i['name'] not in expected for i in packages):
        raise RuntimeError('Incomplete official-package cache checksum manifest')
    debs = CACHE / 'debs'
    debs.mkdir(exist_ok=True)

    def fetch(item):
        path = debs / item['name']
        if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != expected[item['name']]:
            path.write_bytes(raw(item))
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected[item['name']]:
            raise RuntimeError('Cached Debian package checksum mismatch: ' + item['name'])
        return path

    with ThreadPoolExecutor(max_workers=4) as pool:
        paths = list(pool.map(fetch, packages))
    RUNTIME.mkdir(exist_ok=True)
    for path in paths:
        subprocess.run(['dpkg-deb', '-x', str(path), str(RUNTIME)], check=True)
    (CACHE / 'provenance.json').write_text(json.dumps({
        'repository': SOURCE_REPOSITORY, 'commit': SOURCE_COMMIT,
        'origin': 'Official Debian bookworm packages; see pinned source workflow and PROVENANCE.txt',
        'package_checksums_verified': expected, 'packages': len(packages),
        'installation': 'Non-system extraction; no maintainer scripts executed; no replacement stubs',
    }, indent=2))
    return len(packages)


def software_environment():
    lib = RUNTIME / 'usr/lib/x86_64-linux-gnu'
    return {**os.environ,
            'LD_LIBRARY_PATH': str(lib),
            'LIBGL_DRIVERS_PATH': str(lib / 'dri'),
            '__EGL_VENDOR_LIBRARY_FILENAMES': str(RUNTIME / 'usr/share/glvnd/egl_vendor.d/50_mesa.json'),
            'LIBGL_ALWAYS_SOFTWARE': '1',
            'EGL_PLATFORM': 'surfaceless',
            'LP_NUM_THREADS': '2'}


def probe():
    import moderngl
    from PIL import Image
    lib = RUNTIME / 'usr/lib/x86_64-linux-gnu'
    context = moderngl.create_standalone_context(
        require=430, backend='egl', libgl=str(lib / 'libGL.so.1'),
        libegl=str(lib / 'libEGL.so.1'))
    renderer = context.info['GL_RENDERER']
    if 'llvmpipe' not in renderer.lower():
        raise RuntimeError('Expected the explicitly selected llvmpipe CPU renderer')
    program = context.program(
        vertex_shader='''#version 330
        in vec2 position; in vec3 color; out vec3 rgb;
        void main() { gl_Position=vec4(position,0.0,1.0); rgb=color; }''',
        fragment_shader='''#version 330
        in vec3 rgb; out vec4 frag;
        void main() { frag=vec4(rgb,1.0); }''')
    buffer = context.buffer(struct.pack('15f', -.8,-.7,1,0,0, .8,-.7,0,1,0, 0,.8,0,0,1))
    mesh = context.vertex_array(program, [(buffer, '2f 3f', 'position', 'color')])
    frame = context.simple_framebuffer((640, 360), components=3)
    frame.use()
    frame.clear(.04, .06, .10, 1)
    mesh.render()
    context.finish()
    image = Image.frombytes('RGB', (640,360), frame.read(components=3)).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    if len(set(image.resize((32,18)).tobytes())) < 20:
        raise RuntimeError('Software graphics readback appears empty')
    OUT.mkdir(parents=True, exist_ok=True)
    image_path = OUT / 'software-opengl-proof.png'
    image.save(image_path)
    compute = context.compute_shader('''#version 430
        layout(local_size_x=64) in;
        layout(std430,binding=0) buffer Numbers { float values[]; };
        void main() { uint i=gl_GlobalInvocationID.x; if(i<256u) values[i]*=values[i]; }''')
    values = [i/16 for i in range(256)]
    storage = context.buffer(struct.pack('256f', *values))
    storage.bind_to_storage_buffer(0)
    compute.run(group_x=4)
    context.memory_barrier()
    result = struct.unpack('256f', storage.read())
    if any(abs(actual-value*value) > 1e-5 for actual,value in zip(result,values)):
        raise RuntimeError('Software compute-shader result mismatch')
    report = {
        'status': 'SOFTWARE_OPENGL_AND_COMPUTE_PROOF_PASS',
        'vendor': context.info['GL_VENDOR'], 'renderer': renderer,
        'opengl_version': context.info['GL_VERSION'], 'version_code': context.version_code,
        'max_texture_size': context.info['GL_MAX_TEXTURE_SIZE'],
        'shader_rasterization': True, 'compute_shader_values_verified': 256,
        'image_sha256': hashlib.sha256(image_path.read_bytes()).hexdigest(),
        'gpu_hardware_added': False, 'execution_device': 'CPU',
        'does_not_establish': ['CUDA/OptiX availability', 'Vulkan compatibility',
                               'Unreal operation', 'GTA-scale real-time performance'],
        'dependency_source_repository': SOURCE_REPOSITORY,
        'dependency_source_commit': SOURCE_COMMIT,
        'dependencies_are_real_libraries_not_stubs': True,
    }
    (OUT / 'software-opengl-proof.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))
    context.release()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--probe', action='store_true')
    arguments = parser.parse_args()
    if arguments.probe:
        probe()
    else:
        print('Verified/extracted Debian packages:', bootstrap(), flush=True)
        subprocess.run([sys.executable, str(Path(__file__).resolve()), '--probe'],
                       env=software_environment(), check=True)
