"""OpenCV detectors with original-image coordinates and pinned model provenance."""
import hashlib
import math
from pathlib import Path
import threading

import cv2
import numpy as np

MODEL_PATH = Path(__file__).resolve().parent / 'models/face_detection_yunet_2023mar.onnx'
MODEL_SHA256 = '8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4'
DEFAULT_DETECTOR = 'yunet-06'


class YuNetDetector:
    backend = 'opencv-yunet-2023mar'
    # Frozen before the CMU development comparison; detection score is NOT an identity threshold.
    score_threshold = .9
    nms_threshold = .3
    min_long_side = 320
    max_long_side = 960
    profile = f'yunet-{MODEL_SHA256[:12]}-s09-n03-resize320-960-bbox-lbp-v1'

    def __init__(self, model_path=MODEL_PATH, score_threshold=.9):
        if not 0 < score_threshold < 1:
            raise ValueError('Invalid detection score threshold')
        self.score_threshold = score_threshold
        self.profile = f'yunet-{MODEL_SHA256[:12]}-s{score_threshold:g}-n03-resize320-960-bbox-lbp-v1'
        path = Path(model_path)
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != MODEL_SHA256:
            raise ValueError('YuNet model missing or hash mismatch; restore the bundled official model')
        self._detector = cv2.FaceDetectorYN.create(str(path), '', (320, 320),
                                                 self.score_threshold, self.nms_threshold, 5000)
        self._lock = threading.Lock()

    @classmethod
    def input_size(cls, width, height):
        longest = max(width, height)
        scale = min(cls.max_long_side, max(cls.min_long_side, longest)) / longest
        return max(1, round(width * scale)), max(1, round(height * scale))

    def detect(self, image):
        height, width = image.shape[:2]
        size = self.input_size(width, height)
        resized = cv2.resize(image, size, interpolation=cv2.INTER_LINEAR) if size != (width, height) else image
        # OpenCV stores mutable input size and DNN buffers; protect concurrent requests.
        with self._lock:
            self._detector.setInputSize(size)
            _, faces = self._detector.detect(resized)
        if faces is None:
            return np.empty((0, 4), dtype=float)
        faces = np.asarray(faces, dtype=float)
        if faces.ndim != 2 or faces.shape[1] < 15 or not np.isfinite(faces).all():
            raise ValueError('Invalid face detector output')
        # Retain every above-threshold face. Do not pick the largest and hide a second person.
        faces = faces[faces[:, 14] >= self.score_threshold]
        boxes = faces[:, :4].copy()
        boxes *= np.array([width / size[0], height / size[1]] * 2)
        return boxes


class HaarDetector:
    backend = 'opencv-haar'
    profile = 'haar-front-s11-n5-min60-bbox-lbp-v1'

    def __init__(self, small_faces=False):
        self.scale_factor = 1.05 if small_faces else 1.1
        self.min_size = (24, 24) if small_faces else (60, 60)
        if small_faces:
            self.backend = 'opencv-haar-small'
            self.profile = 'haar-front-s105-n5-min24-bbox-lbp-v1'
        self._detector = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self._lock = threading.Lock()

    def detect(self, image):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        with self._lock:
            boxes = self._detector.detectMultiScale(gray, scaleFactor=self.scale_factor, minNeighbors=5, minSize=self.min_size)
        return np.asarray(boxes, dtype=float).reshape(-1, 4)


def create_detector(backend):
    if backend == 'yunet':
        return YuNetDetector()
    if backend == 'haar':
        return HaarDetector()
    if backend == 'haar-small':
        return HaarDetector(small_faces=True)
    if backend == 'yunet-07':
        return YuNetDetector(score_threshold=.7)
    if backend == 'yunet-06':
        return YuNetDetector(score_threshold=.6)
    raise ValueError('FACE_DETECTOR must be yunet-06, yunet-07, yunet, haar or haar-small')


def crop_single_face(image, boxes):
    if len(boxes) != 1:
        raise ValueError(f'Exactly one detectable face is required (found {len(boxes)})')
    x, y, width, height = map(float, boxes[0])
    if not all(math.isfinite(v) for v in (x, y, width, height)) or width <= 0 or height <= 0:
        raise ValueError('Invalid face bounds')
    ih, iw = image.shape[:2]
    x0, y0 = max(0, math.floor(x)), max(0, math.floor(y))
    x1, y1 = min(iw, math.ceil(x + width)), min(ih, math.ceil(y + height))
    if x1 <= x0 or y1 <= y0:
        raise ValueError('Face bounds are outside the image')
    return image[y0:y1, x0:x1]
