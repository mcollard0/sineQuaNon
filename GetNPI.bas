
Sub getNPIs()
    ' D first name, F lasdt name h NPI
    If InStr(1, ActiveWorkbook.Name, "Modality Mapping MultiValue", vbTextCompare) Then
        Windows(1).WindowState = xlNormal
        Windows(1).WindowState = xlMinimized
    End If

    If (InStr(1, ActiveWorkbook.Name, "Compend") = 0 And InStr(1, ActiveWorkbook.Name, "NPI") = 0) Then
    For Each oWb In Application.Workbooks
     If InStr(1, oWb.Name, "Compendium", vbTextCompare) And oWb.Name <> ActiveWorkbook.Name Then Workbooks(oWb.Name).Activate
    Next
    End If
    
    If (InStr(1, ActiveWorkbook.Name, "Compend") = 0) And (InStr(1, ActiveWorkbook.Name, "PCP") = 0) Then result = MsgBox("Please select the Compendium Physicians Tab and hit Okay. If a compendium is not open, a dialog will ask you to open it.", vbOKCancel, "Select Compendium")
    If InStr(1, ActiveSheet.Name, "Resources") = False Then OpenBook = Get_Compendium() ' open a closed compendium
    rowCurrent = 2 ' 11 standard
    
    
    Filename = "C:\temp\NPI.sql"
    Open Filename For Output As #1
    
    Call Out(vbCrLf & vbCrLf & " --/// NPI Guessing Script ///--" & vbCrLf)
    
    For A = rowCurrent To 9000
        'If (rowCurrent Mod 100 = 0) Then
        DoEvents
        
        Out "-- Row " & A
        'Sleep 1                                   ' Make it at least look difficult
        ActiveSheet.range("C" & rowCurrent).Select
        NPI_Number = ActiveCell.Value
        If (Len(NPI_Number) > 1) Then GoTo Nextup:
        ActiveSheet.range("D" & rowCurrent).Select
        first_name = ActiveCell.Value
        ActiveSheet.range("F" & rowCurrent).Select
        last_name = ActiveCell.Value
        
        ActiveSheet.range("J" & rowCurrent).Select
        city = ActiveCell.Value
        ActiveSheet.range("K" & rowCurrent).Select
        If (Len(ActiveCell.Value) = 2) Then state = ActiveCell.Value Else state = ""
        
        If (last_name = "" And first_name = "") Then GoTo CloseUp:
        If (Len(Trim(NPI_Number)) < 10) Then
            NPI_Number = getNPI(last_name, first_name, state)
            Out (first_name + " " + last_name + ": " + NPI_Number)
            Sleep 1                                 ' Make it at least look difficult
            
            If (Len(NPI_Number) = 10) Then
                ActiveSheet.range("C" & rowCurrent).Select
                ActiveCell.Value = NPI_Number
                ActiveCell.NoteText ("This value auto-filled from NPPES.") ';
            End If
        End If
        
        Out (CellString):
Nextup:
    rowCurrent = rowCurrent + 1
Next

CloseUp:
 
    Out ("ROLLBACK -- or COMMIT;")
    
    ' show your work
    Close #1
    'returnvalue = Shell("notepad.exe " & Filename, vbNormalFocus)

    'Cleanup
    Windows(2).WindowState = xlNormal ' seco nd most recently used




    
End Sub



Function getNPI(last_name, first_name, state)
    getNPI = "" '; set up default value
    url = "https://npiregistry.cms.hhs.gov/api/?version=2.1&last_name=" & last_name & "&first_name=" & first_name & "&state=" & state
    Dim vJSON As Variant, sState As String
    
    Set winHttpReq = CreateObject("WinHttp.WinHttpRequest.5.1")
    With winHttpReq
        .Open "GET", url, False
        .Send
        .waitForResponse 4000
        result = .ResponseText
        Debug.Print .ResponseText
        JSON.Parse .ResponseText, vJSON, sState
        getResults = vJSON("result_count")
        If (getResults = 1) Then ' Exact match
            getNPI = vJSON("results")(0)("number")
        End If
    End With
End Function