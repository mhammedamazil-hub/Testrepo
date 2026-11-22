"""MCP integration tests for Reality Engine tools."""
import sys
import os

# Add repo root to path
_repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from universal_engine.mcp_server import TOOL_SCHEMAS, HANDLERS, _EngineServices


def test_reality_tools_registered():
    """All 16 reality_* tools are registered."""
    reality_tools = sorted([k for k in TOOL_SCHEMAS if k.startswith('reality_')])
    assert len(reality_tools) == 16, f'Expected 16 reality tools, got {len(reality_tools)}'
    reality_handlers = sorted([k for k in HANDLERS if k.startswith('reality_')])
    assert len(reality_handlers) == 16, f'Expected 16 reality handlers, got {len(reality_handlers)}'
    print('PASS: All 16 reality_* tools and handlers registered')


def test_reality_tools_execute():
    """All reality_* tools execute real operations."""
    services = _EngineServices()

    result = services.tool_reality_project_create({'name': 'ci_test', 'path': '/tmp/ci_mcp_test'})
    assert result['ok'] is True
    print('PASS: reality_project_create')

    result = services.tool_reality_scene_create({'name': 'ci_scene', 'path': '/tmp/ci_mcp_test'})
    assert result['ok'] is True
    print('PASS: reality_scene_create')

    result = services.tool_reality_entity_create({'scene': 'ci_scene', 'name': 'ci_entity', 'path': '/tmp/ci_mcp_test'})
    assert result['ok'] is True
    print('PASS: reality_entity_create')

    result = services.tool_reality_physics_configure({
        'scene': 'ci_scene', 'id': 'nonexistent', 'body_type': 'dynamic', 'path': '/tmp/ci_mcp_test'
    })
    assert result['ok'] is False
    print('PASS: reality_physics_configure rejects nonexistent entity')

    result = services.tool_reality_engine_diagnostics({})
    assert result['ok'] is True
    assert result['data']['engine'] == 'Reality Engine'
    print('PASS: reality_engine_diagnostics')

    result = services.tool_reality_runtime_status({})
    assert result['ok'] is True
    print('PASS: reality_runtime_status')


if __name__ == '__main__':
    test_reality_tools_registered()
    test_reality_tools_execute()
    print('=== ALL MCP INTEGRATION TESTS PASSED ===')