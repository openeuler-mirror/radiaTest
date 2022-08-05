# Copyright (c) [2022] Huawei Technologies Co.,Ltd.ALL rights reserved.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
####################################
# @Author  : Ethan-Zhang
# @email   : ethanzhang55@outlook.com
# @Date    : 2022/08/10 14:13:00
# @License : Mulan PSL v2
#####################################

from scrapy import Request
from scrapy.spiders import Spider

from scrapyspider.items import OpenqaHomeItem


class OpenqaHomeSpider(Spider):
    name = "openqa_home_spider"
    
    def start_requests(self):
        urls = [
            f"{self.openqa_url}"
        ]
        for url in urls:
            yield Request(url=url, callback=self.parse)

    def parse(self, response):       
        item = OpenqaHomeItem()

        results = response.xpath(f'//div[@id="content"]/h2')

        for result in results:
            item["product_name"] = result.xpath('./a/text()').extract()[0]
            item["group_overview_url"] = result.xpath('./a/@href').extract()[0]

            yield item