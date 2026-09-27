"""Personal, offline, build-checked Resolve theme installer (Python 3.10+)."""
import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import uuid
import zipfile
import zlib

ROOT = Path(__file__).resolve().parent
TARGETS = {'Resolve.exe', 'BMDDavUI.dll', 'Skins/Fusion.fuskin'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def child(root, relative):
    result = (root / relative).resolve()
    require(result.is_relative_to(root.resolve()), 'Path escapes its directory')
    return result


def outside_hash(data, spans):
    h = hashlib.sha256()
    cursor = 0
    for span in spans:
        offset, length = span['offset'], span['length']
        require(offset >= cursor and length > 0 and offset + length <= len(data),
                'Invalid or overlapping profile spans')
        h.update(data[cursor:offset])
        cursor = offset + length
    h.update(data[cursor:])
    return h.hexdigest()


def replacement(span, assets):
    packed = child(assets, span['asset']).read_bytes()
    raw = zlib.decompress(packed)
    require(digest(raw) == span['asset_sha256'], 'Corrupt theme asset')
    if span['mode'] == 'padded_png':
        require(raw.startswith(b'\x89PNG\r\n\x1a\n') and raw[-8:-4] == b'IEND',
                'Invalid banner/icon PNG')
        padding = span['length'] - len(raw) - 12
        require(padding >= 0, 'Image exceeds its resource slot')
        payload = b'npAD' + b'\0' * padding
        raw = (raw[:-12] + struct.pack('>I', padding) + payload
               + struct.pack('>I', zlib.crc32(payload) & 0xffffffff) + raw[-12:])
    else:
        require(span['mode'] == 'bytes', 'Unknown asset mode')
    require(len(raw) == span['length'] and digest(raw) == span['after'],
            'Replacement does not match profile')
    return raw


def transform_binary(data, spec, assets):
    require(len(data) == spec['size'], f"Unsupported size: {spec['path']}")
    require(outside_hash(data, spec['spans']) in spec['outside_sha256'],
            f"Unsupported build or unrelated modifications: {spec['path']}")
    output = bytearray(data)
    changed = 0
    for span in spec['spans']:
        offset, length = span['offset'], span['length']
        current = digest(data[offset:offset + length])
        require(current in (span['before'], span['after']),
                f"Unrecognized resource at {spec['path']}+0x{offset:x}")
        new = replacement(span, assets)  # Validate even on an idempotent run.
        if current != span['after']:
            output[offset:offset + length] = new
            changed += 1
    return bytes(output), changed


def transform_fusion(data, spec):
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)), 'Duplicate Fusion archive entries')
        require(set(names) == set(spec['members']) | {'Fusion.skin'}, 'Unsupported Fusion archive')
        for name, expected in spec['members'].items():
            require(digest(archive.read(name)) == expected, f'Unknown Fusion asset: {name}')
        skin = archive.read('Fusion.skin')
        require(digest(skin) in (spec['before_skin'], spec['after_skin']),
                'Unrecognized Fusion.skin; refusing to replace another theme')
        if digest(skin) == spec['after_skin']:
            return data, 0
        text = skin.decode('utf-8')
        for edit in spec['edits']:
            require(text.count(edit['before']) == 1, f"Ambiguous Fusion color: {edit['name']}")
            text = text.replace(edit['before'], edit['after'], 1)
        updated = text.encode('utf-8')
        require(digest(updated) == spec['after_skin'], 'Fusion output mismatch')
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as output:
            output.comment = archive.comment
            for info in archive.infolist():
                output.writestr(info, updated if info.filename == 'Fusion.skin' else archive.read(info))
        return buffer.getvalue(), len(spec['edits'])


def ensure_closed():
    if os.name != 'nt':
        raise ValueError('Installation is supported on Windows only')
    result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq Resolve.exe', '/FO', 'CSV', '/NH'],
                            capture_output=True, text=True, check=True,
                            creationflags=subprocess.CREATE_NO_WINDOW)
    for row in csv.reader(result.stdout.splitlines()):
        require(not row or row[0].casefold() != 'resolve.exe', 'Close Resolve before applying/restoring')


def plan_theme(install, profile, assets):
    require(profile['schema'] == 1, 'Unsupported profile schema')
    specs = profile['files'] + [profile['fusion']]
    require({s['path'] for s in specs} == TARGETS and len(specs) == 3, 'Invalid target list')
    plans = []
    for spec in specs:
        path = child(install, spec['path'])
        data = path.read_bytes()
        if spec is profile['fusion']:
            output, count = transform_fusion(data, spec)
        else:
            output, count = transform_binary(data, spec, assets)
        print(f"{spec['path']}: {'already applied' if not count else str(count) + ' changes'}")
        if count:
            plans.append({'relative': spec['path'], 'path': path, 'before': digest(data),
                          'after': digest(output), 'output': output})
    return plans


def write_state(path, state):
    temp = path.with_suffix('.json.tmp')
    temp.write_text(json.dumps(state, indent=2) + '\n', encoding='utf-8')
    os.replace(temp, path)


def commit(install, plans, action='apply'):
    """Pre-stage every file, then replace. Roll back completed replacements on errors."""
    if not plans:
        print('Nothing to change; no new backup created.')
        return None
    ensure_closed()
    lock = install / '.blackpink.lock'
    with lock.open('x', encoding='utf-8') as handle:
        handle.write(str(os.getpid()))
    session = install / '.blackpink-backups' / uuid.uuid4().hex
    stages = []
    replaced = []
    state = {'schema': 1, 'action': action, 'status': 'preparing', 'files': []}
    state_path = session / 'state.json'
    try:
        session.mkdir(parents=True)
        for plan in plans:
            path = plan['path']
            require(digest(path.read_bytes()) == plan['before'], f'File changed during preflight: {path}')
            backup = session / (path.name + '.bak')
            shutil.copy2(path, backup)
            require(digest(backup.read_bytes()) == plan['before'], 'Backup verification failed')
            stage = path.with_name(path.name + '.' + session.name + '.theme-tmp')
            stages.append(stage)
            with stage.open('xb') as handle:
                handle.write(plan['output'])
                handle.flush()
                os.fsync(handle.fileno())
            require(digest(stage.read_bytes()) == plan['after'], 'Staging verification failed')
            state['files'].append({'path': plan['relative'], 'backup': backup.name,
                                   'before': plan['before'], 'after': plan['after']})
        state['status'] = 'prepared'
        write_state(state_path, state)
        ensure_closed()
        for plan, stage in zip(plans, stages):
            require(digest(plan['path'].read_bytes()) == plan['before'], 'Target changed before replacement')
            os.replace(stage, plan['path'])
            replaced.append(plan)
            require(digest(plan['path'].read_bytes()) == plan['after'], 'Installed hash mismatch')
        state['status'] = 'complete'
        write_state(state_path, state)
        print(f'Complete. Restore manifest: {state_path}')
        return state_path
    except Exception:
        errors = []
        for plan in reversed(replaced):
            try:
                require(digest(plan['path'].read_bytes()) == plan['after'], 'Target changed; rollback refused')
                backup = session / (plan['path'].name + '.bak')
                require(digest(backup.read_bytes()) == plan['before'], 'Backup changed; rollback refused')
                recovery = plan['path'].with_name(plan['path'].name + '.' + session.name + '.rollback-tmp')
                shutil.copy2(backup, recovery)
                os.replace(recovery, plan['path'])
            except Exception as error:
                errors.append(str(error))
        state['status'] = 'rollback_failed' if errors else 'rolled_back'
        state['errors'] = errors
        if session.exists():
            write_state(state_path, state)
            print(f'Failure record/backups: {state_path}', file=sys.stderr)
        raise
    finally:
        for stage in stages:
            stage.unlink(missing_ok=True)
        lock.unlink(missing_ok=True)


def plan_restore(install, state_path):
    state = json.loads(state_path.read_text(encoding='utf-8'))
    require(state['schema'] == 1, 'Unsupported backup manifest')
    plans = []
    seen = set()
    for entry in state['files']:
        name = entry['path']
        require(name in TARGETS and name not in seen, 'Invalid backup target')
        seen.add(name)
        path = child(install, name)
        backup = child(state_path.parent, entry['backup']).read_bytes()
        require(digest(backup) == entry['before'], 'Backup hash mismatch')
        current = digest(path.read_bytes())
        require(current in (entry['before'], entry['after']), 'Target changed since backup; restore refused')
        if current != entry['before']:
            plans.append({'relative': name, 'path': path, 'before': current,
                          'after': entry['before'], 'output': backup})
    return plans


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('resolve', type=Path, help='Path to Resolve.exe')
    parser.add_argument('--dry-run', action='store_true', help='Validate all files/assets without writes')
    parser.add_argument('--check-closed', action='store_true', help='Also require Resolve closed during preflight')
    parser.add_argument('--restore', type=Path, metavar='STATE_JSON', help='Restore a verified backup session')
    args = parser.parse_args(argv)
    try:
        require(args.resolve.name.casefold() == 'resolve.exe', 'Expected the Resolve.exe path')
        install = args.resolve.resolve().parent
        if args.check_closed or not args.dry_run:
            ensure_closed()
        if args.restore:
            plans = plan_restore(install, args.restore.resolve())
        else:
            profile = json.loads((ROOT / 'profile.json').read_text(encoding='utf-8'))
            print(f"Profile: {profile['name']} / {profile['resolve_build']}")
            plans = plan_theme(install, profile, ROOT / 'assets')
        if args.dry_run:
            print(f'Validation passed: {len(plans)} files would change; no files written.')
        else:
            commit(install, plans, 'restore' if args.restore else 'apply')
        return 0
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, zlib.error, subprocess.SubprocessError) as error:
        print(f'Theme failed: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
