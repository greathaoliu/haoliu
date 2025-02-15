Function CallDeepSeekAPI(api_key As String, inputText As String) As String
    Dim API As String
    Dim SendTxt As String
    Dim Http As Object
    Dim status_code As Integer
    Dim response As String

    API = "https://api.siliconflow.cn/v1/chat/completions"
    SendTxt = "{""model"": ""deepseek-ai/DeepSeek-V3"", ""messages"": [{""role"":""system"", ""content"":""You are a Word assistant""}, {""role"":""user"", ""content"":""" & inputText & """}], ""stream"": false}"
    '想用R1模型，就把上面的model的deepseek-ai/DeepSeek-V3换成deepseek-ai/DeepSeek-R1

    Set Http = CreateObject("MSXML2.XMLHTTP")
    With Http
        .Open "POST", API, False
        .setRequestHeader "Content-Type", "application/json"
        .setRequestHeader "Authorization", "Bearer " & api_key
        .send SendTxt
        status_code = .Status
        response = .responseText
    End With
    If status_code = 200 Then
        CallDeepSeekAPI = response
    Else
        CallDeepSeekAPI = "Error: " & status_code & " - " & response
    End If

    Set Http = Nothing
End Function

Sub DeepSeekV3()
    Dim api_key As String
    Dim inputText As String
    Dim response As String
    Dim regex As Object
    Dim matches As Object
    Dim originalSelection As Range

    ' API Key
    api_key = "输入你的API Key"
    If api_key = "" Then
        MsgBox "Please enter the API key.", vbExclamation
        Exit Sub
    End If

    ' 检查是否有选中文本
    If Selection.Type <> wdSelectionNormal Then
        MsgBox "Please select text.", vbExclamation
        Exit Sub
    End If

    ' 保存原始选区
    Set originalSelection = Selection.Range.Duplicate

    ' 处理特殊字符
    inputText = Selection.Text
    inputText = Replace(inputText, "\", "\\")
    inputText = Replace(inputText, vbCrLf, " ")
    inputText = Replace(inputText, vbCr, " ")
    inputText = Replace(inputText, vbLf, " ")
    inputText = Replace(inputText, """", "\""") ' 转义双引号

    ' 发送 API 请求
    response = CallDeepSeekAPI(api_key, inputText)

    ' 处理 API 响应
    If Left(response, 5) <> "Error" Then
        ' 解析 JSON
        Set regex = CreateObject("VBScript.RegExp")
        With regex
            .Global = True
            .MultiLine = True
            .IgnoreCase = False
            .Pattern = """content"":""(.*?)""" ' 匹配 JSON 的 "content" 字段
        End With
        Set matches = regex.Execute(response)

        If matches.Count > 0 Then
            ' 提取 API 响应的文本内容
            response = matches(0).SubMatches(0)

            ' 处理转义字符
            response = Replace(response, "\n", vbCrLf)
            response = Replace(response, "\\", "\") ' 处理 JSON 里的反斜杠
            response = Replace(response, "&", "") ' 过滤 `&`，防止意外符号

            ' 让光标移动到文档末尾，防止覆盖已有内容
            Selection.Collapse Direction:=wdCollapseEnd
            Selection.TypeParagraph
            Selection.TypeText Text:=response

            ' 将光标移回原来选中文本的末尾
            originalSelection.Select

        Else
            MsgBox "Failed to parse API response.", vbExclamation
        End If
    Else
        MsgBox response, vbCritical
    End If
End Sub
