import contextlib
import fcntl
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch


HELPER = Path(__file__).resolve().parents[1] / 'scripts' / 'cloud_tasks.py'
SPEC = importlib.util.spec_from_file_location('cloud_tasks', HELPER)
cloud_tasks = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cloud_tasks)
SMOKE_TRANSCRIPTS = HELPER.parents[3] / '.pstack/runs/primes-smoke-20261114/transcripts'


def task(identifier, dependencies=None, backend='cloud'):
    return {'id': identifier, 'title': 'Work ' + identifier, 'brief': 'Produce ' + identifier,
            'backend': backend, 'depends_on': dependencies or [],
            'acceptance': ['output verified'], 'allowed_paths': ['result.txt']}


def environment(identifier='default-id', name='Default environment', runnable=True):
    return {'environmentConfigId': identifier, 'name': name, 'runnable': runnable,
            'repositories': []}


def wrapped(value):
    return {'content': [{'type': 'text', 'text': json.dumps(value)}], 'isError': False}


class DesktopRunFixture(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.run = self.directory / 'run'
        self.plan = self.directory / 'plan.md'
        self.plan.write_text('Produce a, independently verify it, then produce b.\n')
        self.spec = self.directory / 'spec.json'
        self.counter = 0
        self.initialize()

    def write_json(self, value):
        self.counter += 1
        path = self.directory / ('input-' + str(self.counter) + '.json')
        path.write_text(json.dumps(value))
        return path

    def invoke(self, action, **options):
        arguments = [action, '--run', str(self.run), '--json']
        for key, value in options.items():
            if value is None or value is False:
                continue
            arguments.append('--' + key.replace('_', '-'))
            if value is not True:
                arguments.append(str(value))
        args = cloud_tasks.parser().parse_args(arguments)
        with contextlib.redirect_stdout(io.StringIO()) as output:
            cloud_tasks.initialize(args) if action == 'init' else cloud_tasks.operate(args)
        return json.loads(output.getvalue())

    def initialize(self, tasks=None, **options):
        self.spec.write_text(json.dumps({'tasks': tasks if tasks is not None else [task('a'), task('b', ['a'])]}))
        return self.invoke('init', spec=self.spec, plan=self.plan, **options)

    def state(self):
        return cloud_tasks.load(self.run)

    def item(self, identifier='a'):
        return cloud_tasks.task_for(self.state(), identifier)

    def configure(self, rows=None, **page):
        return self.invoke('configure', environments=self.write_json(
            {'environments': rows if rows is not None else [environment()], **page}))

    def ready(self):
        self.configure()
        self.invoke('resume', owner='coordinator')

    def prepare(self, identifier='a'):
        return self.invoke('prepare', item=identifier, owner='coordinator')

    def bind(self, identifier='a', response=None, token=None):
        response = response if response is not None else {'threadId': 'thread-' + identifier, 'hostId': 'durable'}
        return self.invoke('bind', item=identifier,
                           submission_token=token or self.item(identifier)['submission_token'],
                           response=self.write_json(response))

    def transcript(self, identifier='a', status='completed', started=100, final='PASS verified result'):
        items = [{'type': 'agentMessage', 'phase': 'commentary', 'text': 'working'}]
        if final is not None:
            items.append({'type': 'agentMessage', 'phase': 'final_answer', 'text': final})
        return {'schemaVersion': 1, 'thread': {'id': 'thread-' + identifier, 'hostId': 'durable'},
                'page': {'order': 'newest_first', 'nextCursor': None, 'hasMore': False},
                'turns': [{'id': 'turn-' + str(started), 'status': status, 'error': None,
                           'startedAt': started, 'items': items}]}

    def observe(self, response=None, identifier='a'):
        return self.invoke('observe', item=identifier,
                           response=self.write_json(response if response is not None else self.transcript(identifier)))

    def completed(self):
        self.ready()
        self.prepare()
        self.bind()
        self.observe()
        return self.item()

    def receipt(self, item=None, **changes):
        item = item or self.item()
        output = self.directory / 'verified-output.txt'
        output.write_text('Independent local verifier passed\n')
        value = {'task_id': item['task_id'], 'base_sha': item['base_sha'],
                 'artifact_sha256': item['artifact']['sha256'], 'evidence': [str(output)],
                 'checks': [{'criterion': 'output verified', 'command': 'python verify.py',
                             'exit_code': 0, 'output': str(output)}], **changes}
        return self.write_json(value)

    def accept(self, receipt=None):
        return self.invoke('accept', item='a', owner='coordinator', receipt=receipt or self.receipt())


class DesktopRunTests(DesktopRunFixture):
    def test_initialization_records_graph_and_does_not_import_runtime_fields(self):
        self.run = self.directory / 'fresh'
        untrusted = task('a')
        untrusted.update(task_id='injected', receipt={'files': {}}, status='completed')
        result = self.initialize([untrusted, task('b', ['a'])])
        self.assertEqual(result['transport'], 'desktop-tools')
        self.assertEqual(result['planned_parallel_groups'], [['a'], ['b']])
        self.assertEqual(result['ready_to_schedule'], ['a'])
        self.assertIsNone(self.item().get('task_id'))
        self.assertIsNone(self.item().get('receipt'))
        self.assertIsNone(self.state()['repository'])
        self.assertIsNone(self.state()['environment_request'])
        with self.assertRaises(cloud_tasks.RunError):
            self.initialize()

    def test_default_environment_is_discovered_from_runnable_rows(self):
        self.configure([environment('other', 'Other'), environment()])
        self.assertEqual(self.state()['environment']['environmentConfigId'], 'default-id')

    def test_explicit_environment_matches_id_before_name(self):
        for requested in ('chosen', 'Custom'):
            with self.subTest(requested=requested):
                self.run = self.directory / requested
                self.initialize(env=requested)
                self.configure([environment(), environment('chosen', 'Custom')])
                self.assertEqual(self.state()['environment']['environmentConfigId'], 'chosen')

    def test_environment_requires_complete_unique_runnable_selection(self):
        cases = [({'nextCursor': 'next'}, [environment()]),
                 ({}, [environment(runnable=False)]), ({}, [environment('a'), environment('b')]),
                 ({}, [environment(name='Other')])]
        for page, rows in cases:
            with self.subTest(page=page, rows=rows), self.assertRaises(cloud_tasks.RunError):
                self.configure(rows, **page)
        self.assertIsNone(self.state()['environment'])

    def test_environment_identity_cannot_change_after_configuration(self):
        self.configure()
        with self.assertRaises(cloud_tasks.RunError):
            self.configure([environment('changed')])
        self.assertEqual(self.state()['environment']['environmentConfigId'], 'default-id')

    def test_prepare_persists_intent_before_returning_create_request(self):
        self.ready()
        with patch.object(cloud_tasks.subprocess, 'run', side_effect=AssertionError('external execution')):
            request = self.prepare()
        item = self.item()
        self.assertEqual(item['status'], 'submission_unknown')
        self.assertEqual(item['submission_token'], request['submission_token'])
        self.assertEqual(request['tool'], 'mcp__codex_app__create_thread')
        self.assertEqual(request['arguments']['target'], {'type': 'codexCloud', 'environmentConfigId': 'default-id'})
        self.assertEqual(json.loads((self.run / 'briefs/a.json').read_text()), request['arguments'])
        self.assertIsNone(item['base_sha'])
        before = (self.run / 'state.json').read_bytes()
        with self.assertRaises(cloud_tasks.RunError):
            self.prepare()
        self.assertEqual((self.run / 'state.json').read_bytes(), before)

    def test_prepare_requires_configuration_and_active_owned_lease(self):
        for setup in ('none', 'lease', 'environment'):
            with self.subTest(setup=setup):
                self.run = self.directory / setup
                self.initialize()
                if setup == 'lease':
                    self.invoke('resume', owner='coordinator')
                if setup == 'environment':
                    self.configure()
                with self.assertRaises(cloud_tasks.RunError):
                    self.prepare()
                self.assertEqual(self.item()['status'], 'planned')

    def test_bind_requires_saved_token_host_and_unique_thread(self):
        self.run = self.directory / 'independent'
        self.initialize([task('a'), task('b')])
        self.ready()
        self.prepare('a')
        self.prepare('b')
        for response, token in [({}, None), ({'threadId': 't'}, None),
                                ({'threadId': 't', 'hostId': 'durable'}, 'wrong')]:
            with self.subTest(response=response), self.assertRaises(cloud_tasks.RunError):
                self.bind(response=response, token=token)
        self.bind()
        with self.assertRaises(cloud_tasks.RunError):
            self.bind('b', {'threadId': 'thread-a', 'hostId': 'durable'})
        self.assertEqual(self.item('b')['status'], 'submission_unknown')

    def test_binding_rejects_non_string_desktop_identities(self):
        for index, response in enumerate(({'threadId': 12, 'hostId': 'durable'},
                                          {'threadId': 'thread-a', 'hostId': ['durable']},
                                          {'clientThreadId': {'id': 'client-a'}})):
            with self.subTest(response=response):
                self.run = self.directory / ('bad-identity-' + str(index))
                self.initialize()
                self.ready()
                self.prepare()
                before = self.item()
                with self.assertRaises(cloud_tasks.RunError):
                    self.bind(response=response)
                self.assertEqual(self.item(), before)

    def test_native_registration_requires_accepted_dependencies_and_stable_identity(self):
        self.run = self.directory / 'native-run'
        self.initialize([task('a', backend='sub'), task('b', ['a'], backend='sub')])
        self.invoke('resume', owner='coordinator')
        with self.assertRaises(cloud_tasks.RunError):
            self.invoke('record-sub', owner='coordinator', item='b', task_id='native-b', status='running')
        self.invoke('record-sub', owner='coordinator', item='a', task_id='native-a', status='completed')
        with self.assertRaises(cloud_tasks.RunError):
            self.invoke('record-sub', owner='coordinator', item='b', task_id='native-b', status='running')
        output = self.directory / 'native-output.txt'
        output.write_text('Independent native output verification passed\n')
        receipt = self.write_json({'task_id': 'native-a', 'base_sha': None, 'evidence': [str(output)],
                                  'checks': [{'criterion': 'output verified', 'command': 'python verify.py',
                                              'exit_code': 0, 'output': str(output)}]})
        self.accept(receipt)
        self.invoke('record-sub', owner='coordinator', item='b', task_id='native-b', status='running')
        with self.assertRaises(cloud_tasks.RunError):
            self.invoke('record-sub', owner='coordinator', item='b', task_id='replacement', status='completed')
        self.assertEqual(self.item('b')['task_id'], 'native-b')

    def test_client_only_response_remains_uncertain_until_thread_is_bound(self):
        self.ready()
        self.prepare()
        self.bind(response={'clientThreadId': 'client-a'})
        self.assertEqual(self.item()['status'], 'submission_unknown')
        self.assertIsNone(self.item()['task_id'])
        with self.assertRaises(cloud_tasks.RunError):
            self.prepare()
        self.bind(response={'threadId': 'thread-a', 'hostId': 'durable'})
        self.assertEqual(self.item()['task_id'], 'thread-a')
        self.assertEqual(self.item()['client_thread_id'], 'client-a')

    def test_pending_client_identity_cannot_be_replaced_or_shared(self):
        self.run = self.directory / 'client-identity'
        self.initialize([task('a'), task('b')])
        self.ready()
        self.prepare('a')
        self.prepare('b')
        self.bind(response={'clientThreadId': 'client-a'})
        for identifier, response in [('a', {'clientThreadId': 'different'}),
                                     ('b', {'clientThreadId': 'client-a'}),
                                     ('a', {'threadId': 'thread-a', 'hostId': 'durable', 'clientThreadId': 'different'})]:
            with self.subTest(identifier=identifier, response=response), self.assertRaises(cloud_tasks.RunError):
                self.bind(identifier, response)

    def test_replaying_bind_preserves_terminal_observation_and_host_identity(self):
        self.completed()
        before = self.item()
        self.bind()
        self.assertEqual(self.item()['status'], 'completed')
        self.assertEqual(self.item()['artifact'], before['artifact'])

    def test_bound_host_identity_cannot_be_replaced(self):
        self.completed()
        before = self.item()
        with self.assertRaises(cloud_tasks.RunError):
            self.bind(response={'threadId': 'thread-a', 'hostId': 'different-host'})
        self.assertEqual(self.item(), before)

    def test_all_uncertain_workers_occupy_capacity(self):
        for status in ('pending', 'running', 'unknown', 'submission_unknown'):
            with self.subTest(status=status):
                self.run = self.directory / status
                self.initialize([task('a', backend='sub'), task('b')], max_parallel=1)
                self.ready()
                self.invoke('record-sub', owner='coordinator', item='a', task_id='native-a', status='unknown')
                state = self.state()
                state['tasks'][0]['status'] = status
                cloud_tasks.save(self.run, state)
                with self.assertRaises(cloud_tasks.RunError):
                    self.prepare('b')
                self.assertEqual(self.item('b')['status'], 'planned')

    def test_observation_uses_real_turn_shape_and_preserves_complete_artifact(self):
        self.ready()
        self.prepare()
        self.bind()
        response = self.transcript()
        response['turns'].append(self.transcript(status='failed', started=50)['turns'][0])
        result = self.observe(wrapped(response))
        item = self.item()
        self.assertEqual(item['status'], 'completed')
        self.assertEqual(item['result_summary'], 'PASS verified result')
        self.assertEqual(json.loads((self.run / item['artifact']['path']).read_text()), response)
        self.assertEqual(result['ready_to_schedule'], [])
        self.observe(response)
        self.assertEqual(len(self.item()['artifact_history']), 1)

    def test_real_smoke_transcripts_can_be_imported_without_live_calls(self):
        paths = sorted(SMOKE_TRANSCRIPTS.glob('*.json'))
        if not paths:
            self.skipTest('Local smoke transcripts are unavailable')
        for index, path in enumerate(paths):
            with self.subTest(transcript=path.name):
                response = json.loads(path.read_text())
                self.run = self.directory / ('smoke-' + str(index))
                self.initialize([task('a')])
                self.ready()
                self.prepare()
                self.bind(response={'threadId': response['thread']['id'], 'hostId': response['thread']['hostId']})
                self.observe(response)
                self.assertEqual(self.item()['status'], 'completed')
                self.assertTrue(self.item()['result_summary'])
                self.assertEqual(json.loads((self.run / self.item()['artifact']['path']).read_text()), response)
                self.assertFalse(cloud_tasks.accepted(self.run, self.item()))

    def test_stale_and_wrong_worker_responses_preserve_latest_observation(self):
        self.completed()
        before = self.item()
        wrong_host = self.transcript()
        wrong_host['thread']['hostId'] = 'other'
        wrong_thread = self.transcript()
        wrong_thread['thread']['id'] = 'other'
        for response in [wrong_host, wrong_thread, self.transcript(started=50), self.transcript(status='inProgress')]:
            with self.subTest(response=response), self.assertRaises(cloud_tasks.RunError):
                self.observe(response)
            self.assertEqual(self.item(), before)

    def test_errors_and_missing_current_turn_revoke_acceptance(self):
        for response in [{'isError': True, 'content': [{'type': 'text', 'text': 'unavailable'}]},
                         {'thread': {'id': 'thread-a', 'hostId': 'durable'}, 'turns': []}]:
            with self.subTest(response=response):
                self.run = self.directory / ('error-' + str(self.counter))
                self.initialize()
                self.completed()
                self.accept()
                self.observe(response)
                self.assertEqual(self.item()['status'], 'unknown')
                self.assertEqual(self.invoke('check')['ready_to_schedule'], [])

    def test_failed_interrupted_unknown_and_incomplete_completed_turns_hold_dependencies(self):
        self.completed()
        for index, status in enumerate(('failed', 'interrupted', 'new-status', 'completed')):
            with self.subTest(status=status):
                self.observe(self.transcript(status=status, started=200 + index, final=None))
                self.assertEqual(self.invoke('check')['ready_to_schedule'], [])
                with self.assertRaises(cloud_tasks.RunError):
                    self.accept()

    def test_new_running_turn_revokes_prior_completed_acceptance(self):
        self.completed()
        self.accept()
        previous_artifact = self.item()['artifact']
        self.observe(self.transcript(status='inProgress', started=200, final=None))
        self.assertEqual(self.item()['status'], 'running')
        self.assertTrue((self.run / previous_artifact['path']).is_file())
        result = self.invoke('check')
        self.assertEqual(result['ready_to_schedule'], [])
        self.assertEqual(result['active_or_uncertain'], ['a'])
        self.assertFalse(cloud_tasks.accepted(self.run, self.item()))

    def test_pause_check_and_resume_never_execute_external_tools(self):
        self.completed()
        with patch.object(cloud_tasks.subprocess, 'run', side_effect=AssertionError('external execution')):
            self.invoke('pause', reason='Review evidence')
            for offline in (False, True):
                result = self.invoke('check', offline=offline)
                self.assertEqual(result['scheduling'], 'paused')
                self.assertEqual(result['pause_reason'], 'Review evidence')
                self.assertEqual(len(result['refresh_requests']), 0 if offline else 1)
            self.assertIsNone(self.state()['coordinator'])
            with self.assertRaises(cloud_tasks.RunError):
                self.accept()
            self.invoke('resume', owner='coordinator')
        self.assertEqual(self.invoke('check')['scheduling'], 'active')

    def test_expired_or_foreign_lease_requires_explicit_takeover(self):
        self.ready()
        with self.assertRaises(cloud_tasks.RunError):
            self.invoke('resume', owner='other')
        state = self.state()
        state['coordinator']['expires_at'] = time.time() - 1
        cloud_tasks.save(self.run, state)
        self.assertEqual(self.invoke('check')['scheduling'], 'orphaned')
        with self.assertRaises(cloud_tasks.RunError):
            self.prepare()
        self.invoke('resume', owner='other')
        self.assertEqual(self.state()['coordinator']['owner'], 'other')

    def test_repository_free_acceptance_unlocks_dependency_with_actual_returned_data(self):
        self.completed()
        with self.assertRaises(cloud_tasks.RunError):
            self.prepare('b')
        self.accept()
        self.assertEqual(self.invoke('check')['ready_to_schedule'], ['b'])
        request = self.prepare('b')
        self.assertIn('PASS verified result', request['arguments']['prompt'])
        self.assertIsNone(self.item('b')['base_sha'])

    def test_accept_requires_matching_artifact_identity_and_complete_passing_evidence(self):
        self.completed()
        for mutation in ('task', 'base', 'artifact', 'criterion', 'failed', 'empty', 'missing', 'command'):
            with self.subTest(mutation=mutation):
                path = self.receipt()
                receipt = json.loads(path.read_text())
                if mutation == 'task':
                    receipt['task_id'] = 'different'
                elif mutation == 'base':
                    receipt['base_sha'] = 'different'
                elif mutation == 'artifact':
                    receipt['artifact_sha256'] = '0' * 64
                elif mutation == 'criterion':
                    receipt['checks'][0]['criterion'] = 'unrelated'
                elif mutation == 'failed':
                    receipt['checks'][0]['exit_code'] = 1
                elif mutation == 'empty':
                    Path(receipt['evidence'][0]).write_text('')
                elif mutation == 'missing':
                    receipt['checks'][0]['output'] = str(self.directory / 'missing')
                else:
                    receipt['checks'][0]['command'] = ''
                path.write_text(json.dumps(receipt))
                with self.assertRaises(cloud_tasks.RunError):
                    self.accept(path)
                self.assertFalse(cloud_tasks.accepted(self.run, self.item()))

    def test_changed_or_deleted_evidence_and_artifact_revoke_receipt(self):
        for change in ('evidence', 'artifact', 'deleted'):
            with self.subTest(change=change):
                self.run = self.directory / change
                self.initialize()
                self.completed()
                self.accept()
                item = self.item()
                path = (self.run / item['artifact']['path']) if change == 'artifact' else Path(next(iter(item['receipt']['files'])))
                path.unlink() if change == 'deleted' else path.write_text('modified\n')
                self.assertEqual(self.invoke('check')['ready_to_schedule'], [])
                self.assertFalse(cloud_tasks.accepted(self.run, self.item()))

    def test_new_result_keeps_artifact_history_and_revokes_old_receipt(self):
        self.completed()
        self.accept()
        first = self.item()['artifact']
        self.observe(self.transcript(started=200, final='PASS changed result'))
        second = self.item()['artifact']
        self.assertNotEqual(first, second)
        self.assertTrue((self.run / first['path']).is_file())
        self.assertEqual(self.item()['artifact_history'], [first, second])
        self.assertEqual(self.invoke('check')['ready_to_schedule'], [])

    def test_changed_or_missing_plan_holds_execution_while_allowing_check_and_pause(self):
        self.ready()
        for change in ('changed', 'missing'):
            with self.subTest(change=change):
                self.plan.write_text('Changed plan') if change == 'changed' else self.plan.unlink()
                result = self.invoke('check')
                self.assertTrue(result['plan_changed'])
                self.assertEqual(result['ready_to_schedule'], [])
                with self.assertRaises(cloud_tasks.RunError):
                    self.prepare()
                with self.assertRaises(cloud_tasks.RunError):
                    self.invoke('resume', owner='coordinator')
                self.invoke('pause', reason='Plan changed')

    def test_definition_drift_is_detected_before_execution(self):
        state = self.state()
        state['tasks'][0]['brief'] = 'Changed hidden scope'
        cloud_tasks.save(self.run, state)
        with self.assertRaises(cloud_tasks.RunError):
            self.invoke('check')

    def test_legacy_v1_state_allows_inspection_and_pause_only(self):
        state = self.state()
        state.update(version=1, environment='retired-environment')
        state['definition_hash'] = cloud_tasks.definition(state)
        cloud_tasks.save(self.run, state)
        result = self.invoke('check')
        self.assertEqual(result['ready_to_schedule'], [])
        self.assertEqual(result['refresh_requests'], [])
        self.invoke('pause', reason='Retired run')
        for action, values in [('resume', {'owner': 'coordinator'}),
                               ('prepare', {'owner': 'coordinator', 'item': 'a'}),
                               ('configure', {'environments': self.write_json({'environments': [environment()]})})]:
            with self.subTest(action=action), self.assertRaises(cloud_tasks.RunError):
                self.invoke(action, **values)
        self.assertEqual(self.state()['scheduling']['state'], 'paused')

    def test_mcp_wrappers_are_accepted_for_environment_and_binding(self):
        self.invoke('configure', environments=self.write_json(wrapped({'environments': [environment()]})))
        self.invoke('resume', owner='coordinator')
        self.prepare()
        self.bind(response=wrapped({'threadId': 'thread-a', 'hostId': 'durable'}))
        self.assertEqual(self.item()['host_id'], 'durable')

    def test_malformed_inputs_exit_cleanly_and_preserve_saved_state(self):
        self.ready()
        before = (self.run / 'state.json').read_bytes()
        for value in ([], None, 'text', {'content': []}, {'environments': None}):
            with self.subTest(value=value):
                path = self.write_json(value)
                arguments = ['cloud_tasks.py', 'configure', '--run', str(self.run), '--environments', str(path)]
                with patch.object(sys, 'argv', arguments), contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(cloud_tasks.main(), 2)
                self.assertEqual((self.run / 'state.json').read_bytes(), before)

    def test_invalid_graph_and_spec_are_rejected_before_registry_creation(self):
        cases = [[task('a', ['missing'])], [task('a', ['b']), task('b', ['a'])],
                 [task('a'), task('a')], [task('../escape')], [],
                 [{**task('a'), 'acceptance': []}], [{**task('a'), 'backend': 'unknown'}]]
        for index, tasks in enumerate(cases):
            with self.subTest(tasks=tasks):
                self.run = self.directory / ('invalid-' + str(index))
                with self.assertRaises(cloud_tasks.RunError):
                    self.initialize(tasks)
                self.assertFalse((self.run / 'state.json').exists())

    def test_another_process_lock_blocks_normal_cli_entrypoint(self):
        before = (self.run / 'state.json').read_bytes()
        with (self.run / '.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = subprocess.run([sys.executable, str(HELPER), 'check', '--run', str(self.run)],
                                    capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('Another command owns this run', result.stderr)
        self.assertEqual((self.run / 'state.json').read_bytes(), before)


class GitBackedRunTests(DesktopRunFixture):
    def setUp(self):
        super().setUp()
        self.repo = self.directory / 'repository'
        self.repo.mkdir()
        self.git('init', '-b', 'main')
        self.git('config', 'user.name', 'Test Worker')
        self.git('config', 'user.email', 'worker@example.invalid')
        (self.repo / 'result.txt').write_text('base\n')
        self.git('add', 'result.txt')
        self.git('commit', '-m', 'base')
        self.base = self.git('rev-parse', 'HEAD')

    def git(self, *arguments):
        return subprocess.run(['git', *arguments], cwd=self.repo, check=True,
                              capture_output=True, text=True).stdout.strip()

    def git_run(self):
        self.run = self.directory / 'git-run'
        self.initialize(repo=self.repo)
        self.completed()
        self.assertEqual(self.item()['base_sha'], self.base)

    def test_git_acceptance_requires_exact_verified_integrated_ancestry(self):
        self.git_run()
        for changes in ({}, {'integrated_sha': self.base, 'verified_sha': '0' * 40},
                        {'integrated_sha': self.base[:10], 'verified_sha': self.base[:10]}):
            with self.subTest(changes=changes), self.assertRaises(cloud_tasks.RunError):
                self.accept(self.receipt(**changes))
        self.git('checkout', '--orphan', 'unrelated')
        self.git('commit', '--allow-empty', '-m', 'unrelated')
        unrelated = self.git('rev-parse', 'HEAD')
        with self.assertRaises(cloud_tasks.RunError):
            self.accept(self.receipt(integrated_sha=unrelated, verified_sha=unrelated))
        self.git('checkout', 'main')
        with self.assertRaises(cloud_tasks.RunError):
            self.accept(self.receipt(integrated_sha=unrelated, verified_sha=unrelated))
        self.accept(self.receipt(integrated_sha=self.base, verified_sha=self.base))
        self.assertEqual(self.invoke('check')['ready_to_schedule'], ['b'])
        self.assertEqual(self.git('status', '--porcelain'), '')

    def test_dependency_must_be_in_source_branch_before_preparing_next_worker(self):
        self.git_run()
        self.git('branch', 'old-base', self.base)
        (self.repo / 'result.txt').write_text('integrated\n')
        self.git('add', 'result.txt')
        self.git('commit', '-m', 'integrated dependency')
        integrated = self.git('rev-parse', 'HEAD')
        self.accept(self.receipt(integrated_sha=integrated, verified_sha=integrated))
        state = self.state()
        state['tasks'][1]['branch'] = 'old-base'
        state['definition_hash'] = cloud_tasks.definition(state)
        cloud_tasks.save(self.run, state)
        with self.assertRaises(cloud_tasks.RunError):
            self.prepare('b')
        self.assertEqual(self.item('b')['status'], 'planned')
        state['tasks'][1]['branch'] = 'main'
        state['definition_hash'] = cloud_tasks.definition(state)
        cloud_tasks.save(self.run, state)
        self.prepare('b')
        self.assertEqual(self.item('b')['base_sha'], integrated)


if __name__ == '__main__':
    unittest.main()
