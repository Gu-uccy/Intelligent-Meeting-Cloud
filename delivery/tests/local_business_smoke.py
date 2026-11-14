"""Real Spring HTTP + isolated MySQL acceptance; no booking mocks or Raspberry Pi.

Run through scripts/test-local-business.ps1, which creates a fresh test instance.
Only synthetic accounts and a database named meeting_acceptance_* are permitted.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import date, timedelta, datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError

base = os.environ["MEETING_TEST_URL"].rstrip("/")
db = os.environ["MEETING_TEST_DB"]
if not db.startswith("meeting_acceptance_") or not db.replace("_", "").isalnum():
    raise RuntimeError("Refusing to test outside an isolated meeting_acceptance_* database")
mysql = os.environ["MEETING_TEST_MYSQL"]
config = os.environ["MEETING_TEST_MYSQL_CONFIG"]
output = Path(os.environ["EVIDENCE_OUTPUT_DIR"])
output.mkdir(parents=True, exist_ok=True)
result = {"generated_at": datetime.now(timezone.utc).isoformat(), "scope": "Real Spring HTTP and isolated MySQL; Redis unavailable/degraded; no mocks, Pi or real faces", "base": base, "checks": []}


def sql(query):
    proc = subprocess.run([mysql, "--defaults-file=" + config, "--batch", "--skip-column-names", db, "-e", query], capture_output=True, text=True, encoding="utf-8")
    if proc.returncode:
        raise RuntimeError("MySQL assertion query failed")
    return proc.stdout.strip()


def http(method, path, payload=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["token"] = token
    request = Request(base + path, data=None if payload is None else json.dumps(payload).encode(), headers=headers, method=method)
    try:
        response = urlopen(request, timeout=15)
    except HTTPError as error:
        response = error
    body = response.read().decode("utf-8")
    return response.status, json.loads(body) if body else None


def check(name, condition):
    if not condition:
        raise AssertionError(name)
    result["checks"].append({"name": name, "status": "PASS"})


def slots(token, day):
    return http("GET", "/user/reservation/slots?roomId=1&date=" + day, token=token)[1]["data"]


try:
    check("isolated database selected", sql("SELECT DATABASE()") == db)
    status, health = http("GET", "/health")
    check("service and schema readiness", status == 200 and health["service"] == "meeting-room-business" and health["database"] and health["schema"])
    check("Redis degradation reported honestly", health["redis"] is False and health["status"] == "degraded")
    result["health"] = health
    check("missing JWT denied", http("GET", "/user/reservation/my")[0] == 401)
    check("invalid JWT denied", http("GET", "/user/reservation/my", token="invalid")[0] == 401)
    check("wrong password denied", http("POST", "/login", {"loginAccount": "test_user", "password": "incorrect"})[1]["code"] == 0)
    status, login = http("POST", "/login", {"loginAccount": "test_user", "password": "123456"})
    check("real BCrypt user login", status == 200 and login["code"] == 1 and login["data"]["username"] == "测试用户")
    token = login["data"]["token"]
    status, admin = http("POST", "/login", {"loginAccount": "sys_admin", "password": "123456"})
    check("seed administrator mapping", status == 200 and admin["code"] == 1 and admin["data"]["isAdmin"] == 1)
    admin_token = admin["data"]["token"]
    _, page1 = http("GET", "/user/room/page?page=1&pageSize=1", token=token)
    _, page2 = http("GET", "/user/room/page?page=2&pageSize=1", token=token)
    check("real PageHelper pagination", page1["data"]["total"] == 3 and len(page1["data"]["records"]) == 1 and page1["data"]["records"][0]["id"] != page2["data"]["records"][0]["id"])
    _, detail = http("GET", "/user/room/1", token=token)
    check("current room schema reads version and capacity", detail["data"]["capacity"] == 10 and detail["data"]["version"] == 0)
    day = (date.today() + timedelta(days=2)).isoformat()
    empty = slots(token, day)
    check("48 available half-hour slots", len(empty) == 48 and all(s["status"] == 0 for s in empty))
    request = {"roomId": 1, "participantNum": 8, "meetingTopic": "LOCAL-ACCEPTANCE", "startTime": day + " 10:00:00", "endTime": day + " 11:00:00"}
    bad_cases = {
        "missing room": {"roomId": None}, "missing start": {"startTime": None},
        "equal times": {"endTime": day + " 10:00:00"},
        "eight and half hours": {"endTime": day + " 18:30:00"},
        "off-grid time": {"startTime": day + " 10:01:00"},
        "invalid capacity": {"participantNum": 11}, "zero people": {"participantNum": 0},
        "unknown room": {"roomId": 99999},
    }
    for name, override in bad_cases.items():
        status, rejected = http("POST", "/user/reservation", request | override, token)
        check("reject " + name, status == 400 and rejected["code"] == 0)
    check("invalid input leaves database empty", sql("SELECT COUNT(*) FROM reservation") == "0")
    status, added = http("POST", "/user/reservation", request, token)
    check("real reservation commit", status == 200 and added["code"] == 1)
    check("database stores pending reservation", sql("SELECT COUNT(*) FROM reservation WHERE status=0 AND user_id=3 AND participant_num=8") == "1")
    _, mine = http("GET", "/user/reservation/my", token=token)
    reservation_id = mine["data"][0]["id"]
    check("reservation list reads database", len(mine["data"]) == 1 and mine["data"][0]["meetingTopic"] == "LOCAL-ACCEPTANCE")
    occupied = {s["startTime"]: s["status"] for s in slots(token, day)}
    check("pending reservation blocks slots with buffer", occupied["09:30:00"] == occupied["10:00:00"] == occupied["10:30:00"] == occupied["11:00:00"] == 1 and occupied["11:30:00"] == 0)
    check("duplicate reservation refused", http("POST", "/user/reservation", request, token)[1]["code"] == 0)
    check("other user cannot cancel", http("PUT", f"/user/reservation/cancel/{reservation_id}", token=admin_token)[0] == 400)
    check("owner cancellation succeeds", http("PUT", f"/user/reservation/cancel/{reservation_id}", token=token)[1]["code"] == 1)
    check("cancellation persisted", sql(f"SELECT status FROM reservation WHERE id={int(reservation_id)}") == "2")
    check("cancelled reservation releases slots", all(s["status"] == 0 for s in slots(token, day)))
    check("same interval can be booked after cancellation", http("POST", "/user/reservation", request, token)[1]["code"] == 1)
    check("unauthenticated requests still denied after login", http("GET", "/user/reservation/my")[0] == 401)
    check("only two commits, no duplicate insert", sql("SELECT COUNT(*) FROM reservation") == "2")
    check("notification query is authenticated", http("GET", "/user/notification/my")[0] == 401)
    status, notifications = http("GET", "/user/notification/my", token=token)
    check("empty notification table returns empty list", status == 200 and notifications["code"] == 1 and notifications["data"] == [])
    sql("INSERT INTO reservation(reservation_no,user_id,room_id,start_time,end_time,status,meeting_topic) "
        f"VALUES('NOTICE-USER',3,2,'{day} 14:00:00','{day} 15:00:00',1,'Notice test'),"
        f"('NOTICE-ADMIN',1,2,'{day} 16:00:00','{day} 17:00:00',3,'Other user')")
    sql("INSERT INTO notification(notify_no,user_id,related_id,related_type,notification_type,content) "
        "SELECT CONCAT('N-',reservation_no),user_id,id,1,0,'Synthetic approval notice' FROM reservation WHERE reservation_no IN ('NOTICE-USER','NOTICE-ADMIN')")
    _, notices = http("GET", "/user/notification/my", token=token)
    check("notification ownership and field mapping", len(notices["data"]) == 1 and notices["data"][0]["status"] == 1 and notices["data"][0]["isRead"] is False)
    _, admin_notices = http("GET", "/user/notification/my", token=admin_token)
    check("another user's notices stay isolated", len(admin_notices["data"]) == 1 and admin_notices["data"][0]["status"] == 3)
    result["status"] = "PASS"
except Exception as error:
    result["status"] = "FAIL"
    result["error"] = str(error)
finally:
    result["passed"] = len(result["checks"])
    (output / "business-http.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
if result["status"] != "PASS":
    raise SystemExit(1)
