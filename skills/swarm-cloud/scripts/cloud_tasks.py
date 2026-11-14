import argparse
import contextlib
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import tempfile
import time
import uuid


class RunError(Exception):
    pass


def stamp():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text())


def atomic(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix='.pending-')
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def save(root, state):
    atomic(root / 'state.json', json.dumps(state, indent=2) + '\n')


@contextlib.contextmanager
def locked(root):
    if not root.is_dir():
        raise RunError('Run directory does not exist')
    with (root / '.lock').open('a') as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RunError('Another command owns this run') from None
        yield


def command(argv, cwd=None, input_text=None):
    try:
        result = subprocess.run(argv, cwd=cwd, input=input_text, capture_output=True,
                                text=True, timeout=90)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RunError(f'Command could not finish: {error}') from error
    if result.returncode:
        raise RunError(f'Command failed ({result.returncode}): {result.stderr.strip()}')
    return result.stdout


def cloud(*args, **kwargs):
    return command(['codex', 'cloud', *args], **kwargs)


def git(state, *args):
    return command(['git', *args], cwd=state['repository']).strip()


def event(root, phase, decision, evidence='', result='open'):
    path = root / 'decisions.tsv'
    def cell(value):
        value = str(value).replace('\t', ' ').replace('\n', ' ')
        return "'" + value if value[:1] in ('=', '+', '-', '@') else value
    with path.open('a') as stream:
        if stream.tell() == 0:
            stream.write('ts\tphase\tdecision\twhy\tevidence\tresult\n')
        stream.write('\t'.join(map(cell, [stamp(), phase, decision,
                                          'Recoverable plan coordination', evidence, result])) + '\n')


def definition(state):
    fields = ('id', 'title', 'backend', 'depends_on', 'branch', 'brief', 'acceptance', 'allowed_paths')
    value = {key: state[key] for key in ('repository', 'environment', 'max_parallel')}
    value['tasks'] = [{key: task[key] for key in fields} for task in state['tasks']]
    return digest(json.dumps(value, sort_keys=True).encode())


def validate(state):
    if state.get('version') != 1 or not isinstance(state.get('tasks'), list):
        raise RunError('Unsupported run state')
    ids = [task['id'] for task in state['tasks']]
    if len(ids) != len(set(ids)) or not ids:
        raise RunError('Task IDs must be unique and nonempty')
    seen = set()
    visiting = set()
    tasks = {task['id']: task for task in state['tasks']}
    def visit(item):
        if item not in tasks:
            raise RunError(f'Unknown dependency: {item}')
        if item in visiting:
            raise RunError('Dependency cycle')
        if item in seen:
            return
        visiting.add(item)
        for dep in tasks[item]['depends_on']:
            visit(dep)
        visiting.remove(item)
        seen.add(item)
    for task in state['tasks']:
        if not all(isinstance(task.get(key), str) for key in ('id', 'title', 'backend', 'branch', 'brief')):
            raise RunError('Task names, backend, branch, and brief must be strings')
        for key in ('depends_on', 'acceptance', 'allowed_paths'):
            if not isinstance(task.get(key), list) or not all(isinstance(v, str) for v in task[key]):
                raise RunError(key + ' must be a list of strings')
        if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}', task['id']):
            raise RunError('Task IDs must be simple path-safe names')
        if task['backend'] not in ('cloud', 'sub'):
            raise RunError('Backend must be cloud or sub')
        if not task['acceptance'] or not task['brief'] or not task['branch']:
            raise RunError('Every task needs a brief, branch, and acceptance checks')
        visit(task['id'])
    if state['max_parallel'] < 1:
        raise RunError('max_parallel must be positive')
    if state.get('definition_hash') != definition(state):
        raise RunError('Plan definition changed; create a revised run rather than reusing receipts')


def load(root):
    state = read_json(root / 'state.json')
    validate(state)
    try:
        state['plan_changed'] = digest(Path(state['plan']['path']).read_bytes()) != state['plan']['sha256']
    except OSError:
        state['plan_changed'] = True
    return state


def task_for(state, item):
    for task in state['tasks']:
        if task['id'] == item:
            return task
    raise RunError(f'Unknown work item: {item}')


def lease_active(state):
    owner = state.get('coordinator')
    return bool(owner and owner['expires_at'] > time.time())


def require_owner(state, owner):
    if state.get('plan_changed'):
        raise RunError('Plan file changed or is unavailable; create a revised run before executing work')
    if state['scheduling']['state'] == 'paused':
        raise RunError('Scheduling is explicitly paused; resume first')
    if not lease_active(state) or state['coordinator']['owner'] != owner:
        raise RunError('Acquire or renew the coordinator lease with resume')
    state['coordinator']['expires_at'] = time.time() + 300


def accepted(root, task):
    receipt = task.get('receipt')
    if not receipt or task['status'] != 'completed' or task.get('result_error'):
        return False
    if any(receipt.get(key) != task.get(key) for key in ('task_id', 'base_sha')):
        return False
    for path, checksum in receipt['files'].items():
        p = Path(path)
        if not p.is_file() or digest(p.read_bytes()) != checksum:
            return False
    patch = task.get('patch')
    if task['backend'] == 'cloud':
        return bool(patch and receipt['patch_sha256'] == patch['sha256']
                    and (root / patch['path']).is_file()
                    and digest((root / patch['path']).read_bytes()) == patch['sha256'])
    return True


def extract_result(patch, item):
    header = f'diff --git a/.pstack-results/{item}.md b/.pstack-results/{item}.md'
    sections = patch.split('diff --git ')
    for section in sections:
        if not ('diff --git ' + section).startswith(header + '\n'):
            continue
        if '\n--- /dev/null\n' not in section:
            return None
        additions = []
        in_hunk = False
        for line in section.splitlines():
            if line.startswith('@@ '):
                in_hunk = True
            elif in_hunk and line.startswith('+'):
                additions.append(line[1:])
        return '\n'.join(additions) + '\n' if additions else None
    return None


def frontier(root, state):
    if state.get('plan_changed'):
        return []
    return [task['id'] for task in state['tasks']
            if not task.get('task_id') and task['status'] == 'planned'
            and all(accepted(root, task_for(state, dep)) for dep in task['depends_on'])]


def listed_tasks():
    tasks = {}
    cursor = None
    visited = set()
    while True:
        args = ['list', '--json', '--limit', '20']
        if cursor:
            args += ['--cursor', cursor]
        page = json.loads(cloud(*args))
        if not isinstance(page.get('tasks'), list):
            raise RunError('Unrecognized cloud task-list response')
        for task in page['tasks']:
            tasks[task['id']] = task
        cursor = page.get('cursor')
        if not cursor:
            return tasks
        if cursor in visited:
            raise RunError('Cloud pagination repeated a cursor')
        visited.add(cursor)


def refresh(root, state):
    state['check_errors'] = []
    try:
        rows = listed_tasks()
    except (RunError, ValueError, KeyError, TypeError) as error:
        rows = {}
        state['check_errors'].append(str(error))
    for task in state['tasks']:
        if task['backend'] != 'cloud' or not task.get('task_id'):
            continue
        row = rows.get(task['task_id'])
        task['last_checked'] = stamp()
        if row is None:
            task['status'] = 'unknown'
            task['observation'] = 'Task missing from list or cloud status unavailable'
            continue
        status = row.get('status')
        task['provider_status'] = status
        task['status'] = {'pending': 'pending', 'ready': 'completed',
                          'applied': 'completed', 'error': 'failed'}.get(status, 'unknown')
        task['observation'] = 'Cloud pending may mean queued or running' if status == 'pending' else str(status)
        if task['status'] == 'completed':
            try:
                patch = cloud('diff', task['task_id'], '--attempt', '1')
                if not patch.strip():
                    raise RunError('No patch returned; report-only task needs a result file in its diff')
                checksum = digest(patch.encode())
                path = f"results/{task['id']}/{checksum}.patch"
                if not (root / path).exists():
                    atomic(root / path, patch)
                artifact = {'path': path, 'sha256': checksum}
                if artifact not in task.setdefault('patch_history', []):
                    task['patch_history'].append(artifact)
                task['patch'] = artifact
                result = extract_result(patch, task['id'])
                if result:
                    result_path = f"results/{task['id']}/{checksum}.md"
                    if not (root / result_path).exists():
                        atomic(root / result_path, result)
                    task['result_path'] = result_path
                    task['result_summary'] = result.strip()[:2000]
                else:
                    task.pop('result_path', None)
                    task.pop('result_summary', None)
                task['result_error'] = None
            except RunError as error:
                task['result_error'] = str(error)
    state['last_checked'] = stamp()
    save(root, state)


def report(root, state, offline=False):
    scheduler = 'paused' if state['scheduling']['state'] == 'paused' else (
        'active' if lease_active(state) else 'orphaned')
    ready = frontier(root, state)
    tasks = []
    remaining = {task['id'] for task in state['tasks']}
    waves = []
    while remaining:
        wave = [task['id'] for task in state['tasks'] if task['id'] in remaining
                and not (set(task['depends_on']) & remaining)]
        waves.append(wave)
        remaining.difference_update(wave)
    for task in state['tasks']:
        ok = accepted(root, task) and not state.get('plan_changed')
        stage = 'accepted' if ok else ('verification pending' if task.get('patch') else 'not retrieved')
        if state.get('plan_changed'):
            next_action = 'inspect saved plan and create a revised run; observation and pause remain available'
        elif ok:
            next_action = 'none'
        elif task['status'] == 'submission_unknown':
            next_action = 'reconcile the saved submission token before retrying'
        elif task.get('result_error'):
            next_action = 'retrieve missing result evidence'
        elif task['status'] == 'completed':
            next_action = 'independently verify and integrate the result'
        elif task['id'] in ready:
            next_action = 'resume scheduling' if scheduler != 'active' else 'submit this ready item'
        elif task['status'] == 'planned':
            next_action = 'wait for accepted and integrated dependencies'
        elif task['status'] == 'failed':
            next_action = 'diagnose the failure before defining replacement work'
        else:
            next_action = 'refresh worker status; do not submit a replacement'
        tasks.append({'id': task['id'], 'title': task['title'], 'backend': task['backend'],
                      'dependencies': task['depends_on'], 'task_id': task.get('task_id'),
                      'worker_state': task['status'], 'result': stage,
                      'ready': task['id'] in ready, 'evidence': task.get('receipt'),
                      'worker_report': task.get('result_summary'),
                      'next_action': next_action,
                      'detail': task.get('result_error') or task.get('observation', '')})
    return {'run_id': state['run_id'], 'scheduling': scheduler,
            'plan_changed': state.get('plan_changed', False),
            'pause_reason': state['scheduling'].get('reason'),
            'last_checked': state.get('last_checked'), 'offline': offline,
            'planned_parallel_groups': waves, 'ready_to_schedule': ready,
            'active_or_uncertain': [t['id'] for t in state['tasks']
                                    if t['status'] in ('pending', 'running', 'unknown', 'submission_unknown')],
            'errors': state.get('check_errors', []), 'tasks': tasks}


def print_report(value, as_json):
    if as_json:
        print(json.dumps(value, indent=2))
        return
    print(f"Run {value['run_id']} | scheduling: {value['scheduling']} | checked: {value['last_checked']}")
    if value['offline']:
        print('OFFLINE: saved observations only; no live status refreshed')
    if value['plan_changed']:
        print('PLAN CHANGED OR UNAVAILABLE: execution held; worker observation and pause remain available')
    if value['pause_reason']:
        print('Pause reason: ' + value['pause_reason'])
    print('Planned parallel groups: ' + ' -> '.join(', '.join(w) for w in value['planned_parallel_groups']))
    print('Active or uncertain: ' + (', '.join(value['active_or_uncertain']) or 'none'))
    print('Ready but not submitted: ' + (', '.join(value['ready_to_schedule']) or 'none'))
    for task in value['tasks']:
        deps = ','.join(task['dependencies']) or 'none'
        print(f"{task['id']} | {task['title']} | {task['backend']} | deps={deps} | "
              f"worker={task['task_id'] or 'not submitted'} | {task['worker_state']} | "
              f"{task['result']} | {task['detail']} | next={task['next_action']}")
        if task['evidence']:
            print('Evidence: ' + ', '.join(task['evidence']['files']) +
                  ' | integrated=' + task['evidence']['integrated_sha'])
        if task.get('worker_report'):
            print('Worker report (unverified): ' + task['worker_report'])
    for error in value['errors']:
        print('Status error: ' + error)
    print('Next: resume coordination if permitted, verify retrieved results, then submit dependency-ready items.')


def initialize(args):
    root = args.run.resolve()
    root.mkdir(parents=True, exist_ok=True)
    with locked(root):
        if (root / 'state.json').exists():
            raise RunError('Run already exists')
        spec = read_json(args.spec)
        tasks = []
        for source in spec['tasks']:
            fields = {key: source[key] for key in ('id', 'title', 'branch', 'brief', 'acceptance')}
            tasks.append({**fields, 'backend': source.get('backend', 'cloud'),
                          'depends_on': source.get('depends_on', []),
                          'allowed_paths': source.get('allowed_paths', []),
                          'status': 'planned'})
        state = {'version': 1, 'run_id': uuid.uuid4().hex, 'repository': str(args.repo.resolve()),
                 'environment': args.env, 'max_parallel': args.max_parallel,
                 'plan': {'path': str(args.plan.resolve()), 'sha256': digest(args.plan.read_bytes())},
                 'tasks': tasks, 'scheduling': {'state': 'active', 'reason': None}, 'coordinator': None}
        state['definition_hash'] = definition(state)
        validate(state)
        git(state, 'rev-parse', '--show-toplevel')
        atomic(root / 'plan.md', args.plan.read_text())
        save(root, state)
        event(root, 'start', 'Initialized cloud coordination', state['plan']['path'])
        print_report(report(root, state, True), args.json)


def submit(root, state, args):
    require_owner(state, args.owner)
    task = task_for(state, args.item)
    if task['backend'] != 'cloud':
        raise RunError('Use native collaboration for subagent tasks, then record-sub')
    refresh(root, state)
    if state['check_errors']:
        raise RunError('Cloud status unavailable; submission held')
    if args.item not in frontier(root, state):
        raise RunError('Item already submitted, uncertain, or dependencies not accepted')
    occupied = sum(task['status'] in ('pending', 'running', 'unknown', 'submission_unknown')
                   for task in state['tasks'])
    if occupied >= state['max_parallel']:
        raise RunError('Parallel limit reached, including uncertain workers')
    if not state['environment']:
        raise RunError('Cloud environment ID is required')
    ref = 'refs/heads/' + task['branch']
    git(state, 'check-ref-format', ref)
    remote = git(state, 'ls-remote', 'origin', ref).split()
    if len(remote) != 2 or remote[1] != ref:
        raise RunError('Branch must exist on origin before submission')
    base = remote[0]
    git(state, 'cat-file', '-e', base + '^{commit}')
    for dep in task['depends_on']:
        receipt = task_for(state, dep)['receipt']
        git(state, 'merge-base', '--is-ancestor', receipt['integrated_sha'], base)
    task['base_sha'] = base
    task['status'] = 'submission_unknown'
    task['submission_token'] = uuid.uuid4().hex
    save(root, state)
    prompt = (f"Run {state['run_id']}, work item {task['id']}, submission {task['submission_token']}.\n"
              f"Verify git HEAD equals {base} before work. A different HEAD is BLOCKED.\n"
              f"Goal: {task['brief']}\nAllowed application paths: {json.dumps(task['allowed_paths'])}\n"
              f"Acceptance checks: {json.dumps(task['acceptance'])}\n"
              'Do not push, merge, deploy, or start nested cloud tasks.\n'
              f"Return commands and actual output in .pstack-results/{task['id']}.md, "
              'including actual starting HEAD and PASS, ISSUES, or BLOCKED. '
              'Stage that result file so it is included in the returned diff. '
              'Keep evidence free of credentials. A remote filesystem path is not a downloaded artifact.')
    atomic(root / 'briefs' / (task['id'] + '.txt'), prompt)
    event(root, 'submit', 'Recorded submission intent for ' + task['id'], task['submission_token'])
    output = cloud('exec', '--env', state['environment'], '--branch', task['branch'],
                   '--attempts', '1', prompt, cwd=state['repository'])
    matches = re.findall(r'https://chatgpt\.com/[^\s]*/(task_[A-Za-z0-9_-]+)', output)
    if len(set(matches)) != 1:
        raise RunError('Submission outcome uncertain; reconcile task ID before retrying')
    if any(other.get('task_id') == matches[0] for other in state['tasks']):
        raise RunError('Provider returned an already registered task ID; reconcile before retrying')
    task['task_id'] = matches[0]
    task['status'] = 'pending'
    save(root, state)
    event(root, 'submit', 'Cloud task submitted for ' + task['id'], task['task_id'])


def accept(root, state, args):
    require_owner(state, args.owner)
    task = task_for(state, args.item)
    if task['status'] != 'completed':
        raise RunError('Worker must have completed before acceptance')
    receipt = read_json(args.receipt)
    for field in ('task_id', 'base_sha'):
        if not task.get(field) or receipt.get(field) != task[field]:
            raise RunError('Receipt does not match ' + field)
    if task['backend'] == 'cloud':
        patch = task.get('patch')
        if not patch or receipt.get('patch_sha256') != patch['sha256']:
            raise RunError('Receipt must match the retrieved patch')
        if digest((root / patch['path']).read_bytes()) != patch['sha256']:
            raise RunError('Retrieved patch changed')
        if task.get('result_error'):
            raise RunError('Latest result retrieval failed')
    if receipt.get('verified_sha') != receipt.get('integrated_sha') or not receipt.get('integrated_sha'):
        raise RunError('Verification must cover the integrated commit')
    integrated = receipt['integrated_sha']
    if git(state, 'rev-parse', integrated + '^{commit}') != integrated:
        raise RunError('Integrated commit must be a full SHA')
    git(state, 'merge-base', '--is-ancestor', integrated, 'HEAD')
    git(state, 'merge-base', '--is-ancestor', task['base_sha'], integrated)
    checks = receipt.get('checks', [])
    covered = {check.get('criterion') for check in checks if check.get('exit_code') == 0}
    if covered != set(task['acceptance']) or not receipt.get('evidence'):
        raise RunError('Receipt must cover every acceptance criterion and include evidence')
    files = {}
    paths = list(receipt['evidence']) + [check['output'] for check in checks]
    for check in checks:
        if not check.get('command') or check.get('exit_code') != 0:
            raise RunError('Every recorded acceptance check must have passed')
    for path in paths:
        p = Path(path).resolve()
        if not p.is_file() or not p.stat().st_size:
            raise RunError('Evidence missing or empty: ' + str(p))
        files[str(p)] = digest(p.read_bytes())
    receipt['files'] = files
    task['receipt'] = receipt
    save(root, state)
    event(root, 'accept', 'Accepted verified and integrated result for ' + task['id'], integrated, 'accepted')


def operate(args):
    root = args.run.resolve()
    with locked(root):
        state = load(root)
        action = args.action
        if action == 'check':
            if not args.offline:
                refresh(root, state)
        elif action == 'pause':
            state['scheduling'] = {'state': 'paused', 'reason': args.reason}
            state['coordinator'] = None
            event(root, 'pause', 'Paused scheduling; cloud workers may continue', result='paused')
        elif action == 'resume':
            if state.get('plan_changed'):
                raise RunError('Plan file changed or is unavailable; create a revised run before resuming')
            if lease_active(state) and state['coordinator']['owner'] != args.owner:
                raise RunError('Another coordinator holds an unexpired lease')
            refresh(root, state)
            state['scheduling'] = {'state': 'active', 'reason': None}
            state['coordinator'] = {'owner': args.owner, 'host': socket.gethostname(),
                                    'expires_at': time.time() + 300}
            event(root, 'resume', 'Coordinator acquired lease: ' + args.owner)
        elif action == 'submit':
            submit(root, state, args)
        elif action == 'accept':
            accept(root, state, args)
        elif action == 'bind':
            require_owner(state, args.owner)
            task = task_for(state, args.item)
            if task['status'] != 'submission_unknown' or task.get('task_id'):
                raise RunError('Only an uncertain submission can be bound')
            rows = listed_tasks()
            if args.task_id not in rows:
                raise RunError('Task ID not found; verify ownership and submission token manually')
            if args.submission_token != task.get('submission_token'):
                raise RunError('Confirm the saved submission token before binding')
            if rows[args.task_id].get('environment_id') != state['environment']:
                raise RunError('Task belongs to a different or unverified cloud environment')
            if any(t.get('task_id') == args.task_id for t in state['tasks']):
                raise RunError('Task ID already assigned')
            task.update(task_id=args.task_id, status='unknown')
            event(root, 'bind', 'Operator reconciled submission for ' + task['id'], args.task_id)
        elif action == 'record-sub':
            require_owner(state, args.owner)
            task = task_for(state, args.item)
            if task['backend'] != 'sub':
                raise RunError('record-sub only accepts native subagent items')
            if task.get('task_id') not in (None, args.task_id):
                raise RunError('Native agent ID differs from registered worker')
            if task.get('base_sha') not in (None, args.base_sha):
                raise RunError('Native agent base changed; start a revised work item')
            if not task.get('task_id') and args.item not in frontier(root, state):
                raise RunError('Dependencies not accepted')
            if not task.get('task_id') and sum(t['status'] in (
                    'pending', 'running', 'unknown', 'submission_unknown') for t in state['tasks']) >= state['max_parallel']:
                raise RunError('Parallel limit reached')
            if git(state, 'rev-parse', args.base_sha + '^{commit}') != args.base_sha:
                raise RunError('Native base must be a full commit SHA')
            for dep in task['depends_on']:
                git(state, 'merge-base', '--is-ancestor',
                    task_for(state, dep)['receipt']['integrated_sha'], args.base_sha)
            task.update(task_id=args.task_id, status=args.status, base_sha=args.base_sha,
                        observation='Coordinator observation of native subagent', last_checked=stamp())
        save(root, state)
        value = report(root, state, getattr(args, 'offline', False))
        atomic(root / 'results' / 'latest-status.json', json.dumps(value, indent=2) + '\n')
        print_report(value, args.json)


def parser():
    p = argparse.ArgumentParser(description='Durable Codex Cloud task registry and recovery checker')
    commands = p.add_subparsers(dest='action', required=True)
    for name in ('init', 'check', 'watch', 'pause', 'resume', 'submit', 'bind', 'accept', 'record-sub'):
        child = commands.add_parser(name)
        child.add_argument('--run', required=True, type=Path)
        child.add_argument('--json', action='store_true')
        if name == 'init':
            for arg in ('plan', 'spec', 'repo'):
                child.add_argument('--' + arg, required=True, type=Path)
            child.add_argument('--env', default='')
            child.add_argument('--max-parallel', type=int, default=2)
        if name == 'check':
            child.add_argument('--offline', action='store_true')
        if name == 'watch':
            child.add_argument('--interval', type=float, default=30)
            child.add_argument('--iterations', type=int, default=10)
        if name == 'pause':
            child.add_argument('--reason', required=True)
        if name in ('resume', 'submit', 'bind', 'accept', 'record-sub'):
            child.add_argument('--owner', required=True)
        if name in ('submit', 'bind', 'accept', 'record-sub'):
            child.add_argument('--item', required=True)
        if name in ('bind', 'record-sub'):
            child.add_argument('--task-id', required=True)
        if name == 'bind':
            child.add_argument('--submission-token', required=True)
        if name == 'accept':
            child.add_argument('--receipt', required=True, type=Path)
        if name == 'record-sub':
            child.add_argument('--status', required=True, choices=('running', 'completed', 'failed', 'unknown'))
            child.add_argument('--base-sha', required=True)
    return p


def main():
    args = parser().parse_args()
    try:
        if args.action == 'init':
            initialize(args)
        elif args.action == 'watch':
            if args.interval < 1 or args.iterations < 1:
                raise RunError('Watch requires positive iterations and interval >= 1 second')
            args.action = 'check'
            args.offline = False
            for index in range(args.iterations):
                operate(args)
                if index + 1 < args.iterations:
                    time.sleep(args.interval)
        else:
            operate(args)
        return 0
    except (RunError, OSError, ValueError, KeyError, TypeError) as error:
        print('BLOCKED: ' + str(error), file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print('Local watch stopped; cloud workers were not cancelled.', file=sys.stderr)
        return 130


if __name__ == '__main__':
    sys.exit(main())
