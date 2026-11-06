#!/usr/bin/env python3
"""Install official pinned Linux x64 analysis tools; requires GitHub release access."""
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import tarfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / '.tools'
DOWNLOADS = TOOLS / 'downloads'


def fetch(url, destination):
    print(f'Downloading {url}', flush=True)
    temporary = destination.with_suffix(destination.suffix + '.partial')
    try:
        with urllib.request.urlopen(url, timeout=120) as response, temporary.open('wb') as output:
            while chunk := response.read(1024 * 1024):
                output.write(chunk)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def asset(repo, tag, name, pinned_hash=None):
    result = subprocess.run(['gh', 'api', f'repos/{repo}/releases/tags/{tag}'],
                            check=True, capture_output=True, text=True)
    release = json.loads(result.stdout)
    entry = next(a for a in release['assets'] if a['name'] == name)
    digest = entry.get('digest') or ''
    expected = pinned_hash or (digest.removeprefix('sha256:') if digest.startswith('sha256:') else None)
    if not expected:
        raise RuntimeError(f'No SHA-256 available for {name}; refusing unverified installation')
    path = DOWNLOADS / name
    if not path.exists():
        fetch(entry['browser_download_url'], path)
    with path.open('rb') as source:
        actual = hashlib.file_digest(source, 'sha256').hexdigest()
    if actual != expected:
        raise RuntimeError(f'SHA-256 mismatch: {path}; remove it before retrying')
    return path


def main():
    if platform.system() != 'Linux' or platform.machine() not in ('x86_64', 'amd64'):
        raise RuntimeError('This installer targets Linux x64 only')
    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    jdk = asset('adoptium/temurin21-binaries', 'jdk-21.0.13+9',
                'OpenJDK21U-jdk_x64_linux_hotspot_21.0.13_9.tar.gz')
    with tarfile.open(jdk) as archive:
        archive.extractall(TOOLS, filter='data')
    asset('1013503897/jadx-headless-mcp', 'v0.7.1', 'jadx-headless-mcp-0.7.1-all.jar',
          '6e5eacf500b64292bfb73c49797c1958f6ee44646e43e868039ae7feb573ff75')
    asset('iBotPeaches/Apktool', 'v3.0.3', 'apktool_3.0.3.jar')
    ghidra = asset('NationalSecurityAgency/ghidra', 'Ghidra_12.1.4_build',
                   'ghidra_12.1.4_PUBLIC_20260921.zip')
    subprocess.run(['unzip', '-q', '-o', str(ghidra), '-d', str(TOOLS)], check=True)
    for executable in [TOOLS / 'ghidra_12.1.4_PUBLIC/support/analyzeHeadless',
                       TOOLS / 'ghidra_12.1.4_PUBLIC/Ghidra/Features/Decompiler/os/linux_x86_64/decompile']:
        executable.chmod(executable.stat().st_mode | 0o111)
    print('Installed. Verify with: npm run rea -- doctor --provider jadx --provider ghidra --json')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        raise SystemExit(f'Installation incomplete: {error}')
