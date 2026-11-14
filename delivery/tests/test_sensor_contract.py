"""Executable contract/regression cases; no physical GPIO or running Pi needed."""
import copy
import csv
import importlib.util
import io
import json
import os
from pathlib import Path
import statistics
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
RESULTS = Path(os.environ.get("EVIDENCE_OUTPUT_DIR", ROOT / "delivery/results"))
RESULTS.mkdir(parents=True, exist_ok=True)
os.environ["MEETING_DATA_MODE"] = "simulation"
_tmp = tempfile.TemporaryDirectory()
os.environ["MEETING_DATA_DIR"] = _tmp.name
spec = importlib.util.spec_from_file_location("sensors", ROOT / "Flask/unified_meeting_room_system.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
INITIAL = copy.deepcopy(m.devices)
records = []


class Contract(unittest.TestCase):
    def setUp(self):
        m.ON_RASPBERRY_PI = False
        m.devices = copy.deepcopy(INITIAL)
        m.history_data = []
        m.current_temp = m.current_humidity = m.current_distance = None
        m.last_dht_success = None
        m.door_servos = {}
        m.dht_device = None
        m.TEMP_MIN, m.TEMP_MAX, m.HUMIDITY_MIN, m.HUMIDITY_MAX = 20, 26, 40, 60
        self.client = m.app.test_client()

    def post(self, **data):
        return self.client.post("/api/control", json=data)

    def test_01_health(self):
        r = self.client.get("/api/health")
        self.assertEqual((r.status_code, r.json["service"], r.json["source"]), (200, "meeting-room-sensors", "simulation"))

    def test_02_partial_keeps_devices(self):
        r = self.client.get("/api/current")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json["quality"], "partial")
        self.assertIsNone(r.json["temperature"])
        self.assertIn("door_open", r.json["devices"])

    def test_03_missing_dht_never_fabricates(self):
        m.ON_RASPBERRY_PI = True
        self.assertEqual(m.read_dht_sensor(), (None, None))

    def test_04_hardware_not_simulated(self):
        m.ON_RASPBERRY_PI = True
        m.current_temp, m.current_humidity = 45.5, 8.0
        m.devices["cooling"] = True
        m.simulate_environment_by_devices()
        self.assertEqual((m.current_temp, m.current_humidity), (45.5, 8.0))

    def test_05_simulation_adjusts(self):
        m.current_temp, m.current_humidity = 25, 50
        m.devices["cooling"] = True
        m.simulate_environment_by_devices()
        self.assertEqual(m.current_temp, 24.8)

    def test_06_history_missing_is_null(self):
        m.append_history(None, None, None, False, 20, 20)
        self.assertIsNone(self.client.get("/api/history").json[0]["temperature"])

    def test_07_history_provenance(self):
        m.devices["door_open"] = True
        m.append_history(25, 50, 30, True, 20, 20)
        row = self.client.get("/api/history").json[0]
        self.assertEqual((row["source"], row["door_open"]), ("simulation", True))

    def test_08_empty_export(self):
        self.assertEqual(self.client.get("/api/export/csv").status_code, 503)

    def test_09_export_roundtrip(self):
        m.append_history(25, 50, 30, True, 20, 20)
        r = self.client.get("/api/export/csv")
        rows = list(csv.reader(io.StringIO(r.get_data(as_text=True))))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(rows[0][-2:], ["门指令状态", "数据来源"])
        self.assertEqual(rows[1][-1], "simulation")
        (RESULTS / "sample_export.csv").write_bytes(r.data)

    def test_10_nonobject_request(self):
        self.assertEqual(self.client.post("/api/control", json=[]).status_code, 400)

    def test_11_malformed_json(self):
        self.assertEqual(self.client.post("/api/control", data="{", content_type="application/json").status_code, 400)

    def test_12_unknown_action(self):
        self.assertEqual(self.post(action="reset-everything").status_code, 400)

    def test_13_unknown_device(self):
        self.assertEqual(self.post(action="manual", device="arbitrary", state=True).status_code, 400)

    def test_14_string_state_rejected(self):
        self.assertEqual(self.post(action="manual", device="door", state="false").status_code, 400)

    def test_15_negative_brightness(self):
        self.assertEqual(self.post(action="manual", device="lighting", state=True, brightness=-1).status_code, 400)

    def test_16_excess_brightness(self):
        self.assertEqual(self.post(action="manual", device="lighting", state=True, brightness=101).status_code, 400)

    def test_17_dim_light(self):
        r = self.post(action="manual", device="lighting", state=True, brightness=40)
        self.assertEqual(r.json["devices"]["lighting_brightness"], 40)

    def test_18_light_on(self):
        r = self.post(action="manual", device="lighting", state=True)
        self.assertTrue(r.json["devices"]["lighting"])

    def test_19_light_off(self):
        r = self.post(action="manual", device="lighting", state=False)
        self.assertEqual(r.json["devices"]["lighting_brightness"], 0)

    def test_20_door_open(self):
        r = self.post(action="manual", device="door", state=True)
        self.assertTrue(r.json["devices"]["door_open"])
        self.assertEqual(r.json["door_state_kind"], "commanded")

    def test_21_door_close(self):
        m.devices["door_open"] = True
        self.assertFalse(self.post(action="manual", device="door", state=False).json["devices"]["door_open"])

    def test_22_unavailable_servo(self):
        m.ON_RASPBERRY_PI = True
        r = self.post(action="manual", device="door", state=True)
        self.assertEqual(r.status_code, 503)
        self.assertFalse(m.devices["door_open"])

    def test_23_failed_pwm_no_success_state(self):
        m.ON_RASPBERRY_PI = True
        bad = Mock()
        bad.ChangeDutyCycle.side_effect = RuntimeError("test driver failure")
        m.door_servos = {"left": bad, "right": Mock()}
        self.assertEqual(self.post(action="manual", device="door", state=True).status_code, 503)
        self.assertFalse(m.devices["door_open"])

    def test_24_auto_toggle(self):
        self.assertFalse(self.post(action="set_auto", enabled=False).json["devices"]["auto_mode"])

    def test_25_auto_bool_validation(self):
        self.assertEqual(self.post(action="set_auto", enabled="true").status_code, 400)

    def test_26_threshold_update(self):
        self.assertEqual(self.post(action="set_params", temp_min=18, temp_max=28).status_code, 200)
        self.assertEqual(m.TEMP_MIN, 18)

    def test_27_threshold_order(self):
        self.assertEqual(self.post(action="set_params", temp_min=30, temp_max=20).status_code, 400)

    def test_28_threshold_type(self):
        self.assertEqual(self.post(action="set_params", temp_min="hot").status_code, 400)

    def test_29_humidity_range(self):
        self.assertEqual(self.post(action="set_params", humidity_max=120).status_code, 400)

    def test_30_stale_sample(self):
        m.ON_RASPBERRY_PI = True
        m.current_temp, m.current_humidity, m.last_dht_success = 25, 50, time.time() - 30
        r = self.client.get("/api/current")
        self.assertEqual((r.json["quality"], r.json["sensor_status"]["climate"]), ("partial", "stale"))

    def test_31_alarm_priority(self):
        m.devices["alarm"] = True
        with patch.object(m, "set_rgb_color") as red, patch.object(m, "set_rgb_brightness") as white:
            m.apply_device_outputs()
            red.assert_called_once_with("red")
            white.assert_not_called()

    def test_32_dual_servo_output(self):
        m.ON_RASPBERRY_PI = True
        m.door_servos = {"left": Mock(), "right": Mock()}
        m.set_door_servo(True)
        for servo in m.door_servos.values():
            servo.ChangeDutyCycle.assert_called_once_with(m.SERVO_OPEN_DUTY)

    def test_53_health_freshness_and_scope(self):
        r = self.client.get('/api/health').json
        self.assertEqual(r['status'], 'degraded')
        self.assertIsNone(r['climate_sample_age_seconds'])
        self.assertGreaterEqual(r['uptime_seconds'], 0)
        self.assertIn('climate only', r['health_scope'])

    def test_54_health_stale_and_recovered(self):
        m.ON_RASPBERRY_PI = True
        m.current_temp, m.current_humidity = 24, 50
        m.last_dht_success = time.time() - 30
        self.assertEqual(self.client.get('/api/health').json['status'], 'degraded')
        m.last_dht_success = time.time()
        self.assertEqual(self.client.get('/api/health').json['status'], 'ok')

    def test_55_threshold_source(self):
        self.post(action='set_params', temp_max=29, humidity_min=45)
        data = self.client.get('/api/current').json
        self.assertEqual((data['temp_max'], data['humidity_min'], data['smoke_threshold']), (29, 45, m.SMOKE_THRESHOLD))


class EvidenceResult(unittest.TextTestResult):
    def startTest(self, test):
        self.started = time.perf_counter()
        super().startTest(test)

    def record(self, test, status, detail=""):
        records.append({"id": "TC_" + test._testMethodName.split("_")[1], "name": test._testMethodName[8:],
                        "status": status, "scope": "isolated Flask test client / GPIO doubles", "detail": detail,
                        "duration_ms": round((time.perf_counter()-self.started)*1000, 3)})

    def addSuccess(self, test):
        super().addSuccess(test)
        self.record(test, "PASS")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.record(test, "FAIL", self._exc_info_to_string(err, test))

    def addError(self, test, err):
        super().addError(test, err)
        self.record(test, "FAIL", self._exc_info_to_string(err, test))


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2, resultclass=EvidenceResult).run(unittest.defaultTestLoader.loadTestsFromTestCase(Contract))
    (RESULTS / "backend_tests.json").write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    # Test-client timings are in-process contract timings, not LAN/hardware latency.
    m.ON_RASPBERRY_PI = False
    m.current_temp, m.current_humidity = 25, 50
    client = m.app.test_client()
    timings = []
    for i in range(100):
        t = time.perf_counter()
        response = client.get("/api/current")
        timings.append({"sample": i+1, "duration_ms": round((time.perf_counter()-t)*1000, 4), "http_status": response.status_code,
                        "scope": "in_process_test_client"})
    with (RESULTS / "api_performance.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(timings[0])); w.writeheader(); w.writerows(timings)
    (RESULTS / "api_performance.json").write_text(json.dumps({"scope": "in_process_test_client", "samples": 100,
        "median_ms": statistics.median(x["duration_ms"] for x in timings),
        "p95_ms": sorted(x["duration_ms"] for x in timings)[94], "hardware_latency_measured": False}, indent=2), encoding="utf-8")
    raise SystemExit(0 if result.wasSuccessful() else 1)
