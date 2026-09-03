"""
Synthetic parcel plan training image generator.

Generates images with known ground truth for beacon detection,
boundary segmentation, and feature classification.
"""

import math
import random
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BEACON_TYPES = ("iron_pin", "concrete", "triangle", "unknown")
NUM_BEACON_CLASSES = len(BEACON_TYPES)

# Feature segmentation classes
# 0: background, 1: boundary_line, 2: beacon, 3: road,
# 4: residential, 5: agricultural, 6: commercial, 7: water, 8: vegetation
NUM_FEATURE_CLASSES = 9
FEATURE_COLORS: list[tuple[int, int, int]] = [
    (245, 240, 230),   # 0 background – beige
    (30, 30, 30),      # 1 boundary – near-black
    (200, 0, 0),       # 2 beacon – red
    (100, 100, 100),   # 3 road – grey
    (180, 130, 200),   # 4 residential – light purple
    (140, 200, 80),    # 5 agricultural – green
    (200, 160, 60),    # 6 commercial – amber
    (60, 140, 220),    # 7 water – blue
    (30, 160, 60),     # 8 vegetation – dark green
]

# Beacon shape colours per type
BEACON_FILL: dict[str, tuple[int, int, int]] = {
    "iron_pin": (80, 80, 80),
    "concrete": (190, 190, 180),
    "triangle": (160, 80, 40),
    "unknown": (120, 120, 120),
}

DEFAULT_GRID_SIZE = 16
YOLO_CHANNELS = 9  # obj, cx, cy, w, h, class0..class3


# ---------------------------------------------------------------------------
# Random helpers
# ---------------------------------------------------------------------------

def _rand_range(lo: float, hi: float) -> float:
    return random.uniform(lo, hi)


def _rand_int(lo: int, hi: int) -> int:
    return random.randint(lo, hi)


def _random_polygon(size: int, num_vertices: int | None = None) -> list[tuple[int, int]]:
    """Return list of (x, y) vertices forming a convex-ish polygon."""
    if num_vertices is None:
        num_vertices = _rand_int(4, 8)
    cx = _rand_int(size // 4, 3 * size // 4)
    cy = _rand_int(size // 4, 3 * size // 4)
    radius = _rand_int(size // 6, size // 3)
    angles = sorted(random.uniform(0, 2 * math.pi) for _ in range(num_vertices))
    return [
        (
            int(cx + radius * math.cos(a) + random.uniform(-size // 20, size // 20)),
            int(cy + radius * math.sin(a) + random.uniform(-size // 20, size // 20)),
        )
        for a in angles
    ]


def _clamp_point(x: int, y: int, size: int) -> tuple[int, int]:
    return (max(0, min(x, size - 1)), max(0, min(y, size - 1)))


# ---------------------------------------------------------------------------
# Drawing primitives
# ---------------------------------------------------------------------------

def _draw_boundary(draw: ImageDraw.ImageDraw, polygon: list[tuple[int, int]], width: int = 2) -> None:
    for i in range(len(polygon)):
        p1 = polygon[i]
        p2 = polygon[(i + 1) % len(polygon)]
        draw.line([p1, p2], fill=FEATURE_COLORS[1], width=width)


def _draw_beacon_marker(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    beacon_type: str,
    radius: int = 6,
) -> None:
    fill = BEACON_FILL.get(beacon_type, (120, 120, 120))
    if beacon_type == "iron_pin":
        draw.ellipse([x - radius, y - radius, x + radius, y + radius], fill=fill, outline=(40, 40, 40))
        draw.ellipse([x - 2, y - 2, x + 2, y + 2], fill=(200, 200, 200))
    elif beacon_type == "concrete":
        s = radius
        draw.rectangle([x - s, y - s, x + s, y + s], fill=fill, outline=(140, 140, 140))
    elif beacon_type == "triangle":
        pts = [(x, y - radius), (x - radius, y + radius), (x + radius, y + radius)]
        draw.polygon(pts, fill=fill, outline=(100, 50, 20))
    else:
        draw.ellipse([x - radius, y - radius, x + radius, y + radius], fill=fill, outline=(80, 80, 80))


def _draw_text_label(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    text: str,
    size: int,
) -> None:
    try:
        font = ImageFont.truetype("arial.ttf", _rand_int(8, 14))
    except OSError:
        font = ImageFont.load_default()
    tx = x + _rand_int(5, 20)
    ty = y + _rand_int(-10, 10)
    tx, ty = _clamp_point(tx, ty, size)
    draw.text((tx, ty), text, fill=(50, 50, 180), font=font)


def _draw_road(draw: ImageDraw.ImageDraw, size: int) -> None:
    x0, y0 = _rand_int(0, size), _rand_int(0, size)
    x1, y1 = _rand_int(0, size), _rand_int(0, size)
    w = _rand_int(3, 8)
    draw.line([(x0, y0), (x1, y1)], fill=FEATURE_COLORS[3], width=w)


def _draw_land_use_region(
    draw: ImageDraw.ImageDraw,
    size: int,
    feature_class: int,
) -> None:
    """Draw a random filled ellipse as a land-use region."""
    cx = _rand_int(size // 6, 5 * size // 6)
    cy = _rand_int(size // 6, 5 * size // 6)
    rx = _rand_int(size // 10, size // 4)
    ry = _rand_int(size // 10, size // 4)
    fill = FEATURE_COLORS[feature_class]
    draw.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=fill)


# ---------------------------------------------------------------------------
# YOLO target construction
# ---------------------------------------------------------------------------

def _build_yolo_targets(
    beacons: list[dict[str, Any]],
    image_size: int,
    grid_size: int,
) -> np.ndarray:
    """Return (grid_size, grid_size, YOLO_CHANNELS) target tensor."""
    targets = np.zeros((grid_size, grid_size, YOLO_CHANNELS), dtype=np.float64)
    cell = image_size / grid_size

    for b in beacons:
        cx_px = b["x"]
        cy_px = b["y"]
        gw = b.get("w", 12) / image_size
        gh = b.get("h", 12) / image_size
        gc = int(b["class_id"])

        col = int(cx_px / cell)
        row = int(cy_px / cell)
        col = max(0, min(col, grid_size - 1))
        row = max(0, min(row, grid_size - 1))

        ox = (cx_px - col * cell) / cell
        oy = (cy_px - row * cell) / cell

        targets[row, col, 0] = 1.0          # objectness
        targets[row, col, 1] = ox            # cx offset
        targets[row, col, 2] = oy            # cy offset
        targets[row, col, 3] = gw            # w
        targets[row, col, 4] = gh            # h
        for k in range(NUM_BEACON_CLASSES):
            targets[row, col, 5 + k] = 1.0 if k == gc else 0.0

    return targets


# ---------------------------------------------------------------------------
# Segmentation mask builders
# ---------------------------------------------------------------------------

def _build_boundary_mask(
    size: int,
    polygon: list[tuple[int, int]],
    beacons: list[dict[str, Any]],
) -> np.ndarray:
    """Return (H, W) int32 mask: 0=bg, 1=boundary, 2=beacon."""
    img = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(img)
    for i in range(len(polygon)):
        p1 = polygon[i]
        p2 = polygon[(i + 1) % len(polygon)]
        draw.line([p1, p2], fill=1, width=3)
    mask = np.array(img, dtype=np.int32)
    for b in beacons:
        r = 6
        y_lo = max(0, b["y"] - r)
        y_hi = min(size, b["y"] + r + 1)
        x_lo = max(0, b["x"] - r)
        x_hi = min(size, b["x"] + r + 1)
        mask[y_lo:y_hi, x_lo:x_hi] = 2
    return mask


def _build_feature_mask(
    size: int,
    polygon: list[tuple[int, int]],
    beacons: list[dict[str, Any]],
    roads: list[tuple[tuple[int, int], tuple[int, int]]],
    land_regions: list[tuple[int, tuple[int, int, int, int]]],
) -> np.ndarray:
    """Return (H, W) int32 mask with NUM_FEATURE_CLASSES labels."""
    img = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(img)

    # land-use regions first (under everything)
    for cls, (cx, cy, rx, ry) in land_regions:
        draw.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=cls)

    # roads
    for p1, p2 in roads:
        draw.line([p1, p2], fill=3, width=_rand_int(3, 8))

    # boundaries
    for i in range(len(polygon)):
        p1 = polygon[i]
        p2 = polygon[(i + 1) % len(polygon)]
        draw.line([p1, p2], fill=1, width=3)

    # beacons
    for b in beacons:
        r = 6
        draw.rectangle([b["x"] - r, b["y"] - r, b["x"] + r, b["y"] + r], fill=2)

    return np.array(img, dtype=np.int32)


# ---------------------------------------------------------------------------
# Augmentation helpers
# ---------------------------------------------------------------------------

def _augment_rotation(
    image: Image.Image,
    bnd_mask: Image.Image,
    feat_mask: Image.Image,
    angle_deg: float,
) -> tuple[Image.Image, Image.Image, Image.Image]:
    image = image.rotate(angle_deg, resample=Image.BILINEAR, fillcolor=FEATURE_COLORS[0])
    bnd_mask = bnd_mask.rotate(angle_deg, resample=Image.NEAREST, fillcolor=0)
    feat_mask = feat_mask.rotate(angle_deg, resample=Image.NEAREST, fillcolor=0)
    return image, bnd_mask, feat_mask


def _augment_brightness_contrast(
    image: Image.Image,
    brightness: float,
    contrast: float,
) -> Image.Image:
    arr = np.array(image, dtype=np.float64)
    arr = (arr - 128.0) * contrast + 128.0 + brightness
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    return Image.fromarray(arr, "RGB")


def _augment_gaussian_noise(image: Image.Image, sigma: float) -> Image.Image:
    arr = np.array(image, dtype=np.float64)
    noise = np.random.normal(0, sigma, arr.shape)
    arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(arr, "RGB")


def _augment_elastic_deformation(
    image: Image.Image,
    bnd_mask: Image.Image,
    feat_mask: Image.Image,
    alpha: float = 20.0,
    sigma: float = 5.0,
) -> tuple[Image.Image, Image.Image, Image.Image]:
    size = image.size  # (W, H)
    h, w = size[1], size[0]

    dx = np.random.normal(0, sigma, (h, w)).astype(np.float32)
    dy = np.random.normal(0, sigma, (h, w)).astype(np.float32)
    from scipy.ndimage import gaussian_filter  # noqa: E402 – fall back to numpy if unavailable
    dx = gaussian_filter(dx, sigma) * alpha / sigma
    dy = gaussian_filter(dy, sigma) * alpha / sigma

    x_grid, y_grid = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    map_x = (x_grid + dx).clip(0, w - 1)
    map_y = (y_grid + dy).clip(0, h - 1)

    def _warp(img: Image.Image, is_mask: bool = False) -> Image.Image:
        arr = np.array(img)
        mode = "nearest" if is_mask else "bilinear"
        from PIL import Image as _Img
        out = _Img.fromarray(arr)
        # Use Pillow remap via transform not available, so use numpy indexing
        if is_mask:
            out_arr = arr[np.round(map_y).astype(int).clip(0, h - 1),
                          np.round(map_x).astype(int).clip(0, w - 1)]
        else:
            out_arr = arr[np.round(map_y).astype(int).clip(0, h - 1),
                          np.round(map_x).astype(int).clip(0, w - 1)]
        return Image.fromarray(out_arr)

    image = _warp(image, False)
    bnd_mask = _warp(bnd_mask, True)
    feat_mask = _warp(feat_mask, True)
    return image, bnd_mask, feat_mask


def _augment_perspective(
    image: Image.Image,
    bnd_mask: Image.Image,
    feat_mask: Image.Image,
    magnitude: float = 0.05,
) -> tuple[Image.Image, Image.Image, Image.Image]:
    w, h = image.size

    def _jitter() -> float:
        return random.uniform(-magnitude, magnitude) * w

    coeffs_image = [
        _jitter(), _jitter(),
        w + _jitter(), _jitter(),
        w + _jitter(), h + _jitter(),
        _jitter(), h + _jitter(),
    ]
    image = image.transform((w, h), Image.QUAD, coeffs_image, Image.BILINEAR)

    coeffs_mask = [
        _jitter(), _jitter(),
        w + _jitter(), _jitter(),
        w + _jitter(), h + _jitter(),
        _jitter(), h + _jitter(),
    ]
    bnd_mask = bnd_mask.transform((w, h), Image.QUAD, coeffs_mask, Image.NEAREST)
    feat_mask = feat_mask.transform((w, h), Image.QUAD, coeffs_mask, Image.NEAREST)
    return image, bnd_mask, feat_mask


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_parcel_batch(
    batch_size: int,
    image_size: int = 256,
    grid_size: int = DEFAULT_GRID_SIZE,
) -> dict[str, Any]:
    """Generate a batch of synthetic parcel plan training samples.

    Returns
    -------
    dict with keys:
        images        : np.ndarray  (N, H, W, 3)  float64, range [0, 255]
        beacon_targets: list of np.ndarray, each (grid_size, grid_size, 9) float64
        boundary_masks: np.ndarray  (N, H, W)     int32
        feature_masks : np.ndarray  (N, H, W)     int32
    """
    images: list[np.ndarray] = []
    beacon_targets: list[np.ndarray] = []
    boundary_masks_list: list[np.ndarray] = []
    feature_masks_list: list[np.ndarray] = []

    for _ in range(batch_size):
        img, bnd, feat, beacons = _generate_single(image_size, grid_size)
        yolo = _build_yolo_targets(beacons, image_size, grid_size)

        images.append(np.array(img, dtype=np.float64))
        beacon_targets.append(yolo)
        boundary_masks_list.append(bnd)
        feature_masks_list.append(feat)

    return {
        "images": np.stack(images, axis=0),
        "beacon_targets": beacon_targets,
        "boundary_masks": np.stack(boundary_masks_list, axis=0),
        "feature_masks": np.stack(feature_masks_list, axis=0),
    }


def _generate_single(
    size: int,
    grid_size: int,
) -> tuple[Image.Image, np.ndarray, np.ndarray, list[dict[str, Any]]]:
    """Generate one image with all annotations before batching."""
    bg = FEATURE_COLORS[0]
    image = Image.new("RGB", (size, size), bg)
    draw = ImageDraw.Draw(image)

    polygon = _random_polygon(size)
    _draw_boundary(draw, polygon, width=_rand_int(2, 4))

    # Generate beacons at polygon vertices
    beacons: list[dict[str, Any]] = []
    for idx, (vx, vy) in enumerate(polygon):
        vx_c, vy_c = _clamp_point(vx, vy, size)
        btype = random.choice(BEACON_TYPES)
        class_id = BEACON_TYPES.index(btype)
        radius = _rand_int(5, 8)
        _draw_beacon_marker(draw, vx_c, vy_c, btype, radius)
        beacons.append({
            "x": vx_c,
            "y": vy_c,
            "w": radius * 2,
            "h": radius * 2,
            "type": btype,
            "class_id": class_id,
        })

    # Optional: add 0-3 extra random beacons inside the polygon
    for _ in range(_rand_int(0, 3)):
        # pick a random point loosely inside
        cx = _rand_int(size // 6, 5 * size // 6)
        cy = _rand_int(size // 6, 5 * size // 6)
        btype = random.choice(BEACON_TYPES)
        class_id = BEACON_TYPES.index(btype)
        radius = _rand_int(5, 8)
        _draw_beacon_marker(draw, cx, cy, btype, radius)
        beacons.append({
            "x": cx,
            "y": cy,
            "w": radius * 2,
            "h": radius * 2,
            "type": btype,
            "class_id": class_id,
        })

    # Text labels near some beacons
    label_pool = [
        "P-1234", "LOT-56", "BLK-7", "REF-90", "PARCEL-A",
        "SEC-12", "UNIT-3", "BLDG-8", "N-45E", "S-30W",
    ]
    for b in beacons[: _rand_int(1, len(beacons))]:
        _draw_text_label(draw, b["x"], b["y"], random.choice(label_pool), size)

    # Road segments (1-3)
    roads: list[tuple[tuple[int, int], tuple[int, int]]] = []
    for _ in range(_rand_int(1, 3)):
        x0, y0 = _rand_int(0, size), _rand_int(0, size)
        x1, y1 = _rand_int(0, size), _rand_int(0, size)
        roads.append(((x0, y0), (x1, y1)))
        _draw_road(draw, size)

    # Land-use regions (2-5)
    land_classes = list(range(4, NUM_FEATURE_CLASSES))  # 4..8
    land_regions: list[tuple[int, tuple[int, int, int, int]]] = []
    for _ in range(_rand_int(2, 5)):
        fc = random.choice(land_classes)
        cx = _rand_int(size // 6, 5 * size // 6)
        cy = _rand_int(size // 6, 5 * size // 6)
        rx = _rand_int(size // 10, size // 4)
        ry = _rand_int(size // 10, size // 4)
        land_regions.append((fc, (cx, cy, rx, ry)))
        _draw_land_use_region(draw, size, fc)

    # Build masks before augmentation
    bnd_mask_arr = _build_boundary_mask(size, polygon, beacons)
    feat_mask_arr = _build_feature_mask(size, polygon, beacons, roads, land_regions)

    bnd_mask_img = Image.fromarray(bnd_mask_arr.astype(np.uint8), mode="L")
    feat_mask_img = Image.fromarray(feat_mask_arr.astype(np.uint8), mode="L")

    # --- Data augmentation ---------------------------------------------------
    # Random rotation
    if random.random() < 0.8:
        angle = _rand_range(0, 360)
        image, bnd_mask_img, feat_mask_img = _augment_rotation(image, bnd_mask_img, feat_mask_img, angle)

    # Random brightness/contrast
    if random.random() < 0.7:
        brightness = _rand_range(-30, 30)
        contrast = _rand_range(0.7, 1.3)
        image = _augment_brightness_contrast(image, brightness, contrast)

    # Random Gaussian noise
    if random.random() < 0.5:
        sigma = _rand_range(1.0, 5.0)
        image = _augment_gaussian_noise(image, sigma)

    # Small random elastic deformation
    if random.random() < 0.3:
        try:
            image, bnd_mask_img, feat_mask_img = _augment_elastic_deformation(
                image, bnd_mask_img, feat_mask_img, alpha=15.0, sigma=4.0
            )
        except ImportError:
            pass  # scipy not available – skip

    # Random perspective
    if random.random() < 0.3:
        image, bnd_mask_img, feat_mask_img = _augment_perspective(
            image, bnd_mask_img, feat_mask_img, magnitude=0.04
        )

    # Final masks
    bnd_final = np.array(bnd_mask_img, dtype=np.int32)
    feat_final = np.array(feat_mask_img, dtype=np.int32)

    return image, bnd_final, feat_final, beacons
