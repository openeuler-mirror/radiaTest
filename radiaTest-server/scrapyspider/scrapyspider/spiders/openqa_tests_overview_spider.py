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

from scrapyspider.items import OpenqaTestsOverviewItem


class OpenqaTestsOverviewSpider(Spider):
    name = "openqa_tests_overview_spider"
    
    def start_requests(self):
        urls = [
            f"{self.openqa_url}{self.tests_overview_url}"
        ]
        for url in urls:
            yield Request(url=url, callback=self.parse)

    def parse(self, response):       
        results = response.xpath('//table[@id="results_dvd"]/tbody/tr')

        for result in results:
            item = OpenqaTestsOverviewItem()
            item["product_build"] = self.product_build
            item["test"] = result.xpath('./td[@class="name"]/span/text()').extract()[0]
            item["aarch64_res_status"] = "-"
            item["aarch64_res_log"] = "-"
            item["aarch64_failedmodule_name"] = "-"
            item["aarch64_failedmodule_log"] = "-"
            item["x86_64_res_status"] = "-"
            item["x86_64_res_log"] = "-"
            item["x86_64_failedmodule_name"] = "-"
            item["x86_64_failedmodule_log"] = "-"

            res_selectors = result.xpath('./td[starts-with(@id, "res_dvd_")]|./td[text()="-"]')
            if not res_selectors:
                yield item
                continue

            aarch64_selector = res_selectors[0]

            if aarch64_selector.extract() != "<td>-</td>":
                res = aarch64_selector.xpath('./span[starts-with(@id, "res-")]/a')
                if not res:
                    res = aarch64_selector.xpath('./a')
                
                item["aarch64_res_status"] = res.xpath('./i/@title').extract()[0]
                item["aarch64_res_log"] = f"{self.openqa_url}{res.xpath('./@href').extract()[0]}"

                failedmodule = aarch64_selector.xpath('./span[@class="failedmodule"]')
                if failedmodule:
                    item["aarch64_failedmodule_name"] = failedmodule.xpath('./a/span/text()').extract()[0]
                    item["aarch64_failedmodule_log"] = f"{self.openqa_url}{failedmodule.xpath('./a/@href').extract()[0]}"

            try:
                x86_64_selector = res_selectors[1]
            except IndexError:
                yield item
                continue

            if x86_64_selector.extract() != "<td>-</td>":
                res = x86_64_selector.xpath('./span[starts-with(@id, "res-")]/a')
                if not res:
                    res = x86_64_selector.xpath('./a')
                
                item["x86_64_res_status"] = res.xpath('./i/@title').extract()[0]
                item["x86_64_res_log"] = f"{self.openqa_url}{res.xpath('./@href').extract()[0]}"

                failedmodule = x86_64_selector.xpath('./span[@class="failedmodule"]')
                if failedmodule:
                    item["x86_64_failedmodule_name"] = failedmodule.xpath('./a/span/text()').extract()[0]
                    item["x86_64_failedmodule_log"] = f"{self.openqa_url}{failedmodule.xpath('./a/@href').extract()[0]}" 

            yield item
