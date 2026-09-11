# 설정 적용 안내

압축 파일은 수정 파일 묶음입니다. 기존 프로젝트에 같은 경로로 덮어쓰세요.
기존 dotpad.py, hardware.mjs, 음원 폴더 등은 계속 사용합니다.
설정 파일 이름은 반드시 game_config.json입니다.
수정 후 서버를 재시작하고 브라우저에서 Ctrl+F5를 누르세요.

## 조절할 설정

모든 경로는 game_config.json의 interaction 아래에 있습니다.

| 설정 경로 | 기본값 | 의미 |
| --- | --- | --- |
| feedback.disappear_delay_ms | 1000 | 물·비료 지점과 요리 선을 통과 후 유지할 시간. 마지막 지점 완료 전환에도 적용. 0이면 즉시 사라짐 |
| feedback.visual_refresh_interval_ms | 100 | 포인터가 정지해도 표시를 갱신하는 주기. 최소 50ms, 실제 삭제 시점은 갱신/통신 때문에 조금 늦을 수 있음 |
| cooking.resume_marker_delay_ms | 2000 | 실제 요리 진행도가 늘지 않을 때 중단 네모를 표시할 시간 |
| cooking.stir_scale | 1.6 | 레시피의 젓기 경로 확대 배율. 화면 여백을 넘지 않도록 제한됨 |
| inventory.items_per_page | 12 | 페이지당 물품 종류 수. 현재 패드 배치에서 1~12 지원 |
| inventory.hide_zero_items | true | 수량 0인 물품 숨김 |
| audio.default_volume | 0.7 | 효과음 기본 전체 볼륨(0~1). 화면 슬라이더로 조절 가능 |
| audio.work_gain.cut / cook | 0.8 | 자르기·젓기 작업음 게인 |
| audio.work_gain.water / soil | 0.45 | 물·비료 작업음 게인 |
| audio.work_gain_during_tts.cut / cook | 0.32 | TTS 재생 중 요리 작업음 게인 |
| audio.work_gain_during_tts.water / soil | 0.18 | TTS 재생 중 물·비료 작업음 게인 |
| audio.reward_gain | 0.42 | correct 게인 |
| audio.reward_gain_during_tts | 0.25 | TTS 재생 중 correct 게인 |
| audio.cooking_correct_interval_ms | 650 | 요리 correct 최소 간격 |
| audio.other_correct_interval_ms | 90 | 물·비료·수확 correct 최소 간격 |
| audio.click_duration_ms | 650 | 물·비료 짧은 클릭음 최대 길이 |
| audio.motion_idle_ms | 450 | 요리 포인터가 멈춘 뒤 작업음을 줄일 때까지 시간 |
| audio.motion_check_interval_ms | 120 | 요리 포인터 움직임 확인 주기 |
| audio.correct_max_load_age_ms | 650 | 로딩으로 너무 늦어진 correct를 생략하는 기준 |
| audio.max_reward_sources | 2 | 동시에 재생할 correct 소스 최대 개수(1 이상) |

## 코드 연결

- game_engine.py: disappear_delay_seconds, resume_marker_delay_seconds, stir_scale,
  inventory_items_per_page, inventory_hide_zero_items 변수로 설정을 읽습니다.
- 서버 상태의 client_settings로 브라우저에 오디오·표시 갱신 설정을 전달합니다.
- game.html: applyClientSettings()에서 반영합니다. 설정이 같으면 볼륨 슬라이더 값을 덮어쓰지 않습니다.
- game-audio.js: configure()와 this.settings를 통해 재생 설정을 참조합니다.
- game_app.py: 지연 표시용 /api/visual-tick 경로를 포함합니다.