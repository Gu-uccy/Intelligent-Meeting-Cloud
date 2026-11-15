# 人脸检测改进与开发对比

2026-11-15，承接 `95d0f76`。已将默认检测改为YuNet并加入保持比例的输入缩放，继续使用项目自研预处理、2891维LBP与余弦比对。

## 原因与结果

原程序只使用正脸Haar，128×120照片中小于60×60的脸被忽略；侧脸、抬头和墨镜遮挡进一步造成漏检。现在使用 [OpenCV Zoo官方YuNet](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet) 的2023mar模型，以兼容项目OpenCV4.x。文件232589字节，MIT许可，模型与版权归原作者，不冒充自研。来源、固定上游提交与许可见 [models](../../MachineLearning/human_face/models/README.md)。[OpenCV示例](https://docs.opencv.org/4.13.0/d0/dd4/tutorial_dnn_face.html)说明了检测分数、NMS和输入尺寸的作用。

| 指标 | 旧Haar流程 | 入选YuNet流程 |
|---|---:|---:|
| 624张中恰好一脸且提取成功 | 155（24.84%） | 579（92.79%） |
| 提取失败（全部保留） | 469 | 45 |
| test划分已知正确识别 | 14/90（15.56%） | 59/90（65.56%） |
| 已知拒识FRR | 76/90（84.44%） | 31/90（34.44%） |
| 已知认错身份 | 0 | 0 |
| 未知误接受FAR | 2/125（1.60%） | 5/125（4.00%） |
| 综合accuracy | 137/215（63.72%） | 179/215（83.26%） |
| 已知test检测失败 | 69/90 | 6/90 |
| 未知test检测失败 | 96/125 | 8/125 |

这是同一批已查看CMU数据上的开发对比，不能称为全新独立测试。没有人工真值框，92.79%是检出单脸并提取成功的比例，不是定位准确率或经标注验证的召回率。低检测分数可能含误检，因此同时报告身份识别和误接受。

新流程检出的84张已知test图像中正确59张（70.24%）；117张检出的未知test图像中误接受5张（条件FAR4.27%）。仍有25张已检出的已知图像被LBP阈值拒绝，另6张未检出。多姿态、光照与裁剪变化仍影响分块纹理特征；未知误接受也比旧版高，不能声明人脸门禁已验收达标。

## 预设方案与选择

先保存 [预设协议](protocol.md)，CMU清单、身份和划分不变，旧证据不覆盖。首轮采用官方示例的检测分数0.9，单脸提取217/624，test已知正确29/90，结果保留在 `yunet/`。

第二阶段提前限定四个候选，仅用登记与标定特征选型，不再加候选。YuNet保持宽高比，将长边小于320的放大、大于960的缩小，框映射回原图裁边。每个候选独立标定身份阈值，要求标定FAR≤5%，按标定已知正确数、误接受数、错认数与固定顺序选择。

| 候选 | 标定已知正确/96 | 标定未知误接受/121 | 登记+标定提取成功/409 |
|---|---:|---:|---:|
| YuNet检测分数0.9 | 25 | 6 | 142 |
| YuNet检测分数0.7 | 62 | 5 | 366 |
| YuNet检测分数0.6 | 63 | 5 | 378 |
| Haar小脸（scale1.05、neighbors5、min24） | 34 | 4 | 229 |

依预设规则选出 `yunet-06`，写入 `selection.json` 后才提取原test特征。身份阈值0.7756757458169413只来自标定，处理test前检查检测器、特征版本、清单哈希和阈值与选择文件一致；冻结文件绑定选择文件SHA256。没有用test选第二个方案。检测分数0.6决定是否存在人脸，身份阈值决定与登记者是否相似，两者不同。

原选择元数据 `test_images_read_in_this_stage=0` 用词不精确：清单校验会读取所有文件字节验证哈希；候选选择没有使用test检测/识别特征。原文件和冻结哈希保留，更正见 [读取范围说明](selection-read-scope-correction.json)，新复现脚本改用准确字段 `test_features_extracted_in_this_stage`。

## 运行行为与复现

- 默认 `FACE_DETECTOR=yunet-06`；保留明确可选的旧Haar与开发候选。模型固定SHA256，启动不联网，缺失或篡改时报错。
- 无脸、多脸、非法框、坏图仍拒绝；不取最大脸掩盖第二人，也没有整图兜底。共享DNN加锁，避免并发请求改变输入尺寸。
- 登记保存 `feature_profile`，核验和追加录入均拒绝混用旧版本；旧底库不自动转换/删除，需重新登记和标定。实际流程配置身份阈值时，必须同时设置与 `/health.feature_profile` 一致的 `FACE_THRESHOLD_PROFILE`。
- 空底库、未配置阈值/有效预约继续拒绝。本次没有导入公开人物到底库、没有改运行阈值或发送门指令。人脸服务重启后生效，没有强行关闭现有旧进程。

从仓库根目录复现，选择新输出目录：

```powershell
python week5/scripts/compare_face_detectors.py --protocol analysis/face-detection-2026-11-15/protocol.md --output-dir .codex-run-logs/detector-recheck
python week5/scripts/cmu_faces.py evaluate --detector yunet-06 --selection .codex-run-logs/detector-recheck/selection.json --output-dir .codex-run-logs/detector-recheck-final
$env:EVIDENCE_OUTPUT_DIR='.codex-run-logs/detector-recheck-tests'
python delivery/tests/test_face_detection.py
python delivery/tests/test_face_pipeline.py
python delivery/tests/test_cmu_faces.py
# 重启前先确认现有5001端口，避免冲突
python MachineLearning/human_face/face_api.py
```

首次准备CMU数据的方法见旧CMU报告；已有缓存时跳过prepare。离线评估脚本 `--detector` 默认仍为 `haar`，用于历史基线复现；网页服务默认是新YuNet。切换后按许可/授权重新登记和标定，不能把离线阈值直接抄到现场相机。

## 验证与限制

18项新增检测/坐标/边界/模型校验/并发/版本与选型隔离测试通过，原25项人脸算法访问与11项评估协议回归通过，共54项。合成回归与公开图像实验分开计数。原始记录见 `tests/`；本机HTTP启动、健康和异常拒绝检查见 `runtime-smoke.json`。

Windows AMD64、Python3.10.11、OpenCV4.13.0。432次标定/test完整尝试含失败平均14.598ms、P95 23.691ms；成功397次平均15.092ms，失败35次平均8.990ms，包含读取/解码/检测/预处理/LBP/比对，排除HTTP与设备。新旧数据来自不同运行，不当作公平硬件性能基准或树莓派性能。

`manifest.json`记录本轮源码及证据哈希。旧目录按 `95d0f76` 的快照核对。原图和别名映射仍只存Git忽略目录，不上传照片或特征。教师是否接受CMU替代采样、全新独立/现场相机数据验证、目标树莓派性能与实物联动继续待办。
