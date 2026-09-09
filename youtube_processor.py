import base64
from difflib import SequenceMatcher

import cv2
import numpy as np
import torch
from rembg import remove, new_session
import easyocr


class YouTubeProcessor:

    def __init__(self, config):
        self.config = config

        self.scene_config = config[
            "scene_detection"
        ]

        self.ocr_config = config[
            "ocr"
        ]

        self.overlay_config = (
            self.ocr_config.get(
                "persistent_overlay",
                {}
            )
        )

        self.rembg_config = config[
            "rembg"
        ]

        self.dotpad_config = config[
            "dotpad"
        ]

        print("rembg loading")

        self.rembg_session = new_session(
            self.rembg_config["model"],
            providers=self.rembg_config[
                "providers"
            ]
        )

        print("rembg ready")

        self.ocr_reader = None

        if self.ocr_config.get(
            "enabled",
            True
        ):
            self.load_ocr()

        self.reset()


    def load_ocr(self):
        languages = self.ocr_config.get(
            "languages",
            ["ko", "en"]
        )

        use_gpu = (
            self.ocr_config.get(
                "gpu",
                True
            )
            and torch.cuda.is_available()
        )

        print(
            f"EasyOCR loading gpu={use_gpu}"
        )

        self.ocr_reader = easyocr.Reader(
            languages,
            gpu=use_gpu
        )

        print("EasyOCR ready")


    def reset(self):
        self.prev_hist = None
        self.prev_gray = None

        self.last_scene_time = -999999.0

        self.scene_id = -1

        self.current_dot_image = None
        self.current_ocr_text = ""

        self.last_scene_similarity = None
        self.last_pixel_difference = None

        self.ocr_tracks = []
        self.next_ocr_track_id = 0


    def status(self):
        return {
            "scene_id":
                self.scene_id,

            "ocr_loaded":
                self.ocr_reader is not None,

            "rembg_loaded":
                self.rembg_session is not None,

            "ocr_text":
                self.current_ocr_text,

            "persistent_overlays":
                sum(
                    1
                    for track in self.ocr_tracks
                    if track.get(
                        "is_overlay",
                        False
                    )
                )
        }


    def process_scene_frame(
        self,
        frame,
        timestamp
    ):
        timestamp = float(
            timestamp
        )

        scene_changed, similarity, pixel_difference = (
            self.check_scene_change(
                frame,
                timestamp
            )
        )

        if scene_changed:
            self.scene_id += 1

            dot_image = self.create_dot_image(
                frame
            )

            self.current_dot_image = (
                self.encode_png(
                    dot_image
                )
            )

            print(
                f"Scene {self.scene_id} "
                f"time={timestamp:.2f} "
                f"hist={similarity} "
                f"diff={pixel_difference}"
            )

        return {
            "timestamp":
                timestamp,

            "scene_id":
                self.scene_id,

            "scene_changed":
                scene_changed,

            "scene_similarity":
                similarity,

            "pixel_difference":
                pixel_difference,

            "dot_image":
                self.current_dot_image
        }


    def process_ocr_frame(
        self,
        frame,
        timestamp
    ):
        timestamp = float(
            timestamp
        )

        if self.ocr_reader is None:
            return {
                "timestamp":
                    timestamp,

                "ocr_text":
                    self.current_ocr_text,

                "ocr_updated":
                    False,

                "ocr_clear":
                    False
            }

        result = self.run_ocr(
            frame,
            timestamp
        )

        new_text = result[
            "text"
        ]

        force_update = result[
            "overlay_registered"
        ]

        updated = self.is_new_ocr_text(
            new_text,
            allow_empty=force_update
        )

        if updated:
            self.current_ocr_text = (
                new_text
            )

            display_text = (
                new_text
                if new_text
                else "<empty>"
            )

            print(
                f"OCR time={timestamp:.2f} "
                f"text={display_text}"
            )

        return {
            "timestamp":
                timestamp,

            "ocr_text":
                self.current_ocr_text,

            "ocr_updated":
                updated,

            "ocr_clear":
                updated
                and not bool(
                    self.current_ocr_text
                ),

            "persistent_overlays":
                result[
                    "overlay_count"
                ]
        }


    def prepare_scene_frame(
        self,
        frame
    ):
        height, width = (
            frame.shape[:2]
        )

        top_ratio = float(
            self.scene_config.get(
                "crop_top_ratio",
                0.0
            )
        )

        bottom_ratio = float(
            self.scene_config.get(
                "crop_bottom_ratio",
                0.0
            )
        )

        side_ratio = float(
            self.scene_config.get(
                "crop_side_ratio",
                0.0
            )
        )

        top = int(
            height * top_ratio
        )

        bottom = int(
            height
            * (1.0 - bottom_ratio)
        )

        left = int(
            width * side_ratio
        )

        right = int(
            width
            * (1.0 - side_ratio)
        )

        if bottom <= top:
            top = 0
            bottom = height

        if right <= left:
            left = 0
            right = width

        roi = frame[
            top:bottom,
            left:right
        ]

        target_width = int(
            self.scene_config.get(
                "resize_width",
                192
            )
        )

        target_height = int(
            self.scene_config.get(
                "resize_height",
                108
            )
        )

        return cv2.resize(
            roi,
            (
                target_width,
                target_height
            ),
            interpolation=cv2.INTER_AREA
        )


    def check_scene_change(
        self,
        frame,
        timestamp
    ):
        scene_frame = self.prepare_scene_frame(
            frame
        )

        hsv = cv2.cvtColor(
            scene_frame,
            cv2.COLOR_BGR2HSV
        )

        hist = cv2.calcHist(
            [hsv],
            [0, 1],
            None,
            self.scene_config[
                "histogram_bins"
            ],
            self.scene_config[
                "histogram_ranges"
            ]
        )

        cv2.normalize(
            hist,
            hist,
            alpha=0,
            beta=1,
            norm_type=cv2.NORM_MINMAX
        )

        gray = cv2.cvtColor(
            scene_frame,
            cv2.COLOR_BGR2GRAY
        )

        if (
            self.prev_hist is None
            or self.prev_gray is None
        ):
            self.prev_hist = hist
            self.prev_gray = gray

            self.last_scene_time = (
                timestamp
            )

            return (
                True,
                None,
                None
            )

        similarity = cv2.compareHist(
            self.prev_hist,
            hist,
            cv2.HISTCMP_CORREL
        )

        difference_image = cv2.absdiff(
            self.prev_gray,
            gray
        )

        pixel_difference = float(
            np.mean(
                difference_image
            )
        )

        self.prev_hist = hist
        self.prev_gray = gray

        self.last_scene_similarity = (
            float(similarity)
        )

        self.last_pixel_difference = (
            pixel_difference
        )

        min_interval = float(
            self.scene_config[
                "min_interval_sec"
            ]
        )

        if (
            timestamp
            - self.last_scene_time
            < min_interval
        ):
            return (
                False,
                float(similarity),
                pixel_difference
            )

        similarity_threshold = float(
            self.scene_config[
                "similarity_threshold"
            ]
        )

        difference_threshold = float(
            self.scene_config[
                "pixel_difference_threshold"
            ]
        )

        changed = (
            similarity
            < similarity_threshold
            or
            pixel_difference
            > difference_threshold
        )

        if changed:
            self.last_scene_time = (
                timestamp
            )

        return (
            changed,
            float(similarity),
            pixel_difference
        )


    def create_dot_image(
        self,
        frame
    ):
        frame_rgb = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )

        removed_bg = remove(
            frame_rgb,
            session=self.rembg_session
        )

        if (
            removed_bg.ndim == 3
            and removed_bg.shape[2] >= 4
        ):
            alpha_channel = (
                removed_bg[:, :, 3]
            )

            _, fg_mask = cv2.threshold(
                alpha_channel,
                int(
                    self.rembg_config[
                        "alpha_threshold"
                    ]
                ),
                255,
                cv2.THRESH_BINARY
            )

        else:
            fg_mask = np.full(
                frame.shape[:2],
                255,
                dtype=np.uint8
            )

        gray = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2GRAY
        )

        target_width = int(
            self.dotpad_config[
                "width"
            ]
        )

        target_height = int(
            self.dotpad_config[
                "height"
            ]
        )

        small_gray = cv2.resize(
            gray,
            (
                target_width,
                target_height
            ),
            interpolation=cv2.INTER_AREA
        )

        small_mask = cv2.resize(
            fg_mask,
            (
                target_width,
                target_height
            ),
            interpolation=cv2.INTER_NEAREST
        )

        small_edges = cv2.Canny(
            small_gray,
            int(
                self.dotpad_config[
                    "canny_low"
                ]
            ),
            int(
                self.dotpad_config[
                    "canny_high"
                ]
            )
        )

        small_edges = cv2.bitwise_and(
            small_edges,
            small_mask
        )

        contours, _ = cv2.findContours(
            small_mask,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        cv2.drawContours(
            small_edges,
            contours,
            -1,
            255,
            int(
                self.dotpad_config[
                    "contour_thickness"
                ]
            )
        )

        return small_edges


    def run_ocr(
        self,
        frame,
        timestamp
    ):
        results = self.ocr_reader.readtext(
            frame,
            detail=1,
            paragraph=False,
            decoder="greedy"
        )

        threshold = float(
            self.ocr_config.get(
                "confidence_threshold",
                0.3
            )
        )

        frame_height, frame_width = (
            frame.shape[:2]
        )

        detected = []

        for item in results:

            if len(item) < 3:
                continue

            raw_box = item[0]
            text = str(
                item[1]
            ).strip()

            confidence = float(
                item[2]
            )

            if (
                not text
                or confidence < threshold
            ):
                continue

            box = self.box_from_points(
                raw_box,
                frame_width,
                frame_height
            )

            if box is None:
                continue

            detected.append({
                "box": box,
                "text": text,
                "confidence": confidence,
                "patch": self.make_ocr_patch(
                    frame,
                    box
                )
            })

        overlay_registered = (
            self.update_ocr_tracks(
                detected,
                timestamp,
                frame_width,
                frame_height
            )
        )

        filtered = []

        for item in detected:

            if self.is_persistent_overlay_box(
                item["box"],
                timestamp
            ):
                continue

            x1, y1, _, _ = (
                item["box"]
            )

            filtered.append(
                (
                    y1,
                    x1,
                    item["text"]
                )
            )

        filtered.sort(
            key=lambda item: (
                item[0],
                item[1]
            )
        )

        text = self.normalize_text(
            " ".join(
                item[2]
                for item in filtered
            )
        )

        overlay_count = sum(
            1
            for track in self.ocr_tracks
            if track.get(
                "is_overlay",
                False
            )
        )

        return {
            "text": text,
            "overlay_registered":
                overlay_registered,
            "overlay_count":
                overlay_count
        }


    def box_from_points(
        self,
        points,
        frame_width,
        frame_height
    ):
        if not points:
            return None

        x_values = [
            float(point[0])
            for point in points
        ]

        y_values = [
            float(point[1])
            for point in points
        ]

        x1 = max(
            0,
            int(min(x_values))
        )

        y1 = max(
            0,
            int(min(y_values))
        )

        x2 = min(
            frame_width,
            int(max(x_values)) + 1
        )

        y2 = min(
            frame_height,
            int(max(y_values)) + 1
        )

        if (
            x2 <= x1
            or y2 <= y1
        ):
            return None

        return [
            x1,
            y1,
            x2,
            y2
        ]


    def make_ocr_patch(
        self,
        frame,
        box
    ):
        x1, y1, x2, y2 = box

        crop = frame[
            y1:y2,
            x1:x2
        ]

        if crop.size == 0:
            return None

        patch_width = int(
            self.overlay_config.get(
                "patch_width",
                48
            )
        )

        patch_height = int(
            self.overlay_config.get(
                "patch_height",
                24
            )
        )

        gray = cv2.cvtColor(
            crop,
            cv2.COLOR_BGR2GRAY
        )

        resized = cv2.resize(
            gray,
            (
                patch_width,
                patch_height
            ),
            interpolation=cv2.INTER_AREA
        )

        return cv2.equalizeHist(
            resized
        )


    def update_ocr_tracks(
        self,
        detected,
        timestamp,
        frame_width,
        frame_height
    ):
        if not self.overlay_config.get(
            "enabled",
            True
        ):
            return False

        self.prune_ocr_tracks(
            timestamp
        )

        matched_track_ids = set()
        overlay_registered = False

        for item in detected:
            track = self.find_ocr_track(
                item["box"],
                timestamp,
                matched_track_ids,
                frame_width,
                frame_height
            )

            if track is None:
                track = self.create_ocr_track(
                    item,
                    timestamp
                )

                self.ocr_tracks.append(
                    track
                )

            else:
                self.update_ocr_track(
                    track,
                    item,
                    timestamp,
                    frame_width,
                    frame_height
                )

            matched_track_ids.add(
                track["id"]
            )

            if (
                not track["is_overlay"]
                and self.should_mark_overlay(
                    track,
                    timestamp,
                    frame_width,
                    frame_height
                )
            ):
                track["is_overlay"] = True
                overlay_registered = True

                box = [
                    int(round(value))
                    for value in track["box"]
                ]

                print(
                    f"OCR overlay {track['id']} "
                    f"time={timestamp:.2f} "
                    f"box={box} "
                    f"scenes={len(track['scene_ids'])}"
                )

        return overlay_registered


    def create_ocr_track(
        self,
        item,
        timestamp
    ):
        track = {
            "id": self.next_ocr_track_id,
            "box": [
                float(value)
                for value in item["box"]
            ],
            "last_box": [
                float(value)
                for value in item["box"]
            ],
            "first_seen": timestamp,
            "last_seen": timestamp,
            "seen_count": 1,
            "scene_ids": set(),
            "patch": item["patch"],
            "patch_compare_count": 0,
            "patch_stable_count": 0,
            "geometry_compare_count": 0,
            "geometry_stable_count": 0,
            "is_overlay": False
        }

        if self.scene_id >= 0:
            track["scene_ids"].add(
                int(self.scene_id)
            )

        self.next_ocr_track_id += 1

        return track


    def update_ocr_track(
        self,
        track,
        item,
        timestamp,
        frame_width,
        frame_height
    ):
        current_box = [
            float(value)
            for value in item["box"]
        ]

        previous_box = track[
            "last_box"
        ]

        track[
            "geometry_compare_count"
        ] += 1

        if self.is_geometry_stable(
            previous_box,
            current_box,
            frame_width,
            frame_height
        ):
            track[
                "geometry_stable_count"
            ] += 1

        previous_patch = track.get(
            "patch"
        )

        current_patch = item.get(
            "patch"
        )

        if (
            previous_patch is not None
            and current_patch is not None
            and previous_patch.shape
                == current_patch.shape
        ):
            difference = float(
                np.mean(
                    cv2.absdiff(
                        previous_patch,
                        current_patch
                    )
                )
            )

            track[
                "patch_compare_count"
            ] += 1

            patch_threshold = float(
                self.overlay_config.get(
                    "patch_difference_threshold",
                    22.0
                )
            )

            if difference <= patch_threshold:
                track[
                    "patch_stable_count"
                ] += 1

        smooth = float(
            self.overlay_config.get(
                "box_smoothing",
                0.75
            )
        )

        smooth = min(
            0.95,
            max(
                0.0,
                smooth
            )
        )

        track["box"] = [
            smooth * old
            + (1.0 - smooth) * new
            for old, new in zip(
                track["box"],
                current_box
            )
        ]

        track["last_box"] = (
            current_box
        )

        track["patch"] = (
            current_patch
        )

        track["last_seen"] = (
            timestamp
        )

        track["seen_count"] += 1

        if self.scene_id >= 0:
            track["scene_ids"].add(
                int(self.scene_id)
            )


    def find_ocr_track(
        self,
        box,
        timestamp,
        matched_track_ids,
        frame_width,
        frame_height
    ):
        max_age = float(
            self.overlay_config.get(
                "track_match_max_age_sec",
                2.5
            )
        )

        iou_threshold = float(
            self.overlay_config.get(
                "box_iou_threshold",
                0.5
            )
        )

        best_track = None
        best_score = -1.0

        for track in self.ocr_tracks:

            if track["id"] in matched_track_ids:
                continue

            if (
                timestamp
                - track["last_seen"]
                > max_age
            ):
                continue

            iou = self.box_iou(
                track["box"],
                box
            )

            geometry_match = (
                self.is_geometry_stable(
                    track["last_box"],
                    box,
                    frame_width,
                    frame_height
                )
            )

            if (
                iou < iou_threshold
                and not geometry_match
            ):
                continue

            score = iou

            if geometry_match:
                score += 0.25

            if score > best_score:
                best_score = score
                best_track = track

        return best_track


    def should_mark_overlay(
        self,
        track,
        timestamp,
        frame_width,
        frame_height
    ):
        duration = (
            timestamp
            - track["first_seen"]
        )

        min_duration = float(
            self.overlay_config.get(
                "min_duration_sec",
                8.0
            )
        )

        min_seen = int(
            self.overlay_config.get(
                "min_seen_count",
                6
            )
        )

        min_scenes = int(
            self.overlay_config.get(
                "min_scene_count",
                3
            )
        )

        if duration < min_duration:
            return False

        if track["seen_count"] < min_seen:
            return False

        if len(track["scene_ids"]) < min_scenes:
            return False

        geometry_count = max(
            1,
            track["geometry_compare_count"]
        )

        geometry_ratio = (
            track["geometry_stable_count"]
            / geometry_count
        )

        min_geometry_ratio = float(
            self.overlay_config.get(
                "min_geometry_stable_ratio",
                0.8
            )
        )

        if geometry_ratio < min_geometry_ratio:
            return False

        patch_count = max(
            1,
            track["patch_compare_count"]
        )

        patch_ratio = (
            track["patch_stable_count"]
            / patch_count
        )

        if self.is_corner_box(
            track["box"],
            frame_width,
            frame_height
        ):
            min_patch_ratio = float(
                self.overlay_config.get(
                    "corner_patch_stable_ratio",
                    0.35
                )
            )

        else:
            min_patch_ratio = float(
                self.overlay_config.get(
                    "general_patch_stable_ratio",
                    0.75
                )
            )

        return (
            patch_ratio
            >= min_patch_ratio
        )


    def is_persistent_overlay_box(
        self,
        box,
        timestamp
    ):
        filter_iou = float(
            self.overlay_config.get(
                "filter_iou_threshold",
                0.35
            )
        )

        expire_sec = float(
            self.overlay_config.get(
                "overlay_expire_sec",
                15.0
            )
        )

        for track in self.ocr_tracks:

            if not track.get(
                "is_overlay",
                False
            ):
                continue

            if (
                timestamp
                - track["last_seen"]
                > expire_sec
            ):
                continue

            if self.box_iou(
                track["box"],
                box
            ) >= filter_iou:
                return True

        return False


    def prune_ocr_tracks(
        self,
        timestamp
    ):
        stale_sec = float(
            self.overlay_config.get(
                "track_expire_sec",
                5.0
            )
        )

        overlay_expire_sec = float(
            self.overlay_config.get(
                "overlay_expire_sec",
                15.0
            )
        )

        kept = []

        for track in self.ocr_tracks:
            age = (
                timestamp
                - track["last_seen"]
            )

            limit = (
                overlay_expire_sec
                if track.get(
                    "is_overlay",
                    False
                )
                else stale_sec
            )

            if age <= limit:
                kept.append(
                    track
                )

        self.ocr_tracks = kept


    def is_geometry_stable(
        self,
        old_box,
        new_box,
        frame_width,
        frame_height
    ):
        old_width = max(
            1.0,
            old_box[2] - old_box[0]
        )

        old_height = max(
            1.0,
            old_box[3] - old_box[1]
        )

        new_width = max(
            1.0,
            new_box[2] - new_box[0]
        )

        new_height = max(
            1.0,
            new_box[3] - new_box[1]
        )

        old_center_x = (
            old_box[0] + old_box[2]
        ) / 2.0

        old_center_y = (
            old_box[1] + old_box[3]
        ) / 2.0

        new_center_x = (
            new_box[0] + new_box[2]
        ) / 2.0

        new_center_y = (
            new_box[1] + new_box[3]
        ) / 2.0

        dx = abs(
            new_center_x - old_center_x
        ) / max(
            1.0,
            float(frame_width)
        )

        dy = abs(
            new_center_y - old_center_y
        ) / max(
            1.0,
            float(frame_height)
        )

        max_center_shift = float(
            self.overlay_config.get(
                "max_center_shift_ratio",
                0.035
            )
        )

        min_size_ratio = float(
            self.overlay_config.get(
                "min_size_ratio",
                0.7
            )
        )

        width_ratio = min(
            old_width,
            new_width
        ) / max(
            old_width,
            new_width
        )

        height_ratio = min(
            old_height,
            new_height
        ) / max(
            old_height,
            new_height
        )

        return (
            dx <= max_center_shift
            and dy <= max_center_shift
            and width_ratio >= min_size_ratio
            and height_ratio >= min_size_ratio
        )


    def is_corner_box(
        self,
        box,
        frame_width,
        frame_height
    ):
        x1, y1, x2, y2 = box

        center_x = (
            x1 + x2
        ) / 2.0

        center_y = (
            y1 + y2
        ) / 2.0

        horizontal_ratio = float(
            self.overlay_config.get(
                "corner_horizontal_ratio",
                0.28
            )
        )

        vertical_ratio = float(
            self.overlay_config.get(
                "corner_vertical_ratio",
                0.28
            )
        )

        near_side = (
            center_x
            <= frame_width
            * horizontal_ratio
            or center_x
            >= frame_width
            * (1.0 - horizontal_ratio)
        )

        near_top = (
            center_y
            <= frame_height
            * vertical_ratio
        )

        return (
            near_side
            and near_top
        )


    def box_iou(
        self,
        box_a,
        box_b
    ):
        x1 = max(
            box_a[0],
            box_b[0]
        )

        y1 = max(
            box_a[1],
            box_b[1]
        )

        x2 = min(
            box_a[2],
            box_b[2]
        )

        y2 = min(
            box_a[3],
            box_b[3]
        )

        intersection = (
            max(0.0, x2 - x1)
            * max(0.0, y2 - y1)
        )

        area_a = (
            max(0.0, box_a[2] - box_a[0])
            * max(0.0, box_a[3] - box_a[1])
        )

        area_b = (
            max(0.0, box_b[2] - box_b[0])
            * max(0.0, box_b[3] - box_b[1])
        )

        union = (
            area_a
            + area_b
            - intersection
        )

        if union <= 0.0:
            return 0.0

        return float(
            intersection / union
        )


    def is_new_ocr_text(
        self,
        text,
        allow_empty=False
    ):
        old_text = self.normalize_text(
            self.current_ocr_text
        )

        new_text = self.normalize_text(
            text
        )

        if not new_text:
            return (
                allow_empty
                and bool(old_text)
            )

        if old_text == new_text:
            return False

        if not old_text:
            return True

        similarity = SequenceMatcher(
            None,
            old_text,
            new_text
        ).ratio()

        threshold = float(
            self.ocr_config.get(
                "duplicate_similarity",
                0.9
            )
        )

        return (
            similarity < threshold
        )


    def normalize_text(
        self,
        text
    ):
        return " ".join(
            str(text)
            .replace("\n", " ")
            .split()
        ).strip()


    def encode_png(
        self,
        image
    ):
        success, buffer = (
            cv2.imencode(
                ".png",
                image
            )
        )

        if not success:
            raise RuntimeError(
                "Dot 이미지 인코딩 실패"
            )

        encoded = (
            base64.b64encode(
                buffer
            ).decode(
                "utf-8"
            )
        )

        return (
            "data:image/png;base64,"
            + encoded
        )