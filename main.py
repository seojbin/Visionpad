
import cv2
import numpy as np
import os
import subprocess
import requests
import base64
import gc
import time
import json
import sys
import torch

from ultralytics import YOLO
from rembg import remove, new_session

# 오디오 추출
def extract_audio(video_path, output_dir):
    audio_path = os.path.join(
        output_dir,
        "audio.mp3"
    )

    print(
        f"\n오디오 추출 시작: "
        f"{audio_path}"
    )

    try:
        command = [
            "ffmpeg",
            "-i",
            video_path,
            "-q:a",
            "0",
            "-map",
            "a",
            audio_path,
            "-y"
        ]

        subprocess.run(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )

        print("오디오 추출 성공!")

    except Exception as e:
        print(
            f"오디오 추출 실패: {e}"
        )


# =========================================================
# JSON metadata 저장
# =========================================================

def save_scene_metadata(
    scene_metadata,
    output_dir
):
    json_path = os.path.join(
        output_dir,
        "scene_metadata.json"
    )

    try:
        with open(
            json_path,
            "w",
            encoding="utf-8"
        ) as f:
            json.dump(
                scene_metadata,
                f,
                ensure_ascii=False,
                indent=2
            )

        print(
            f"[저장] scene_metadata.json "
            f"({len(scene_metadata)}개 Scene)"
        )

        return True

    except Exception as e:

        print(
            f"[오류] scene_metadata.json 저장 실패: {e}"
        )

        return False


# GPU 상태 출력

def print_gpu_memory(label=""):

    if not torch.cuda.is_available():

        print(
            f"[GPU] {label}: CUDA 사용 불가"
        )

        return

    try:

        free, total = torch.cuda.mem_get_info()

        free_gb = free / (1024 ** 3)
        total_gb = total / (1024 ** 3)
        used_gb = total_gb - free_gb

        print(
            f"[GPU] {label} | "
            f"사용 {used_gb:.2f} GB / "
            f"전체 {total_gb:.2f} GB | "
            f"가용 {free_gb:.2f} GB"
        )

    except Exception as e:

        print(
            f"[GPU] 메모리 확인 실패: {e}"
        )

# YOLO / rembg GPU 해제

def release_local_gpu_models(
    model,
    rembg_session
):

    print("\n")
    print("=" * 60)
    print(
        "YOLO / rembg GPU 메모리 해제 시작"
    )
    print("=" * 60)

    try:

        if model is not None:

            try:
                model.cpu()

            except Exception:
                pass

            del model

        if rembg_session is not None:

            try:
                del rembg_session

            except Exception:
                pass


        gc.collect()

        if torch.cuda.is_available():

            try:
                torch.cuda.synchronize()

            except Exception:
                pass


            try:
                torch.cuda.empty_cache()

            except Exception:
                pass


            try:
                torch.cuda.ipc_collect()

            except Exception:
                pass


            try:
                torch.cuda.synchronize()

            except Exception:
                pass


        print_gpu_memory(
            "YOLO / rembg 해제"
        )

        print(
            "YOLO / rembg GPU 해제 완료"
        )

    except Exception as e:

        print(
            f"GPU 모델 해제 중 경고: {e}"
        )



# AI 서버 시작
def start_ai_server():

    print("\n")
    print("=" * 60)
    print("AI Relay Server 시작")
    print("=" * 60)

    server_path = os.path.join(
        os.path.dirname(
            os.path.abspath(__file__)
        ),
        "server.py"
    )

    if not os.path.exists(server_path):

        print(
            f"[오류] server.py를 찾을 수 없습니다:\n"
            f"{server_path}"
        )

        return None


    try:

        creation_flags = (
            subprocess.CREATE_NEW_CONSOLE
        )

        server_process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "server:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8001"
            ],
            cwd=os.path.dirname(
                os.path.abspath(__file__)
            ),
            creationflags=creation_flags
        )

        print(
            f"AI Relay Server PID: "
            f"{server_process.pid}"
        )

        return server_process

    except Exception as e:

        print(
            f"AI 서버 시작 실패: {e}"
        )

        return None



def wait_for_ai_server(
    api_base_url,
    timeout_sec=180
):

    print("\nAI 서버 준비 상태 확인 중...")

    start_time = time.time()

    status_url = (
        f"{api_base_url}/status"
    )


    while (
        time.time() - start_time
        < timeout_sec
    ):

        try:

            response = requests.get(
                status_url,
                timeout=5
            )

            if response.ok:

                data = response.json()

                print(
                    "AI 서버 연결 성공 "
                    f"(mode={data.get('mode')})"
                )

                return True

        except Exception:

            pass


        time.sleep(2)


    print(
        f"AI 서버가 "
        f"{timeout_sec}초 안에 준비되지 않았습니다."
    )

    return False


# Moondream 전체 Scene 분석

def analyze_scenes_with_moondream(
    api_base_url,
    scene_metadata,
    output_dir
):

    print("\n")
    print("=" * 60)
    print(
        "PHASE 2 : 저장된 Scene 전체 "
        "Moondream 분석"
    )
    print("=" * 60)


    for data in scene_metadata:

        scene_id = data["scene_id"]

        image_path = (
            data["analysis_image_path"]
        )


        print("\n")
        print(
            f"[Scene {scene_id}] "
            "Moondream 분석 시작"
        )


        if not os.path.exists(image_path):

            print(
                f"  [오류] Scene 이미지 없음: "
                f"{image_path}"
            )

            data["english_desc"] = ""

            save_scene_metadata(
                scene_metadata,
                output_dir
            )

            continue


        try:
            # 저장된 Scene 이미지 읽기

            with open(
                image_path,
                "rb"
            ) as f:

                img_b64 = (
                    base64.b64encode(
                        f.read()
                    ).decode("utf-8")
                )



            # YOLO 결과 전달

            detected_classes = (
                data.get(
                    "yolo_objects",
                    []
                )
            )


            md_prompt = (
                "Describe this scene briefly "
                "and identify the main visible "
                "place, people, objects, actions, "
                "time or important text. "
    "Describe only what is visibly present in the image. "
    "Do not guess, infer, interpret, translate, or explain. "
    "Use one short factual English description."
                f"Key objects detected by YOLO: "
                f"{detected_classes}."
            )

            response = requests.post(

                f"{api_base_url}/vision",

                json={
                    "image_base64": img_b64,
                    "prompt": md_prompt
                },

                timeout=180
            )


            response.raise_for_status()


            english_desc = (
                response
                .json()
                .get("result", "")
                .strip()
            )


            data["english_desc"] = (
                english_desc
            )


            print(
                f"  Moondream(Eng): "
                f"{english_desc}"
            )

            save_scene_metadata(
                scene_metadata,
                output_dir
            )


        except Exception as e:

            print(
                f"  Moondream 오류: {e}"
            )

            data["english_desc"] = ""

            save_scene_metadata(
                scene_metadata,
                output_dir
            )


    print("\n")
    print("=" * 60)
    print("PHASE 2 Moondream 분석 완료")
    print("=" * 60)


    save_scene_metadata(
        scene_metadata,
        output_dir
    )


    return scene_metadata


# AI 서버를 LLM 전환

def switch_ai_server_to_llm(
    api_base_url
):

    print("\n")
    print("=" * 60)
    print(
        "AI 서버 LLM 전환 요청"
    )
    print("=" * 60)


    try:

        response = requests.post(
            f"{api_base_url}/switch-to-llm",
            timeout=300
        )

        response.raise_for_status()

        data = response.json()

        print(
            "AI 서버 LLM 전환 성공:",
            data
        )

        return True


    except Exception as e:

        print(
            f"AI 서버 LLM 전환 실패: {e}"
        )

        return False


# Gemma 한국어 요약

def summarize_scene(
    api_base_url,
    english_desc
):

    if not english_desc:

        return "분석 실패"


    try:

        response = requests.post(

            f"{api_base_url}/summarize",

            json={
                "english_desc": english_desc
            },

            timeout=120
        )


        response.raise_for_status()


        result = (
            response
            .json()
            .get("result", "")
            .strip()
        )



        result = (
            result
            .replace("\n", " ")
            .replace(".", "")
            .replace(",", "")
            .replace('"', "")
            .replace("'", "")
            .replace("(", "")
            .replace(")", "")
            .replace("[", "")
            .replace("]", "")
            .replace("{", "")
            .replace("}", "")
            .replace("/", "")
            .replace("\\", "")
            .replace(":", "")
            .replace(";", "")
            .replace("!", "")
            .replace("?", "")
            .replace("·", "")
            .replace("•", "")
            .strip()
        )


        result = " ".join(
            result.split()
        ).strip()


        return result


    except Exception as e:

        print(
            f"Gemma 요약 API 오류: {e}"
        )

        return "서버 통신 지연"



# 영상 처리

def process_video_to_tactile_edges(
    video_path,
    output_dir="output_edges",
    min_interval_sec=10
):

    # 디렉터리 생성

    outline_dir = os.path.join(
        output_dir,
        "outline"
    )

    dot_dir = os.path.join(
        output_dir,
        "dot"
    )

    analysis_dir = os.path.join(
        output_dir,
        "analysis"
    )


    os.makedirs(
        outline_dir,
        exist_ok=True
    )

    os.makedirs(
        dot_dir,
        exist_ok=True
    )

    os.makedirs(
        analysis_dir,
        exist_ok=True
    )


    print("=" * 60)

    print(
        "VideoBraille 시작"
    )

    print(
        f"입력 영상: {video_path}"
    )

    print(
        f"출력 폴더: {output_dir}"
    )

    print(
        f"CUDA 사용 가능: "
        f"{torch.cuda.is_available()}"
    )

    print_gpu_memory(
        "프로그램 시작"
    )

    print("=" * 60)



    print("\n")
    print("PHASE 1 : 영상 전체 Scene 처리")
    print("YOLO GPU + rembg GPU")


    print("\nYOLO 모델 로드...")

    model = YOLO(
        "yolov8n.pt"
    )

    print(
        "rembg GPU 세션 초기화"
    )

    rembg_session = new_session(
        "bria-rmbg",
        providers=[
            "CUDAExecutionProvider"
        ]
    )


    print_gpu_memory(
        "YOLO + rembg 준비 후"
    )


    cap = cv2.VideoCapture(
        video_path
    )


    if not cap.isOpened():

        print(
            "비디오를 열 수 없습니다."
        )

        release_local_gpu_models(
            model,
            rembg_session
        )

        return []


    fps = cap.get(
        cv2.CAP_PROP_FPS
    )


    if fps <= 0:

        fps = 30.0


    min_frames_between_scenes = int(
        fps * min_interval_sec
    )


    prev_hist = None


    frames_since_last_scene = (
        min_frames_between_scenes
    )


    scene_count = 0
    frame_count = 0


    # 0.5초 간격
    skip_frames = max(
        1,
        int(fps / 2)
    )


    scene_metadata = []


    # 초기 JSON 생성
    save_scene_metadata(
        scene_metadata,
        output_dir
    )



    while cap.isOpened():

        ret, frame = cap.read()


        if not ret:
            break


        frame_count += 1

        # 0.5초마다 Scene 확인

        if (
            frame_count
            % skip_frames
            != 0
        ):

            frames_since_last_scene += 1

            continue


        # Histogram
        hsv_frame = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2HSV
        )


        hist = cv2.calcHist(
            [hsv_frame],
            [0, 1],
            None,
            [50, 50],
            [0, 180, 0, 256]
        )


        cv2.normalize(
            hist,
            hist,
            alpha=0,
            beta=1,
            norm_type=cv2.NORM_MINMAX
        )


        is_new_scene = False


        if prev_hist is None:

            is_new_scene = True


        elif (
            frames_since_last_scene
            >= min_frames_between_scenes
        ):

            similarity = cv2.compareHist(
                prev_hist,
                hist,
                cv2.HISTCMP_CORREL
            )


            if similarity < 0.85:

                is_new_scene = True



        if is_new_scene:

            current_time_sec = (
                cap.get(
                    cv2.CAP_PROP_POS_MSEC
                ) / 1000.0
            )


            print("\n")
            print(
                f"[Scene {scene_count}] "
                f"탐지 "
                f"({current_time_sec:.2f}초)"
            )


            # A. YOLO

            print(
                "  YOLO 분석 중..."
            )


            results = model(
                frame,
                device=0,
                verbose=False
            )[0]


            detected_classes = list(
                set(
                    [
                        model.names[
                            int(box.cls[0])
                        ]

                        for box in results.boxes
                    ]
                )
            )


            print(
                f"  YOLO 객체: "
                f"{detected_classes}"
            )


            # B. 원본 Scene 이미지 저장

            analysis_filename = (
                f"scene_{scene_count:03d}_"
                f"{current_time_sec:.1f}s.jpg"
            )


            analysis_path = os.path.join(
                analysis_dir,
                analysis_filename
            )


            cv2.imwrite(
                analysis_path,
                frame
            )


            print(
                f"  Scene 이미지 저장: "
                f"{analysis_path}"
            )


            # C. rembg 전경 추출

            frame_rgb = cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2RGB
            )


            removed_bg = remove(
                frame_rgb,
                session=rembg_session
            )


            alpha_channel = (
                removed_bg[:, :, 3]
            )


            _, fg_mask = cv2.threshold(
                alpha_channel,
                127,
                255,
                cv2.THRESH_BINARY
            )


            # D. Outline

            gray = cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2GRAY
            )


            blurred = cv2.GaussianBlur(
                gray,
                (5, 5),
                0
            )


            fg_edges_raw = cv2.Canny(
                blurred,
                30,
                100
            )


            fg_edges_masked = (
                cv2.bitwise_and(
                    fg_edges_raw,
                    fg_mask
                )
            )


            contours, _ = cv2.findContours(
                fg_mask,
                cv2.RETR_EXTERNAL,
                cv2.CHAIN_APPROX_SIMPLE
            )


            outline_mask = np.zeros_like(
                fg_mask
            )


            cv2.drawContours(
                outline_mask,
                contours,
                -1,
                255,
                3
            )


            combined_edges = (
                cv2.bitwise_or(
                    fg_edges_masked,
                    outline_mask
                )
            )


            final_outline = cv2.dilate(
                combined_edges,
                np.ones(
                    (2, 2),
                    np.uint8
                ),
                iterations=1
            )


            # E. DotPad 60 x 40

            target_width = 60
            target_height = 40


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
                50,
                150
            )


            small_edges = cv2.bitwise_and(
                small_edges,
                small_mask
            )


            small_contours, _ = cv2.findContours(
                small_mask,
                cv2.RETR_EXTERNAL,
                cv2.CHAIN_APPROX_SIMPLE
            )


            cv2.drawContours(
                small_edges,
                small_contours,
                -1,
                255,
                1
            )


            dotpad_image = small_edges


            # F. 파일 저장
            out_filename = (
                f"scene_{scene_count:03d}_"
                f"{current_time_sec:.1f}s.jpg"
            )


            outline_path = os.path.join(
                outline_dir,
                out_filename
            )


            dotpad_path = os.path.join(
                dot_dir,
                out_filename
            )


            cv2.imwrite(
                outline_path,
                final_outline
            )


            cv2.imwrite(
                dotpad_path,
                dotpad_image
            )


            # G. metadata 추가

            scene_metadata.append(
                {
                    "scene_id":
                        scene_count,

                    "timestamp_sec":
                        current_time_sec,

                    "analysis_image_path":
                        analysis_path,

                    "outline_image_path":
                        outline_path,

                    "dotpad_image_path":
                        dotpad_path,

                    "yolo_objects":
                        detected_classes,

                    "english_desc":
                        "",

                    "braille_text":
                        ""
                }
            )



            save_scene_metadata(
                scene_metadata,
                output_dir
            )


            prev_hist = hist

            frames_since_last_scene = 0

            scene_count += 1


        else:

            frames_since_last_scene += 1



    cap.release()


    print("\n")
    print("=" * 60)
    print(
        f"PHASE 1 완료 - "
        f"{len(scene_metadata)}개 Scene"
    )
    print("=" * 60)

    # 오디오 추출

    extract_audio(
        video_path,
        output_dir
    )


    # Scene metadata 최종 저장

    save_scene_metadata(
        scene_metadata,
        output_dir
    )


    # 이제 YOLO + rembg를 GPU에서 제거

    release_local_gpu_models(
        model,
        rembg_session
    )


    model = None
    rembg_session = None


    # PHASE 2 시작
    # AI 서버 시작

    server_process = start_ai_server()


    if server_process is None:

        print(
            "AI 서버 시작 실패"
        )

        return scene_metadata


    API_BASE_URL = (
        "http://127.0.0.1:8001/api"
    )



    if not wait_for_ai_server(
        API_BASE_URL,
        timeout_sec=180
    ):

        print(
            "AI 서버가 준비되지 않았습니다."
        )

        return scene_metadata


    # Moondream

    scene_metadata = (
        analyze_scenes_with_moondream(
            API_BASE_URL,
            scene_metadata,
            output_dir
        )
    )


    # PHASE 3 Gemma

    print("\n")
    print("=" * 60)
    print(
        "PHASE 3 : Moondream → Gemma 전환"
    )
    print("=" * 60)


    if not switch_ai_server_to_llm(
        API_BASE_URL
    ):

        print(
            "Gemma 전환 실패"
        )

        return scene_metadata


    print("\n")
    print(
        "Gemma 한국어 요약"
    )


    for data in scene_metadata:

        scene_id = data["scene_id"]

        english_desc = (
            data.get(
                "english_desc",
                ""
            )
        )


        print("\n")
        print(
            f"[Scene {scene_id}] "
            f"한국어 요약 중"
        )


        korean_desc = summarize_scene(
            API_BASE_URL,
            english_desc
        )


        data["braille_text"] = (
            korean_desc
        )


        print(
            f"  Eng: {english_desc}"
        )

        print(
            f"  Kor: {korean_desc}"
        )

        print(
            f"  문자 수: "
            f"{len(korean_desc)}"
        )


        save_scene_metadata(
            scene_metadata,
            output_dir
        )


    # 최종 descriptions.txt

    txt_path = os.path.join(
        output_dir,
        "descriptions.txt"
    )


    try:

        with open(
            txt_path,
            "w",
            encoding="utf-8"
        ) as f:

            for data in scene_metadata:

                f.write(
                    f"[{data['timestamp_sec']:.1f}s] "
                    f"{data['braille_text']}\n"
                )


        print(
            f"\n텍스트 결과 저장 완료: "
            f"{txt_path}"
        )


    except Exception as e:

        print(
            f"description.txt 저장 실패: {e}"
        )


    # 최종 JSON

    save_scene_metadata(
        scene_metadata,
        output_dir
    )



    print("\n")
    print("=" * 60)
    print("작업 완료!")
    print("=" * 60)

    print(
        f"총 Scene 수: "
        f"{len(scene_metadata)}"
    )

    print(
        f"결과 폴더: "
        f"{output_dir}"
    )

    print(
        f"메타데이터: "
        f"{os.path.join(output_dir, 'scene_metadata.json')}"
    )

    print(
        f"텍스트: "
        f"{txt_path}"
    )


    return scene_metadata


# 프로그램 시작

if __name__ == "__main__":

    video_file = "video.mp4"

    if os.path.exists(video_file):

        process_video_to_tactile_edges(
            video_file,
            min_interval_sec=5
        )

    else:

        print(
            f"{video_file} 파일을 찾을 수 없습니다."
        )
