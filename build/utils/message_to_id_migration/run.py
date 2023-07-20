# Copyright (c) [2022] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
####################################
# @Author  : hukun66
# @email   : hu_kun@hoperun.com
# @Date    : 2023/09/04
# @License : Mulan PSL v2
#####################################

import argparse
from pathlib import Path

import pymysql

root_path = Path(__file__).parent


class MigrationMessage(object):
    def __init__(self, host, database, user, password, port=3306):
        # 连接数据库
        self.conn = pymysql.connect(
                host=host,
                user=user,
                password=password,
                database=database,
                port=port
                )
        self.cursor = self.conn.cursor()
        self.recover_script = root_path.joinpath('recover_msg_user.sql')

    def backup_record(self):
        # 查询出message表的id和to_id
        self.cursor.execute('SELECT id, to_id FROM message')
        rows = self.cursor.fetchall()

        # 将数据转为插入语句并写入recover_msg_user.sql文件
        with open(self.recover_script, 'w') as f:
            for row in rows:
                f.write(f"INSERT INTO message_users (message_id, user_id) VALUES ({row[0]}, '{row[1]}');\n")

    def close(self):
        # 关闭数据库连接
        self.cursor.close()
        self.conn.close()

    def recover_msg_user(self):
        with open(self.recover_script, "r") as f:
            for insert_sql in f.readlines():
                print(insert_sql)
                self.cursor.execute(insert_sql)
            self.conn.commit()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='migration message user')
    parser.add_argument('-b', '--backup', help='将message表id,to_id备份成message_users插入脚本', action='store_true')
    parser.add_argument(
        '-r', '--recover', help='恢复message表丢失的所有者to_id, 执行该操作前必须先执行backup', action='store_true')
    args = parser.parse_args()
    migration = MigrationMessage(host="mysql_host", user="mysql_user",
                                 password="password", database="radia-test", port=3306)
    if args.backup:
        migration.backup_record()
    if args.recover:
        migration.recover_msg_user()

