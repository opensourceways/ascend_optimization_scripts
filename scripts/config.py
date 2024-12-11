#! -*- coding: utf-8 -*-

# *********************************  HTML配置  **********************************

table_header = """
<table style="border-collapse: collapse">
    <tr>
        <th>检查项</th>
        <th>状态</th>
        <th colspan="2">详情</th>
        <th>日志</th>
        <th>出包</th>
    </tr>
"""

table_body = """
<tr>
    <td>{0}</td>
    <td>&#{1};</td>
    <td colspan="2">{2}</td>
    <td>{3}</td>
    <td>{4}</td>
</tr>
"""

# *********************************  请各位CIE认真阅读以下配置参数并修改  **********************************

# 检查项映射表, key为标准命名
check_name_map = {
    "sca": ["sca", "codecheck_scan", "CodeSCA", "CodeSCA检查"],
    "anti_poison": ["anti_poison", "codecheck_ftd", "防投毒扫描"],
    "code_check": ["code_check", "codecheck", "codecheck扫描", "CodeCheck代码检查"],
    "dt_check": ["dt_check", "DT"],
    "build": ["build", "Build构建", "pr构建编译", "build构建"],
    "build_arm": ["build_arm", "Build_ARM"],
    "build_x86": ["build_x86", "Build_X86"],
}

OBSName = "mindstudio-pr-log"
GiteeAddr = "https://gitee.com/api/v5/repos"  # Gitee 接口地址

# 北京四区
CodeBuildAddr = "https://cloudbuild-ext.cn-north-4.myhuaweicloud.com"  # 编译地址
CodeartsAPI = "https://cloudpipeline-ext.cn-north-4.myhuaweicloud.com/v5"  # codearts接口前缀
CodeArtsDomain = "https://devcloud.cn-north-4.huaweicloud.com"  # codearts域名
HWLoginAPI = "https://iam.cn-north-4.myhuaweicloud.com/v3/auth/tokens"  # 华为云登录地址
MajunURL = "https://majun.osinfra.cn"  # Majun域名
