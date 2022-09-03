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
    def get_md_tables2list(md_content):
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
                HtmlUtil.parse_table(table)
            )
        return tables_content_list


class HtmlUtil:
    """parse html format text
    table format as follow
    <table>
        <thead>
            <tr><th>xxx</th><th>xxx</th></tr>
        </thead>
        <tbody>
            <tr><td>xxx</td><td>xxx</td></tr>
            <tr><td>xxx</td><td>xxx</td></tr>
        </tbody>
    </table>
    """

    @staticmethod
    def parse_table(table_content):
        """parse xpath table element 2 python list

        Args:
            table_content (xpath node): result of html.xpath("//table") element
        
        return:
            list: [[th list],[td list 1], [td list 2]]
        """
        table_result = []
        # 解析 thead
        thead_list = table_content.xpath("thead/tr/th")
        if not thead_list:
            current_app.logger.debug("html content has no table info")
            return []
        thead_content_list = []
        for thead in thead_list:
            thead_content_list.append(thead.text)
        table_result.append(thead_content_list)
        # 解析 tbody
        tbody_tr_list = table_content.xpath("tbody/tr")
        for tbody_tr in tbody_tr_list:
            td_content_list = []
            td_list = tbody_tr.xpath("td")
            # 渲染md过程中,该组件会将连在表格后面的内容一起转换在table标签下,对这些内容进行过滤
            if td_list and (not HtmlUtil.parse_td_text(td_list[0])):
                break
            for td in td_list:
                td_content_list.append(HtmlUtil.parse_td_text(td))
            table_result.append(td_content_list)
        return table_result

    @staticmethod
    def parse_td_text(td_content):
        """parse td’s text and chile nodes' text

        Args:
            td_content (xpath node): result of html.xpath("td") element

        td format as follow:
            <td>text</td>
            <td><a>text1</a><a>text1</a></td>
        
        return:
            list: [tds' text]
        """
        if td_content.text:
            return td_content.text
        a_list = td_content.xpath("a")
        if a_list:
            result = []
            for a_content in a_list:
                if a_content.text:
                    result.append(a_content.text) 
            return " ".join(result)
        return ""
