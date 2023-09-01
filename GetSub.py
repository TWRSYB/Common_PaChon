import re
import concurrent.futures
import threading
import time
from os import makedirs
from typing import List, Tuple

from lxml import etree

from Config import StartPoint
from Config.Config import JSON_DATA_SUB_DETAIL, OUTPUT_DIR
from Config.ReqConfig import URL_HOST, PAGE_PATH_SUB, URL_HOST_API, API_PATH_EXAMPLE_SUB
from Dao.SubDao import SubDao, SubVo
from LogUtil import LogUtil
from LogUtil.LogUtil import com_log, process_log, async_log, pic_log
from MyUtil.MyUtil import filename_rm_invalid_chars
from MyUtil.RcdDataJson import rcd_data_json
from MyUtil.StrToContainerUtil import StrToContainer, tran_dict_by_param_dict
from MyUtil.XpathUtil import xpath_util
from ReqUtil.ReqUtil import ReqUtil
from ReqUtil.SavePicUtil import SavePicUtil

req_util = ReqUtil()
save_pic_util = SavePicUtil()

set_issuer_id = set()
set_director_id = set()
set_series_id = set()

# 创建一个互斥锁
lock = threading.Lock()


def get_sub_detail(sub_id, log=com_log, sub_order=0) -> SubVo:
    # 创建需要的dao, 不使用共享资源, 保证多线程时的线程安全 ↓↓↓
    sub_dao = SubDao()
    # 创建需要的dao, 不使用共享资源, 保证多线程时的线程安全 ↑↑↑

    # sub_vo = SubVo(**dict_sub)

    res = req_util.try_get_times(f"{URL_HOST}{PAGE_PATH_SUB}/{sub_id}",
                                 msg=f"获取子页面 sub_order: {sub_order}, sub_id: {sub_id}",
                                 log=log)
    if res:
        # 解析 Vue js ↓↓↓
        etree_res = etree.HTML(res.text)
        script_text = etree_res.xpath("/html/body/script[not(@src)]/text()")[0].replace(r'\u002F', '/')
        match = re.match(r'window.__NUXT__=\(function\((.+)\){return {layout:"default",data:\[{subDetail:({.+}),'
                         r'query:{.+}\((.+)\)\);',
                         script_text)
        key_list = match.group(1).split(',')
        value_list = StrToContainer(the_str=f"[{match.group(3)}]").get_monomer()
        param_dict = {key: value_list[i] for i, key in enumerate(key_list)}

        sub_detail_str = match.group(2)
        sub_detail_dict = StrToContainer(the_str=sub_detail_str).get_monomer()
        tran_dict_by_param_dict(sub_detail_dict, param_dict)
        log.info(f"获取到子页面的 Vue 数据 sub_detail_dict: {sub_detail_dict}")
        # 解析 Vue js ↑↑↑

        print(sub_detail_dict)
        with lock:
            rcd_data_json.update_dict_json(json_file=JSON_DATA_SUB_DETAIL, new_entry={sub_id: sub_detail_dict},
                                           log=log)

        # 从sdd中获取子信息 ↓↓↓
        name = sub_detail_dict.get('name')
        trailer = sub_detail_dict.get('trailer')
        # 从sdd中获取子信息 ↑↑↑

        # xpath获取发行商信息 ↓↓↓
        card_info = etree_res.xpath("//ul[@class='c-m-u']")[0]
        issuer_name = xpath_util.get_unique(element=card_info,
                                            xpath="./li/div/span[@class='label' and text()='发行：']/../span[@class='cont']/text()"
                                            ).strip()
        # xpath获取发行商信息 ↑↑↑

        # 创建sub对象 ↓↓↓
        sub_vo = SubVo(sub_id, name, trailer, issuer_name)
        log.info(f"获取到子信息: {sub_vo}")
        # 创建sub对象 ↑↑↑

        # 预告片保存 ↓↓↓
        get_and_save_trailer(sub_vo)
        # 预告片保存 ↑↑↑

        insert_result = sub_dao.insert(sub_vo, log=log)
        if insert_result == 1:
            # 在访问共享资源之前获取锁
            lock.acquire()
            # 访问共享资源
            try:
                rcd_data_json.json_file_sub.write(f"{sub_vo}\n")
                log.info(f"json写入文件成功 sub JSON: {sub_vo}")
            except Exception as e:
                log.error(f"json写入文件出现异常 sub JSON: {sub_vo}"
                          f"\n\t异常: {e}")
            # 完成操作后释放锁
            lock.release()

        return sub_vo


def get_and_save_trailer(sub_vo, log=pic_log):
    if sub_vo.trailer:
        dir_trailer_studio = f"{OUTPUT_DIR}/{filename_rm_invalid_chars(sub_vo.name if sub_vo.name else '_NoName')}"
        makedirs(dir_trailer_studio, exist_ok=True)
        places: List[Tuple[str, str]] = [(dir_trailer_studio, f"{sub_vo.studio_name}_{sub_vo.number}")]
        save_pic_util.save_pic_multi_places(url=sub_vo.trailer, places=places, timeout=200,
                                            msg=f"子预告片, sub_vo: {sub_vo}", log=log, is_async=True)


def get_sub_detail_async(args):
    sub_id, example_id, page_num, i = args
    process_log.process4(f"获取子信息: 第{i + 1}个 第{page_num}页 示例: {example_id} Start")
    sub_vo = get_sub_detail(sub_id=sub_id, log=async_log, sub_order=i + 1)
    process_log.process4(f"获取子信息: 第{i + 1}个 第{page_num}页 示例: {example_id} End")
    return sub_vo


def get_example_sub_page(example_id, page_num):
    sub_list: List = []

    data = {
        'filter': 9,  # 过滤: 0-全部, 1-有字幕, 2-可下载, 3-含短评  试了下,没有更多码值
        'id': example_id,
        'page': page_num,
        'pageSize': 50,
        'sort': "1",  # 排序: 1-发布日期, 2-磁链更新  试了下,没有更多码值
        # 'cid': '2',

    }
    dict_res = req_util.try_ajax_post_times(url=f"{URL_HOST_API}{API_PATH_EXAMPLE_SUB}", data=data,
                                            msg=f"获取示例子列表: 第{page_num}页 示例: {example_id}")

    if dict_res:
        if str(dict_res.get('data').get('pageSize')) != '50':
            com_log.error(f"获取示例子列表, 响应的pageSize不是50: {dict_res}, 第{page_num}页 示例:"
                          f" {example_id}")
        # for i, dict_sub in enumerate(dict_res.get('data').get('list')):
        #     LogUtil.LOG_PROCESS_SUB_ORDER = i + 1
        #     if StartPoint.START_POINT_SUB_ORDER > 1:
        #         process_log.process4(f"跳过 获取子信息: 第{i + 1}个 第{page_num}页 示例: {example_id}")
        #         StartPoint.START_POINT_SUB_ORDER -= 1
        #         continue
        #     process_log.process4(f"获取子信息: 第{i + 1}个 第{page_num}页 示例: {example_id} Start")
        #     sub_vo = get_sub_detail(dict_sub.get('id'))
        #     sub_list.append(sub_vo)
        #     process_log.process4(f"获取子信息: 第{i + 1}个 第{page_num}页 示例: {example_vo} End")

        # 创建线程池, 异步多线程获取子信息(整页开始)
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # 开启多个线程获取子详情
            futures = [executor.submit(get_sub_detail_async, args=(dict_sub.get('id'), example_id, page_num, i))
                       for i, dict_sub in enumerate(dict_res.get('data').get('list'))]
        # 等待所有线程完成并获取结果
        for future in concurrent.futures.as_completed(futures):
            if future.result():
                sub_list.append(future.result())
    else:
        com_log.error(f"获取示例子列表失败: 第{page_num}页 示例: {example_id}")
    return sub_list


def get_example_sub(example_id):
    for i in range(1, 100):
        LogUtil.LOG_PROCESS_LEVEL_4 = i
        LogUtil.LOG_PROCESS_LEVEL_5 = 0
        if StartPoint.START_POINT_LEVEL_4 > 1:
            process_log.process3(f"跳过 获取示例子列表: 第{i}页 示例: {example_id}")
            StartPoint.START_POINT_LEVEL_4 -= 1
            continue
        process_log.process3(f"获取示例子列表: 第{i}页 示例: {example_id} Start")
        sub_list = get_example_sub_page(example_id, i)
        com_log.info(f"获取示例子列表完成: 第{i}页 示例: {example_id} 结果: {sub_list}")
        process_log.process3(f"获取示例子列表: 第{i}页 示例: {example_id} End")
        if not sub_list:
            process_log.process3(f"获取示例子列表第{i}页没有数据, 不再获取下一页了")
            break


def test_get_example_sub():
    get_example_sub(1065)


def read_sub_from_file(file_path, reg):
    dict_sub_list = []
    dict_sub_dict = {}
    with open(file=file_path, mode='r', encoding='utf-8') as f:
        lines = f.readlines()
        for line in lines:
            match = re.match(reg, line)
            if match:
                dict_sub = eval(match.group(1))
                dict_sub_list.append(dict_sub)
                dict_sub_dict[dict_sub.get('id')] = dict_sub
    return dict_sub_dict, dict_sub_list


def batch_get_trailer_from_error_log():
    sub_vo_list = []
    sub_vo_dict = {}
    with open(file=r'', mode='r',
              encoding='utf-8') as f:
        lines = f.readlines()
        for line in lines:
            match = re.match(r'2023-0.+出现异常!!! 第5次 msg: 子预告片, sub_vo: ({.+})', line)
            if not match:
                match = re.match(r'2023-0.+响应错误!!! 第5次 msg: 子预告片, sub_vo: ({.+})', line)
            if match:
                dict_sub = eval(match.group(1))
                sub_vo = SubVo(**dict_sub)

                sub_vo_list.append(sub_vo)
                sub_vo_dict[sub_vo.id] = sub_vo

    com_log.info(f"从日志中发现的 预告片 获取失败的子列表: {sub_vo_list}")
    com_log.info(f"从日志中发现的 预告片 获取失败的子列表长度: {len(sub_vo_list)}")
    com_log.info(f"从日志中发现的 预告片 获取失败的子列表去重后: {sub_vo_dict}")
    com_log.info(f"从日志中发现的 预告片 获取失败的子列表长度去重后: {len(sub_vo_dict)}")

    # i = 0
    # for key, value in sub_vo_dict.items():
    #     print(key)
    #     i = i + 1
    #     LogUtil.LOG_PROCESS_SUB_ORDER = i
    #     if i > 0 and i % 100 == 0:
    #         time.sleep(100)  # 模拟耗时操作
    #     threading.Thread(target=get_and_save_trailer, args=(value,)).start()
    #     time.sleep(1)


def batch_get_sub_from_error_log():
    sub_id_list = []
    sub_id_set = set()
    with open(file=r'', mode='r',
              encoding='utf-8') as f:
        lines = f.readlines()
        for line in lines:
            match = re.match(r'2023-0.+响应错误!!! 第5次 msg: 获取子页面.+sub_id: (.+) res:', line)
            if not match:
                match = re.match(r'2023-0.+出现异常!!! 第5次 msg: 获取子页面, sub_vo: ({.+})', line)
            if match:
                sub_id = match.group(1)

                sub_id_list.append(sub_id)
                sub_id_set.add(sub_id)
    com_log.info(f"从日志中发现的 子页面 获取失败的子列表: {sub_id_list}")
    com_log.info(f"从日志中发现的 子页面 获取失败的子列表长度: {len(sub_id_list)}")
    com_log.info(f"从日志中发现的 子页面 获取失败的子列表去重后: {sub_id_set}")
    com_log.info(f"从日志中发现的 子页面 获取失败的子列表长度去重后: {len(sub_id_set)}")
    i = 0
    for sub_id in sub_id_set:
        print(sub_id)
        i = i + 1
        LogUtil.LOG_PROCESS_LEVEL_5 = i
        if i > 0 and i % 100 == 0:
            time.sleep(100)  # 模拟耗时操作
        threading.Thread(target=get_sub_detail, args=(sub_id, async_log, i)).start()
        time.sleep(1)


if __name__ == '__main__':
    start_time = time.time()
    # test_get_example_sub()
    # test_get_sub_detail()
    # batch_get_trailer_from_error_log()
    batch_get_sub_from_error_log()
    end_time = time.time()
    duration = end_time - start_time
    duration_minutes = duration / 60
    print("程序持续时间：", duration_minutes, "分钟")
