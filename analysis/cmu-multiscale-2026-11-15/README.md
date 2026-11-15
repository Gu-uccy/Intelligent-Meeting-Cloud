# 同批CMU多尺度Root-LBP开发比较

2026-11-15，基线 `2168569`。完成8个固定候选的实现、标定选型、入选方案评估和回归。**本轮未得到测试划分上的提升，服务默认保持单尺度4×4 / 944维。** 多尺度作为显式实验选项，未导入运行身份阈值或人物底库。

## 方案和选型

沿用20人624张有效CMU原图、原图哈希与划分：192登记、217标定、215原test。提前写 [协议](protocol.md)，固定YuNet0.6、五点对齐比例0.85、112×112预处理，仅比较网格与采样半径组合；每个分块保留59个uniform-LBP桶。

每个分支独立Root-LBP和L2归一化，乘权重平方根、级联再归一化。最终内积等于分支余弦相似度的加权和。每人取某一张登记照片的最高综合分，不在各分支挑不同照片再拼分。半径2使用8个整数方形偏移，不是插值圆形LBP。

只对登记/标定提取候选特征，标定约束FAR≤5%，再最少已知错误。跨候选按已知正确更多、未知误接受更少、已知错认更少、固定顺序选型，并列优先基线。选择文件落盘后才提取入选者test特征，未根据test选第二个候选或改阈值。

| 候选 | 分支（网格/半径/权重） | 维度 | 标定已知正确/96 | 标定未知误接受/121 |
|---|---|---:|---:|---:|
| single（默认） | 4/1/1 | 944 | 80 | 6 |
| coarse-80 | 4/1/0.8 + 2/1/0.2 | 1180 | 80 | 3 |
| **coarse-50（标定入选）** | **4/1/0.5 + 2/1/0.5** | **1180** | **81** | **4** |
| pyramid-80 | 4/1/0.8 + 7/1/0.2 | 3835 | 77 | 5 |
| pyramid-50 | 4/1/0.5 + 7/1/0.5 | 3835 | 71 | 2 |
| radius-80 | 4/1/0.8 + 4/2/0.2 | 1888 | 80 | 4 |
| radius-50 | 4/1/0.5 + 4/2/0.5 | 1888 | 80 | 5 |
| mixed | 4/1/0.7 + 2/1/0.15 + 4/2/0.15 | 2124 | 80 | 4 |

入选阈值0.9568763123663867，标定正确81/96（84.38%）、未知误接受4/121（3.31%）。不是检测分数0.6，也不能直接用作现场阈值。所有候选31/409开发图提取失败，保留在分母。

## 冻结后原test结果

| 指标 | 现有single | 标定入选coarse-50 |
|---|---:|---:|
| 已知正确 | 70/90（77.78%） | 70/90（77.78%） |
| 已知拒识 | 20/90（22.22%） | 20/90（22.22%） |
| 已知错认 | 0 | 0 |
| 未知误接受 | 2/125（1.60%） | 3/125（2.40%） |
| 综合accuracy | 193/215（89.77%） | 192/215（89.30%） |
| 已知提取失败 | 6/90 | 6/90 |
| 未知提取失败 | 8/125 | 8/125 |

全部提取仍579/624成功、45失败。检出子集：已知70/84正确（83.33%），未知3/117误接受（2.56%）；主表含全部失败。20张已知拒识中6张未检出、14张已提取但低于阈值。

逐图对照3个变化：CMU02/031从拒识恢复，CMU12/030从正确变拒识，CMU19/003新增未知误接受，见 [对照JSON](outcome-comparison.json)。这是选型后的描述性诊断，没有据此追加候选。

标定小幅改善，原test没有改善。保留原默认是一项部署决定，不把test反过来用于另选候选；coarse-50仍是本轮规则选出的唯一测试方案。未测其他候选的test，不宣称single是所有候选的最佳泛化方案。

同一CMU已多轮查看，JSON的 `held_out_test` 是沿用划分名，**不是新独立验证或现场验收**。粗网格可能利用头发、轮廓、背景，无法证明因果或排除过拟合。仅靠同批数据调参收益有限，独立拍摄/授权样本和现场相机更能验证实际效果。

## 服务与兼容

默认 `FACE_LBP_VARIANT=single`、比例0.85、网格4，原feature_profile逐字保持。实验显式设 `FACE_LBP_VARIANT=coarse-50`；非single仅支持aligned-root-lbp与grid4。

`/health`新增 `lbp_variant`，报告实际维度。实验profile含分支名和版本；coarse-80与coarse-50虽同为1180维，也拒绝混用底库或阈值。实验须按当前授权重新登记/标定，`FACE_THRESHOLD_PROFILE`匹配实际profile。旧底库不自动转换或删除，离线脚本不更改运行配置。默认无身份阈值/无预约，保持拒绝；人脸门控仅模拟，没有活体检测，不控制实物门。

## 复现与检查

仓库根目录，已有CMU缓存，使用新输出目录：

```powershell
python week5/scripts/compare_multiscale_lbp.py --protocol analysis/cmu-multiscale-2026-11-15/protocol.md --output-dir .codex-run-logs/cmu-multiscale-recheck
python week5/scripts/cmu_faces.py evaluate --detector yunet-06 --feature-mode aligned-root-lbp --alignment-scale 0.85 --lbp-grid 4 --lbp-variant coarse-50 --selection .codex-run-logs/cmu-multiscale-recheck/selection.json --output-dir .codex-run-logs/cmu-multiscale-recheck-final
$env:EVIDENCE_OUTPUT_DIR='.codex-run-logs/cmu-multiscale-recheck-tests'
python delivery/tests/test_multiscale_lbp.py
python delivery/tests/test_cmu_tuning.py
python delivery/tests/test_face_recognition.py
python delivery/tests/test_face_detection.py
python delivery/tests/test_face_pipeline.py
python delivery/tests/test_cmu_faces.py
```

16项新增测试覆盖半径参考计算、分支权重/相似度、基线逐元素兼容、动态维度、同维异版本隔离、API登记与拒绝、选型不提取test；加旧80项，共96项通过。另修复选型脚本的空结果防护：全部提取失败也能满足FAR=0，现在至少须正确识别一张已知照片才可入选；不改变本轮8个实际候选的选择结果。默认新进程另通过5项localhost HTTP检查。预期offline日志来自测试替身，未操作实物。

8候选选择及入选者全部预测重复运行核对一致（排除计时与生成时间），仅验证可复现，不增加统计样本。见 `verification.json`、`tests/`、`runtime-smoke.json`。`comparison/`保存8份409行结果，`selected/`保存624行结果、阈值曲线与冻结哈希；源码/证据哈希在 `manifest.json`。前四轮证据保持原快照。

首轮Windows AMD64 / Python3.10.11 / OpenCV4.13.0，432次标定/test完整尝试平均16.233ms、P95 27.512ms，含读取、解码、检测、对齐、预处理、特征和比对，排除HTTP/设备。多尺度维度增加25%，额外一组分块；复现耗时受系统负载影响明显，不据此声称公平加速或树莓派性能。

原图、别名映射与特征不上传，未读取旧私人 `id/`、`test/`。教学来源许可见 [CMU记录](../cmu-faces-2026-11-15/README.md)，模型许可见 [模型记录](../../MachineLearning/human_face/models/README.md)。树莓派未连接；独立样本、现场相机、目标设备耗时/实体联动和教师接受公开样本替代仍待确认，视频按用户要求不制作。
