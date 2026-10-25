import cv2
import numpy as np


class ArucoPadTracker:

    def __init__(self, config):
        self.config = config

        dictionary_name = config.get(
            "dictionary",
            "DICT_4X4_50"
        )

        if not hasattr(cv2, "aruco"):
            raise RuntimeError(
                "cv2.aruco를 찾을 수 없습니다. "
                "opencv-contrib-python을 설치하세요."
            )

        if not hasattr(cv2.aruco, dictionary_name):
            raise ValueError(
                f"지원하지 않는 ArUco dictionary: {dictionary_name}"
            )

        dictionary_id = getattr(
            cv2.aruco,
            dictionary_name
        )

        self.dictionary = (
            cv2.aruco.getPredefinedDictionary(
                dictionary_id
            )
        )

        if hasattr(cv2.aruco, "DetectorParameters"):
            parameters = cv2.aruco.DetectorParameters()
        else:
            parameters = cv2.aruco.DetectorParameters_create()

        self.parameters = parameters

        if hasattr(cv2.aruco, "ArucoDetector"):
            self.detector = cv2.aruco.ArucoDetector(
                self.dictionary,
                self.parameters
            )
        else:
            self.detector = None

        marker_ids = config.get(
            "marker_ids",
            {}
        )

        self.id_tl = int(
            marker_ids.get("top_left", 0)
        )
        self.id_tr = int(
            marker_ids.get("top_right", 1)
        )
        self.id_bl = int(
            marker_ids.get("bottom_left", 2)
        )
        self.id_br = int(
            marker_ids.get("bottom_right", 3)
        )


    def detect(self, frame, draw=True):
        gray = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2GRAY
        )

        if self.detector is not None:
            corners_list, ids, _ = (
                self.detector.detectMarkers(
                    gray
                )
            )
        else:
            corners_list, ids, _ = (
                cv2.aruco.detectMarkers(
                    gray,
                    self.dictionary,
                    parameters=self.parameters
                )
            )

        if ids is None:
            return {
                "marker_count": 0,
                "ids": [],
                "quad": None,
                "all_required": False
            }

        flat_ids = [
            int(value)
            for value in ids.flatten()
        ]

        if draw:
            cv2.aruco.drawDetectedMarkers(
                frame,
                corners_list,
                ids
            )

        id_to_corners = {
            int(marker_id):
                corners.reshape(4, 2).astype(
                    np.float32
                )
            for corners, marker_id
            in zip(
                corners_list,
                ids.flatten()
            )
        }

        required = [
            self.id_tl,
            self.id_tr,
            self.id_bl,
            self.id_br
        ]

        all_required = all(
            marker_id in id_to_corners
            for marker_id in required
        )

        ordered_quad = None

        if all_required:
            tl = id_to_corners[
                self.id_tl
            ][2]

            tr = id_to_corners[
                self.id_tr
            ][3]

            br = id_to_corners[
                self.id_br
            ][0]

            bl = id_to_corners[
                self.id_bl
            ][1]

            ordered_quad = np.array(
                [tl, tr, br, bl],
                dtype=np.float32
            )

            if draw:
                for i in range(4):
                    p1 = tuple(
                        ordered_quad[i]
                        .astype(int)
                    )

                    p2 = tuple(
                        ordered_quad[
                            (i + 1) % 4
                        ].astype(int)
                    )

                    cv2.line(
                        frame,
                        p1,
                        p2,
                        (255, 0, 0),
                        2,
                        cv2.LINE_AA
                    )

        return {
            "marker_count": len(flat_ids),
            "ids": flat_ids,
            "quad": ordered_quad,
            "all_required": all_required
        }
