import queue
import threading

import sounddevice as sd


class YouTubeAudioOutput:

    def __init__(
        self,
        output_device=None,
        queue_max_chunks=512
    ):
        self.output_device = output_device
        self.queue_max_chunks = int(
            queue_max_chunks
        )

        self.lock = threading.Lock()
        self.stop_event = threading.Event()

        self.audio_queue = None
        self.worker_thread = None

        self.sample_rate = None
        self.delay_sec = 0.0
        self.channels = 1

        self.running = False
        self.playing = False
        self.received_frames = 0
        self.dropped_chunks = 0


    def start(
        self,
        sample_rate,
        delay_sec
    ):
        self.stop()

        sample_rate = int(
            sample_rate
        )

        delay_sec = max(
            0.0,
            float(delay_sec)
        )

        if sample_rate <= 0:
            raise ValueError(
                "sample_rate는 0보다 커야 합니다."
            )

        with self.lock:
            self.sample_rate = sample_rate
            self.delay_sec = delay_sec
            self.channels = 1

            self.audio_queue = queue.Queue(
                maxsize=self.queue_max_chunks
            )

            self.stop_event = threading.Event()

            self.running = True
            self.playing = False
            self.received_frames = 0
            self.dropped_chunks = 0

            self.worker_thread = threading.Thread(
                target=self._playback_worker,
                name="VideoBrailleAudioOutput",
                daemon=True
            )

            self.worker_thread.start()

        print(
            f"[Audio] 시작 "
            f"sample_rate={sample_rate} "
            f"delay={delay_sec:.2f}s"
        )


    def push_pcm(
        self,
        pcm_bytes
    ):
        if not pcm_bytes:
            return

        with self.lock:
            audio_queue = self.audio_queue
            running = self.running

        if (
            not running
            or audio_queue is None
        ):
            return

        frame_size = 4 * self.channels

        valid_size = (
            len(pcm_bytes)
            // frame_size
        ) * frame_size

        if valid_size <= 0:
            return

        chunk = pcm_bytes[:valid_size]

        try:
            audio_queue.put_nowait(
                chunk
            )

            with self.lock:
                self.received_frames += (
                    valid_size
                    // frame_size
                )

        except queue.Full:
            try:
                audio_queue.get_nowait()
            except queue.Empty:
                pass

            try:
                audio_queue.put_nowait(
                    chunk
                )
            except queue.Full:
                pass

            with self.lock:
                self.dropped_chunks += 1


    def stop(self):
        with self.lock:
            thread = self.worker_thread
            stop_event = self.stop_event

            if not self.running and thread is None:
                return

            self.running = False
            self.playing = False

            self.worker_thread = None
            self.audio_queue = None

        stop_event.set()

        if (
            thread is not None
            and thread.is_alive()
            and thread is not threading.current_thread()
        ):
            thread.join(
                timeout=1.5
            )

        print(
            "[Audio] 중지"
        )


    def status(self):
        with self.lock:
            buffered_chunks = 0

            if self.audio_queue is not None:
                buffered_chunks = (
                    self.audio_queue.qsize()
                )

            return {
                "running": self.running,
                "playing": self.playing,
                "sample_rate": self.sample_rate,
                "delay_sec": self.delay_sec,
                "received_frames": self.received_frames,
                "buffered_chunks": buffered_chunks,
                "dropped_chunks": self.dropped_chunks,
                "output_device": self.output_device
            }


    def _playback_worker(self):
        with self.lock:
            sample_rate = self.sample_rate
            delay_sec = self.delay_sec
            audio_queue = self.audio_queue
            stop_event = self.stop_event
            output_device = self.output_device

        if audio_queue is None:
            return

        target_frames = int(
            sample_rate
            * delay_sec
        )

        buffered_frames = 0
        prebuffer = []

        try:
            while not stop_event.is_set():
                try:
                    chunk = audio_queue.get(
                        timeout=0.2
                    )
                except queue.Empty:
                    continue

                prebuffer.append(
                    chunk
                )

                buffered_frames += (
                    len(chunk)
                    // 4
                )

                if (
                    buffered_frames
                    >= target_frames
                ):
                    break

            if stop_event.is_set():
                return

            print(
                f"[Audio] 버퍼 준비 "
                f"{buffered_frames / sample_rate:.2f}s"
            )

            with sd.RawOutputStream(
                samplerate=sample_rate,
                channels=1,
                dtype="float32",
                device=output_device,
                blocksize=0
            ) as stream:

                with self.lock:
                    self.playing = True

                print(
                    "[Audio] 스피커 재생 시작"
                )

                for chunk in prebuffer:
                    if stop_event.is_set():
                        return

                    stream.write(
                        chunk
                    )

                while not stop_event.is_set():
                    try:
                        chunk = audio_queue.get(
                            timeout=0.2
                        )
                    except queue.Empty:
                        continue

                    stream.write(
                        chunk
                    )

        except Exception as e:
            print(
                f"[Audio] 출력 오류: {e}"
            )

        finally:
            with self.lock:
                self.playing = False
                self.running = False
