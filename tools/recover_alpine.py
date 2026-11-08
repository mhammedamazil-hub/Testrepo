"""Preserve completed clips and recover only absent native frames from a frozen scene."""
import argparse
import datetime
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.error
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.assemble_partial_preview import api, download_artifact, validate_segment
from scripts.project_config import CHUNK_COUNT, CHUNK_SIZE, FRAME_COUNT, FPS, WIDTH, HEIGHT

SOURCE = ROOT / 'output' / 'recovery_source'
PLAN = SOURCE / 'recovery_plan.json'
SCENE_FILES = ['Alpine_Mirror.blend', 'scene_manifest.json', 'scene_validation.json']
STILL = 'Alpine_Mirror_1080p.png'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def retry(call):
    for attempt in range(4):
        try:
            return call()
        except urllib.error.HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504) or attempt == 3:
                raise
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if attempt == 3:
                raise
        time.sleep(2 ** attempt)


def artifacts(repo, run, token):
    result = []
    for page in range(1, 101):
        batch = retry(lambda: api(f'repos/{repo}/actions/runs/{run}/artifacts?per_page=100&page={page}', token))['artifacts']
        result.extend(batch)
        if len(batch) < 100:
            return result
    raise RuntimeError('Unexpected artifact pagination size')


def latest(items, name):
    found = [a for a in items if a['name'] == name and not a.get('expired', False)]
    return max(found, key=lambda a: a['id']) if found else None


def extract_named(data, destination, names):
    """Extract only exact expected basenames; never trust ZIP member paths."""
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for name in names:
            if Path(name).name != name:
                raise RuntimeError('Expected basename, not an archive path')
            matches = [n for n in archive.namelist() if Path(n).name == name and not n.endswith('/')]
            if len(matches) != 1:
                raise RuntimeError(f'Missing/ambiguous artifact file: {name}')
            (destination / name).write_bytes(archive.read(matches[0]))


def make_tasks(missing, shard_size=1):
    if not 1 <= shard_size <= 3:
        raise ValueError('Recovery shards must contain at most three native frames')
    if len(set(missing)) != len(missing) or any(not 0 <= c < CHUNK_COUNT for c in missing):
        raise ValueError('Invalid missing clip list')
    tasks = []
    for chunk in sorted(missing):
        first = chunk * CHUNK_SIZE + 1
        last = min(FRAME_COUNT, first + CHUNK_SIZE - 1)
        for part, start in enumerate(range(first, last + 1, shard_size)):
            tasks.append({'shard': f'{chunk:03d}-{part:02d}', 'chunk': chunk,
                          'start': start, 'end': min(last, start + shard_size - 1)})
    if not tasks or len(tasks) > 256:
        raise RuntimeError('Recovery matrix empty or exceeds CI matrix limit; batch explicitly')
    return tasks


def load_plan():
    plan = json.loads(PLAN.read_text())
    if digest(SOURCE / SCENE_FILES[0]) != plan['scene_sha256']:
        raise RuntimeError('Frozen recovery scene changed')
    return plan


def plan_recovery(repo, run, token):
    from PIL import Image
    items = artifacts(repo, run, token)
    source = latest(items, 'alpine-scene')
    still = latest(items, 'alpine-still')
    if source is None or still is None:
        raise RuntimeError('Original scene or still unavailable; do not rebuild/mix scene identities')
    extract_named(retry(lambda: download_artifact(repo, source['id'], token)), SOURCE, SCENE_FILES)
    extract_named(retry(lambda: download_artifact(repo, still['id'], token)), SOURCE, [STILL])
    scene_hash = digest(SOURCE / SCENE_FILES[0])
    manifest = json.loads((SOURCE / 'scene_manifest.json').read_text())
    validation = json.loads((SOURCE / 'scene_validation.json').read_text())
    if (manifest['revision'] != 2 or manifest['fps'] != FPS or manifest['frames'] != FRAME_COUNT
            or manifest['resolution'] != [WIDTH, HEIGHT] or validation['technical_status'] != 'PASS'
            or not all(validation['checks'].values())):
        raise RuntimeError('Wrong/invalid source scene')
    with Image.open(SOURCE / STILL) as image:
        if image.size != (WIDTH, HEIGHT):
            raise RuntimeError('Wrong original still dimensions')
        image.verify()
    available, missing, receipts = [], [], {}
    for chunk in range(CHUNK_COUNT):
        artifact = latest(items, f'alpine-segment-{chunk}')
        if artifact is None:
            missing.append(chunk)
            continue
        names = [f'segment_{chunk:03d}.mp4', f'segment_{chunk:03d}.json']
        extract_named(retry(lambda: download_artifact(repo, artifact['id'], token)), SOURCE / 'segments', names)
        info = validate_segment(SOURCE / 'segments' / names[0], chunk)
        if info['scene_sha256'] != scene_hash:
            raise RuntimeError(f'Original clip {chunk} has a different scene hash')
        available.append(chunk)
        receipts[str(chunk)] = {'artifact_id': artifact['id'], 'sha256': info['sha256']}
        print(f'Preserved original clip {chunk}', flush=True)
    tasks = make_tasks(missing)
    plan = {'source_run': run, 'repository': repo, 'scene_artifact_id': source['id'],
            'still_artifact_id': still['id'], 'scene_sha256': scene_hash,
            'still_sha256': digest(SOURCE / STILL), 'available_chunks': available,
            'missing_chunks': missing, 'original_clip_receipts': receipts,
            'native_frames_to_recover': sum(t['end'] - t['start'] + 1 for t in tasks),
            'tasks': tasks, 'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}
    PLAN.write_text(json.dumps(plan, indent=2) + '\n')
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
            output.write('matrix=' + json.dumps({'include': tasks}, separators=(',', ':')) + '\n')
    print(json.dumps({k: plan[k] for k in ('available_chunks', 'missing_chunks', 'native_frames_to_recover', 'scene_sha256')}, indent=2))


def restore_shard(repo, run, token, shard):
    plan = load_plan()
    task = next((t for t in plan['tasks'] if t['shard'] == shard), None)
    if task is None:
        raise RuntimeError('Unknown recovery shard')
    shutil.copyfile(SOURCE / SCENE_FILES[0], ROOT / 'output' / SCENE_FILES[0])
    if int(os.environ.get('GITHUB_RUN_ATTEMPT', '1')) <= 1:
        return
    existing = latest(artifacts(repo, run, token), f'alpine-recovery-frames-{shard}')
    if existing is None:
        return
    data = retry(lambda: download_artifact(repo, existing['id'], token))
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        files = archive.namelist()
        for frame in range(task['start'], task['end'] + 1):
            names = [f'alpine_{frame:04d}.png', f'alpine_{frame:04d}.render.json']
            if all(sum(Path(n).name == name for n in files) == 1 for name in names):
                extract_named(data, ROOT / 'output' / 'frames', names)
    # render_frames.py independently verifies saved PNGs and their full fingerprints.


def prepare_assembly():
    plan = load_plan()
    output = ROOT / 'output'
    for name in SCENE_FILES + [STILL]:
        shutil.copyfile(SOURCE / name, output / name)
    if digest(output / STILL) != plan['still_sha256']:
        raise RuntimeError('Original still changed')
    segments = output / 'segments'
    segments.mkdir(exist_ok=True)
    for chunk in plan['available_chunks']:
        for suffix in ('.mp4', '.json'):
            name = f'segment_{chunk:03d}{suffix}'
            shutil.copyfile(SOURCE / 'segments' / name, segments / name)
        info = validate_segment(segments / f'segment_{chunk:03d}.mp4', chunk)
        if info['sha256'] != plan['original_clip_receipts'][str(chunk)]['sha256']:
            raise RuntimeError('A preserved clip changed')
    for task in plan['tasks']:
        for frame in range(task['start'], task['end'] + 1):
            receipt = json.loads((output / 'frames' / f'alpine_{frame:04d}.render.json').read_text())
            expected = {'scene_sha256': plan['scene_sha256'], 'frame': frame, 'samples': 128,
                        'percent': 100, 'noise': .03, 'min_samples': 24, 'renderer': '4.2.23 LTS'}
            if any(receipt.get(k) != v for k, v in expected.items()):
                raise RuntimeError(f'Recovered frame {frame} settings/scene mismatch')
    for chunk in plan['missing_chunks']:
        subprocess.run([sys.executable, 'scripts/encode_chunk.py', '--chunk', str(chunk)], cwd=ROOT, check=True)
    for chunk in range(CHUNK_COUNT):
        info = validate_segment(segments / f'segment_{chunk:03d}.mp4', chunk)
        if info['scene_sha256'] != plan['scene_sha256']:
            raise RuntimeError('Mixed recovered scene')


def finish_delivery(repo, run):
    plan = load_plan()
    output = ROOT / 'output'
    delivery = json.loads((output / 'delivery_validation.json').read_text())
    independent = json.loads((output / 'independent_verification.json').read_text())
    if (delivery['status'] != 'TECHNICAL_PASS' or independent['status'] != 'PASS'
            or delivery['scene_sha256'] != plan['scene_sha256']
            or independent['decoded_frames'] != FRAME_COUNT):
        raise RuntimeError('Final verification not complete')
    plan['recovery_run'] = run
    plan['recovery_url'] = f'https://github.com/{repo}/actions/runs/{run}'
    plan['status'] = 'COMPLETE_TECHNICALLY_VERIFIED'
    plan['final_movie_sha256'] = digest(output / 'Alpine_Mirror_1080p_20s.mp4')
    plan['successful_original_clips_reencoded'] = False
    (output / 'recovery_validation.json').write_text(json.dumps(plan, indent=2) + '\n')
    preview = output / 'Alpine_Mirror_PARTIAL_1080p60.mp4'
    preview_url = None
    if preview.exists():
        commit = subprocess.check_output(['git', 'log', '-1', '--format=%H', '--', str(preview.relative_to(ROOT))], cwd=ROOT, text=True).strip()
        if not commit:
            raise RuntimeError('Cannot archive preview safely without a historical commit')
        preview_url = f'https://github.com/{repo}/raw/{commit}/output/{preview.name}'
    readme = ROOT / 'README.md'
    original = readme.read_text()
    tail = original[original.index('## Rebuild locally'):] if '## Rebuild locally' in original else ''
    intro = f'''# Alpine Mirror — verified revision 2

## Completed 20-second 1080p60 delivery

- `output/Alpine_Mirror_1080p_20s.mp4` — **1920×1080, 60 fps, 1,200 native rendered frames, exactly 20 seconds**, H.264, silent.
- `output/Alpine_Mirror_1080p.png` — original revision-2 full-HD 384-sample hero still.
- `output/Alpine_Mirror.blend` — the exact packed, editable Blender 4.2 LTS scene used by all clips.
- `output/delivery_validation.json`, `output/independent_verification.json`, `output/recovery_validation.json` — full-decode, native-frame and recovery provenance reports.

[Successful recovery and final assembly]({plan['recovery_url']}). Preserved {len(plan['available_chunks'])} completed clips byte-for-byte and recovered only {plan['native_frames_to_recover']} missing frames in small jobs. No upscaling, retiming, interpolation or fabricated frames. Final assembly stream-copies compatible clips, without another lossy encode.

**Visual disclosure:** technical verification is not a photorealism certification. This remains a procedural 3D reconstruction with an art-directed CC0 photographic sky and ray-traced volumetric mist; separate artistic review is required.

The earlier full-render workflow hit worker time limits. Use the recovery workflow for this recovery, not an unnecessary restart of all completed clips. Before any future fresh full render, reduce the original workflow's twelve-frame chunks using measured worst-case frame times.

'''
    if preview_url:
        intro += f'[Historical 11.4-second preview]({preview_url}) remains downloadable from its original commit. Its redundant working-tree copy is removed only after the verified full movie is archived, to keep the delivery within storage limits.\n\n'
    readme.write_text(intro + tail)
    note = ROOT / 'docs' / 'RECOVERY_COMPLETE.md'
    note.write_text(f'# Recovery complete\n\nRun: {plan["recovery_url"]}\n\nPreserved {len(plan["available_chunks"])} original clips and recovered {plan["native_frames_to_recover"]} native frames. Full 1,200-frame 1080p60 / 20-second decode and scene-hash checks passed.\n\nScene SHA-256: `{plan["scene_sha256"]}`\n\nMovie SHA-256: `{plan["final_movie_sha256"]}`\n\nTechnical completion is separate from final artistic review.\n')
    print('Final delivery technically verified; ready for archive and publication.', flush=True)


def cleanup(repo, run, token):
    # Only our regenerable raw-frame artifacts from this recovery run, after
    # verified final files have been uploaded AND successfully pushed.
    for item in artifacts(repo, run, token):
        if item['name'].startswith('alpine-recovery-frames-'):
            import urllib.request
            request = urllib.request.Request(
                f'https://api.github.com/repos/{repo}/actions/artifacts/{item["id"]}',
                headers={'Authorization': 'Bearer ' + token}, method='DELETE')
            with urllib.request.urlopen(request, timeout=60):
                pass
            print('Removed archived raw-frame intermediate', item['name'], flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['plan', 'restore', 'assemble', 'finish', 'cleanup'])
    parser.add_argument('--source-run', type=int, default=42202373037)
    parser.add_argument('--shard')
    args = parser.parse_args()
    repo = os.environ.get('GITHUB_REPOSITORY', 'mhammedamazil-hub/Testrepo')
    run = int(os.environ.get('GITHUB_RUN_ID', '0'))
    token = os.environ.get('GH_TOKEN', '')
    if args.mode == 'plan':
        plan_recovery(repo, args.source_run, token)
    elif args.mode == 'restore':
        restore_shard(repo, run, token, args.shard)
    elif args.mode == 'assemble':
        prepare_assembly()
    elif args.mode == 'finish':
        finish_delivery(repo, run)
    else:
        cleanup(repo, run, token)


if __name__ == '__main__':
    main()
