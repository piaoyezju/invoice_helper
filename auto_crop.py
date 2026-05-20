"""
发票图片自动裁剪模块
从手机截图中自动裁出发票区域，去掉状态栏、浏览器栏等多余部分。

两步法:
1. 找二维码 → 采样周围背景色（发票白色背景）
2. 背景色遮罩 → 找包含二维码的连通区域 → 裁剪
"""

import cv2
import numpy as np
from PIL import Image


def auto_crop_invoice(input_path, padding=10):
    img = cv2.imread(input_path)
    if img is None:
        return None

    h, w = img.shape[:2]
    if w < 100 or h < 100:
        return None

    rect = _find_invoice_rect(img, w, h)
    if rect is None:
        return None

    x, y, bw, bh = rect
    x2 = min(x + bw, w)
    y2 = min(y + bh, h)
    cropped = img[max(0, y):y2, max(0, x):x2]

    if cropped.size == 0:
        return None

    if padding > 0:
        cropped = cv2.copyMakeBorder(cropped, padding, padding, padding, padding,
                                     cv2.BORDER_CONSTANT, value=(255, 255, 255))

    return Image.fromarray(cv2.cvtColor(cropped, cv2.COLOR_BGR2RGB))


def _find_invoice_rect(img, w, h):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 1. 找二维码
    qr = _find_qr_code(gray, w, h)
    if qr is None:
        return None

    qx, qy, qw, qh = qr

    # 2. 采样二维码外围背景色（不是中间的logo）
    bg_val = _sample_bg_around_qr(gray, qr, w, h)
    if bg_val is None:
        return None

    # 3. 全图遮罩：与背景色接近的像素
    tolerance = 12
    diff = np.abs(gray.astype(int) - int(bg_val))
    mask = (diff < tolerance).astype(np.uint8) * 255

    # 把二维码区域填白，确保连通
    mask[qy:qy + qh, qx:qx + qw] = 255

    # 排除深色文字
    mask[gray < 140] = 0

    # 排除红色边框/印章（作为连通屏障，把发票内外隔开）
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    r1 = cv2.inRange(hsv, np.array([0, 40, 50]), np.array([15, 255, 255]))
    r2 = cv2.inRange(hsv, np.array([165, 40, 50]), np.array([180, 255, 255]))
    red_pixels = (r1 | r2).astype(np.uint8)
    mask[red_pixels > 0] = 0

    # 连通域分析
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
        mask, connectivity=8)

    if num_labels <= 1:
        return None

    # 找包含QR中心的连通区域
    qr_cx = qx + qw // 2
    qr_cy = qy + qh // 2

    for i in range(1, num_labels):
        x = stats[i, cv2.CC_STAT_LEFT]
        y = stats[i, cv2.CC_STAT_TOP]
        bw = stats[i, cv2.CC_STAT_WIDTH]
        bh = stats[i, cv2.CC_STAT_HEIGHT]
        if x <= qr_cx <= x + bw and y <= qr_cy <= y + bh:
            if bw < w * 0.1 or bh < h * 0.05:
                return None
            return (x, y, bw, bh)

    return None


def _find_qr_code(gray, w, h):
    """找二维码位置。先用pyzbar，失败则用方差扫描"""
    # pyzbar
    try:
        from pyzbar.pyzbar import decode
        codes = decode(Image.fromarray(gray))
        if codes:
            qr = codes[0]
            return (qr.rect.left, qr.rect.top, qr.rect.width, qr.rect.height)
    except ImportError:
        pass

    # 回退: 扫描上半部分左半侧，找方差最大的正方形区域
    search_h = h // 2
    search_w = w // 2  # QR通常在左半边
    best_score = 0
    best_rect = None
    for size in range(70, 180, 10):
        step = max(size // 2, 15)
        for y in range(0, search_h - size, step):
            for x in range(0, search_w - size, step):
                block = gray[y:y + size, x:x + size]
                if block.shape[0] < size or block.shape[1] < size:
                    continue
                v = float(np.var(block))
                dark_pct = np.mean(block < 128)
                if v > 3000 and 0.25 < dark_pct < 0.7:
                    score = v * (1 - abs(dark_pct - 0.5))
                    if score > best_score:
                        best_score = score
                        best_rect = (x, y, size, size)

    return best_rect


def _sample_bg_around_qr(gray, qr_rect, w, h):
    """从二维码四条边外侧采样背景色（避开QR内部logo）"""
    qx, qy, qw, qh = qr_rect
    samples = []

    # 上方: QR上边缘外侧
    for d in [5, 8, 12]:
        sy = qy - d
        if sy >= 1:
            roi = gray[sy - 1:sy + 2, max(0, qx + 5):min(w, qx + qw - 5)]
            if roi.size > 0:
                samples.append(float(np.mean(roi)))

    # 左方: QR左边缘外侧
    for d in [5, 8, 12]:
        sx = qx - d
        if sx >= 1:
            roi = gray[max(0, qy + 5):min(h, qy + qh - 5), sx - 1:sx + 2]
            if roi.size > 0:
                samples.append(float(np.mean(roi)))

    # 右方: QR右边缘外侧
    for d in [5, 8, 12]:
        sx = qx + qw + d
        if sx < w:
            roi = gray[max(0, qy + 5):min(h, qy + qh - 5), max(0, sx - 1):min(w, sx + 2)]
            if roi.size > 0:
                samples.append(float(np.mean(roi)))

    # 下方: QR下边缘外侧
    for d in [5, 8, 12]:
        sy = qy + qh + d
        if sy < h:
            roi = gray[max(0, sy - 1):min(h, sy + 2), max(0, qx + 5):min(w, qx + qw - 5)]
            if roi.size > 0:
                samples.append(float(np.mean(roi)))

    if not samples:
        return None

    # 取最大值（白色背景）
    bg_val = max(samples)
    if bg_val < 200:
        return None
    return bg_val
