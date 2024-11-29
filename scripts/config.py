#! -*- coding: utf-8 -*-

# 检查项映射表, key为标准命名
check_name_map = {
    "sca": ["sca"],
    "anti_poison": ["anti_poison", "防投毒扫描"],
    "build": ["build", "Build构建", "pr构建编译"],
}

GithubAddr = "https://api.github.com/repos"  # Github 接口地址
GiteeAddr = "https://gitee.com/api/v5/repos"  # Gitee 接口地址

# 北京四区
PipelineAPI = "https://cloudpipeline-ext.cn-north-4.myhuaweicloud.com"  # 流水线API地址
CodeCheckAddr = "https://codecheck-ext.cn-north-4.myhuaweicloud.com"  # 代码检查地址
BuildAddr = "https://cloudbuild-ext.cn-north-4.myhuaweicloud.com"  # 编译地址
HWIAMAddr = "https://iam.cn-north-4.myhuaweicloud.com"  # 获取token地址
PipelineUrl = "https://devcloud.cn-north-4.huaweicloud.com/cicd/project"  # 流水线URL
OBSDomain = "https://opensourceways-ci.test.osinfra.cn"  # OBS域地址,访问文件用
OBSAddr = "obs.cn-north-4.myhuaweicloud.com"  # 写入文件用
OBSName = "opensourceways-ci"
