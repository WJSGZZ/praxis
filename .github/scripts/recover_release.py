"""Recover six verified assets on an existing frozen release, never publish it.

Intended location: .github/scripts/recover_release.py. Definition is checked out
from the workflow HEAD; product exporter/resources come from the frozen tag.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
import zlib

TAG = 'v0.5.0'
COMMIT = '685cdae4074920d8bc72e32d7bef9730a388b2d1'
RELEASE_ID = 409767876
HOSTS = ('portable', 'codex', 'claude', 'copilot', 'gemini', 'cursor')
ZIP_DATE = (2026, 10, 11, 0, 0, 0)
API = 'https://api.github.com'
EMPTY_SHA = hashlib.sha256(b'').hexdigest()


def require(condition, message):
    if not condition:
        raise SystemExit(message)


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def parse_checksums(text):
    parsed = {}
    for line in text.strip().splitlines():
        match = re.fullmatch(r'([a-f0-9]{64})  (praxis-0\.5\.0-[a-z]+\.zip)', line.strip())
        require(match is not None, 'Expected checksums must be complete standard SHA256SUMS lines')
        digest, name = match.groups()
        require(name not in parsed, 'Duplicate expected asset name')
        parsed[name] = digest
    required = {f'praxis-0.5.0-{host}.zip' for host in HOSTS}
    require(set(parsed) == required, 'Expected checksums must cover exactly the six host ZIPs')
    return parsed


def checksum_text(checksums):
    return ''.join(f'{checksums[f"praxis-0.5.0-{host}.zip"]}  praxis-0.5.0-{host}.zip\n'
                   for host in HOSTS)


def build(args, expected):
    source = args.source.resolve()
    out = args.out.resolve()
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip()
    require(commit == COMMIT, 'Checked-out tag commit does not match frozen v0.5.0 identity')
    require(sys.version_info[:2] == (3, 12), 'Frozen recipe uses Python 3.12, as required by the tag lockfile')
    out.mkdir(parents=True, exist_ok=False)
    tree = out / 'tag-source'
    tree.mkdir()
    archive = subprocess.check_output(['git', 'archive', '--format=tar', commit], cwd=source)
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        for member in tar.getmembers():
            require(not member.issym() and not member.islnk(), 'Tag archive contains a link')
            require(not Path(member.name).is_absolute() and '..' not in Path(member.name).parts,
                    'Tag archive contains an unsafe path')
        tar.extractall(tree, filter='data')
    # Import the product exporter from the archived tag, never the workflow HEAD.
    sys.path.insert(0, str(tree))
    from scripts.build_plugin import build_plugin
    from scripts.plugin_hosts import HOSTS as tag_hosts
    require(tuple(tag_hosts) == HOSTS, 'Frozen tag host list changed')
    require(json.loads((tree / 'packaging/plugin.json').read_text())['version'] == '0.5.0',
            'Tag manifest version is not 0.5.0')
    assets = out / 'assets'
    assets.mkdir()
    rows = []
    for host in HOSTS:
        package = out / 'packages' / host / 'praxis'
        build_plugin(package, source=tree, host=host)
        receipt = json.loads((package / 'build-receipt.json').read_text())
        require(all(sha(package / name) == digest for name, digest in receipt['files_sha256'].items()),
                f'{host}: exported receipt hash mismatch')
        require(len(list((package / 'skills').glob('*/SKILL.md'))) == 9, f'{host}: expected nine skills')
        target = assets / f'praxis-0.5.0-{host}.zip'
        # Literal frozen writer: hand-made ZipInfo keeps its default compression
        # level. Do not add a per-entry level=9; that changes frozen ZIP bytes.
        with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zipped:
            for path in sorted(package.rglob('*')):
                if not path.is_file():
                    continue
                info = zipfile.ZipInfo('praxis/' + path.relative_to(package).as_posix(), date_time=ZIP_DATE)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                zipped.writestr(info, path.read_bytes())
        with zipfile.ZipFile(target) as zipped:
            files = [p for p in sorted(package.rglob('*')) if p.is_file()]
            names = ['praxis/' + p.relative_to(package).as_posix() for p in files]
            require(zipped.namelist() == names, f'{host}: ZIP member order differs')
            require(all(info.date_time == ZIP_DATE and info.external_attr == 0o100644 << 16
                        and info.compress_type == zipfile.ZIP_DEFLATED for info in zipped.infolist()),
                    f'{host}: ZIP metadata differs')
            require(all(hashlib.sha256(zipped.read(name)).hexdigest() == sha(path)
                        for name, path in zip(names, files)), f'{host}: ZIP member bytes differ')
        digest = sha(target)
        rows.append({'name': target.name, 'sha256': digest, 'bytes': target.stat().st_size,
                     'expected_sha256': expected[target.name], 'passed': digest == expected[target.name]})
        print(f'{target.name}: {digest}', flush=True)
    report = {'tag': TAG, 'source_commit': commit, 'workflow_commit': os.environ.get('GITHUB_SHA'),
              'python': sys.version, 'zlib_runtime': zlib.ZLIB_RUNTIME_VERSION,
              'zip_date': ZIP_DATE, 'zip_mode': '0100644', 'archive_constructor_level': 9,
              'entry_level': None, 'assets': rows, 'passed': all(row['passed'] for row in rows)}
    (out / 'build-receipt.json').write_text(json.dumps(report, indent=2) + '\n')
    (out / 'SHA256SUMS.txt').write_text(checksum_text({row['name']: row['sha256'] for row in rows}))
    require(report['passed'], 'Frozen six-ZIP hash check failed; nothing may be uploaded')


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, file, code, message, headers, newurl):
        return None


class GitHub:
    def __init__(self):
        self.repo = os.environ.get('GITHUB_REPOSITORY', '')
        require(re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', self.repo) is not None,
                'GITHUB_REPOSITORY is missing or invalid')
        self.token = os.environ.get('GH_TOKEN', '')
        require(bool(self.token), 'Built-in GH_TOKEN is missing')
        self.prefix = f'{API}/repos/{self.repo}'
        self.opener = urllib.request.build_opener(NoRedirect())

    def headers(self, accept='application/vnd.github+json'):
        return {'Authorization': f'Bearer {self.token}', 'Accept': accept,
                'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'praxis-release-recovery'}

    def api(self, path, method='GET', data=None, upload_url=None):
        url = upload_url if upload_url else self.prefix + path
        parsed = urllib.parse.urlsplit(url)
        require(parsed.scheme == 'https' and parsed.netloc in ('api.github.com', 'uploads.github.com'),
                'Untrusted authenticated API endpoint')
        headers = self.headers()
        if data is not None:
            headers['Content-Type'] = 'application/zip'
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with self.opener.open(request, timeout=300) as response:
                required = 201 if method == 'POST' else 204 if method == 'DELETE' else 200
                require(response.status == required, 'Unexpected API status')
                body = response.read()
                return json.loads(body) if body else None
        except urllib.error.HTTPError as error:
            raise SystemExit(f'{method} GitHub API HTTP {error.code}; rerun can resume verified assets') from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise SystemExit(f'{method} GitHub API transport failure; no automatic upload retry') from None

    def download(self, asset_id):
        # Only the first API request receives authentication. Redirects to signed
        # storage URLs are followed without a token, and never logged or saved.
        url = f'{self.prefix}/releases/assets/{asset_id}'
        headers = self.headers('application/octet-stream')
        for unused in range(6):
            parsed = urllib.parse.urlsplit(url)
            require(parsed.scheme == 'https' and parsed.username is None and parsed.password is None,
                    'Unsafe download redirect')
            try:
                with self.opener.open(urllib.request.Request(url, headers=headers), timeout=300) as response:
                    require(response.status == 200, 'Unexpected download status')
                    return response.read()
            except urllib.error.HTTPError as error:
                if error.code not in (301, 302, 303, 307, 308):
                    raise SystemExit(f'Asset download HTTP {error.code}') from None
                location = error.headers.get('Location')
                require(bool(location), 'Download redirect has no Location')
                url = urllib.parse.urljoin(url, location)
                headers = {'Accept': 'application/octet-stream', 'User-Agent': 'praxis-release-recovery'}
            except (urllib.error.URLError, TimeoutError, OSError):
                raise SystemExit('Asset download transport failure') from None
        raise SystemExit('Too many asset download redirects')

    def assets(self, release_id):
        result = []
        page = 1
        while True:
            batch = self.api(f'/releases/{release_id}/assets?per_page=100&page={page}')
            require(isinstance(batch, list), 'Invalid release assets response')
            result.extend(batch)
            if len(batch) < 100:
                return result
            page += 1

    def confirm_tag(self):
        obj = self.api('/git/ref/tags/' + urllib.parse.quote(TAG, safe=''))['object']
        for unused in range(8):
            if obj['type'] == 'commit':
                require(obj['sha'] == COMMIT, 'Remote tag no longer matches the frozen commit')
                return
            require(obj['type'] == 'tag', 'Unexpected tag reference object')
            obj = self.api('/git/tags/' + obj['sha'])['object']
        raise SystemExit('Too many annotated tag indirections')


def named_asset(catalog, name):
    matches = [asset for asset in catalog if asset.get('name') == name]
    require(len(matches) <= 1, f'{name}: duplicate remote asset names')
    return matches[0] if matches else None


def disposition(asset, name, expected, local_size, downloaded_sha=None):
    require(asset.get('name') == name and type(asset.get('id')) is int and asset['id'] > 0,
            f'{name}: asset identity mismatch')
    if asset.get('state') == 'starter':
        require(asset.get('size') == 0 and asset.get('digest') in (None, 'sha256:' + EMPTY_SHA)
                and asset.get('content_type') in ('application/zip', 'application/octet-stream'),
                f'{name}: starter metadata does not prove an empty recoverable ZIP')
        return 'starter-empty'
    require(asset.get('state') == 'uploaded' and asset.get('size') == local_size,
            f'{name}: existing asset differs or is incomplete; refusing replacement')
    require(asset.get('digest') in (None, 'sha256:' + expected),
            f'{name}: existing digest differs; refusing replacement')
    if downloaded_sha is None:
        return 'verify'
    require(downloaded_sha == expected, f'{name}: existing bytes differ; refusing replacement')
    return 'keep'


def verify_existing(client, asset, name, expected, size):
    endpoint = f'{client.prefix}/releases/assets/{asset["id"]}'
    require(str(asset.get('url', '')).lower() == endpoint.lower(), f'{name}: asset API URL mismatch')
    fresh = client.api(f'/releases/assets/{asset["id"]}')
    require(fresh.get('id') == asset['id'] and str(fresh.get('url', '')).lower() == endpoint.lower(),
            f'{name}: refreshed asset identity mismatch')
    status = disposition(fresh, name, expected, size)
    if status == 'verify':
        digest = hashlib.sha256(client.download(fresh['id'])).hexdigest()
        status = disposition(fresh, name, expected, size, digest)
    return status, fresh


def upload(args, expected):
    out = args.out.resolve()
    report = json.loads((out / 'build-receipt.json').read_text())
    require(report.get('passed') is True and report['source_commit'] == COMMIT and report['tag'] == TAG,
            'A successful frozen-tag build receipt is required')
    paths = {name: out / 'assets' / name for name in expected}
    require(all(path.is_file() and sha(path) == expected[name] for name, path in paths.items()),
            'All six local files must pass hashes again before any remote mutation')
    client = GitHub()
    client.confirm_tag()
    # The release-by-tag endpoint returns 404 for this unpublished draft.
    # Bind the already-created release ID and independently verify its tag.
    release = client.api(f'/releases/{RELEASE_ID}')
    require(release.get('tag_name') == TAG and release.get('id') == RELEASE_ID,
            'Existing release identity mismatch')
    require(release.get('assets_url') == f'{client.prefix}/releases/{release["id"]}/assets',
            'Existing release assets URL mismatch')
    catalog = client.assets(release['id'])
    manifest = named_asset(catalog, 'SHA256SUMS.txt')
    if manifest:
        require(manifest.get('state') == 'uploaded' and manifest.get('size', 0) > 0,
                'Existing SHA256SUMS is incomplete; do not replace it')
        remote_expected = parse_checksums(client.download(manifest['id']).decode('utf-8'))
        require(remote_expected == expected, 'Existing release SHA256SUMS conflicts with the complete input')
    state = {'tag': TAG, 'source_commit': COMMIT, 'workflow_commit': os.environ.get('GITHUB_SHA'),
             'release_id': release['id'], 'original_draft_state': release.get('draft'),
             'actions': [], 'passed': False, 'release_metadata_mutated': False}
    try:
        # Preflight ALL existing names before any delete/upload; content mismatch
        # anywhere fails the whole run without replacing any completed asset.
        plan = {}
        for name, path in paths.items():
            asset = named_asset(catalog, name)
            if asset is None:
                plan[name] = 'missing'
            else:
                plan[name], unused = verify_existing(client, asset, name, expected[name], path.stat().st_size)
        require(not release.get('immutable') or all(status == 'keep' for status in plan.values()),
                'Immutable release is missing assets; refusing mutation')
        upload_base = release.get('upload_url', '').split('{', 1)[0]
        require(upload_base == f'https://uploads.github.com/repos/{client.repo}/releases/{release["id"]}/assets',
                'Existing release upload URL mismatch')
        for name, path in paths.items():
            # Refresh catalog and metadata immediately before a possible mutation.
            asset = named_asset(client.assets(release['id']), name)
            if asset is not None:
                status, fresh = verify_existing(client, asset, name, expected[name], path.stat().st_size)
                if status == 'keep':
                    state['actions'].append({'name': name, 'asset_id': fresh['id'], 'action': 'kept-same-hash'})
                    print(f'{name}: kept verified existing asset', flush=True)
                    continue
                require(status == 'starter-empty', f'{name}: refusing cleanup')
                client.api(f'/releases/assets/{fresh["id"]}', method='DELETE')
                state['actions'].append({'name': name, 'asset_id': fresh['id'], 'action': 'deleted-confirmed-empty-starter'})
            url = upload_base + '?' + urllib.parse.urlencode({'name': name})
            attempted = {'name': name, 'action': 'upload-attempt-result-unknown'}
            state['actions'].append(attempted)
            uploaded = client.api('', method='POST', data=path.read_bytes(), upload_url=url)
            require(disposition(uploaded, name, expected[name], path.stat().st_size) == 'verify',
                    f'{name}: upload response is incomplete')
            attempted.update(asset_id=uploaded['id'], action='uploaded')
            print(f'{name}: uploaded; final remote byte check pending', flush=True)
        final = client.assets(release['id'])
        state['verified_remote_sha256'] = {}
        for name, path in paths.items():
            asset = named_asset(final, name)
            require(asset is not None, f'{name}: final asset missing')
            status, fresh = verify_existing(client, asset, name, expected[name], path.stat().st_size)
            require(status == 'keep', f'{name}: final asset not complete')
            state['verified_remote_sha256'][name] = expected[name]
        state['passed'] = True
        print('All six remote ZIP byte hashes verified; release draft/publish state was not changed.', flush=True)
    finally:
        # Only public identity/status/hash metadata is serialized. Never headers,
        # token, signed redirect URLs, or raw exception/request objects.
        (out / 'upload-receipt.json').write_text(json.dumps(state, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('build', 'upload'))
    parser.add_argument('--source', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--tag', required=True)
    parser.add_argument('--expected-checksums', type=Path,
                        help='Local check only; Actions uses the complete EXPECTED_SHA256SUMS input')
    args = parser.parse_args()
    require(args.tag == TAG, 'This frozen recovery recipe accepts v0.5.0 only')
    raw = args.expected_checksums.read_text() if args.expected_checksums else os.environ.get('EXPECTED_SHA256SUMS', '')
    expected = parse_checksums(raw)
    if args.stage == 'build':
        require(args.source is not None, 'build requires --source')
        build(args, expected)
    else:
        upload(args, expected)


if __name__ == '__main__':
    main()
