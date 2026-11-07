"""Read completed production artifacts and publish a separate, continuous preview.
Never dispatches/cancels a render, modifies a scene, or overwrites final outputs.
"""
import argparse
import datetime
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from project_config import WIDTH, HEIGHT, FPS, CHUNK_SIZE, CHUNK_COUNT, FRAME_COUNT


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def api(path, token):
    request = urllib.request.Request('https://api.github.com/' + path, headers={
        'Authorization': 'Bearer ' + token,
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
    })
    with urllib.request.urlopen(request, timeout=90) as response:
        return json.load(response)


def download_artifact(repo, artifact_id, token):
    request = urllib.request.Request(
        f'https://api.github.com/repos/{repo}/actions/artifacts/{artifact_id}/zip',
        headers={'Authorization': 'Bearer ' + token})
    try:
        response = urllib.request.build_opener(NoRedirect()).open(request, timeout=90)
    except urllib.error.HTTPError as error:
        if error.code != 302:
            raise
        location = error.headers['Location']
        error.close()
        # Never forward the GitHub credential to the signed storage URL.
        if not location.startswith('https://'):
            raise RuntimeError('Non-HTTPS artifact redirect')
        with urllib.request.urlopen(location, timeout=180) as response:
            return response.read()
    else:
        with response:
            return response.read()


def contiguous_prefix(artifacts):
    available = {}
    for item in artifacts:
        match = re.fullmatch(r'alpine-segment-(\d+)', item['name'])
        if match and not item.get('expired', False):
            chunk = int(match.group(1))
            if 0 <= chunk < CHUNK_COUNT:
                available[chunk] = item
    selected = []
    while len(selected) in available:
        selected.append(available[len(selected)])
    if not selected:
        raise RuntimeError('No continuous finished opening is available yet')
    return selected, sorted(set(available) - set(range(len(selected))))


def validate_segment(path, chunk):
    info = json.loads(path.with_suffix('.json').read_text())
    start = chunk * CHUNK_SIZE + 1
    end = min(FRAME_COUNT, start + CHUNK_SIZE - 1)
    expected = {'chunk': chunk, 'start': start, 'end': end,
                'source_frames_verified': end - start + 1,
                'decoded_frames': end - start + 1,
                'size': [WIDTH, HEIGHT], 'fps': FPS, 'samples_max': 128}
    for key, value in expected.items():
        if info.get(key) != value:
            raise RuntimeError(f'Invalid segment {chunk}: {key}')
    if hashlib.sha256(path.read_bytes()).hexdigest() != info['sha256']:
        raise RuntimeError(f'Segment {chunk} checksum mismatch')
    if not re.fullmatch('[0-9a-f]{64}', info.get('scene_sha256', '')):
        raise RuntimeError('Invalid scene fingerprint')
    return info


def assemble(paths, video):
    import imageio_ffmpeg
    manifests = [validate_segment(path, chunk) for chunk, path in enumerate(paths)]
    scene_hashes = {item['scene_sha256'] for item in manifests}
    if len(scene_hashes) != 1:
        raise RuntimeError('Mixed scene revisions')
    listing = paths[0].parent / 'partial_concat.txt'
    listing.write_text(''.join(f"file '{path.as_posix()}'\n" for path in paths))
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-hide_banner', '-y',
                    '-f', 'concat', '-safe', '0', '-i', str(listing),
                    '-map', '0:v:0', '-c', 'copy', '-an',
                    '-video_track_timescale', str(FPS * 1000),
                    '-movflags', '+faststart', str(video)], check=True)
    reader = imageio_ffmpeg.read_frames(str(video), pix_fmt='rgb24')
    meta = next(reader)
    count = 0
    hashes = set()
    for frame in reader:
        if len(frame) != WIDTH * HEIGHT * 3:
            raise RuntimeError('Incorrect decoded frame size')
        hashes.add(hashlib.sha256(frame).digest())
        count += 1
    expected = sum(item['decoded_frames'] for item in manifests)
    if (count != expected or len(hashes) != count
            or tuple(meta['size']) != (WIDTH, HEIGHT)
            or abs(meta['fps'] - FPS) > .001
            or abs(meta['duration'] - count / FPS) > .05):
        raise RuntimeError('Partial preview failed full-decode verification')
    return {'status': 'TECHNICAL_PASS', 'kind': 'PARTIAL_PREVIEW_NOT_FINAL_DELIVERY',
            'file': video.name, 'width': WIDTH, 'height': HEIGHT, 'fps': FPS,
            'decoded_frames': count, 'unique_decoded_frames': len(hashes),
            'duration_seconds': count / FPS, 'source_frame_range': [1, count],
            'completed_chunks_included': list(range(len(paths))),
            'scene_sha256': next(iter(scene_hashes)),
            'sha256': hashlib.sha256(video.read_bytes()).hexdigest(),
            'assembly': 'Continuous finished opening; stream-copy, no re-encode',
            'missing_footage_fabricated': False, 'production_render_modified': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=int, required=True)
    args = parser.parse_args()
    repo = os.environ.get('GITHUB_REPOSITORY', 'mhammedamazil-hub/Testrepo')
    token = os.environ['GH_TOKEN']
    artifacts = []
    for page in range(1, 100):
        batch = api(f'repos/{repo}/actions/runs/{args.run}/artifacts?per_page=100&page={page}', token)['artifacts']
        artifacts.extend(batch)
        if len(batch) < 100:
            break
    selected, omitted = contiguous_prefix(artifacts)
    output = ROOT / 'output'
    output.mkdir(exist_ok=True)
    video = output / 'Alpine_Mirror_PARTIAL_1080p60.mp4'
    with tempfile.TemporaryDirectory(prefix='alpine-preview-') as folder:
        paths = []
        for chunk, item in enumerate(selected):
            data = download_artifact(repo, item['id'], token)
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                for suffix in ('.mp4', '.json'):
                    name = f'segment_{chunk:03d}{suffix}'
                    matches = [entry for entry in archive.namelist() if Path(entry).name == name]
                    if len(matches) != 1:
                        raise RuntimeError('Unexpected artifact contents')
                    (Path(folder) / name).write_bytes(archive.read(matches[0]))
            paths.append(Path(folder) / f'segment_{chunk:03d}.mp4')
            print(f'Downloaded completed clip {chunk + 1}/{len(selected)}', flush=True)
        report = assemble(paths, video)
    report.update(source_run=args.run, source_url=f'https://github.com/{repo}/actions/runs/{args.run}',
                  generated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  omitted_noncontiguous_completed_chunks=omitted,
                  target_final_frames=FRAME_COUNT)
    (output / 'partial_preview_validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
