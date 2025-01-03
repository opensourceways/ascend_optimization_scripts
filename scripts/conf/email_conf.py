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
