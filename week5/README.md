# 第5-6周项目实践作业提交说明（week5）

本文件夹为《智能会议室管理系统III》第5周与第6周（验收周）人脸识别 + 3D 优化任务的全部提交内容，与本组综II人脸识别服务（`human_face/face_api.py`）、门禁系统（`chapter9/10 smart_door_system*.py`）、3D 场景（`Room3D`）配套。

```
week5/
├── data/
│   ├── face_sample_manifest.csv     # 样本清单与授权/脱敏记录（≥3人×≥10张）
│   ├── authorization_template.md    # 人脸数据采集与使用授权同意书（模板）
│   └── （样本照片不入库，存放于本地私有存储，路径见 manifest）
├── scripts/
│   ├── preprocess_face.py           # 自研①：灰度化+尺寸归一化+直方图均衡化
│   ├── lbp_face.py                  # 自研②：分块均匀LBP特征+余弦比对+阈值判定
│   ├── run_face_eval.py             # 测试集评估：准确率/FAR/FRR/混淆矩阵/阈值标定
│   ├── collect_face_samples.py      # 样本采集脚本（采集设备上运行）
│   └── blender_modify_scene.py      # Blender 建模/材质/灯光脚本（导出 room_301.glb）
├── docs/
│   ├── face_recognition_flow.md     # 7步流程图说明（输入/输出/判定依据）
│   ├── face_flow.svg                # 流程图（图片）
│   ├── data_authorization.md        # 样本集说明 + 授权/脱敏记录
│   ├── algorithm_notes.md           # 算法说明 + 改进理由 + 课堂问题1/2/3回答
│   ├── business_linkage.md          # 业务联动（登录/预约/权限/开门）+ 失败不放行
│   ├── 3d_optimization.md           # Blender/Unity 3D 优化方案 + ≥3类状态联动
│   ├── week5_weekly_plan.md         # 第5周推进计划
│   └── week6_weekly_plan.md         # 第6周推进计划（验收周）
├── 3d/
│   ├── scene_preview.html           # 3D 场景初版（浏览器打开，内嵌统一状态对象，
│   │                                #   演示人员/门/灯光/温湿度/报警状态联动）
│   ├── 场景截图_空闲.png            # 浏览器实测截图（空闲状态）
│   └── 场景截图_有人开门.png        # 浏览器实测截图（有人+开门状态，联动验证）
├── mock/
│   └── state.json                   # 统一状态对象（与 week3 一致，3D/Web 消费）
├── tests/
│   ├── face_test_protocol.md        # 测试协议（指标口径、失败不放行用例）
│   └── face_test_record.md          # 测试记录（算法自测已填写；真实集实测待硬件环境）
└── results/
    ├── face_eval_run.log            # 评估真实运行日志（算法自测）
    ├── face_eval_result.json        # 评估结果 JSON
    └── 阈值标定曲线.png             # 阈值扫描曲线（真实运行生成）
```

## 第5周交付内容对照

| 要求 | 交付物 |
| --- | --- |
| 流程图（7步：采集/注册→预处理→检测→特征→比对→阈值判断→业务动作，含输入/输出/判定依据） | `docs/face_flow.svg` + `docs/face_recognition_flow.md` |
| 样本集：≥3名对象×≥10张，按人分目录，授权与脱敏记录 | `data/face_sample_manifest.csv`、`docs/data_authorization.md`、`data/authorization_template.md` |
| 自研关键步骤（≥1，含源代码、算法说明、改进理由） | `scripts/preprocess_face.py`、`scripts/lbp_face.py`、`docs/algorithm_notes.md`（自研4项） |

## 第6周交付内容对照

| 要求 | 交付物 |
| --- | --- |
| 识别测试：本人/非本人，准确率/FAR/FRR/响应时间 | `scripts/run_face_eval.py`、`tests/face_test_protocol.md`、`tests/face_test_record.md`、`results/阈值标定曲线.png` |
| 业务联动：登录/预约/权限/开门至少1个闭环，失败不放行 | `docs/business_linkage.md`（门禁+登录双闭环，fail-closed） |
| 3D优化：Blender/Unity 模型、材质、灯光、相机、交互；≥3类状态随数据更新 | `scripts/blender_modify_scene.py`、`docs/3d_optimization.md`、`3d/scene_preview.html`（人员/门/温湿度/设备 4 类联动） |
| 周推进计划 | `docs/week5_weekly_plan.md`、`docs/week6_weekly_plan.md` |

## 课堂问题回答位置

- 问题1（为什么用别人的阈值不算自研）：`docs/algorithm_notes.md` 第三节
- 问题2（什么是特征、为什么换张照片还能认出同一人）：`docs/algorithm_notes.md` 第三节
- 问题3（什么是失败不放行）：`docs/algorithm_notes.md` 第三节 + `docs/business_linkage.md`

## 运行方式

```powershell
# 算法自测评估（已运行，可重跑）
cd week5
python scripts/run_face_eval.py

# 3D 场景初版（浏览器直接打开）
start 3d/scene_preview.html

# 真实人脸评估（需本地测试集，见 tests/face_test_protocol.md）
python scripts/run_face_eval.py --data-dir D:\face_data\test_set

# Blender 建模（需安装 Blender 3.x）
blender --background --python scripts/blender_modify_scene.py
```

## 数据真实性与待办说明

- 已真实运行并验证：算法自测评估（`results/face_eval_run.log`、`阈值标定曲线.png`）、3D 场景初版（浏览器实测通过，含截图 `3d/场景截图_*.png`）；
- 待硬件/现场执行后回填：真实人脸测试指标（本人/非本人、FAR/FRR/响应时间）、联动录屏、Blender 渲染图（记录模板均已就绪，见 `tests/face_test_record.md` 第三节，**不编造数据**）。
