from pathlib import Path
import asyncio
import base64
import json

import cv2
import websockets

from tracking import VisionPadTracker


BASE_DIR = Path(__file__).resolve().parent


with open(
    BASE_DIR / "tracking_config.json",
    "r",
    encoding="utf-8"
) as file:
    CONFIG = json.load(file)


CLIENTS = set()


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


async def client_handler(websocket):
    CLIENTS.add(websocket)

    print(
        "Tracking client connected:",
        websocket.remote_address
    )

    try:
        async for message in websocket:
            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                continue

            if data.get("type") == "ping":
                await websocket.send(
                    json.dumps({
                        "type": "pong"
                    })
                )

    except websockets.exceptions.ConnectionClosed:
        pass

    finally:
        CLIENTS.discard(
            websocket
        )

        print(
            "Tracking client disconnected"
        )


async def broadcast(message):
    if not CLIENTS:
        return

    dead = []

    for websocket in list(CLIENTS):
        try:
            await websocket.send(
                message
            )
        except Exception:
            dead.append(
                websocket
            )

    for websocket in dead:
        CLIENTS.discard(
            websocket
        )


async def camera_loop():
    tracker = VisionPadTracker(
        CONFIG
    )

    cap = open_camera(
        CONFIG["camera"]
    )

    if not cap.isOpened():
        raise RuntimeError(
            "카메라를 열 수 없습니다."
        )

    debug_config = CONFIG.get(
        "debug",
        {}
    )

    send_camera_image = bool(
        debug_config.get(
            "send_camera_image",
            False
        )
    )

    jpeg_quality = int(
        debug_config.get(
            "jpeg_quality",
            75
        )
    )

    try:
        while True:
            ok, frame = cap.read()

            if not ok:
                await asyncio.sleep(
                    0.01
                )
                continue

            data, display, _ = (
                tracker.process_frame(
                    frame,
                    draw=send_camera_image
                )
            )

            if send_camera_image:
                encoded_ok, buffer = (
                    cv2.imencode(
                        ".jpg",
                        display,
                        [
                            cv2.IMWRITE_JPEG_QUALITY,
                            jpeg_quality
                        ]
                    )
                )

                if encoded_ok:
                    data["image"] = (
                        base64.b64encode(
                            buffer
                        ).decode("ascii")
                    )

            await broadcast(
                json.dumps(
                    data,
                    ensure_ascii=False
                )
            )

            await asyncio.sleep(0)

    finally:
        cap.release()
        tracker.close()


async def main():
    websocket_config = CONFIG[
        "websocket"
    ]

    host = str(
        websocket_config.get(
            "host",
            "127.0.0.1"
        )
    )

    port = int(
        websocket_config.get(
            "port",
            8765
        )
    )

    print(
        f"Tracking WebSocket: "
        f"ws://{host}:{port}"
    )

    server = await websockets.serve(
        client_handler,
        host,
        port
    )

    await asyncio.gather(
        server.wait_closed(),
        camera_loop()
    )


if __name__ == "__main__":
    try:
        asyncio.run(
            main()
        )
    except KeyboardInterrupt:
        print("Tracking server 종료")
