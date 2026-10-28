"""Email new game predictions, keeping a delivery record for each recipient."""

from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import parseaddr
import json
import os
from pathlib import Path
import smtplib
import ssl
import subprocess

ROOT = Path(__file__).resolve().parent
DEFAULT_STATE = ROOT / 'email_state.json'
CREDENTIAL = ROOT / '.gmail-credential.xml'


def load_config(path):
    config = json.loads(path.read_text(encoding='utf-8-sig'))
    addresses = [config['sender'], *config['recipients']]
    if not config['recipients']:
        raise ValueError('Email recipient list is empty')
    for address in addresses:
        if not isinstance(address, str) or '\n' in address or '\r' in address:
            raise ValueError('Invalid email address in configuration')
        if parseaddr(address)[1] != address or '@' not in address:
            raise ValueError(f'Invalid email address: {address}')
    config['recipients'] = list(dict.fromkeys(config['recipients']))
    return config


def load_state(path):
    if not path.exists():
        return {'deliveries': {}}
    state = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(state.get('deliveries'), dict):
        raise ValueError('Invalid email delivery record; restore it before sending')
    return state


def game_key(game):
    return f'{game["game_date"]}:{game["game_id"]}'


def unsent_games(games, recipients, state):
    """A game is new if at least one configured recipient has not received it."""
    return [game for game in games if any(
        game_key(game) not in state['deliveries'].get(recipient, {})
        for recipient in recipients)]


def load_password():
    password = os.environ.get('MLB_GMAIL_APP_PASSWORD')
    if password:
        return password.replace(' ', '')
    if not CREDENTIAL.is_file():
        raise ValueError('Gmail is not authorized. Run setup_automation.ps1 locally first.')
    # Windows encrypts this credential for the current user on this computer.
    # Capture the decrypted password in memory; never place it in command arguments.
    process = subprocess.run(
        ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command',
         '$ErrorActionPreference="Stop"; '
         '$c=Import-Clixml -LiteralPath $env:MLB_CREDENTIAL_PATH; '
         '[Console]::Out.Write($c.GetNetworkCredential().Password)'],
        env={**os.environ, 'MLB_CREDENTIAL_PATH': str(CREDENTIAL)},
        capture_output=True, text=True)
    if process.returncode or not process.stdout.strip():
        raise ValueError('Cannot unlock Gmail credential; rerun setup_automation.ps1 as this Windows user')
    return process.stdout.strip().replace(' ', '')


def make_message(sender, recipient, prediction_date, games):
    message = EmailMessage()
    message['From'] = f'MLB Model Predictions <{sender}>'
    message['To'] = recipient
    message['Subject'] = f'MLB predictions — {prediction_date} ({len(games)} new)'
    lines = [f'MLB predictions — {prediction_date}', '']
    for game in games:
        lines.extend([
            f'{game["away_team"]} at {game["home_team"]}',
            f'  {game["away_team"]}: {game["away_win_probability"]:.1%}',
            f'  {game["home_team"]}: {game["home_win_probability"]:.1%}',
            f'  Pick: {game["predicted_winner"]}',
        ])
        if game['imputed_features']:
            lines.append('  Features filled with training medians: '
                         + ', '.join(game['imputed_features']))
        lines.append('')
    lines.append('Probabilities are estimates from the saved logistic regression model.')
    message.set_content('\n'.join(lines))
    return message


def send_new_predictions(result, config, state_path=DEFAULT_STATE):
    state = load_state(state_path)
    predicted = [g for g in result['games'] if g['status'] == 'predicted']
    pending = unsent_games(predicted, config['recipients'], state)
    if not pending:
        print('No new predictions to email.')
        return 0
    password = load_password()
    sent = 0
    with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=ssl.create_default_context(), timeout=30) as smtp:
        smtp.login(config['sender'], password)
        for recipient in config['recipients']:
            games = unsent_games(pending, [recipient], state)
            if not games:
                continue
            message = make_message(config['sender'], recipient, result['requested_date'], games)
            refused = smtp.send_message(message)
            if refused:
                raise ValueError(f'Email was refused for {recipient}')
            # Persist after each accepted email so a later recipient failure does
            # not resend earlier recipients' messages on the next hourly run.
            delivered = state['deliveries'].setdefault(recipient, {})
            timestamp = datetime.now(timezone.utc).isoformat()
            delivered.update({game_key(game): timestamp for game in games})
            state_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = state_path.with_suffix(state_path.suffix + '.tmp')
            temporary.write_text(json.dumps(state, indent=2) + '\n', encoding='utf-8')
            temporary.replace(state_path)
            sent += 1
            print(f'Emailed {len(games)} new prediction(s) to {recipient}.')
    return sent
