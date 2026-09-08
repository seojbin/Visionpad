setup 1회 실행 후 run.bat 실행하기
Moondream3 소스코드 수정필요
.cache\huggingface\modules\transformers_modules\moondream\moondream3_hyphen_preview\5112966d1a723413b1c9a1e8bea272b72e647b35\moondream.py
mask.seq_lengths = (1, mask.seq_lengths[1])를
if hasattr(mask, 'seq_lengths'):
    mask.seq_lengths = (1, mask.seq_lengths[1])로.


실행시 비디오 이름 video.mp4(    video_file = "video.mp4")

필요ai - models폴더밑에 gemma-4-E4B-it-Q6_K.gguf등 gguf 위치하기

ffmpeg 설치& PATH둥록필요