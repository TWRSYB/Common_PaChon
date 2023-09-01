from Dao.ComDao import ComVo, ComDao
from LogUtil.LogUtil import com_log


class SubVo(ComVo):

    def __init__(self, id, name, trailer, issuer_name):
        self.id = id  # ID
        self.name = name  # 名称
        self.trailer = trailer  # 预告片
        self.issuer_name = issuer_name  # 发行商


class SubDao(ComDao):
    def __init__(self):
        super().__init__()
        self.table_name = '子表'
        self.select_by_id_sql = f"""
            """

    def insert(self, vo: SubVo, log=com_log):
        insert_sql = f"""
            """
        insert_data = [vo.id, vo.name]
        return self.try_insert(insert_sql, insert_data, vo, log)

    def update_by_id(self, vo: SubVo, log=com_log):
        update_sql = f"""
            """
        update_data = [vo.name, vo.id]
        return self.try_update(update_sql, update_data, vo, log)

    def get_data_id(self, vo):
        return [vo.id]
