#! -*- coding: utf-8 -*-

import os
import time
import logging
import requests
import argparse
import subprocess
from datetime import datetime

from smtplib import SMTP_SSL
from email.mime.text import MIMEText

from tools.utils import retry_decorator
from conf.email_conf import Config

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)s: %(message)s")


class App:

    def __init__(self,
                 enterprise: str,
                 token: str,
                 user: str,
                 smtp_host: str,
                 smtp_port: str,
                 smtp_username: str,
                 smtp_password: str,
                 smtp_sender: str,
                 smtp_receiver: str
                 ):
        """
        :param enterprise:  组织
        :param token:  gitee token
        :param user: gitee账户
        :param smtp_host:
        :param smtp_port:
        :param smtp_username:
        :param smtp_password:
        :param smtp_sender:
        :param smtp_receiver: 以;分隔
        """
        self.token = token
        self.enterprise = enterprise
        self.user = user
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_username = smtp_username
        self.smtp_password = smtp_password
        self.smtp_sender = smtp_sender
        self.smtp_receiver = smtp_receiver

        self.base_url = "https://gitee.com/api/v5"

    def download_code(self, repo: str):
        """
        下载代码仓
        :param repo: repo名字
        :return:
        """
        logging.info(f"git clone {repo} to local...")
        url = f"https://{self.user}:{self.token}@gitee.com/{self.enterprise}/{repo}.git"
        cmd = [f"./tools/collect_git_repo.sh", repo, url]
        subprocess.call(cmd)

    @staticmethod
    def find_distinct_files(repo: str):
        """
        找到repo目录下目标文件，并拷贝至目标目录
        :param repo:
        :return:
        """
        logging.info(f"parse repo {repo} OWNERS file...")
        repo_path = f'./repos/{repo}'
        paths = os.walk(repo_path)
        for path, _, file_lst in paths:
            for filename in file_lst:
                if filename == Config.TargetFileName:
                    _path = path.replace("./repos/", "")
                    distinct = f"./{Config.ExcludeRepo}/{_path}"
                    os.makedirs(distinct, exist_ok=True)
                    cmd = [f"cp", os.path.join(path, filename), distinct]
                    logging.info(cmd)
                    subprocess.call(cmd)

    @staticmethod
    def commit_code():
        """
        提交更改
        :return:
        """
        logging.info(f"commit code {Config.ExcludeRepo}...")
        cmd = ["./tools/commit_code.sh", Config.ExcludeRepo]
        subprocess.call(cmd)

    def parse_repo_owners(self, repo: str):
        """
        解析代码仓的owners文件
        :param repo: 代码仓名称
        :return:
        """
        self.download_code(repo)
        self.find_distinct_files(repo)

    def get_repos(self) -> list:
        """
        获取self.enterprise组织下所有代码仓
        :return:
        """
        url = f"{self.base_url}/orgs/{self.enterprise}/repos"
        page = 0
        repos = []
        params = dict(access_token=self.token, per_page=50, page=page)
        while True:
            logging.info(f"get page {page} repo names...")
            response = requests.get(url, params=params)
            logging.info(f"get page {page} repo names, status code: {response.status_code}")
            _repos = response.json()
            repos.extend([x.get("full_name").split("/")[-1] for x in _repos])
            total_page = response.headers.get("total_page")
            if page >= int(total_page):
                break
            page += 1
            params["page"] = page
        return list(set(repos))

    def write_repos_down(self, repos: list):
        """
        将代码仓保存至本地
        :param repos:
        :return:
        """
        logging.info(f"write {self.enterprise} repos down...")
        repos = [x + '\n' for x in repos]
        with open(f'./{self.enterprise}.txt', 'w+') as f:
            f.writelines(repos)

    @retry_decorator
    def send_email(self, repos: list):
        """
        新增代码仓时。需要通知社区CIE
        :param repos:
        :return:
        """
        logging.info("send email...")
        with open("./conf/email_attention.txt", 'r') as f:
            content = f.read()

        body = ""
        for repo in repos:
            body += f"<p>https://gitee.com/{self.enterprise}/{repo}</p>"

        email_body = content.replace("{{repos}}", body)

        msg = MIMEText(email_body, "html", _charset="utf-8")
        msg["Subject"] = Config.EMAIL_SUBJECT
        msg["from"] = self.smtp_sender
        msg["to"] = self.smtp_receiver

        with SMTP_SSL(host=self.smtp_host, port=self.smtp_port) as smtp:
            smtp.login(user=self.smtp_username, password=self.smtp_password)

            smtp.sendmail(from_addr=self.smtp_username,
                          to_addrs=self.smtp_receiver.split(";"),
                          msg=msg.as_string()
                          )

    def has_new_repo(self, repos: list):
        """
        检测是否有新repo
        :return:
        """
        path = f"./{self.enterprise}.txt"
        if not os.path.exists(path):
            return

        # 读取已有repos
        with open(path, 'r+') as f:
            lines = f.readlines()
            already_repos = [x.strip("\n") for x in lines]

            new_repos = list(set(repos) - set(already_repos))

        if not new_repos:
            return

        # 将新增的repo写入到log文件中去
        new_repos = [x + '\n' for x in new_repos]
        today = datetime.today().strftime("%Y-%m-%d")
        os.makedirs("./log", exist_ok=True)

        with open(f"./log/{today}.log", 'w+') as f:
            f.writelines(new_repos)

        # 发邮件通知
        self.send_email(new_repos)

    def run(self):
        while True:
            repos = self.get_repos()
            self.has_new_repo(repos)
            self.write_repos_down(repos)
            for repo in repos:
                if repo != Config.ExcludeRepo:
                    self.parse_repo_owners(repo)
            self.commit_code()
            logging.info(f"task done, sleep {Config.Trigger} hour for next task...")
            time.sleep(Config.Trigger * 60 * 60)


def init_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--smtp_host', help='SMTP_HOST', type=str)
    parser.add_argument('--smtp_port', help='SMTP_PORT', required=True, type=str)
    parser.add_argument('--smtp_username', help='SMTP_USERNAME', required=True, type=str)
    parser.add_argument('--smtp_password', help='SMTP_PASSWORD', required=True, type=str)
    parser.add_argument('--smtp_sender', help='SMTP_SENDER', required=True, type=str)
    parser.add_argument('--smtp_receiver', help='SMTP_RECEIVER, 以;隔开', required=True, type=str)
    parser.add_argument('--access_token', help='access token', required=True, type=str)
    parser.add_argument('--username', help='gitee username', required=True, type=str)
    return parser.parse_args()


if __name__ == '__main__':
    args = init_args()

    app = App(enterprise=Config.Enterprise,
              smtp_host=args.smtp_host,
              smtp_port=args.smtp_port,
              smtp_username=args.smtp_username,
              smtp_password=args.smtp_password,
              smtp_sender=args.smtp_sender,
              smtp_receiver=args.smtp_receiver,
              token=args.access_token,
              user=args.username,
              )

    app.run()
