"""
メインアプリケーションコントローラーモジュール

音声録音、文字起こし、UI、ホットキー処理など、
すべてのコンポーネントを統合するメインコントローラー。
"""

import queue
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Set, Union

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QApplication
from pynput import keyboard

from .config import ConfigManager, HotkeyMode, TranscriptionBackend
from .config.constants import CONFIG_CHECK_INTERVAL_SEC
from .config.types import TranscriptionTask
from .core import AudioRecorder, GroqTranscriber, InputHandler, OpenAITranscriber, Transcriber
from .ui import DynamicIslandOverlay, SettingsWindow, SystemTray
from .utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class HotkeySlot:
    """
    ホットキースロットの状態管理クラス。

    各スロットのホットキー設定と、API使用時のTranscriberインスタンスを保持する。

    Attributes:
        slot_id: スロットID（1または2）
        hotkey: ホットキー文字列
        hotkey_mode: 動作モード（hold/toggle）
        required_keys: パース済みのキーセット
        backend: 使用するバックエンド
        api_model: APIモデル名
        api_prompt: APIプロンプト
        api_transcriber: API Transcriberインスタンス（APIバックエンドの場合のみ）
    """
    slot_id: int
    hotkey: str
    hotkey_mode: str
    required_keys: Set[str]
    backend: str
    api_model: str
    api_prompt: str
    api_transcriber: Optional[Union[GroqTranscriber, OpenAITranscriber]] = None


class SuperWhisperApp(QObject):
    """
    メインアプリケーションコントローラー。
    
    すべてのコンポーネント（音声録音、文字起こし、UI、設定、ホットキー）を
    統合し、アプリケーション全体のライフサイクルを管理する。
    
    Signals:
        status_changed: 状態変更通知（UIスレッドセーフ）
        text_ready: 文字起こし完了通知
    """
    
    # UIスレッドセーフな更新用シグナル
    status_changed = Signal(str)
    text_ready = Signal(str)
    
    def __init__(self) -> None:
        """アプリケーションを初期化する。"""
        super().__init__()
        logger.info("WhisperWinを初期化中...")
        
        self._setup_config()
        self._setup_core_components()
        self._setup_ui_components()
        self._setup_signals()
        self._setup_state()
        self._start_background_threads()
        self._preload_models_async()  # 状態初期化後にプリロード

        logger.info("アプリケーション準備完了。")
        self.status_changed.emit("idle")

    def _setup_config(self) -> None:
        """設定マネージャーを初期化する。"""
        self._config = ConfigManager()

    def _setup_core_components(self) -> None:
        """コアビジネスロジックコンポーネントを初期化する。"""
        self._recorder = AudioRecorder()

        # 音声レベルコールバックを設定（波形アニメーション用）
        self._recorder.set_level_callback(self._on_audio_level)

        # ローカルTranscriberは共有インスタンス（遅延初期化）
        self._local_transcriber: Optional[Transcriber] = None

        self._input_handler = InputHandler()

    def _get_transcriber_for_slot(self, slot: HotkeySlot) -> Union[Transcriber, GroqTranscriber, OpenAITranscriber]:
        """
        スロットに対応するTranscriberを取得する。

        ローカルバックエンドの場合は共有インスタンスを返し、
        APIバックエンドの場合はスロット固有のインスタンスを返す。

        Args:
            slot: ホットキースロット

        Returns:
            Transcriberインスタンス
        """
        if slot.backend == TranscriptionBackend.LOCAL.value:
            if self._local_transcriber is None:
                self._local_transcriber = self._create_local_transcriber()
            return self._local_transcriber
        else:
            return slot.api_transcriber

    def _create_api_transcriber(self, slot: HotkeySlot) -> Optional[Union[GroqTranscriber, OpenAITranscriber]]:
        """
        APIバックエンドのTranscriberを作成する。

        Args:
            slot: ホットキースロット

        Returns:
            APITranscriberインスタンス、またはNone
        """
        language = self._config.get("language", "ja")
        vad_filter = self._config.get("vad_filter", True)
        vad_min_silence = self._config.get("vad_min_silence_duration_ms", 500)

        if slot.backend == TranscriptionBackend.GROQ.value:
            transcriber = GroqTranscriber(
                model=slot.api_model,
                language=language,
                prompt=slot.api_prompt,
                vad_filter=vad_filter,
                vad_min_silence_duration_ms=vad_min_silence,
            )

            if not transcriber.is_available():
                logger.warning(
                    "Groq APIが利用できません（SDKが未インストールまたはGROQ_API_KEYが未設定）。"
                )
                self._show_backend_warning("groq_unavailable")
                return None

            logger.info(f"ホットキー{slot.slot_id}: Groq API使用 (モデル={transcriber.model})")
            return transcriber

        elif slot.backend == TranscriptionBackend.OPENAI.value:
            transcriber = OpenAITranscriber(
                model=slot.api_model,
                language=language,
                prompt=slot.api_prompt,
                vad_filter=vad_filter,
                vad_min_silence_duration_ms=vad_min_silence,
            )

            if not transcriber.is_available():
                logger.warning(
                    "OpenAI APIが利用できません（SDKが未インストールまたはOPENAI_API_KEYが未設定）。"
                )
                self._show_backend_warning("openai_unavailable")
                return None

            logger.info(f"ホットキー{slot.slot_id}: OpenAI API使用 (モデル={transcriber.model})")
            return transcriber

        return None

    def _create_local_transcriber(self) -> Transcriber:
        """ローカルGPU Transcriberを作成する（共通）。"""
        logger.info("ローカルGPUバックエンド（faster-whisper）を使用")
        local_config = self._config.get("local_backend", {})
        return Transcriber(
            model_size=local_config.get("model_size", "base"),
            compute_type=local_config.get("compute_type", "float16"),
            language=self._config.get("language", "ja"),
            release_memory_delay=local_config.get("release_memory_delay", 300),
            vad_filter=self._config.get("vad_filter", True),
            vad_min_silence_duration_ms=self._config.get("vad_min_silence_duration_ms", 500),
            condition_on_previous_text=local_config.get("condition_on_previous_text", False),
            no_speech_threshold=local_config.get("no_speech_threshold", 0.6),
            log_prob_threshold=local_config.get("log_prob_threshold", -1.0),
            no_speech_prob_cutoff=local_config.get("no_speech_prob_cutoff", 0.7),
            beam_size=local_config.get("beam_size", 5),
            model_cache_dir=local_config.get("model_cache_dir", ""),
        )

    def _show_backend_warning(self, warning_type: str) -> None:
        """
        バックエンド問題についてユーザーに警告を表示する。

        Args:
            warning_type: 警告タイプ（"groq_unavailable", "openai_unavailable"等）
        """
        messages = {
            "groq_unavailable": "Groq API unavailable\nUsing local GPU",
            "openai_unavailable": "OpenAI API unavailable\nUsing local GPU",
        }
        message = messages.get(warning_type, "API unavailable\nUsing local GPU")
        self._overlay.show_temporary_message(
            message,
            duration_ms=3000,
            is_error=False
        )

    def _preload_vad_model(self) -> None:
        """
        VADモデルをバックグラウンドでプリロードする。

        アプリ起動時に呼び出すことで、最初の音声入力時の
        VADモデルロード遅延を回避する。
        """
        def _preload_worker():
            try:
                # APIバックエンドのスロットがあればVADをプリロード
                if hasattr(self, '_hotkey_slots'):
                    for slot in self._hotkey_slots.values():
                        if slot.api_transcriber and hasattr(slot.api_transcriber, 'preload_vad'):
                            slot.api_transcriber.preload_vad()
                logger.debug("VADプリロード完了")
            except Exception as e:
                logger.warning(f"VADプリロードに失敗しました: {e}")

        # バックグラウンドスレッドでプリロード
        threading.Thread(target=_preload_worker, daemon=True).start()

    def _preload_local_transcriber(self) -> None:
        """
        ローカルTranscriberとWhisperモデルを事前にロードする。

        最初の文字起こし時の遅延を回避するため、起動時に呼び出す。
        """
        try:
            if self._local_transcriber is None:
                logger.info("ローカルTranscriberをプリロード中...")
                self._local_transcriber = self._create_local_transcriber()

            logger.info("Whisperモデルをプリロード中...")
            self._local_transcriber.load_model()
            logger.info("Whisperモデルのプリロードが完了しました")
        except Exception as e:
            logger.warning(f"ローカルTranscriberのプリロードに失敗: {e}")

    def _preload_models_async(self) -> None:
        """
        起動時にモデルをバックグラウンドでプリロードする。

        UIをブロックせずに、VADとWhisperモデルをロードする。
        """
        if not self._config.get("preload_on_startup", True):
            logger.info("起動時プリロードが無効です")
            return

        def _preload_worker():
            try:
                # 1. API Transcriber用VADをプリロード
                for slot in self._hotkey_slots.values():
                    if slot.api_transcriber and hasattr(slot.api_transcriber, 'preload_vad'):
                        slot.api_transcriber.preload_vad()
                        logger.info(f"スロット{slot.slot_id}のVADをプリロードしました")

                # 2. ローカルバックエンドを使用するスロットがあればWhisperモデルをプリロード
                uses_local_backend = any(
                    slot.backend == "local" for slot in self._hotkey_slots.values()
                )
                if uses_local_backend:
                    self._preload_local_transcriber()

                logger.info("モデルプリロード完了")
            except Exception as e:
                logger.warning(f"モデルプリロードに失敗: {e}")

        threading.Thread(target=_preload_worker, daemon=True).start()

    def _setup_ui_components(self) -> None:
        """UIコンポーネントを初期化する。"""
        self._overlay = DynamicIslandOverlay()
        self._settings_window = SettingsWindow()
        self._tray = SystemTray()

    def _on_audio_level(self, level: float, has_voice: bool) -> None:
        """
        音声レベルコールバック。録音中の音声レベルを受け取る。
        
        Args:
            level: 正規化された音声レベル（0.0-1.0）
            has_voice: 音声が検出されている場合True
        """
        # オーバーレイの波形に音声検出状態を伝達
        if self._is_recording and hasattr(self._overlay, 'set_voice_active'):
            self._overlay.set_voice_active(has_voice)

    def _setup_signals(self) -> None:
        """シグナルをスロットに接続する。"""
        self._tray.open_settings.connect(self._open_settings)
        self._tray.quit_app.connect(self._quit_app)
        self.status_changed.connect(self._update_ui_status)
        self.text_ready.connect(self._handle_transcription_result)

    def _setup_state(self) -> None:
        """アプリケーション状態を初期化する。"""
        self._is_recording = False
        self._is_transcribing = False
        self._active_slot: Optional[int] = None  # 現在アクティブなスロット

        # キュー関連の状態変数
        self._transcription_queue: queue.Queue = queue.Queue()
        self._queue_worker_running = False

        # ホットキースロットの初期化
        self._hotkey_slots: Dict[int, HotkeySlot] = {}
        self._setup_hotkey_slots()

        # 現在押されているキー（全スロット共通）
        self._pressed_keys: Set[str] = set()

        # スレッド制御
        self._monitoring = True

    def _setup_hotkey_slots(self) -> None:
        """両方のホットキースロットを設定する。"""
        for slot_id in [1, 2]:
            slot_config = self._config.get(f"hotkey{slot_id}", {})

            hotkey = slot_config.get("hotkey", f"<f{slot_id + 1}>")
            hotkey_mode = slot_config.get("hotkey_mode", HotkeyMode.TOGGLE.value)
            backend = slot_config.get("backend", "local")
            api_model = slot_config.get("api_model", "")
            api_prompt = slot_config.get("api_prompt", "")

            # APIモデルのデフォルト値を設定
            if not api_model and backend in ["groq", "openai"]:
                defaults = self._config.get("default_api_models", {})
                api_model = defaults.get(backend, "")

            slot = HotkeySlot(
                slot_id=slot_id,
                hotkey=hotkey,
                hotkey_mode=hotkey_mode,
                required_keys=self._parse_hotkey(hotkey),
                backend=backend,
                api_model=api_model,
                api_prompt=api_prompt,
            )

            # API Transcriberの作成（必要な場合）
            if backend != "local":
                slot.api_transcriber = self._create_api_transcriber(slot)

            self._hotkey_slots[slot_id] = slot
            logger.info(f"ホットキースロット{slot_id}: {hotkey} ({hotkey_mode}) -> {backend}")

    def _start_background_threads(self) -> None:
        """ホットキーと設定監視のバックグラウンドスレッドを開始する。"""
        # ホットキーリスナー
        self._listener_thread = threading.Thread(
            target=self._start_keyboard_listener,
            daemon=True
        )
        self._listener_thread.start()
        
        # 設定ファイル監視
        self._monitor_thread = threading.Thread(
            target=self._monitor_config,
            daemon=True
        )
        self._monitor_thread.start()

    # -------------------------------------------------------------------------
    # UIアクション
    # -------------------------------------------------------------------------

    def _open_settings(self) -> None:
        """設定ウィンドウを開く。"""
        self._settings_window.show()
        self._settings_window.activateWindow()

    def _quit_app(self) -> None:
        """アプリケーションを終了する。"""
        logger.info("終了中...")
        self._monitoring = False
        QApplication.quit()

    def _update_ui_status(self, status: str) -> None:
        """UIコンポーネントの状態を更新する。"""
        self._overlay.set_state(status)
        self._tray.set_status(status)

    def _handle_transcription_result(self, text: str) -> None:
        """
        文字起こし結果を処理する。

        Args:
            text: 文字起こしテキスト
        """
        if not text:
            logger.info("テキストが検出されませんでした。")
            return

        if text.startswith("Error:"):
            logger.error(f"文字起こし失敗: {text}")
            return

        # 開発者モード：出力を引用符で囲む
        dev_mode = self._config.get("dev_mode", False)
        if dev_mode:
            text = f'"{text}"'

        logger.info(f"結果: {text}")

        insert_start = time.perf_counter()
        self._input_handler.insert_text(text)
        insert_time = (time.perf_counter() - insert_start) * 1000

        # 開発者モード：タイミングをファイルに記録
        if dev_mode:
            self._log_timing_to_file(insert_time)

    def _log_timing_to_file(self, insert_time: float) -> None:
        """
        タイミングデータをdev_timing.logファイルに記録する。
        
        Args:
            insert_time: テキスト挿入時間（ミリ秒）
        """
        import datetime
        log_file = "dev_timing.log"
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 前回の文字起こしからタイミング情報を取得
        whisper_time = getattr(self, '_last_whisper_time', 0)
        audio_duration = getattr(self, '_last_audio_duration', 0)
        vad_time = getattr(self, '_last_vad_time', 0)
        whisper_api_time = getattr(self, '_last_whisper_api_time', 0)
        
        # 実際の合計時間を計算（Whisper + Insert）
        real_total_time = whisper_time + insert_time
        
        # 詳細なログエントリ
        log_entry = (
            f"{timestamp} | "
            f"Audio: {audio_duration:.1f}s | "
            f"VAD: {vad_time:.0f}ms | "
            f"WhisperAPI: {whisper_api_time:.0f}ms | "
            f"Insert: {insert_time:.0f}ms | "
            f"Total: {real_total_time:.0f}ms\n"
        )
        
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(log_entry)
            logger.debug(f"タイミングを {log_file} に記録しました")
        except Exception as e:
            logger.warning(f"タイミングログの書き込みに失敗: {e}")

    # -------------------------------------------------------------------------
    # 録音と文字起こし
    # -------------------------------------------------------------------------

    def start_recording(self, slot_id: Optional[int] = None) -> None:
        """
        音声録音を開始する。

        文字起こし中でも新しい録音を許可する。
        結果はキューに追加され、順番に処理される。

        Args:
            slot_id: アクティブなホットキースロットID
        """
        if self._is_recording or slot_id is None:
            return

        self._active_slot = slot_id
        slot = self._hotkey_slots[slot_id]

        logger.info(f"録音開始 (スロット {slot_id}, バックエンド: {slot.backend})")
        self._is_recording = True
        self.status_changed.emit("recording")

        # 使用するTranscriberのモデルをプリロード
        transcriber = self._get_transcriber_for_slot(slot)
        threading.Thread(target=transcriber.load_model, daemon=True).start()
        self._recorder.start()

    def stop_and_transcribe(self) -> None:
        """録音を停止して文字起こしタスクをキューに追加する。"""
        if not self._is_recording or self._active_slot is None:
            return

        logger.info("録音停止")
        self._is_recording = False

        audio_data = self._recorder.stop()

        # 音声データが空の場合
        if len(audio_data) == 0:
            # キューワーカーが動いていなければidle状態に戻す
            if not self._queue_worker_running:
                self.status_changed.emit("idle")
            return

        # 開発者モード用: 音声時間を計算
        audio_duration = len(audio_data) / 16000  # 16kHzサンプリングレート
        self._last_audio_duration = audio_duration

        # タスクをキューに追加
        task = TranscriptionTask(
            audio_data=audio_data,
            slot_id=self._active_slot,
            timestamp=time.perf_counter()
        )
        self._transcription_queue.put(task)

        # 処理中状態を表示
        self.status_changed.emit("transcribing")

        # ワーカーが動いていなければ開始
        if not self._queue_worker_running:
            self._start_queue_worker()

    def _start_queue_worker(self) -> None:
        """キュー処理ワーカースレッドを開始する。"""
        self._queue_worker_running = True
        self._is_transcribing = True
        threading.Thread(target=self._queue_processor, daemon=True).start()

    def _queue_processor(self) -> None:
        """キューからタスクを順番に処理するワーカー。"""
        try:
            while True:
                try:
                    task = self._transcription_queue.get(timeout=0.1)
                except queue.Empty:
                    break  # キューが空になったら終了

                self._process_transcription_task(task)
                self._transcription_queue.task_done()
        finally:
            self._queue_worker_running = False
            self._is_transcribing = False
            # キューが空で録音中でなければidle状態に移行
            if self._transcription_queue.empty() and not self._is_recording:
                self.status_changed.emit("idle")

    def _process_transcription_task(self, task: TranscriptionTask) -> None:
        """
        単一の文字起こしタスクを処理する。

        Args:
            task: 処理する文字起こしタスク
        """
        try:
            slot = self._hotkey_slots[task.slot_id]
            transcriber = self._get_transcriber_for_slot(slot)

            transcribe_start = time.perf_counter()
            text = transcriber.transcribe(task.audio_data)
            transcribe_time = (time.perf_counter() - transcribe_start) * 1000

            # タイミング情報を保存
            self._last_whisper_time = transcribe_time
            self._last_vad_time = getattr(transcriber, 'last_vad_time', 0)
            self._last_whisper_api_time = getattr(transcriber, 'last_api_time', 0)
            self._last_total_time = (time.perf_counter() - task.timestamp) * 1000

            self.text_ready.emit(text)
        except Exception as e:
            logger.error(f"文字起こしエラー: {e}")
            self.text_ready.emit("")

    # -------------------------------------------------------------------------
    # ホットキー処理
    # -------------------------------------------------------------------------



    def _start_keyboard_listener(self) -> None:
        """両方のホットキースロットを監視するキーボードリスナーを開始する。"""
        # いずれかのスロットがHoldモードの場合は低レベルリスナーを使用
        has_hold_mode = any(
            slot.hotkey_mode == HotkeyMode.HOLD.value
            for slot in self._hotkey_slots.values()
        )

        if has_hold_mode:
            # Hold モードがある場合は低レベルリスナーを使用
            with keyboard.Listener(
                on_press=self._handle_key_press,
                on_release=self._handle_key_release
            ) as listener:
                listener.join()
        else:
            # 両方Toggleモードの場合はGlobalHotKeysを使用
            hotkey_map = {}
            for slot_id, slot in self._hotkey_slots.items():
                hotkey_map[slot.hotkey] = lambda sid=slot_id: self._on_activate_toggle(sid)

            with keyboard.GlobalHotKeys(hotkey_map) as h:
                h.join()

    def _on_activate_toggle(self, slot_id: int) -> None:
        """
        トグルモードのアクティベーションを処理する。

        Args:
            slot_id: アクティベーションされたスロットID
        """
        if not self._is_recording:
            self.start_recording(slot_id)
        else:
            self.stop_and_transcribe()

    def _handle_key_press(self, key: Any) -> None:
        """
        キー押下イベントを処理する。

        Args:
            key: 押されたキー
        """
        try:
            key_str = self._normalize_key(key)
            if key_str:
                self._pressed_keys.add(key_str)
                # 録音中でなければ、どのスロットのホットキーかチェック
                if not self._is_recording:
                    for slot_id, slot in self._hotkey_slots.items():
                        if self._check_hotkey_match_for_slot(slot):
                            self.start_recording(slot_id)
                            break
        except Exception:
            pass

    def _handle_key_release(self, key: Any) -> None:
        """
        キー解放イベントを処理する。

        Args:
            key: 解放されたキー
        """
        try:
            key_str = self._normalize_key(key)
            if key_str and key_str in self._pressed_keys:
                self._pressed_keys.remove(key_str)
                # ホットキーに含まれるキーが離されたら録音停止
                if self._is_recording and self._active_slot is not None:
                    active_slot = self._hotkey_slots[self._active_slot]
                    if self._is_hotkey_key_released_for_slot(key_str, active_slot):
                        self.stop_and_transcribe()
        except Exception:
            pass

    def _is_hotkey_key_released_for_slot(self, key_str: str, slot: HotkeySlot) -> bool:
        """
        解放されたキーが指定スロットのホットキーの一部かチェックする。

        汎用修飾キー（ctrl, alt, shift）の場合は対応する左右キーも確認。

        Args:
            key_str: 解放されたキー文字列
            slot: チェック対象のスロット

        Returns:
            ホットキーの一部の場合True
        """
        # 直接マッチ
        if key_str in slot.required_keys:
            return True

        # 汎用修飾キーへのマッピングをチェック
        specific_to_generic = {
            'ctrl_l': 'ctrl', 'ctrl_r': 'ctrl',
            'alt_l': 'alt', 'alt_r': 'alt',
            'shift_l': 'shift', 'shift_r': 'shift',
            'cmd_l': 'cmd', 'cmd_r': 'cmd',
        }

        generic_key = specific_to_generic.get(key_str)
        if generic_key and generic_key in slot.required_keys:
            return True

        return False

    def _normalize_key(self, key: Any) -> Optional[str]:
        """
        キーを標準的な文字列表現に正規化する。
        
        左右の修飾キー（ctrl_l/r, alt_l/r, shift_l/r, cmd_l/r）を
        個別に認識しつつ、汎用設定（ctrl, alt, shift）にも対応。
        
        Args:
            key: 正規化するキー
            
        Returns:
            正規化されたキー文字列、または失敗時None
        """
        try:
            if hasattr(key, 'name'):
                name = key.name.lower()
                # alt_gr（AltGr/右Alt）をalt_rとして認識
                if name == 'alt_gr':
                    return 'alt_r'
                # 左右の修飾キーはそのまま保持（pynputの名前形式）
                # これにより <ctrl_l> のような設定が動作する
                return name
            elif hasattr(key, 'char') and key.char:
                return key.char.lower()
        except Exception:
            pass
        return None

    def _parse_hotkey(self, hotkey_str: str) -> Set[str]:
        """
        ホットキー文字列をキー名のセットにパースする。
        
        汎用設定 (ctrl, alt, shift) と左右指定 (ctrl_l, alt_r) の
        両方に対応。汎用設定の場合は左右両方を展開する。
        
        Args:
            hotkey_str: ホットキー文字列（例："<ctrl>+<space>" or "<alt_r>"）
            
        Returns:
            キー名のセット
        """
        keys = hotkey_str.replace('<', '').replace('>', '').split('+')
        result = set()
        
        for k in keys:
            k = k.strip()
            if k:
                result.add(k)
        
        return result

    def _check_hotkey_match_for_slot(self, slot: HotkeySlot) -> bool:
        """
        現在押されているキーが指定スロットのホットキー設定と一致するかチェックする。

        汎用修飾キー（ctrl, alt, shift）の場合は左右どちらでも一致、
        左右指定（ctrl_l, alt_r等）の場合は完全一致を要求。

        Args:
            slot: チェック対象のスロット

        Returns:
            ホットキーが一致した場合True
        """
        # 汎用修飾キーから具体的な左右キー名へのマッピング
        generic_to_specific = {
            'ctrl': ('ctrl_l', 'ctrl_r'),
            'alt': ('alt_l', 'alt_r'),
            'shift': ('shift_l', 'shift_r'),
            'cmd': ('cmd_l', 'cmd_r'),
        }

        for required_key in slot.required_keys:
            if required_key in generic_to_specific:
                # 汎用キー: 左右どちらかが押されていればOK
                left, right = generic_to_specific[required_key]
                if left not in self._pressed_keys and right not in self._pressed_keys:
                    return False
            else:
                # 具体的なキー（ctrl_l等）または通常キー: 完全一致
                if required_key not in self._pressed_keys:
                    return False

        return True

    # -------------------------------------------------------------------------
    # 設定監視
    # -------------------------------------------------------------------------

    def _monitor_config(self) -> None:
        """設定ファイルの変更を監視する。"""
        while self._monitoring:
            time.sleep(CONFIG_CHECK_INTERVAL_SEC)
            
            if self._config.reload_if_changed():
                self._apply_config_changes()
                logger.info("設定を再読み込みして適用しました。")

    def _apply_config_changes(self) -> None:
        """設定変更を適用する。"""
        # ホットキースロット設定を更新
        slots_changed = False
        for slot_id in [1, 2]:
            slot_config = self._config.get(f"hotkey{slot_id}", {})
            new_hotkey = slot_config.get("hotkey", f"<f{slot_id + 1}>")
            new_mode = slot_config.get("hotkey_mode", HotkeyMode.TOGGLE.value)
            new_backend = slot_config.get("backend", "local")

            current_slot = self._hotkey_slots.get(slot_id)
            if current_slot:
                if (new_hotkey != current_slot.hotkey or
                    new_mode != current_slot.hotkey_mode or
                    new_backend != current_slot.backend):
                    slots_changed = True
                    logger.info(f"ホットキースロット{slot_id}を更新: {new_hotkey} -> {new_backend}")

        # スロット設定が変更された場合は再初期化
        if slots_changed:
            self._setup_hotkey_slots()

        # ローカルTranscriber設定を更新
        self._update_local_transcriber_settings()

    def _update_local_transcriber_settings(self) -> None:
        """ローカルTranscriber設定を更新する。"""
        if self._local_transcriber is None:
            return

        local_config = self._config.get("local_backend", {})
        new_model_size = local_config.get("model_size", "base")

        # model_sizeが変更された場合、モデルをアンロード
        model_changed = new_model_size != self._local_transcriber.model_size
        if model_changed:
            logger.info(f"ローカルモデルサイズ変更: {self._local_transcriber.model_size} -> {new_model_size}")
            self._local_transcriber.model_size = new_model_size
            if self._local_transcriber.model is not None:
                self._local_transcriber.unload_model()

        # 他の設定も更新
        self._local_transcriber.compute_type = local_config.get("compute_type", "float16")
        self._local_transcriber.language = self._config.get("language", "ja")
        self._local_transcriber.release_memory_delay = local_config.get("release_memory_delay", 300)
        self._local_transcriber.vad_filter = self._config.get("vad_filter", True)
        self._local_transcriber.vad_min_silence_duration_ms = self._config.get("vad_min_silence_duration_ms", 500)
        self._local_transcriber.condition_on_previous_text = local_config.get("condition_on_previous_text", False)
        self._local_transcriber.no_speech_threshold = local_config.get("no_speech_threshold", 0.6)
        self._local_transcriber.log_prob_threshold = local_config.get("log_prob_threshold", -1.0)
        self._local_transcriber.no_speech_prob_cutoff = local_config.get("no_speech_prob_cutoff", 0.7)
        self._local_transcriber.beam_size = local_config.get("beam_size", 5)

        new_cache_dir = local_config.get("model_cache_dir", "")
        self._local_transcriber.model_cache_dir = new_cache_dir or None
