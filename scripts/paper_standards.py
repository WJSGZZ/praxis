"""Query and validate the venue rules in references/paper-standards.md.

The Markdown file is the single source: agents without a terminal read it directly,
and this script parses its rule tables so that a target venue retrieves its own
rules, the shared scientific core, and the topics still lacking a confirmed rule.

    uv run --locked python -m scripts.paper_standards --venue SIAP
    uv run --locked python -m scripts.paper_standards --venue "Nature" --topic 配色
    uv run --locked python -m scripts.paper_standards --check
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / 'references/paper-standards.md'
COLUMNS = ('ID', '类型', '主题', '规范', '适用条件', '状态', '来源', '查阅')
STATUSES = ('已证实', '已推导', '往届参考', '待确认', '未查到', '项目默认')
TOPICS = ('格式', '分辨率', '尺寸', '字体', '配色', '图注', '编号', '表格', '单位', '误差', '可及性', '复现', '版面')
# Venue type -> aliases a user or task is likely to name. Matching is case-insensitive substring.
VENUES = {
    'core': ('通用', 'core'),
    'siam': ('siam', 'siap', 'sinum', 'sisc', 'siopt', 'siads', '数学期刊'),
    'elsevier': ('elsevier', '爱思唯尔', 'applied mathematical modelling', 'cell press'),
    'ieee': ('ieee', 'transactions on'),
    'aps': ('aps', 'physical review', 'phys. rev', 'prl', '物理评论'),
    'nature': ('nature',),
    'science': ('science', 'aaas'),
    'statistics': ('统计', 'jasa', 'american statistical', 'annals of statistics', 'ims', 'jrss', 'royal statistical'),
    'mcm': ('mcm', 'icm', 'comap', '美赛'),
    'cumcm': ('cumcm', '国赛', '全国大学生数学建模'),
    'zh': ('中文期刊', '学位论文', 'gb/t', '国标', '硕士', '博士', '毕业论文', '学报'),
}
_ROW = re.compile(r'^\|(.+)\|\s*$')
_URL = re.compile(r'https?://[^\s)>\]]+')


def parse(text: str) -> list[dict]:
    """Return every row of every table whose header is exactly COLUMNS."""
    rules, header = [], None
    for line in text.splitlines():
        match = _ROW.match(line.strip())
        if not match:
            header = None
            continue
        cells = [cell.strip() for cell in match.group(1).split('|')]
        if tuple(cells) == COLUMNS:
            header = cells
            continue
        if header is None or set(''.join(cells)) <= set('-: '):
            continue
        if len(cells) != len(COLUMNS):
            raise ValueError(f'Rule row has {len(cells)} cells, expected {len(COLUMNS)}: {line[:60]}')
        rules.append(dict(zip(COLUMNS, cells)))
    return rules


def validate(rules: list[dict]) -> list[str]:
    errors, seen = [], set()
    for rule in rules:
        rid = rule['ID'].strip('`')
        if rid in seen:
            errors.append(f'{rid}: duplicate ID')
        seen.add(rid)
        if rule['类型'] not in VENUES:
            errors.append(f'{rid}: unknown venue type {rule["类型"]!r}')
        elif not rid.startswith(rule['类型'] + '-'):
            errors.append(f'{rid}: ID must start with its venue type')
        if rule['主题'] not in TOPICS:
            errors.append(f'{rid}: unknown topic {rule["主题"]!r}')
        if rule['状态'] not in STATUSES:
            errors.append(f'{rid}: unknown status {rule["状态"]!r}')
        if not rule['规范'] or not rule['适用条件']:
            errors.append(f'{rid}: rule and applicability are required')
        has_url = bool(_URL.search(rule['来源']))
        if rule['状态'] in ('已证实', '待确认', '未查到') and not has_url:
            errors.append(f'{rid}: {rule["状态"]} needs the URL that was read or searched')
        if rule['状态'] == '往届参考' and not ((has_url or '](' in rule['来源'])
                                            and re.search(r'(19|20)\d\d', rule['适用条件'] + rule['来源'])):
            errors.append(f'{rid}: 往届参考 must name the award papers (year, problem) and where they were read')
        if rule['状态'] in ('项目默认', '已推导') and not (has_url or '](' in rule['来源'] or '`' in rule['来源']):
            errors.append(f'{rid}: {rule["状态"]} must name its template, file, computation or source')
        try:
            date.fromisoformat(rule['查阅'])
        except ValueError:
            errors.append(f'{rid}: 查阅 must be an ISO date')
    for venue in VENUES:
        if venue != 'core' and not any(r['类型'] == venue and r['状态'] == '已证实' for r in rules):
            errors.append(f'{venue}: no confirmed rule')
    return errors


def resolve(name: str) -> list[str]:
    """Map a journal, contest or thesis name to venue types; unknown names return []."""
    key = name.strip().lower()
    if key in VENUES:
        return [key]
    def hit(alias):
        if alias.isascii():  # whole words, so that 'ims' does not match 'claims'
            return re.search(r'(?<![a-z])' + re.escape(alias) + r'(?![a-z])', key) is not None
        return alias in key
    return [venue for venue, aliases in VENUES.items() if venue != 'core' and any(hit(a) for a in aliases)]


def query(rules: list[dict], venue: str, topic: str | None = None) -> dict:
    venues = resolve(venue)
    chosen = [r for r in rules if r['类型'] in ('core', *venues) and (topic is None or r['主题'] == topic)]
    confirmed = {r['主题'] for r in chosen if r['类型'] != 'core' and r['状态'] == '已证实'}
    topics = (topic,) if topic else TOPICS
    return {
        'venue': venue, 'venue_types': venues, 'rules': chosen,
        'unconfirmed_topics': [t for t in topics if t not in confirmed],
        'note': ('Unknown venue: read its current author guide; only the core rules apply.' if not venues else
                 'Venue rules outrank the core and any Praxis default. Topics without a confirmed rule '
                 'must be checked in the current author guide or marked as unknown.'),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--venue', help='journal, contest or thesis type, e.g. SIAP, IEEE, 国赛, 学位论文')
    parser.add_argument('--topic', choices=TOPICS)
    parser.add_argument('--check', action='store_true', help='validate the rule tables')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    rules = parse(SOURCE.read_text(encoding='utf-8'))
    if args.check or not args.venue:
        errors = validate(rules)
        print('\n'.join(errors) if errors else f'{len(rules)} rules valid')
        return 1 if errors else 0
    result = query(rules, args.venue, args.topic)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=1))
        return 0
    print(f'{args.venue} -> {", ".join(result["venue_types"]) or "未识别"}')
    for rule in result['rules']:
        print(f'- [{rule["ID"].strip("`")}·{rule["主题"]}·{rule["状态"]}] {rule["规范"]}（{rule["适用条件"]}；{rule["查阅"]}）')
    print('未有已证实规则的主题：' + ('、'.join(result['unconfirmed_topics']) or '无'))
    print(result['note'])
    return 0


if __name__ == '__main__':
    sys.exit(main())
