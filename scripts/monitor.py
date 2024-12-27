#! -*- coding: utf-8 -*-

import argparse
import functools
import json
import os
import subprocess
import time
import warnings
import requests
import logging
import yaml
import smtplib

from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from config import GithubAddr, check_name_map, PipelineAPI, HWIAMAddr, PipelineUrl, GiteeAddr, CodeCheckAddr, \
    BuildAddr, OBSDomain, OBSAddr, OBSName
from html_config import CodeCheckHTML, BuildLogHTML, TableHeader, TableBody, TableBodyURL, TableBodyPure

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)s: %(message)s")

status_map = dict(COMPLETED="9989",
                  RUNNING="128346",
                  CANCELED="10060",
                  FAILED="10060", BLANK="32",
                  UNSELECTED="128762")

Retry_times = 3


def retry_decorator(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        is_success, res = True, None
        for i in range(Retry_times):
            try:
                res = func(*args, **kwargs)
            except Exception as e:
                is_success = False
                logging.error(e)
                logging.info(f"exec {func.__name__} failed {i + 1} times...")
            finally:
                if is_success:
                    break
            time.sleep(5)

        if not is_success:
            raise Exception(f"{func.__name__} still fail after try {Retry_times} times...")
        return res

    return wrapper


class GithubApp:

    def __init__(self,
                 token: str,
                 owner: str,
                 repo: str,
                 pr_id: str
                 ):
        """
        @token: github token
        @owner: 代码仓所属企业
        @repo: 代码仓名称
        @pr_id: 提交pr id
        """
        self.token = token
        self.owner = owner
        self.repo = repo
        self.pr_id = pr_id
        self.prefix_url = f'{GithubAddr}/{owner}/{repo}/issues/{pr_id}'
        self.prefix_gitee_url = f'{GiteeAddr}/{owner}/{repo}/pulls/{pr_id}'

    @retry_decorator
    def add_comment(self, msg: str, is_github: bool = True):
        """
        @msg: 评论内容
        @is_github: 是否是github仓
        """
        if is_github:
            url = f'{self.prefix_url}/comments'
            logging.info(f"comment url: {url}")
            response = requests.post(url,
                                     json=dict(body=msg),
                                     headers=dict(Authorization=f"token {self.token}")
                                     )
        else:
            url = f'{self.prefix_gitee_url}/comments'
            logging.info(f"comment url: {url}")
            response = requests.post(url,
                                     data=dict(access_token=self.token, body=msg)
                                     )

        if response.status_code in [200, 201, 204]:
            logging.info(f'comment success...')
        else:
            logging.info(response.text)
            raise ConnectionError("comment fail...")

    @retry_decorator
    def add_label(self, label: str, is_github: bool = True):
        """
        给 pr 添加标签
        :param is_github:
        :param label: 要增加的标签的名字
        :return:
        """
        if is_github:
            url = f'{self.prefix_url}/labels'
            response = requests.post(url,
                                     json=dict(labels=[label]),
                                     headers=dict(Authorization=f"token {self.token}")
                                     )
        else:
            url = f'{self.prefix_gitee_url}/labels?access_token={self.token}'
            response = requests.post(url,
                                     json=[label]
                                     )

        if response.status_code in [200, 201, 204]:
            logging.info(f"add label: '{label}' success...")
        else:
            logging.info(response.text)
            raise ConnectionError(f"add label '{label}' failure...")

    @retry_decorator
    def del_label(self, label: str, is_github: bool = True):
        """
        删除 pr 标签
        :param label: 待删除标签
        :param is_github:
        :return:
        """
        no_label = ["Label does not exist", "Labels not found"]
        if is_github:
            url = f'{self.prefix_url}/labels/{label}'
            response = requests.delete(url,
                                       headers=dict(Authorization=f"token {self.token}")
                                       )
        else:
            url = f'{self.prefix_gitee_url}/labels/{label}?access_token={self.token}'
            response = requests.delete(url)

        if response.status_code in [200, 201, 204]:
            logging.info(f"delete label: '{label}' success...")
        elif response.status_code == 404 and response.json().get("message") in no_label:
            logging.info(f"label '{label}' not exist...")
        else:
            logging.info(response.text)
            raise ConnectionError(f"delete label '{label}' failure...")


class CheckListRemark:

    def __init__(self,
                 token: str,
                 owner: str,
                 repo: str,
                 pr_id: str,
                 project_id: str,
                 pipeline_id: str,
                 pipeline_run_id: str,
                 username: str,
                 subUsername: str,
                 password: str,
                 ak: str,
                 sk: str,
                 is_github: str,
                 smtp_host: str,
                 smtp_port: str,
                 smtp_username: str,
                 smtp_password: str,
                 smtp_sender: str,
                 ):
        """
        @token: github token
        @owner: 代码仓所属企业
        @repo: 代码仓名称
        @pr_id: 待合入pr id
        @project_id: codearts 项目id
        @pipeline_id: codearts 流水线id
        @pipeline_run_id: codearts 流水线任务id
        @username: codearts 主账户
        @subUsername: codearts 从账户
        @password: codearts 密码
        @ak: codearts ak
        @sk: codearts sk
        @is_github: 是否为github仓
        @smtp_host: smtp host
        @smtp_port: smtp port
        @smtp_username: smtp username
        @smtp_password: smtp password
        @smtp_sender: smtp sender
        """
        self.token = token
        self.owner = owner
        self.repo = repo
        self.pr_id = pr_id
        self.project_id = project_id
        self.pipeline_id = pipeline_id
        self.pipeline_run_id = pipeline_run_id
        self.username = username
        self.subUsername = subUsername
        self.password = password
        self.ak = ak
        self.sk = sk
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_username = smtp_username
        self.smtp_password = smtp_password
        self.smtp_sender = smtp_sender
        self.git_app = GithubApp(token, owner, repo, pr_id)
        self.is_github = True if is_github.lower() == "true" else False
        self.headers = self.get_codearts_token(username, subUsername, password)
        self.log_path = f"/home/logs/{self.repo}/{self.pr_id}"

    @retry_decorator
    def send_mail(self, msg: str, receivers: list):
        """
        发送邮件
        :param msg: 邮件内容
        :param receivers: 邮件接收者
        :return:
        """
        subject = "%s门禁检查结果通知" % self.repo
        receivers.extend(["shishupei@huawei.com", "zhaokunhang@huawei.com", "jun.zhongjun@huawei.com"])

        receivers = list(set(receivers))
        # 构建邮件
        now = datetime.now()
        formatted_time = now.strftime("%Y-%m-%d %H:%M:%S")
        msg = f"代码仓{self.owner}/{self.repo}在{formatted_time}执行的门禁检查结果如下:<br/><br/>" + msg

        if self.is_github:
            url = f"https://github.com/{self.owner}/{self.repo}/pull/{self.pr_id}"
        else:
            url = f"https://gitee.com/{self.owner}/{self.repo}/pulls/{self.pr_id}"

        msg += f"<br/>PR链接: {url}"
        mail_msg = MIMEMultipart()
        mail_msg['From'] = self.smtp_sender
        mail_msg['To'] = ', '.join(receivers)
        mail_msg['Subject'] = subject
        mail_msg.attach(MIMEText(msg, 'html'))

        # 上传附件
        for filename in os.listdir(self.log_path):
            logging.info(f"log filename: {filename}")
            path = os.path.join(self.log_path, filename)

            attach = MIMEApplication(open(path, 'rb').read())
            attach.add_header('Content-Disposition', 'attachment', filename=filename)

            mail_msg.attach(attach)

        # 发送邮件
        try:
            if int(self.smtp_port) == 465:
                server = smtplib.SMTP_SSL(self.smtp_host, int(self.smtp_port))
                server.ehlo()
                server.login(self.smtp_username, self.smtp_password)
            else:
                server = smtplib.SMTP(self.smtp_host, int(self.smtp_port))
                server.ehlo()
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
            server.sendmail(self.smtp_sender, receivers, mail_msg.as_string())
        except Exception as e:
            raise ConnectionError(f"send email failure: {e}")

    @staticmethod
    def convert_check_name_map():
        """
        将检查项映射表key, value翻转过来
        """
        res = {}
        for k, v in check_name_map.items():
            for i in v:
                res[i] = k
        return res

    @staticmethod
    def generate_table(items: list):
        """
        将检查项结果转换成html table
        """
        html = TableHeader
        for item in items:
            check_name, status, link = item.get("check_name"), item.get("status"), item.get("link")
            if check_name == "DT覆盖率":
                html += TableBodyPure.format(check_name, status, link)
            elif check_name == "流水线链接":
                html += TableBodyURL.format(check_name, status)
            elif not link.startswith("https"):
                html += TableBody.replace(r'<a href="{2}">查看日志</a>', link).format(check_name, status)
            else:
                html += TableBody.format(check_name, status, link)
        html = html + "</table>"
        return html

    @staticmethod
    def get_codearts_token(username, subUsername, password):
        """
        获取codearts token信息
        :param username:
        :param subUsername:
        :param password:
        :return:
        """
        logging.info("获取codearts token...")
        user = dict(password=password, domain=dict(name=username), name=subUsername)
        header = {
            "auth": {
                "identity": {
                    "password": {"user": user},
                    "methods": ["password"]
                },
                "scope": {"project": {"name": "cn-north-4"}}
            }
        }
        resp = requests.post(
            url=f"{HWIAMAddr}/v3/auth/tokens",
            data=json.dumps(header)
        )
        token = resp.headers["X-Subject-Token"]
        return {"x-auth-token": token}

    def get_codecheck_statistic(self, task_id: str):
        """
        获取代码检查缺陷详情统计信息
        :param task_id: 代码检查的任务id
        :return:
        """
        url = f"{CodeCheckAddr}/v2/tasks/{task_id}/defects-statistic"
        response = requests.get(url,
                                headers=self.headers)
        return response.json()

    def get_daily_build_number(self, step_run_id):
        """
        获取daily_build_number, 形如 20241119.24， 因流水线可能不携带该参数，所以申明了该方法
        :param step_run_id:
        :return:
        """
        warnings.warn("get_daily_build_number is deprecated", DeprecationWarning)

        url = f"{PipelineAPI}/v5/{self.project_id}/api/pipelines/{self.pipeline_id}/pipeline-runs/{self.pipeline_run_id}/steps/outputs"
        response = requests.get(url,
                                params={"step_run_ids": step_run_id},
                                headers=self.headers
                                )
        results = response.json()['step_outputs'][0]['output_result']
        for entry in results:
            if entry['key'] == 'dailyBuildNumber':
                return entry['value']

    def get_build_number(self, job_id, daily_build_number):
        """
        获取构建编号，数字
        :param job_id:
        :param daily_build_number:
        :return:
        """
        warnings.warn("get_build_number is deprecated", DeprecationWarning)

        url = f'{BuildAddr}/v3/jobs/{job_id}/history'
        response = requests.get(url,
                                params=dict(limit=100, interval=1, offset=0),
                                headers=self.headers
                                )
        records = response.json()['history_records']
        for entry in records:
            if entry['record_id'] == daily_build_number:
                return entry['build_number']

    def get_build_record_id(self, job_id, build_number):
        url = f'{BuildAddr}/v4/jobs/{job_id}/{build_number}/record-info'
        response = requests.get(url, headers=self.headers)
        build_record_id = response.json()['result']['build_record_id']
        return build_record_id

    def get_build_log(self, job_id: str, step_run_id: str):
        """
        获取编译构建的代码
        :param job_id:
        :param step_run_id:
        :return:
        """
        build_number = self.get_build_actual_task_id(job_id, step_run_id)
        record_id = self.get_build_record_id(job_id, build_number)
        url = f"{BuildAddr}/v4/{record_id}/download-log"
        response = requests.get(url, headers=self.headers)
        return response.text

    def save_file(self, job_name: str, content: str) -> str:
        """
        保存日志文件
        :param job_name: 任务名称
        :param content: 文件内容
        :return: 文件绝对路径
        """
        os.makedirs(self.log_path, exist_ok=True)
        file_path = f"{self.log_path}/{self.pr_id}_{job_name}.html"
        with open(file_path, "a+") as f:
            f.write(content)
        return file_path

    def upload_to_obs(self, file_path: str):
        """
        将文件上传至obs
        :param file_path: 文件绝对路径
        :return:
        """
        subprocess.call(
            f"""
            cd /home/logs/{self.repo}/{self.pr_id}
            obsutil config -i={self.ak} -k={self.sk} -e={OBSAddr}
            obsutil cp {file_path} obs://{OBSName}/log/{self.repo}/{self.pr_id}/ -r -f
            """,
            shell=True
        )

    def upload_codecheck_log_to_obs(self, job_name: str, log: dict, job_link: str):
        """
        上传codecheck日志至obs
        :param job_name: 任务名称
        :param log: 日志内容
        :param job_link: codecheck任务链接
        :return:
        """
        severity = log.get("severity")
        values = [severity.get("critical"), severity.get("major"), severity.get("minor"), severity.get("suggestion")]
        content = CodeCheckHTML.format(*values, sum(values), job_link)
        file_path = self.save_file(job_name, content)
        self.upload_to_obs(file_path)

    def upload_build_log_to_obs(self, job_name: str, log: str):
        """
        上传构建日志至obs
        :param job_name: 任务名称
        :param log: 日志内容
        :return:
        """
        content = BuildLogHTML.format(job_name, log)
        file_path = self.save_file(job_name, content)
        self.upload_to_obs(file_path)

    def find_coverage_rate(self, job_name: str) -> str:
        """
        查找覆盖率
        :param job_name: 任务名称
        :return:
        """
        file_path = f"/home/logs/{self.repo}/{self.pr_id}/{self.pr_id}_{job_name}.html"
        with open(file_path, "r") as f:
            for line in f.readlines():
                if "COVERAGE=" in line:  # Go
                    rate = line.split("=")[-1][:4]  # 只保留前四位
                    return f"{rate.strip(' ')}%"
                elif "Jacoco Coverge:" in line:  # Java
                    rate = line.split(":")[-1].strip(" ").split(" ")[0][:4]
                    return f"{rate.strip(' ')}%"

    def get_mail_receives(self):
        """
        从配置文件获取邮件接收人列表
        :return:
        """
        headers = {
            'Authorization': f'token {self.token}',
            'Accept': 'application/vnd.github.v3.raw'  # 请求原始内容
        }
        try:
            yml_url = "https://raw.githubusercontent.com/opensourceways/codearts-ci-config/main/pipeline-config.yml"
            response = requests.get(yml_url, headers=headers)
            response.raise_for_status()  # 如果请求失败，抛出异常

            # 解析YAML内容
            data = yaml.safe_load(response.text)

            # 根据repo名称获取值
            repo_info = data.get(self.repo, {})

            if repo_info:
                return repo_info["mail"].replace(" ", "").split(",")
            else:
                return []
        except requests.RequestException as e:
            logging.error(e)
            return []
        except yaml.YAMLError as e:
            logging.error(e)
            return []

    def get_build_actual_task_id(self, job_id: str, step_run_id: str):
        """
        获取codecheck真实运行的job_id
        :param job_id: codecheck分支id
        :param step_run_id: 流水线步骤id
        :return:
        """
        url = f'{PipelineAPI}/v5/{self.project_id}/api/pipelines/{self.pipeline_id}/pipeline-runs/{self.pipeline_run_id}/jobs/{job_id}/steps/{step_run_id}/jump-link'
        response = requests.get(url,
                                headers=self.headers
                                )

        link: str = response.json().get("jumpLink", "")
        j_id = link.split("/defects?")[0].split("/")[-1]

        return j_id if j_id else job_id

    def run(self):
        # 1. 解析流水线任务结果
        result = []
        no_failure = True
        task_url = f'{PipelineAPI}/v5/{self.project_id}/api/pipelines/{self.pipeline_id}/pipeline-runs/detail?pipeline_run_id={self.pipeline_run_id}'

        resp = requests.get(url=task_url, headers=self.headers)

        logging.info(f"Get pipeline detail status: {resp.status_code}")
        resp_txt = json.loads(resp.text)
        gate_jobs = resp_txt["stages"][0]["jobs"]
        for j in gate_jobs:
            job_name, status = j["name"], j["status"]
            logging.info(f"job name: {job_name}, status: {status}")

            if status == "UNSELECTED":
                continue

            if job_name == "统一评论":
                break

            if status != "COMPLETED":
                no_failure = False

            obs_log_url = f"{OBSDomain}/log/{self.repo}/{self.pr_id}/{self.pr_id}_{job_name}.html"
            item = {"check_name": job_name, "status": status_map.get(status), "link": obs_log_url}

            # 提取日志
            step_run_id = j["steps"][0]["id"]
            job_id = ""
            for entry in j["steps"][0]["inputs"]:
                if entry["key"] != "jobId":
                    continue
                job_id = entry["value"]

            if "代码检查" in job_name and status == "COMPLETED":
                job_id = self.get_build_actual_task_id(job_id, step_run_id)
                log = self.get_codecheck_statistic(job_id)
                url_prefix = PipelineUrl.replace('cicd', 'codechecknew')
                job_link = f"{url_prefix}/{self.project_id}/codecheck/task/{job_id}/defects"  # codecheck任务链接
                self.upload_codecheck_log_to_obs(job_name, log, job_link)

                problems = log.get("severity", {}).get("critical", 0) + log.get("severity", {}).get("major", 0)
                if problems > 0:
                    no_failure = False
                    item["status"] = status_map.get("FAILED")
            elif "代码检查" in job_name and status != "COMPLETED":
                item["link"] = "任务失败, 请重试"
            else:
                try:
                    log = self.get_build_log(job_id, step_run_id)
                    self.upload_build_log_to_obs(job_name, log)
                except Exception as err:
                    logging.error(err)
                    item["link"] = ""

            if "覆盖率" in job_name:
                rate = self.find_coverage_rate(job_name)
                if rate:
                    item["check_name"] = "DT覆盖率"
                    item["status"] = rate

            result.append(item)

        # 2. 统一评论
        url_addr = f'{PipelineUrl}/{self.project_id}/pipeline/detail/{self.pipeline_id}/{self.pipeline_run_id}'
        result.append(dict(check_name="流水线链接", status=url_addr))
        html = self.generate_table(result)
        self.git_app.add_comment(html, self.is_github)

        # 3. 发送邮件
        logging.info("Codearts Pipeline Failed, Send Email...")
        receivers = self.get_mail_receives()
        if receivers:
            self.send_mail(html, receivers)

        # 4. 添加标签
        label = "gate_check_pass"
        if no_failure:
            self.git_app.add_label(label)


def init_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--access_token', help='github access token', required=True, type=str)
    parser.add_argument('--owner', help='owner', required=True, type=str)
    parser.add_argument('--pr_id', help='pr id', required=True, type=str)
    parser.add_argument('--repo', help='code repo', required=True, type=str)
    parser.add_argument('--project_id', help='current pipeline project id', type=str, default=None, required=False)
    parser.add_argument('--pipeline_id', help='current pipeline id', type=str, default=None, required=False)
    parser.add_argument('--pipeline_run_id', help='current pipeline run id', type=str, default=None, required=False)
    parser.add_argument('--username', help='codearts username', required=True, type=str)
    parser.add_argument('--subUsername', help='codearts subUsername', required=True, type=str)
    parser.add_argument('--password', help='codearts password', required=True, type=str)
    parser.add_argument('--ak', help='codearts ak', required=True, type=str)
    parser.add_argument('--sk', help='codearts sk', required=True, type=str)
    parser.add_argument('--is_github', help='is github repo', required=True, type=str)
    parser.add_argument("--smtp_host", help="smtp host", required=True, type=str)
    parser.add_argument("--smtp_port", help="smtp port", required=True, type=str)
    parser.add_argument("--smtp_username", help="smtp username", required=True, type=str)
    parser.add_argument("--smtp_password", help="smtp password", required=True, type=str)
    parser.add_argument("--smtp_sender", help="smtp sender", required=True, type=str)
    return parser.parse_args()


if __name__ == '__main__':
    args = init_args()

    checklist_remark = CheckListRemark(token=args.access_token,
                                       owner=args.owner,
                                       repo=args.repo,
                                       pr_id=args.pr_id,
                                       project_id=args.project_id,
                                       pipeline_id=args.pipeline_id,
                                       pipeline_run_id=args.pipeline_run_id,
                                       username=args.username,
                                       subUsername=args.subUsername,
                                       password=args.password,
                                       ak=args.ak,
                                       sk=args.sk,
                                       is_github=args.is_github,
                                       smtp_host=args.smtp_host,
                                       smtp_port=args.smtp_port,
                                       smtp_username=args.smtp_username,
                                       smtp_password=args.smtp_password,
                                       smtp_sender=args.smtp_sender,
                                       )

    checklist_remark.run()
