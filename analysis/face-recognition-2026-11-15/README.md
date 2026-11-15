# 人脸对齐与Root-LBP识别改进

2026-11-15，基线 `e1d66d2`。继YuNet减少漏检后，本轮改进检测后的裁剪与纹理比较，保持检测分数0.6及同一CMU数据清单。

## 改了什么

旧版直接将包围框拉伸成112×112，眼睛、鼻子、嘴在7×7网格中的位置可能变化。现在使用YuNet五个关键点，在原图坐标中求无反射的相似变换，将人脸对齐到112×112标准参考几何，再做自研灰度、均衡化和LBP。

变换由项目NumPy SVD最小二乘求解，缩放、旋转、平移统一拟合，不对不同身份调参数；图像采样调用OpenCV warpAffine。五点模板参考 [OpenCV FaceRecognizerSF源码](https://github.com/opencv/opencv/blob/4.13.0/modules/objdetect/src/face_recognize.cpp) 的标准112×112几何；[官方教程](https://docs.opencv.org/4.13.0/d0/dd4/tutorial_dnn_face.html)也在识别前进行alignCrop。本项目不使用SFace识别网络，不复制教程的身份阈值。相似变换不能消除侧脸透视和遮挡。

LBP仍为7×7块、每块59箱、2891维。新Root-LBP每块直方图先L1归一化、再开平方，级联后L2归一化，用余弦比对；这样减少大频数分箱的支配程度。保留原LBP函数与显式模式，不覆盖历史算法。数学归一化方法不是本组首次提出，具体数组实现属于项目代码。

## 选择与开发结果

先保存 [协议](protocol.md)，再比较四个固定候选。只在192张登记和217张标定图像上提取特征并选择；先各自标定身份阈值（标定FAR≤5%，已知错误最少），再按标定正确数、较少未知误接受、较少已知错认和固定顺序选方案。原test的215张图像不参与选择；清单校验只读其字节哈希。

| 特征候选 | 标定正确/96 | 标定拒识/96 | 标定未知误接受/121 |
|---|---:|---:|---:|
| 包围框+原LBP（上一版） | 63 | 33 | 5 |
| 五点对齐+原LBP | 64 | 32 | 6 |
| 包围框+Root-LBP | 66 | 30 | 5 |
| 五点对齐+Root-LBP（入选） | 66 | 30 | 4 |

选择写入 `comparison/selection.json` 后，仅对入选方案处理原test，并冻结身份阈值0.7936409785305589；未根据test结果选择第二方案或增加候选。评估在读取test特征前校验检测器、特征版本、清单哈希和阈值，冻结文件绑定选择文件SHA256。

| 原test划分指标 | 上一版包围框LBP | 本轮对齐Root-LBP |
|---|---:|---:|
| 已知身份正确识别 | 59/90（65.56%） | 64/90（71.11%） |
| 已知拒识FRR | 31/90（34.44%） | 26/90（28.89%） |
| 已知认错身份 | 0 | 0 |
| 未知误接受FAR | 5/125（4.00%） | 4/125（3.20%） |
| 综合accuracy | 179/215（83.26%） | 185/215（86.05%） |
| 已知检测/提取失败 | 6/90 | 6/90 |
| 未知检测/提取失败 | 8/125 | 8/125 |

624张中提取成功仍为579、失败45，照片没有新增或排除。原test已检出的84张已知中正确64张（条件正确率76.19%）；117张已检出的未知中误接受4张（条件FAR3.42%）。26张已知拒识中6张未检出、20张虽检出但未达身份阈值。这是有限改善，不表示识别问题已解决。

本批CMU数据已经多次查看，以上均为开发对比，不能当作新的独立验证，`held_out_test`只是沿用JSON字段名。数据没有独立拍摄会话信息，未验证现场摄像头、活体或树莓派；未知误接受4次仍存在，不能声明完整门禁验收达标。YuNet单脸数量也不是人工真值框验证的检测召回率。

## 当前服务行为

默认 `FACE_DETECTOR=yunet-06`、`FACE_FEATURE_MODE=aligned-root-lbp`；可显式指定 `bbox-lbp` 复现上一版。检测关键点与框一起映射回原图，单脸才对齐；关键点越界、退化或不合法则拒绝，不用整图/包围框静默兜底。

特征维数相同也不能混用版本：原YuNet包围框底库及其阈值不适用于新流程，按已有授权重新登记、标定。新登记保存feature_profile，服务要求 `FACE_THRESHOLD_PROFILE` 与 `/health.feature_profile` 一致。默认仍无身份阈值、空底库、空有效预约；本轮离线评估只用内存特征，没有导入公开人物到底库或发送设备指令。重启人脸服务后加载新默认，不强行终止用户已有进程。

## 复现与证据

已准备CMU缓存时，从仓库根目录运行；没有缓存先按 [原CMU报告](../cmu-faces-2026-11-15/README.md) 下载官方教学数据。照片仍在Git忽略目录，不上传原图/别名映射/特征。

```powershell
python week5/scripts/compare_face_features.py --protocol analysis/face-recognition-2026-11-15/protocol.md --output-dir .codex-run-logs/recognition-recheck
python week5/scripts/cmu_faces.py evaluate --detector yunet-06 --feature-mode aligned-root-lbp --selection .codex-run-logs/recognition-recheck/selection.json --output-dir .codex-run-logs/recognition-recheck-final
$env:EVIDENCE_OUTPUT_DIR='.codex-run-logs/recognition-recheck-tests'
python delivery/tests/test_face_recognition.py
python delivery/tests/test_face_detection.py
python delivery/tests/test_face_pipeline.py
python delivery/tests/test_cmu_faces.py
```

离线CMU脚本默认 `--detector haar --feature-mode bbox-lbp`，用于复现最早基线；当前服务默认有意独立。不要将离线阈值直接抄到现场相机。检测候选复现脚本也显式使用bbox-lbp，避免服务默认改变历史实验。

原始证据在 `comparison/`、`selected/`、`tests/`。新增15项关键点/相似变换/Root-LBP/版本与选择隔离测试通过，旧54项回归通过，共69项。5项真实localhost HTTP启动、健康、空图/缺图/无管理员拒绝检查通过，见 `runtime-smoke.json`；不读取旧私人目录，不驱动GPIO。本轮没有前端修改。

本机Windows AMD64、Python3.10.11、OpenCV4.13.0，432次标定/test完整尝试平均17.114ms、P95 28.904ms；成功397次平均17.880ms，失败35次平均8.433ms。计时含读取、解码、检测、对齐、预处理、特征和比对，排除HTTP/设备动作。与旧运行耗时比较不当作公平硬件基准，不能称树莓派速度。

协议、源码及结果哈希见 `manifest.json`，一致性检查见 `verification.json`；此前两轮CMU/检测结果保持快照不改写。保留待办：独立/现场相机验证、树莓派完整耗时与实物联动，及教师对公开样本替代采样的确认。
