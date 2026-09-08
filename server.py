from pathlib import Path
import io
import base64
import asyncio
import gc

import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from PIL import Image
from transformers import AutoModelForCausalLM
from llama_cpp import Llama


app = FastAPI(title="AI Server")
#GPU락
gpu_lock = asyncio.Lock()

moondream_model = None
llm = None

MODE = "vision"  # vision / llm


BASE_DIR = Path(__file__).resolve().parent
GEMMA_PATH = BASE_DIR / "models" / "gemma-4-E4B-it-Q6_K.gguf"


def print_gpu_memory(label=""):
    if not torch.cuda.is_available():
        print(f"[GPU] {label} CUDA 사용 불가")
        return

    free, total = torch.cuda.mem_get_info()

    free_gb = free / (1024 ** 3)
    total_gb = total / (1024 ** 3)
    used_gb = total_gb - free_gb

    print(
        f"[GPU] {label} "
        f"사용={used_gb:.2f}GB / "
        f"전체={total_gb:.2f}GB / "
        f"가용={free_gb:.2f}GB"
    )


# Moondream 로드

def load_moondream():
    global moondream_model, MODE

    if moondream_model is not None:
        return

    print("1. Moondream3 로드 중")

    print_gpu_memory("Moondream 로드 전")

    moondream_model = AutoModelForCausalLM.from_pretrained(
        "moondream/moondream3-preview",
        trust_remote_code=True,
        dtype=torch.float16,
        device_map={"": "cuda"},
        attn_implementation="eager"
    )

    MODE = "vision"

    print_gpu_memory("Moondream 로드 후")
    print("Moondream3 로드 완료")


# ---------------------------------------------------------
# Moondream GPU 완전 해제
# ---------------------------------------------------------

def unload_moondream():
    global moondream_model

    if moondream_model is None:
        print("Moondream은 이미 해제되어 있습니다.")
        return

    print("Moondream GPU 메모리 해제 시작")

    try:
        if torch.cuda.is_available():
            torch.cuda.synchronize()

        del moondream_model
        moondream_model = None

        gc.collect()

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
            torch.cuda.synchronize()

        print_gpu_memory("Moondream 해제 후")
        print("Moondream GPU 메모리 해제 완료")

    except Exception as e:
        print(f"Moondream 해제 중 경고: {e}")
        moondream_model = None


# Gemma 로드

def load_gemma():
    global llm, MODE

    if llm is not None:
        print("Gemma는 이미 로드되어 있습니다.")
        MODE = "llm"
        return

    if not GEMMA_PATH.exists():
        raise FileNotFoundError(
            f"Gemma GGUF 파일을 찾을 수 없습니다:\n{GEMMA_PATH}"
        )

    print("2. Gemma4 (GGUF) 로드 중")
    print("Gemma 경로:", GEMMA_PATH)
    print("파일 존재:", GEMMA_PATH.exists())
    print("파일 크기:", GEMMA_PATH.stat().st_size, "bytes")

    print_gpu_memory("Gemma 로드 전")

    llm = Llama(
        model_path=str(GEMMA_PATH),
        n_gpu_layers=-1,
        n_ctx=1024,
        verbose=True
    )

    MODE = "llm"

    print_gpu_memory("Gemma 로드 후")
    print("Gemma4 로드 완료")



load_moondream()

print("AI 릴레이 서버 구동 완료!")
print("현재 모드: VISION")



class VisionRequest(BaseModel):
    image_base64: str
    prompt: str


class SummaryRequest(BaseModel):
    english_desc: str



@app.post("/api/vision")
async def process_vision(req: VisionRequest):

    async with gpu_lock:

        if moondream_model is None:
            raise HTTPException(
                status_code=503,
                detail="Moondream이 현재 로드되어 있지 않습니다."
            )

        if MODE != "vision":
            raise HTTPException(
                status_code=503,
                detail=f"현재 서버 모드는 {MODE} 입니다."
            )

        try:
            img_data = base64.b64decode(req.image_base64)

            pil_image = Image.open(
                io.BytesIO(img_data)
            ).convert("RGB")

            with torch.no_grad():

                enc_image = moondream_model.encode_image(
                    pil_image
                )

                result = moondream_model.answer_question(
                    enc_image,
                    req.prompt
                ).strip()

            return {
                "result": result
            }

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=str(e)
            )


@app.post("/api/switch-to-llm")
async def switch_to_llm():

    global MODE

    async with gpu_lock:

        try:
            print("\n")
            print("LLM 모드 전환 시작")

            #Moondream 제거
            unload_moondream()

            gc.collect()

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.ipc_collect()

            print_gpu_memory("Gemma 로드 직전")

            # Gemma 로드
            load_gemma()

            MODE = "llm"


            print("LLM 모드 전환 완료")

            return {
                "status": "ok",
                "mode": MODE
            }

        except Exception as e:

            MODE = "vision"

            raise HTTPException(
                status_code=500,
                detail=f"LLM 전환 실패: {e}"
            )





@app.post("/api/summarize")
async def process_summary(req: SummaryRequest):

    async with gpu_lock:

        if llm is None:
            raise HTTPException(
                status_code=503,
                detail="Gemma가 현재 로드되어 있지 않습니다."
            )

        if MODE != "llm":
            raise HTTPException(
                status_code=503,
                detail=f"현재 서버 모드는 {MODE} 입니다."
            )

        try:


            system_prompt = (
                "너는 시각장애인용 20셀 점자 디스플레이의 "
                "초단문 장면 요약기다. "

                "영문 장면 설명을 읽고 핵심 정보만 "
                "한국어 10자 이내로 압축한다. "

                "정보 선택 우선순위는 다음과 같다. "
                "1 시간 "
                "2 장소 "
                "3 인물 "
                "4 행동 "
                "5 화면에 표시된 글자 "

                "시간이 있으면 가장 먼저 넣는다. "
                "장소가 있으면 넣는다. "
                "인물이 있으면 넣는다. "
                "행동이 있으면 넣는다. "

                "시간 장소 인물 행동이 충분히 있으면 "
                "화면의 장식이나 긴 설명은 버린다. "

                "시간 장소 인물 행동이 부족하거나 거의 없고 "
                "화면에 중요한 글자가 보이면 "
                "그 글자의 핵심 내용을 요약한다. "

                "인물 수는 숫자로 표시한다. "
                "예: 남자2 여자1 사람3 자동차2 "

                "조사 은 는 이 가 을 를 에 에서 로 으로 와 과 "
                "등은 가능한 한 사용하지 않는다. "

                "불필요한 관형어 형용사 부사 긴 수식어를 제거한다. "

                "문장으로 쓰지 말고 "
                "명사와 짧은 동작 표현을 이어 붙인다. "

                "예: "
                "실외 문앞 남자2 대화 "
                "교실 여자1 칠판쓰기 "
                "저녁 거리 남자2 걷기 "

                "같은 의미를 반복하지 않는다. "

                "가장 중요한 정보를 우선 남기고 "
                "10자를 넘기지 않는다. "

                "10자보다 짧더라도 의미가 완성되면 더 늘리지 않는다. "

                "마침표 쉼표 따옴표 괄호 슬래시 콜론 세미콜론을 사용하지 않는다. "

                "설명 문장이나 해설을 절대 출력하지 않는다. "

                "오직 최종 요약 한 줄만 출력한다."

                "가능하면 받침이 있는 문자를 쓰지 않는다"
            )


            # -------------------------------------------------
            # Few-shot 예시
            # -------------------------------------------------

            full_user_prompt = f"""다음 영문 장면을
점자 디스플레이용 초단문 한국어로 요약해.

[규칙]
- 최대 10자
- 시간 우선
- 장소 다음
- 인물 다음
- 행동 다음
- 중요 글자가 있으면 글자 내용 요약
- 조사 생략
- 긴 설명 삭제
- 인물 수는 숫자
- 명사와 짧은 행동 중심
- 기호 금지
- 최종 결과만 출력

[예시 1]
입력:
A cartoon milk carton character with blue arms holds a white paper on a light gray concrete surface.

출력:
야외 도로 우유인형 서있음

[예시 2]
입력:
Two man stand on a sidewalk near a red door.

출력:
실외 문앞 남자2 대화

[예시 3]
입력:
The image shows a large title, 'A few month later'.

출력:
글자 몇 달 뒤

[예시 4]
입력:
A woman is walking alone inside a classroom.

출력:
교실 여자1 걷기

[예시 5]
입력:
Two cars are moving along a city road at night.

출력:
밤 도시도로 자동차2 이동

[예시 6]
입력:
A man is standing outside a store holding a bag.

출력:
가게앞 남자1 서있음

[입력 영문]
{req.english_desc}

[출력]
"""


            # Gemma 호출

            try: llm.reset() 
            except Exception: 
                pass 
            response = llm.create_chat_completion( messages=[ { "role": "system", "content": system_prompt }, { "role": "user", "content": full_user_prompt } ], max_tokens=16, temperature=0.01 )

            result = (
                response["choices"][0]["message"]["content"]
                .strip()
            )


            # 줄바꿈 제거
            result = result.replace("\n", " ")

            # 기호 제거
            for char in [
                ".",
                ",",
                '"',
                "'",
                "`",
                "(",
                ")",
                "[",
                "]",
                "{",
                "}",
                ":",
                ";",
                "/",
                "\\",
                "!",
                "?",
                "·",
                "•",
                "-"
            ]:
                result = result.replace(char, "")


            # 중복 공백 제거
            result = " ".join(result.split()).strip()


            # 한국어 조사 제거


            particles = [
                "에서는",
                "에서",
                "으로",
                "에게",
                "까지",
                "부터",
                "처럼",
                "보다",
                "하고",
                "와",
                "과",
                "은",
                "는",
                "이",
                "가",
                "을",
                "를",
                "에",
                "로"
            ]

            words = result.split()

            cleaned_words = []

            for word in words:

                cleaned = word

                for particle in particles:

                    if (
                        len(cleaned) > len(particle)
                        and cleaned.endswith(particle)
                    ):
                        cleaned = cleaned[
                            :-len(particle)
                        ]
                        break

                if cleaned:
                    cleaned_words.append(cleaned)


            result = " ".join(cleaned_words).strip()


            if len(result) > 10:
                result = result[:10].rstrip()



            if not result:
                result = "분석실패"


            print(
                f"[Gemma 요약] "
                f"{result} "
                f"({len(result)}자)"
            )


            return {
                "result": result
            }


        except Exception as e:

            raise HTTPException(
                status_code=500,
                detail=str(e)
            )




@app.get("/api/status")
async def status():

    return {
        "mode": MODE,
        "moondream_loaded": moondream_model is not None,
        "gemma_loaded": llm is not None
    }