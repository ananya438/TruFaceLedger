import os
import hashlib
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
import cv2
import numpy as np
from PIL import Image

try:
    import face_recognition
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    face_recognition = None
    FACE_RECOGNITION_AVAILABLE = False


def calculate_file_sha256(file_path: str) -> str:
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()


def calculate_data_sha256(data: Any) -> str:
    if isinstance(data, (list, dict)):
        serialized = json.dumps(data, sort_keys=True).encode("utf-8")
    elif isinstance(data, str):
        serialized = data.encode("utf-8")
    elif isinstance(data, bytes):
        serialized = data
    else:
        serialized = str(data).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def compute_vector_similarity(vec1: List[float], vec2: List[float]) -> float:
    if not vec1 or not vec2:
        return 0.0
    a = np.array(vec1, dtype=np.float32)
    b = np.array(vec2, dtype=np.float32)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def extract_encoding_from_array(img_array: np.ndarray) -> Optional[List[float]]:
    try:
        if FACE_RECOGNITION_AVAILABLE and face_recognition is not None:
            rgb = cv2.cvtColor(img_array, cv2.COLOR_BGR2RGB) if len(img_array.shape) == 3 else img_array
            locations = face_recognition.face_locations(rgb)
            if locations:
                encs = face_recognition.face_encodings(rgb, locations)
                if encs:
                    return encs[0].tolist()
        
        gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY) if len(img_array.shape) == 3 else img_array
        cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=3, minSize=(20, 20))
        
        if len(faces) > 0:
            x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
            face_roi = cv2.resize(gray[y:y+h, x:x+w], (64, 64))
        else:
            face_roi = cv2.resize(gray, (64, 64))
            
        hist = cv2.calcHist([face_roi], [0], None, [128], [0, 256]).flatten()
        norm = np.linalg.norm(hist)
        return (hist / (norm if norm > 0 else 1.0)).tolist()
    except Exception:
        return None


def detect_and_encode_face(image_path: str, crop_output_dir: str = "crops") -> Dict[str, Any]:
    if not os.path.isfile(image_path):
        raise FileNotFoundError(f"Input image not found: {image_path}")

    image_hash = calculate_file_sha256(image_path)
    Path(crop_output_dir).mkdir(parents=True, exist_ok=True)
    crop_filename = f"face_crop_{Path(image_path).stem}.jpg"
    crop_path = os.path.join(crop_output_dir, crop_filename)

    cv_img = cv2.imread(image_path)
    if cv_img is None:
        raise ValueError(f"Could not read image: {image_path}")

    orig_h, orig_w = cv_img.shape[:2]
    scale_factor = 1.0
    proc_img = cv_img

    if orig_w < 600 or orig_h < 600:
        scale_factor = 3.0
        proc_img = cv2.resize(cv_img, (int(orig_w * scale_factor), int(orig_h * scale_factor)), interpolation=cv2.INTER_CUBIC)

    gray = cv2.cvtColor(proc_img, cv2.COLOR_BGR2GRAY)
    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    faces = cascade.detectMultiScale(gray, scaleFactor=1.08, minNeighbors=3, minSize=(20, 20))

    if len(faces) == 0:
        alt_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_alt2.xml")
        faces = alt_cascade.detectMultiScale(gray, scaleFactor=1.08, minNeighbors=2, minSize=(15, 15))

    if len(faces) == 0:
        return {
            "success": False,
            "face_count": 0,
            "image_hash": image_hash,
            "face_encoding": None,
            "face_encoding_hash": None,
            "bounding_box": None,
            "crop_path": None,
            "engine": "opencv_haar_cascade",
            "error": "No face detected in the provided image. Please provide a clear portrait photo."
        }

    x_s, y_s, w_s, h_s = max(faces, key=lambda f: f[2] * f[3])
    x = int(x_s / scale_factor)
    y = int(y_s / scale_factor)
    w = int(w_s / scale_factor)
    h = int(h_s / scale_factor)

    pad_y, pad_x = int(h * 0.1), int(w * 0.1)
    face_crop_cv = cv_img[max(0, y - pad_y):min(orig_h, y + h + pad_y), max(0, x - pad_x):min(orig_w, x + w + pad_x)]
    cv2.imwrite(crop_path, face_crop_cv)

    face_roi_gray = cv2.resize(gray[y_s:y_s+h_s, x_s:x_s+w_s], (64, 64))
    hist = cv2.calcHist([face_roi_gray], [0], None, [128], [0, 256]).flatten()
    norm = np.linalg.norm(hist)
    normalized_encoding = (hist / (norm if norm > 0 else 1.0)).tolist()

    return {
        "success": True,
        "face_count": len(faces),
        "image_hash": image_hash,
        "face_encoding": normalized_encoding,
        "face_encoding_hash": calculate_data_sha256(normalized_encoding),
        "bounding_box": {"top": int(y), "right": int(x + w), "bottom": int(y + h), "left": int(x)},
        "crop_path": crop_path,
        "engine": "opencv_haar_cascade",
        "error": None
    }
