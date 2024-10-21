#! -*- coding: utf-8 -*-

table_header = """
<table style="border-collapse: collapse">
    <tr>
        <th>检查项</th>
        <th>状态</th>
    </tr>
"""

table_body = """
<tr>
    <td>{0}</td>
    <td>&#{1};</td>
</tr>
"""

# 检查项映射表, key为标准命名
check_name_map = {
    "sca": ["sca"],
    "anti_poison": ["anti_poison", "防投毒扫描"],
    "build": ["build", "Build构建", "pr构建编译"],
}

GithubAddr = "https://api.github.com/repos"  # Gitee 接口地址

# 北京四区
PipelineAddr = "https://cloudpipeline-ext.cn-north-4.myhuaweicloud.com"  # 流水线地址
HWIAMAddr = "https://iam.cn-north-4.myhuaweicloud.com/v3/auth/tokens"
