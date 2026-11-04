# 更新日志

## v1.1.1 · 适配 iKuai 4.0.315（全面复核取数路径）

### 为什么发这一版

iKuai **4.0.315 Build202610291837** 改了首页接口的返回结构：

- `homepage` + `TYPE=sysstat,ac_status` 在 315 上**只返回** `boot_time` /
  `hostname` / `link_status` / `timestamp` / `uptime` / `verinfo`；
  4.0.314 里的 `cpu`、`memory`、`stream`、`online_user`、`freq`、`cputemp`
  **全部消失**（只读实测，连测 3 次一致）；
- `TYPE=stream`、`TYPE=sys_info` 直接返回 `2007 unknown TYPE`；
- 新版把数据挪到了监控接口：`monitor_system`（cpu / memory / cputemp /
  conn_num / on_terminal）与 `monitor_iface`（`TYPE=iface_check,iface_stream`，
  每口实时速率、累计流量、连接数）。

旧代码在字段缺失时用 `get(..., 0)` / `get(..., "")` 兜底，于是 315 上升级后
`sensor.ikuai_upload`、`sensor.ikuai_download`、`sensor.ikuai_total_up`、
`sensor.ikuai_total_down`（以及连带 `connect_num`）**从正常值变成恒 0 且不再刷新**。
`total_up` / `total_down` 是累计量，长期统计曲线因此被一条平的 0 线覆盖。

### 改了什么

1. **换数据源 + 逐级回退**（`data_fetcher.py`）
   - `upload` / `download` / `total_up` / `total_down` / `connect_num`：
     优先 `monitor_iface` + `TYPE=iface_check,iface_stream`，只汇总
     `iface_check.result == "success"` 的在线 WAN（拿不到体检结果时退回 `wan*` 口）；
     汇总为空再退回 homepage `sysstat.stream`（314）。
   - `cpu` / `memory` / `cputemp`：优先 `monitor_system`（不带 TYPE，一次取全）；
     退回 homepage `sysstat`（314）。
   - `online_user`：优先 homepage `sysstat.online_user`（314），
     其次 `monitor_system.on_terminal`，再退回本轮 `monitor_lanip` 的 `total`（零新增请求）。
   - 314 及更早固件走 `sysstat` 时分支不触发，**请求量与原行为完全不变**。

2. **能力探测 + 缓存 + 指数退避**
   - 每个新数据源维护 `{ok, fails, next}`：成功即缓存并逐轮使用；
     失败按 30s → 60s → 120s → … → 600s 上限退避，期间不再打该接口
     （既避免每轮试错，也避免撞 315 的疑似限流）。
   - 退避状态可通过 `data["ext"]["data_sources"]` 查看。

3. **缺字段绝不写 0**
   - 本轮缺失的扁平键会被显式置 `None` 并记入 `data["missing"]`；
     对应实体 `available = False`（显示 **unavailable**，不是 0 / unknown）：
     `ikuai_cpu`、`ikuai_memory`、`ikuai_cputemp`、`ikuai_online_user`、
     `ikuai_upload`、`ikuai_download`、`ikuai_total_up`、`ikuai_total_down`、
     `ikuai_connect_num`；主指标缺失时聚合实体 `system_info` / `lan_info` 也置 unavailable。
   - `iface_stream` 的 `"--"` 一律按缺失处理，不当 0。

4. **版本读数修正**
   - 已安装版本改用 `homepage/sysstat.verinfo.version` + `verinfo.build_date`
     （315 上为 `4.0.315-beta` / `202610291837`），不再依赖升级后可能滞后的
     `upgrade.data.system_ver`。

5. **`update.ikuai_firmware` 不再自相矛盾**
   - `installed_version` 取 `verinfo`；`latest_version` 在
     `upgrade.data.new_system_ver` 与已装一致（版本号 + build 相同）时返回已装版本，
     即显示“已是最新”，不再出现 installed 4.0.314 / latest 4.0.315 的假升级提示。

6. **WAN 在线判定统一**
   - 新增 `const.wan_line_online()`，抓取层（多拨在线数）与实体层（线路在线二进制
     传感器）共用同一套多级判定：
     有 IP 且上线时间 > 0 → 在线；PPPoE 但无 IP → 离线；其余回退 `enabled`。
   - **注意**：315 实测 `vlan_internet` 是接入方式（2=PPPoE、1=DHCP、0=静态），
     **不是**在线状态（当前设备的 `wan1` 就是 `vlan_internet=2` 但 `enabled=no`
     且无 IP），因此不能把 `vlan_internet == 2` 直接当成 online。

7. **取数路径全面复核（315 只读实测）**
   - 仍可用：`lan`、`wan`(vlan_data)、`ipv6`、`arp`、`monitor_lanip`(含 total)、
     `dhcp_server/lease/static/acl`、`ac/pptp/l2tp_server`、`pppoe_server`、
     `upgrade`、`basic`、`hardwareinfo`、`irqbalance`、`upgrade`、`webuser`、
     `ikmessages`、`monitor_app_flow`、12 类日志（`syslog-*` / `audit_im_log`）等。
   - 315 返回 `1003 Access denied`：`docker_container`、`rt_collect`、
     `ipgroup` / `macgroup` / `dtgroup` / `ipv6group`（详见对照矩阵文档，标为
     “未证”，可能是会话权限而非固件回归）。

### ⚠️ 行为变化（会改变已有实体，升级前请读）

1. 当 `monitor_system` / `monitor_iface` 都取不到时，上述实体**从“0”变成
   `unavailable`**。如果你的自动化用 `numeric_state below:` 之类条件，
   `unavailable` 不参与状态判断；历史统计曲线在 unavailable 期间不会写点。
2. `total_up` / `total_down` 恢复为真实累计值（此前 315 上恒 0），
   HA 长期统计会从 0 跳回真实量级，属正常现象。
3. `update.ikuai_firmware` 在 315 上会显示“已是最新”（因为确实已装 4.0.315），
   不再提示升到 4.0.314 的“新版本”。
4. 多拨在线数可能变化：PPPoE 线路必须有 IP 且上线时间 > 0 才算在线，
   停用但 `vlan_internet=2` 的线路不再被误计为在线。
5. `sensor.ikuai_cpu` / `memory` 的值来自 `monitor_system` 的采样序列
   （实测约 25 点、30 分钟一个点，取最新一条），属于**准实时**，
   与旧 `sysstat` 的秒级读数相比刷新粒度更粗。

### 验证

- `py_compile` 通过（`data_fetcher.py`、`sensor.py`、`const.py`、`update.py`、`__init__.py`）；
- `tests/test_315_mapping.py`：8 个用例全过，覆盖「缺字段 → None/unavailable」、
  「315 新源字段 → MB/s、GB、连接数换算」、「314 旧结构不回退」、
  「数据源失败进入退避且不再打接口」、「WAN 在线多级判定」；
- 315 只读实测（120+ 个接口/字段组合），矩阵见 `ikuai-4.0.315-适配对照矩阵.md`。

### 未验证

- **未在真实 HA 实例上跑一轮**（本轮只做只读接口探测与离线单测）；
- `1003 Access denied` 的那几个接口；
- `monitor_system` 的 30 分钟采样间隔在别的 315 设备上是否一致。
