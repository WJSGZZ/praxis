"""Check public version, skill and tool facts in both README languages."""
import hashlib
import json
import re
import tomllib
from pathlib import Path
from pypdf import PdfReader

from scripts import build_plugin, mcp_server
from scripts.paper_template import MCM_SIMULATION_TEAM, review_mcm_identity_statements

ROOT = Path(__file__).resolve().parents[1]
GALLERY = Path('demos/mcm-studies')
GALLERY_CATEGORIES = {
    'mechanism': {'zh': '物理机制与工程设计', 'en': 'Physical mechanisms and engineering'},
    'data': {'zh': '数据分析与逆问题', 'en': 'Data analysis and inverse problems'},
    'risk': {'zh': '长期风险与决策', 'en': 'Long-term risk and decisions'},
}


def readme_errors(text, language, version, skill_names, tool_names):
    errors = []
    for advertised in re.findall(r'(?:Version-|/releases/tag/v)(\d+\.\d+\.\d+)', text):
        if advertised != version:
            errors.append(f'{language}: advertised version {advertised} differs from {version}')
    if '/releases/latest' not in text:
        errors.append(f'{language}: latest published release link is missing')
    listed_skills = set(re.findall(r'\[`(praxis(?:-[a-z-]+)?)`\]', text))
    if listed_skills != set(skill_names):
        errors.append(f'{language}: skill table differs: {sorted(listed_skills ^ set(skill_names))}')
    heading = '## 数学工具' if language == 'zh' else '## Math tools'
    if heading not in text:
        return errors + [f'{language}: tool section is missing']
    section = text.split(heading, 1)[1].split('\n## ', 1)[0]
    listed_tools = set(re.findall(r'`([a-z][a-z_0-9]*)`', section))
    if listed_tools != set(tool_names):
        errors.append(f'{language}: tool table differs: {sorted(listed_tools ^ set(tool_names))}')
    return errors


def check_gallery(root=ROOT):
    """Validate the single-best public paper gallery and its bilingual index."""
    gallery = root / GALLERY
    errors = []
    if not gallery.is_dir():
        return {'entries': 0, 'errors': [f'Gallery directory is missing: {gallery}']}
    catalog_path = gallery / 'catalog.json'
    if not catalog_path.is_file():
        return {'entries': 0, 'errors': [f'Gallery catalog is missing: {catalog_path}']}
    try:
        catalog = json.loads(catalog_path.read_text(encoding='utf-8'))
        entries = catalog['entries']
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        return {'entries': 0, 'errors': [f'Invalid gallery catalog: {exc}']}
    if not entries:
        errors.append('Gallery catalog has no entries')
    slugs = [entry.get('slug') for entry in entries]
    if len(set(slugs)) != len(slugs):
        errors.append('Gallery catalog contains duplicate slugs')
    identities = [(entry.get('contest'), entry.get('edition'), entry.get('problem'))
                  for entry in entries]
    if len(set(identities)) != len(identities):
        errors.append('A contest problem appears more than once in the gallery catalog')
    pdf_paths = [entry.get('pdf_path') for entry in entries]
    metadata_paths = [entry.get('metadata') for entry in entries]
    if len(set(pdf_paths)) != len(pdf_paths):
        errors.append('Gallery catalog reuses a PDF path for multiple papers')
    if len(set(metadata_paths)) != len(metadata_paths):
        errors.append('Gallery catalog reuses a metadata path for multiple papers')
    for entry in entries:
        slug = entry.get('slug', '')
        if entry.get('category') not in GALLERY_CATEGORIES:
            errors.append(f'{slug}: unknown or missing gallery category')
        expected_pdf = '../mcm-2016-a/paper.pdf' if slug == 'mcm-2016-a' else f'papers/{slug}.pdf'
        if entry.get('metadata') != f'metadata/{slug}.json' or entry.get('pdf_path') != expected_pdf:
            errors.append(f'{slug}: catalog paths must use canonical slug names')

    expected_metadata = {entry.get('metadata') for entry in entries}
    expected_pdfs = {entry.get('pdf_path') for entry in entries
                     if entry.get('pdf_path', '').endswith('.pdf')}
    actual_metadata = {p.relative_to(gallery).as_posix()
                       for p in gallery.rglob('*.json') if p != catalog_path}
    actual_pdfs = {p.relative_to(gallery).as_posix()
                   for p in gallery.rglob('*.pdf')}
    if actual_metadata != expected_metadata:
        errors.append(f'Gallery metadata files differ from catalog: extra={sorted(actual_metadata-expected_metadata)}, missing={sorted(expected_metadata-actual_metadata)}')
    local_pdf_paths = {p for p in expected_pdfs if p.startswith('papers/')}
    if actual_pdfs != local_pdf_paths:
        errors.append(f'Gallery PDF files differ from catalog: extra={sorted(actual_pdfs-local_pdf_paths)}, missing={sorted(local_pdf_paths-actual_pdfs)}')

    for entry in entries:
        slug = entry.get('slug', '<missing-slug>')
        try:
            metadata_path = gallery / entry['metadata']
            metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
            pdf = (gallery / entry['pdf_path']).resolve()
            if not pdf.is_file():
                errors.append(f'{slug}: PDF is missing: {entry["pdf_path"]}')
                continue
            expected_sha = entry.get('pdf_sha256')
            actual_sha = hashlib.sha256(pdf.read_bytes()).hexdigest()
            if actual_sha != expected_sha:
                errors.append(f'{slug}: PDF SHA-256 differs from catalog')
            reader = PdfReader(str(pdf))
            pages = len(reader.pages)
            identity = {'mode': 'simulation', 'team': MCM_SIMULATION_TEAM}
            if entry.get('identity') != identity or metadata.get('identity') != identity:
                errors.append(f'{slug}: gallery identity must declare the fixed simulation team')
            summary = reader.pages[0].extract_text() or ''
            teams = re.findall(r'Team\s+Control\s+Number\s*([0-9]+)', summary)
            if teams != [MCM_SIMULATION_TEAM]:
                errors.append(f'{slug}: summary does not use the fixed simulation team')
            for number, page in enumerate(reader.pages[1:], 2):
                page_text = page.extract_text() or ''
                teams = re.findall(r'Team\s*#\s*([0-9]+)', page_text)
                if teams != [MCM_SIMULATION_TEAM]:
                    errors.append(f'{slug}: page {number} does not use the fixed simulation team')
                fields = re.findall(r'(?:From:\s*Team\s+|(?:Respectfully|Sincerely),\s*Team\s+|internal control identifier\s+)([0-9]+)\b', page_text)
                if any(team != MCM_SIMULATION_TEAM for team in fields):
                    errors.append(f'{slug}: page {number} has a conflicting team signature or disclosure')
                identity_review = review_mcm_identity_statements(page_text, MCM_SIMULATION_TEAM)
                errors.extend(f'{slug}: page {number}: {error}'
                              for error in identity_review['errors'])
            if pages != entry.get('pages'):
                errors.append(f'{slug}: PDF has {pages} pages; catalog says {entry.get("pages")}')
            if metadata.get('pdf_sha256') != expected_sha or metadata.get('pages') != entry.get('pages'):
                errors.append(f'{slug}: metadata page count or SHA-256 differs from catalog')
            if metadata.get('pdf_path') != '../' + entry['pdf_path']:
                errors.append(f'{slug}: metadata PDF path differs from catalog')
        except (OSError, KeyError, json.JSONDecodeError, ValueError) as exc:
            errors.append(f'{slug}: cannot validate metadata/PDF: {exc}')

    for lang, filename in [('zh', 'README.md'), ('en', 'README.en.md')]:
        path = gallery / filename
        if not path.is_file():
            errors.append(f'{lang}: gallery README is missing')
            continue
        text = path.read_text(encoding='utf-8')
        row_slugs = []
        # Include every displayed paper row, even under an unrecognized heading.
        paper_rows = [line for line in text.splitlines()
                      if line.startswith('|') and re.search(r'\]\([^)]*\.pdf\)', line)]
        if len(paper_rows) != len(entries):
            errors.append(f'{lang}: all displayed paper rows must match the catalog exactly once')
        section_categories = {title: category
                              for category, title in ((key, value[lang])
                                                      for key, value in GALLERY_CATEGORIES.items())}
        sections = re.split(r'^## ', text, flags=re.MULTILINE)[1:]
        seen_categories = set()
        for section in sections:
            title = section.splitlines()[0].strip()
            category = section_categories.get(title)
            if category is None:
                continue
            seen_categories.add(category)
            body = section.split('\n', 1)[1] if '\n' in section else ''
            rows = [line for line in body.splitlines()
                    if line.startswith('|') and not re.match(r'^\|[-: |]+\|$', line)]
            data_rows = rows[1:] if rows else []
            expected_slugs = {entry['slug'] for entry in entries
                              if entry.get('category') == category}
            if len(data_rows) != len(expected_slugs):
                errors.append(f'{lang}: section {title!r} has {len(data_rows)} rows; expected {len(expected_slugs)} from catalog')
            for row in data_rows:
                links = re.findall(r'\[[^]]+\]\(([^)]+)\)', row)
                pdf_links = [link for link in links if link.endswith('.pdf')]
                metadata_links = [link for link in links if link.endswith('.json')]
                if len(pdf_links) != 1 or len(metadata_links) != 1:
                    errors.append(f'{lang}: each gallery row must link one PDF and one metadata record')
                    continue
                matching = [e for e in entries if e['pdf_path'] == pdf_links[0]
                            and e['metadata'] == metadata_links[0]]
                if len(matching) != 1:
                    errors.append(f'{lang}: row links do not identify exactly one catalog entry')
                elif matching[0].get('category') != category:
                    errors.append(f'{lang}: row is under the wrong category for {matching[0]["slug"]}')
                else:
                    entry = matching[0]
                    label = row.split('|')[1].strip()
                    identity = (rf"^{entry['edition']}\s+{re.escape(entry['contest'])}"
                                rf"\s+{re.escape(entry['problem'])}\b")
                    if not re.match(identity, label):
                        errors.append(f'{lang}: displayed problem label differs from {entry["slug"]}')
                    row_slugs.append(entry['slug'])
        expected_categories = {entry.get('category') for entry in entries}
        if seen_categories != expected_categories:
            errors.append(f'{lang}: README sections do not match catalog categories')
        if len(row_slugs) != len(entries) or set(row_slugs) != set(slugs) or len(set(row_slugs)) != len(entries):
            errors.append(f'{lang}: table rows must list each catalog paper exactly once')
    return {'entries': len(entries), 'errors': errors}


def check(root=ROOT):
    project = tomllib.loads((root / 'pyproject.toml').read_text(encoding='utf-8'))['project']
    version = project['version']
    manifest = json.loads((root / 'packaging/plugin.json').read_text(encoding='utf-8'))
    errors = [] if manifest['version'] == version else ['Plugin and project versions differ']
    skills = {'praxis', *build_plugin.FOCUSED}
    for language, file in [('zh', 'README.md'), ('en', 'README.en.md')]:
        errors += readme_errors((root / file).read_text(encoding='utf-8'), language, version, skills, mcp_server.TOOLS)
    if not re.search(r'^## ' + re.escape(version) + r' · ',
                     (root / 'CHANGELOG.md').read_text(encoding='utf-8'), re.MULTILINE):
        errors.append('Current version has no changelog entry')
    for language, file in [('zh', 'installation.md'), ('en', 'installation.en.md')]:
        text = (root / 'references' / file).read_text(encoding='utf-8')
        versions = set(re.findall(r'/releases/(?:tag|download)/v(\d+\.\d+\.\d+)', text))
        if versions != {version}:
            errors.append(f'{language}: installation release versions {sorted(versions)} differ from {version}')
    # The explicit exporter omits the secondary gallery. Accept that narrower
    # scope only from its actual bundle receipt; a missing source catalog fails.
    bundle = root.parent.parent
    receipt_path = bundle / 'build-receipt.json'
    exported_without_gallery = False
    if root == bundle / 'skills/praxis' and receipt_path.is_file():
        receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
        exported_without_gallery = (receipt.get('format') == 'praxis-plugin-export-v1'
            and isinstance(receipt.get('files_sha256'), dict)
            and not any(name.startswith('skills/praxis/demos/mcm-studies/')
                        for name in receipt['files_sha256']))
    gallery_included = (root / GALLERY).exists() or not exported_without_gallery
    gallery_result = check_gallery(root) if gallery_included else {'entries': 0, 'errors': []}
    errors.extend(gallery_result['errors'])
    return {'version': version, 'skills': len(skills), 'tools': len(mcp_server.TOOLS),
            'gallery': {'scope': 'included' if gallery_included else 'excluded',
                        'entries': gallery_result['entries']}, 'errors': errors}


def main():
    result = check()
    print(json.dumps(result, ensure_ascii=False))
    return int(bool(result['errors']))


if __name__ == '__main__':
    raise SystemExit(main())
