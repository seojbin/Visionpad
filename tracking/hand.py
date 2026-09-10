import cv2
import mediapipe as mp


class HandTracker:

    def __init__(self, config):
        self.config = config

        self.mp_hands = (
            mp.solutions.hands
        )

        self.mp_draw = (
            mp.solutions.drawing_utils
        )

        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=int(
                config.get(
                    "max_num_hands",
                    2
                )
            ),
            model_complexity=int(
                config.get(
                    "model_complexity",
                    1
                )
            ),
            min_detection_confidence=float(
                config.get(
                    "min_detection_confidence",
                    0.5
                )
            ),
            min_tracking_confidence=float(
                config.get(
                    "min_tracking_confidence",
                    0.5
                )
            )
        )

        self.preferred_hand = str(
            config.get(
                "preferred_hand",
                "any"
            )
        ).lower()


    def close(self):
        if self.hands is not None:
            self.hands.close()


    def process(self, frame, draw=True):
        height, width = frame.shape[:2]

        rgb = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )

        result = self.hands.process(
            rgb
        )

        detected = []

        if not result.multi_hand_landmarks:
            return detected

        handedness_list = (
            result.multi_handedness
            or []
        )

        for index, hand_landmarks in enumerate(
            result.multi_hand_landmarks
        ):
            label = "Unknown"
            score = 0.0

            if index < len(handedness_list):
                classification = (
                    handedness_list[index]
                    .classification[0]
                )

                label = (
                    classification.label
                )

                score = float(
                    classification.score
                )

            if (
                self.preferred_hand
                in ("left", "right")
                and label.lower()
                    != self.preferred_hand
            ):
                continue

            points = []

            for landmark in hand_landmarks.landmark:
                points.append(
                    (
                        float(landmark.x * width),
                        float(landmark.y * height),
                        float(landmark.z)
                    )
                )

            detected.append({
                "handedness": label,
                "score": score,
                "landmarks": points,
                "index_tip": points[8][:2],
                "thumb_tip": points[4][:2],
                "index_mcp": points[5][:2],
                "pinky_mcp": points[17][:2]
            })

            if draw:
                self.mp_draw.draw_landmarks(
                    frame,
                    hand_landmarks,
                    self.mp_hands.HAND_CONNECTIONS
                )

                tip = points[8]

                cv2.circle(
                    frame,
                    (
                        int(round(tip[0])),
                        int(round(tip[1]))
                    ),
                    8,
                    (0, 220, 255),
                    -1,
                    cv2.LINE_AA
                )

        return detected
