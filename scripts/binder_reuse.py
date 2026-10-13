"""Explicit, disposable reuse within one GitHub Actions job; disabled by default."""
from __future__ import annotations
import argparse
from contextlib import contextmanager
from contextvars import ContextVar
import hashlib
import importlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import sysconfig
import tempfile
import time

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
        self._file_hashes = {}

    def file_digest(self, path, before=None):
        path = Path(path)
        before = path.stat() if before is None else before
        def identity(stat):
            return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)
        signature = identity(before)
        cached = self._file_hashes.get(path)
        # Linux ctime changes on writes, including same-size edits followed by
        # restoring mtime. Never persist this optimization across processes/jobs.
        # Rehash recently changed files to avoid same-clock-tick (racy stat)
        # collisions. CI uses Linux's local filesystem; elsewhere always read.
        old_enough = time.time_ns() - before.st_ctime_ns > 1_000_000_000
        if sys.platform == 'linux' and old_enough and cached is not None and cached[0] == signature:
            return cached[1]
        value = digest(path.read_bytes())
        if identity(path.stat()) != signature:
            raise RuntimeError(f'input changed while hashing: {path}')
        self._file_hashes[path] = (signature, value)
        return value

    def snapshot(self, roots):
        records = []
        excluded = {'__pycache__', 'site-packages'}
        directories = []
        for root in sorted(set(Path(p).resolve() for p in roots)):
            # A containing tree already covers these bytes, except paths below
            # deliberately excluded package/cache directories. Explicit package
            # roots below site-packages must still be included.
            if any(parent in root.parents and not excluded.intersection(root.relative_to(parent).parts)
                   for parent in directories):
                continue
            if not root.exists():
                records.append((str(root), None))
                continue
            if root.is_file():
                records.append((str(root), self.file_digest(root)))
                continue
            directories.append(root)
            visited = set()
            pending = [(root, root.stat(), None)]
            while pending:
                directory, info, link = pending.pop()
                records.append((str(directory), 'directory', link))
                identity = (info.st_dev, info.st_ino)
                if identity in visited:
                    continue
                visited.add(identity)
                # DirEntry reuses filesystem type/stat information. Tracking
                # device/inode avoids resolving every ancestor of every folder
                # and still terminates directory-symlink cycles.
                with os.scandir(directory) as scan:
                    entries = sorted(scan, key=lambda entry: entry.name)
                children = []
                for entry in entries:
                    path = Path(entry.path)
                    if entry.is_dir(follow_symlinks=True):
                        if entry.name not in excluded:
                            # Windows DirEntry.stat omits inode/device information.
                            info = entry.stat() if sys.platform == 'linux' else path.stat()
                            children.append((path, info, os.readlink(path) if entry.is_symlink() else None))
                    elif entry.is_file(follow_symlinks=True) and path.suffix not in {'.pyc', '.pyo'}:
                        info = entry.stat() if sys.platform == 'linux' else path.stat()
                        records.append((str(path), self.file_digest(path, info)))
                pending.extend(reversed(children))
        return digest(encoded(records))

    def toolchain(self):
        # Full TeX/font trees include search-order additions as well as used files.
        # Actual bytes, binaries, shared libraries and Python packages enter the key.
        roots = [Path('/etc/texmf'), Path('/var/lib/texmf'), Path('/usr/share/texlive'),
                 Path('/usr/share/texmf'), Path('/etc/fonts'), Path('/usr/share/fonts'),
                 Path('/usr/share/poppler'), Path('/usr/share/color'),
                 Path('/usr/local/share/fonts'), Path.home() / '.fonts',
                 Path.home() / '.local/share/fonts', Path.home() / '.cache/fontconfig',
                 Path.home() / '.config/fontconfig',
                 Path(sys.executable), Path(sysconfig.get_path('stdlib'))]
        for variable, suffix in [('XDG_DATA_HOME', 'fonts'), ('XDG_CONFIG_HOME', 'fontconfig'),
                                 ('XDG_CACHE_HOME', 'fontconfig')]:
            if os.environ.get(variable):
                roots.append(Path(os.environ[variable]) / suffix)
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
        linked = subprocess.run(['ldd', sys.executable], capture_output=True, check=True, text=True).stdout
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
            # Wheels can place native libraries beside their import package.
            distribution = importlib.metadata.distribution('Pillow' if name == 'PIL' else name)
            roots.extend(distribution.locate_file(p) for p in distribution.files or ()
                         if p.suffix not in {'.pyc', '.pyo'})
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
            if not isinstance(metadata, dict) or not isinstance(metadata.get('dependencies'), list):
                raise ValueError('invalid reuse record')
            dependencies = metadata['dependencies']
            if any(not isinstance(item, list) or len(item) != 2
                   or not all(isinstance(value, str) for value in item) for item in dependencies):
                raise ValueError('invalid reuse dependency record')
            if (metadata.get('key') != key or metadata.get('sha256') != digest(data)
                    or any(self.file_digest(Path(p)) != h for p, h in dependencies)):
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
