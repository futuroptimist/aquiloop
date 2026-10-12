"""Explicit, disposable reuse within one GitHub Actions job; disabled by default."""
from __future__ import annotations
import argparse
from contextlib import contextmanager
from contextvars import ContextVar
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import sysconfig
import tempfile

ACTIVE = ContextVar('binder_reuse', default=None)
OWNER_KEYS = ('GITHUB_REPOSITORY', 'GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT', 'GITHUB_JOB')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def owner():
    if os.environ.get('GITHUB_ACTIONS') != 'true' or not all(os.environ.get(k) for k in OWNER_KEYS):
        raise ValueError('reuse requires an identified GitHub Actions job')
    return {k: os.environ[k] for k in OWNER_KEYS}


def initialize():
    identity = owner()
    root = Path(tempfile.mkdtemp(prefix='binder-reuse-', dir=os.environ['RUNNER_TEMP'])).resolve()
    path = root / 'session.json'
    path.write_text(json.dumps({'schema': 1, 'owner': identity, 'root': str(root)}), encoding='utf8')
    return path


class Session:
    def __init__(self, path):
        path = Path(path).resolve()
        record = json.loads(path.read_text(encoding='utf8'))
        root = Path(record['root']).resolve()
        if (record.get('schema') != 1 or record.get('owner') != owner()
                or path != root / 'session.json'
                or Path(os.environ['RUNNER_TEMP']).resolve() not in root.parents):
            raise ValueError('reuse session is not owned by this job')
        self.root = root

    def file_digest(self, path):
        # Content identity, including same-size edits with preserved timestamps.
        return digest(Path(path).read_bytes())

    def snapshot(self, roots):
        records = []
        for root in sorted(set(Path(p).resolve() for p in roots)):
            if not root.exists():
                records.append((str(root), None))
                continue
            if root.is_file():
                records.append((str(root), self.file_digest(root)))
                continue
            visited = set()
            for directory, dirs, names in os.walk(root, followlinks=True):
                real = Path(directory).resolve()
                records.append((str(Path(directory)), 'directory', str(real)))
                if real in visited:
                    dirs[:] = []
                    continue
                visited.add(real)
                dirs[:] = sorted(d for d in dirs if d not in {'__pycache__', 'site-packages'})
                for name in sorted(names):
                    path = Path(directory) / name
                    if path.is_file() and path.suffix not in {'.pyc', '.pyo'}:
                        records.append((str(path), self.file_digest(path)))
        return digest(encoded(records))

    def toolchain(self):
        # Full TeX/font trees include search-order additions as well as used files.
        # Actual bytes, binaries, shared libraries and Python packages enter the key.
        roots = [Path('/etc/texmf'), Path('/var/lib/texmf'), Path('/usr/share/texlive'),
                 Path('/usr/share/texmf'), Path('/etc/fonts'), Path('/usr/share/fonts'),
                 Path('/usr/local/share/fonts'), Path.home() / '.fonts',
                 Path.home() / '.local/share/fonts', Path.home() / '.cache/fontconfig',
                 Path(sys.executable), Path(sysconfig.get_path('stdlib'))]
        versions = {'python': sys.version, 'platform': sys.platform}
        for tool, flag in [('lualatex', '--version'), ('pdftoppm', '-v'), ('kpsewhich', '--version')]:
            executable = shutil.which(tool)
            if not executable:
                raise RuntimeError(f'{tool} is required for reuse')
            roots.append(Path(executable).resolve())
            result = subprocess.run([executable, flag], capture_output=True, check=True)
            versions[tool] = (result.stdout + result.stderr).decode('utf8', errors='replace')
            linked = subprocess.run(['ldd', executable], capture_output=True, check=True, text=True).stdout
            roots.extend(Path(p) for p in re.findall(r'(/[^\s()]+)', linked) if Path(p).is_file())
        for variable in ('TEXMFDIST', 'TEXMFLOCAL', 'TEXMFHOME', 'TEXMFVAR', 'TEXMFSYSVAR',
                         'TEXMFCONFIG', 'TEXMFSYSCONFIG'):
            value = subprocess.check_output(['kpsewhich', '--var-value=' + variable], text=True).strip()
            versions[variable] = value
            if value:
                roots.append(Path(value))
        for name in ('pypdf', 'PIL'):
            module = importlib.import_module(name)
            versions[name] = module.__version__
            roots.append(Path(module.__file__).parent)
        environment = {k: v for k, v in os.environ.items()
                       if k.startswith(('TEX', 'LUATEX', 'FONT', 'XDG_', 'LC_', 'LD_', 'GS_'))
                       or k in {'PATH', 'HOME', 'LANG', 'PYTHONPATH', 'PYTHONHOME'}}
        for name in ('FONTCONFIG_FILE', 'FONTCONFIG_PATH', 'OSFONTDIR', 'TEXMFCNF',
                     'TEXINPUTS', 'LUAINPUTS', 'TEXFONTS'):
            for value in os.environ.get(name, '').split(os.pathsep):
                if value:
                    # Snapshot a recursive-search directory at its literal prefix.
                    value = value.lstrip('!').split('//', 1)[0]
                    if any(c in value for c in '{}$~'):
                        raise ValueError(f'unsupported custom {name} path for reuse')
                    roots.append(Path(value))
        return {'versions': versions, 'environment': environment, 'files': self.snapshot(roots)}

    def key(self, namespace, inputs):
        return digest(encoded({'schema': 1, 'namespace': namespace, 'inputs': inputs}))

    def restore(self, namespace, key, output):
        folder = self.root / namespace / key
        try:
            metadata = json.loads((folder / 'record.json').read_text(encoding='utf8'))
            data = (folder / 'payload').read_bytes()
            if (metadata.get('key') != key or metadata.get('sha256') != digest(data)
                    or any(self.file_digest(Path(p)) != h for p, h in metadata.get('dependencies', []))):
                raise ValueError('reuse payload digest mismatch')
        except (OSError, ValueError):
            print(f'reuse {namespace} miss {key}')
            return False
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        Path(output).write_bytes(data)
        print(f'reuse {namespace} hit {key}')
        return True

    def save(self, namespace, key, output, dependencies=()):
        folder = self.root / namespace / key
        folder.mkdir(parents=True, exist_ok=True)
        data = Path(output).read_bytes()
        # A failed/partial write cannot yield a hit: the record is written last.
        (folder / 'payload').write_bytes(data)
        (folder / 'record.json').write_text(json.dumps({'key': key, 'sha256': digest(data),
            'dependencies': [(str(p), self.file_digest(p)) for p in dependencies]}), encoding='utf8')


@contextmanager
def activate(path):
    token = ACTIVE.set(Session(path) if path else None)
    try:
        yield ACTIVE.get()
    finally:
        ACTIVE.reset(token)


def compile_key(session, root, staged, records, selected, options):
    return session.key('compile', {
        'repository': session.snapshot([root / 'binder', root / 'scripts', root / 'requirements-binder.txt',
                                        Path(options['base'])]),
        'staged': {p.name: digest(p.read_bytes()) for p in sorted(staged.glob('*.tex'))},
        'records': records, 'selected': selected, 'options': options,
        'toolchain': session.toolchain(), 'epoch': {'SOURCE_DATE_EPOCH': '0', 'FORCE_SOURCE_DATE': '1'},
        'command': ['lualatex', '-recorder', '-no-shell-escape', '-halt-on-error', '-interaction=nonstopmode', 'template.tex'],
        'passes': 2,
    })


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['init'])
    parser.parse_args()
    print(initialize())
