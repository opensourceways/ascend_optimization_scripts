CodeCheckHTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>代码检查</title>
</head>
<body>
    <table>
    <tr>
        <th>检查项</th>
        <th>结果</th>
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
</body>
</html>
"""


BuildLogHTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{0}</title>
</head>
<body>
    <p>
        {1}
    </p>
</body>
</html>
"""