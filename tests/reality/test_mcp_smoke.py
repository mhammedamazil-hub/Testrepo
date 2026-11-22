"""MCP server smoke test for original tools."""
import json
import subprocess
import sys


def mpc_msg(method, params=None, mid=1):
    m = {'jsonrpc': '2.0', 'id': mid, 'method': method}
    if params is not None:
        m['params'] = params
    s = json.dumps(m)
    return f'Content-Length: {len(s)}\r\n\r\n{s}'.encode()


def main():
    data = b''.join([
        mpc_msg('initialize', {}, 1),
        mpc_msg('tools/list', {}, 2),
    ])
    proc = subprocess.run(
        [sys.executable, '-m', 'universal_engine.mcp_server'],
        input=data,
        capture_output=True,
        timeout=15,
    )
    assert proc.returncode == 0, proc.stderr.decode()
    assert b'project_create' in proc.stdout
    assert b'scene_create' in proc.stdout
    assert b'game_create' in proc.stdout
    print('MCP smoke test passed')


if __name__ == '__main__':
    main()