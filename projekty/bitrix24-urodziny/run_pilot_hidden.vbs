Option Explicit
Dim shell, files, root, python, script, command, result
Set shell = CreateObject("WScript.Shell")
Set files = CreateObject("Scripting.FileSystemObject")
root = files.GetParentFolderName(files.GetParentFolderName(files.GetParentFolderName(WScript.ScriptFullName)))
python = shell.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\hermes\hermes-agent\venv\Scripts\python.exe"
script = root & "\projekty\bitrix24-urodziny\birthday_pilot.py"
shell.CurrentDirectory = root
command = Chr(34) & python & Chr(34) & " " & Chr(34) & script & Chr(34) & " --run --not-before 09:30"
result = shell.Run(command, 0, True)
WScript.Quit result
