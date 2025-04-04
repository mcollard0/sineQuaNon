' MultiValueSearchAndReplace.bas / vba / xlsm
'
' This script accepts multiple values in a A$:B$ range and replaces them in a given search range. So for example, you can replace a column of car colors with normalized values such as BLUE->1, RED->2. The manner is case insensitive. 
'
' Application: this is commonly used for importing customer-sourced data in Excel to a database. 
'
'
' This VBA script was part of a specified domain knowledge spreadsheet at one time. AS non-germaine here, it's been removed.
'
'
'

Dim OpenBook As Workbook
Public Declare PtrSafe Sub Sleep Lib "kernel32" (ByVal Milliseconds As LongPtr)

Sub MultiFindNReplace()
On Error Resume Next

'Update 20221201
' Adds error handling

Dim Rng As range

Dim InputRng As range, ReplaceRng As range
xTitleId = "toolsforExcel"

Set InputRng = Application.Selection


Set InputRng = Application.InputBox("Select Column to change ", xTitleId, InputRng.Address, Type:=8)
'If InputRng.Rows = 0 Then End

Set ReplaceRng = Application.InputBox("Replace Range :", xTitleId, Type:=8)
If ReplaceRng.Rows.Count < 1 Or ReplaceRng.Columns.Count <> 2 Then
    r = MsgBox("Please select at least one row of data to change, and a two columns of oldvalue:newvalue to replace it with.", 0, "Nothing to be done")
    End
End If
Application.ScreenUpdating = False

For Each Rng In ReplaceRng.Columns(1).Cells
    InputRng.Replace what:=Rng.Value, replacement:=Rng.Offset(0, 1).Value
Next

Application.ScreenUpdating = True

End Sub
Function Out(towrite)
    Print #1, towrite:
    Debug.Print towrite
End Function
Function Out2(towrite)
    Print #2, towrite:
    Debug.Print towrite
End Function
