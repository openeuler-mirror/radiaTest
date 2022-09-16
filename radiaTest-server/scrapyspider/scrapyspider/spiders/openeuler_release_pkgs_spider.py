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
# @Date    : 2022/09/05 14:13:00
# @License : Mulan PSL v2
#####################################

from scrapy import Request
from scrapy.spiders import Spider

from scrapyspider.items import OpeneulerPkgsListItem


class OpeneulerPkgsListSpider(Spider):
    name = "openeuler_pkgs_list_spider"
    custom_settings = {
        'ITEM_PIPELINES': {
            'scrapyspider.pipelines.FilePipeline': 500,
        }
    }
    
    def start_requests(self):
        urls = [
            f"{self.openeuler_repo_url}/everything/aarch64/Packages/",
            f"{self.openeuler_repo_url}/everything/x86_64/Packages/",
        ]
        for url in urls:
            yield Request(url=url, callback=self.parse)

    def parse(self, response):
        item = OpeneulerPkgsListItem()

        results = response.xpath(f'//table[@id="list"]/tbody/tr')

        for result in results:
            package = result.xpath('./td[@class="link"]/a/text()').extract()[0]
            if package != "Parent directory/":
                item["rpm_file_name"] = package
                item["build"] = self.build
                item["product"] = self.product
                yield item