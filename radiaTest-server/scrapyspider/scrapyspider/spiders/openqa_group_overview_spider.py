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

from scrapyspider.items import OpenqaGroupOverviewItem


class OpenqaHomeSpider(Spider):
    name = "openqa_group_overview_spider"
    
    def start_requests(self):
        urls = [
            f"{self.group_overview_url}?limit_builds=400"
        ]
        for url in urls:
            yield Request(url=url, callback=self.parse)

    def parse(self, response):       
        results = response.xpath('//div[@id="build-results"]/div[@class="row build-row no-children"]')

        for result in results:
            item = OpenqaGroupOverviewItem()
            item["product_name"] = self.product_name
            
            title = result.xpath('./div[@class="col-lg-4 text-nowrap"]/span[@class="h4"]')

            item["build_name"] = title.xpath('./a/text()').extract()[0]
            item["build_tests_url"] = title.xpath('./a/@href').extract()[0]
            item["build_time"] = title.xpath('./abbr/@title').extract()[0]

            yield item