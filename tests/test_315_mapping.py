"""4.0.315 字段映射单测（不依赖 Home Assistant，可直接跑）。

覆盖三条回归点：
1. 315 的 homepage/sysstat 缺 cpu/memory/stream → 必须留空并记入
   data["missing"]，**绝不能写 0 / 空串**；
2. monitor_system / monitor_iface 新数据源的字段 → 正确单位换算（B/s→MB/s、
   B→GB、连接数）；
3. 314 旧结构与 315 新结构在两个方向上都不互相破坏。

运行： python -m unittest tests.test_315_mapping   （或直接 python tests/test_315_mapping.py）
"""
import asyncio
import importlib.util
import os
import sys
import types
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG_DIR = os.path.join(ROOT, "custom_components", "ikuai")


def _load_modules():
    """用 stub 绕过 homeassistant / aiohttp 依赖，只加载纯逻辑模块。"""
    async def _timeout(*_a, **_k):
        raise NotImplementedError

    stubs = {
        "async_timeout": {"timeout": _timeout},
        "aiohttp": {"ClientError": Exception},
        "homeassistant": {},
        "homeassistant.helpers": {},
        "homeassistant.helpers.aiohttp_client": {"async_get_clientsession": lambda *a, **k: None},
    }
    for name, attrs in stubs.items():
        if name not in sys.modules:
            mod = types.ModuleType(name)
            for key, value in attrs.items():
                setattr(mod, key, value)
            sys.modules[name] = mod

    pkg = types.ModuleType("ikuai_pkg")
    pkg.__path__ = [PKG_DIR]
    sys.modules["ikuai_pkg"] = pkg

    def load(mod_name):
        full = f"ikuai_pkg.{mod_name}"
        spec = importlib.util.spec_from_file_location(
            full, os.path.join(PKG_DIR, mod_name + ".py"))
        module = importlib.util.module_from_spec(spec)
        sys.modules[full] = module
        spec.loader.exec_module(module)
        return module

    load("const")
    return load("data_fetcher")


df = _load_modules()


# ---------------------------------------------------------------- fixtures
def _sysstat_315():
    """实测（4.0.315-beta x64 Build202610291837）homepage TYPE=sysstat,ac_status。"""
    return {
        "code": 0,
        "results": {
            "sysstat": {
                "boot_time": "2026-10-29 18:37:21",
                "hostname": "iKuai",
                "link_status": "online",
                "timestamp": 1793763749,
                "uptime": 431000,
                "verinfo": {
                    "verstring": "4.0.315-beta x64 Build202610291837",
                    "version": "4.0.315-beta",
                    "build_date": 202610291837,
                    "sysbit": "x64",
                    "arch": "x86",
                    "modelname": "iKuai",
                },
            },
            "ac_status": {"ap_online": 0},
        },
    }


def _sysstat_314():
    """4.0.314 的旧结构（cpu/memory/stream/online_user 齐全）。"""
    return {
        "code": 0,
        "results": {
            "sysstat": {
                "hostname": "iKuai",
                "uptime": 500000,
                "verinfo": {"verstring": "4.0.314 x64 Build202610131658",
                            "version": "4.0.314", "build_date": 202610131658},
                "cpu": ["23%", "18%", "27%"],
                "freq": ["2200", "2200"],
                "cputemp": [42],
                "memory": {"used": "37", "total": "8192000", "available": "5000000"},
                "online_user": {"count": 12},
                "stream": {"connect_num": 321, "upload": 1572864, "download": 3145728,
                           "total_up": 1073741824 * 3, "total_down": 1073741824 * 7},
            },
            "ac_status": {"ap_online": 2},
        },
    }


def _monitor_system_315():
    """实测 monitor_system（无 TYPE）：约 25 点采样序列，取最新一条。"""
    return {
        "code": 0,
        "results": {
            "data": [
                {"timestamp": 1793750000, "cpu": 60.0, "memory_use": 40,
                 "cputemp1": 0, "conn_num": 200, "on_terminal": 10},
                {"timestamp": 1793763749, "cpu": 96.72, "memory_use": 37,
                 "cputemp1": 0, "conn_num": 125, "on_terminal": 34},
            ]
        }
    }


def _monitor_iface_315():
    """实测 monitor_iface TYPE=iface_check,iface_stream（wan1 有数据，wan2 为 --）。"""
    return {
        "code": 0,
        "results": {
            "iface_check": [
                {"interface": "wan1", "result": "success", "isp": "电信"},
                {"interface": "wan2", "result": "--", "isp": "--"},
            ],
            "iface_stream": [
                {"interface": "wan1", "upload": 573256, "download": 121252,
                 "total_up": 385315994, "total_down": 388151129, "connect_num": 125},
                {"interface": "wan2", "upload": "--", "download": "--",
                 "total_up": "--", "total_down": "--", "connect_num": "--"},
            ],
        }
    }


class FakeFetcher:
    """只替换网络请求，其余走真实 DataFetcher 逻辑。"""

    def __init__(self, responses):
        fetcher = object.__new__(df.DataFetcher)
        fetcher._host = "http://router"
        fetcher._unsupported = set()
        fetcher._ext_cache = {}
        fetcher._caps = {}
        fetcher._last_lan_total = None
        fetcher.requestpost_json = self._make_post(fetcher, responses)
        fetcher._header = lambda _sess: {}
        self.fetcher = fetcher

    @staticmethod
    def _make_post(fetcher, responses):
        async def post(_url, _headers, body):
            func = body.get("func_name")
            value = responses.get(func)
            return value() if callable(value) else value
        return post


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


class TestPureMapping(unittest.TestCase):
    def test_num_ignores_dashes(self):
        self.assertIsNone(df._num("--"))
        self.assertIsNone(df._num(""))
        self.assertIsNone(df._num(None))
        self.assertEqual(df._num("125"), 125)
        self.assertAlmostEqual(df._num("96.72"), 96.72)

    def test_latest_sample_picks_max_timestamp(self):
        rows = [{"timestamp": 3, "cpu": 1}, {"timestamp": 9, "cpu": 2},
                {"timestamp": 5, "cpu": 3}]
        self.assertEqual(df._latest_sample(rows)["cpu"], 2)
        self.assertEqual(df._latest_sample([]), {})

    def test_aggregate_units_and_skip_missing(self):
        agg = df._aggregate_iface_stream(
            _monitor_iface_315()["results"]["iface_stream"],
            _monitor_iface_315()["results"]["iface_check"])
        self.assertAlmostEqual(agg["upload"], round(573256 / 1024 / 1024, 3))
        self.assertAlmostEqual(agg["download"], round(121252 / 1024 / 1024, 3))
        self.assertAlmostEqual(agg["total_up"], round(385315994 / 1024 ** 3, 2))
        self.assertAlmostEqual(agg["total_down"], round(388151129 / 1024 ** 3, 2))
        self.assertEqual(agg["connect_num"], 125)
        # 全部为 "--" → 取不到，必须返回 None（调用方置 unavailable，而不是 0）
        self.assertIsNone(df._aggregate_iface_stream(
            [{"interface": "wan2", "upload": "--"}]))

    def test_wan_line_online_multi_level(self):
        from ikuai_pkg.const import wan_line_online  # noqa: E402
        # 实测：vlan_internet=2 但是停用且没有 IP，不能算在线
        self.assertFalse(wan_line_online(
            {"vlan_internet": 2, "enabled": "no", "pppoe_ip_addr": "", "pppoe_updatetime": 0}))
        self.assertTrue(wan_line_online(
            {"vlan_internet": 2, "enabled": "yes", "pppoe_ip_addr": "1.2.3.4",
             "pppoe_updatetime": 1793760000}))
        self.assertTrue(wan_line_online({"vlan_internet": 1, "enabled": "yes"}))
        self.assertFalse(wan_line_online({"vlan_internet": 0, "enabled": "no"}))


class TestStatusMapping(unittest.TestCase):
    def test_315_missing_fields_stay_none(self):
        fake = FakeFetcher({"homepage": _sysstat_315()})
        data = {"ext": {}}
        _run(fake.fetcher._get_ikuai_status("sess", data, data["ext"]))
        for key in ("ikuai_cpu", "ikuai_memory", "ikuai_cputemp", "ikuai_online_user",
                    "ikuai_connect_num", "ikuai_upload", "ikuai_download",
                    "ikuai_total_up", "ikuai_total_down"):
            self.assertIsNone(data[key], f"{key} 缺字段时必须为 None，不能写 0")
            self.assertIn(key, data["missing"])
        self.assertIn("4.0.315", data["sw_version"])
        self.assertEqual(data["ikuai_version"], "4.0.315-beta")
        self.assertEqual(data["ext"]["firmware"]["build_date"], 202610291837)

    def test_314_old_structure_unchanged(self):
        fake = FakeFetcher({"homepage": _sysstat_314()})
        data = {"ext": {}}
        _run(fake.fetcher._get_ikuai_status("sess", data, data["ext"]))
        self.assertEqual(data["ikuai_cpu"], "23")
        self.assertEqual(data["ikuai_memory"], "37")
        self.assertEqual(data["ikuai_online_user"], 12)
        self.assertEqual(data["ikuai_connect_num"], 321)
        self.assertEqual(data["ikuai_upload"], 1.5)
        self.assertEqual(data["ikuai_download"], 3.0)
        self.assertEqual(data["ikuai_total_up"], 3.0)
        self.assertEqual(data["ikuai_total_down"], 7.0)
        self.assertEqual(data["missing"], [])

    def test_new_sources_fill_missing(self):
        responses = {
            "homepage": _sysstat_315(),
            "monitor_system": _monitor_system_315(),
            "monitor_iface": _monitor_iface_315(),
        }
        fake = FakeFetcher(responses)
        fetcher = fake.fetcher
        data = {"ext": {}}
        _run(fetcher._get_ikuai_status("sess", data, data["ext"]))
        _run(fetcher._get_ikuai_system_monitor("sess", data, data["ext"]))
        _run(fetcher._get_ikuai_iface_stream("sess", data, data["ext"]))

        self.assertEqual(data["ikuai_cpu"], "96.72")
        self.assertEqual(data["ikuai_memory"], "37")
        self.assertAlmostEqual(data["ikuai_upload"], 0.547)
        self.assertEqual(data["ikuai_connect_num"], 125)
        # 在线终端仍为空：等 monitor_lanip 的 total（实时值）来补
        self.assertIsNone(data["ikuai_online_user"])
        self.assertEqual(data["ext"]["on_terminal"], 34)

        # 回退链 1：本轮 monitor_lanip.total（优先）
        fetcher._last_lan_total = 25
        fetcher._fill_online_user(data, data["ext"])
        self.assertEqual(data["ikuai_online_user"], 25)
        self.assertNotIn("ikuai_online_user", data["missing"])

        # 回退链 2：lanip 拿不到 → monitor_system.on_terminal
        data["ikuai_online_user"] = None
        data["missing"].append("ikuai_online_user")
        fetcher._last_lan_total = None
        fetcher._fill_online_user(data, data["ext"])
        self.assertEqual(data["ikuai_online_user"], 34)

        for key in ("ikuai_cpu", "ikuai_memory", "ikuai_upload", "ikuai_download",
                    "ikuai_total_up", "ikuai_total_down", "ikuai_connect_num",
                    "ikuai_online_user"):
            self.assertNotIn(key, data["missing"])
        self.assertTrue(fetcher._caps["monitor_system"]["ok"])
        self.assertTrue(fetcher._caps["monitor_iface"]["ok"])

    def test_source_failure_backs_off_and_falls_back(self):
        fake = FakeFetcher({"homepage": _sysstat_315(), "monitor_system": None,
                            "monitor_iface": None})
        fetcher = fake.fetcher
        data = {"ext": {}}
        _run(fetcher._get_ikuai_status("sess", data, data["ext"]))
        _run(fetcher._get_ikuai_system_monitor("sess", data, data["ext"]))
        state = fetcher._cap_state("monitor_system")
        self.assertFalse(state["ok"])
        self.assertEqual(state["fails"], 1)
        self.assertGreater(state["next"], 0)
        # 失败后进入退避：下一轮不再打接口，字段保持 unavailable
        before = fetcher._caps["monitor_system"]["next"]
        _run(fetcher._get_ikuai_system_monitor("sess", data, data["ext"]))
        self.assertEqual(fetcher._caps["monitor_system"]["fails"], 1)
        self.assertEqual(fetcher._caps["monitor_system"]["next"], before)
        self.assertIsNone(data["ikuai_cpu"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
