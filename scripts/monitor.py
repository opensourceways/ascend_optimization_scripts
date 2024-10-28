#! -*- coding: utf-8 -*-

import argparse
import functools
import json
import time

import requests
import logging

from config import GithubAddr, check_name_map, PipelineAPI, table_header, table_body, table_body_url, HWIAMAddr, \
    PipelineUrl, GiteeAddr

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)s: %(message)s")

status_map = dict(COMPLETED="9989", RUNNING="128346", CANCELED="10060", FAILED="10060")
Retry_times = 3


def retry_request(func):
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
        self.remark_url = f'{GithubAddr}/{owner}/{repo}/issues/{pr_id}/comments'
        self.gitee_remark_url = f'{GiteeAddr}/{owner}/{repo}/pulls/{pr_id}/comments'

    @retry_request
    def add_comment(self, msg: str, is_github: bool = True):
        """
        @msg: 评论内容
        @is_github: 是否是github仓
        """
        if is_github:
            logging.info(f"comment url: {self.remark_url}")
            response = requests.post(self.remark_url,
                                     json=dict(body=msg),
                                     headers=dict(Authorization=f"token {self.token}")
                                     )
        else:
            logging.info(f"comment url: {self.gitee_remark_url}")
            response = requests.post(self.gitee_remark_url,
                                     data=dict(access_token=self.token, body=msg)
                                     )

        if response.status_code in [200, 201, 204]:
            logging.info(f'comment success')
        else:
            logging.info(response.text)
            raise ConnectionError("comment fail...")


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
                 is_github: str
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
        @is_github: 是否为github仓
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
        self.git_app = GithubApp(token, owner, repo, pr_id)
        self.is_github = True if is_github.lower() == "true" else False

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
        html = table_header
        for item in items:
            check_name, status = item.get("check_name"), item.get("status")
            if check_name != "流水线链接":
                html += table_body.format(check_name, status)
            else:
                html += table_body_url.format(check_name, status)
        html = html + "</table>"
        return html

    def get_codearts_token(self):
        logging.info("获取codearts token...")
        user = dict(password=self.password, domain=dict(name=self.username), name=self.subUsername)
        header = {
            "auth": {
                "identity": {
                    "password": {"user": user},
                    "methods": ["password"]
                },
                "scope": {"project": {"name": "cn-north-4"}}
            }
        }
        resp = requests.post(url=HWIAMAddr, data=json.dumps(header))
        token = resp.headers["X-Subject-Token"]
        return {"x-auth-token": token}

    def run(self):
        # job_name_map = self.convert_check_name_map()
        result = []
        task_url = f'{PipelineAPI}/v5/{self.project_id}/api/pipelines/{self.pipeline_id}/pipeline-runs/detail?pipeline_run_id={self.pipeline_run_id}'
        resp = requests.get(url=task_url, headers=self.get_codearts_token())
        resp_txt = json.loads(resp.text)
        for stage in resp_txt["stages"]:
            for j in stage["jobs"]:
                job_name, status = j["name"], j["status"]
                if job_name == "统一评论":
                    break
                result.append(dict(check_name=job_name, status=status_map.get(status)))

        url_addr = f'{PipelineUrl}/{self.project_id}/pipeline/detail/{self.pipeline_id}/{self.pipeline_run_id}'
        result.append(dict(check_name="流水线链接", status=url_addr))
        html = self.generate_table(result)
        self.git_app.add_comment(html, self.is_github)


def init_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--access_token', help='gitub access token', required=True, type=str)
    parser.add_argument('--owner', help='owner', required=True, type=str)
    parser.add_argument('--pr_id', help='pr id', required=True, type=str)
    parser.add_argument('--repo', help='code repo', required=True, type=str)
    parser.add_argument('--project_id', help='current pipeline project id', type=str, default=None, required=False)
    parser.add_argument('--pipeline_id', help='current pipeline id', type=str, default=None, required=False)
    parser.add_argument('--pipeline_run_id', help='current pipeline run id', type=str, default=None, required=False)
    parser.add_argument('--username', help='codearts username', required=True, type=str)
    parser.add_argument('--subUsername', help='codearts subUsername', required=True, type=str)
    parser.add_argument('--password', help='codearts password', required=True, type=str)
    parser.add_argument('--is_github', help='is github repo', required=True, type=str)
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
                                       is_github=args.is_github,
                                       )

    checklist_remark.run()
