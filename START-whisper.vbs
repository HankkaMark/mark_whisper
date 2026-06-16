' Launch Whisper without cmd.exe (corporate firewall often blocks cmd/bat)
' Double-click this file, or pin to taskbar.
Option Explicit

Dim fso, shell, base, py, cmd
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
base = fso.GetParentFolderName(WScript.ScriptFullName)
py = base & "\.venv\Scripts\pythonw.exe"

If Not fso.FileExists(py) Then
  MsgBox "Whisper is not installed." & vbCrLf & vbCrLf & _
         "Ask IT to run once (offline):" & vbCrLf & _
         base & "\tools\bootstrap_install.py" & vbCrLf & vbCrLf & _
         "Using WinPython if available.", vbCritical, "Whisper"
  WScript.Quit 1
End If

shell.CurrentDirectory = base
shell.Environment("PROCESS")("PYTHONPATH") = base
cmd = """" & py & """ -m whisper"
' 0 = hidden window (tray only)
shell.Run cmd, 0, False
