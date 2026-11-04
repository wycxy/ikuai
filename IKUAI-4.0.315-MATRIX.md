# iKuai 4.0.315 取数路径对照矩阵（314 → 315）

> 环境：iKuai 4.0.315-beta x64 Build202610291837（`verinfo.version` / `verinfo.build_date`）。
> 方法：通过 HA 同源反代（`/ikuai/web/Action/call`）做**只读** `show` 探测，每个 func_name/TYPE 组合实打实发一次请求并记录返回结构；无写操作、未改路由器配置。
> 标注：**实测** = 本轮真实返回；**代码推断** = 由返回结构反推代码路径；**未证** = 没拿到证据（会写明卡在哪）。

## 一、结论速览

| 结论 | 数量 | 说明 |
|---|---|---|
| 结构变化、已适配 | 3 | homepage/sysstat 缺字段；monitor_system、monitor_iface 为新来源 |
| 已移除 | 2 | `TYPE=stream`、`TYPE=sys_info` → 2007 |
| 未证（1003） | 6 | docker_container、rt_collect、4 个 `*group` 表 |
| 其余 | 约 110 | 结构未变，原样可用 |

## 二、逐项矩阵

### 主轮询

| 探测项 | func_name / TYPE | 315 结果 | 结论 | 备注 |
|---|---|---|---|---|
| core.homepage.sysstat | `homepage` {"TYPE": "sysstat,ac_status"} | code=0 | 结构变化·已适配 | 只回 boot_time/hostname/link_status/timestamp/uptime/verinfo；cpu/memory/stream/online_user/freq/cputemp 全部缺失（连测 3 次一致） |
| core.lan.ether | `lan` {"TYPE": "ether_info,snapshoot"} | code=0 | 可用·结构不变 | ether_info / snapshoot_lan / snapshoot_wan 都在；行: snapshoot_lan(1行)、snapshoot_wan(2行) |
| core.wan.vlan | `wan` {"TYPE": "vlan_data,vlan_total", "limit": "0,100"} | code=0 | 可用·语义需注意 | vlan_data 字段齐全；但 vlan_internet 是接入方式（2=PPPoE、1=DHCP、0=静态），不是在线状态；行: vlan_data(3行) |
| core.ipv6.lan | `ipv6` {"TYPE": "lan_data,lan_total"} | code=0 | 可用·结构不变 | 行: lan_data(1行) |
| core.ipv6.wan | `ipv6` {"TYPE": "data,total"} | code=0 | 可用·结构不变 | 行: data(1行) |
| core.acl_mac | `acl_mac` {"TYPE": "total,data", "limit": "0,100"} | code=0 | 可用·结构不变 | 行: data(4行) |
| core.pptp | `pptp_client` {"TYPE": "total,data", "limit": "0,100", "ORDER_BY": "", "ORDER": ""} | code=0 | 可用·结构不变 |  |
| core.l2tp | `l2tp_client` {"TYPE": "total,data", "limit": "0,100", "ORDER_BY": "", "ORDER": ""} | code=0 | 可用·结构不变 |  |
| core.lanip | `monitor_lanip` {"TYPE": "data,total", "limit": "0,100"} | code=0 | 可用·已复用 | data/total 正常；total 被用作 online_user 回退（零新增请求）；行: data(25行) |
| core.lanipv6 | `monitor_lanipv6` {"TYPE": "data,total", "limit": "0,100"} | code=0 | 可用·结构不变 | 行: data(8行) |
| core.arp_options | `arp` {"TYPE": "options"} | code=0 | 可用·结构不变 | arp_filter / arp_filter_iface / dhcpd_arp |
| core.stream_control | `stream_control` {"TYPE": "stream_ctl_mode"} | code=0 | 可用·结构不变 | 行: stream_ctl_mode(1行) |
| new.monitor_system | `monitor_system` {"TYPE": "cpu,memory"} | code=0 | 新增数据源·已接入 | 不带 TYPE 一次返回 data 采样序列（约 25 点/30 分钟一点），取最新一条；TYPE=cpu,memory 也可用。**准实时，不是秒级**；行: cpu(25行)、memory(25行) |
| new.monitor_iface | `monitor_iface` {"TYPE": "iface_check,iface_stream"} | code=0 | 新增数据源·已接入 | iface_check + iface_stream：每口 upload/download(B/s)、total_up/down(B)、connect_num；实测每次请求数值都在变（实时）；行: iface_check(2行)、iface_stream(3行) |
| new.sysstat_stream | `homepage` {"TYPE": "stream"} | code=2007 | 已移除 | 2007 unknown TYPE：旧的 TYPE=stream 在 315 不再存在 |
| new.sysstat_sysinfo | `homepage` {"TYPE": "sys_info"} | code=2007 | 已移除 | 2007 unknown TYPE |

### 系统 / 设置

| 探测项 | func_name / TYPE | 315 结果 | 结论 | 备注 |
|---|---|---|---|---|
| ext.basic | `basic` {"TYPE": "timestamp,data,interface,support_fast"} | code=0 | 可用·结构不变 | 行: data(1行) |
| ext.advanced | `advanced` {} | code=0 | 可用·结构不变 | 行: data(1行) |
| ext.sysctl | `ik_sysctl` {"TYPE": "data"} | code=0 | 可用·结构不变 | 行: data(1行) |
| ext.watchdog | `watchdog` {} | code=0 | 可用·结构不变 | 行: data(1行) |
| ext.hardware | `hardwareinfo` {} | code=0 | 可用·结构不变 |  |
| ext.irq | `irqbalance` {"TYPE": "cpulist,freqlist"} | code=0 | 可用·可作 freq 来源 | current_cpufreq + cpulist + cpufreq_list；扩展轮询每 3 轮一次，未强行拉进主轮询 |
| ext.disk | `disk_mgmt` {"TYPE": "data"} | code=0 | 可用·结构不变 | 行: data(1行) |
| ext.remote | `remote_control` {} | code=0 | 可用·结构不变 | 行: data(1行) |
| ext.webuser | `webuser` {"TYPE": "data", "limit": "0,100"} | code=0 | 可用·结构不变 | 行: data(1行) |
| ext.upgrade | `upgrade` {"TYPE": "auto_upgrade,data,fileinfo"} | code=0 | 可用·读数已修正 | 本次实测 data.system_ver=4.0.315、new_system_ver=4.0.315、build 202610291837，已与 verinfo 一致；集成仍以 verinfo 为准 |
| ext.register | `register` {"TYPE": "data,gwid"} | code=0 | 可用·结构不变 | 行: data(1行) |
| ext.backup | `backup` {"TYPE": "data"} | code=0 | 可用·结构不变 | 行: data(1行) |

### 服务

| 探测项 | func_name / TYPE | 315 结果 | 结论 | 备注 |
|---|---|---|---|---|
| svc.netsnmp | `netsnmp` {} | code=0 | 可用·结构不变 | 行: data(1行) |
| svc.smbd | `smbd` {"TYPE": "data"} | code=0 | 可用·结构不变 | 行: data(1行) |
| svc.ftp | `ftp_server` {"TYPE": "ftp_status"} | code=0 | 可用·结构不变 |  |
| svc.upnpd | `upnpd` {"TYPE": "interface_wan,data"} | code=0 | 可用·结构不变 | 行: data(1行) |
| svc.webauth | `webauth` {"TYPE": "data,sync_interface,template"} | code=0 | 可用·结构不变 | 行: data(1行) |
| svc.alg | `alg` {"TYPE": "data"} | code=0 | 可用·结构不变 | 行: data(1行) |
| svc.igmp | `igmp_proxy` {"TYPE": "data,lan_interface,wan_interface"} | code=0 | 可用·结构不变 | 行: data(1行) |
| svc.iptv | `iptv` {"TYPE": "data,ether_info"} | code=0 | 可用·结构不变 | 行: data(1行) |
| svc.audit | `audit` {"TYPE": "data"} | code=0 | 可用·结构不变 | 行: data(1行) |
| svc.cflow | `cflow` {} | code=0 | 可用·结构不变 |  |
| svc.wuying | `wuying` {"TYPE": "data,interface", "limit": "0,100"} | code=0 | 可用·结构不变 | 行: data(1行) |
| svc.web_cache | `ik_web_cache` {"TYPE": "data,status", "object": "service", "service": "data,video"} | code=0 | 可用·结构不变 | 行: status(2行) |

### 网络 / DHCP / 路由 / 终端

| 探测项 | func_name / TYPE | 315 结果 | 结论 | 备注 |
|---|---|---|---|---|
| net.wan_bands | `wan` {"TYPE": "data,total", "limit": "0,100"} | code=0 | 可用·结构不变 | 行: data(2行) |
| net.arp | `arp` {"TYPE": "total,data", "ORDER_BY": "ip_addr_int", "orderType": "IP", "ORDER": "asc", "limit": "0,100"} | code=0 | 可用·结构不变 | 行: data(25行) |
| net.dhcp_server | `dhcp_server` {"TYPE": "total,data", "limit": "0,100"} | code=0 | 可用·结构不变 | 行: data(1行) |
| net.dhcp_lease | `dhcp_lease` {"TYPE": "data,total", "ORDER_BY": "timeout", "ORDER": "desc", "limit": "0,100"} | code=0 | 可用·结构不变 | 行: data(21行) |
| net.dhcp6_lease | `dhcp6_lease` {"TYPE": "client_list,client_total", "ORDER_BY": "expires", "ORDER": "desc", "limit": "0,100"} | code=0 | 可用·字段名不同 | 返回 client_data/client_total（代码已兼容 client_list 两套字段名）；行: client_data(3行) |
| net.dhcp_static | `dhcp_static` {"TYPE": "static_total,static_data,dhcpd_arp", "limit": "0,100"} | code=0 | 可用·结构不变 | 行: static_data(49行) |
| net.dhcp_acl | `dhcp_acl_mac` {"TYPE": "total,data,dhcp_acl_mac", "limit": "0,100"} | code=0 | 可用·结构不变 |  |
| net.dhcp6_acl | `dhcp6_acl_mac` {"TYPE": "total,data,dhcp6_acl_mac", "limit": "0,100"} | code=0 | 可用·结构不变 |  |
| net.static_rt4 | `static_rt_table` {"TYPE": "data,total", "limit": "0,100"} | code=0 | 可用·结构不变 | 行: data(4行) |
| net.static_rt6 | `static_rt_table` {"TYPE": "data6,total6", "limit": "0,100"} | code=0 | 可用·结构不变 | 行: data(5行) |
| net.ipv6_neighbor | `ipv6_neighbor` {"TYPE": "data,total", "ORDER_BY": "id", "ORDER": "desc", "limit": "0,100"} | code=0 | 可用·结构不变 | 行: data(13行) |
| biz.terminal_flow | `monitor_lanip` {"TYPE": "terminal_flow", "limit": "0,100", "ORDER_BY": "", "ORDER": ""} | code=0 | 条件性·需参数 | 必须带 ip，否则返回 code=3001 的内层错误（314 同样如此），属预期 |

### 业务 / 设备

| 探测项 | func_name / TYPE | 315 结果 | 结论 | 备注 |
|---|---|---|---|---|
| biz.docker | `docker_container` {"TYPE": "data,network,image,cpuused,memavailable,sysbit"} | code=1003 | 未证·1003 Access denied | 只读探测返回 1003；可能是会话权限（非管理员账号）而非 315 回归，需在真实集成会话下复核 |
| biz.qemu | `qemu` {"TYPE": "total,data", "limit": "0,100"} | code=0 | 可用·结构不变 |  |
| biz.ac | `ac_server` {"TYPE": "total,data", "limit": "0,100"} | code=0 | 可用·结构不变 |  |
| biz.camera | `camera` {"TYPE": "total,data", "limit": "0,100"} | code=0 | 可用·结构不变 |  |
| biz.wakeup | `wakeup` {"TYPE": "total,data", "limit": "0,100"} | code=0 | 可用·结构不变 |  |
| biz.ppp_online | `ppp_online` {"TYPE": "data,total", "limit": "0,100"} | code=0 | 可用·结构不变 |  |
| biz.pppuser | `pppuser` {"TYPE": "total,data", "limit": "0,100"} | code=0 | 可用·结构不变 |  |
| biz.pppoe_server | `pppoe_server` {"TYPE": "data"} | code=0 | 可用·结构不变 | 行: data(1行) |
| biz.pptp_server | `pptp_server` {} | code=0 | 可用·结构不变 | 行: data(1行) |
| biz.l2tp_server | `l2tp_server` {} | code=0 | 可用·结构不变 | 行: data(1行) |
| biz.openvpn_server | `openvpn-server` {"TYPE": "data,status"} | code=0 | 可用·结构不变 | 行: data(1行) |
| biz.messages | `ikmessages` {"TYPE": "total,data", "ORDER_BY": "id", "ORDER": "desc", "limit": "0,10"} | code=0 | 可用·结构不变 |  |
| biz.messages_unread | `ikmessages` {"TYPE": "total", "FILTER1": "read,==,0"} | code=0 | 可用·结构不变 |  |
| biz.rt_collect | `rt_collect` {"TYPE": "warning_notify,data,total", "ORDER_BY": "id", "ORDER": "desc", "limit": "0,100"} | code=1003 | 未证·1003 Access denied | 同上；集成里该模块取不到时按空处理 |
| biz.app_flow30 | `homepage` {"TYPE": "app_flow", "minute": 30} | code=0 | 可用·结构不变 |  |
| biz.app_flow60 | `homepage` {"TYPE": "app_flow", "minute": 60} | code=0 | 可用·结构不变 |  |
| biz.app_flow1440 | `homepage` {"TYPE": "app_flow", "minute": 1440} | code=0 | 可用·结构不变 |  |
| biz.monitor_app_flow | `monitor_app_flow` {"TYPE": "flow", "limit": "0,15"} | code=0 | 可用·结构不变 |  |
| biz.audit_url_log | `audit_url_log` {"TYPE": "data", "limit": "0,100", "ORDER_BY": "timestamp", "ORDER": "desc"} | code=0 | 可用·结构不变 | 行: data(100行) |
| biz.audit_terminal_log | `audit_terminal_log` {"TYPE": "data", "limit": "0,100", "ORDER_BY": "id", "ORDER": "desc"} | code=0 | 可用·结构不变 | 行: data(100行) |

### 规则表计数

| 探测项 | func_name / TYPE | 315 结果 | 结论 | 备注 |
|---|---|---|---|---|
| count.acl | `acl` {"TYPE": "total,data", "limit": "0,10"} | code=0 | 可用·结构不变 | 行: data(1行) |
| count.conn_limit | `conn_limit` {"TYPE": "total,data", "limit": "0,10"} | code=0 | 可用·结构不变 | 行: data(1行) |
| count.acl_l7 | `acl_l7` {"TYPE": "total,data", "limit": "0,10"} | code=0 | 可用·结构不变 | 行: data(1行) |
| count.acl_qq | `acl_qq` {"TYPE": "total,data", "limit": "0,10"} | code=0 | 可用·结构不变 |  |
| count.dnat | `dnat` {"TYPE": "total,data", "limit": "0,10"} | code=0 | 可用·结构不变 | 行: data(10行) |
| count.nat_rule | `nat_rule` {"TYPE": "total,data", "limit": "0,10"} | code=0 | 可用·结构不变 |  |
| count.static_rt | `static_rt` {"TYPE": "total,data", "limit": "0,10"} | code=0 | 可用·结构不变 |  |
| count.vlan | `vlan` {"TYPE": "total,data", "limit": "0,10"} | code=0 | 可用·结构不变 |  |
| count.stream_ipport | `stream_ipport` {"TYPE": "total,data", "limit": "0,10"} | code=0 | 可用·结构不变 | 行: data(6行) |
| count.stream_layer7 | `stream_layer7` {"TYPE": "total,data", "limit": "0,10"} | code=0 | 可用·结构不变 |  |
| count.stream_domain | `stream_domain` {"TYPE": "total,data", "limit": "0,10"} | code=0 | 可用·结构不变 |  |
| count.stream_updown | `stream_updown` {"TYPE": "total,data", "limit": "0,10"} | code=0 | 可用·结构不变 |  |
| count.simple_qos | `simple_qos` {"TYPE": "total,data", "limit": "0,10"} | code=0 | 可用·结构不变 | 行: data(1行) |
| count.mac_qos | `mac_qos` {"TYPE": "total,data", "limit": "0,10"} | code=0 | 可用·结构不变 |  |
| count.alone_limit | `alone_limit` {"TYPE": "total,data", "limit": "0,10"} | code=0 | 可用·结构不变 |  |
| count.high_prio_host | `high_prio_host` {"TYPE": "total,data", "limit": "0,10"} | code=0 | 可用·结构不变 |  |
| count.dprotos | `dprotos` {"TYPE": "total,data", "limit": "0,10"} | code=0 | 可用·结构不变 |  |
| count.dprotos_l7 | `dprotos_l7` {"TYPE": "total,data", "limit": "0,10"} | code=0 | 可用·结构不变 |  |
| count.port_mirror | `port_mirror` {"TYPE": "total,data", "limit": "0,10"} | code=0 | 可用·结构不变 |  |
| count.udp_proxy | `udp_proxy` {"TYPE": "total,data", "limit": "0,10"} | code=0 | 可用·结构不变 |  |
| count.lb_pcc | `lb_pcc` {"TYPE": "total,data", "limit": "0,10"} | code=0 | 可用·结构不变 | 行: data(1行) |
| count.custom_isp | `custom_isp` {"TYPE": "total,data", "limit": "0,10"} | code=0 | 可用·结构不变 |  |
| count.upnpd_leases | `upnpd_leases` {"TYPE": "total,data", "limit": "0,10"} | code=0 | 可用·结构不变 |  |
| count.dev_control | `dev_control` {"TYPE": "total,data", "limit": "0,10"} | code=0 | 可用·结构不变 |  |
| count.cloud_switch | `cloud_switch` {"TYPE": "total,data", "limit": "0,10"} | code=0 | 可用·结构不变 |  |
| count.wakeup_list | `wakeup` {"TYPE": "total,data", "limit": "0,10"} | code=0 | 可用·结构不变 |  |
| count.coupon | `coupon` {"TYPE": "total,data", "limit": "0,10"} | code=0 | 可用·结构不变 |  |
| count.pppuser | `pppuser` {"TYPE": "total,data", "limit": "0,10"} | code=0 | 可用·结构不变 |  |
| count.ipgroup | `ipgroup` {"TYPE": "total,data", "limit": "0,10"} | code=1003 | 未证·1003 Access denied | 同上（ipgroup/macgroup/dtgroup/ipv6group 四个分组表全部 1003） |
| count.macgroup | `macgroup` {"TYPE": "total,data", "limit": "0,10"} | code=1003 | 未证·1003 Access denied | 同上 |
| count.dtgroup | `dtgroup` {"TYPE": "total,data", "limit": "0,10"} | code=1003 | 未证·1003 Access denied | 同上 |
| count.ipv6group | `ipv6group` {"TYPE": "total,data", "limit": "0,10"} | code=1003 | 未证·1003 Access denied | 同上 |
| count.domain_blacklist | `domain_blacklist` {"TYPE": "total,data", "limit": "0,10"} | code=0 | 可用·结构不变 |  |
| count.dns | `dns` {"TYPE": "dns_proxy,dns_proxy_total", "limit": "0,10"} | code=0 | 可用·结构不变 | 行: data(1行) |
| count.dns_replace | `dns_replace` {"TYPE": "data,total", "limit": "0,10"} | code=0 | 可用·结构不变 |  |
| count.url_keywords | `url_keywords` {"TYPE": "data,total", "limit": "0,10"} | code=0 | 可用·结构不变 |  |
| count.url_redirect | `url_redirect` {"TYPE": "data,total", "limit": "0,10"} | code=0 | 可用·结构不变 |  |
| count.url_replace | `url_replace` {"TYPE": "data,total", "limit": "0,10"} | code=0 | 可用·结构不变 |  |

### 日志

| 探测项 | func_name / TYPE | 315 结果 | 结论 | 备注 |
|---|---|---|---|---|
| log.system | `syslog-sysevent` {"TYPE": "total,data", "ORDER_BY": "id", "ORDER": "desc", "limit": "0,10"} | code=0 | 可用·结构不变 | 行: data(10行) |
| log.webadmin | `syslog-webadmin` {"TYPE": "total,data", "ORDER_BY": "id", "ORDER": "desc", "limit": "0,10"} | code=0 | 可用·结构不变 | 行: data(10行) |
| log.pppauth | `syslog-pppauth` {"TYPE": "total,data", "ORDER_BY": "id", "ORDER": "desc", "limit": "0,10"} | code=0 | 可用·结构不变 |  |
| log.arp | `syslog-arp` {"TYPE": "total,data", "ORDER_BY": "id", "ORDER": "desc", "limit": "0,10"} | code=0 | 可用·结构不变 | 行: data(10行) |
| log.apaction | `syslog-apaction` {"TYPE": "total,data", "ORDER_BY": "id", "ORDER": "desc", "limit": "0,10"} | code=0 | 可用·结构不变 |  |
| log.dhcpd | `syslog-dhcpd` {"TYPE": "total,data", "ORDER_BY": "id", "ORDER": "desc", "limit": "0,10"} | code=0 | 可用·结构不变 | 行: data(10行) |
| log.ddns | `syslog-ddns` {"TYPE": "total,data", "ORDER_BY": "id", "ORDER": "desc", "limit": "0,10"} | code=0 | 可用·结构不变 | 行: data(10行) |
| log.wanpppoe | `syslog-wanpppoe` {"TYPE": "total,data", "ORDER_BY": "id", "ORDER": "desc", "limit": "0,10"} | code=0 | 可用·结构不变 | 行: data(10行) |
| log.notice | `syslog-notice` {"TYPE": "total,data", "ORDER_BY": "id", "ORDER": "desc", "limit": "0,10"} | code=0 | 可用·结构不变 |  |
| log.im_log | `audit_im_log` {"TYPE": "total,data", "ORDER_BY": "id", "ORDER": "desc", "limit": "0,10"} | code=0 | 可用·结构不变 | 行: data(10行) |

## 三、315 上真正改了什么（实测）

1. **`homepage` 的 `sysstat` 被瘦身**：只剩元数据（boot_time/hostname/link_status/timestamp/uptime/verinfo）。CPU、内存、温度、频率、在线终端、流量、连接数全部不在这个响应里了。

2. **`TYPE=stream` / `TYPE=sys_info` 被删除**：返回 `2007 unknown TYPE`，说明不是字段改名，而是这两个 TYPE 整体下线。

3. **数据搬到监控接口**：
   - `monitor_system`（无 TYPE）→ `data`：cpu、memory、memory_use、cputemp1/2、conn_num、on_terminal、wired/wireless_terminal、rx/tx packages 等；**采样序列，约 30 分钟一个点**；
   - `monitor_iface` `TYPE=iface_check,iface_stream` → 每口实时 upload/download（B/s）、total_up/total_down（B）、connect_num；**实测每次请求都在变**。

4. **`upgrade.data` 本身没坏**：本次实测 `system_ver` 已经是 4.0.315，但升级刚完成时它可能还写 4.0.314 —— 版本读数改以 `verinfo` 为准，不再依赖它。

5. **`vlan_internet` 不是在线状态**：实测 3 条线路取值为 2/0/1，分别对应 PPPoE/静态/DHCP；`wan1` 是 `vlan_internet=2` 且 `enabled=no`、无 IP。把 2 当在线会误判。

6. **列表类接口（DHCP / ARP / 路由 / 终端 / 日志 / 规则计数）结构未变**，12 类日志全部可用。

## 四、没拿到证据的项目

- `docker_container`、`rt_collect`、`ipgroup`/`macgroup`/`dtgroup`/`ipv6group`：只读探测统一返回 `1003 Access denied`。**卡在**：探测使用的是 HA 反代会话（非集成本身的登录会话），无法区分「315 收紧了权限」还是「该会话权限不足」。需要：在真实集成会话（管理员账号）下再跑一次同名请求，或提供一次 315 下的抓包。

- `monitor_system` 的采样间隔：只在这台设备上观察到约 30 分钟一点（25 点覆盖约 24h）。**未证** 其它 315 设备是否相同；因此集成把它当“准实时”，并在取不到时回退 homepage/unavailable。

- `biz.terminal_flow`：必须带 `ip` 参数，否则返回内层 code=3001（314 行为一致），不构成回归，但本轮没有逐台终端去验证。
