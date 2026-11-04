"""iKuai 固件更新实体（HA 设备页原生「有更新」提示）。

只展示版本信息，不提供一键升级（固件升级是高风险操作，统一在爱快后台执行）。
数据来自 ext.upgrade.data（每次扩展轮询抓取，无新接口）。
"""
from homeassistant.components.update import UpdateEntity

from .const import COORDINATOR, DOMAIN
from .entity import IKuaiEntity, category


async def async_setup_entry(hass, config_entry, async_add_entities):
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]
    async_add_entities([IKuaiFirmwareUpdate(coordinator)], False)


class IKuaiFirmwareUpdate(IKuaiEntity, UpdateEntity):
    """固件版本：当前版本 / 最新版本 / 更新说明。"""

    _attr_icon = "mdi:package-up"

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_entity_category = category("config")
        # 固定英文实体 ID：update.ikuai_firmware
        self._setup_forced_entity_id("update", "firmware")

    @property
    def name(self):
        return "固件更新"

    @property
    def unique_id(self):
        return f"{DOMAIN}_firmware_{self.coordinator.host}"

    def _data(self) -> dict:
        block = (self.coordinator.data or {}).get("ext", {}).get("upgrade") or {}
        return block.get("data") if isinstance(block, dict) else None

    def _verinfo(self) -> dict:
        """已安装固件的真实版本（315 起以 homepage/sysstat 的 verinfo 为准）。

        ``upgrade.data.system_ver`` 在 4.0.315 上升级后仍可能滞后于实际
        （曾出现 verinfo=4.0.315、system_ver=4.0.314 的自相矛盾），所以
        installed_version 优先用 verinfo.version + verinfo.build_date。
        """
        info = (self.coordinator.data or {}).get("ext", {}).get("verinfo") or {}
        return info if isinstance(info, dict) else {}

    @staticmethod
    def _fmt(ver, build):
        if ver and build:
            return f"{ver} Build{build}"
        return ver or None

    def _installed_pair(self):
        data = self._data() or {}
        info = self._verinfo()
        ver = info.get("version") or data.get("system_ver")
        build = info.get("build_date") or data.get("build_date")
        return ver, build

    def _same_release(self, new_ver, new_build):
        """新版本是否其实就是已安装的这一版（315 的 new_system_ver 会等于已装版）。"""
        cur_ver, cur_build = self._installed_pair()
        if new_ver and cur_ver and str(new_ver) != str(cur_ver):
            return False
        if new_build and cur_build:
            return str(new_build) == str(cur_build)
        return bool(new_ver) and str(new_ver) == str(cur_ver)

    @property
    def installed_version(self):
        ver, build = self._installed_pair()
        return self._fmt(ver, build)

    @property
    def latest_version(self):
        data = self._data() or {}
        new_ver = data.get("new_system_ver")
        new_build = data.get("new_build_date")
        if not new_ver or self._same_release(new_ver, new_build):
            # 没有新版本（或“最新”与已装相同）时返回当前版本，HA 即显示「最新」
            return self.installed_version
        return self._fmt(new_ver, new_build)

    @property
    def release_summary(self):
        return (self._data() or {}).get("update_content") or None

    @property
    def extra_state_attributes(self):
        data = self._data() or {}
        info = self._verinfo()
        attrs = {
            "version_source": "verinfo" if info.get("version") else "upgrade.data",
            "verstring": info.get("verstring"),
            "build_date": info.get("build_date"),
            "upgrade_system_ver": data.get("system_ver"),
            "libproto_ver": data.get("libproto_ver"),
            "libaudit_ver": data.get("libaudit_ver"),
            "libdomain_ver": data.get("libdomain_ver"),
            "firmware_channel": data.get("firmware_channel"),
            "querytime": (self.coordinator.data or {}).get("querytime"),
        }
        return {k: v for k, v in attrs.items() if v not in ("", None)}
