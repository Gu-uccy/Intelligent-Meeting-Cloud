# 第4周项目实践作业提交说明

## 目录结构

```
week4/
├── data/
│   └── processed/
│       └── clean_data_v1.csv        # 第3周约定数据版本（14113 条，可被清洗脚本重跑）
├── scripts/
│   ├── clean_data.py                # 第3周清洗脚本副本（重跑闭环）
│   ├── baseline_model.py            # 基线预测模型（阈值基线，可复现）
│   ├── generate_analysis_charts.py  # 4 张分析图表生成（可复现）
│   └── publish_baseline_to_state.py # 基线预测结果写入统一状态对象（结果可见性联动）
├── docs/
│   ├── data_dictionary.md           # 数据字典（字段与接口/状态对象一致核对）
│   ├── week4_analysis_report.md     # 数据分析报告（口径+结论+基线指标）
│   └── week4_weekly_plan.md         # 第4周推进计划
├── charts/
│   ├── 01_分时段占用率.png
│   ├── 02_各会议室占用强度.png
│   ├── 03_工作日vs周末占用率.png
│   └── 04_温度分布.png
└── results/
    ├── baseline_result.json         # 基线指标（真实运行结果）
    ├── baseline_run.log             # 基线运行日志
    ├── charts_summary.json          # 图表口径与数值汇总
    ├── baseline_predictions.json    # 预测明细
    ├── state_with_baseline.json     # 统一状态对象（含预测 occupancy，供3D/Web消费）
    └── publish_run.log              # 联动脚本运行日志
```

## 三周检查点对照

### 检查一：第3周交付物闭环
- 清洗脚本可重跑：`python scripts/clean_data.py` → 重新生成 `clean_data_v1.csv`
- 字段名与接口/状态对象一致：见 `docs/data_dictionary.md`（与 week3/docs/state-object.md 逐条核对 ✅）
- 数据字典匹配实际字段：16 列全部按 clean_data_v1.csv 实核 ✅

### 检查二：第4周节点（≥3张图表 + 基线预测）
- 4 张图表分别回答 4 个业务问题，标题注明口径
- 基线模型：阈值基线，样本量 294、按时间切分、准确率 85.03%
- 结果可见性：基线预测写入统一状态对象（`results/state_with_baseline.json`），3D 场景与 Web 端按 occupancy/devices 消费

### 检查三：周推进计划
- `docs/week4_weekly_plan.md`

## 运行方式

```powershell
cd week4
python scripts/baseline_model.py              # 重跑基线 → 更新 results/baseline_result.json
python scripts/generate_analysis_charts.py    # 重跑图表 → 更新 charts/*.png
python scripts/publish_baseline_to_state.py --hour 10   # 预测当前小时占用并写入状态对象
```

## 图表口径速查

| 图 | 业务问题 | 口径 | 结论（真实运行结果） |
| --- | --- | --- | --- |
| 01_分时段占用率 | 哪个时段最忙 | 每小时“有人”采样数÷该小时有效采样总数（3室合并） | 高峰 10:00 占用率 42.9% |
| 02_各会议室占用强度 | 哪间使用最频繁 | 每室“有人”采样数÷该室有效采样总数 | 301 44.4%（约173h）> 302 36.0%（约141h）> 501 6.5%（维修） |
| 03_工作日vs周末 | 周末是否闲置 | 工作日/周末分别的占用采样÷有效采样总数 | 工作日 38.5% vs 周末 5.1% |
| 04_温度分布 | 空调是否舒适 | 温度有效采样落在各区间的占比（2℃分档） | 26~28℃占 31.7%；20~26℃舒适区间仅 9.5% |
