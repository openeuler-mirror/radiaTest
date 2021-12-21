class CommonCli:
    mem_usage_cli = "echo $(free | grep -w Mem | awk '{print $3}') $(free | grep -w Mem | awk '{print $2}') | awk '{print $1/$2*100}'"

    mem_total_cli = "echo $(free | grep -w Mem | awk '{print $2/(1024*1024)}')"

    cpu_usage_cli = "LAST_CPU_IDLE=$(cat /proc/stat | grep -w cpu | awk '{print $5'}) && LAST_CPU_TOTAL=$(cat /proc/stat | grep -w cpu | awk '{print $2+$3+$4+$5+$6+$7+$8}') && sleep 1 && NEXT_CPU_IDLE=$(cat /proc/stat | grep -w cpu | awk '{print $5}') && NEXT_CPU_TOTAL=$(cat /proc/stat | grep -w cpu | awk '{print $2+$3+$4+$5+$6+$7+$8}') && CPU_IDLE=$(echo $NEXT_CPU_IDLE $LAST_CPU_IDLE | awk '{print $1 - $2}') && CPU_TOTAL=$(echo $NEXT_CPU_TOTAL $LAST_CPU_TOTAL | awk '{print $1 - $2}') && CPU_USAGE=$(echo $CPU_IDLE $CPU_TOTAL | awk '{print 100-$1/$2*100}') && echo $CPU_USAGE"

    cpu_num_cli = "cat /proc/cpuinfo | grep 'physical id' | sort | uniq | wc -l"

    cpu_physical_cores_cli = "cat /proc/cpuinfo | grep 'cpu cores' | uniq | awk '{print $4}'"

    cpu_logical_cores_cli = "cat /proc/cpuinfo | grep 'processor' | wc -l"

    os_cli = "cat /etc/os-release | grep -w PRETTY_NAME | awk -F '\"' '{print $2}'"

    kernel_cli = "echo $(uname -s) $(uname -r)"

    cpu_index_cli = "export LANG=en_US.UTF-8 && lscpu | grep -i '^model name:' | awk -F ': *' '{print $NF}'"



