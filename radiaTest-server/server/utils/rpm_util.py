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
# @Date    : 2022/07/30
# @License : Mulan PSL v2
#####################################

import os
import argparse
from flask import current_app
from enum import Enum


class RpmCompareStatus(Enum):
    SAME = 0 # name, version, release all same
    VER_UP = 1 # name same, version update, ignore release change
    VER_DOWN = 2 # name same, version downgrade, ignore release change
    REL_UP = 3 # name version same, release changed
    REL_DOWN = 4 # name version same, release downgrade
    ADD = 5 # rpm packages has been added
    DEL = 6 # rpm packages has been removed
    LACK = 7 # lack of rpm packages
    DIFFERENT = 8 # name, version, release, one or more of them are diffrent
    ERROR = 200 # unexpected compare

class RpmName():
    
    file_name = "" # rpm包名
    name = "" # rpm名，即spec中的package的字段
    src_name = "" # 源码包rpm名，即spec中的Name字段
    version = "" # rpm version版本信息，即spec中的Version字段
    release = "" # rpm release版本信息，即spec中的Release字段
    epoch = "" # rpm epoch版本信息，即spec中的Epoch字段，默认为0
    arch = "" # rpm 架构信息，即spec中的Epoch字段，根据架构由不同ok
 
    def __init__(self, **kwargs) -> None:
        """_

        Args:
            - rpm_file_name (str): <name>-<version>-<release>.<arch>.rpm
            
            while using parsed data init a RpmName object, args belows should be provided
            - name (str): <name>
            - version (str): <version>
            - release (str): <release>
            - arch (str): <arch>
        """
        if kwargs.get("rpm_file_name"):
            self.file_name = kwargs.get("rpm_file_name")
            [self.name, self.version, self.release, self.arch] = RpmName.parse_rpm_file_name(self.file_name)
        elif kwargs.keys() == set(["rpm_file_name", "name", "version", "release", "arch"]):
            self.file_name = kwargs.get("rpm_file_name")
            self.name = kwargs.get("name")
            self.version = kwargs.get("version")
            self.release = kwargs.get("release")
            self.arch = kwargs.get("arch")
        else:
            raise ValueError("Arguments are invalid to init a RpmName Object")
    
    def __str__(self) -> str:
        if not self.is_parsed:
            return "unsupported name format"
        return "name: {} version: {} release: {} arch: {}".format(
            self.name,
            self.version,
            self.release,
            self.arch
        )
    
    @staticmethod
    def parse_rpm_file_name(rpm_file_name: str):
        """parse rpm file name

        Args:
            rpm_file_name (str): <name>-<version>-<release>.<arch>.rpm
        
        return:
            list: [<name>, <version>, <release>, <arch>]
        """
        # split rpmfilename to [<name>-<version>-<release>, <arch>, rpm]
        if not rpm_file_name:
            return ["", "", "", ""]
        rpm_split_l1 = rpm_file_name.strip().rsplit(".", 2)
        if len(rpm_split_l1) != 3 and rpm_split_l1[-1] != "rpm":
            current_app.logger.warning(f"{rpm_file_name} is unsupported name format")
            return ["", "", "", ""]
        arch = rpm_split_l1[1]
        # split to [<name>, <version>, <release>]
        rpm_split_l2 = rpm_split_l1[0].rsplit("-", 2)
        if len(rpm_split_l2) != 3:
            current_app.logger.warning(f"{rpm_file_name} is unsupported name format")
            return ["", "", "", ""]
        
        rpm_split_l2.append(arch)
        return rpm_split_l2

    @property
    def is_parsed(self):
        """parse rpm file name

        Args:
            self : example of RpmName
        
        return:
            Boolean: result of RpmName is parsed
        """
        if not self.name or not self.version or not self.release:
            return False
        return True

    def to_dict(self):
        return {
            "name": self.name,
            "version": self.version,
            "release": self.release,
            "arch": self.arch,
            "rpm_file_name": self.file_name,
        }



class RpmNameLoader():
    @staticmethod
    def rpmlist2rpmdict(rpmlist):
        """parse list of string <rpm name> to dict { str: [Rpname] }

        Args:
            rpmlist : list of rpmname [<rpm name 1>, <rpm name 2>, ...]
        
        return:
            rpm_name_dict: dict : { <rpm name 1>.<rpm arch 1>: [ RpmName1], ...}
            repeat_rpm_name_dict : list : [ RpmName1.to_dict(), RpmName2.to_dict(), ...]
        """
        rpm_name_dict = {}
        for rpm_name in rpmlist:
            tmp_rpm_info = RpmName(rpm_file_name=rpm_name)
            if tmp_rpm_info.is_parsed:
                _rpm_name_arch = f"{tmp_rpm_info.name}.{tmp_rpm_info.arch}"
                if _rpm_name_arch not in rpm_name_dict:
                    rpm_name_dict[_rpm_name_arch] = []
                rpm_name_dict[_rpm_name_arch].append(tmp_rpm_info)

        repeat_rpm_dict_list = list()
        for rpm_name, val in rpm_name_dict.items():
            if len(val) > 1:
                for rpm in val:
                    repeat_rpm_dict_list.append(rpm.to_dict())

                is_equal = RpmNameComparator.compare_str_version(val[0].version, val[1].version)
                if is_equal == 0:
                    is_equal1 = RpmNameComparator.compare_str_version(val[0].release, val[1].release)
                    if is_equal1 == 1:
                        rpm_name_dict.update(
                            {rpm_name: [val[1]]}
                        )
                    elif is_equal1 == 2:
                        rpm_name_dict.update(
                            {rpm_name: [val[0]]}
                        )
                elif is_equal == 1:
                    rpm_name_dict.update(
                        {rpm_name: [val[1]]}
                    )
                elif is_equal == 2:
                    rpm_name_dict.update(
                        {rpm_name: [val[0]]}
                    )

        return rpm_name_dict, repeat_rpm_dict_list

    @staticmethod
    def rpmlist2rpmdict_by_name(rpmlist):
        """parse list of string <rpm name> to dict { str: [Rpname] }

        Args:
            rpmlist : list of rpmname [<rpm name 1>, <rpm name 2>, ...]
        
        return:
            dict : { <rpm name 1>: [ RpmName1, RpmName2], ...}
        """
        rpm_name_dict = {}
        for rpm_name in rpmlist:
            tmp_rpm_info = RpmName(rpm_file_name=rpm_name)
            if tmp_rpm_info.is_parsed:
                _rpm_name = f"{tmp_rpm_info.name}"
                if _rpm_name not in rpm_name_dict:
                    rpm_name_dict[_rpm_name] = []
                rpm_name_dict.get(_rpm_name).append(tmp_rpm_info)
        return rpm_name_dict

    @staticmethod
    def get_parsed_rpmlist(rpmlist):
        return [RpmName(rpm_file_name=_r).to_dict() for _r in rpmlist]

    @staticmethod
    def load_rpmlist_from_file(filepath):
        """read rpmlist from from , then `load_rpm_from_list`

        Args:
            filepath : path of file which contain list of rpm name
        
        return:
            rpmlist : list of rpmname [<rpm name 1>, <rpm name 2>, ...]
        """
        real_path = os.path.realpath(filepath)
        rpmset = set()
        # now only supported read from utf-8
        with open(real_path, "r", encoding='utf-8') as f:
            lines = f.readlines()
            for line in lines:
                if line.strip().endswith(".rpm"):
                    rpmset.add(line.strip())
        rpmlist = list(rpmset)
        return rpmlist

    @staticmethod
    def load_rpmdict_from_file(filepath):
        return RpmNameLoader.rpmlist2rpmdict(RpmNameLoader.load_rpmlist_from_file(filepath))


class RpmNameComparator():
    
    @staticmethod
    def compare_str_version(version_a, version_b):
        """Compare the order between two given version strings

        Args:
            version_a (str): one version numbers a, like "v1.11.1"
            version_b (str): one version numbers b, like "1.12.1"
        return:
            is_equal (int):
                0: version_a = version_b
                1: version_a > version_b
                2: version_a < version_b
        e.g.
            v1.11.1 < 1.12.1
            v1.22.2 > v1.22
            4.oe2203sp1 < 4.oe2209
        """
        version_a_arr = version_a.split(".")
        version_b_arr = version_b.split(".")

        cnt = len(version_a_arr) if len(version_a_arr) > len(version_b_arr) else len(version_b_arr)
        is_equal = 0
        for i in range(cnt):
            if i == len(version_a_arr):
                is_equal = 2
                break
            if i == len(version_b_arr):
                is_equal = 1
                break
            if version_a_arr[i] == version_b_arr[i]:
                continue
            if version_a_arr[i].startswith("oe") and version_b_arr[i].startswith("oe"):
                tmp_a = version_a_arr[i]
                tmp_b = version_b_arr[i]
                tmp_cnt = len(tmp_b) if len(tmp_a) > len(tmp_b) else len(tmp_a)
                for j in range(tmp_cnt):
                    if tmp_a[j] == tmp_b[j]:
                        continue
                    else:
                        is_equal = 1 if tmp_a[j] > tmp_b[j] else 2
                        break
                if is_equal == 0:
                    if len(tmp_a) != len(tmp_b):
                        is_equal = 1 if len(tmp_a) > len(tmp_b) else 2
                        break
                    continue
                else:
                    break
            if version_a_arr[i].isnumeric():
                version_a_t = int(version_a_arr[i])
            else:
                tmp_a = "".join(filter(str.isdigit, version_a_arr[i]))
                if tmp_a == "":
                    version_a_t = -1
                else:
                    version_a_t = int(tmp_a)
            if version_b_arr[i].isnumeric():
                version_b_t = int(version_b_arr[i])
            else:
                tmp_b = "".join(filter(str.isdigit, version_b_arr[i]))
                #如果全为字母，设大小为-1，作为比较值
                if tmp_b == "":
                    version_b_t = -1
                else:
                    version_b_t = int(tmp_b)
            if version_a_t == version_b_t:
                continue
            else:
                is_equal = 1 if version_a_t > version_b_t else 2
                break
        return is_equal

    @staticmethod
    def compare_rpm_name_cls(rpm_info_1, rpm_info_2, get_dist=False):
        """compare the rpm info from rpm file name(static method)

        Args:
            rpm_info_1 (RpmName): rpm name info from class RpmName
            rpm_info_2 (RpmName): rpm name info from class RpmName
            get_dist (bool, optional): either to . Defaults to False.
        """
        if isinstance(rpm_info_1, RpmName) and isinstance(rpm_info_2, RpmName):
            if not (rpm_info_1.is_parsed or rpm_info_2.is_parsed):
                current_app.logger.error("unsuported rpm name format")
                return RpmCompareStatus.ERROR
            if rpm_info_1.version == rpm_info_2.version:
                # todo for compare dist diff
                if rpm_info_1.release == rpm_info_2.release:
                    return RpmCompareStatus.SAME
                else:
                    is_equal = RpmNameComparator.compare_str_version(
                        rpm_info_1.release, rpm_info_2.release
                    )
                    if is_equal == 1:
                        return RpmCompareStatus.REL_DOWN
                    return RpmCompareStatus.REL_UP
            else:
                is_equal = RpmNameComparator.compare_str_version(
                    rpm_info_1.version, rpm_info_2.version
                )
                if is_equal == 1:
                    return RpmCompareStatus.VER_DOWN
                return RpmCompareStatus.VER_UP
        elif isinstance(rpm_info_1, RpmName):
            return RpmCompareStatus.DEL
        elif isinstance(rpm_info_2, RpmName):
            return RpmCompareStatus.ADD
        else:
            raise ValueError("params value invalid, because one of rpm_info must a RpmName instance at least")

    @staticmethod
    def compare_rpm_name_cls2(rpm_info_1, rpm_info_2, get_dist=False):
        """compare the rpm info from rpm file name(static method)

        Args:
            rpm_info_1 (RpmName): rpm name info from class RpmName
            rpm_info_2 (RpmName): rpm name info from class RpmName
            get_dist (bool, optional): either to . Defaults to False.
        """
        if isinstance(rpm_info_1, RpmName) and isinstance(rpm_info_2, RpmName):
            if not (rpm_info_1.is_parsed or rpm_info_2.is_parsed):
                current_app.logger.error("unsuported rpm name format")
                return RpmCompareStatus.ERROR
            if rpm_info_1.version != rpm_info_2.version or rpm_info_1.release != rpm_info_2.release:
                return RpmCompareStatus.DIFFERENT
            else:
                return RpmCompareStatus.SAME
        elif isinstance(rpm_info_1, RpmName):
            return RpmCompareStatus.LACK
        elif isinstance(rpm_info_2, RpmName):
            return RpmCompareStatus.LACK
        else:
            raise ValueError("params value invalid, because one of rpm_info must a RpmName instance at least")

    @staticmethod
    def compare_version(ver1, ver2):
        """compare the rpm info from rpm file name(static method)

        Args:
            rpm_info_1 (RpmName): rpm name info from class RpmName
            rpm_info_2 (RpmName): rpm name info from class RpmName

        return
            RpmCompareStatus
        """
        pass 

    @staticmethod
    def compare_rpm_name(rpm_name1:str, rpm_name2:str, get_dict=False):
        return RpmNameComparator.compare_rpm_name_cls(
            RpmName(rpm_file_name=rpm_name1), 
            RpmName(rpm_file_name=rpm_name2)
        )

    @staticmethod
    def compare_rpm_dict(rpmdict1, rpmdict2):
        compare_result_list = []
        for rpm_name in set(list(rpmdict1.keys()) + list(rpmdict2.keys())):
            rpm_1 = rpmdict1.get(rpm_name)[0] if isinstance(rpmdict1.get(rpm_name), list) else None
            rpm_2 = rpmdict2.get(rpm_name)[0] if isinstance(rpmdict2.get(rpm_name), list) else None
            tmp_result = RpmNameComparator.compare_rpm_name_cls(rpm_1, rpm_2)
            compare_result_list.append({
                "arch": rpm_1.arch if rpm_1 else rpm_2.arch,
                "rpm_list_1": rpm_1.file_name if rpm_1 else '',
                "rpm_list_2": rpm_2.file_name if rpm_2 else '',
                "compare_result": tmp_result.name
            })
        return compare_result_list

    @staticmethod
    def compare_rpm_dict2(rpmdict1, rpmdict2):
        compare_result_list = []
        for rpm_name in set(list(rpmdict1.keys()) + list(rpmdict2.keys())):
            rpm_1 = rpmdict1.get(rpm_name)[0] if isinstance(rpmdict1.get(rpm_name), list) else None
            rpm_2 = rpmdict2.get(rpm_name)[0] if isinstance(rpmdict2.get(rpm_name), list) else None
            tmp_result = RpmNameComparator.compare_rpm_name_cls2(rpm_1, rpm_2)
            compare_result_list.append({
                "rpm_name": rpm_name,
                "rpm_x86": rpm_1.file_name if rpm_1 else '',
                "rpm_arm": rpm_2.file_name if rpm_2 else '',
                "compare_result": tmp_result.name
            })
        return compare_result_list


def parse_rpm_name(rpm_args):
    rpm_name = rpm_args.rpmname
    rpm_name_info = RpmName(rpm_file_name=rpm_name)
    current_app.logger.debug(f"{str(rpm_name_info)}")
    return rpm_name_info


def compare_rpm_name(rpm_args):
    if len(rpm_args.rpmlist) != 2:
        current_app.logger.warning("this cli only support 2 rpm name compare")
        return RpmCompareStatus.ERROR
    result = RpmNameComparator.compare_rpm_name(rpm_args.rpmlist[0], rpm_args.rpmlist[1])
    return [rpm_args.rpmlist[0], rpm_args.rpmlist[1], result]


def compare_rpm_list(rpm_args, save_file=True, output_file="output.csv"): 
    if len(rpm_args.rpmlistfile) != 2:
        current_app.logger.warning("this cli only support 2 rpmlist file compare")
        return []
    rpmdict1 = RpmNameLoader.load_rpmdict_from_file(rpm_args.rpmlistfile[0])
    rpmdict2 = RpmNameLoader.load_rpmdict_from_file(rpm_args.rpmlistfile[1])
    result = RpmNameComparator.compare_rpm_dict(rpmdict1, rpmdict2)
    if save_file:
        with open(output_file, "w") as f:
            for line in result:
                f.write("{},{},{},{}".format(
                    line.get("arch", ""),
                    line.get("rpm_list_1", ""),
                    line.get("rpm_list_2", ""),
                    line.get("compare_result", "")
                ))
                # 为保证CSV文件换行无空白行，故强制使用\n作为换行符
                f.write("\n")
    return result


def load_compare_rpm_name_args():
    """cli input parser

    Returns:
        args : cli input
    """
    parser = argparse.ArgumentParser()
    
    subparsers = parser.add_subparsers(dest="cmd_name",
                                       help="use sub command rpmnama parse, rpmname compare, rpmlist compare")
    
    rpmname_parser = subparsers.add_parser("rpm_name",
                                        help="get license from spec")
    rpmname_parser.add_argument("-rn", "--rpmname", type=str,
                                help="the name of rpmfile")
    rpmname_parser.set_defaults(func=parse_rpm_name)
    
    
    rpmname_com_parser = subparsers.add_parser("rpm_compare",
                                        help="get license from spec")
    rpmname_com_parser.add_argument("-rl", "--rpmlist", type=str, nargs=2,
                                help="the name list of rpmfile")
    rpmname_com_parser.set_defaults(func=compare_rpm_name)
    
    rpmlist_com_parser = subparsers.add_parser("rpmlist_compare",
                                        help="get license from spec")    
    rpmlist_com_parser.add_argument("-rf", "--rpmlistfile", type=str, nargs=2,
                                help="the file path of rpmlist")
    rpmlist_com_parser.set_defaults(func=compare_rpm_list)
    
    return parser.parse_args()


if __name__ == "__main__":
    args = load_compare_rpm_name_args()
    compare_result = args.func(args)
    print(compare_result)
