#!/usr/bin/python3
# coding: utf-8
# author: 9ian1i   https://github.com/Qianlitp

"""
    4698

    域控的计划任务创建
"""

from models.Log import Log
from modules.detect.DetectBase import DetectBase, MEDIUM_LEVEL

EVENT_ID = [4698]

ALERT_CODE = "508"
TITLE = "域控新增计划任务"
DESC_TEMPLATE = "来自于 [source_ip]([source_workstation]) 使用身份 [source_user_name] 在域控 [dc_hostname] " \
                "上创建了新的计划任务 [task_name]。"


class ScheduledTasks(DetectBase):
    def __init__(self):
        super().__init__(code=ALERT_CODE, title=TITLE, desc=DESC_TEMPLATE)

    def run(self, log: Log):
        self.init(log=log)

        return self._generate_alert_doc()

    def _generate_alert_doc(self, **kwargs) -> dict:
        source_ip = self._get_source_ip_by_logon_id(self.log.subject_info.logon_id,
                                                    self.log.subject_info.full_user_name)
        form_data = {
            "source_workstation": self._get_workstation_by_source_ip(source_ip),
            "source_ip": source_ip,
            "source_user_name": self.log.subject_info.user_name,
            "source_user_sid": self.log.subject_info.user_sid,
            "source_logon_id": self.log.subject_info.logon_id,
            "source_domain": self.log.subject_info.domain_name,
            "task_name": self.log.event_data["TaskName"],
            "task_content_raw": self.log.event_data["TaskContent"],
            "dc_hostname": self.log.dc_host_name,
            **kwargs
        }
        doc = self._get_base_doc(
            level=self._get_level(),
            unique_id=self._get_unique_id(self.code, self.log.subject_info.user_name),
            form_data=form_data
        )
        return doc

    def _get_level(self) -> str:
        return MEDIUM_LEVEL


