#! -*- coding: utf-8 -*-

import os
import re
import json
import time
import logging
import requests
import argparse
import subprocess

from config import table_header, table_body, GiteeAddr, check_name_map, OBSName, CodeartsAPI, CodeArtsDomain, \
    HWLoginAPI, CodeBuildAddr, MajunURL
from tools.utils import retry_decorator

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)s: %(message)s")

URL_Pattern = re.compile(r"https://[-A-Za-z0-9+&@#/%?=~_|!:,.;]+[-A-Za-z0-9+&@#/%=~_|]")

NA = "N/A"
Status_Dict = {
    "COMPLETED": dict(code="9989", detail="SUCCESS"),
    "RUNNING": dict(code="128346", detail="RUNNING"),
    "CANCELED": dict(code="10060", detail="任务终止，请检查"),
    "FAILED": dict(code="10060", detail="FAILED"),
}


class GiteeApp:

    def __init__(self,
                 token: str,
                 owner: str,
                 repo: str,
                 pr_id: str
                 ):
        """
        @token: gitee token
        @owner: 代码仓所属企业
        @repo: 代码仓名称
        @pr_id: 提交pr id
        """
        self.token = token
        self.owner = owner
        self.repo = repo
        self.pr_id = pr_id
        self.root_url = f'{GiteeAddr}/{self.owner}/{self.repo}'
        self.remark_url = f"{self.root_url}/pulls/{self.pr_id}/comments"

    @retry_decorator
    def get_labels(self, page: int = 1, per_page: int = 100):
        """
        获取repo pr_id 标签
        :param page:
        :param per_page:
        :return:
        """
        logging.info(f"get pr_id: {self.pr_id} labels...")
        prefix = f'{self.root_url}/pulls/{self.pr_id}/labels'
        url = f'{prefix}?access_token={self.token}&page={page}&per_page={per_page}'

        resp = requests.get(url)
        if resp.status_code not in [200, 201, 204]:
            raise ConnectionError("get labels fail...")
        return resp.json()

    @retry_decorator
    def del_labels(self, label: str):
        """
        删除某个标签
        :param label:
        :return:
        """
        prefix = f'{self.root_url}/pulls/{self.pr_id}/labels'
        resp = requests.delete(url=f'{prefix}/{label}?access_token={self.token}')
        if resp.status_code not in [200, 201, 204]:
            raise ConnectionError("get labels fail...")

    @retry_decorator
    def add_comment(self, msg: str):
        """
        增加评论
        :param msg: 评论内容
        """
        logging.info(f"comment url: {self.remark_url}")
        response = requests.post(self.remark_url,
                                 data=dict(access_token=self.token, body=msg))
        if response.status_code not in [200, 201, 204]:
            raise ConnectionError("comment fail...")

        logging.info(f'comment success')

    @retry_decorator
    def get_comments(self, page: int = 1, per_page: int = 100, desc: bool = True):
        """
        获取评论
        :param page:
        :param per_page:
        :param desc: 是否倒序
        :return:
        """
        desc = "desc" if desc else ""
        params = dict(access_token=self.token, page=page, per_page=per_page, direction=desc)
        resp = requests.get(self.remark_url, params=params)

        if resp.status_code == 200:
            return resp.json()
        raise ConnectionError("request comments failure..")

    @retry_decorator
    def del_comment(self, comment_id: str):
        """
        删除评论
        :param comment_id:
        :return:
        """
        del_url = f'{self.remark_url}/{comment_id}?access_token={args.access_token}'
        resp = requests.delete(url=del_url)
        if resp.status_code != 200:
            logging.error(f'delete comment failure, comment id: {comment_id}')
            raise ConnectionError("del comment fail...")


class ChecklistApp:

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
                 obs_dict: str,
                 ak: str,
                 sk: str,
                 remove_detail: str
                 ):
        """
        @token: github token
        @owner: 代码仓所属企业
        @repo: 代码仓名称
        @pr_id: 待合入pr id
        @project_id: codearts 项目id
        @pipeline_id: codearts 流水线id
        @pipeline_run_id: codearts 流水线任务id
        @username: codearts 主账号
        @subUsername: codearts 从账号
        @password: codearts 登陆密码
        @obs_dict: codearts obs地址
        @ak: codearts ak
        @sk: codearts sk
        @remove_detail: 是否删除详情列
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
        self.obs_dic = obs_dict
        self.ak = ak
        self.sk = sk
        self.remove_detail = remove_detail
        self.last_project_id = ""
        self.last_pipeline_id = ""
        self.last_pipeline_run_id = ""
        self.commit_id = ""
        self.last_pl_api_pref = ""
        self.self_url = f'{CodeArtsDomain}/cicd/project/{project_id}/pipeline/detail/{pipeline_id}/{pipeline_run_id}'
        self.gitee_app = GiteeApp(token, owner, repo, pr_id)

    def get_daily_build_number(self, headers, step_run_id):
        url = f"{self.last_pl_api_pref}/{self.last_pipeline_run_id}/steps/outputs"
        response = requests.get(url,
                                params={"step_run_ids": step_run_id},
                                headers=headers)

        if response.status_code == 200:
            for entry in response.json()['step_outputs'][0]['output_result']:
                if entry['key'] == 'dailyBuildNumber':
                    number = entry['value']
                    logging.info(f"daily_build_number: {number}")
                    return number
        else:
            logging.error(f'请求失败,状态码: {response.status_code},相应阶段: get_daily_build_number')

    @staticmethod
    def get_build_number(headers, job_id, daily_build_number):
        url = f'{CodeBuildAddr}/v3/jobs/{job_id}/history'
        k = 200
        for i in range(0, 3):
            response = requests.get(url,
                                    params=dict(limit=100, interval=5, offset=i),
                                    headers=headers)

            if response.status_code == 200:
                for entry in response.json()['history_records']:
                    if entry['record_id'] == daily_build_number:
                        logging.info(f"build_number: {entry['build_number']}")
                        return entry['build_number']

            k = response.status_code
        logging.error(f'请求失败,状态码: {k},相应阶段: get_build_number')

    @staticmethod
    def get_build_record_id(headers, job_id, build_number):
        url = f'{CodeBuildAddr}/v4/jobs/{job_id}/{build_number}/record-info'
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            build_record_id = response.json()['result']['build_record_id']
            logging.info(f"build_record_id: {build_record_id}")
            return build_record_id
        logging.error(f'请求失败,状态码: {response.status_code},相应阶段: get_build_record_id')

    def get_codearts_token(self) -> dict:
        """
        获取codearts token
        :return:
        """
        logging.info("获取codearts token...")
        user = dict(password=self.password, domain=dict(name=self.username), name=self.subUsername)
        header = {
            "auth": {
                "identity": {"password": {"user": user}, "methods": ["password"]},
                "scope": {"project": {"name": "cn-north-4"}}
            }
        }
        resp = requests.post(url=HWLoginAPI, data=json.dumps(header))
        token = resp.headers["X-Subject-Token"]
        return {"x-auth-token": token}

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

    def download_failed_log(self, headers, job_id, job_name, step_run_id):
        """
        下载失败的日志至本地
        :param headers: codearts 请求头
        :param job_id: 任务id
        :param job_name: 任务名称
        :param step_run_id:
        :return:
        """
        daily_build_num = self.get_daily_build_number(headers, step_run_id)
        build_num = self.get_build_number(headers, job_id, daily_build_num)
        record_id = self.get_build_record_id(headers, job_id, build_num)

        url = f'{CodeBuildAddr}/v4/{record_id}/download-log'
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            dir_path = f'/usr1/log/{self.repo}/{self.pr_id}/'
            os.makedirs(dir_path, exist_ok=True)
            with open(dir_path + f'{self.pr_id}_{job_name}.txt', 'a+', encoding='UTF-8') as f:
                f.write(response.text)
        else:
            logging.error(f'请求失败,状态码: {response.status_code},相应阶段: download_log')

    def upload_failed_log(self):
        subprocess.call(
            f"""
            cd /usr1/log
            rm -rf {self.repo}/{self.pr_id}/codecheck*
            obsutil config -i={self.ak} -k={self.sk} -e=obs.cn-north-4.myhuaweicloud.com
            obsutil cp {self.repo} obs://{OBSName}/PR/ -r -f""",
            shell=True
        )

    def find_majun_url(self, name: str) -> str:
        """
        从日志中匹配majun的任务链接
        :param name: 任务名称
        :return:
        """
        with open(f'/usr1/log/{self.repo}/{self.pr_id}/{self.pr_id}_{name}.txt', 'r', encoding='UTF-8') as f:
            for line in f.readlines():
                if MajunURL in line and f'{MajunURL}/api' not in line:
                    urls = re.findall(URL_Pattern, line)
                    if urls:
                        return urls[0]
        return ''

    @staticmethod
    def generate_table(items: list, remove_detail: str):
        """
        将检查项结果转换成html table
        """
        packages = [x.get("package") for x in items]
        has_pkg = bool([x for x in packages if x not in [NA, "", None]])

        remove_flag = True if remove_detail.lower() == "true" else False

        header, body = table_header, table_body
        if not has_pkg:
            header = table_header.replace("<th>出包</th>\n", "")
            body = table_body.replace("<td>{4}</td>\n", "")

        if remove_flag:
            header = header.replace("<th>日志</th>\n", "")
            body = body.replace("<td>{3}</td>\n", "")

        html = header
        for item in items:
            check_name, status = item.get("check_name"), item.get("status")
            detail, log, package = item.get("detail"), item.get("log"), item.get("package")
            if has_pkg and not remove_flag:
                html += body.format(check_name, status, detail, log, package)
            elif has_pkg and remove_flag:
                html += body.format(check_name, status, log, package)
            elif not has_pkg and not remove_flag:
                html += body.format(check_name, status, detail, log)
            else:
                html += body.format(check_name, status, log)

        html = html + "</table>"
        return html

    def update_stage_comment(self, comment_table: str):
        """更新评论"""
        comment_data = self.gitee_app.get_comments()
        if not comment_data:
            return
        for comments in comment_data:
            comment, cid = comments["body"], comments["id"]
            if '状态' in comment:
                self.gitee_app.del_comment(cid)
                break
        self.gitee_app.add_comment(comment_table)

    def get_plug_in_state(self, headers, step_run_id):
        """
        :param headers: codearts 请求头
        :param step_run_id:
        :return:
        """
        url = f'{self.last_pl_api_pref}/{self.last_pipeline_run_id}/steps/outputs'
        response = requests.get(url,
                                params=dict(step_run_ids=step_run_id),
                                headers=headers)

        res = {
            "check_name": "dist_test_or_not",
            "status": "9989",
            "detail": "执行分布式用例",
            "log": NA,
            "package": NA
        }

        if response.status_code == 200:
            data = response.json()['step_outputs'][0]['output_result']
            for entry in data:
                if entry['key'] == 'execute':
                    execute_flag = entry['value']
                    logging.info(f"execute_flag: {execute_flag}")
                    if execute_flag != 'yes':
                        res["detail"] = "未执行分布式用例"
        else:
            logging.error(f'请求失败,状态码: {response.status_code},相应阶段: get_plug_in_state')
        return res

    def get_package_link(self, name: str):
        """
        获取包链接
        :param name: 任务名称
        :return:
        """
        prefix = f"https://{self.obs_dic}/{self.pr_id}"
        if 'build_x86' in name.lower():
            return f'<a href="{prefix}/torch_npu_x86_64.tar.gz">>>></a>'
        elif 'build_arm' in name.lower():
            return f'<a href="{prefix}/torch_npu_aarch64.tar.gzz">>>></a>'
        elif 'build_libtorch' in name.lower():
            return f'<a href="{prefix}/libtorch_npu_x86_64.tar.gz">>>></a>'

    def get_function_pipeline(self):
        """
        获取流水先一的信息
        :return:
        """
        logging.info("获取流水线一相关信息...")
        data = self.gitee_app.get_comments()

        if not data:
            return

        for j in data:
            comment, comment_id = j['body'], j['id']
            if "流水线任务触发成功，正在执行，请稍候" in comment:
                ids = comment.split("(")[-1].split(")")[0].split("/")
                project_id, pipeline_id, pipeline_run_id = ids[-5], ids[-2], ids[-1]
                logging.info(f'获取完毕, comment id: {comment_id}')
                return project_id, pipeline_id, pipeline_run_id, comment_id

    def del_history_remark(self):
        """
        删除历史评论
        :return:
        """
        data = self.gitee_app.get_comments(desc=True)
        if not data:
            return

        is_recent = True
        for j in data:
            comment, cid = j['body'], j['id']
            if "流水线任务已触发" in comment:
                self.gitee_app.del_comment(cid)
            if "流水线任务触发成功" in comment:
                if not is_recent:
                    self.gitee_app.del_comment(cid)
                is_recent = False

    def run(self):
        # 1. 获取codearts接口访问token
        headers = self.get_codearts_token()

        # 2. 删除历史评论
        self.del_history_remark()

        # 3. 添加本流水线初始化评论
        comment = f'checklist流水线任务已触发，正在执行，请稍候。<a href="{self.self_url}">任务链接[{self.pipeline_run_id}]</a>'
        self.gitee_app.add_comment(comment)

        # 4. 删除pushed标签
        labels_info = self.gitee_app.get_labels()
        for info in labels_info:
            if "pushed" in info["name"]:
                self.gitee_app.del_labels("pushed")

        # 5. 获取流水线一的信息
        pl = self.get_function_pipeline()
        if pl:
            self.last_project_id, self.last_pipeline_id, self.last_pipeline_run_id, self.commit_id = pl

        # 6. 解析流水线1结果
        job_name_map = self.convert_check_name_map()
        self.last_pl_api_pref = f"{CodeartsAPI}/{self.last_project_id}/api/pipelines/{self.last_pipeline_id}/pipeline-runs"
        while True:
            check_res = []
            pipeline_detail = f'{self.last_pl_api_pref}/detail?pipeline_run_id={self.last_pipeline_run_id}'
            resp = requests.get(pipeline_detail, headers=headers)
            resp_text = json.loads(resp.text)
            logging.info(f"流水线一运行状态为: {resp_text['status']}")

            for stage in resp_text["stages"]:
                for job in stage["jobs"]:
                    name, status = job["name"], job["status"]
                    log_link, pack_link = NA, NA
                    standard_name = job_name_map.get(name, name)
                    obs_log_url = f"https://{self.obs_dic}/{self.repo}/{self.pr_id}/{self.pr_id}_{name}.txt"
                    step_run_id = job["steps"][0]["id"]

                    if name in "monitor_trigger":
                        continue

                    if status in ["FAILED", "COMPLETED"]:
                        if name != "dist_test_or_not":
                            for entry in job["steps"][0]["inputs"]:
                                if entry["key"] == "jobId":
                                    job_id = entry['value']
                                    self.download_failed_log(headers=headers,
                                                             job_id=job_id,
                                                             job_name=name,
                                                             step_run_id=step_run_id
                                                             )
                                    self.upload_failed_log()
                        if standard_name in ["sca", "anti_poison", "code_check"]:
                            obs_log_url = self.find_majun_url(name)

                    logging.info(f"job name: {standard_name}, obs_log_url: {obs_log_url}, status: {status}")

                    log_link = f'<a href="{obs_log_url}">>>></a>'

                    if self.repo == "pytorch" and status == "COMPLETED":
                        if 'dist_test_or_not' in name.lower():
                            tmp_dict = self.get_plug_in_state(headers, step_run_id)
                            check_res.append(tmp_dict)
                        if 'build' in standard_name:
                            pack_link = self.get_package_link(name)

                    info = Status_Dict.get(status)
                    if info and name != "dist_test_or_not":
                        check_res.append(dict(check_name=standard_name.lower(),
                                              status=info.get("code"),
                                              detail=info.get("detail"),
                                              log=log_link,
                                              package=pack_link))

            comment_table = self.generate_table(check_res, self.remove_detail)
            self.update_stage_comment(comment_table)

            if resp_text["status"] != "RUNNING":
                break

            time.sleep(60)


def init_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--access_token', help='gitee access token', required=True, type=str)
    parser.add_argument('--owner', help='owner', required=True, type=str)
    parser.add_argument('--pr_id', help='pr id', required=True, type=str)
    parser.add_argument('--repo', help='code repo', required=True, type=str)
    parser.add_argument('--username', help='codearts username', required=True, type=str)
    parser.add_argument('--subUsername', help='codearts subUsername', required=True, type=str)
    parser.add_argument('--password', help='codearts password', required=True, type=str)
    parser.add_argument('--obs_dic', help='obs_dic', required=True, type=str)
    parser.add_argument('--ak', help='ak', required=True, type=str)
    parser.add_argument('--sk', help='sk', required=True, type=str)
    parser.add_argument('--project_id', help='current pipeline project id', type=str, default=None, required=False)
    parser.add_argument('--pipeline_id', help='current pipeline id', type=str, default=None, required=False)
    parser.add_argument('--pipeline_run_id', help='current pipeline run id', type=str, default=None, required=False)
    parser.add_argument('--remove_detail', help='remove detail column', type=str, default="true", required=False)
    return parser.parse_args()


if __name__ == '__main__':
    args = init_args()

    checklist_remark = ChecklistApp(token=args.access_token,
                                    owner=args.owner,
                                    repo=args.repo,
                                    pr_id=args.pr_id,
                                    project_id=args.project_id,
                                    pipeline_id=args.pipeline_id,
                                    pipeline_run_id=args.pipeline_run_id,
                                    username=args.username,
                                    subUsername=args.subUsername,
                                    password=args.password,
                                    obs_dict=args.obs_dict,
                                    ak=args.ak,
                                    sk=args.sk,
                                    remove_detail=args.remove_detail
                                    )

    checklist_remark.run()
