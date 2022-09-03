# Copyright (c) [2022] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
####################################
# @Author  : 凹凸曼打小怪兽
# @email   : 15710801006@163.com
# @Date    : 2022/09/05
# @License : Mulan PSL v2
#####################################

#!/bin/bash

# $1: name of vmachine
# $2: type of config for vmachine
# except $1 and $2: vm-xml values

if [[ $2 == "vncport" ]];then
    /usr/bin/expect <<-EOF
    spawn virsh edit $1
    send ":%s/type=\'vnc\' port=\'-1\' autoport=\'yes\'/type=\'vnc\' port=\'$3\' autoport=\'no\'/g\n"
    send ":wq!\n"
    expect eof
EOF
    echo "vncport update is successful"
    exit 0
elif [[ $2 == "vmem" ]];then
    /usr/bin/expect <<-EOF
    spawn virsh edit $1
    send ":%s/<memory unit=\'KiB\'>\\\w*<\\\/memory>/<memory unit=\'KiB\'>$3<\\\/memory>/g\n"
    send ":%s/<currentMemory unit=\'KiB\'>\\\w*<\\\/currentMemory>/<currentMemory unit=\'KiB\'>$3<\\\/currentMemory>/g\n"
    send ":wq!\n"
    expect eof
EOF
    echo "vmemory update is successful"
    exit 0
elif [[ $3 == "vcpu" ]];then
    /usr/bin/expect <<-EOF
    spawn virsh edit $1
    send ":%s/<vcpu placement=\'static\'>\\\w*<\\\/vcpu>/<vcpu placement=\'static\'>$3<\\\/vcpu>/g\n"
    send ":%s/sockets=\'\\\w*\'/sockets=\'$4\'/g\n"
    send ":%s/cores=\'\\\w*\'/cores=\'$5\'/g\n"
    send ":%s/threads=\'\\\w*\'/threads=\'$6\'/g\n"
    send ":wq!\n"
    expect eof
EOF
    echo "vcpu update is successful"
    exit 0
else
  echo "unkown type"
  exit 1
fi
