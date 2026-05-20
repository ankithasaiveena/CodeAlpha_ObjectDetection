import cv2
from ultralytics import YOLO
import numpy as np
import random
import math
from datetime import datetime

# ═══════════════════════════════════════════════
#   VISIONTRACK PRO — AI Object Detection
#   Futuristic HUD with Neon Cyberpunk Theme
# ═══════════════════════════════════════════════

print("┌─────────────────────────────────────┐")
print("│   VISIONTRACK PRO  v2.0             │")
print("│   AI Object Detection & Tracking    │")
print("│   Loading Neural Network...         │")
print("└─────────────────────────────────────┘")

model = YOLO("yolov8m.pt")
print("✅ Neural Network Ready!")

# ── NEON COLOR PALETTE ───────────────────────────
NEON_COLORS = [
    (0,   255, 255),   # Cyan
    (255,  0,  255),   # Magenta
    (0,   255, 128),   # Green
    (255, 165,   0),   # Orange
    (0,   128, 255),   # Blue
    (255, 255,   0),   # Yellow
    (128,   0, 255),   # Purple
    (255,  64,  64),   # Red
    (64,  255, 128),   # Mint
    (255, 128,   0),   # Amber
]

class_colors = {}
track_history  = {}
scan_angle     = 0
frame_count    = 0
screenshot_n   = 0
paused         = False
prev_tick      = 0

def neon_color(class_id):
    if class_id not in class_colors:
        class_colors[class_id] = NEON_COLORS[class_id % len(NEON_COLORS)]
    return class_colors[class_id]

# ── DRAWING HELPERS ──────────────────────────────

def glow_line(img, p1, p2, color, thickness=1):
    """Line with soft glow effect"""
    overlay = img.copy()
    cv2.line(overlay, p1, p2, color, thickness + 4)
    cv2.addWeighted(overlay, 0.3, img, 0.7, 0, img)
    cv2.line(img, p1, p2, color, thickness)

def glow_circle(img, center, radius, color, thickness=1):
    overlay = img.copy()
    cv2.circle(overlay, center, radius + 3, color, thickness + 2)
    cv2.addWeighted(overlay, 0.25, img, 0.75, 0, img)
    cv2.circle(img, center, radius, color, thickness)

def draw_hex_bracket(img, x1, y1, x2, y2, color, size=18):
    """Draw hexagonal corner brackets"""
    s = size
    pts_tl = [(x1, y1+s), (x1, y1), (x1+s, y1)]
    pts_tr = [(x2-s, y1), (x2, y1), (x2, y1+s)]
    pts_bl = [(x1, y2-s), (x1, y2), (x1+s, y2)]
    pts_br = [(x2-s, y2), (x2, y2), (x2, y2-s)]
    for pts in [pts_tl, pts_tr, pts_bl, pts_br]:
        for i in range(len(pts)-1):
            glow_line(img, pts[i], pts[i+1], color, 2)
    # faint fill
    overlay = img.copy()
    cv2.rectangle(overlay, (x1, y1), (x2, y2), color, -1)
    cv2.addWeighted(overlay, 0.05, img, 0.95, 0, img)

def draw_neon_text(img, text, x, y, color,
                   scale=0.6, thick=1):
    """Text with neon glow"""
    font = cv2.FONT_HERSHEY_SIMPLEX
    # Glow layer
    overlay = img.copy()
    cv2.putText(overlay, text, (x, y), font,
                scale, color, thick + 4, cv2.LINE_AA)
    cv2.addWeighted(overlay, 0.3, img, 0.7, 0, img)
    # Sharp layer
    cv2.putText(img, text, (x, y), font,
                scale, (255,255,255), thick, cv2.LINE_AA)

def draw_scan_line(img, angle, cx, cy, radius, color):
    """Rotating radar scan line"""
    rad = math.radians(angle)
    ex  = int(cx + radius * math.cos(rad))
    ey  = int(cy + radius * math.sin(rad))
    overlay = img.copy()
    cv2.line(overlay, (cx, cy), (ex, ey), color, 2)
    cv2.addWeighted(overlay, 0.6, img, 0.4, 0, img)

def draw_radar(img, x, y, r, objects, angle):
    """Mini radar widget"""
    # Dark background circle
    overlay = img.copy()
    cv2.circle(overlay, (x, y), r, (0, 20, 0), -1)
    cv2.addWeighted(overlay, 0.7, img, 0.3, 0, img)

    # Grid rings
    for ri in [r//4, r//2, 3*r//4, r]:
        cv2.circle(img, (x, y), ri, (0, 80, 0), 1)
    # Cross hairs
    cv2.line(img, (x-r, y), (x+r, y), (0, 80, 0), 1)
    cv2.line(img, (x, y-r), (x, y+r), (0, 80, 0), 1)

    # Scan sweep
    draw_scan_line(img, angle, x, y, r, (0, 255, 100))

    # Blips for each detected object
    total = sum(objects.values())
    for i, name in enumerate(objects.keys()):
        bangle = (angle + i * 45) % 360
        brad   = math.radians(bangle)
        dist   = random.randint(r//4, r - 10)
        bx     = int(x + dist * math.cos(brad))
        by_    = int(y + dist * math.sin(brad))
        glow_circle(img, (bx, by_), 4,
                    NEON_COLORS[i % len(NEON_COLORS)], -1)

    # Border
    glow_circle(img, (x, y), r, (0, 255, 100), 2)
    draw_neon_text(img, "RADAR", x - 22, y + r + 16,
                   (0, 255, 100), 0.45)

def draw_top_hud(img, fps, total, w):
    """Top bar HUD"""
    overlay = img.copy()
    cv2.rectangle(overlay, (0, 0), (w, 60), (0, 0, 15), -1)
    cv2.addWeighted(overlay, 0.88, img, 0.12, 0, img)

    # Accent border line
    glow_line(img, (0, 60), (w, 60), (0, 255, 255), 1)

    # App name
    cv2.putText(img, "VISION", (18, 42),
                cv2.FONT_HERSHEY_SIMPLEX, 1.1,
                (0, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(img, "TRACK", (115, 42),
                cv2.FONT_HERSHEY_SIMPLEX, 1.1,
                (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(img, "PRO", (210, 42),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65,
                (255, 0, 255), 2, cv2.LINE_AA)

    # Divider
    cv2.line(img, (260, 10), (260, 50), (0, 255, 255), 1)

    # Stats
    draw_neon_text(img, f"OBJECTS : {total:02d}",
                   280, 25, (0, 255, 255), 0.55)
    draw_neon_text(img, f"FPS     : {fps:05.1f}",
                   280, 48, (0, 255, 128), 0.55)

    # Time & date
    now = datetime.now()
    draw_neon_text(img,
                   now.strftime("%H:%M:%S"),
                   w - 200, 28, (0, 255, 255), 0.7)
    draw_neon_text(img,
                   now.strftime("%d/%m/%Y"),
                   w - 200, 50, (100, 100, 100), 0.45)

    # Status dot
    cv2.circle(img, (w - 30, 30), 8, (0, 255, 100), -1)
    draw_neon_text(img, "LIVE", w - 22, 35,
                   (0, 255, 100), 0.4)

def draw_object_panel(img, object_count, w, h):
    """Right side object list panel"""
    if not object_count:
        return
    pw = 220
    ph = len(object_count) * 38 + 55
    px = w - pw - 12
    py = 72

    # Panel background
    overlay = img.copy()
    cv2.rectangle(overlay, (px, py),
                  (px+pw, py+ph), (0, 5, 20), -1)
    cv2.addWeighted(overlay, 0.82, img, 0.18, 0, img)

    # Panel border with glow
    glow_line(img, (px, py), (px+pw, py),
              (0, 255, 255), 1)
    glow_line(img, (px, py), (px, py+ph),
              (0, 255, 255), 1)
    glow_line(img, (px+pw, py), (px+pw, py+ph),
              (0, 100, 100), 1)
    glow_line(img, (px, py+ph), (px+pw, py+ph),
              (0, 100, 100), 1)

    # Header
    draw_neon_text(img, "◈ DETECTED OBJECTS",
                   px+10, py+22,
                   (0, 255, 255), 0.5)
    cv2.line(img, (px+8, py+30),
             (px+pw-8, py+30), (0, 255, 255), 1)

    # Each object
    mx = max(object_count.values())
    for i, (name, cnt) in enumerate(object_count.items()):
        iy    = py + 52 + i * 38
        color = NEON_COLORS[i % len(NEON_COLORS)]

        # Bar track
        bx1, bx2 = px+10, px+pw-10
        cv2.rectangle(img, (bx1, iy-2),
                      (bx2, iy+14), (20, 20, 40), -1)

        # Bar fill (animated width)
        fill = int((cnt / mx) * (bx2 - bx1))
        overlay2 = img.copy()
        cv2.rectangle(overlay2, (bx1, iy-2),
                      (bx1+fill, iy+14), color, -1)
        cv2.addWeighted(overlay2, 0.55,
                        img, 0.45, 0, img)

        # Glow border on bar
        cv2.rectangle(img, (bx1, iy-2),
                      (bx2, iy+14), color, 1)

        # Text
        cv2.putText(img,
                    f"{name.upper()}",
                    (bx1+5, iy+11),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.48, (255,255,255), 1,
                    cv2.LINE_AA)
        cv2.putText(img, f"x{cnt}",
                    (bx2-28, iy+11),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, color, 1, cv2.LINE_AA)

        # Small color dot
        glow_circle(img, (bx1-8, iy+6),
                    4, color, -1)

def draw_bottom_hud(img, w, h):
    """Bottom control bar"""
    overlay = img.copy()
    cv2.rectangle(overlay, (0, h-40),
                  (w, h), (0, 0, 15), -1)
    cv2.addWeighted(overlay, 0.88, img, 0.12, 0, img)
    glow_line(img, (0, h-40), (w, h-40),
              (0, 255, 255), 1)

    controls = "[Q] QUIT    [S] SCREENSHOT    [P] PAUSE"
    cv2.putText(img, controls, (15, h-12),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55, (100, 200, 200), 1, cv2.LINE_AA)
    cv2.putText(img,
                "Powered by YOLOv8 + OpenCV",
                (w-265, h-12),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5, (60, 60, 80), 1, cv2.LINE_AA)

def draw_crosshair(img, cx, cy, size, color):
    """Targeting crosshair on object center"""
    s = size
    glow_line(img, (cx-s, cy), (cx-s//3, cy), color, 1)
    glow_line(img, (cx+s//3, cy), (cx+s, cy), color, 1)
    glow_line(img, (cx, cy-s), (cx, cy-s//3), color, 1)
    glow_line(img, (cx, cy+s//3), (cx, cy+s), color, 1)
    glow_circle(img, (cx, cy), 3, color, -1)

# ── MAIN LOOP ─────────────────────────────────────
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT,  720)

if not cap.isOpened():
    print("❌ Cannot open webcam!")
    exit()

print("✅ Webcam Ready!")
print("Controls: Q=Quit | S=Screenshot | P=Pause")

while True:
    if not paused:
        ret, frame = cap.read()
        if not ret:
            break

        h, w = frame.shape[:2]
        frame_count += 1
        scan_angle = (scan_angle + 3) % 360

        # FPS
        curr = cv2.getTickCount()
        fps  = (cv2.getTickFrequency() /
                (curr - prev_tick)) if prev_tick else 0
        prev_tick = curr

        # ── Detection ────────────────────────────
        results = model.track(
            frame,
            persist=True,
            conf=0.35,
            iou=0.45,
            verbose=False
        )

        object_count = {}

        if results[0].boxes is not None:
            for box in results[0].boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cid   = int(box.cls[0])
                cname = model.names[cid]
                conf  = float(box.conf[0])
                tid   = int(box.id[0]) if box.id is not None else 0
                color = neon_color(cid)

                object_count[cname] = \
                    object_count.get(cname, 0) + 1

                # Box
                draw_hex_bracket(frame,
                                 x1, y1, x2, y2,
                                 color, 20)

                # Center crosshair
                cx = (x1+x2)//2
                cy = (y1+y2)//2
                draw_crosshair(frame, cx, cy,
                               14, color)

                # Trail
                if tid not in track_history:
                    track_history[tid] = []
                track_history[tid].append((cx, cy))
                if len(track_history[tid]) > 30:
                    track_history[tid].pop(0)
                pts = track_history[tid]
                for i in range(1, len(pts)):
                    alpha = i / len(pts)
                    t     = max(1, int(alpha * 3))
                    fade  = tuple(int(c * alpha)
                                  for c in color)
                    cv2.line(frame, pts[i-1],
                             pts[i], fade, t)

                # Label pill
                label = (f"{cname.upper()} "
                         f"#{tid}  "
                         f"{conf:.0%}")
                font  = cv2.FONT_HERSHEY_SIMPLEX
                (tw, th), _ = cv2.getTextSize(
                    label, font, 0.52, 1)
                lx, ly = x1, y1 - 10
                pill = frame.copy()
                cv2.rectangle(pill,
                              (lx-4, ly-th-6),
                              (lx+tw+4, ly+4),
                              color, -1)
                cv2.addWeighted(pill, 0.7,
                                frame, 0.3, 0,
                                frame)
                cv2.rectangle(frame,
                              (lx-4, ly-th-6),
                              (lx+tw+4, ly+4),
                              color, 1)
                cv2.putText(frame, label,
                            (lx, ly),
                            font, 0.52,
                            (0,0,0), 2,
                            cv2.LINE_AA)
                cv2.putText(frame, label,
                            (lx, ly),
                            font, 0.52,
                            (255,255,255), 1,
                            cv2.LINE_AA)

        # ── HUD Layers ───────────────────────────
        total = sum(object_count.values())
        draw_top_hud(frame, fps, total, w)
        draw_object_panel(frame, object_count, w, h)
        draw_bottom_hud(frame, w, h)

        # Radar (bottom left)
        draw_radar(frame, 90, h-130,
                   75, object_count, scan_angle)

        # Corner decoration dots
        for pos in [(8,8),(w-8,8),(8,h-8),(w-8,h-8)]:
            glow_circle(frame, pos, 4,
                        (0,255,255), -1)

    # ── Show ─────────────────────────────────────
    cv2.imshow(
        "VisionTrack PRO — AI Object Detection",
        frame)

    key = cv2.waitKey(1) & 0xFF
    if key in (ord('q'), ord('Q')):
        print("👋 Closing VisionTrack PRO...")
        break
    elif key in (ord('s'), ord('S')):
        screenshot_n += 1
        fname = f"visiontrack_{screenshot_n}.jpg"
        cv2.imwrite(fname, frame)
        print(f"📸 Saved: {fname}")
    elif key in (ord('p'), ord('P')):
        paused = not paused
        print("⏸ Paused" if paused else "▶ Resumed")

cap.release()
cv2.destroyAllWindows()
print("✅ VisionTrack PRO closed!")