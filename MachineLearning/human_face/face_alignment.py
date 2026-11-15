"""Five-landmark similarity alignment; NumPy fit, OpenCV image resampling."""
import cv2
import numpy as np

# Same standard 112x112 reference geometry documented in OpenCV FaceRecognizerSF.
# https://github.com/opencv/opencv/blob/4.13.0/modules/objdetect/src/face_recognize.cpp
REFERENCE_POINTS = np.array([[38.2946,51.6963],[73.5318,51.5014],[56.0252,71.7366],
                             [41.5493,92.3655],[70.7299,92.2041]],dtype=np.float64)


def similarity_transform(source, target=REFERENCE_POINTS):
    """Least-squares rotation, positive uniform scale and translation; no reflection."""
    source, target = np.asarray(source,dtype=float), np.asarray(target,dtype=float)
    if source.shape != (5,2) or target.shape != (5,2) or not np.isfinite(source).all() or not np.isfinite(target).all():
        raise ValueError('Invalid five face landmarks')
    source_mean, target_mean = source.mean(axis=0), target.mean(axis=0)
    a, b = source-source_mean, target-target_mean
    if np.linalg.matrix_rank(a) < 2 or np.linalg.matrix_rank(b) < 2:
        raise ValueError('Degenerate face landmarks')
    u, singular, vt = np.linalg.svd(a.T @ b)
    sign = np.ones(2)
    if np.linalg.det(vt.T @ u.T) < 0:
        sign[-1] = -1
    rotation = vt.T @ np.diag(sign) @ u.T
    variance = np.sum(a*a)
    scale = np.dot(singular,sign)/variance
    if not np.isfinite(scale) or scale <= 0:
        raise ValueError('Invalid face alignment scale')
    linear = scale*rotation
    translation = target_mean-linear@source_mean
    transform = np.column_stack((linear,translation))
    if not np.isfinite(transform).all():
        raise ValueError('Invalid face alignment transform')
    return transform


def align_single_face(image, faces, template_scale=1.0):
    if template_scale not in (.85,1.0,1.15):
        raise ValueError('Alignment scale must be 0.85, 1.0 or 1.15')
    if len(faces) != 1:
        raise ValueError(f'Exactly one detectable face is required (found {len(faces)})')
    face = np.asarray(faces[0],dtype=float)
    if face.shape != (15,) or not np.isfinite(face).all():
        raise ValueError('Invalid face landmarks')
    points=face[4:14].reshape(5,2)
    h,w=image.shape[:2]
    if np.any(points < 0) or np.any(points[:,0] >= w) or np.any(points[:,1] >= h):
        raise ValueError('Face landmarks outside the image')
    if np.linalg.norm(points[0]-points[1]) < 1:
        raise ValueError('Degenerate face landmarks')
    target=56+(REFERENCE_POINTS-56)*template_scale
    transform=similarity_transform(points,target)
    return cv2.warpAffine(image,transform,(112,112),flags=cv2.INTER_LINEAR,
                          borderMode=cv2.BORDER_CONSTANT,borderValue=0)
