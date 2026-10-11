"""Run a player-context Lua probe in an isolated OpenMW session (Windows v1)."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import uuid

ASSETS = Path(__file__).resolve().parents[1] / 'assets'
PROBE_CONTENT = 'omw_runtime_probe.omwscripts'


def cfg_path(path):
    value = Path(path).as_posix()
    if any(c in value for c in '\r\n\0'):
        raise ValueError('Configuration paths cannot contain line breaks or NUL')
    return '"' + value.replace('&', '&&').replace('"', '&"') + '"'


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_inputs(args):
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        raise ValueError('--timeout must be a finite positive number')
    args.openmw = args.openmw.resolve(strict=True)
    args.resources = args.resources.resolve(strict=True)
    args.probe = args.probe.resolve(strict=True)
    args.data = [p.resolve(strict=True) for p in args.data]
    args.output = args.output.resolve()
    if not args.openmw.is_file() or not args.probe.is_file():
        raise ValueError('--openmw and --probe must be files')
    for folder in [args.resources, *args.data]:
        if not folder.is_dir():
            raise ValueError(f'Not a directory: {folder}')
        if args.output.is_relative_to(folder):
            raise ValueError('Output must be outside input data/resource directories')
        cfg_path(folder)
    cfg_path(args.output)
    if args.output.exists():
        raise ValueError('Output already exists; choose a new evidence directory')
    for name in [*args.content, *args.archive]:
        if not name or name in {'.', '..', PROBE_CONTENT} or any(c in name for c in '/\\\r\n\0'):
            raise ValueError('Content/archive arguments must be plain filenames')
        if not any((folder / name).is_file() for folder in args.data):
            raise ValueError(f'Not found in the supplied data directories: {name}')
    if len(args.content) != len(set(args.content)):
        raise ValueError('Duplicate content entry')
    if not args.start.strip() or any(c in args.start for c in '\r\n\0'):
        raise ValueError('--start must be a cell name')


def prepare(args, run_id):
    out = args.output
    out.mkdir(parents=True, exist_ok=False)
    data, config = out / 'data', out / 'config'
    script_dir = data / 'scripts' / 'omw_runtime_test'
    script_dir.mkdir(parents=True)
    config.mkdir()
    (out / 'user-data').mkdir()
    shutil.copy2(args.probe, script_dir / 'case.lua')
    driver = (ASSETS / 'driver.lua').read_text(encoding='utf-8')
    if driver.count('__RUN_ID__') != 1:
        raise ValueError('Invalid bundled driver: expected one run-id placeholder')
    (script_dir / 'driver.lua').write_text(driver.replace('__RUN_ID__', run_id), encoding='utf-8')
    (data / PROBE_CONTENT).write_text('PLAYER: scripts/omw_runtime_test/driver.lua\n', encoding='utf-8')
    lines = ['replace=data', 'replace=content', 'replace=fallback-archive', 'replace=groundcover',
             f'resources={cfg_path(args.resources)}', 'encoding=win1252']
    builtin = args.resources / 'vfs-mw'
    if builtin.is_dir():
        lines.append(f'data={cfg_path(builtin)}')
    lines += [f'data={cfg_path(folder)}' for folder in args.data]
    lines += [f'data={cfg_path(data)}', f'data-local={cfg_path(data)}',
              f'user-data={cfg_path(out / "user-data")}']
    lines += [f'fallback-archive={name}' for name in args.archive]
    lines += [f'content={name}' for name in [*args.content, PROBE_CONTENT]]
    (config / 'openmw.cfg').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    (config / 'settings.cfg').write_text(
        '[Video]\nfullscreen = false\nresolution x = 1280\nresolution y = 960\nvsync = true\n'
        '\n[GUI]\nscaling factor = 1.0\n\n[Sound]\nmaster volume = 0\n', encoding='utf-8')
    return [str(args.openmw), '--replace', 'config', '--config', str(config),
            '--skip-menu', '--new-game=0', '--start=' + args.start, '--no-grab', '--no-sound']


def execute(command, output, timeout):
    startup = None
    if sys.platform == 'win32':
        startup = subprocess.STARTUPINFO()
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = 0
    started, timed_out, launch_error = time.monotonic(), False, None
    code = None
    with (output / 'stdout.txt').open('w', encoding='utf-8') as stdout, \
            (output / 'stderr.txt').open('w', encoding='utf-8') as stderr:
        try:
            process = subprocess.Popen(command, cwd=output, stdout=stdout, stderr=stderr, startupinfo=startup)
        except OSError as err:
            launch_error = str(err)
        else:
            try:
                code = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                process.terminate()
                try:
                    code = process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    code = process.wait(timeout=5)
            except KeyboardInterrupt:
                process.kill()
                process.wait(timeout=5)
                raise
    return {'exit_code': code, 'timed_out': timed_out, 'launch_error': launch_error,
            'elapsed_seconds': round(time.monotonic() - started, 3)}


def assess(stdout, logs, run_id, process_result):
    pattern = re.compile(r'OMW_TEST\|' + re.escape(run_id) + r'\|(BEGIN|PASS|COMPLETE|FAIL)(?:\||$)')
    markers = []
    for line in stdout.splitlines():
        match = pattern.search(line)
        if match:
            markers.append({'event': match[1], 'line': line})
    errors = sorted({line for line in logs.splitlines()
                     if re.search(r'Lua error|Error running (?:script|Lua)|Lua exception', line, re.IGNORECASE)})
    reasons = []
    if process_result['launch_error']:
        reasons.append('Engine launch failed')
    if process_result['timed_out']:
        reasons.append('Engine exceeded timeout')
    if process_result['exit_code'] != 0:
        reasons.append('Engine did not exit successfully')
    events = [m['event'] for m in markers]
    if 'FAIL' in events:
        reasons.append('Probe reported failure')
    if events != ['BEGIN', 'PASS', 'COMPLETE']:
        reasons.append('Missing, duplicate, or out-of-order completion markers')
    if errors:
        reasons.append('Engine logged Lua errors')
    return {'passed': not reasons, 'reasons': reasons, 'markers': markers, 'lua_errors': errors}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--openmw', type=Path, required=True)
    parser.add_argument('--resources', type=Path, required=True)
    parser.add_argument('--data', type=Path, action='append', required=True,
                        help='Data directory; repeat in load order (later directories override earlier ones)')
    parser.add_argument('--content', action='append', required=True, help='Content filename; repeat in load order')
    parser.add_argument('--archive', action='append', default=[], help='BSA filename; repeat in load order')
    parser.add_argument('--probe', type=Path, required=True, help='Lua module returning {step=function, cleanup=function?}')
    parser.add_argument('--output', type=Path, required=True, help='New directory for configuration, storage and evidence')
    parser.add_argument('--start', default='Vivec, Arena Pit', help='Start cell from supplied game content')
    parser.add_argument('--timeout', type=float, default=45)
    args = parser.parse_args(argv)
    if sys.platform != 'win32':
        parser.error('Version 1 supports Windows; other platforms have not been validated')
    try:
        validate_inputs(args)
        run_id = uuid.uuid4().hex
        command = prepare(args, run_id)
    except (ValueError, OSError) as err:
        parser.error(str(err))
    process_result = execute(command, args.output, args.timeout)
    stdout = (args.output / 'stdout.txt').read_text(encoding='utf-8', errors='replace')
    logs = '\n'.join(path.read_text(encoding='utf-8', errors='replace') for path in
                     [args.output / 'stdout.txt', args.output / 'stderr.txt', args.output / 'config' / 'openmw.log']
                     if path.is_file())
    result = {'run_id': run_id, 'command': command, 'platform': sys.platform,
              'probe_sha256': sha256(args.output / 'data' / 'scripts' / 'omw_runtime_test' / 'case.lua'),
              'runner_sha256': sha256(__file__), 'content': args.content,
              **process_result, **assess(stdout, logs, run_id, process_result)}
    (args.output / 'result.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    for marker in result['markers']:
        print(marker['line'])
    print(('PASS' if result['passed'] else 'FAIL') + ': ' + str(args.output / 'result.json'))
    for reason in result['reasons']:
        print(reason)
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
