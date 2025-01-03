#! -*- coding: utf-8 -*-

class EmailConf:
    SMTP_HOST = "****"
    SMTP_PORT = "****"
    SMTP_USERNAME = "****"
    SMTP_PASSWORD = "****"
    SMTP_SENDER = "****"
    SMTP_RECEIVER = "****"  # 以;隔开
    EMAIL_SUBJECT = 'Ascend社区代码仓新增提醒'


class OwnersCollectionsConfig:
    Enterprise = "ascend"
    Token = "****"
    Retry_times = 3
    Trigger = 12  # Hour
    ExcludeRepo = "owners_collections"
    User = "****"
    TargetFileName = "OWNERS"


EmailContent = """
<p>Dear CIEs,</p>
<span>我们检测到Ascend社区有新增的代码仓:</span>
<br/>
<br/>
{{repos}}
<br/>
<p>请及时配置该代码仓codearts门禁流水线；如无需配置，请忽略</p>
<span>------</span>
<span>Ascend社区代码仓监测服务</span>
"""
