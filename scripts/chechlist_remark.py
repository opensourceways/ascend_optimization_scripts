#! -*- coding: utf-8 -*-

import logging
import os
import json
import sys
import time
import requests
import argparse
import subprocess

from config import table_header, table_body, GiteeAddr, CodeArtsAddr, CodeBuildAddr, PipelineAddr, HWIAMAddr, \
    check_name_map, NA, OBSName

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)s: %(message)s")

ut_failed_flag = False
log_link = pack_link = NA

status_dict = {
    'COMPLETED': ['9989', 'SUCCESS', log_link, pack_link],
    'RUNNING': ['128346', 'RUNNING', NA, NA],
    'CANCELED': ['10060', '任务终止，请检查', NA, NA],
    'FAILED': ['10060', 'FAILED', log_link, NA]
}


def get_pipeline_id(args):
    """
    获取流水线信息
    """
    logging.info('获取流水线相关信息...')
    wait_comment = "流水线任务触发成功，正在执行，请稍候"
    url = f'{GiteeAddr}/{args.owner}/{args.repo}/pulls/{args.pr_id}/comments'

    params = dict(access_token=args.access_token, page=1, per_page=100, direction="desc")
    response = requests.get(url, params)

    if response.status_code == 200:
        for j in response.json():
            comment, comment_id = j['body'], j['id']
            if wait_comment in comment:
                ids = str(comment).split("(")[-1].split(")")[0].split("/")
                project_id, pipeline_id, pipeline_run_id = ids[-5], ids[-2], ids[-1]
                logging.info(f'获取完毕, comment id: {comment_id}')
                return project_id, pipeline_id, pipeline_run_id, comment_id


def get_token(args):
    logging.info("获取token中....")
    headers_get_token = {
        "auth": {
            "identity": {
                "password": {
                    "user": {
                        "password": f"{args.password}",
                        "domain": {"name": f"{args.username}"},
                        "name": f"{args.subUsername}"
                    }},
                "methods": ["password"]
            },
            "scope": {
                "project": {"name": "cn-north-4"}
            }
        }
    }
    req_get_token = requests.post(url=HWIAMAddr, data=json.dumps(headers_get_token))
    token = req_get_token.headers["X-Subject-Token"]
    logging.info("token获取完毕")
    time.sleep(1)
    return token


def add_comment(args, comment_info):
    url = f'{GiteeAddr}/{args.owner}/{args.repo}/pulls/{args.pr_id}/comments'
    post_data = dict(access_token=args.access_token, body=comment_info)
    logging.info(f"pr_url: https://gitee.com/ascend/{args.repo}/pulls/{args.pr_id}")
    response = requests.post(url, data=post_data)
    if response.status_code in [200, 201, 204]:
        logging.info(f'comment success')
    else:
        logging.error(f'comment failed')


def create_header(args):
    token = get_token(args)
    return {"x-auth-token": token}


def convert_check_name_map():
    """
    将检查项映射表key, value翻转过来
    """
    res = {}
    for k, v in check_name_map.items():
        for i in v:
            res[i] = k
    return res


def generate_table(items, remove_detail):
    """
    将检查项结果转换成html table
    """
    packages = [x.get("package") for x in items]
    has_pkg = bool([x for x in packages if x not in [NA, "", None]])

    remove_flag = True if remove_detail == "true" else False

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


def get_status(headers, pipeline_obj, args):
    global ut_failed_flag, pack_link, log_link
    json_skip_flag = json_compare(args.file)
    logging.info('判断结果: ' + str(json_skip_flag))
    # third_url = f'{HWCloudAddr}&service={CodeArtsAddr}/cicd/project/{pipeline_obj[0]}/pipeline/detail/{pipeline_obj[1]}/{pipeline_obj[2]}'

    flag, ut_out_flag, job_dict = False, False, {'dist_test_or_not': log_link}
    job_name_map = convert_check_name_map()
    while True:
        result = []
        url_get_status = f'{PipelineAddr}/v5/{pipeline_obj[0]}/api/pipelines/{pipeline_obj[1]}/pipeline-runs/detail?pipeline_run_id={pipeline_obj[2]}'
        status_list = requests.get(url=url_get_status, headers=headers)
        status_test = json.loads(status_list.text)
        if status_test['status'] != 'RUNNING':
            logging.info('流水线运行结束，运行结果为:' + status_test['status'])
        else:
            logging.info('流水线运行中...请稍后查看')
        for i in status_test['stages']:
            for j in i['jobs']:
                job_name, status = j['name'], j['status']
                standard_job_name = job_name_map.get(job_name, job_name)
                obs_log_url = f"https://{args.obs_dic}/{args.repo}/{args.pr_id}/{args.pr_id}_{job_name}.txt"

                if job_name in 'monitor_trigger':
                    continue

                logging.info(f"job name: {standard_job_name}, obs_log_url: {obs_log_url}, status: {status}")

                step_run_id = j['steps'][0]['id']
                if status in ["FAILED", "COMPLETED"]:
                    if job_name not in job_dict.keys():
                        for entry in j['steps'][0]['inputs']:
                            if entry['key'] == 'jobId':
                                job_id = entry['value']
                                download_failed_log(pipeline_obj, step_run_id, args.repo, job_name, job_id, args.pr_id)
                                upload_failed_log()
                    if standard_job_name in ["sca", "anti_poison", "code_check"]:
                        obs_log_url = check_majun(args.repo, job_name, args.pr_id)

                log_link = '<a href="{}">>>></a>'.format(obs_log_url)
                pack_link = 'N/A'

                if status == 'FAILED':
                    flag = True
                    status_dict['FAILED'][2] = log_link
                    if 'ut' in job_name.lower():
                        ut_out_flag = True
                if args.repo == 'pytorch':
                    # build_package
                    if status == 'COMPLETED':
                        if 'dist_test_or_not' in job_name.lower():
                            tmp_dict = get_plug_in_state(pipeline_obj, step_run_id)
                            result.append(tmp_dict)
                        if 'build' in standard_job_name:
                            pack_link = get_package_link(job_name, args.pr_id, args.obs_dic)
                status_dict['COMPLETED'][2] = log_link
                status_dict['COMPLETED'][3] = pack_link

                if (str(status) in status_dict.keys()) and job_name != 'dist_test_or_not':
                    logging.info('进入status')
                    _status = status_dict[status]
                    result.append(dict(check_name=standard_job_name,
                                       status=_status[0],
                                       detail=_status[1],
                                       log=_status[2],
                                       package=_status[3]))

        # 输出测试用例标签
        # tmp_dict = ut_comment(json_skip_flag, ut_failed_flag, ut_out_flag)
        # result.extend(tmp_dict)

        # result.append(dict(check_name="流水线链接",
        #                    status=160,
        #                    detail="",
        #                    log='<a href="{}">点此跳转</a>'.format(third_url),
        #                    package=""))

        comment_table = generate_table(result, args.remove_detail)
        update_stage_comment(args, comment_table)
        logging.info(f"流水线状态: {status_test['status']}")
        if status_test['status'] != 'RUNNING':
            if ut_out_flag:
                add_comment(args, 'ut failed')
            if flag:
                sys.exit(1)
            break
        time.sleep(60)
    return status_test['status']


def get_plug_in_state(pipeline_obj, step_run_id):
    url = f'{PipelineAddr}/v5/{pipeline_obj[0]}/api/pipelines/{pipeline_obj[1]}/pipeline-runs/{pipeline_obj[2]}/steps/outputs'
    params = dict(step_run_ids=step_run_id)
    response = requests.get(url, params=params, headers=headers)

    res = {"check_name": "dist_test_or_not", "status": "9989", "detail": "执行分布式用例", "log": NA, "package": NA}
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


def get_package_link(job_name, pr_id, obs_dic):
    prefix = f"https://{obs_dic}/{pr_id}"
    if 'build_x86' in job_name.lower():
        return f'<a href="{prefix}/torch_npu_x86_64.tar.gz">>>></a>'
    elif 'build_arm' in job_name.lower():
        return f'<a href="{prefix}/torch_npu_aarch64.tar.gzz">>>></a>'
    elif 'build_libtorch' in job_name.lower():
        return f'<a href="{prefix}/libtorch_npu_x86_64.tar.gz">>>></a>'


def check_majun(repo, job_name, pr_id):
    obs_log_url = ''
    with open(f'/usr1/log/{repo}/{pr_id}/{pr_id}_{job_name}.txt', 'r', encoding='UTF-8') as codecheck_file:
        for line in codecheck_file.readlines():
            if 'majun_url' in line:
                obs_log_url = line.split(
                    'majun_url:')[-1].split('\n')[0]
    return obs_log_url


def download_failed_log(pipeline_obj, step_run_id, repo, job_name, job_id, pr_id):
    daily_build_number = get_daily_build_number(
        pipeline_obj, step_run_id)
    build_number = get_build_number(job_id, daily_build_number)
    record_id = get_build_record_id(job_id, build_number)
    download_log(record_id, job_name, repo, pr_id)


def ut_comment(json_skip_flag, ut_failed_flag, ut_out_flag):
    result = [
        dict(check_name="跳过测试用例", status=160, detail="否", log="", package=""),
        dict(check_name="UT失败过", status=160, detail="否", log="", package="")
    ]
    if json_skip_flag:
        result[0]["detail"] = "是"
    if ut_out_flag or ut_failed_flag:
        result[1]["detail"] = "是"

    return result


def update_stage_comment(args, comment_table):
    """更新评论"""
    url = f'{GiteeAddr}/{args.owner}/{args.repo}/pulls/{args.pr_id}/comments'
    params = dict(access_token=args.access_token, page=1, per_page=100, direction="desc")
    response = requests.get(url, params=params, headers=headers)

    if response.status_code == 200:
        for comments in response.json():
            comment, cid = comments['body'], comments['id']
            if str('状态') in comment:
                logging.info(f"comment_id: {cid}")
                del_comment(args, cid)
                break
        add_comment(args, comment_table)
    else:
        logging.error(f'请求失败,状态码: {response.status_code},相应阶段: update_stage_comment')


def del_comment(args, comment_id):
    del_url = f'{GiteeAddr}/{args.owner}/{args.repo}/pulls/comments/{comment_id}?access_token={args.access_token}'
    req_del_comment = requests.delete(url=del_url)
    logging.info('删除评论' + str(req_del_comment))


def json_compare(file):
    if file is None:
        logging.info('文件不存在!')
        return False
    logging.info('判断UT用例是否修改!')
    file_name = 'test/unsupported_test_cases/.pytorch-disabled-tests.json'
    # file_name = 'test_operators.py'
    with open(f'{file}', 'r') as f:
        if any(file_name in line for line in f):
            return True
    return False


def get_daily_build_number(pipeline_obj, step_run_ids):
    url = f'{PipelineAddr}/v5/{pipeline_obj[0]}/api/pipelines/{pipeline_obj[1]}/pipeline-runs/{pipeline_obj[2]}/steps/outputs'
    params = dict(step_run_ids=step_run_ids)
    response = requests.get(url, params=params, headers=headers)

    if response.status_code == 200:
        data = response.json()['step_outputs'][0]['output_result']
        for entry in data:
            if entry['key'] == 'dailyBuildNumber':
                daily_build_number = entry['value']
                logging.info(f"daily_build_number: {daily_build_number}")
                return daily_build_number
    else:
        logging.error(f'请求失败,状态码: {response.status_code},相应阶段: get_daily_build_number')


def get_build_number(job_id, daily_build_number):
    url = f'{CodeBuildAddr}/v3/jobs/{job_id}/history'
    k = 200
    params = dict(limit=100, interval=5)
    for i in range(0, 3):
        params["offset"] = i
        response = requests.get(url, params=params, headers=headers)
        if response.status_code == 200:
            data = response.json()['history_records']
            for entry in data:
                if entry['record_id'] == daily_build_number:
                    build_number = entry['build_number']
                    logging.info(f"build_number: {build_number}")
                    return build_number
        k = response.status_code
    logging.error(f'请求失败,状态码: {k},相应阶段: get_build_number')


def get_build_record_id(job_id, build_number):
    url = f'{CodeBuildAddr}/v4/jobs/{job_id}/{build_number}/record-info'
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        build_record_id = response.json()['result']['build_record_id']
        logging.info(f"build_record_id: {build_record_id}")
        return build_record_id
    logging.error(f'请求失败,状态码: {response.status_code},相应阶段: get_build_record_id')


def download_log(record_id, job_name, repo, pr_id):
    url = f'{CodeBuildAddr}/v4/{record_id}/download-log'
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        dir_path = f'/usr1/log/{repo}/{pr_id}/'
        os.makedirs(dir_path, exist_ok=True)
        with open(dir_path + f'{pr_id}_{job_name}.txt', 'a+', encoding='UTF-8') as f:
            f.write(response.text)
    else:
        logging.error(f'请求失败,状态码: {response.status_code},相应阶段: download_log')


def upload_failed_log():
    subprocess.call(f"""
    cd /usr1/log
    rm -rf {args.repo}/{args.pr_id}/codecheck*
    obsutil config -i={args.ak} -k={args.sk} -e=obs.cn-north-4.myhuaweicloud.com
    obsutil cp {args.repo} obs://{OBSName}/PR/ -r -f
    """, shell=True)


def del_pushed_labels(args):
    logging.info('判断是否存在pushed标签...')
    prefix = f'{GiteeAddr}{args.owner}/{args.repo}/pulls/{args.pr_id}/labels'
    url = f'{prefix}?access_token={args.access_token}&page=1&per_page=100'
    response = requests.get(url).json()
    for j in response:
        if str('pushed') in j['name']:
            # add_comment(repo, pr_id, '删除pushed标签', access_token)
            del_url = f'{prefix}/pushed?access_token={args.access_token}'
            req_del_comment = requests.delete(url=del_url)
            logging.info('删除pushed标签！')


def remark_start_comment(params):
    """
    pipeline start remark
    @params: params  程序入参
    """
    project_id, pipeline_id, pipeline_run_id = args.project_id, args.pipeline_id, args.pipeline_run_id

    if project_id and pipeline_id and pipeline_run_id:
        url = f'{CodeArtsAddr}/cicd/project/{project_id}/pipeline/detail/{pipeline_id}/{pipeline_run_id}'
        comment = f'checklist流水线任务已触发，正在执行，请稍候。<a href="{url}">任务链接[{pipeline_run_id}]</a>'
        add_comment(params, comment)


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
    parser.add_argument('--file', help='codearts', type=str)
    parser.add_argument('--project_id', help='current pipeline project id', type=str, default=None, required=False)
    parser.add_argument('--pipeline_id', help='current pipeline id', type=str, default=None, required=False)
    parser.add_argument('--pipeline_run_id', help='current pipeline run id', type=str, default=None, required=False)
    parser.add_argument('--remove_detail', help='remove detail column', type=str, default="true", required=False)
    return parser.parse_args()


if __name__ == '__main__':
    args = init_args()
    headers = create_header(args)
    time.sleep(30)
    del_pushed_labels(args)
    pipeline_obj = get_pipeline_id(args)
    remark_start_comment(args)
    completed = get_status(headers, pipeline_obj, args)
    if completed != 'COMPLETED':
        sys.exit(1)
