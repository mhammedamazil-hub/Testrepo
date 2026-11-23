"""MCP and CLI consistency tests — verifies both interfaces use the same backend."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest


def mpc_msg(method, params=None, mid=1):
    """Build a Content-Length framed MCP message."""
    m = {"jsonrpc": "2.0", "id": mid, "method": method}
    if params is not None:
        m["params"] = params
    s = json.dumps(m)
    return f"Content-Length: {len(s)}\r\n\r\n{s}".encode("utf-8")


def parse_responses(output):
    """Parse Content-Length framed MCP responses from raw bytes."""
    responses = []
    pos = 0
    while pos < len(output):
        cl_idx = output.find(b"Content-Length: ", pos)
        if cl_idx == -1:
            break
        cl_end = output.find(b"\r\n", cl_idx)
        if cl_end == -1:
            break
        length = int(output[cl_idx + 16 : cl_end])
        body_start = output.find(b"\r\n\r\n", cl_end) + 4
        if body_start + 4 > len(output):
            break
        body = output[body_start : body_start + length]
        try:
            responses.append(json.loads(body.decode("utf-8")))
        except json.JSONDecodeError:
            responses.append({"_parse_error": body[:200]})
        pos = body_start + length
    return responses


def run_mcp(messages, timeout=30):
    """Send MCP messages and return (responses, returncode, stderr)."""
    stdin_data = b"".join(messages)
    proc = subprocess.run(
        [sys.executable, "-m", "universal_engine.mcp_server"],
        input=stdin_data,
        capture_output=True,
        timeout=timeout,
    )
    return parse_responses(proc.stdout), proc.returncode, proc.stderr


def run_cli(*args, json_mode=True):
    """Run the CLI as a subprocess and return (exit_code, parsed_json_or_text)."""
    argv = list(args)
    if json_mode and "--json" not in argv:
        argv.insert(0, "--json")
    proc = subprocess.run(
        [sys.executable, "-m", "universal_engine"] + argv,
        capture_output=True,
        text=True,
        timeout=30,
        cwd="/home/user/Testrepo",
    )
    try:
        return proc.returncode, json.loads(proc.stdout)
    except json.JSONDecodeError:
        return proc.returncode, proc.stdout


class TestMcpCliConsistency(unittest.TestCase):
    """Verify CLI and MCP produce the same results for the same operations."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_mcp_initialize_and_tools(self):
        """MCP initialize returns valid server info and tool list."""
        responses, rc, _ = run_mcp([
            mpc_msg("initialize", {}, 1),
            mpc_msg("tools/list", {}, 2),
        ])
        self.assertEqual(rc, 0)
        self.assertEqual(len(responses), 2)

        init_resp = responses[0]
        self.assertIn("result", init_resp)
        self.assertEqual(init_resp["result"]["serverInfo"]["name"], "universal-engine-mcp")

        tools_resp = responses[1]
        self.assertIn("result", tools_resp)
        tool_names = [t["name"] for t in tools_resp["result"]["tools"]]
        required = [
            "project_create", "project_inspect", "project_validate",
            "scene_create", "scene_inspect", "node_create", "node_modify",
            "script_create", "asset_import", "physics_configure",
            "game_create", "game_run", "game_stop", "game_test",
            "preview_capture", "adapters_list",
        ]
        for name in required:
            self.assertIn(name, tool_names, f"Missing MCP tool: {name}")

    def test_mcp_project_create_scene_node(self):
        """MCP project_create, scene_create, node_create/modify work end-to-end on universal scenes."""
        responses, rc, _ = run_mcp([
            mpc_msg("initialize", {}, 1),
            mpc_msg("tools/call", {
                "name": "project_create",
                "arguments": {"name": "McpConsistency", "path": self.tmp},
            }, 3),
            mpc_msg("tools/call", {
                "name": "scene_create",
                "arguments": {"name": "Level1", "path": self.tmp},
            }, 4),
            mpc_msg("tools/call", {
                "name": "scene_inspect",
                "arguments": {"name": "Level1", "path": self.tmp},
            }, 5),
            mpc_msg("tools/call", {
                "name": "node_create",
                "arguments": {
                    "scene": "Level1", "type": "CharacterBody3D", "name": "Player",
                    "parent": None, "properties": {"position": [0, 2, 0]},
                    "path": self.tmp,
                },
            }, 6),
            mpc_msg("tools/call", {
                "name": "node_modify",
                "arguments": {
                    "scene": "Level1", "node": "Player",
                    "properties": {"position": [0, 5, 0]},
                    "path": self.tmp,
                },
            }, 7),
            mpc_msg("tools/call", {
                "name": "script_create",
                "arguments": {"name": "Player", "path": self.tmp, "extends": "CharacterBody3D"},
            }, 8),
            mpc_msg("tools/call", {
                "name": "project_validate",
                "arguments": {"path": self.tmp},
            }, 9),
        ])
        self.assertEqual(rc, 0)

        # project_create
        self.assertTrue(responses[1]["result"]["ok"])
        # scene_create
        self.assertTrue(responses[2]["result"]["ok"])
        self.assertEqual(responses[2]["result"]["data"]["scene"], "Level1")
        # scene_inspect
        self.assertTrue(responses[3]["result"]["ok"])
        self.assertEqual(responses[3]["result"]["data"]["scene"], "Level1")
        # node_create
        self.assertTrue(responses[4]["result"]["ok"])
        self.assertEqual(responses[4]["result"]["data"]["node"], "Player")
        # node_modify
        self.assertTrue(responses[5]["result"]["ok"])
        self.assertEqual(responses[5]["result"]["data"]["node"], "Player")
        # script_create
        self.assertTrue(responses[6]["result"]["ok"])
        # project_validate
        self.assertTrue(responses[7]["result"]["ok"])
        self.assertTrue(responses[7]["result"]["data"]["valid"])

        # Verify files exist on disk
        self.assertTrue(os.path.isfile(os.path.join(self.tmp, "universal-engine.json")))
        self.assertTrue(os.path.isfile(os.path.join(self.tmp, "scenes", "Level1.scene.json")))
        self.assertTrue(os.path.isfile(os.path.join(self.tmp, "scripts", "Player.gd")))

    def test_cli_equivalents(self):
        """CLI produces the same results as MCP for the same operations."""
        proj = self.tmp

        # CLI project create
        code, data = run_cli("project", "create", "CliConsistency", "--path", proj)
        self.assertEqual(code, 0)
        self.assertTrue(data["ok"])

        # CLI scene create
        code, data = run_cli("scene", "create", "Level1", "--path", proj)
        self.assertEqual(code, 0)
        self.assertTrue(data["ok"])

        # CLI scene inspect
        code, data = run_cli("scene", "inspect", "Level1", "--path", proj)
        self.assertEqual(code, 0)
        self.assertTrue(data["ok"])
        self.assertEqual(data["data"]["object_count"], 3)

        # CLI validate
        code, data = run_cli("project", "validate", "--path", proj)
        self.assertEqual(code, 0)
        self.assertTrue(data["ok"])
        self.assertTrue(data["data"]["valid"])

        # Verify same files as MCP
        self.assertTrue(os.path.isfile(os.path.join(proj, "universal-engine.json")))
        self.assertTrue(os.path.isfile(os.path.join(proj, "scenes", "Level1.scene.json")))

    def test_error_handling_consistency(self):
        """Both CLI and MCP return proper errors for invalid input."""
        # MCP unknown tool
        responses, rc, _ = run_mcp([
            mpc_msg("initialize", {}, 1),
            mpc_msg("tools/call", {"name": "nonexistent", "arguments": {}}, 3),
        ])
        self.assertEqual(rc, 0)
        self.assertIn("error", responses[1])
        self.assertEqual(responses[1]["error"]["code"], -32601)

        # CLI invalid command
        code, data = run_cli("invalid_command")
        self.assertNotEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
