import os

os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['PYTHONWARNINGS'] = 'ignore::UserWarning'

from deepface import DeepFace


def recognize_face(target_img_path, db_path, model_name, detector_backend, distance_metric, threshold):
    """
    在底库中搜索目标人脸，支持超参数配置
    """
    try:
        # DeepFace.find 默认会使用每个模型建议的官方阈值。
        # 传入 threshold 参数可以强制覆盖默认阈值，实现自定义的严格程度。
        dfs = DeepFace.find(
            img_path=target_img_path,
            db_path=db_path,
            model_name=model_name,
            detector_backend=detector_backend,
            distance_metric=distance_metric,
            threshold=threshold,  # 使用自定义的相似度(距离)阈值
            enforce_detection=True  # 确保抓拍图里真的有人脸
        )

        # dfs 是一个列表，如果图里有多个脸，列表长度就大于1。取第一张脸的匹配结果：
        if len(dfs) > 0 and not dfs[0].empty:
            # 结果已经按 distance 升序排好，第一行就是最相似的
            best_match = dfs[0].iloc[0]
            matched_image_path = best_match['identity']
            distance = best_match['distance']

            print(f"✅ 匹配成功！")
            print(f"   👤 识别人员: {matched_image_path}")
            print(f"   📏 距离得分: {distance:.4f} (当前阈值上限: {threshold})")
            return True, matched_image_path
        else:
            print(f"❌ 匹配失败：得分未达到阈值 {threshold}，或数据库中无此人（陌生人）。")
            return False, None

    except ValueError as e:
        print(f"⚠️ 流程异常: {e}")
        return False, None
    except Exception as e:
        print(f"❌ 发生未知错误: {e}")
        return False, None


if __name__ == "__main__":
    # ==========================================
    # ⚙️ 路径与超参数配置区
    # ==========================================
    DB_PATH = "./id"  # 底库文件夹路径
    TARGET_IMG = "./test/test_1.png"  # 现场抓拍的测试图片路径

    # 1. 模型与检测器
    MODEL_NAME = "ArcFace"  # 特征提取模型
    DETECTOR = "retinaface"  # 人脸检测器

    # 2. 距离度量方式 (可选: "cosine", "euclidean", "euclidean_l2")
    # 推荐使用 cosine (余弦距离)。注意：这里计算的是“距离”，所以越小越相似！
    METRIC = "cosine"

    # 3. 自定义阈值 (Threshold)
    # ArcFace 使用 cosine 时的官方默认阈值是 0.68。
    # 距离 < 阈值 = 认为是同一个人。
    # 如果你希望会议室门禁更严格（宁可认不出，不能认错人），请把阈值调小，比如 0.50 或 0.45。
    CUSTOM_THRESHOLD = 0.8

    # ==========================================
    # 🚀 执行比对
    # ==========================================
    print("-" * 40)
    print(f"🔍 正在检索: {TARGET_IMG}")
    print(f"⚙️  配置: {MODEL_NAME} + {DETECTOR} | 度量: {METRIC} | 严格阈值: {CUSTOM_THRESHOLD}")
    print("-" * 40)

    is_match, identity = recognize_face(
        target_img_path=TARGET_IMG,
        db_path=DB_PATH,
        model_name=MODEL_NAME,
        detector_backend=DETECTOR,
        distance_metric=METRIC,
        threshold=CUSTOM_THRESHOLD
    )
