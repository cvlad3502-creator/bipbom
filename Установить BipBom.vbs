Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
dir = fso.GetParentFolderName(WScript.ScriptFullName)
sh.CurrentDirectory = dir

venvPy = dir & "\.venv\Scripts\python.exe"

If Not fso.FileExists(venvPy) Then
  r = sh.Run("py -m venv """ & dir & "\.venv""", 0, True)
  If r <> 0 Then
    MsgBox "Не удалось создать окружение. Проверьте, что установлен Python 3.10+ (команда py).", 16, "BipBom"
    WScript.Quit 1
  End If
End If

r = sh.Run("""" & venvPy & """ -m pip install -q -r """ & dir & "\requirements.txt""", 0, True)
If r <> 0 Then
  MsgBox "Не удалось установить зависимости. Нужен интернет.", 16, "BipBom"
  WScript.Quit 1
End If

MsgBox "Готово. Теперь запускайте 'Запустить бота.vbs'.", 64, "BipBom"
