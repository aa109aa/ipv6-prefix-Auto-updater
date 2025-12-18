# IPv6 前缀/Prefix 自动检测与地址更新项目

## 一、项目背景与目标

本项目用于特定情况下 **在 Linux（Debian 12）系统上自动检测光猫（型号：ZXHN F7610M）下发的 IPv6 前缀变化**，并在前缀发生变化时：

* 自动生成固定 IPv6 地址（前缀 + `::a1`）
* 自动更新到指定网络接口（如 `ens33`）
* 开机自启动
* 每小时自动检查一次
* 全流程可追溯（前缀记录到文件）

该方案基于 **systemd service + timer**，不依赖 crontab，结构清晰、稳定可靠。适用于飞牛/FnOS1.1.4版本。

光猫仅需关闭ipv6的RA通告和ipv6DHCP，不影响ipv6本地链路，其余终端可通过本项目思路访问ipv6外网。

目前仅适用于 **光猫型号：ZXHN F7610M**，其余型号需自行测试，可用默认用户登录

本项目仅提供简单思路，进一步可以实现光猫定时重启，不同光猫登录逻辑可能不相同，需自行研究。

![ScreenShot_2025-12-19_021411_028.png](IMG%2FScreenShot_2025-12-19_021411_028.png)

![ScreenShot_2025-12-19_021421_520.png](IMG%2FScreenShot_2025-12-19_021421_520.png)

![ScreenShot_2025-12-16_032110_059.png](IMG%2FScreenShot_2025-12-16_032110_059.png)
---

## 二、整体工作流程

```text
systemd timer（每小时 / 开机）
        ↓
ipv6-update.service（oneshot）
        ↓
ipv6_update.sh
        ↓
1. 读取历史前缀（prefix1）
2. 调用 python 脚本获取新前缀
3. 再次读取最新前缀（prefix2）
4. 判断前缀是否合法（以数字 2 开头）
5. 若前缀发生变化：
   - 生成 IPv6 地址（prefix::a1/64）
   - 刷新接口 IPv6
   - 添加新 IPv6
```

---

## 三、目录结构

```text
/root/ipv6_update/
├── ipv6_prefix_get.py        # 获取 IPv6 前缀并追加日志记录
├── ipv6_prefix_record.txt   # IPv6 前缀历史日志
├── ipv6_update.sh           # 前缀对比 + IPv6 更新脚本
├── ipv6-update.service      # systemd 服务（oneshot）
├── ipv6-update.timer        # systemd 定时器（每小时）
└── README.md                # 本说明文件
```

---

## 四、各文件职责说明

### 1️⃣ ipv6_prefix_get.py

**作用：**

* 登录光猫后台
* 获取当前 IPv6 前缀（格式如：`2409:xxxx::/60`）
* 追加写入到记录文件最后一行

**记录格式：**

```text
2409:xxxx:xxx:xxxx::/60 - 2025-12-15 23:33:02
```

**注意：**

* 使用绝对路径写入：

  ```
  /root/ipv6_update/ipv6_prefix_record.txt
  ```
* 每次运行都会写一行（便于历史追溯）

---

### 2️⃣ ipv6_prefix_record.txt

**作用：**

* 保存所有历史 IPv6 前缀
* shell 脚本通过 `tail -n 1` 读取最后一条作为“当前前缀”

---

### 3️⃣ ipv6_update.sh

**作用：**

* 前缀变化判断
* IPv6 地址生成
* 网络接口配置更新

**核心逻辑：**

1. 读取旧前缀（prefix1）
2. 执行 `ipv6_prefix_get.py`
3. 再次读取新前缀（prefix2）
4. 判断：

   * prefix2 是否以 `2` 开头（合法公网 IPv6）
   * prefix1 与 prefix2 是否不同
5. 若变化：

   * 生成 `xxxx::a1/64`
   * 执行：

     ```bash
     ip -6 addr flush dev ens33
     ip -6 addr add <ipv6_address>/64 dev ens33
     ```
注意：
1、每次更新都会 flush 掉之前的地址，然后添加新的地址。如果有多个 IPv6 地址需求的话，这个脚本需要改进一下，改成只添加新的地址而不是 flush 掉所有地址。

---

### 4️⃣ ipv6-update.service

**类型：**

* `Type=oneshot`

**作用：**

* 每次被 timer 触发时执行一次 `ipv6_update.sh`
* 执行完即退出（这是正确行为）

---

### 5️⃣ ipv6-update.timer

**作用：**

* 系统级调度器
* 实现：

  * 开机自动启动
  * 每小时执行一次

**触发逻辑：**

* 开机时以及开机后延迟三分钟执行一次
* 此后每 1 小时执行一次

---

---

## 五、手动调试

### 1️⃣ 手动执行 Python 脚本

手动安装依赖,只需要安装两个额外的库
```bash
pip3 install requests --break-system-packages
pip3 install beautifulsoup4 --break-system-packages
```

从光猫上获取ipv6前缀，需替换自己的用户名和密码
```bash
root@imini:~# python3 ipv6_update/ipv6_prefix_get.py
当前 IPv6 前缀：2409:xxxx:xxx:xxxx::/60 - 2025-12-16 03:01:54
```
![ScreenShot_2025-12-16_025928_393.png](IMG%2FScreenShot_2025-12-16_025928_393.png)

### 2️⃣ 手动执行更新脚本
执行ipv6更新命令，需替换接口，以及需要的ipv6地址后缀
```bash
root@imini:~# bash ipv6_update/ipv6_update.sh
当前 IPv6 前缀：2409:xxxx:xxx:xxxx::/60 - 2025-12-16 03:03:31
```
![ScreenShot_2025-12-16_030102_229.png](IMG%2FScreenShot_2025-12-16_030102_229.png)

### 3️⃣ 查看当前 IPv6 地址

```bash
ip -6 addr show dev ens33
```

---

## 六、部署步骤

### 1️⃣ 确保脚本可执行

```bash
chmod +x /root/ipv6_update/ipv6_update.sh
#python3 /root/ipv6_update/ipv6_prefix_get.py #手动调试
#bash /root/ipv6_update/ipv6_update.sh   #手动调试
```

---

### 2️⃣ 创建 systemd 链接

```bash
ln -sf /root/ipv6_update/ipv6-update.service /etc/systemd/system/ipv6-update.service
ln -sf /root/ipv6_update/ipv6-update.timer   /etc/systemd/system/ipv6-update.timer
```

---

### 3️⃣ 重新加载 systemd

```bash
systemctl daemon-reload
```

---

### 4️⃣ 启用并启动定时器（关键）

```bash
systemctl enable --now ipv6-update.timer
```

---

## 七、运行状态验证

### 查看定时器状态

```bash
systemctl list-timers | grep ipv6
```

示例输出（正常）：

```text
NEXT                         LEFT      LAST                         PASSED    UNIT
Tue 00:33:02 CST             59min     Mon 23:33:02 CST              6s ago    ipv6-update.timer
```

---

### 查看服务执行记录

```bash
systemctl status ipv6-update.service
```

或查看完整日志：

```bash
journalctl -u ipv6-update.service
```

最终效果如下，飞牛OS可自动更新前缀，有ipv6访问需求的可以设置静态ipv6满足需求。

![ScreenShot_2025-12-19_025141_489.png](IMG%2FScreenShot_2025-12-19_025141_489.png)

![ScreenShot_2025-12-19_025045_149.png](IMG%2FScreenShot_2025-12-19_025045_149.png)

## 八、设计原则说明（为什么这样做）

* 使用 **systemd timer 而非 crontab**

  * 更可靠
  * 更可观测
  * 与系统生命周期绑定
* 使用 **oneshot service**

  * 无常驻进程
  * 无资源浪费
* 使用 **绝对路径**

  * systemd / shell / 手动执行行为一致
* 前缀记录持久化

  * 方便排错
  * 可回溯历史变化

---

## 九、当前实现状态总结

✔ 开机自动运行
✔ 每小时自动检查
✔ 前缀变化自动更新 IPv6
✔ 日志清晰
✔ 结构稳定
✔ 可长期维护


