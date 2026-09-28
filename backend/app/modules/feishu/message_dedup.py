# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.feishu.models import FeishuMessageReceipt

# 飞书消息幂等：基于 message_id 唯一约束的处理前 claim / 失败 release 闭环。


def claim_feishu_message(db: Session, message_id: str) -> bool:
    """处理前原子占用一条消息。用 INSERT 唯一约束兜底并发重投：

    成功插入即取得处理权(返回 True)；重复 message_id 触发 IntegrityError
    返回 False，由调用方跳过。处理成功后保留 receipt 永久去重；只有处理
    失败时才 release 回退，允许后续重投重新处理。
    """
    try:
        with db.begin_nested():
            db.add(FeishuMessageReceipt(message_id=message_id))
            db.flush()
        db.commit()
    except IntegrityError:
        db.rollback()
        return False
    return True


def release_feishu_message(db: Session, message_id: str) -> None:
    """处理失败时删除 receipt，放行后续重投重新处理。成功路径不调用此函数。"""
    receipt = db.get(FeishuMessageReceipt, message_id)
    if receipt is not None:
        db.delete(receipt)
        db.commit()
