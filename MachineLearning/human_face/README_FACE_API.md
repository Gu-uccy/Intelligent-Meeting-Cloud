# 自研人脸服务与模拟门禁

当前主路径：OpenCV Haar 单脸检测 → 自研灰度/双线性缩放/直方图均衡化 → 自研 7×7 uniform LBP（2891维）→ 余弦比对 → 服务端有效预约名单 → 统一 Flask 模拟门指令 → 设备确认 → 模拟签到日志。未检测到单脸、陌生人、无预约、未审核/过期/房间不符、阈值缺失、设备错误均不确认放行。

这是课堂实验，没有活体检测，也未完成真实样本标定。人脸服务只允许对 `source=simulation` 的统一服务发送门指令；不会控制实物门。手动门灯控制仍由原有统一传感器接口提供。模拟签到记录在本地 JSONL，不写入 Spring 预约数据库。网页不能自己决定放行。

## 启动

在仓库根目录运行，不能单独复制 `face_api.py`（它依赖仓库中的自研模块）：

```powershell
python -m pip install -r MachineLearning/human_face/requirements.txt
python MachineLearning/human_face/face_api.py
```

默认 `127.0.0.1:5001`；`GET /health`。Demo 一键启动会同时启动本服务。默认无阈值、空底库、空预约，拒绝放行是预期行为。不会读取旧 `id/` 和 `test/` 私人图片。

## 授权样本到评估

先完成 `week5/docs/data_authorization.md`。在仓库外复制空清单，填写 `path,identity,split,kind`；split 为 enroll/calibration/test，kind 为 known/unknown。每个 known 身份至少10张且三个划分都有照片；unknown 身份不能入库。脚本拒绝相同内容跨行、越界路径、缺少未知测试集等情况。无脸或多脸图像会报错，需在清单中修正并记录排除理由，不能静默跳过。

```powershell
python week5/scripts/run_face_eval.py --data-dir D:/AuthorizedFaces --manifest D:/AuthorizedFaces/manifest.csv --authorized --output-dir D:/FaceResults/run-01
```

结果包含独立标定集阈值扫描、冻结阈值的最终测试、accuracy/FAR/FRR、错误身份数和机器环境。耗时包括读取/检测/预处理/LBP/比对，HTTP 与设备响应耗时另看 `/verify` 的 pipeline_ms。应在最终目标设备上跑评估；本机结果不能称树莓派结果。无合格 FAR 阈值时不生成可放行结论。

## 配置与接口

所有设置在启动服务前通过环境变量配置：`FACE_DATA_DIR`（特征和匿名日志私有目录）、`FACE_ADMIN_TOKEN`（录入/删除管理令牌）、`FACE_THRESHOLD`（授权标定后才填写）、`FACE_POLICY_PATH`（私有预约策略 JSON）、`FACE_DEVICE_URL`（默认 http://127.0.0.1:5058）、`FACE_API_PORT`、`FACE_HOST`（默认仅本机）。不要把管理令牌写进前端 VITE 环境变量、截图或 Git。

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
