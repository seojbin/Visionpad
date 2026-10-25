# Dotdew Valley

[English](README.md) | 한국어

60×40 촉각 디스플레이인 Dot Pad용 농사·생활 시뮬레이션 게임이다. 시각장애인과 저시력 사용자가 촉각과 소리로 게임 세계를 읽고, 읽고 있는 바로 그 화면에서 직접 행동한다. 집, 농장, 마을, 광산, 낚시 호수를 오가며 농사, 요리, 채굴, 낚시, 거래, 연구를 한다. 도형과 영어 음성이 안내하며 점자를 몰라도 된다.

브라우저 시뮬레이터는 마우스와 키보드를 지원한다. USB 또는 블루투스 Dot Pad와 외부 손 추적 카메라를 연결할 수 있고, 별도의 Visual Companion 창이 같은 게임을 이미지로 보여 주어 저시력 사용자와 함께하는 사람이 볼 수 있다.

## 설치

Python 3.11 이상을 설치한 뒤 **install-windows.bat**(Windows) 또는 **install-mac.command**(macOS)를 한 번 연다. 프로젝트 안에 `.venv/`를 만들고 `engine/requirements.txt`를 설치하며 영어 음성 두 개를 내려받는다. 전역 Python에는 아무것도 설치하지 않는다. 이 단계에는 인터넷이 필요하며 계정이나 API 키는 쓰지 않는다.

프로젝트 폴더에서 직접 설치하려면:

```
python -m venv .venv
.venv\Scripts\activate                 # macOS / Linux: source .venv/bin/activate
python -m pip install -r engine/requirements.txt
python engine/tools/prepare_speech.py --download
```

`python engine/launcher/check_setup.py --synthesize`는 게임을 시작하지 않고 패키지·파일·소리·음성을 점검한다.

## 실행

**start-windows.bat**(http://127.0.0.1:8003) 또는 **start-mac.command**(http://127.0.0.1:8000)를 열거나 `python engine/launcher/launch_game.py --prepare-demo`(포트 8000)를 실행한다. 실행기는 설치 상태를 확인하고, 게임 서버를 새로 시작하거나 이미 켜진 서버를 재사용하며, 시연 음성을 준비하고 브라우저를 연다. 플레이하는 동안 실행 창을 열어 둔다.

1. 게임 페이지를 클릭하거나 키를 눌러 오디오를 켠다.
2. **Open visual display**를 눌러 시각화 창을 연다(팝업 허용).
3. F3를 길게 눌러 저장한다. 서버를 끄면 진행이 사라진다. 저장 파일은 `saves/`에 있다.

## 조작

| 입력 | 동작 |
|---|---|
| 올려놓기(호버) | 오브젝트 이름과 상태 듣기 |
| 클릭, Enter, F4 | 선택, 시설 사용, 돌 치기, 낚시 |
| 목표나 경로 위로 이동 | 물 주기, 비료, 수확, 요리 경로 따라가기 |
| F1 / F2 | 지도 / 인벤토리. 다시 누르면 돌아온다 |
| F3 짧게 / 길게 | 저장 목록 열기 / 새 슬롯에 저장 |
| 왼쪽·오른쪽 방향키 또는 패드 버튼 | 이동, 뒤로 가기, 페이지 넘기기 |
| W A S D (Shift는 큰 이동) | 포인터 이동 |
| Space | 누름/뗌 전환 |

장소 순서는 농장 ↔ 집 ↔ 마을 ↔ 광산 ↔ 낚시 호수다. 탐색과 이동은 게임 시간을 쓰지 않으며, 올려놓기만으로는 행동이 일어나지 않는다.

## 폴더

| 폴더 | 내용 |
|---|---|
| `engine/` | 공통 코드: 서버, 엔진 핵심, Dot Pad 화면, 저장, 음성, 브라우저 재생기(오디오·키·패드), Visual Companion, 설정, 실행기·설치 로직, 카메라 추적, 개발 도구, 공통 테스트. [engine/README.md](engine/README.md) 참고(영어). |
| `game/` | 기능마다 한 폴더(cooking, farming, fishing, flowers, harvest, home, inventory, minimap, mining, npc, research, seafood, shop, village). 각 폴더에 Python 코드, 브라우저 문구, 소리, 이미지, 테스트, README가 있다. [game/README.md](game/README.md) 참고(영어). |
| `install-*`, `start-*` | `engine/launcher/`를 호출하는 얇은 실행 파일. |
| `AGENTS.md` | 사람과 AI 에이전트를 위한 규칙: 폴더 담당, 승인이 필요한 변경, 저장 형식. |

## 기능 추가

1. `game/<name>/`에 `feature.py`(`register(reg)`에서 `engine/core/registry.py`를 통해 화면·행동·그리기·상태·이벤트를 선언하는 `Feature` 하위 클래스)와 이를 `Feature`로 내보내는 `__init__.py`를 만든다.
2. `game/__init__.py`의 `ENABLED`에 `<name>`을 추가한다.
3. 선택: `client.js`(화면 문구), `audio/`, `assets/`, `engine/config/game.json`의 설정 항목, `game/<name>/tests/`의 테스트, README.

2단계, 설정 값, 소리, 이미지, 그리고 `engine/`의 모든 변경은 승인이 필요하다. 예시는 [game/README.md](game/README.md), 규칙은 [AGENTS.md](AGENTS.md)에 있다.

## 테스트

```
.venv\Scripts\python.exe engine\tools\run_tests.py                   # 전체
.venv\Scripts\python.exe engine\tools\run_tests.py --feature fishing # 한 기능
```

macOS/Linux에서는 `.venv/bin/python engine/tools/run_tests.py`를 쓴다. Python과 Node 테스트(Node.js 20 이상), 브라우저 점검을 실행한다(`--no-browser`로 생략 가능. 브라우저 점검에는 `pip install -r engine/requirements-dev.txt`와 `python -m playwright install chromium`이 필요). 마지막 줄이 **All green.** 이어야 한다. 알려진 실패는 테스트 안에 표시되어 있고 이유와 함께 출력된다.

## 라이선스 안내

음성은 [Piper](https://pypi.org/project/piper-tts/)(GPL-3.0 이상)와 `en_US-hfc_female-medium`, `en_US-hfc_male-medium` 음성 모델을 사용한다. 모델의 학습 데이터는 CC BY-NC-SA 4.0이므로 **비상업적 용도로만** 사용할 수 있다. 모델은 설치할 때 내려받으며 저장소에 포함되지 않는다. 출처: [engine/README.md](engine/README.md#voices-and-their-sources).
