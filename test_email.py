"""Check email behavior without connecting to Gmail or modifying live state."""

from contextlib import redirect_stdout, redirect_stderr
from copy import deepcopy
import io
import json
from pathlib import Path
import smtplib
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import main
import send_email


class EmailTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.addCleanup(self.directory.cleanup)
        self.state = Path(self.directory.name) / 'state.json'
        self.config = {'sender': 'sender@example.com', 'recipients': ['a@example.com', 'b@example.com']}
        self.game = {'game_date': '2026-10-19', 'game_id': 123, 'status': 'predicted',
                     'home_team': 'Home', 'away_team': 'Away', 'home_win_probability': .56,
                     'away_win_probability': .44, 'predicted_winner': 'Home', 'imputed_features': []}
        self.result = {'requested_date': '2026-10-19', 'games': [self.game]}

    def test_delivery_is_per_recipient_and_not_repeated(self):
        with patch('send_email.load_password', return_value='fake'), patch('send_email.smtplib.SMTP_SSL') as factory, redirect_stdout(io.StringIO()):
            smtp = factory.return_value.__enter__.return_value
            smtp.send_message.return_value = {}
            self.assertEqual(send_email.send_new_predictions(self.result, self.config, self.state), 2)
            self.game['home_win_probability'] = .60
            self.assertEqual(send_email.send_new_predictions(self.result, self.config, self.state), 0)
            self.config['recipients'].append('c@example.com')
            self.assertEqual(send_email.send_new_predictions(self.result, self.config, self.state), 1)
            messages = [c.args[0] for c in smtp.send_message.call_args_list]
            self.assertEqual([str(m['To']) for m in messages], self.config['recipients'])
            self.assertIn('56.0%', messages[0].get_content())

    def test_partial_failure_does_not_repeat_successful_recipient(self):
        with patch('send_email.load_password', return_value='fake'), patch('send_email.smtplib.SMTP_SSL') as factory, redirect_stdout(io.StringIO()):
            smtp = factory.return_value.__enter__.return_value
            smtp.send_message.side_effect = [{}, smtplib.SMTPException('failed')]
            with self.assertRaises(smtplib.SMTPException):
                send_email.send_new_predictions(self.result, self.config, self.state)
            smtp.send_message.reset_mock(side_effect=True)
            smtp.send_message.return_value = {}
            self.assertEqual(send_email.send_new_predictions(self.result, self.config, self.state), 1)
            self.assertEqual(str(smtp.send_message.call_args.args[0]['To']), 'b@example.com')

    def test_skips_and_no_games_never_connect(self):
        with patch('send_email.load_password') as password, patch('send_email.smtplib.SMTP_SSL') as smtp, redirect_stdout(io.StringIO()):
            self.game['status'] = 'skipped'
            self.assertEqual(send_email.send_new_predictions(self.result, self.config, self.state), 0)
            self.result['games'] = []
            self.assertEqual(send_email.send_new_predictions(self.result, self.config, self.state), 0)
            password.assert_not_called()
            smtp.assert_not_called()

    def test_invalid_state_is_not_reset(self):
        self.state.write_text('{invalid', encoding='utf-8')
        with self.assertRaises(ValueError):
            send_email.load_state(self.state)

    def test_doubleheader_is_a_new_game(self):
        state = {'deliveries': {'a@example.com': {send_email.game_key(self.game): 'sent'}}}
        other = deepcopy(self.game)
        other['game_id'] = 124
        self.assertEqual(send_email.unsent_games([self.game, other], ['a@example.com'], state), [other])


class PipelineTests(unittest.TestCase):
    def invoke(self, fail=None, extra=None, snapshot=None):
        commands = []
        def run(command, **kwargs):
            self.assertTrue(kwargs['check'])
            commands.append(command)
            if Path(command[1]).name == fail:
                raise subprocess.CalledProcessError(2, command)
        stream = io.StringIO()
        argv = ['main.py', '--project', 'example-project', '--date', '2026-10-19'] + (extra or [])
        with patch.object(sys, 'argv', argv), patch('main.subprocess.run', side_effect=run), \
                patch.object(Path, 'is_file', return_value=True), \
                patch.object(Path, 'read_text', return_value=json.dumps(snapshot or {'requested_date': '2026-10-19', 'games': []})), \
                redirect_stdout(stream), redirect_stderr(stream):
            if fail:
                with self.assertRaises(SystemExit) as exc:
                    main.main()
                self.assertEqual(exc.exception.code, 1)
            else:
                main.main()
        return commands, stream.getvalue()

    def test_order_and_same_interpreter_date(self):
        commands, text = self.invoke()
        self.assertEqual([Path(c[1]).name for c in commands], ['get_matchups.py', 'update_features.py', 'predict.py'])
        for command in commands:
            self.assertEqual(command[0], sys.executable)
            self.assertEqual(command[command.index('--date') + 1], '2026-10-19')
        self.assertIn('No upcoming games', text)

    def test_failure_stops_later_steps(self):
        for script, count in [('get_matchups.py', 1), ('update_features.py', 2), ('predict.py', 3)]:
            commands, text = self.invoke(fail=script)
            self.assertEqual(len(commands), count)
            self.assertIn('Pipeline stopped', text)

    def test_offseason_never_launches_scripts(self):
        commands, text = self.invoke(extra=['--scheduled', '--date', '2026-12-01'])
        self.assertEqual(commands, [])
        self.assertIn('Offseason', text)

    def test_empty_hourly_check_skips_refresh_and_email(self):
        with patch('send_email.load_config', return_value={'recipients': ['a@example.com']}), \
                patch('send_email.load_state', return_value={'deliveries': {}}), \
                patch('send_email.load_password') as password, \
                patch('send_email.send_new_predictions') as send:
            commands, text = self.invoke(extra=['--email'])
            self.assertEqual(len(commands), 1)
            self.assertIn('No new games', text)
            password.assert_not_called()
            send.assert_not_called()


if __name__ == '__main__':
    unittest.main()
