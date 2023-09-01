from Dao.ComDao import ComVo, ComDao
from LogUtil.LogUtil import com_log


class ExampleVo(ComVo):

    def __init__(self, id, name, pic):
        self.id = id  # ID
        self.name = name  # 名称
        self.pic = pic  # 图片


class ExampleDao(ComDao):
    def __init__(self):
        super().__init__()
        self.table_name = '示例表'
        self.select_by_id_sql = f"""
            """

    def insert(self, vo: ExampleVo, log=com_log):
        insert_sql = f"""
            """
        insert_data = [vo.id, vo.name]
        return self.try_insert(insert_sql, insert_data, vo, log)

    def update_by_id(self, vo: ExampleVo, log=com_log):
        update_sql = f"""
            """
        update_data = [vo.name, vo.id]
        return self.try_update(update_sql, update_data, vo, log)

    def get_data_id(self, vo):
        return [vo.id]
