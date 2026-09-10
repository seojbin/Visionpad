from pathlib import Path
import json
import time

import cv2

from tracking import VisionPadTracker


BASE_DIR = Path(__file__).resolve().parent


with open(
    BASE_DIR / "tracking_config.json",
    "r",
    encoding="utf-8"
) as file:
    CONFIG = json.load(file)


def open_camera(config):
    camera_index = int(
        config.get("index", 0)
    )

    backend = str(
        config.get(
            "backend",
            "dshow"
        )
    ).lower()

    if backend == "dshow":
        cap = cv2.VideoCapture(
            camera_index,
            cv2.CAP_DSHOW
        )
    else:
        cap = cv2.VideoCapture(
            camera_index
        )

    cap.set(
        cv2.CAP_PROP_FRAME_WIDTH,
        int(config.get("width", 1280))
    )

    cap.set(
        cv2.CAP_PROP_FRAME_HEIGHT,
        int(config.get("height", 720))
    )

    cap.set(
        cv2.CAP_PROP_FPS,
        int(config.get("fps", 30))
    )

    cap.set(
        cv2.CAP_PROP_BUFFERSIZE,
        int(config.get("buffer_size", 1))
    )

    return cap


def main():
    tracker = VisionPadTracker(
        CONFIG
    )

    cap = open_camera(
        CONFIG["camera"]
    )

    if not cap.isOpened():
        raise RuntimeError(
            "카메라를 열 수 없습니다. "
            "tracking_config.json의 camera.index를 확인하세요."
        )

    print("Tracking Test 시작")
    print("Q 또는 ESC: 종료")
    print("R: 캘리브레이션 초기화")
    print("손을 치운 상태에서 ArUco 4개를 모두 보여주세요.")

    try:
        while True:
            ok, frame = cap.read()

            if not ok:
                time.sleep(0.01)
                continue

            data, display, pad_view = (
                tracker.process_frame(
                    frame,
                    draw=True
                )
            )

            cv2.imshow(
                "VisionPad Tracking Camera",
                display
            )

            cv2.imshow(
                "VisionPad Canonical 60x40",
                pad_view
            )

            key = cv2.waitKey(1) & 0xFF

            if key in (
                27,
                ord("q")
            ):
                break

            if key == ord("r"):
                tracker.reset_calibration()
                print("캘리브레이션 초기화")

    finally:
        cap.release()
        tracker.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
