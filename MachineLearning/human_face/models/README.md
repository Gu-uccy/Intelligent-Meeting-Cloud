# YuNet检测模型

模型来自 [OpenCV Zoo](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet)，2023mar版本供OpenCV4.x FaceDetectorYN使用。文件232589字节，SHA256 `8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4`，应用初始化校验哈希。固定上游提交、下载URL及许可哈希见 `yunet-provenance.json`，MIT版权与许可全文见 `LICENSE-YuNet.txt`。

这是预训练检测模型，不是参与者照片或识别特征库。仅替换检测环节，项目自研预处理、2891维LBP与余弦比对保留，不宣称本组训练或自研YuNet。启动不联网，模型缺失/校验失败直接报错。

服务默认 `FACE_DETECTOR=yunet-06`，检测分数0.6、NMS0.3，输入长边320–960且保持比例。保留 `yunet`（0.9）、`yunet-07`（0.7）、`haar-small`、`haar`（旧基线）。检测分数不是身份相似度阈值，所有模式均要求恰好一脸。选择与限制见 [改进记录](../../../analysis/face-detection-2026-11-15/README.md)。
