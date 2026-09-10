import time

import cv2
import numpy as np


class PadCoordinateMapper:

    def __init__(
        self,
        pad_config,
        calibration_config
    ):
        self.dot_width = int(
            pad_config.get(
                "dot_width",
                60
            )
        )

        self.dot_height = int(
            pad_config.get(
                "dot_height",
                40
            )
        )

        self.canonical_width = int(
            pad_config.get(
                "canonical_width",
                600
            )
        )

        self.canonical_height = int(
            pad_config.get(
                "canonical_height",
                400
            )
        )

        self.good_timeout_sec = float(
            calibration_config.get(
                "good_timeout_sec",
                1.0
            )
        )

        self.lost_timeout_sec = float(
            calibration_config.get(
                "lost_timeout_sec",
                3.0
            )
        )

        self.reset()


    def reset(self):
        self.homography = None
        self.last_quad = None
        self.last_update_time = None


    def update(self, ordered_quad, timestamp=None):
        if ordered_quad is None:
            return False

        if timestamp is None:
            timestamp = time.monotonic()

        destination = np.array(
            [
                [0, 0],
                [self.canonical_width - 1, 0],
                [
                    self.canonical_width - 1,
                    self.canonical_height - 1
                ],
                [0, self.canonical_height - 1]
            ],
            dtype=np.float32
        )

        self.homography = (
            cv2.getPerspectiveTransform(
                ordered_quad.astype(
                    np.float32
                ),
                destination
            )
        )

        self.last_quad = (
            ordered_quad.copy()
        )

        self.last_update_time = float(
            timestamp
        )

        return True


    def status(self, timestamp=None):
        if self.homography is None:
            return "lost"

        if timestamp is None:
            timestamp = time.monotonic()

        if self.last_update_time is None:
            return "lost"

        age = (
            float(timestamp)
            - self.last_update_time
        )

        if age <= self.good_timeout_sec:
            return "good"

        if age <= self.lost_timeout_sec:
            return "degraded"

        return "lost"


    def map_camera_point(
        self,
        point,
        timestamp=None
    ):
        if point is None:
            return None

        if self.status(timestamp) == "lost":
            return None

        points = np.array(
            [[point]],
            dtype=np.float32
        )

        mapped = (
            cv2.perspectiveTransform(
                points,
                self.homography
            )[0, 0]
        )

        x = float(mapped[0])
        y = float(mapped[1])

        inside = (
            0.0 <= x <= self.canonical_width - 1
            and
            0.0 <= y <= self.canonical_height - 1
        )

        dot_x = (
            x
            / max(
                1,
                self.canonical_width - 1
            )
            * (self.dot_width - 1)
        )

        dot_y = (
            y
            / max(
                1,
                self.canonical_height - 1
            )
            * (self.dot_height - 1)
        )

        return {
            "canonical_x": x,
            "canonical_y": y,
            "dot_x": float(dot_x),
            "dot_y": float(dot_y),
            "dot_x_int": int(
                round(
                    max(
                        0.0,
                        min(
                            self.dot_width - 1,
                            dot_x
                        )
                    )
                )
            ),
            "dot_y_int": int(
                round(
                    max(
                        0.0,
                        min(
                            self.dot_height - 1,
                            dot_y
                        )
                    )
                )
            ),
            "inside": inside
        }


    def warp(self, frame):
        if self.homography is None:
            return None

        return cv2.warpPerspective(
            frame,
            self.homography,
            (
                self.canonical_width,
                self.canonical_height
            ),
            flags=cv2.INTER_CUBIC
        )
