# 第6周人脸识别测试协议（tests/face_test_protocol.md）

## 一、测试目标

在目标设备（树莓派门禁主机）上，用人脸测试集验证识别系统：

1. 本人是否被正确识别（通过）；
2. 非本人是否被拒绝（不通过）；
3. 计算准确率、FAR（误识率）、FRR（拒识率）、响应时间；
4. 验证“失败不放行”（fail-closed）行为。

## 二、测试集组织（与 data_authorization.md 一致）

- 测试集目录（本地私有存储）：`~/face_data/test_set/`，结构 `person_id/photo_N.jpg`；
- 本人测试：3 名已注册对象（A01/A02/A03），每人测试照片 ≥ 5 张；
- 非本人测试：≥ 5 名未注册对象（含陌生人照片，需单独授权或使用公开人脸库并注明来源），每人 ≥ 3 张；
- 注册库：`~/face_data/raw/A01..A03/`（每人 ≥ 10 张注册照）。

## 三、测试步骤

```powershell
# 1. 评估（真实模式，自动输出准确率/FAR/FRR/混淆矩阵/耗时）
python week5\scripts\run_face_eval.py --data-dir D:\face_data\test_set

# 2. 阈值标定（真实集上扫描 θ，选择 FAR<=0.05 前提下 FRR 最小）
python week5\scripts\run_face_eval.py --data-dir D:\face_data\test_set

# 3. 响应时间（在树莓派上测量：预处理+特征+比对单次耗时）
#    结果填入 tests/face_test_record.md
```

## 四、指标定义（口径）

| 指标 | 定义 | 计算公式 |
| --- | --- | --- |
| TP | 本人被正确识别 | 实际本人且判定本人 |
| TN | 非本人被正确拒绝 | 实际非本人且判定非本人 |
| FP（误识） | 非本人被放行 | 实际非本人但判定为某人 |
| FN（拒识） | 本人被拒绝 | 实际本人但判定非本人 |
| 准确率 | 全部判定正确比例 | (TP+TN)/(TP+TN+FP+FN) |
| FAR 误识率 | 非本人被放行比例 | FP/(FP+TN) |
| FRR 拒识率 | 本人被拒绝比例 | FN/(TP+FN) |
| 响应时间 | 单次识别总耗时 | 预处理+检测+特征+比对（毫秒） |

## 五、失败不放行测试用例

| 用例 | 输入 | 期望结果 |
| --- | --- | --- |
| 未注册陌生人刷脸 | 非本人照片 | 拒绝，门保持锁定，写失败日志 |
| 低置信度本人（模糊/逆光） | 本人照片但相似度 < θ | 拒绝（fail-closed），提示重试 |
| 摄像头无画面 | 无帧输入 | 返回 no_face，不判定通过 |
| 人脸库不可读 | 注册库损坏 | 拒绝并告警（fail-closed） |

## 六、记录要求

每项测试结果（数量、指标、阈值、耗时、设备环境、日期）填写 `tests/face_test_record.md`；
原始评估输出归档 `results/face_eval_result.json` 与 `results/face_eval_run.log`。
