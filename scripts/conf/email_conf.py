#! -*- coding: utf-8 -*-

class EmailConf:
    SMTP_HOST = "smtp.163.com"
    SMTP_PORT = "465"
    SMTP_USERNAME = "17625331900@163.com"
    SMTP_PASSWORD = "XULEYDWOBPCXPZBC"
    SMTP_SENDER = "17625331900@163.com"
    SMTP_RECEIVER = ";"  # 以;隔开
    EMAIL_SUBJECT = 'Ascend社区新建代码仓提醒'


class OwnersCollectionsConfig:
    Enterprise = "ascend"
    Token = "****9018ba07f30b**2241533af*****"
    Retry_times = 3
    Trigger = 12  # Hour
    ExcludeRepo = "owners_collections"
    User = "ascend-ci-bot"
    TargetFileName = "OWNERS"
