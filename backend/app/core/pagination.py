# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from typing import Annotated, Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel, Field

# 统一分页：固定每页 PAGE_SIZE 条，避免前端任意指定 pageSize 导致大查询。
PAGE_SIZE = 50

T = TypeVar("T")


class PageParams(BaseModel):
    """分页参数，page 从 1 起。offset 由页码推导，供 service 层直接使用。"""

    page: int = Field(default=1, ge=1)

    @property
    def offset(self) -> int:
        return (self.page - 1) * PAGE_SIZE


class PageResponse(BaseModel, Generic[T]):
    """分页响应，固定 page_size 便于前端一致渲染。"""

    items: list[T]
    total: int
    page: int
    page_size: int = PAGE_SIZE


def get_page_params(
    page: Annotated[int, Query(ge=1)] = 1,
) -> PageParams:
    """FastAPI 依赖：从 ?page= 解析分页参数。"""
    return PageParams(page=page)
