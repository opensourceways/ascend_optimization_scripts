#! -*- coding: utf-8 -*-

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

GiteeAddr = "https://gitee.com/api/v5/repos/"  # Gitee 接口地址

# 北京四区
CodeBuildAddr = "https://cloudbuild-ext.cn-north-4.myhuaweicloud.com"  # 编译地址
PipelineAddr = "https://cloudpipeline-ext.cn-north-4.myhuaweicloud.com"  # 流水线地址
CodeArtsAddr = "https://devcloud.cn-north-4.huaweicloud.com"
# HWCloudAddr = "https://auth.huaweicloud.com/authui/federation/websso?domain_id=0d336831568090260fd5c01450729240&idp=OneAcess&protocol=saml"
HWIAMAddr = "https://iam.cn-north-4.myhuaweicloud.com/v3/auth/tokens"

OBSName = "mindstudio-pr-log"

NA = "N/A"
