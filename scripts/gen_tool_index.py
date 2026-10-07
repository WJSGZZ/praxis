"""Write references/tool-index.md from the server's tool table, so the index can never drift from the tools.

    uv run --locked python -m scripts.gen_tool_index          # rewrite the file
    uv run --locked python -m scripts.gen_tool_index --check  # exit 1 if the file is out of date"""
import argparse
import json
import sys
from pathlib import Path

from scripts import mcp_server

OUT = Path(__file__).resolve().parents[1] / 'references/tool-index.md'


def render() -> str:
    lines = ['# 工具索引', '', '由 `scripts/gen_tool_index.py` 从工具表生成，不要手改。字段后带 * 的必填；`--describe 工具名` 看完整输入格式和一个可运行示例。', '',
             '| 工具 | 字段 | 做什么 |', '|---|---|---|']
    for name, tool in mcp_server.TOOLS.items():
        schema = tool['schema']
        required = schema.get('required', [])
        fields = ', '.join(f'{k}*' if k in required else k for k in schema['properties'])
        description = tool['description'].split('. ')[0].rstrip('.').replace('|', '/')
        lines.append(f'| `{name}` | {fields} | {description} |')
    lines += ['', '调用方式：`uv run --locked python -m scripts.mcp_server --call 工具名 \'{"字段": 值}\'`；Python 入口见 [praxis-explore](../skills/praxis-explore/SKILL.md) 的对照表。', '']
    return '\n'.join(lines)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    text = render()
    if args.check:
        sys.exit(0 if OUT.exists() and OUT.read_text() == text else 1)
    OUT.write_text(text)
    print(json.dumps({'written': str(OUT), 'tools': len(mcp_server.TOOLS)}))
