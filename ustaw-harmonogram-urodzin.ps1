$ErrorActionPreference = 'Stop'
$taskName = 'Lidertax - podglady urodzin'
$taskRoot = $PSScriptRoot
if ((Get-TimeZone).Id -ne 'GMT Standard Time') {
    throw 'Komputer musi miec strefe London (GMT Standard Time), aby 09:30 oznaczalo czas UK.'
}
$taskUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$scheduler = New-Object -ComObject 'Schedule.Service'
$scheduler.Connect()
$folder = $scheduler.GetFolder('\')
$task = $scheduler.NewTask(0)
$task.RegistrationInfo.Description = 'Podglady urodzin tylko do pm@lidertax.co.uk. Codziennie 09:30 UK, po logowaniu oraz po pominietym terminie. Klienci nie otrzymuja wiadomosci.'
$task.Principal.UserId = $taskUser
$task.Principal.LogonType = 3
$task.Principal.RunLevel = 0
$task.Settings.Enabled = $true
$task.Settings.StartWhenAvailable = $true
$task.Settings.DisallowStartIfOnBatteries = $false
$task.Settings.StopIfGoingOnBatteries = $false
$task.Settings.MultipleInstances = 2
$task.Settings.ExecutionTimeLimit = 'PT30M'
$task.Settings.WakeToRun = $false
$daily = $task.Triggers.Create(2)
$daily.StartBoundary = (Get-Date).Date.ToString('yyyy-MM-dd') + 'T09:30:00'
$daily.DaysInterval = 1
$daily.Enabled = $true
$logon = $task.Triggers.Create(9)
$logon.UserId = $taskUser
$logon.Delay = 'PT1M'
$logon.Enabled = $true
$action = $task.Actions.Create(0)
$action.Path = Join-Path $env:WINDIR 'System32\wscript.exe'
$action.Arguments = '//B //NoLogo "' + (Join-Path $taskRoot 'projekty\bitrix24-urodziny\run_pilot_hidden.vbs') + '"'
$action.WorkingDirectory = $taskRoot
$registered = $folder.RegisterTaskDefinition($taskName, $task, 6, $taskUser, $null, 3)
Write-Host ('Zarejestrowano: ' + $registered.Name)
Write-Host ('Nastepny termin: ' + $registered.NextRunTime)
Write-Host '09:30 czasu UK + po zalogowaniu; pominięty termin zostanie wykonany po udostepnieniu komputera.'
