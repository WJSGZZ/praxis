import hashlib
import json
import subprocess
import sys

import pytest

from scripts.paper_structure import inspect_structure


ONE_CHILD = '\\section{Model}\n\\subsection{Parameters}\n'


def write_review(tmp_path, result, approvals=None, **changes):
    data = {'tex_sha256': result['tex_sha256'], 'approved_single_child_nodes': (
        [{'id': candidate['id'], 'reason': 'The parent states the result; the child isolates its derivation.'}
         for candidate in result['candidates']] if approvals is None else approvals)}
    data.update(changes)
    path = tmp_path / 'structure-review.json'
    path.write_text(json.dumps(data), encoding='utf-8')
    return path


def test_one_child_reports_expected_outline_and_review_request():
    result = inspect_structure(ONE_CHILD)
    assert result['parsed'] and not result['passed'] and not result['errors']
    assert result['tex_sha256'] == hashlib.sha256(ONE_CHILD.encode()).hexdigest()
    parent, child = result['headings']
    assert parent['parent_id'] is None and parent['children'] == [child['id']]
    assert child['parent_id'] == parent['id'] and child['children'] == []
    candidate, = result['candidates']
    assert (candidate['parent_title'], candidate['child_title']) == ('Model', 'Parameters')
    assert (candidate['parent_level'], candidate['child_level']) == (1, 2)
    assert (candidate['parent_line'], candidate['child_line']) == (1, 2)
    assert result['unresolved'] == [candidate]
    assert 'not a mathematical error' in candidate['message']
    json.dumps(result)


def test_two_real_siblings_pass_and_sections_need_no_dummy_chapter():
    result = inspect_structure(ONE_CHILD + r'\subsection{Prediction}\section{Conclusion}')
    assert result['passed'] and result['candidates'] == []
    assert len(result['headings'][0]['children']) == 2
    assert result['headings'][-1]['parent_id'] is None


def test_starred_section_delimits_ancestry_without_adding_a_numbered_child():
    text = ONE_CHILD + r'\section*{References}\subsection*{Primary sources}\section{Conclusion}'
    result = inspect_structure(text)
    parent, child, references, sources, conclusion = result['headings']
    assert parent['children'] == [child['id']]
    assert references['parent_id'] is None and references['children'] == [sources['id']]
    assert not references['numbered'] and not sources['numbered']
    assert conclusion['parent_id'] is None
    assert [c['parent_id'] for c in result['candidates']] == [parent['id']]


def test_starred_sibling_does_not_hide_the_only_numbered_child():
    result = inspect_structure(ONE_CHILD + r'\subsection*{Notation note}')
    assert len(result['headings'][0]['children']) == 2
    assert len(result['candidates']) == 1 and not result['passed']


def test_nested_braces_formatted_titles_short_title_and_multiline():
    text = (r'\section[Short {name}]' + '\n' + r'{A \textbf{nested {title}}}' + '\n'
            + r'\subsection' + '\n' + r'{A \emph{method} and $x$}')
    result = inspect_structure(text)
    assert not result['errors']
    parent, child = result['headings']
    assert parent['title'] == 'A nested title'
    assert parent['title_tex'] == r'A \textbf{nested {title}}'
    assert parent['short_title_tex'] == 'Short {name}'
    assert child['line'] == 3 and child['title'] == 'A method and x'
    assert len(result['candidates']) == 1


def test_comments_and_escaped_percent_are_not_heading_sources():
    text = ('% \\section{Fake}\n' + r'\section{Model \% yield}' + '\n'
            + '% \\subsection{Fake}\n' + r'\subsection{Real}')
    result = inspect_structure(text)
    assert [n['title'] for n in result['headings']] == ['Model % yield', 'Real']
    assert [n['line'] for n in result['headings']] == [2, 4]


def test_inter_argument_comments_preserve_short_titles_and_star_boundaries():
    text = ('\\section% between macro and optional argument\n'
            '[Short]% between optional argument and title\n{Full}\n'
            '\\subsection{Only}\n'
            '\\section% between macro and star\n*% between star and title\n{References}')
    result = inspect_structure(text)
    assert not result['errors']
    parent, child, references = result['headings']
    assert parent['title'] == 'Full' and parent['short_title_tex'] == 'Short'
    assert not references['numbered'] and references['title'] == 'References'
    assert references['parent_id'] is None and parent['children'] == [child['id']]


@pytest.mark.parametrize('declaration', [
    r'\titleformat{\section}[hang]{\bfseries}{\thesection}{1em}{}',
    r'\titleformat*{\section}{\itshape}',
    r'\titlespacing*{\subsection}{0pt}{12pt}{6pt}',
])
def test_titlesec_heading_command_arguments_are_style_data(declaration):
    result = inspect_structure(declaration + '\n' + ONE_CHILD)
    assert not result['errors'] and [n['title'] for n in result['headings']] == ['Model', 'Parameters']


def test_actual_public_shared_style_does_not_add_fake_heading_tokens():
    from scripts.paper_template import preamble
    source = preamble('7391857', 'A title') + ONE_CHILD + r'\end{document}'
    result = inspect_structure(source)
    assert not result['errors'] and [n['title'] for n in result['headings']] == ['Model', 'Parameters']
    assert len(result['candidates']) == 1


@pytest.mark.parametrize('environment,prefix', [
    ('verbatim', ''), ('verbatim*', ''), ('Verbatim', '[fontsize=small]'),
    ('Verbatim*', ''), ('lstlisting', '[language=Python]'), ('lstlisting*', ''),
    ('minted', '[linenos]{python}'), ('minted*', '{python}'),
])
def test_raw_code_environment_never_parses_its_heading_examples(environment, prefix):
    # Unbalanced braces/math are legitimate raw code, and would break TeX AST parsing.
    code = '\\section{Fake}\n\\subsection{Fake}\n{ unmatched $ \\\n'
    text = ('\\begin{' + environment + '}' + prefix + '\n' + code
            + '\\end{' + environment + '}\n' + ONE_CHILD)
    result = inspect_structure(text)
    assert not result['errors'] and [n['title'] for n in result['headings']] == ['Model', 'Parameters']
    assert len(result['candidates']) == 1


@pytest.mark.parametrize('code', [
    r'\verb|\section{Fake} { $|', r'\verb*|\section{Fake} { $|',
    r'\lstinline[language=TeX]|\section{Fake} { $|',
])
def test_inline_verbatim_does_not_add_headings(code):
    result = inspect_structure(code + '\n' + ONE_CHILD)
    assert not result['errors'] and len(result['headings']) == 2


@pytest.mark.parametrize('definition', [
    r'\newcommand{\fake}[1]{\section{Fake}#1}',
    r'\renewcommand*\fake[1][x]{\subsection{Fake}#1}',
    r'\providecommand{\fake}{\section{Fake}}',
    r'\DeclareRobustCommand{\fake}{\section{Fake}}',
    r'\newenvironment{fake}{\section{Fake}}{\subsection{Fake}}',
    r'\NewDocumentCommand{\fake}{m}{\section{Fake}#1}',
    r'\RenewDocumentEnvironment{fake}{m}{\section{Fake}}{\subsection{Fake}}',
    r'\def\fake#1{\section{Fake}#1}', r'\gdef\fake#1,#2;{\section{Fake}#1}',
    r'\edef\fake{\subsection{Fake}}', r'\long\xdef\fake#1{\section{Fake}}',
])
def test_macro_definitions_are_data_not_document_headings(definition):
    result = inspect_structure(definition + '\n' + ONE_CHILD)
    assert not result['errors'] and [n['title'] for n in result['headings']] == ['Model', 'Parameters']
    assert result['unexpanded_constructs'][0]['kind'] == 'macro_definition'


def test_math_mode_heading_tokens_are_ignored():
    text = (r'$\section{Fake}$ $$\subsection{Fake}$$ \[\chapter{Fake}\]' + '\n'
            + r'\begin{align}\section{Fake}&=0\end{align}' + '\n' + ONE_CHILD)
    result = inspect_structure(text)
    assert not result['errors'] and len(result['headings']) == 2


def test_chapter_and_single_tertiary_child_are_checked_at_their_own_level():
    result = inspect_structure(r'\chapter{Study}\section{Model}\subsection{Analysis}'
                               r'\subsubsection{Proof}\subsection{Checks}\section{Conclusion}')
    assert [(c['parent_title'], c['child_title']) for c in result['candidates']] == [('Analysis', 'Proof')]
    assert result['candidates'][0]['child_level'] == 3


def test_grouped_and_environment_body_headings_keep_document_order():
    result = inspect_structure(r'\begin{document}{\section{Model}}'
                               r'\subsection{One}\subsection{Two}\end{document}')
    assert result['passed'] and len(result['headings']) == 3


def test_candidate_id_is_stable_under_unrelated_prose_and_line_changes():
    original = inspect_structure(ONE_CHILD)
    moved = inspect_structure('New prose.\n\n' + ONE_CHILD)
    assert original['candidates'][0]['id'] == moved['candidates'][0]['id']
    assert original['tex_sha256'] != moved['tex_sha256']


def test_current_reasoned_review_resolves_candidates_without_certifying_quality(tmp_path):
    result = inspect_structure(ONE_CHILD)
    reviewed = inspect_structure(ONE_CHILD, write_review(tmp_path, result))
    assert reviewed['passed'] and reviewed['unresolved'] == [] and not reviewed['errors']
    assert reviewed['candidates'][0]['approved']
    assert reviewed['candidates'][0]['approval_reason']
    assert reviewed['review']['approved_ids'] == [result['candidates'][0]['id']]
    assert any('does not certify article quality' in limitation for limitation in reviewed['limitations'])


def test_review_is_rejected_after_any_source_change_even_if_id_is_stable(tmp_path):
    result = inspect_structure(ONE_CHILD)
    stale = inspect_structure('Extra prose.\n' + ONE_CHILD, write_review(tmp_path, result))
    assert not stale['passed'] and 'does not match' in stale['errors'][0]['message']
    assert stale['unresolved'][0]['approved'] is False


@pytest.mark.parametrize('problem', ['unknown', 'duplicate', 'blank', 'missing', 'wrong_type'])
def test_invalid_approvals_fail_closed_and_do_not_apply_partial_approval(tmp_path, problem):
    result = inspect_structure(ONE_CHILD)
    approval = {'id': result['candidates'][0]['id'], 'reason': 'Preserve the distinct derivation.'}
    bad = dict(approval)
    if problem == 'unknown':
        bad['id'] = 'unknown-node'
        approvals = [approval, bad]
    elif problem == 'duplicate':
        approvals = [approval, bad]
    else:
        if problem == 'blank': bad['reason'] = ' \t\n'
        if problem == 'missing': del bad['reason']
        if problem == 'wrong_type': bad['reason'] = True
        approvals = [bad]
    reviewed = inspect_structure(ONE_CHILD, write_review(tmp_path, result, approvals))
    assert not reviewed['passed'] and reviewed['errors'][0]['kind'] == 'review_error'
    assert reviewed['review']['approved_ids'] == []
    assert not reviewed['candidates'][0]['approved']


def test_partial_review_leaves_other_candidates_unresolved(tmp_path):
    text = ONE_CHILD + r'\section{Validation}\subsection{Independent answer}'
    result = inspect_structure(text)
    approval = {'id': result['candidates'][0]['id'], 'reason': 'The derivation needs a separate navigation entry.'}
    reviewed = inspect_structure(text, write_review(tmp_path, result, [approval]))
    assert not reviewed['passed'] and not reviewed['errors']
    assert len(reviewed['unresolved']) == 1 and reviewed['unresolved'][0]['parent_title'] == 'Validation'


@pytest.mark.parametrize('source', [r'\section{Unclosed', r'\section', r'{\section}',
                                     r'\begin{document}\section{Model}',
                                     r'\begin{minted}{python}\section{Fake}'])
def test_parser_failure_is_explicit_and_never_reports_passed(source):
    result = inspect_structure(source)
    assert not result['passed'] and not result['parsed']
    assert result['errors'][0]['kind'] == 'parse_error'


def test_inputs_and_conditions_are_declared_without_reading_or_evaluation(tmp_path, monkeypatch):
    external = tmp_path / 'external.tex'
    external.write_text(r'\section{External}\subsection{Hidden}')
    def refuse_read(*args, **kwargs):
        raise AssertionError('Static inspection attempted filesystem access')
    monkeypatch.setattr(type(external), 'read_bytes', refuse_read)
    monkeypatch.setattr(type(external), 'read_text', refuse_read)
    text = ('\\input{' + str(external) + '}' + '\n'
            + r'\iftrue\section{Visible}\else\section{Other branch}\fi')
    result = inspect_structure(text)
    assert result['passed'] and [n['title'] for n in result['headings']] == ['Visible', 'Other branch']
    assert {item['kind'] for item in result['unexpanded_constructs']} == {'external_input', 'conditional'}


def test_review_json_duplicate_keys_are_rejected(tmp_path):
    result = inspect_structure(ONE_CHILD)
    review = tmp_path / 'ambiguous-review.json'
    review.write_text('{"tex_sha256":"' + result['tex_sha256'] + '","tex_sha256":"old",'
                      '"approved_single_child_nodes":[]}')
    checked = inspect_structure(ONE_CHILD, review)
    assert not checked['passed'] and 'Duplicate JSON key' in checked['errors'][0]['message']


def test_cli_preserves_byte_hash_and_uses_exit_status_for_unresolved_review(tmp_path):
    source = tmp_path / 'paper.tex'
    payload = ONE_CHILD.replace('\n', '\r\n').encode()
    source.write_bytes(payload)
    command = [sys.executable, '-m', 'scripts.paper_structure', str(source)]
    pending = subprocess.run(command, capture_output=True, text=True)
    result = json.loads(pending.stdout)
    assert pending.returncode == 1 and result['tex_sha256'] == hashlib.sha256(payload).hexdigest()
    review = write_review(tmp_path, result)
    checked = subprocess.run(command + ['--review', str(review)], capture_output=True, text=True)
    assert checked.returncode == 0 and json.loads(checked.stdout)['passed']
    assert checked.stderr == ''
