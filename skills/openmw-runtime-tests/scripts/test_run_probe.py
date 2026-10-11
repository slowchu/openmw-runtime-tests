"""Runner regressions; no OpenMW/game installation is needed."""
import argparse
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import run_probe as runner


class Outcomes(unittest.TestCase):
    def result(self, events=('BEGIN', 'PASS', 'COMPLETE'), extra='', code=0, timed_out=False):
        text = '\n'.join(f'[engine] OMW_TEST|test-id|{event}|' for event in events)
        return runner.assess(text, text + '\n' + extra, 'test-id',
                             {'exit_code': code, 'timed_out': timed_out, 'launch_error': None})

    def test_completed_success(self):
        self.assertTrue(self.result()['passed'])

    def test_clean_exit_without_completion_fails(self):
        self.assertFalse(self.result(('BEGIN',))['passed'])

    def test_lua_failure_with_zero_exit_fails(self):
        self.assertFalse(self.result(('BEGIN', 'FAIL'))['passed'])

    def test_late_engine_lua_error_fails(self):
        self.assertFalse(self.result(extra='[engine] Lua error: delayed widget update')['passed'])

    def test_crash_and_timeout_fail_even_with_markers(self):
        self.assertFalse(self.result(code=1)['passed'])
        self.assertFalse(self.result(timed_out=True)['passed'])

    def test_duplicate_and_out_of_order_markers_fail(self):
        self.assertFalse(self.result(('BEGIN', 'PASS', 'COMPLETE', 'COMPLETE'))['passed'])
        self.assertFalse(self.result(('PASS', 'BEGIN', 'COMPLETE'))['passed'])

    def test_stale_other_run_cannot_pass(self):
        text = 'OMW_TEST|other-run|BEGIN|\nOMW_TEST|other-run|PASS|\nOMW_TEST|other-run|COMPLETE|'
        self.assertFalse(runner.assess(text, text, 'test-id',
                                      {'exit_code': 0, 'timed_out': False, 'launch_error': None})['passed'])


class FilesAndProcess(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        data, resources = self.base / 'game', self.base / 'resources'
        data.mkdir()
        (resources / 'vfs-mw').mkdir(parents=True)
        (data / 'game.esm').write_text('fixture')
        probe = self.base / 'case.lua'
        probe.write_text('return {step=function() return true end}')
        self.args = argparse.Namespace(openmw=Path(sys.executable), resources=resources, probe=probe,
                                       data=[data], content=['game.esm'], archive=[], timeout=2,
                                       output=self.base / 'run', start='Test Cell')

    def test_profile_isolated_and_existing_output_refused(self):
        runner.validate_inputs(self.args)
        command = runner.prepare(self.args, 'test-id')
        config = (self.args.output / 'config' / 'openmw.cfg').read_text()
        self.assertIn('replace=content', config)
        self.assertIn('user-data=' + runner.cfg_path(self.args.output / 'user-data'), config)
        self.assertIn('--replace', command)
        self.assertIn('config', command)
        self.assertLess(config.index('data=' + runner.cfg_path(self.args.data[0])),
                        config.index('data-local=' + runner.cfg_path(self.args.output / 'data')))
        self.assertEqual((self.args.output / 'data' / runner.PROBE_CONTENT).read_text(),
                         'PLAYER: scripts/omw_runtime_test/driver.lua\n')
        with self.assertRaises(ValueError):
            runner.validate_inputs(self.args)

    def test_output_inside_game_data_refused(self):
        self.args.output = self.args.data[0] / 'generated'
        with self.assertRaises(ValueError):
            runner.validate_inputs(self.args)

    def test_invalid_content_and_timeout_refused(self):
        for value in ['../game.esm', 'missing.esm', 'game.esm\nconfig=other']:
            self.args.content = [value]
            with self.assertRaises(ValueError):
                runner.validate_inputs(self.args)
        self.args.content = ['game.esm']
        for value in [0, -1, float('nan'), float('inf')]:
            self.args.timeout = value
            with self.assertRaises(ValueError):
                runner.validate_inputs(self.args)

    def test_quoted_path_escaping(self):
        self.assertEqual(runner.cfg_path(Path('a&b')), '"a&&b"')
        with self.assertRaises(ValueError):
            runner.cfg_path(Path('a\nb'))

    def test_launch_failure_recorded(self):
        output = self.base / 'failed'
        output.mkdir()
        result = runner.execute([str(self.base / 'does-not-exist.exe')], output, 1)
        self.assertIsNotNone(result['launch_error'])
        self.assertIsNone(result['exit_code'])

    def test_timeout_stops_its_child_without_stopping_other_processes(self):
        output = self.base / 'timeout'
        output.mkdir()
        other = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])
        try:
            result = runner.execute([sys.executable, '-c', 'import time; time.sleep(30)'], output, .15)
            self.assertTrue(result['timed_out'])
            self.assertIsNotNone(result['exit_code'])
            self.assertIsNone(other.poll())
        finally:
            other.terminate()
            other.wait(timeout=5)


if __name__ == '__main__':
    unittest.main()
