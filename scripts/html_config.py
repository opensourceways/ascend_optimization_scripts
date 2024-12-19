#! -*- coding: utf-8 -*-

TableHeader = """
<table style="border-collapse: collapse" border=1>
    <tr>
        <th>检查项</th>
        <th>状态</th>
        <th>日志</th>
    </tr>
"""
###################################################
TableBody = """
<tr>
    <td>{0}</td>
    <td>&#{1};</td>
    <td><a href="{2}">查看日志</a></td>
</tr>
"""
###################################################
TableBodyPure = """
<tr>
    <td>{0}</td>
    <td>{1}</td>
    <td><a href="{2}">查看日志</a></td>
</tr>
"""
###################################################
TableBodyURL = """
<tr>
    <td>{0}</td>
    <td colspan="2"><a href="{1}">点击跳转</a></td>
</tr>
"""
###################################################
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
    <tr>
        <td colspan="2"><a href="{5}">点击跳转至codecheck任务</a></td>
    </tr>
</table>
</body>
</html>
"""
###################################################
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
