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


    def status(self):
        return {
            "scene_id":
                self.scene_id,

            "ocr_loaded":
                self.ocr_reader is not None,

            "rembg_loaded":
                self.rembg_session is not None,

            "ocr_text":
                self.current_ocr_text
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
                    False
            }

        new_text = self.run_ocr(
            frame
        )

        updated = self.is_new_ocr_text(
            new_text
        )

        if updated:
            self.current_ocr_text = (
                new_text
            )

            print(
                f"OCR time={timestamp:.2f} "
                f"text={new_text}"
            )

        return {
            "timestamp":
                timestamp,

            "ocr_text":
                self.current_ocr_text,

            "ocr_updated":
                updated
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
        frame
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

        detected = []

        for item in results:

            if len(item) < 3:
                continue

            box = item[0]
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

            x = min(
                point[0]
                for point in box
            )

            y = min(
                point[1]
                for point in box
            )

            detected.append(
                (
                    y,
                    x,
                    text
                )
            )

        detected.sort(
            key=lambda item: (
                item[0],
                item[1]
            )
        )

        return self.normalize_text(
            " ".join(
                item[2]
                for item in detected
            )
        )


    def is_new_ocr_text(
        self,
        text
    ):
        old_text = self.normalize_text(
            self.current_ocr_text
        )

        new_text = self.normalize_text(
            text
        )

        if not new_text:
            return False

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