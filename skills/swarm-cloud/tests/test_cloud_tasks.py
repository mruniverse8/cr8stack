import argparse
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


class CloudRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.repo = self.directory / 'repository'
        self.repo.mkdir()
        self.git('init', '-b', 'main')
        self.git('config', 'user.name', 'Test Worker')
        self.git('config', 'user.email', 'worker@example.invalid')
        (self.repo / 'file.txt').write_text('base\n')
        self.git('add', 'file.txt')
        self.git('commit', '-m', 'base')
        self.base = self.git('rev-parse', 'HEAD')
        self.remote = self.directory / 'origin.git'
        subprocess.run(['git', 'init', '--bare', str(self.remote)], check=True, capture_output=True)
        self.git('remote', 'add', 'origin', str(self.remote))
        self.git('push', '-u', 'origin', 'main')
        self.plan = self.directory / 'plan.md'
        self.plan.write_text('Build a and then b.\n')
        self.spec = self.directory / 'spec.json'
        self.run = self.directory / 'run'
        self.initialize()

    def git(self, *args):
        return subprocess.run(['git', *args], cwd=self.repo, check=True, capture_output=True,
                              text=True).stdout.strip()

    def initialize(self, tasks=None):
        self.spec.write_text(json.dumps({'tasks': tasks or [self.task('a'), self.task('b', ['a'])]}))
        args = argparse.Namespace(run=self.run, repo=self.repo, plan=self.plan, spec=self.spec,
                                  env='environment', max_parallel=2, json=True)
        with contextlib.redirect_stdout(io.StringIO()):
            cloud_tasks.initialize(args)

    def task(self, identifier, dependencies=None, backend='cloud'):
        return {'id': identifier, 'title': identifier, 'backend': backend,
                'depends_on': dependencies or [], 'branch': 'main', 'brief': 'Implement ' + identifier,
                'acceptance': ['tests pass'], 'allowed_paths': ['file.txt']}

    def state(self):
        return cloud_tasks.load(self.run)

    def operate(self, action, **values):
        args = argparse.Namespace(action=action, run=self.run, json=True, owner='coordinator',
                                  offline=False, **values)
        with contextlib.redirect_stdout(io.StringIO()):
            cloud_tasks.operate(args)

    def resume(self):
        with patch.object(cloud_tasks, 'cloud', return_value='{"tasks": []}'):
            self.operate('resume')

    def completed(self, backend='cloud'):
        self.resume()
        state = self.state()
        task = state['tasks'][0]
        task.update(backend=backend, task_id='task_a', status='completed', base_sha=self.base)
        if backend == 'cloud':
            patch_path = self.run / 'results' / 'a.patch'
            patch_path.parent.mkdir(exist_ok=True)
            patch_path.write_text('diff --git a/file.txt b/file.txt\n')
            task['patch'] = {'path': 'results/a.patch',
                             'sha256': cloud_tasks.digest(patch_path.read_bytes())}
        state['definition_hash'] = cloud_tasks.definition(state)
        cloud_tasks.save(self.run, state)
        return task

    def receipt(self, task, integrated=None):
        output = self.directory / 'test-output.txt'
        output.write_text('1 test passed\n')
        receipt = {'task_id': task['task_id'], 'base_sha': task['base_sha'],
                   'verified_sha': integrated or self.base, 'integrated_sha': integrated or self.base,
                   'evidence': [str(output)], 'checks': [{'criterion': 'tests pass',
                   'command': 'python -m unittest', 'exit_code': 0, 'output': str(output)}]}
        if task.get('patch'):
            receipt['patch_sha256'] = task['patch']['sha256']
        path = self.directory / 'receipt.json'
        path.write_text(json.dumps(receipt))
        return path

    def test_initialization_persists_graph_and_blocks_second_initialization(self):
        state = self.state()
        self.assertEqual(cloud_tasks.frontier(self.run, state), ['a'])
        self.assertEqual(cloud_tasks.report(self.run, state)['planned_parallel_groups'], [['a'], ['b']])
        with self.assertRaisesRegex(cloud_tasks.RunError, 'already exists'):
            self.initialize()

    def test_cycles_and_unknown_dependencies_are_rejected_before_state_exists(self):
        for tasks, message in [([self.task('a', ['b']), self.task('b', ['a'])], 'cycle'),
                               ([self.task('a', ['absent'])], 'Unknown dependency')]:
            with self.subTest(message=message):
                self.run = self.directory / message.replace(' ', '_')
                with self.assertRaisesRegex(cloud_tasks.RunError, message):
                    self.initialize(tasks)
                self.assertFalse((self.run / 'state.json').exists())

    def test_live_check_keeps_explicit_pause_and_does_not_submit(self):
        self.operate('pause', reason='Review the patch')
        with patch.object(cloud_tasks, 'cloud', return_value='{"tasks": []}') as provider:
            self.operate('check')
        self.assertEqual(self.state()['scheduling']['state'], 'paused')
        self.assertIsNone(self.state()['coordinator'])
        self.assertEqual([call.args[0] for call in provider.call_args_list], ['list'])
        with self.assertRaisesRegex(cloud_tasks.RunError, 'explicitly paused'):
            self.operate('submit', item='a')

    def test_expired_coordinator_is_orphaned_until_explicit_resume(self):
        self.resume()
        state = self.state()
        state['coordinator']['expires_at'] = time.time() - 1
        cloud_tasks.save(self.run, state)
        self.assertEqual(cloud_tasks.report(self.run, self.state())['scheduling'], 'orphaned')
        self.resume()
        self.assertEqual(cloud_tasks.report(self.run, self.state())['scheduling'], 'active')

    def test_other_owner_cannot_acquire_unexpired_lease(self):
        self.resume()
        state = self.state()
        state['coordinator']['owner'] = 'another-owner'
        cloud_tasks.save(self.run, state)
        with patch.object(cloud_tasks, 'cloud') as provider:
            with self.assertRaisesRegex(cloud_tasks.RunError, 'unexpired lease'):
                self.operate('resume')
            provider.assert_not_called()

    def test_pagination_finds_task_on_second_page(self):
        with patch.object(cloud_tasks, 'cloud', side_effect=[
                json.dumps({'tasks': [{'id': 'task_a', 'status': 'pending'}], 'cursor': 'next'}),
                json.dumps({'tasks': [{'id': 'task_b', 'status': 'ready'}]})]) as provider:
            rows = cloud_tasks.listed_tasks()
        self.assertEqual(set(rows), {'task_a', 'task_b'})
        self.assertEqual(provider.call_args_list[1].args, ('list', '--json', '--limit', '20', '--cursor', 'next'))

    def test_repeated_pagination_cursor_is_rejected(self):
        with patch.object(cloud_tasks, 'cloud', return_value='{"tasks": [], "cursor": "again"}'):
            with self.assertRaisesRegex(cloud_tasks.RunError, 'repeated a cursor'):
                cloud_tasks.listed_tasks()

    def test_unknown_provider_state_occupies_slot_and_cannot_unlock_dependencies(self):
        state = self.state()
        state['tasks'][0].update(task_id='task_a', status='pending')
        cloud_tasks.save(self.run, state)
        with patch.object(cloud_tasks, 'cloud', return_value='{"tasks": [{"id": "task_a", "status": "new_state"}]}'):
            self.operate('check')
        report = cloud_tasks.report(self.run, self.state())
        self.assertEqual(report['active_or_uncertain'], ['a'])
        self.assertEqual(report['ready_to_schedule'], [])
        self.assertEqual(report['tasks'][0]['worker_state'], 'unknown')

    def test_retrieved_patch_requires_acceptance_to_unlock_dependency(self):
        task = self.completed()
        with patch.object(cloud_tasks, 'cloud', side_effect=[
                '{"tasks": [{"id": "task_a", "status": "ready"}]}', 'retrieved patch\n']):
            self.operate('check')
        state = self.state()
        self.assertEqual(cloud_tasks.frontier(self.run, state), [])
        self.assertEqual((self.run / state['tasks'][0]['patch']['path']).read_text(), 'retrieved patch\n')
        task = state['tasks'][0]
        self.operate('accept', item='a', receipt=self.receipt(task))
        self.assertEqual(cloud_tasks.frontier(self.run, self.state()), ['b'])

    def test_receipt_evidence_or_patch_changes_revoke_dependency_readiness(self):
        task = self.completed()
        receipt = self.receipt(task)
        self.operate('accept', item='a', receipt=receipt)
        state = self.state()
        self.assertEqual(cloud_tasks.frontier(self.run, state), ['b'])
        evidence = self.directory / 'test-output.txt'
        evidence.write_text('changed evidence\n')
        self.assertEqual(cloud_tasks.frontier(self.run, state), [])
        evidence.write_text('1 test passed\n')
        self.assertEqual(cloud_tasks.frontier(self.run, state), ['b'])
        (self.run / task['patch']['path']).write_text('changed patch\n')
        self.assertEqual(cloud_tasks.frontier(self.run, state), [])

    def test_plan_changes_are_observable_but_definition_mutation_blocks_loading(self):
        self.plan.write_text('New plan\n')
        state = self.state()
        self.assertTrue(state['plan_changed'])
        self.assertEqual(cloud_tasks.frontier(self.run, state), [])
        self.plan.write_text('Build a and then b.\n')
        state = self.state()
        state['tasks'][0]['brief'] = 'Different work'
        cloud_tasks.save(self.run, state)
        with self.assertRaisesRegex(cloud_tasks.RunError, 'Plan definition changed'):
            self.state()

    def test_changed_or_deleted_plan_preserves_observation_and_pause_only(self):
        for mutation in ('changed', 'deleted'):
            with self.subTest(mutation=mutation):
                if mutation == 'deleted':
                    self.run = self.directory / 'missing-plan-run'
                    self.plan.write_text('Build a and then b.\n')
                    self.initialize()
                self.resume()
                state = self.state()
                state['tasks'][0].update(task_id='task_a', status='pending', base_sha=self.base)
                cloud_tasks.save(self.run, state)
                original_plan = (self.run / 'plan.md').read_bytes()
                self.assertEqual(cloud_tasks.digest(original_plan), state['plan']['sha256'])
                if mutation == 'changed':
                    self.plan.write_text('New external plan\n')
                else:
                    self.plan.unlink()
                with patch.object(cloud_tasks, 'cloud', return_value='{"tasks": [{"id": "task_a", "status": "pending"}]}'):
                    self.operate('check')
                state = self.state()
                self.assertTrue(state['plan_changed'])
                self.assertEqual(state['tasks'][0]['provider_status'], 'pending')
                self.assertTrue(state['tasks'][0]['last_checked'])
                self.assertEqual(cloud_tasks.frontier(self.run, state), [])
                with patch.object(cloud_tasks, 'cloud') as provider:
                    args = argparse.Namespace(action='check', run=self.run, json=True, offline=True)
                    with contextlib.redirect_stdout(io.StringIO()):
                        cloud_tasks.operate(args)
                    self.operate('pause', reason='Plan must be revised')
                    for action, arguments in [('resume', {}), ('submit', {'item': 'b'}),
                                              ('accept', {'item': 'a', 'receipt': self.directory / 'unused.json'})]:
                        with self.subTest(action=action):
                            with self.assertRaisesRegex(cloud_tasks.RunError, 'Plan file changed or is unavailable'):
                                self.operate(action, **arguments)
                    provider.assert_not_called()
                self.assertEqual(self.state()['scheduling']['state'], 'paused')
                self.assertEqual((self.run / 'plan.md').read_bytes(), original_plan)
                report = json.loads((self.run / 'results' / 'latest-status.json').read_text())
                self.assertTrue(report['plan_changed'])
                self.assertEqual(report['ready_to_schedule'], [])

    def test_changed_plan_marks_old_accepted_receipt_unusable_in_report(self):
        task = self.completed()
        self.operate('accept', item='a', receipt=self.receipt(task))
        self.plan.write_text('Revised external plan\n')
        report = cloud_tasks.report(self.run, self.state())
        self.assertTrue(report['plan_changed'])
        self.assertNotEqual(report['tasks'][0]['result'], 'accepted')
        self.assertEqual(report['ready_to_schedule'], [])

    def test_failed_or_ambiguous_submit_is_durable_and_never_retried(self):
        for index, outcome in enumerate([cloud_tasks.RunError('connection lost'),
                'https://chatgpt.com/codex/task_one https://chatgpt.com/codex/task_two']):
            with self.subTest(outcome=str(outcome)):
                if index:
                    self.run = self.directory / 'second-run'
                    self.initialize()
                self.resume()
                with patch.object(cloud_tasks, 'cloud', side_effect=['{"tasks": []}', outcome]) as provider:
                    with self.assertRaises(cloud_tasks.RunError):
                        self.operate('submit', item='a')
                task = self.state()['tasks'][0]
                self.assertEqual(task['status'], 'submission_unknown')
                self.assertTrue(task['submission_token'])
                self.assertTrue((self.run / 'briefs' / 'a.txt').exists())
                with patch.object(cloud_tasks, 'cloud', return_value='{"tasks": []}') as retry:
                    with self.assertRaisesRegex(cloud_tasks.RunError, 'already submitted, uncertain'):
                        self.operate('submit', item='a')
                self.assertEqual([call.args[0] for call in retry.call_args_list], ['list'])

    def test_successful_submit_uses_pushed_sha_and_rejects_duplicate(self):
        self.resume()
        (self.repo / 'local.txt').write_text('not pushed\n')
        self.git('add', 'local.txt')
        self.git('commit', '-m', 'local work not available to cloud')
        with patch.object(cloud_tasks, 'cloud', side_effect=['{"tasks": []}',
                'https://chatgpt.com/codex/task_a']) as provider:
            self.operate('submit', item='a')
        self.assertEqual(self.state()['tasks'][0]['base_sha'], self.base)
        self.assertIn('Verify git HEAD equals ' + self.base, provider.call_args_list[1].args[-1])
        with patch.object(cloud_tasks, 'cloud', return_value='{"tasks": [{"id": "task_a", "status": "pending"}]}'):
            with self.assertRaisesRegex(cloud_tasks.RunError, 'already submitted'):
                self.operate('submit', item='a')

    def test_submissions_require_dependency_integration_on_remote_branch(self):
        task = self.completed()
        (self.repo / 'integrated.txt').write_text('integrated result\n')
        self.git('add', 'integrated.txt')
        self.git('commit', '-m', 'integrate dependency')
        integrated = self.git('rev-parse', 'HEAD')
        self.operate('accept', item='a', receipt=self.receipt(task, integrated))
        with patch.object(cloud_tasks, 'cloud', side_effect=[
                '{"tasks": [{"id": "task_a", "status": "ready"}]}',
                (self.run / task['patch']['path']).read_text()]) as provider:
            with self.assertRaises(cloud_tasks.RunError):
                self.operate('submit', item='b')
        self.assertNotIn('exec', [call.args[0] for call in provider.call_args_list])
        self.assertEqual(self.state()['tasks'][1]['status'], 'planned')

    def test_unreachable_or_unverified_integrated_commit_is_rejected(self):
        task = self.completed()
        path = self.receipt(task)
        receipt = json.loads(path.read_text())
        receipt['verified_sha'] = '0' * 40
        path.write_text(json.dumps(receipt))
        with self.assertRaisesRegex(cloud_tasks.RunError, 'Verification must cover'):
            self.operate('accept', item='a', receipt=path)
        self.git('checkout', '--orphan', 'unrelated')
        self.git('commit', '--allow-empty', '-m', 'unrelated')
        unrelated = self.git('rev-parse', 'HEAD')
        self.git('checkout', 'main')
        path = self.receipt(task, unrelated)
        with self.assertRaises(cloud_tasks.RunError):
            self.operate('accept', item='a', receipt=path)

    def test_accept_rejects_integrated_commit_unrelated_to_task_base(self):
        task = self.completed()
        self.git('checkout', '--orphan', 'unrelated')
        self.git('commit', '--allow-empty', '-m', 'unrelated')
        unrelated = self.git('rev-parse', 'HEAD')
        with self.assertRaises(cloud_tasks.RunError):
            self.operate('accept', item='a', receipt=self.receipt(task, unrelated))
        self.assertFalse(cloud_tasks.accepted(self.run, self.state()['tasks'][0]))

    def test_completed_native_worker_cannot_reuse_receipt_for_changed_base(self):
        task = self.completed(backend='sub')
        self.operate('accept', item='a', receipt=self.receipt(task))
        (self.repo / 'next.txt').write_text('later base\n')
        self.git('add', 'next.txt')
        self.git('commit', '-m', 'later base')
        new_base = self.git('rev-parse', 'HEAD')
        try:
            self.operate('record-sub', item='a', task_id='task_a', status='completed', base_sha=new_base)
        except cloud_tasks.RunError:
            return
        self.assertFalse(cloud_tasks.accepted(self.run, self.state()['tasks'][0]))

    def test_init_does_not_import_worker_registration_or_receipt(self):
        self.run = self.directory / 'untrusted-spec-run'
        task = self.task('a')
        task.update(task_id='task_injected', base_sha=self.base,
                    receipt={'files': {}, 'integrated_sha': self.base})
        self.initialize([task])
        initialized = self.state()['tasks'][0]
        self.assertIsNone(initialized.get('task_id'))
        self.assertIsNone(initialized.get('receipt'))
        self.assertEqual(cloud_tasks.frontier(self.run, self.state()), ['a'])

    def test_another_process_lock_blocks_command_without_provider_calls(self):
        with (self.run / '.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = subprocess.run([sys.executable, str(HELPER), 'check', '--run', str(self.run)],
                                    capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('Another command owns this run', result.stderr)

    def test_check_and_accept_do_not_apply_or_merge_git_changes(self):
        task = self.completed()
        before = self.git('rev-parse', 'HEAD')
        original_git = cloud_tasks.git
        with patch.object(cloud_tasks, 'git', wraps=original_git) as git_calls:
            self.operate('accept', item='a', receipt=self.receipt(task))
            with patch.object(cloud_tasks, 'cloud', side_effect=[
                    '{"tasks": [{"id": "task_a", "status": "ready"}]}', 'updated patch\n']):
                self.operate('check')
        self.assertEqual(self.git('rev-parse', 'HEAD'), before)
        self.assertEqual(self.git('status', '--porcelain'), '')
        self.assertFalse(any(call.args[1] in ('apply', 'merge', 'cherry-pick', 'reset')
                             for call in git_calls.call_args_list))

    def test_latest_failed_patch_retrieval_revokes_old_acceptance(self):
        task = self.completed()
        self.operate('accept', item='a', receipt=self.receipt(task))
        with patch.object(cloud_tasks, 'cloud', side_effect=[
                '{"tasks": [{"id": "task_a", "status": "ready"}]}',
                cloud_tasks.RunError('diff unavailable')]):
            self.operate('check')
        self.assertEqual(cloud_tasks.frontier(self.run, self.state()), [])

    def test_native_dependent_worker_cannot_start_before_integrated_dependency(self):
        task = self.completed()
        (self.repo / 'integrated.txt').write_text('integrated result\n')
        self.git('add', 'integrated.txt')
        self.git('commit', '-m', 'integrate dependency')
        integrated = self.git('rev-parse', 'HEAD')
        self.operate('accept', item='a', receipt=self.receipt(task, integrated))
        state = self.state()
        state['tasks'][1]['backend'] = 'sub'
        state['definition_hash'] = cloud_tasks.definition(state)
        cloud_tasks.save(self.run, state)
        with self.assertRaises(cloud_tasks.RunError):
            self.operate('record-sub', item='b', task_id='native_b', status='running', base_sha=self.base)

    def test_manual_bind_requires_token_environment_and_unique_provider_id(self):
        self.resume()
        state = self.state()
        state['tasks'][0].update(status='submission_unknown', submission_token='saved-token', base_sha=self.base)
        cloud_tasks.save(self.run, state)
        for token, environment in [('wrong-token', 'environment'), ('saved-token', 'different')]:
            with self.subTest(token=token, environment=environment):
                rows = json.dumps({'tasks': [{'id': 'task_recovered', 'environment_id': environment}]})
                with patch.object(cloud_tasks, 'cloud', return_value=rows):
                    with self.assertRaises(cloud_tasks.RunError):
                        self.operate('bind', item='a', task_id='task_recovered', submission_token=token)
                self.assertIsNone(self.state()['tasks'][0].get('task_id'))
        rows = '{"tasks": [{"id": "task_recovered", "environment_id": "environment"}]}'
        with patch.object(cloud_tasks, 'cloud', return_value=rows):
            self.operate('bind', item='a', task_id='task_recovered', submission_token='saved-token')
        self.assertEqual(self.state()['tasks'][0]['task_id'], 'task_recovered')
        self.assertEqual(self.state()['tasks'][0]['status'], 'unknown')

    def test_provider_cannot_register_same_worker_for_two_items(self):
        state = self.state()
        state['tasks'][1]['depends_on'] = []
        state['definition_hash'] = cloud_tasks.definition(state)
        cloud_tasks.save(self.run, state)
        self.resume()
        with patch.object(cloud_tasks, 'cloud', side_effect=[
                '{"tasks": []}', 'https://chatgpt.com/codex/task_a']):
            self.operate('submit', item='a')
        with patch.object(cloud_tasks, 'cloud', side_effect=[
                '{"tasks": [{"id": "task_a", "status": "pending"}]}',
                'https://chatgpt.com/codex/task_a']):
            with self.assertRaises(cloud_tasks.RunError):
                self.operate('submit', item='b')
        state = self.state()
        self.assertEqual(state['tasks'][1]['status'], 'submission_unknown')
        self.assertIsNone(state['tasks'][1].get('task_id'))

    def test_unknown_worker_occupies_parallel_capacity(self):
        self.resume()
        state = self.state()
        state['max_parallel'] = 1
        state['tasks'][0].update(task_id='task_a', status='pending')
        state['tasks'][1]['depends_on'] = []
        state['definition_hash'] = cloud_tasks.definition(state)
        cloud_tasks.save(self.run, state)
        with patch.object(cloud_tasks, 'cloud', return_value='{"tasks": []}') as provider:
            with self.assertRaisesRegex(cloud_tasks.RunError, 'Parallel limit reached'):
                self.operate('submit', item='b')
        self.assertEqual([call.args[0] for call in provider.call_args_list], ['list'])
        self.assertEqual(self.state()['tasks'][0]['status'], 'unknown')

    def test_provider_failure_holds_submission_without_resetting_uncertainty(self):
        self.resume()
        with patch.object(cloud_tasks, 'cloud', side_effect=cloud_tasks.RunError('provider unavailable')) as provider:
            with self.assertRaisesRegex(cloud_tasks.RunError, 'status unavailable'):
                self.operate('submit', item='a')
        self.assertEqual([call.args[0] for call in provider.call_args_list], ['list'])
        self.assertEqual(self.state()['tasks'][0]['status'], 'planned')

    def test_cloud_patch_change_from_provider_revokes_existing_receipt(self):
        task = self.completed()
        self.operate('accept', item='a', receipt=self.receipt(task))
        with patch.object(cloud_tasks, 'cloud', side_effect=[
                '{"tasks": [{"id": "task_a", "status": "applied"}]}', 'different patch\n']):
            self.operate('check')
        self.assertEqual(self.state()['tasks'][0]['status'], 'completed')
        self.assertEqual(cloud_tasks.frontier(self.run, self.state()), [])

    def test_accept_requires_passing_complete_nonempty_local_evidence(self):
        task = self.completed()
        for mutation in ('failed', 'missing criterion', 'missing output', 'different task', 'different base'):
            with self.subTest(mutation=mutation):
                path = self.receipt(task)
                receipt = json.loads(path.read_text())
                if mutation == 'failed':
                    receipt['checks'][0]['exit_code'] = 1
                elif mutation == 'missing criterion':
                    receipt['checks'][0]['criterion'] = 'unrelated check'
                elif mutation == 'missing output':
                    receipt['checks'][0]['output'] = str(self.directory / 'absent-output.txt')
                elif mutation == 'different task':
                    receipt['task_id'] = 'task_wrong'
                else:
                    receipt['base_sha'] = '0' * 40
                path.write_text(json.dumps(receipt))
                with self.assertRaises(cloud_tasks.RunError):
                    self.operate('accept', item='a', receipt=path)
                self.assertEqual(cloud_tasks.frontier(self.run, self.state()), [])

    def test_live_unknown_state_revokes_previously_accepted_receipt(self):
        task = self.completed()
        self.operate('accept', item='a', receipt=self.receipt(task))
        with patch.object(cloud_tasks, 'cloud', return_value='{"tasks": []}'):
            self.operate('check')
        self.assertEqual(self.state()['tasks'][0]['status'], 'unknown')
        self.assertEqual(cloud_tasks.frontier(self.run, self.state()), [])

    def test_offline_check_does_not_refresh_provider_or_resume_scheduling(self):
        self.operate('pause', reason='Manual verification')
        args = argparse.Namespace(action='check', run=self.run, json=True, offline=True)
        with patch.object(cloud_tasks, 'cloud') as provider:
            with contextlib.redirect_stdout(io.StringIO()) as output:
                cloud_tasks.operate(args)
        provider.assert_not_called()
        report = json.loads(output.getvalue())
        self.assertTrue(report['offline'])
        self.assertEqual(report['scheduling'], 'paused')

    def test_watch_is_bounded_and_keeps_pause_while_refreshing(self):
        self.operate('pause', reason='Watch results')
        arguments = ['cloud_tasks.py', 'watch', '--run', str(self.run), '--iterations', '2', '--interval', '1', '--json']
        with patch.object(sys, 'argv', arguments), patch.object(cloud_tasks.time, 'sleep') as sleep:
            with patch.object(cloud_tasks, 'cloud', return_value='{"tasks": []}') as provider:
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(cloud_tasks.main(), 0)
        self.assertEqual(provider.call_count, 2)
        sleep.assert_called_once_with(1)
        self.assertEqual(self.state()['scheduling']['state'], 'paused')

    def test_new_result_file_is_retrieved_locally_and_reported(self):
        self.completed()
        patch_text = ('diff --git a/.pstack-results/a.md b/.pstack-results/a.md\n'
                      'new file mode 100644\nindex 0000000..1234567\n--- /dev/null\n'
                      '+++ b/.pstack-results/a.md\n@@ -0,0 +1,3 @@\n'
                      '+PASS\n+Starting HEAD: ' + self.base + '\n+python -m unittest: 1 test passed\n')
        with patch.object(cloud_tasks, 'cloud', side_effect=[
                '{"tasks": [{"id": "task_a", "status": "ready"}]}', patch_text]):
            self.operate('check')
        task = self.state()['tasks'][0]
        result = self.run / task['result_path']
        self.assertEqual(result.read_text(), 'PASS\nStarting HEAD: ' + self.base + '\npython -m unittest: 1 test passed\n')
        report = json.loads((self.run / 'results' / 'latest-status.json').read_text())
        self.assertIn('PASS', json.dumps(report))
        self.assertEqual(cloud_tasks.frontier(self.run, self.state()), [])

    def test_new_patch_versions_preserve_earlier_patch_report_and_receipt_evidence(self):
        self.completed()
        patches = []
        artifacts = []
        for version in ('first', 'second'):
            patch_text = ('diff --git a/.pstack-results/a.md b/.pstack-results/a.md\n'
                          'new file mode 100644\n--- /dev/null\n+++ b/.pstack-results/a.md\n'
                          '@@ -0,0 +1,1 @@\n+PASS ' + version + '\n')
            patches.append(patch_text)
            with patch.object(cloud_tasks, 'cloud', side_effect=[
                    '{"tasks": [{"id": "task_a", "status": "ready"}]}', patch_text]):
                self.operate('check')
            task = self.state()['tasks'][0]
            checksum = cloud_tasks.digest(patch_text.encode())
            artifact = task['patch'].copy()
            artifacts.append(artifact)
            self.assertEqual(artifact['sha256'], checksum)
            self.assertEqual(Path(artifact['path']).name, checksum + '.patch')
            self.assertEqual(Path(artifact['path']).parent, Path('results/a'))
            self.assertEqual(Path(task['result_path']).name, checksum + '.md')
            self.assertEqual((self.run / artifact['path']).read_text(), patch_text)
            self.assertEqual((self.run / task['result_path']).read_text(), 'PASS ' + version + '\n')
            if version == 'first':
                first_report = self.run / task['result_path']
                self.operate('accept', item='a', receipt=self.receipt(task))
                self.assertEqual(cloud_tasks.frontier(self.run, self.state()), ['b'])
        task = self.state()['tasks'][0]
        self.assertNotEqual(artifacts[0]['path'], artifacts[1]['path'])
        self.assertEqual((self.run / artifacts[0]['path']).read_text(), patches[0])
        self.assertEqual(first_report.read_text(), 'PASS first\n')
        self.assertEqual(task['patch_history'], artifacts)
        self.assertEqual(cloud_tasks.frontier(self.run, self.state()), [])
        with patch.object(cloud_tasks, 'cloud', side_effect=[
                '{"tasks": [{"id": "task_a", "status": "ready"}]}', patches[1]]):
            self.operate('check')
        self.assertEqual(self.state()['tasks'][0]['patch_history'], artifacts)


if __name__ == '__main__':
    unittest.main()
