#!/bin/bash
#set -e
#exec >> /root/ipv6_update/ipv6_update.log 2>&1 #可选，记录sh日志
# =========================
# 固定配置
# =========================
BASE_DIR="/root/ipv6_update"
RECORD_FILE="$BASE_DIR/ipv6_prefix_record.txt"
PYTHON_SCRIPT="$BASE_DIR/ipv6_prefix_get.py"
IFACE="ens33"
FIRST_RUN_FLAG="/run/ipv6_first_run"  #开机首次运行标志文件

# =========================
# 3.1 读取旧前缀 prefix1
# =========================
last_line_before=$(tail -n 1 "$RECORD_FILE" 2>/dev/null)
prefix1=$(echo "$last_line_before" | awk -F' - ' '{print $1}')

# --- 开机第一次：强制更新 ---
if [[ ! -f "$FIRST_RUN_FLAG" ]]; then
    echo "[INFO] first run after boot, force update"
    prefix1=""
    touch "$FIRST_RUN_FLAG"
fi

#echo "[DEBUG] prefix1(before) = '$prefix1'"

# =========================
# 3.2 执行获取前缀脚本
# =========================
python3 "$PYTHON_SCRIPT"

# =========================
# 3.3 读取新前缀 prefix2
# =========================
last_line_after=$(tail -n 1 "$RECORD_FILE")
prefix2=$(echo "$last_line_after" | awk -F' - ' '{print $1}')
#echo "[DEBUG] prefix2(after)  = '$prefix2'"

# =========================
# 3.4 判断 prefix2 是否以数字 2 开头
# =========================
if [[ ! "$prefix2" =~ ^2 ]]; then
#    echo "[WARN] invalid prefix2, abort"
    exit 0
fi

# =========================
# 3.4 / 3.5 对比并更新 IPv6
# =========================
if [[ "$prefix1" != "$prefix2" ]]; then
    #echo "[INFO] prefix changed, updating IPv6"
    # 去掉 / 及后面的内容，拼接 a1
    base_prefix="${prefix2%%/*}"
    ipv6_address="${base_prefix}a1"
    #echo "[INFO] new IPv6 = ${ipv6_address}"
    # 刷新并设置 IPv6
    ip -6 addr flush dev "$IFACE"
    ip -6 addr add "${ipv6_address}/64" dev "$IFACE"
fi
#echo "==== ipv6_update end ===="
exit 0
