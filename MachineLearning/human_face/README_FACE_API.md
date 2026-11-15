# 自研人脸服务与模拟门禁

当前主路径：OpenCV YuNet 单脸检测 → 五点相似变换对齐 → 自研灰度/双线性缩放/直方图均衡化 → 自研 4×4 Root-LBP（944维）→ 余弦比对 → 服务端有效预约名单 → 统一 Flask 模拟门指令 → 设备确认 → 模拟签到日志。未检测到单脸、陌生人、无预约、未审核/过期/房间不符、阈值缺失、设备错误均不确认放行。

这是课堂实验，没有活体检测，未完成现场相机/目标设备标定。人脸服务只允许对 `source=simulation` 的统一服务发送门指令；不会控制实物门。手动门灯控制仍由原有统一传感器接口提供。模拟签到记录在本地 JSONL，不写入 Spring 预约数据库。网页不能自己决定放行。

## 同批CMU参数调优（当前默认）

最新多尺度实验比较8种组合，标定入选4×4+2×2/1180维，但原test仍正确70/90、未知误接受增至3/125。因此默认保持 `FACE_LBP_VARIANT=single` / 944维，多尺度为显式实验选项；`/health`报告分支和维度，版本与阈值须重新匹配。96项回归及5项HTTP检查通过，见 [多尺度实验与保留默认的依据](../../analysis/cmu-multiscale-2026-11-15/README.md)。同批开发结果不能替代独立验证。

默认 `FACE_ALIGNMENT_SCALE=0.85`、`FACE_LBP_GRID=4`，特征944维。在固定9组登记/标定选型后，原test已知正确从64/90增至70/90、未知误接受从4/125降至2/125；标定误接受则从4/121升至6/121。较宽范围可能利用头发/背景，以上仅同批数据开发调优，见 [本轮报告](../../analysis/cmu-tuning-2026-11-15/README.md)。重启服务生效，旧特征和阈值需重新登记/标定，不自动导入离线阈值。显式比例1.0、网格7可复现上一版；以下小节保留历史记录。

## 2026-11-15识别改进（上一版）

默认 `FACE_FEATURE_MODE=aligned-root-lbp`，使用五点对齐和分块直方图开平方归一化。CMU开发对比原test已知正确从59/90增至64/90，未知误接受从5/125降至4/125；同批已查看数据仍不能作为新独立验收。旧包围框特征与新特征不能混用，须按当前 `feature_profile` 重新登记/标定，见 [本轮报告](../../analysis/face-recognition-2026-11-15/README.md)。显式 `FACE_FEATURE_MODE=bbox-lbp` 可复现上一版；离线CMU脚本默认保留haar/bbox-lbp复现最早基线。以下检测小节是前一轮结果。

## 2026-11-15检测改进

默认 `FACE_DETECTOR=yunet-06`，YuNet检测分数0.6、长边320–960等比例缩放；仅检测使用官方模型，自研预处理/LBP/比对保留。CMU开发对比检出单脸从155/624增至579/624，原test已知正确从14/90增至59/90，未知误接受5/125；同一已查看数据不能算全新独立验收。见 [检测改进与复现](../../analysis/face-detection-2026-11-15/README.md)。下方CMU小节保留此前Haar基线结果。

模型和MIT许可随仓库保存，启动不下载，重启服务后生效。旧特征和阈值不能跨检测版本混用：按当前流程重新登记/标定，并将 `FACE_THRESHOLD_PROFILE` 设置为健康接口返回的 `feature_profile`。新登记自动保存版本；旧数据不会自动转换或删除。默认仍为空底库/无阈值，离线实验没有改运行配置。

## 启动

在仓库根目录运行，不能单独复制 `face_api.py`（它依赖仓库中的自研模块）：

```powershell
python -m pip install -r MachineLearning/human_face/requirements.txt
python MachineLearning/human_face/face_api.py
```

默认 `127.0.0.1:5001`；`GET /health`。Demo 一键启动会同时启动本服务。默认无阈值、空底库、空预约，拒绝放行是预期行为。不会读取旧 `id/` 和 `test/` 私人图片。

## CMU公开图像离线评估（2026-11-15）

已接入[CMU官方教学数据](https://www.cs.cmu.edu/~tom/faces.html)：20人624张有效原图，原图只存Git忽略目录；使用依据见 `week5/docs/data_authorization.md`。固定登记/标定/最终测试，并隔离未知身份；全部检测失败保留在分母。

完整服务流程最终已知正确14/90、FRR76/90、未知误接受2/125；另做整幅肖像特征诊断正确85/90，但跳过检测，不能当成完整服务效果。详细证据与命令见 [CMU评估报告](../../analysis/cmu-faces-2026-11-15/README.md)。离线底库仅在内存，未写服务特征或导出运行阈值；默认拒绝配置保持。当前瓶颈为小尺寸/侧脸检测，仍需优化和现场验证。

## 授权样本到评估

先完成 `week5/docs/data_authorization.md`。在仓库外复制空清单，填写 `path,identity,split,kind`；split 为 enroll/calibration/test，kind 为 known/unknown。每个 known 身份至少10张且三个划分都有照片；unknown 身份不能入库。脚本拒绝相同内容跨行、越界路径、缺少未知测试集等情况。无脸或多脸图像会报错，需在清单中修正并记录排除理由，不能静默跳过。

```powershell
python week5/scripts/run_face_eval.py --data-dir D:/AuthorizedFaces --manifest D:/AuthorizedFaces/manifest.csv --authorized --output-dir D:/FaceResults/run-01
```

结果包含独立标定集阈值扫描、冻结阈值的最终测试、accuracy/FAR/FRR、错误身份数和机器环境。耗时包括读取/检测/预处理/LBP/比对，HTTP 与设备响应耗时另看 `/verify` 的 pipeline_ms。应在最终目标设备上跑评估；本机结果不能称树莓派结果。无合格 FAR 阈值时不生成可放行结论。

## 配置与接口

所有设置在启动服务前通过环境变量配置：`FACE_DATA_DIR`（特征和匿名日志私有目录）、`FACE_ADMIN_TOKEN`（录入/删除管理令牌）、`FACE_THRESHOLD`（授权标定后才填写）、`FACE_THRESHOLD_PROFILE`（与当前feature_profile一致）、`FACE_DETECTOR`（默认yunet-06；复现haar时同时设置bbox-lbp特征）、`FACE_FEATURE_MODE`（默认aligned-root-lbp）、`FACE_ALIGNMENT_SCALE`（默认0.85，可选1.0/1.15）、`FACE_LBP_GRID`（默认4，可选7/8；旧非Root模式固定7）、`FACE_LBP_VARIANT`（默认single，实验coarse-50等非single仅支持aligned-root-lbp与grid4）、`FACE_POLICY_PATH`（私有预约策略 JSON）、`FACE_DEVICE_URL`（默认 http://127.0.0.1:5058）、`FACE_API_PORT`、`FACE_HOST`（默认仅本机）。不要把管理令牌写进前端 VITE 环境变量、截图或 Git。

`POST /api/face/enroll`：multipart image、identity（匿名编号）、consent=true，header `X-Face-Admin-Token`。每次追加一条特征，最多30条，不覆盖整个身份。不返回磁盘路径。网页录入需勾选已有授权并手动输入令牌，令牌仅保存在当前组件内存。

`DELETE /api/face/enroll/<identity>`：同管理令牌，删除身份特征。

`POST /api/face/verify`：multipart image、room（默认 A101）。返回 matched、similarity（越大越接近）、threshold、pipeline_ms 和服务端 access。只有 `matched=true && access.allowed=true && access.device.acknowledged=true` 才可显示模拟放行。非200也要按拒绝处理。

策略模板 `face-policy.example.json` 默认为空。授权实测时在私有副本中加入预约，字段为 `id`、`room`、`identities`（匿名编号数组）、`approved`（布尔）、`start`、`end`（含时区的 ISO 日期）。设置 `FACE_POLICY_PATH` 指向副本；客户端传入身份/预约号不能改变名单。错误策略拒绝访问。日志 access.jsonl 记录模拟核验/设备确认，特征删除后历史日志仍按保留期限管理。

## 回归验证

```powershell
python delivery/tests/test_face_pipeline.py
python week5/scripts/run_face_eval.py --self-test --output-dir D:/FaceResults/synthetic-01
```

第一条使用随机数组、注入的检测替身与统一 Flask 测试客户端验证异常和模拟闭环，不读取私人照片，不驱动 GPIO。第二条只验证匹配与指标逻辑，输出 `synthetic_logic_only`，不代表真实人脸准确率。
