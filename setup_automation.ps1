<# Register the hourly March-November task and securely configure Gmail locally. #>
param([switch]$RegisterOnly)
$ErrorActionPreference = 'Stop'
$taskName = 'MLB Model Hourly Predictions'
$rootPath = $PSScriptRoot
$pythonPath = Join-Path $rootPath '.venv\Scripts\pythonw.exe'
$credentialPath = Join-Path $rootPath '.gmail-credential.xml'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw "Python environment missing: $pythonPath" }
$config = Get-Content -LiteralPath (Join-Path $rootPath 'email_config.json') -Raw | ConvertFrom-Json

if (-not $RegisterOnly) {
    Write-Host "Configure Gmail sending as $($config.sender)."
    Write-Host 'Use a Google app password, not your regular Gmail password.'
    $appPassword = Read-Host 'Google app password (hidden)' -AsSecureString
    if ($appPassword.Length -eq 0) { throw 'App password cannot be empty' }
    $credential = [System.Management.Automation.PSCredential]::new($config.sender, $appPassword)
    $credential | Export-Clixml -LiteralPath $credentialPath
}

# A monthly calendar trigger avoids launching the task at all in Dec-Feb.
# Local computer timezone is Eastern; a second season check lives in main.py.
$days = (1..31 | ForEach-Object { "<Day>$_</Day>" }) -join ''
$months = @('March','April','May','June','July','August','September','October','November')
$monthXml = ($months | ForEach-Object { "<$_ />" }) -join ''
$userId = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$escapedUser = [System.Security.SecurityElement]::Escape($userId)
$escapedRoot = [System.Security.SecurityElement]::Escape($rootPath)
$escapedPython = [System.Security.SecurityElement]::Escape($pythonPath)
$mainPath = Join-Path $rootPath 'main.py'
$arguments = '-u "' + $mainPath + '" --project project-d31ef9de-ef00-481f-ae3 --scheduled --email'
$escapedArguments = [System.Security.SecurityElement]::Escape($arguments)
$enabled = if (Test-Path -LiteralPath $credentialPath) { 'true' } else { 'false' }
$xml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo><Description>Check hourly March-November and email only new game predictions.</Description></RegistrationInfo>
  <Triggers><CalendarTrigger>
    <Repetition><Interval>PT1H</Interval><Duration>P1D</Duration><StopAtDurationEnd>false</StopAtDurationEnd></Repetition>
    <StartBoundary>2026-01-01T00:00:00</StartBoundary><Enabled>true</Enabled>
    <ScheduleByMonth><DaysOfMonth>$days</DaysOfMonth><Months>$monthXml</Months></ScheduleByMonth>
  </CalendarTrigger></Triggers>
  <Principals><Principal id="Author"><UserId>$escapedUser</UserId><LogonType>InteractiveToken</LogonType><RunLevel>LeastPrivilege</RunLevel></Principal></Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries><StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <StartWhenAvailable>true</StartWhenAvailable><RunOnlyIfNetworkAvailable>true</RunOnlyIfNetworkAvailable>
    <AllowStartOnDemand>true</AllowStartOnDemand><Enabled>$enabled</Enabled><Hidden>false</Hidden>
    <WakeToRun>false</WakeToRun><ExecutionTimeLimit>PT2H</ExecutionTimeLimit>
  </Settings>
  <Actions Context="Author"><Exec><Command>$escapedPython</Command><Arguments>$escapedArguments</Arguments><WorkingDirectory>$escapedRoot</WorkingDirectory></Exec></Actions>
</Task>
"@
Register-ScheduledTask -TaskName $taskName -Xml $xml -Force | Out-Null
Write-Host "Registered: $taskName"
if ($enabled -eq 'false') {
    Write-Host 'Task is DISABLED until Gmail is configured. Run this script again without -RegisterOnly.'
} else {
    Write-Host 'Task is ENABLED: every hour on the hour, March-November, using this computer timezone.'
    Write-Host 'You must be signed into Windows; the computer must be awake and online.'
    Write-Host 'No email or pipeline has been run by this setup script.'
}
