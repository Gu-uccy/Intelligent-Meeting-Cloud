# 第4周数据字典

> 对应检查一：字段名与接口/状态对象约定一致。以下字典逐条对照 `clean_data_v1.csv` 实际字段与 `../week3/docs/state-object.md` 统一状态对象约定核对，全部一致。

## 一、数据版本

- 文件名：`data/processed/clean_data_v1.csv`
- 生成脚本：`scripts/clean_data.py`（来自第3周，可重跑）
- 记录数：14113 条
- 时间范围：2026-09-01 08:00 至 2026-09-28 21:55
- 采样周期：每 5 分钟 1 条，每日 08:00—22:00，共 3 间会议室（301/302/501）

## 二、字段字典

| 字段名 | 类型 | 单位/取值 | 含义 | 数据来源 | 非空数 | 实际范围 | 缺失处理 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| timestamp | 字符串 | `YYYY-MM-DD HH:MM:SS` | 采样时间 | 系统时钟 | 14113 | 2026-09-01 08:00:00 ~ 2026-09-28 21:55:00 | 无缺失 |
| room_id | 数值 | 301 / 302 / 501 | 会议室编号（与 meeting_room.room_code 一致） | 数据库 | 14113 | 301~501 | 无缺失 |
| temperature | 数值 | ℃（0~50 合理） | 温度（DHT11） | 综II传感器系统 | 14084 | 23.8 ~ 33.3 | 缺失/异常置空 |
| humidity | 数值 | %（0~100 合理） | 相对湿度（DHT11） | 综II传感器系统 | 14088 | 37.5 ~ 59.4 | 缺失/异常置空 |
| light | 数值 | 0~255 | 光照值（光敏传感器） | 综II传感器系统 | 14111 | 10 ~ 160 | 缺失/异常置空 |
| smoke | 数值 | 0~200 | 烟雾值（MQ-2） | 综II传感器系统 | 14112 | 16 ~ 200 | 缺失/异常置空 |
| distance | 数值 | cm（2~450 合理） | 门前距离（HC-SR04） | 综II传感器系统 | 14094 | 8.0 ~ 250.0 | 缺失/异常置空 |
| motion | 数值 | 0 / 1 | 人体移动检测（PIR） | 综II传感器系统 | 14113 | 0 ~ 1 | 无缺失 |
| occupancy | 数值 | 0 / 1 | 是否有人（占用状态，统一后布尔） | PIR+占用判定 | 14083 | 0 ~ 1 | 缺失/非法值置空 |
| cooling | 字符串 | 开 / 关 | 制冷设备状态 | 自动控制逻辑 | 14113 | 开/关 | 无缺失 |
| heating | 字符串 | 开 / 关 | 制热设备状态 | 自动控制逻辑 | 14113 | 关 | 无缺失 |
| humidifier | 字符串 | 开 / 关 | 加湿设备状态 | 自动控制逻辑 | 14113 | 关 | 无缺失 |
| dehumidifier | 字符串 | 开 / 关 | 除湿设备状态 | 自动控制逻辑 | 14113 | 关 | 无缺失 |
| lighting | 字符串 | 开 / 关 | 照明设备状态 | 自动控制逻辑 | 14113 | 关 | 无缺失 |
| alarm | 字符串 | 开 / 关 | 烟雾报警状态 | 自动控制逻辑 | 14113 | 开/关 | 无缺失 |
| auto_mode | 字符串 | 自动 / 手动 | 自动控制模式 | 系统配置 | 14113 | 自动 | 无缺失 |

## 三、字段一致性核对

| 数据字典字段 | 状态对象字段（state-object.md） | 一致 |
| --- | --- | --- |
| timestamp | timestamp | ✅ |
| room_id | room_id | ✅ |
| temperature | temperature | ✅ |
| humidity | humidity | ✅ |
| light | light | ✅ |
| smoke | smoke | ✅ |
| distance | distance | ✅ |
| occupancy | occupancy | ✅（motion 作为扩展字段保留） |
| motion | （扩展字段，3D 人员联动使用） | ✅ |
| cooling / heating / humidifier / dehumidifier / lighting / alarm | devices.cooling / devices.heating / devices.humidifier / devices.dehumidifier / devices.lighting / devices.alarm | ✅（CSV 中为“开/关”，统一对象中为 on/off，含义一致） |

## 四、使用说明

- 基线预测（`scripts/baseline_model.py`）与本报告全部图表（`scripts/generate_analysis_charts.py`）均只读取本字典中的字段；
- 占用率口径中的“有效采样”指 occupancy 非空的记录；
- 温度等数值字段的缺失与异常已在第3周清洗中处理（置空保留，不做插值）。
