import time
from typing import List, Tuple

from Config import StartPoint
from Config.Config import JSON_DATA_EXAMPLE, OUTPUT_DIR
from Config.ReqConfig import URL_HOST_API, API_PATH_EXAMPLE_LIST, API_PATH_EXAMPLE
from Dao.ExampleDao import ExampleVo, ExampleDao
from GetSub import get_example_sub
from LogUtil import LogUtil
from LogUtil.LogUtil import process_log, com_log, pic_log
from MyUtil.RcdDataJson import rcd_data_json
from ReqUtil.ReqUtil import ReqUtil
from ReqUtil.SavePicUtil import SavePicUtil
from SpcUtil.SpcUtil import set_cid_for_vo

req_util = ReqUtil()
save_pic_util = SavePicUtil()

example_dao = ExampleDao()


def get_example_list_page(cid, page_num) -> List[ExampleVo]:
    example_list: List[ExampleVo] = []
    params = {
        'cid': cid,
        'page': page_num,
        'pageSize': '50',

    }
    dict_res = req_util.try_ajax_get_times(url=f"{URL_HOST_API}/{API_PATH_EXAMPLE_LIST}", params=params,
                                           msg=f"获取 示例 列表: 第{page_num}页")
    if dict_res:
        if str(dict_res.get('data').get('pageSize')) != '50':
            com_log.error(f"获取 示例 列表, 响应的pageSize不是50: {dict_res}, 第{page_num}页 cid: {cid}")
        for i, dict_example in enumerate(dict_res.get('data').get('exampleList')):
            LogUtil.LOG_PROCESS_LEVEL_3 = i + 1
            LogUtil.LOG_PROCESS_LEVEL_4 = 0
            LogUtil.LOG_PROCESS_LEVEL_5 = 0
            if StartPoint.START_POINT_LEVEL_3 > 1:
                process_log.process1(f"跳过 获取 示例 信息: 第{i + 1}个 第{page_num}页")
                StartPoint.START_POINT_LEVEL_3 -= 1
                continue
            process_log.process2(f"获取 示例 信息: 第{i + 1}个 第{page_num}页 Start")
            example_id = dict_example.get('id')

            example_vo = save_example(example_id, cid)
            example_list.append(example_vo)

            process_log.process2(f"获取 示例 信息: 第{i + 1}个 第{page_num}页 End")
    else:
        com_log.error(f"获取 示例 列表失败: 第{page_num}页")
    return example_list


def save_example(example_id, cid) -> ExampleVo:
    """
    进一步获取并保存 示例 的信息
    :param cid:
    :param example_id:
    :return:
    """

    example_vo = None
    data = {
        'id': example_id
    }

    dict_res = req_util.try_ajax_post_times(f'{URL_HOST_API}{API_PATH_EXAMPLE}', data=data,
                                            msg=f"获取 示例 信息,  示例 ID: {example_id}")
    if dict_res:
        dict_example = dict_res.get('data')
        name = dict_example.get('name')
        pic = dict_example.get('pic')
        example_vo = ExampleVo(id=example_id, name=name, pic=pic)

        set_cid_for_vo(example_vo, cid)

        com_log.info(f"获取到 示例 : {example_vo}")

        #  示例 入库并保存JSON ↓↓↓
        insert_result = example_dao.insert(example_vo, log=com_log)
        if insert_result == 1:
            rcd_data_json.add_data_to_json_list(json_file=JSON_DATA_EXAMPLE, data=example_vo)
        elif isinstance(insert_result, Tuple):
            example_vo = ExampleVo(*insert_result[0])
            set_cid_for_vo(example_vo, cid)
            update_result = example_dao.update_by_id(example_vo)
            if update_result == 1:
                rcd_data_json.update_data_to_json(json_file=JSON_DATA_EXAMPLE, data=example_vo,
                                                  update_by_list=[('id', example_vo.id)], msg=f" 示例 ")
        #  示例 入库并保存JSON ↑↑↑

        # 保存 示例 图片 ↓↓↓
        if example_vo.pic:
            places: List[Tuple[str, str]] = [(f"{OUTPUT_DIR}", f"{example_vo.id}_{example_vo.name}")]
            save_pic_util.save_pic_multi_places(url=f"{example_vo.pic}", places=places,
                                                msg=f"获取 示例 头像:  示例 {example_vo}"
                                                # , is_async=True, log=pic_log
                                                )
        # 保存 示例 头像 ↑↑↑

        # 获取 示例 子信息 ↓↓↓
        if cid in [2, 3, 4, 10]:
            get_example_sub(example_vo.id)
        # 获取 示例 子信息 ↑↑↑
    else:
        com_log.error(f"获取 示例 信息失败,  示例 ID: {example_id}")
    return example_vo


def get_cid_data(cid):
    """
    获取不同cid的数据
    :param cid:
    :return:
    """
    for i in range(1, 500):
        LogUtil.LOG_PROCESS_LEVEL_2 = i
        LogUtil.LOG_PROCESS_LEVEL_3 = 0
        LogUtil.LOG_PROCESS_LEVEL_4 = 0
        LogUtil.LOG_PROCESS_LEVEL_5 = 0
        if StartPoint.START_POINT_LEVEL_2 > 1:
            process_log.process1(f"跳过 example 列表: 第{i}页")
            StartPoint.START_POINT_LEVEL_2 -= 1
            continue
        process_log.process1(f"获取 example 列表: 第{i}页 Start")
        example_list = get_example_list_page(cid, i)
        process_log.process1(f"获取 example 列表成功: 第{i}页 结果: {example_list}")
        process_log.process1(f"获取 example 列表: 第{i}页 End")
        if not example_list:
            process_log.process1(f"获取 example 列表第{i}页 结果为空, 不再获取下一页")
            break


def start():
    for i, cid in enumerate([1, 2, 3, 4, 10]):
        LogUtil.LOG_PROCESS_LEVEL_1 = i + 1
        LogUtil.LOG_PROCESS_LEVEL_2 = 0
        LogUtil.LOG_PROCESS_LEVEL_3 = 0
        LogUtil.LOG_PROCESS_LEVEL_4 = 0
        LogUtil.LOG_PROCESS_LEVEL_5 = 0
        if StartPoint.START_POINT_LEVEL_1 > 1:
            process_log.process1(f"跳过 获取cid的数据: cid:{cid}")
            StartPoint.START_POINT_LEVEL_1 -= 1
            continue
        process_log.process1(f"获取cid的数据: cid:{cid} Start")
        get_cid_data(cid)
        process_log.process1(f"获取cid的数据: cid:{cid} End")


def test_get_example_list_page():
    get_example_list_page(cid=10, page_num=1)


if __name__ == '__main__':
    start_time = time.time()
    # start()
    get_cid_data(2)
    # test_get_example_list_page()
    end_time = time.time()
    duration = end_time - start_time
    duration_minutes = duration / 60
    print("程序持续时间：", duration_minutes, "分钟")
