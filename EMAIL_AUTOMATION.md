# Hourly email predictions

`email_config.json` contains the sender and recipients. Add addresses to the
`recipients` list whenever needed. No passwords belong in that file.

Sender: `ahgrossman96@gmail.com`.
Recipients: `ahgrossman96@gmail.com`, `the.lauen.malik@gmail.com`.

## Finish setup locally

Enable Google 2-Step Verification, then create a Google app password:
[Google's instructions](https://support.google.com/accounts/answer/185833).
App passwords are unavailable for some accounts; if yours does not offer one,
Gmail OAuth would need to replace this SMTP setup.

From this project folder, run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\setup_automation.ps1
```

Enter the app password at the hidden local prompt. It is encrypted by Windows
for your user on this computer in `.gmail-credential.xml`, then the task is
enabled. Do not paste your password into chat. The setup script does not send
a test email or run the pipeline. An environment variable named
`MLB_GMAIL_APP_PASSWORD` is also supported for manually managed deployments.

## What runs

Task Scheduler task: **MLB Model Hourly Predictions**.
Checks run every hour on the hour, 24 hours/day, March 1-November 30 inclusive.
Its calendar trigger excludes December, January, and February. The pipeline
also checks the season using America/New_York. This computer uses Eastern time;
if that setting changes, the task's clock times change with it.

Windows must be signed in (a locked session is fine), awake, and online. The task
does not wake a sleeping computer and does not run while signed out. A missed
check may run after the computer becomes available. Concurrent runs are blocked.

The task invokes:

```powershell
.\.venv\Scripts\python.exe main.py --project project-d31ef9de-ef00-481f-ae3 --scheduled --email
```

Each check fetches matchups. If no ready, unemailed games exist, it stops before
refreshing statistics. Otherwise it refreshes statistics, predicts, and emails
only successfully predicted games that the recipient has not already received.
Each recipient receives a separate email. No emails are sent for missing
lineups, missing history, no games, or an unchanged set of predictions.

"New" means a new game ID and game date, per recipient. Changed probabilities
for a previously emailed game do not trigger another email. Doubleheaders have
separate IDs. New recipients may receive any still-upcoming game not yet sent
to them. Delivery history is in `email_state.json`; keep it to prevent repeats.

The record is saved after Gmail accepts each recipient's message. SMTP cannot
guarantee exactly-once delivery: a crash after acceptance but before saving the
record, or an ambiguous network failure, can cause a duplicate on a later run.
Existing delivery records are never silently discarded if the file is invalid.

Raw pitch data must already be current: there is no raw-data update script in
this project. Offline tests pass without sending mail, but a live end-to-end
run with ready lineups and Gmail authorization is still required.

Manual `main.py` runs without `--email` continue to generate predictions only.
The latest predictions stay in `predictions.json`. Quiet hourly checks leave
the previous predictions file untouched; its date/timestamp identifies its age.
Scheduled output and errors are appended to `pipeline.log`. The Windows task
uses `pythonw.exe` so hourly checks do not open a console window.

Inspect/stop the schedule in Windows Task Scheduler, or use:

```powershell
Get-ScheduledTask -TaskName 'MLB Model Hourly Predictions'
Disable-ScheduledTask -TaskName 'MLB Model Hourly Predictions'
```
