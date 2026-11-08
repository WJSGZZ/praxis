"""Emit a bounded instruction packet from exact existing document regions.

No network, model execution, source mutation or implicit detail loading. The
--overlay option reviews an uninstalled candidate against an unchanged bundle.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import posixpath
from pathlib import Path
import re
import sys

LIMIT = 9390
CORE_BEGIN = '<!-- praxis:core:start -->\n'
CORE_END = '<!-- praxis:core:end -->'
DETAIL_BEGIN = '<!-- praxis:details:start -->\n'
DETAIL_END = '<!-- praxis:details:end -->'
ROLES = ('model', 'compute', 'verify', 'report')
PHASE_GUIDES = {
    'model': ('methods', 'modeling-gate', 'automation'),
    'compute': ('methods', 'modeling-gate', 'automation'),
    'verify': ('methods', 'automation'),
    'report': ('methods', 'writing', 'automation'),
}
STAGES = (*ROLES, 'contest', 'research')
REQUIRED_DETAILS = {'research': ('research',)}
CONTEST_GUIDES = ('contest-paper-checklist', 'contest-delivery')
# Details are explicit choices or a declared stage requirement, never recursive.
DETAILS = {
    'environment-api': ('references/automation.md', '@intro', '定位实际工具/环境/权限范围或runtime_info诊断'),
    'case-choice': ('references/automation.md', '先判断要不要走案例系统', '已有可复现链或是否建案例需要取舍'),
    'parallel-budget': ('references/automation.md', '并行计算的预算', '准备并行计算前核资源与小样本计时'),
    'case-intake': ('references/automation.md', '建立案例', '首次接收文件/编码/目录/延后审计接口不清'),
    'content-boundary': ('references/automation.md', '内容理解不是脚本替代的', '机器门与题意/独立性判断的职责不清'),
    'information-api': ('references/automation.md', '按信息截点映射版本', '多版本预测或信息截点映射'),
    'math-results': ('references/automation.md', '数学工具的结果契约', '调用数学工具前核返回/保证/范围'),
    'run-api': ('references/automation.md', '运行与接续', '运行参数/快照/失败/过期或接续接口不清'),
    'writing-api': ('references/automation.md', '写作连接', '跨多个交付诊断接口、需完整写作API；不用于默认入门'),
    'feedback-api': ('references/automation.md', '可选运行反馈', '用户选择保存运行反馈'),
    'live-case-api': ('references/automation.md', '活案例：字段绑定、依赖与局部更新', '选择活案例字段/依赖/局部更新操作'),
    'convergence': ('references/convergence.md', None, '正文/附录取舍或整稿收敛仍不清'),
    'data': ('references/data-computing.md', None, '数据口径/连接/信息版本缺口'),
    'tasks': ('references/tasks-template.md', None, '任务记录结构不清，需要骨架'),
    'tools': ('references/model-library.md', None, '方法/工具适用范围或既有实现不明'),
    'scientific-writing': ('references/scientific-writing.md', None, '局部学术论证/公式解释需要专项修订'),
    'literature': ('references/literature-review.md', None, '需要综述而非普通来源核读'),
    'research': ('references/research-mode.md', None, '任务为研究而非完整竞赛'),
    'defense': ('references/defense-coaching.md', None, '实际共同研究或答辩准备'),
    'capabilities': ('references/capabilities.md', None, '请求超出四主责或需要专业分工'),
    'methods-failure': ('references/methods.md', '失败回到原因所在的环节', '无法确定失败应退回哪个阶段'),
    'methods-records': ('references/methods.md', '工作单元与记录', '跨案例依赖或任务ID记录不清'),
    'methods-models': ('references/methods.md', '模型与验证一起选择', '已选模型需要对应基线/升级/核查速查'),
    'methods-assumptions': ('references/methods.md', '假设、理由与结论范围', '实质前提用途/失效分析仍不清'),
    'methods-evidence': ('references/methods.md', '证据的层次', '证明辅助性质或独立证据的覆盖范围不清'),
    'methods-stop': ('references/methods.md', '停止深挖与交付', '预算中断或候选/有效版本接续不清'),
    'methods-change': ('references/methods.md', '根因修复与全文变更影响', '跨章节变更影响/重算范围仍不清'),
    'methods-learning': ('references/methods.md', '吸收外部方法的统一规则', '拟引入外部方法或新增永久步骤'),
    'writing-name': ('references/writing.md', '正式报告文件命名', '改名或候选/正式文件管理问题'),
    'writing-chinese-english': ('references/writing.md', '中文论文与英文论文各按自己的习惯写', '目标语言术语/句法/格式自然度问题'),
    'writing-argument': ('references/writing.md', '论证先于润色', '主线/章节论证仍不清'),
    'writing-closeout': ('references/writing.md', '接收与交付', '全文联核/引文/PDF文本诊断仍有疑点'),
    'delivery-style': ('references/contest-delivery.md', '共享模板与实际成品', '样式漂移/特殊组件/历史版式问题'),
    'delivery-submit': ('references/contest-delivery.md', '披露与提交结构', '提交对象/附件/支撑包差异不清'),
    'gate-fields': ('references/modeling-gate.md', None, '字段格式不清或契约门禁报错'),
    'paper-components': ('references/contest-paper-checklist.md', None, '需要表格/Memo格式示例或检查组件缺项'),
    'writing-language': ('references/writing.md', '语言专项：先冻结含义，再分别写作', '仅语言修订/自然度问题'),
    'writing-sources': ('references/writing.md', '来源服务于具体论断', '需要检索/核读外部来源'),
    'writing-figures': ('references/writing.md', '论文骨架、验证与图表', '图题/证明/参数解释或章节编辑缺口'),
    'delivery-api': ('references/automation.md', '竞赛模板与组件 API', '特殊组件或编译/冻结接口及报错无法由核心解决'),
    'reader-api': ('references/automation.md', '当前交付的论文诊断（全部先告警）', '独立读者包字段/诊断接口不清'),
    'model-api': ('references/automation.md', '模型与验证器', '模型/验证器接口不清或运行契约报错'),
    'requirements-api': ('references/automation.md', '数值任务的证据索引', 'requirements/evidence接口不清'),
    'workflow-api': ('references/automation.md', '可选任务协调', '选择多轮workflow且其审阅字段/经验连接不清'),
    'intake-api': ('references/automation.md', '接收 Word 和 Excel 附件', '复杂Word/Excel附件、对象抽取缺失'),
    'routes': ('references/structure-discovery.md', None, '结构/路线未知、常规基线与备选无法回答'),
    'math': ('references/mathematical-reasoning.md', None, '表示/参数可辨识性/界/外推保证缺口'),
    'domain': ('references/domain-models.md', None, '领域机制/量级无法由现有契约确认'),
    'foundations': ('references/scientific-foundations.md', None, '数值/统计/不确定性检查细节缺口'),
    'review': ('references/review-protocol.md', None, '重要评语需复现并判断实际影响'),
    'figures': ('references/visualization.md', None, '具体制图/图例/空间数据/最终字号问题'),
    'contest-profile': ('references/contest-delivery.md', '届次、格式与阅读文件', '非默认赛事或需要核官方规范与项目选择'),
}


def stage_sources(stage):
    """One canonical resource spec for execution and the offline index."""
    if stage not in STAGES:
        raise ValueError('Unknown stage')
    role_names = ROLES if stage in ('contest', 'research') else (stage,)
    paths = [('SKILL.md', 'full', None)]
    paths += [(f'skills/praxis-{r}/SKILL.md', 'full', None) for r in role_names]
    guides = tuple(dict.fromkeys(g for r in role_names for g in PHASE_GUIDES[r]))
    if stage == 'contest':
        guides += CONTEST_GUIDES
    paths += [(f'references/{g}.md', 'core', None) for g in guides]
    paths += [('references/integrity.md', 'full', None),
              ('references/learning-loop.md', 'section', '同题资料与接触范围')]
    return paths


def render_index():
    """Render a deterministic source-layout Markdown index without reading files."""
    def link(relative):
        target = posixpath.relpath(relative, 'references')
        return f'[{relative}]({target})'

    lines = [
        '# 指令阶段与按需细则索引', '',
        '由 `scripts/instruction_packet.py --print-index` 从运行时资源定义生成；勿手工修改。', '',
        '无终端时按下表直接读取文件与指定区段。core 指唯一 '
        '`<!-- praxis:core:start -->` 至 `<!-- praxis:core:end -->` 内的正文；'
        '全文包括技能头信息。章节指同名标题及其下级内容，至下一个同级或更高标题。', '',
        '每阶段均包含完整 integrity 安全文与 learning-loop 的“同题资料与接触范围”节。'
        '研究阶段另外必读 research 原文，不继承竞赛清单或 MCM current 命令；'
        '竞赛阶段才增加竞赛清单与交付核心。', '',
        '公共核心限制9390字符；研究额外必读与条件细则另计，研究全部阅读不受此数字代表。'
        '无终端或工具不支持选区时，实际加载量未知；如读取了更多正文须如实计入，'
        '不能声称已运行、已精确限量或已通过执行检查。', '',
        '普通链接不自动递归；实际缺口出现时按本索引继续选择细则，并记录加载。', '',
        '## 阶段必读', '', '| 阶段 | 文件 | 范围 |', '|---|---|---|']
    for stage in STAGES:
        for relative, mode, heading in stage_sources(stage):
            scope = {'full': '全文', 'core': 'core', 'section': f'章节：{heading}'}[mode]
            lines.append(f'| {stage} | {link(relative)} | {scope} |')
        for key in REQUIRED_DETAILS.get(stage, ()):
            relative, heading, _ = DETAILS[key]
            scope = f'章节：{heading}' if heading else '全文'
            lines.append(f'| {stage} | {link(relative)} | 额外必读 detail `{key}`；{scope} |')
    lines += ['', '## 条件细则', '',
              '只有对应缺口或明确阶段要求才读取；先选ID，再按真实文件/标题取文。'
              '被core/details分区的文件，细则取details区；标题未指定时取整个细则区，'
              '未分区的文件取全文；`@intro`取文件开头至首个二级标题前。', '',
              '| ID | 文件 | 标题/范围 | 触发 |', '|---|---|---|---|']
    for key, (relative, heading, trigger) in DETAILS.items():
        scope = heading or '全文/整个details区'
        lines.append(f'| `{key}` | {link(relative)} | {scope} | {trigger} |')
    return '\n'.join(lines) + '\n'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _exported_role_source(bundle, relative):
    """Resolve only the four fixed roles in an authenticated official layout."""
    roles = {f'skills/praxis-{role}/SKILL.md' for role in ROLES}
    core = bundle.resolve()
    if relative not in roles or core.name != 'praxis' or core.parent.name != 'skills':
        raise ValueError(f'Outside bundle: {relative}')
    skills = core.parent
    receipt_path = skills.parent / 'build-receipt.json'
    if receipt_path.is_symlink():
        raise ValueError('Symlinked export receipt')
    if (core / 'SKILL.md').is_symlink():
        raise ValueError('Symlinked export core identity')
    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    if not isinstance(receipt, dict):
        raise ValueError('Invalid export receipt')
    hashes = receipt.get('files_sha256', {})
    if (receipt.get('format') != 'praxis-plugin-export-v1'
            or receipt.get('name') != 'praxis' or not isinstance(hashes, dict)
            or not roles.issubset(hashes)
            or hashes.get('skills/praxis/SKILL.md') != digest((core / 'SKILL.md').read_bytes())):
        raise ValueError('Unmanaged export skills collection')
    role = relative.split('/')[1]
    path = skills / role / 'SKILL.md'
    # Containment in skills alone would admit another role or arbitrary neighbor.
    # Require the exact regular file and directory, then bind its final bytes.
    if path.parent.is_symlink() or path.is_symlink() or path.resolve() != path:
        raise ValueError(f'Outside managed role: {relative}')
    raw = path.read_bytes()
    if hashes[relative] != digest(raw):
        raise ValueError(f'Export role differs from receipt: {relative}')
    return path, raw


def read_source(bundle, overlay, relative):
    # Only canonical logical resource identities may reach either layout.
    resource = Path(relative)
    if resource.is_absolute() or '..' in resource.parts or resource.as_posix() != relative:
        raise ValueError(f'Outside bundle: {relative}')
    candidate = overlay / relative if overlay is not None else None
    use_overlay = candidate is not None and (candidate.exists() or candidate.is_symlink())
    path = candidate if use_overlay else bundle / relative
    root = overlay if use_overlay else bundle
    resolved = path.resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError(f'Outside bundle: {relative}')
    if not use_overlay and not path.exists() and not path.is_symlink():
        path, raw = _exported_role_source(bundle, relative)
        resolved = path.resolve()
    else:
        raw = path.read_bytes()
    return raw.decode('utf-8'), {'path': relative, 'resolved_path': str(resolved),
                                'source_sha256': digest(raw)}


def marker_region(text, begin, end):
    if text.count(begin) != 1 or text.count(end) != 1:
        raise ValueError(f'Expected one explicit region: {begin.strip()}')
    prefix, remainder = text.split(begin, 1)
    region, suffix = remainder.split(end, 1)
    if end in prefix or begin in suffix:
        raise ValueError('Reversed or nested instruction markers')
    return region


def _headings(lines):
    """CommonMark-style ATX headings outside backtick or tilde fences."""
    fence = None
    for index, line in enumerate(lines):
        raw = line.rstrip('\r\n')
        marker = re.match(r" {0,3}(`{3,}|~{3,})(.*)$", raw)
        if fence is not None:
            if (marker and marker[1][0] == fence[0] and len(marker[1]) >= fence[1]
                    and not marker[2].strip(' \t')):
                fence = None
            continue
        if marker and (marker[1][0] != '`' or '`' not in marker[2]):
            fence = (marker[1][0], len(marker[1]))
            continue
        heading = re.match(r' {0,3}(#{1,6})[ \t]+(.+?)(?:[ \t]+#+)?[ \t]*$', raw)
        if heading:
            yield index, len(heading[1]), heading[2]


def section_region(text, title):
    lines = text.splitlines(keepends=True)
    headings = list(_headings(lines))
    if title == '@intro':
        stop = next((i for i, level, _ in headings if level == 2), len(lines))
        return ''.join(lines[:stop])
    starts = [(i, level) for i, level, name in headings if name == title]
    if len(starts) != 1:
        raise ValueError(f'Expected exactly one heading: {title}')
    start, level = starts[0]
    stop = next((i for i, depth, _ in headings if i > start and depth <= level), len(lines))
    return ''.join(lines[start:stop])


FRONTMATTER = re.compile(r'\A---\n.*?\n---\n', re.S)


def strip_frontmatter(text):
    """Hosts route on the YAML description; the packet carries only the body."""
    return FRONTMATTER.sub('', text, count=1)


def build_packet(bundle, overlay=None, stage='contest', details=(), limit=LIMIT):
    if type(limit) is not int or not 1 <= limit <= LIMIT:
        raise ValueError(f'Limit must be within 1..{LIMIT}; cannot bypass the fixed budget')
    paths = stage_sources(stage)
    records, blocks = [], []
    for relative, mode, title in paths:
        text, record = read_source(bundle, overlay, relative)
        part = marker_region(text, CORE_BEGIN, CORE_END) if mode == 'core' else (
            section_region(text, title) if mode == 'section' else strip_frontmatter(text))
        record.update(region=mode, heading=title, characters=len(part),
                      selected_sha256=digest(part.encode('utf-8')))
        blocks.append(f'[{relative}]\n{part}')
        records.append(record)
    body = '\n'.join(blocks)
    core_characters = len(body)
    if core_characters > limit:
        raise ValueError(f'Core packet {core_characters} characters exceeds {limit}; no packet emitted')
    detail_records, detail_blocks, required_records = [], [], []
    required_characters = conditional_characters = 0
    required = REQUIRED_DETAILS.get(stage, ())
    for key in dict.fromkeys((*required, *details)):
        if key not in DETAILS:
            raise ValueError(f'Unknown detail: {key}')
        relative, heading, trigger = DETAILS[key]
        text, record = read_source(bundle, overlay, relative)
        if DETAIL_BEGIN in text:
            text = marker_region(text, DETAIL_BEGIN, DETAIL_END)
        part = section_region(text, heading) if heading else text
        record.update(id=key, heading=heading, trigger=trigger, characters=len(part),
                      selected_sha256=digest(part.encode('utf-8')))
        block = f'[{relative}#{heading or "details"} sha256={record["selected_sha256"]}]\n{part}'
        detail_blocks.append(block)
        if key in required:
            required_records.append(record)
            required_characters += len('\n' + block)
        else:
            detail_records.append(record)
            conditional_characters += len('\n' + block)
    static = []
    for path in ('templates/mcm-paper.tex', 'templates/mcm-style.tex'):
        text, record = read_source(bundle, overlay, path)
        record['characters'] = len(text)
        static.append(record)
    text = body + ('\n' + '\n'.join(detail_blocks) if detail_blocks else '')
    # Metadata stays outside the instruction budget and is reported separately.
    manifest = {'schema': 1, 'stage': stage, 'limit': limit,
                'metric': 'Python len of emitted Unicode text, including source-region headers and whitespace; hashes are separate provenance metadata',
                'core_characters': core_characters, 'emitted_characters': len(text),
                'conditional_detail_characters': conditional_characters,
                'required_details': required_records,
                'required_detail_characters': required_characters,
                'core_sha256': digest(body.encode('utf-8')), 'sources': records,
                'details': detail_records, 'static_templates_not_emitted': static,
                'static_template_characters': sum(x['characters'] for x in static),
                'note': 'Required stage details are emitted and counted separately; other details are explicit trigger selections; templates are consumed by paper_template, not loaded into this packet. No source or scientific result is modified.'}
    return text, manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--overlay', type=Path, help='Candidate replacements only; unchanged inputs come from --bundle')
    parser.add_argument('--stage', choices=STAGES, default='contest')
    parser.add_argument('--detail', action='append', default=[], choices=tuple(DETAILS))
    parser.add_argument('--list-details', action='store_true')
    parser.add_argument('--print-index', action='store_true', help='Print the offline Markdown index; never writes source files')
    parser.add_argument('--limit', type=int, default=LIMIT)
    parser.add_argument('--manifest', type=Path, help='Write provenance/counts outside emitted instruction text')
    args = parser.parse_args()
    try:
        if args.limit < 1 or args.limit > LIMIT:
            raise ValueError(f'Limit must be within 1..{LIMIT}; cannot bypass the fixed budget')
        if args.print_index:
            sys.stdout.write(render_index())
            return
        if args.list_details:
            print(json.dumps({k: {'path': v[0], 'heading': v[1], 'trigger': v[2]}
                              for k, v in DETAILS.items()}, ensure_ascii=False, indent=2))
            return
        text, manifest = build_packet(args.bundle, args.overlay, args.stage, args.detail, args.limit)
        if args.manifest:
            # Explicit new evidence only; do not overwrite an existing user file.
            with args.manifest.open('x', encoding='utf-8') as stream:
                json.dump(manifest, stream, ensure_ascii=False, indent=2)
                stream.write('\n')
        sys.stdout.write(text)
        print(f'\npacket core={manifest["core_characters"]}/{LIMIT}; '
              f'emitted={manifest["emitted_characters"]}; static={manifest["static_template_characters"]}; ' f'sha256={manifest["core_sha256"]}', file=sys.stderr)
    except (ValueError, OSError, UnicodeError) as error:
        parser.exit(2, f'{error}\n')


if __name__ == '__main__':
    main()
