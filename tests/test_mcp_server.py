"""MCP server tests — real JSON-RPC 2.0 communication over stdio."""

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


def run_mcp(messages, timeout=15):
    """Send MCP messages to the server and return parsed responses."""
    stdin_data = b"".join(messages)
    proc = subprocess.run(
        [sys.executable, "-m", "universal_engine.mcp_server"],
        input=stdin_data,
        capture_output=True, timeout=timeout,
    )
    # Parse Content-Length framed responses from raw bytes.
    output = proc.stdout
    responses = []
    pos = 0
    while pos < len(output):
        cl_idx = output.find(b"Content-Length: ", pos)
        if cl_idx == -1:
            break
        cl_end = output.find(b"\r\n", cl_idx)
        if cl_end == -1:
            break
        length = int(output[cl_idx + 16:cl_end])
        body_start = output.find(b"\r\n\r\n", cl_end) + 4
        if body_start + 4 > len(output):
            break
        body = output[body_start:body_start + length]
        try:
            responses.append(json.loads(body.decode("utf-8")))
        except json.JSONDecodeError:
            responses.append({"_parse_error": body[:200]})
        pos = body_start + length
    return responses, proc.returncode, proc.stderr


class TestMcpInitialize(unittest.TestCase):
    def test_initialize(self):
        responses, rc, stderr = run_mcp([mpc_msg("initialize", {}, 1)])
        self.assertEqual(rc, 0)
        self.assertEqual(len(responses), 1)
        r = responses[0]
        self.assertEqual(r["jsonrpc"], "2.0")
        self.assertEqual(r["id"], 1)
        self.assertIn("result", r)
        self.assertEqual(r["result"]["serverInfo"]["name"], "universal-engine-mcp")

    def test_initialized_notification(self):
        responses, rc, stderr = run_mcp([
            mpc_msg("initialize", {}, 1),
            mpc_msg("initialized", {}, 2),  # notification
        ])
        self.assertEqual(rc, 0)
        self.assertEqual(len(responses), 1)  # notification has no response


class TestMcpToolsList(unittest.TestCase):
    def test_tools_list(self):
        responses, rc, _ = run_mcp([
            mpc_msg("initialize", {}, 1),
            mpc_msg("tools/list", {}, 2),
        ])
        self.assertEqual(rc, 0)
        # initialize response + tools/list response
        self.assertEqual(len(responses), 2)
        tools_resp = responses[1]
        self.assertIn("result", tools_resp)
        tools = tools_resp["result"]["tools"]
        tool_names = [t["name"] for t in tools]
        required = [
            "project_create", "project_inspect", "project_validate",
            "scene_create", "scene_inspect", "node_create", "node_modify",
            "script_create", "asset_import", "physics_configure",
            "game_create", "game_run", "game_stop", "game_test",
            "preview_capture", "adapters_list",
        ]
        for name in required:
            self.assertIn(name, tool_names, f"Missing tool: {name}")


class TestMcpToolCalls(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_project_create_tool(self):
        responses, rc, _ = run_mcp([
            mpc_msg("initialize", {}, 1),
            mpc_msg("tools/call", {
                "name": "project_create",
                "arguments": {"name": "McpProj", "path": self.tmp},
            }, 3),
        ])
        self.assertEqual(rc, 0)
        resp = responses[1]
        self.assertIn("result", resp)
        self.assertTrue(resp["result"]["ok"])
        self.assertTrue(os.path.exists(os.path.join(self.tmp, "universal-engine.json")))

    def test_scene_create_and_inspect_tool(self):
        proj = os.path.join(self.tmp, "McpScene")
        os.makedirs(proj, exist_ok=True)
        with open(os.path.join(proj, "universal-engine.json"), "w") as f:
            json.dump({"name": "McpScene", "root": proj}, f)

        responses, rc, _ = run_mcp([
            mpc_msg("initialize", {}, 1),
            mpc_msg("tools/call", {
                "name": "scene_create",
                "arguments": {"name": "Level1", "path": proj},
            }, 3),
            mpc_msg("tools/call", {
                "name": "scene_inspect",
                "arguments": {"name": "Level1", "path": proj},
            }, 4),
        ])
        self.assertEqual(rc, 0)
        # responses[0] = init, [1] = scene_create, [2] = scene_inspect
        create_resp = responses[1]
        self.assertTrue(create_resp["result"]["ok"], create_resp)
        inspect_resp = responses[2]
        self.assertTrue(inspect_resp["result"]["ok"], inspect_resp)
        self.assertEqual(inspect_resp["result"]["data"]["scene"], "Level1")


class TestMcpErrors(unittest.TestCase):
    def test_unknown_tool(self):
        responses, rc, _ = run_mcp([
            mpc_msg("initialize", {}, 1),
            mpc_msg("tools/call", {"name": "nonexistent_tool", "arguments": {}}, 3),
        ])
        self.assertEqual(rc, 0)
        resp = responses[1]
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["code"], -32601)

    def test_not_initialized(self):
        responses, rc, _ = run_mcp([
            mpc_msg("tools/call", {"name": "project_create", "arguments": {}}, 1),
        ])
        self.assertEqual(rc, 0)
        resp = responses[0]
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["code"], -32002)


if __name__ == "__main__":
    unittest.main()
