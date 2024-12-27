#! -*- coding: utf-8 -*-

import argparse
import os
import subprocess
import requests
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)s: %(message)s")

OBSAddr = "obs.cn-north-4.myhuaweicloud.com"
OBSName = "opensourceways-ci"


class GiteeApp:

    def __init__(self,
                 token: str,
                 owner: str,
                 repo: str
                 ):
        """

        :param token:
        :param owner:
        :param repo:
        """
        self.token = token
        self.owner = owner
        self.repo = repo

    def creat_release(self,
                      tag_name: str,
                      name: str,
                      body: str,
                      prerelease: bool = False,
                      target_commitish: str = None
                      ):
        """
        :param tag_name: 标签名称, Eg: V1.0.0
        :param name: Release名称, Eg: Release Client For V1.0.0
        :param body: 描述文件
        :param prerelease: 是否为预览版本
        :param target_commitish: 分支名称或者commit SHA
        :return:
        """
        url = f"https://gitee.com/api/v5/repos/{self.owner}/{self.repo}/releases?access_token={self.token}"
        response = requests.post(url,
                                 json=dict(tag_name=tag_name,
                                           name=name,
                                           body=body,
                                           prerelease=prerelease,
                                           target_commitish=target_commitish
                                           )
                                 )

        logging.info(f"Create release: {response.text}")

        if response.status_code in [200, 201, 204]:
            data = response.json()
            return data.get("id")

        raise Exception("Create Release failure...")

    def upload_attach_file(self,
                           release_id: str,
                           file: str):
        """

        :param release_id: Release ID
        :param file: 文件路径
        :return:
        """
        url = f"https://gitee.com/api/v5/repos/{self.owner}/{self.repo}/releases/{release_id}/attach_files?access_token={self.token}"
        files = {"file": open(file, "rb")}
        response = requests.post(url,
                                 files=files
                                 )
        logging.info(f"Upload file to Release: {release_id}, result: {response.text}")

        if response.status_code in [200, 201, 204]:
            return response.status_code

        raise Exception(f"Upload File to Release: {release_id} failure...")


def download_file_from_obs(obs_path: str,
                           file_name: str,
                           ak: str,
                           sk: str,
                           obs_name: str,
                           obs_addr: str = OBSAddr
                           ) -> str:
    """
    从obs下载制品
    :param obs_path: 制品在obs上的路径
    :param file_name: 包名
    :param ak:
    :param sk:
    :param obs_name: obs桶名
    :param obs_addr: obs地址
    :return:
    """
    local_path = "/tmp/data"
    if not os.path.exists(local_path):
        os.makedirs(local_path)

    subprocess.call(
        f"""
        cd {local_path}
        obsutil config -i={ak} -k={sk} -e={obs_addr}
        obsutil cp obs://{obs_name}/{obs_path} {local_path}/{file_name} -r -f
        """,
        shell=True
    )
    return "{local_path}/{file_name}"


def init_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--token', help='gitee access token', required=True, type=str)
    parser.add_argument('--owner', help='owner', required=True, type=str)
    parser.add_argument('--repo', help='code repo', required=True, type=str)
    parser.add_argument('--ak', help='codearts ak', required=True, type=str)
    parser.add_argument('--sk', help='codearts sk', required=True, type=str)
    parser.add_argument('--tag_name', help='tag name, eg: v0.0.1', required=True, type=str)
    parser.add_argument('--name', help='release name, eg: Release For v0.0.1', required=True, type=str)
    parser.add_argument('--body', help='release desc', required=True, type=str)
    parser.add_argument('--commit_id', help='release bind commit id', required=True, type=str)
    parser.add_argument('--file_name', help='release attach file name', required=True, type=str)
    parser.add_argument('--commit_id', help='release bind commit id', required=True, type=str)
    parser.add_argument('--obs_path', help='file in obs path', required=True, type=str)
    return parser.parse_args()


if __name__ == '__main__':
    args = init_args()

    app = GiteeApp(token=args.token, owner=args.owner, repo=args.repo)

    # 1. 将制品从obs下载至本地
    file_path = download_file_from_obs(obs_path=args.obs_path,
                                       file_name=args.file_name,
                                       ak=args.ak,
                                       sk=args.sk,
                                       obs_name=OBSName,
                                       obs_addr=OBSAddr,
                                       )

    # 2. 创建release
    release_id = app.creat_release(
        tag_name=args.tag_name,
        name=args.name,
        body=args.body,
        target_commitish=args.commit_id
    )

    # 3. 上传相应分支的附件
    app.upload_attach_file(
        release_id=release_id,
        file=file_path
    )
