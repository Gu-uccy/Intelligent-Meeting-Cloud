# 第3周课堂实践作业提交说明（week3）

本文件夹为《智能会议室管理系统III》第3周课堂实践作业的全部提交内容

## 目录结构

```
week3/
├── data/
│   ├── raw/
│   │   ├── 原始数据样例.csv          # 原始数据（14152 条，含教学脏数据）
│   │   └── 脏数据注入清单.json        # 注入脏数据明细
│   └── processed/
│       ├── clean_data_v1.csv         # 清洗后正式数据版本（第4周数据分析使用）
│       └── clean_sensor_data.csv     # 第3周提交要求文件名
├── scripts/
│   ├── generate_raw_data.py          # 重新生成原始数据
│   └── clean_data.py                 # 数据清洗与质量检查程序（可重复运行）
├── docs/
│   ├── data_quality_report.md        # 作业1：数据质量检查报告
│   ├── state-object.md               # 作业2：统一会议室状态对象说明
│   ├── api-contract.md               # 作业2：接口契约
│   └── cleaning_run_log.txt          # 清洗运行日志（过程证据）
├── mock/
│   ├── state.json                    # 统一状态对象（mock 数据源）
│   └── mock_state_api.py             # 状态查询模拟接口（Flask）
├── tests/
│   ├── state_api_test.md             # 接口测试记录
│   └── state_api_test_log.txt        # 接口测试真实运行日志（过程证据）
└── results/
    └── quality_report.json           # 质量统计（过程证据）
```

## 作业1：会议室数据清洗与质量检查

- 数据读取：`scripts/clean_data.py` 读取 `data/raw/原始数据样例.csv`
- 时间处理：兼容 6 种时间格式，统一为 `YYYY-MM-DD HH:MM:SS` 并按时间升序排列
- 去重处理：删除重复记录 39 条
- 异常检查：温度（0~50℃）等 5 类异常共 14 条置为缺失
- 缺失处理：逐字段统计（温度 29、湿度 25、光照 2、烟雾 1、距离 19、占用 30），保留空值不做填充并说明策略
- 输出结果：`data/processed/clean_data_v1.csv`（14113 条）
- 可复现性：`python scripts/clean_data.py` 一键重跑，固定随机种子
- 过程证据：`docs/cleaning_run_log.txt`、`results/quality_report.json`

## 作业2：统一会议室状态对象并完成接口测试

- 字段统一：Web / 后端 / 树莓派 / 3D 端统一字段命名（`docs/state-object.md`）
- 状态对象：`mock/state.json`（含会议室、时间、人员、环境、门、设备状态）
- 接口：`mock/mock_state_api.py` 实现 `GET /api/rooms/{room_id}/state`，统一响应包 {code, message, data}
- 正常测试：301/302 返回 200 与规范 JSON
- 异常测试：R99 返回 404 room not found
- 数据来源：source 字段区分 sensor（真实）/ mock（模拟），真实数据映射见 `docs/api-contract.md`

## 运行方式

```powershell
# 作业1
cd week3
python scripts/generate_raw_data.py   # 可选：重新生成原始数据
python scripts/clean_data.py          # 运行清洗，重新输出数据与质量统计

# 作业2
python mock/mock_state_api.py         # 启动模拟接口（端口 5002）
curl http://127.0.0.1:5002/api/rooms/301/state
curl http://127.0.0.1:5002/api/rooms/R99/state
```

## 数据版本说明

`clean_data_v1.csv` 是第4周数据分析与基线预测的正式数据版本（v1），字段名与 `state-object.md` 统一状态对象约定一致；后续第4周图表、基线预测均基于该版本，保证数据可追溯、可复现。
