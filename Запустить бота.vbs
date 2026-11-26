Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
dir = fso.GetParentFolderName(WScript.ScriptFullName)
sh.CurrentDirectory = dir

py = dir & "\.venv\Scripts\pythonw.exe"
pyw = dir & "\.venv\Scripts\python.exe"

If Not fso.FileExists(py) Then
  MsgBox "Сначала запустите 'Установить BipBom.vbs' — он подготовит окружение.", 16, "BipBom"
  WScript.Quit 1
End If

sh.Run """" & py & """ """ & dir & "\tray.py""", 0, False
WScript.Quit 0
