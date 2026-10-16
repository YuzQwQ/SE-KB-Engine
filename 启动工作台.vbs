Option Explicit
Dim shell, files, root, python
Set shell = CreateObject("WScript.Shell")
Set files = CreateObject("Scripting.FileSystemObject")
root = files.GetParentFolderName(WScript.ScriptFullName)
python = root & "\.venv\Scripts\pythonw.exe"
If Not files.FileExists(python) Then
    MsgBox "Project Python environment not found." & vbCrLf & "Run in the project folder:" & vbCrLf & "uv sync --frozen --extra api --extra desktop --group dev", 48, "SE-KB Launcher"
    WScript.Quit 1
End If
shell.CurrentDirectory = root
shell.Run Chr(34) & python & Chr(34) & " " & Chr(34) & root & "\start_launcher.py" & Chr(34), 0, False
