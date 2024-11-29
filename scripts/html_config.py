CodeCheckHTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>代码检查</title>
    <style>
        th, td{{
            padding: 8px;
        }}
        table{{
            background: ghostwhite;
            margin-left: 40px;
            margin-top: 40px;
        }}
        tr{{
            text-align: center;
        }}
    </style>
</head>
<body>
    <table border="10px" width="30%">
    <tr>
        <th width="40%">检查项</th>
        <th  width="60%">结果</th>
    </tr>
    <tr>
        <td>致命</td>
        <td>{0}</td>
    </tr>
    <tr>
        <td>严重</td>
        <td>{1}</td>
    </tr>
    <tr>
        <td>一般</td>
        <td>{2}</td>
    </tr>
    <tr>
        <td>提示</td>
        <td>{3}</td>
    </tr>
    <tr>
        <td>问题总数</td>
        <td>{4}</td>
    </tr>
</table>
<br>
codecheck 任务链接: <a href="{5}">{6}</a>
</body>
</html>
"""

BuildLogHTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{0}</title>
</head>
<body>
    <pre>
        {1}
    </pre>
</body>
</html>
"""