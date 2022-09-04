# Copyright (c) [2022] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
####################################
# @Author  : disnight
# @email   : fjc837005411@outlook.com
# @Date    : 2022/08/21
# @License : Mulan PSL v2
#####################################

from flask import current_app

import markdown
from lxml import etree


class MdUtil:

    DEFAULT_MD_EXT = [
        "markdown.extensions.extra",
        "markdown.extensions.codehilite"
    ]

    @staticmethod
    def get_md_tables2html(md_content):
        """parse md table 2 lxml table list

        Args:
            md_content (str): content of markdown file
        
        return:
            list: [ lxml_table_1, lxml_table_2]
        """
        try :
            html_content = markdown.markdown(md_content, extensions=MdUtil.DEFAULT_MD_EXT)
        except UnicodeDecodeError as ude:
            current_app.logger.error(f"unsupported unicode in markdown file :{str(ude)}")
            html_content = ""
        except ValueError as ve:
            current_app.logger.error(f"unsupported grammar in markdown file :{str(ve)}")
            html_content = ""
        
        if not html_content:
            return []
        html_etree = etree.HTML(html_content, parser=etree.HTMLParser(encoding="utf-8"))
        table_list = html_etree.xpath("//table")
        return table_list

    @staticmethod
    def get_md_tables2list(md_content, resolver):
        """parse md table 2 python list

        Args:
            md_content (str): content of markdown file
        
        return:
            list: [[md table 1],[md table 2]]
        """
        table_list = MdUtil.get_md_tables2html(md_content)

        tables_content_list = []
        for table in table_list:
            tables_content_list.append(
                resolver(table).parse_table()
            )
        return tables_content_list

