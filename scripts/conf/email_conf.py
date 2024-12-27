#! -*- coding: utf-8 -*-

class Config:
    EMAIL_SUBJECT = 'Ascend社区代码仓新增提醒'
    Enterprise = "ascend"
    Retry_times = 3
    Trigger = 12  # Hour
    ExcludeRepo = "owners_collections"
    TargetFileName = "OWNERS"
