# 同批CMU参数调优结果

2026-11-15，用户明确要求继续在同批CMU上调参，基线 `1a70158`。本轮固定YuNet0.6与五点对齐/Root-LBP，比较对齐范围及LBP分块大小。当前服务默认采用入选参数：`FACE_ALIGNMENT_SCALE=0.85`、`FACE_LBP_GRID=4`、944维；旧1.0/7×7/2891维保留为显式可复现配置。

## 怎么选参数

先写 [协议](protocol.md)，限定9组：模板比例0.85/1.0/1.15 × 网格4/7/8。比例围绕输出中心(56,56)缩放五点模板；比例越小，脸在112×112中越小，周围内容越多。网格每块保留59个uniform-LBP分箱，分块L1归一化、开平方、整体L2归一化及最大余弦比对不变。

同一20人624张原图、登记192张、标定217张、原test215张保持不变。只在登记/标定上提取候选特征和选择身份阈值（标定FAR≤5%下最少已知错误）；候选按标定已知正确、较少未知误接受、较少已知错认、固定顺序选择，优先保留基线。选择落盘后才提取入选者test特征；没有按test加候选或反向调整阈值。

| 对齐比例 | 网格 | 维度 | 标定已知正确/96 | 标定未知误接受/121 |
|---:|---:|---:|---:|---:|
| 1.00（基线） | 7×7 | 2891 | 66 | 4 |
| **0.85（入选）** | **4×4** | **944** | **80** | **6** |
| 0.85 | 7×7 | 2891 | 69 | 4 |
| 0.85 | 8×8 | 3776 | 75 | 6 |
| 1.00 | 4×4 | 944 | 70 | 6 |
| 1.00 | 8×8 | 3776 | 66 | 6 |
| 1.15 | 4×4 | 944 | 63 | 3 |
| 1.15 | 7×7 | 2891 | 54 | 6 |
| 1.15 | 8×8 | 3776 | 54 | 5 |

入选身份阈值0.9311644386168618，来自标定集；该值与检测分数0.6含义不同。较粗网格与较宽对齐范围在这批数据上容忍更多姿态/局部位置变化；但这只是对结果的解释，未做因素因果证明。0.85可能引入头发、轮廓、背景，不能把分数提升全归因于面部身份信息。

## 原test划分开发对比

| 指标 | 上一版1.0/7×7 | 本轮0.85/4×4 |
|---|---:|---:|
| 已知身份正确识别 | 64/90（71.11%） | **70/90（77.78%）** |
| 已知拒识FRR | 26/90（28.89%） | **20/90（22.22%）** |
| 已知认错身份 | 0 | 0 |
| 未知误接受FAR | 4/125（3.20%） | **2/125（1.60%）** |
| 综合accuracy | 185/215（86.05%） | **193/215（89.77%）** |
| 已知检测/提取失败 | 6/90 | 6/90 |
| 未知检测/提取失败 | 8/125 | 8/125 |

624张中仍提取成功579、失败45；没有跳过困难图像。已检出的84张已知test中正确70张（83.33%），117张检出的未知中误接受2张（条件FAR1.71%）。20张本人拒识中6张未检出，14张已检出但低于身份阈值。

标定误接受由4/121升至6/121（4.96%），test误接受由4/125降至2/125；必须同时报告，不能只称误接受整体改善。所有数据已被多轮查看，本轮是开发调优，JSON的 `held_out_test` 为沿用字段，不能称新独立测试或现场门禁达标。未知误接受仍有2次，背景利用和标定过拟合风险尚未排除。

## 运行、兼容与复现

新默认：`FACE_DETECTOR=yunet-06`、`FACE_FEATURE_MODE=aligned-root-lbp`、比例0.85、网格4。相同维度也必须核对feature_profile，模型、特征方式、比例或网格不同均拒绝混用。旧底库不会自动转换/删除，按当前授权重新登记/标定，`FACE_THRESHOLD_PROFILE` 必须等于 `/health.feature_profile`。此次没有导入CMU人物到底库或启用运行身份阈值，默认仍拒绝，设备动作仍仅限模拟与有效预约确认。

`/health`新增 `alignment_scale`、`lbp_grid`、`feature_dimensions`。旧7×7算法保持逐元素兼容；旧实验脚本显式使用比例1.0、网格7，避免默认变化改写历史结果。服务重启后新默认生效，未强行终止已有服务。

```powershell
# 仓库根目录，已有CMU缓存；输出使用新目录
python week5/scripts/tune_cmu_parameters.py --protocol analysis/cmu-tuning-2026-11-15/protocol.md --output-dir .codex-run-logs/cmu-tuning-recheck
python week5/scripts/cmu_faces.py evaluate --detector yunet-06 --feature-mode aligned-root-lbp --alignment-scale 0.85 --lbp-grid 4 --selection .codex-run-logs/cmu-tuning-recheck/selection.json --output-dir .codex-run-logs/cmu-tuning-recheck-final
$env:EVIDENCE_OUTPUT_DIR='.codex-run-logs/cmu-tuning-recheck-tests'
python delivery/tests/test_cmu_tuning.py
python delivery/tests/test_face_recognition.py
python delivery/tests/test_face_detection.py
python delivery/tests/test_face_pipeline.py
python delivery/tests/test_cmu_faces.py
# 复现上一版服务时，启动前同时指定：
$env:FACE_ALIGNMENT_SCALE='1.0'
$env:FACE_LBP_GRID='7'
```

原始结果在 `comparison/`（9组标定与409行逐图结果）、`selected/`（624行完整结果、阈值曲线和冻结记录）、`tests/`。11项新增参数/覆盖/版本隔离/选择隔离测试与旧69项回归通过，共80项；5项真实localhost HTTP健康与异常拒绝检查通过，见 `runtime-smoke.json`。合成回归不计入真实照片数量，未读取旧私人目录或驱动GPIO。

Windows AMD64、Python3.10.11、OpenCV4.13.0；432次标定/test完整尝试平均12.999ms、P95 23.146ms，含读取、解码、检测、对齐、预处理、LBP与比对，排除HTTP/设备；成功397次平均13.446ms，失败35次平均7.928ms。旧版运行平均17.114ms，两个运行不视为公平硬件基准或树莓派性能证明。

`manifest.json`记录源码与证据哈希，`verification.json`记录一致性与复现检查，前三轮证据保持快照。原图、原始别名映射与特征不上传，来源许可仍见 [CMU记录](../cmu-faces-2026-11-15/README.md)。保留独立/现场相机验证、树莓派耗时与实物联动、教师接受公开样本替代的待办。
