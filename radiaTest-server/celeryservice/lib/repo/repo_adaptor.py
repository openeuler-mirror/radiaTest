# Copyright (c) [2022] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
####################################
# @Author  :
# @email   :
# @Date    :
# @License : Mulan PSL v2
#####################################

from server.apps.git_repo.adaptor.ltp import Ltp
from server.apps.git_repo.adaptor.mugen import Mugen
from server.apps.git_repo.adaptor.openjdk import Jdk8uDev, Jdk11uDev, Jdk17uDev
from server.apps.git_repo.adaptor.oss_fuzz import OssFuzz
from server.apps.git_repo.adaptor.gcc import Gcc


class GitRepoAdaptor:
    """dictionary of git repo testcase resolvers.
    this dictionary might be used by getattr function, for example:
        - resolver = getattr(GitRepoAdaptor, 'mugen')
        - resolver = getattr(GitRepoAdator, 'Jdk11uDev')
    
    then, the resolver could be utilized under the same interfaces 
    to block the difference
    """
    mugen = Mugen
    ltp_20220121 = Ltp
    ltp_20230127 = Ltp
    jdk8 = Jdk8uDev
    jdk11 = Jdk11uDev
    jdk17 = Jdk17uDev
    oss_fuzz = OssFuzz
    gcc = Gcc