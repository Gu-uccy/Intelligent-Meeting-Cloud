#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
seed_demo_data.py —— 准备「刷脸解锁」演示数据（真实写入 MySQL）

作用：
    1. 确保指定登录账号存在（不存在则创建，密码 123456，BCrypt 加密）；
    2. 给该账号在指定会议室插入一条「覆盖当前时刻」的有效预约（status=1 已确认）；
    3. 打印账号、会议室、时段，方便直接去 3D 页面刷脸解锁。

为什么需要它：
    「刷脸解锁」的业务前提是「本人 + 当前时段该会议室有有效预约」。
    如果只是注册了账号但没有任何覆盖当前时刻的预约，系统会正确拒绝开门（fail-closed），
    演示时就容易误以为是识别有问题。这个脚本用来快速造出合法的演示上下文。

用法（默认连 127.0.0.1:3307 的 meeting_room_db）：
    python scripts/seed_demo_data.py --account 13900000002 --password 123456 --room 301
    python scripts/seed_demo_data.py --account demo --password 123456 --room 302 --minutes 60
    # 只清理该账号的历史演示预约：
    python scripts/seed_demo_data.py --account 13900000002 --room 301 --clean
"""

import argparse
import os
import sys
from datetime import datetime, timedelta

import pymysql

DB = {
    "host": os.environ.get("MYSQL_HOST", "127.0.0.1"),
    "port": int(os.environ.get("MYSQL_PORT", "3307")),
    "user": os.environ.get("MYSQL_USER", "root"),
    "password": os.environ.get("MYSQL_PASSWORD", ""),
    "database": os.environ.get("MYSQL_DB", "meeting_room_db"),
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
}


def bcrypt_hash(raw: str) -> str:
    """优先用 bcrypt 库；没装时用 passlib；都没有则提示。"""
    try:
        import bcrypt

        return bcrypt.hashpw(raw.encode("utf-8"), bcrypt.gensalt(rounds=10)).decode("utf-8")
    except ImportError:
        pass
    try:
        from passlib.hash import bcrypt as passlib_bcrypt

        return passlib_bcrypt.using(rounds=10).hash(raw)
    except ImportError:
        raise SystemExit(
            "需要 bcrypt 或 passlib 来生成与 Spring Security 兼容的密码哈希：\n"
            "  python -m pip install bcrypt\n"
            "或者改用网页「注册」功能创建账号（推荐，走真实注册接口）"
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--account", default="13900000002", help="登录账号")
    parser.add_argument("--password", default="123456", help="账号密码（新建时使用）")
    parser.add_argument("--name", default=None, help="姓名（默认取账号）")
    parser.add_argument("--room", default="301", help="会议室编号：301/302/501")
    parser.add_argument("--before", type=int, default=20, help="预约开始于当前时间之前多少分钟")
    parser.add_argument("--minutes", type=int, default=60, help="预约总时长（分钟）")
    parser.add_argument("--clean", action="store_true", help="只清理该账号的演示预约")
    args = parser.parse_args()

    conn = pymysql.connect(**DB)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, login_account, username FROM user WHERE login_account=%s", (args.account,))
            user = cur.fetchone()

            if args.clean:
                if not user:
                    print("账号不存在，无需清理")
                    return
                cur.execute(
                    "DELETE FROM reservation WHERE user_id=%s AND create_by='seed_demo'", (user["id"],))
                conn.commit()
                print("已清理演示预约 %d 条" % cur.rowcount)
                return

            if not user:
                cur.execute(
                    "INSERT INTO user (login_account, password, username, gender, phone, email,"
                    " is_active, is_admin, create_by) VALUES (%s,%s,%s,%s,%s,%s,1,0,'seed_demo')",
                    (args.account, bcrypt_hash(args.password), args.name or args.account, 0,
                     args.account if len(args.account) == 11 and args.account.isdigit() else None,
                     "%s@example.com" % args.account),
                )
                conn.commit()
                cur.execute("SELECT id, login_account, username FROM user WHERE login_account=%s", (args.account,))
                user = cur.fetchone()
                print("已创建账号 %s（密码 %s）" % (args.account, args.password))
            else:
                print("复用已有账号 %s（id=%s）" % (args.account, user["id"]))

            cur.execute("SELECT id, room_code, capacity, is_active FROM meeting_room WHERE room_code=%s",
                        (args.room,))
            room = cur.fetchone()
            if not room:
                raise SystemExit("会议室 %s 不存在，请先执行数据库初始化" % args.room)

            now = datetime.now().replace(microsecond=0)

            # 先清理该账号在该会议室「已经结束」的历史演示/联调预约，避免旧的已过期记录干扰
            cur.execute(
                "DELETE FROM reservation WHERE user_id=%s AND room_id=%s AND end_time < %s"
                " AND (create_by IN ('seed_demo','e2e') OR reservation_no LIKE 'E2E%%'"
                "      OR reservation_no LIKE 'DEMO%%')",
                (user["id"], room["id"], now),
            )
            cleaned = cur.rowcount
            if cleaned:
                conn.commit()
                print("已清理过期演示预约 %d 条" % cleaned)

            # 已有预约正好覆盖当前时刻 → 直接复用
            cur.execute(
                "SELECT id, reservation_no, start_time, end_time FROM reservation"
                " WHERE room_id=%s AND user_id=%s AND status IN (0,1)"
                "   AND start_time <= %s AND end_time >= %s LIMIT 1",
                (room["id"], user["id"], now, now),
            )
            live = cur.fetchone()
            if live:
                print("\n当前时刻已有有效预约，可直接演示：")
                print("  账号      : %s" % args.account)
                print("  会议室    : %s（id=%s）" % (room["room_code"], room["id"]))
                print("  预约号    : %s" % live["reservation_no"])
                print("  有效时段  : %s ~ %s" % (live["start_time"], live["end_time"]))
                return

            start = (now - timedelta(minutes=args.before)).replace(second=0)
            # 对齐到 30 分钟，避免违反「整点/半点」校验
            start = start.replace(minute=(start.minute // 30) * 30)
            end = start + timedelta(minutes=args.minutes)
            if end <= now:
                end = now + timedelta(minutes=max(30, args.minutes // 2))

            cur.execute(
                "SELECT id, reservation_no, start_time, end_time FROM reservation"
                " WHERE room_id=%s AND status IN (0,1) AND start_time < %s AND end_time > %s",
                (room["id"], end, start),
            )
            conflict = cur.fetchone()
            if conflict:
                print("⚠ 该时段被别的预约占用：%s（%s ~ %s）" % (
                    conflict["reservation_no"], conflict["start_time"], conflict["end_time"]))
                print("  可换一间会议室（--room 302）或缩短时长（--minutes 30）")
                return

            reservation_no = "DEMO%d" % int(datetime.now().timestamp())
            cur.execute(
                "INSERT INTO reservation (reservation_no, user_id, room_id, start_time, end_time,"
                " status, meeting_topic, participant_num, create_by, remark)"
                " VALUES (%s,%s,%s,%s,%s,1,%s,%s,'seed_demo','演示数据')",
                (reservation_no, user["id"], room["id"], start, end,
                 "刷脸解锁演示（%s）" % room["room_code"], 4),
            )
            # 同步会议室状态为「已预约未使用」，与业务语义一致
            cur.execute("UPDATE meeting_room SET status=3 WHERE id=%s", (room["id"],))
            conn.commit()

            print("\n演示数据已就绪：")
            print("  账号      : %s（密码 %s）" % (args.account, args.password))
            print("  会议室    : %s（id=%s，%s）" % (room["room_code"], room["id"], args.room))
            print("  预约号    : %s" % reservation_no)
            print("  有效时段  : %s ~ %s（当前时间 %s 落在区间内）" % (
                start, end, now.strftime("%Y-%m-%d %H:%M:%S")))
            print("\n下一步：")
            print("  1) 浏览器登录 %s，到「人脸门禁」录入本人人脸（或上传照片录入）；" % args.account)
            print("  2) 打开 3D 会议室页面，点「刷脸解锁会议室」，门会打开且 3D 门同步转动。")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
