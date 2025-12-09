"""
メインアプリケーションコントローラーモジュール

音声録音、文字起こし、UI、ホットキー処理など、
すべてのコンポーネントを統合するメインコントローラー。
"""

import threading
import time
from typing import Any, Optional, Set

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QApplication
from pynput import keyboard

from .config import ConfigManager, HotkeyMode, TranscriptionBackend
from .config.constants import CONFIG_CHECK_INTERVAL_SEC
from .core import AudioRecorder, GroqTranscriber, InputHandler, TextProcessor, Transcriber
from .ui import DynamicIslandOverlay, SettingsWindow, SystemTray
from .utils.logger import get_logger

logger = get_logger(__name__)


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

        # バックエンド設定に基づいてTranscriberを初期化
        backend_type = self._config.get("transcription_backend", "local")
        self._transcriber = self._create_transcriber(backend_type)

        self._input_handler = InputHandler()

        # LLM後処理の初期化
        self._setup_text_processor()
        
        # VADモデルをバックグラウンドでプリロード（初回入力時の遅延を防ぐ）
        self._preload_vad_model()

    def _create_transcriber(self, backend_type: str):
        """
        バックエンドタイプに応じたTranscriberを作成する。
        
        Args:
            backend_type: "local" または "groq"
        
        Returns:
            TranscriberまたはGroqTranscriberのインスタンス
        """
        if backend_type == TranscriptionBackend.GROQ.value:
            transcriber = GroqTranscriber(
                model=self._config.get("groq_model", "whisper-large-v3-turbo"),
                language=self._config.get("language", "ja"),
                vad_filter=self._config.get("vad_filter", True),
                vad_min_silence_duration_ms=self._config.get("vad_min_silence_duration_ms", 500),
            )

            if not transcriber.is_available():
                logger.warning(
                    "Groq APIが利用できません（SDKが未インストールまたはGROQ_API_KEYが未設定）。 "
                    "ローカルGPU文字起こしにフォールバックします。"
                )
                self._show_backend_warning("groq_unavailable")
                return self._create_local_transcriber()

            logger.info(f"Groq APIバックエンドを使用: モデル={transcriber.model}")
            return transcriber
        else:
            return self._create_local_transcriber()

    def _create_local_transcriber(self) -> Transcriber:
        """ローカルGPU Transcriberを作成する。"""
        logger.info("ローカルGPUバックエンド（faster-whisper）を使用")
        return Transcriber(
            model_size=self._config.get("model_size"),
            compute_type=self._config.get("compute_type", "float16"),
            language=self._config.get("language"),
            release_memory_delay=self._config.get("release_memory_delay", 300),
            vad_filter=self._config.get("vad_filter", True),
            vad_min_silence_duration_ms=self._config.get("vad_min_silence_duration_ms", 500),
            condition_on_previous_text=self._config.get("condition_on_previous_text", False),
            no_speech_threshold=self._config.get("no_speech_threshold", 0.6),
            log_prob_threshold=self._config.get("log_prob_threshold", -1.0),
            no_speech_prob_cutoff=self._config.get("no_speech_prob_cutoff", 0.7),
            beam_size=self._config.get("beam_size", 5),
            model_cache_dir=self._config.get("model_cache_dir", ""),
        )

    def _show_backend_warning(self, warning_type: str) -> None:
        """
        バックエンド問題についてユーザーに警告を表示する。
        
        Args:
            warning_type: 警告タイプ（"groq_unavailable"等）
        """
        if warning_type == "groq_unavailable":
            self._overlay.show_temporary_message(
                "Groq API unavailable\nUsing local GPU",
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
                if isinstance(self._transcriber, GroqTranscriber):
                    # Groqモードの場合
                    self._transcriber.preload_vad()
                elif hasattr(self._transcriber, 'vad_filter') and self._transcriber.vad_filter:
                    # ローカルモードでVADが有効な場合
                    # ローカルTranscriberのVADはfaster-whisper内部で処理されるため
                    # 別途プリロードは不要
                    pass
                logger.debug("VADプリロード完了")
            except Exception as e:
                logger.warning(f"VADプリロードに失敗しました: {e}")
        
        # バックグラウンドスレッドでプリロード
        threading.Thread(target=_preload_worker, daemon=True).start()

    def _setup_text_processor(self) -> None:
        """LLMテキスト後処理を初期化する。"""
        llm_config = self._config.get("llm_postprocess", {})
        self._text_processor_enabled = llm_config.get("enabled", False)

        if self._text_processor_enabled:
            self._text_processor = TextProcessor(
                provider=llm_config.get("provider", "groq"),
                model=llm_config.get("model", "llama-3.3-70b-versatile"),
                system_prompt=llm_config.get("system_prompt", ""),
                timeout=llm_config.get("timeout", 5.0),
                fallback_on_error=llm_config.get("fallback_on_error", True),
            )

            if not self._text_processor.is_available():
                logger.warning(
                    f"LLMプロバイダー {llm_config.get('provider')} が利用できません。 "
                    "後処理を無効化します。"
                )
                self._text_processor_enabled = False
                self._text_processor = None
            else:
                logger.info(
                    f"LLM後処理を有効化: {llm_config.get('provider')} / "
                    f"{llm_config.get('model')}"
                )
        else:
            self._text_processor = None

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
        self._cancel_transcription = False
        
        # ホットキー設定
        self._hotkey = self._config.get("hotkey", "<f2>")
        self._hotkey_mode = self._config.get("hotkey_mode", HotkeyMode.TOGGLE.value)
        self._pressed_keys: Set[str] = set()
        self._required_keys: Set[str] = self._parse_hotkey(self._hotkey)
        
        # スレッド制御
        self._monitoring = True

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
            # idle状態に移行してオーバーレイを消す
            self.status_changed.emit("idle")
            return

        if text.startswith("Error:"):
            logger.error(f"文字起こし失敗: {text}")
            # idle状態に移行してオーバーレイを消す
            self.status_changed.emit("idle")
            return

        llm_time = 0
        llm_api_time = 0
        # LLM後処理
        if self._text_processor_enabled and self._text_processor:
            raw_text = text  # 処理前のテキストを保存
            logger.info(f"[LLM処理前] {raw_text}")
            llm_start = time.perf_counter()
            text = self._text_processor.process(text)
            llm_time = (time.perf_counter() - llm_start) * 1000
            llm_api_time = getattr(self._text_processor, 'last_api_time', 0)
            logger.info(f"[LLM処理後] {text}")

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
            self._log_timing_to_file(llm_time, llm_api_time, insert_time)

        # 即座にアイドル状態に戻る（オーバーレイを消す）
        self.status_changed.emit("idle")

    def _log_timing_to_file(self, llm_time: float, llm_api_time: float, insert_time: float) -> None:
        """
        タイミングデータをdev_timing.logファイルに記録する。
        
        Args:
            llm_time: LLM処理時間（ミリ秒）
            llm_api_time: LLM API呼び出し時間（ミリ秒）
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
        
        # 実際の合計時間を計算（Whisper + LLM + Insert）
        real_total_time = whisper_time + llm_time + insert_time
        
        # LLMプロバイダーとモデル情報を取得
        llm_config = self._config.get("llm_postprocess", {})
        llm_provider = llm_config.get("provider", "none")
        llm_model = llm_config.get("model", "none")
        llm_enabled = llm_config.get("enabled", False)
        
        # 詳細なログエントリ
        log_entry = (
            f"{timestamp} | "
            f"Audio: {audio_duration:.1f}s | "
            f"VAD: {vad_time:.0f}ms | "
            f"WhisperAPI: {whisper_api_time:.0f}ms | "
            f"LLMAPI: {llm_api_time:.0f}ms ({llm_provider}/{llm_model}) | "
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

    def start_recording(self) -> None:
        """音声録音を開始する。"""
        if self._is_recording:
            return
        
        # 進行中の文字起こしをキャンセル
        if self._is_transcribing:
            logger.info("新しい録音開始 - 現在の文字起こしをキャンセル")
            self._cancel_transcription = True
        
        logger.info("録音開始")
        self._is_recording = True
        self.status_changed.emit("recording")
        
        # バックグラウンドでモデルをプリロード
        threading.Thread(target=self._transcriber.load_model, daemon=True).start()
        self._recorder.start()

    def stop_and_transcribe(self) -> None:
        """録音を停止して文字起こしを開始する。処理中はオーバーレイを表示。"""
        if not self._is_recording:
            return
        
        stop_start = time.perf_counter()
        logger.info("録音停止")
        self._is_recording = False
        self._is_transcribing = True
        self._cancel_transcription = False
        
        # 処理中状態を表示（キーを離してもオーバーレイは表示続行）
        self.status_changed.emit("transcribing")
        
        audio_data = self._recorder.stop()
        audio_stop_time = (time.perf_counter() - stop_start) * 1000
        audio_duration = len(audio_data) / 16000  # 16kHzサンプリングレート
        
        # 開発者モード用に保存
        self._last_audio_duration = audio_duration
        
        # バックグラウンドで文字起こしを実行
        threading.Thread(
            target=self._transcribe_worker,
            args=(audio_data, time.perf_counter()),
            daemon=True
        ).start()

    def _transcribe_worker(self, audio_data, start_time: float = None) -> None:
        """
        文字起こしワーカースレッド。
        
        Args:
            audio_data: 音声データ
            start_time: 開始時刻（タイミング計測用）
        """
        try:
            if len(audio_data) == 0:
                self.text_ready.emit("")
                return

            # 開始前にキャンセルをチェック
            if self._cancel_transcription:
                logger.info("処理前に文字起こしがキャンセルされました")
                return

            transcribe_start = time.perf_counter()
            text = self._transcriber.transcribe(audio_data)
            transcribe_time = (time.perf_counter() - transcribe_start) * 1000
            
            # 開発者モード用に保存
            self._last_whisper_time = transcribe_time
            
            # Transcriberから詳細なタイミング情報を取得（利用可能な場合）
            self._last_vad_time = getattr(self._transcriber, 'last_vad_time', 0)
            self._last_whisper_api_time = getattr(self._transcriber, 'last_api_time', 0)
            
            # 処理後にキャンセルをチェック
            if self._cancel_transcription:
                logger.info("文字起こしがキャンセルされました - 結果を破棄")
                return
            
            if start_time:
                total_time = (time.perf_counter() - start_time) * 1000
                # 開発者モード用に保存
                self._last_total_time = total_time
            
            self.text_ready.emit(text)
        finally:
            self._is_transcribing = False

    # -------------------------------------------------------------------------
    # ホットキー処理
    # -------------------------------------------------------------------------



    def _start_keyboard_listener(self) -> None:
        """ホットキーモードに基づいてキーボードリスナーを開始する。"""
        if self._hotkey_mode == HotkeyMode.HOLD.value:
            with keyboard.Listener(
                on_press=self._handle_key_press,
                on_release=self._handle_key_release
            ) as listener:
                listener.join()
        else:
            hotkey_map = {self._hotkey: self._on_activate_toggle}
            with keyboard.GlobalHotKeys(hotkey_map) as h:
                h.join()

    def _on_activate_toggle(self) -> None:
        """トグルモードのアクティベーションを処理する。"""
        if not self._is_recording:
            self.start_recording()
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
                # 新しいマッチングロジック：汎用/左右指定の両方に対応
                if self._check_hotkey_match() and not self._is_recording:
                    self.start_recording()
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
                if self._is_recording and self._is_hotkey_key_released(key_str):
                    self.stop_and_transcribe()
        except Exception:
            pass

    def _is_hotkey_key_released(self, key_str: str) -> bool:
        """
        解放されたキーがホットキーの一部かチェックする。
        
        汎用修飾キー（ctrl, alt, shift）の場合は対応する左右キーも確認。
        
        Args:
            key_str: 解放されたキー文字列
            
        Returns:
            ホットキーの一部の場合True
        """
        # 直接マッチ
        if key_str in self._required_keys:
            return True
        
        # 汎用修飾キーへのマッピングをチェック
        specific_to_generic = {
            'ctrl_l': 'ctrl', 'ctrl_r': 'ctrl',
            'alt_l': 'alt', 'alt_r': 'alt',
            'shift_l': 'shift', 'shift_r': 'shift',
            'cmd_l': 'cmd', 'cmd_r': 'cmd',
        }
        
        generic_key = specific_to_generic.get(key_str)
        if generic_key and generic_key in self._required_keys:
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

    def _check_hotkey_match(self) -> bool:
        """
        現在押されているキーがホットキー設定と一致するかチェックする。
        
        汎用修飾キー（ctrl, alt, shift）の場合は左右どちらでも一致、
        左右指定（ctrl_l, alt_r等）の場合は完全一致を要求。
        
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
        
        for required_key in self._required_keys:
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
        # ホットキー設定を更新
        new_hotkey = self._config.get("hotkey", "<f2>")
        new_mode = self._config.get("hotkey_mode", HotkeyMode.TOGGLE.value)
        
        if new_hotkey != self._hotkey or new_mode != self._hotkey_mode:
            self._hotkey = new_hotkey
            self._hotkey_mode = new_mode
            self._required_keys = self._parse_hotkey(self._hotkey)
            logger.info(f"ホットキーを更新: {self._hotkey}")
        
        # Transcriber設定を更新
        self._update_transcriber_settings()

        # LLM後処理設定を更新
        self._setup_text_processor()

    def _update_transcriber_settings(self) -> None:
        """設定からTranscriber設定を更新する。"""
        new_backend = self._config.get("transcription_backend", "local")
        current_backend = "groq" if isinstance(self._transcriber, GroqTranscriber) else "local"

        # バックエンドが変更された場合 - Transcriberを再作成
        if new_backend != current_backend:
            logger.info(f"文字起こしバックエンドを切り替え: {current_backend} -> {new_backend}")

            # 古いTranscriberをアンロード
            if hasattr(self._transcriber, 'unload_model'):
                self._transcriber.unload_model()

            # 新しいTranscriberを作成
            self._transcriber = self._create_transcriber(new_backend)
            return

        # 同じバックエンド - 設定を更新
        if current_backend == "local":
            self._update_local_transcriber_settings()
        else:
            self._update_groq_transcriber_settings()

    def _update_local_transcriber_settings(self) -> None:
        """ローカルTranscriber設定を更新する。"""
        if not isinstance(self._transcriber, Transcriber):
            return

        new_model_size = self._config.get("model_size")
        model_changed = new_model_size != self._transcriber.model_size

        # 設定を更新
        self._transcriber.model_size = new_model_size
        self._transcriber.compute_type = self._config.get("compute_type", "float16")
        self._transcriber.language = self._config.get("language")
        self._transcriber.release_memory_delay = self._config.get("release_memory_delay", 300)
        self._transcriber.vad_filter = self._config.get("vad_filter", True)
        self._transcriber.vad_min_silence_duration_ms = self._config.get("vad_min_silence_duration_ms", 500)
        self._transcriber.condition_on_previous_text = self._config.get("condition_on_previous_text", False)
        self._transcriber.no_speech_threshold = self._config.get("no_speech_threshold", 0.6)
        self._transcriber.log_prob_threshold = self._config.get("log_prob_threshold", -1.0)
        self._transcriber.no_speech_prob_cutoff = self._config.get("no_speech_prob_cutoff", 0.7)
        self._transcriber.beam_size = self._config.get("beam_size", 5)

        new_cache_dir = self._config.get("model_cache_dir", "")
        self._transcriber.model_cache_dir = new_cache_dir or None

        # 設定が変更された場合はモデルをアンロード
        if model_changed:
            if self._transcriber.model is not None:
                logger.info("モデル設定が変更されました。再読み込みのためアンロードします...")
                self._transcriber.unload_model()

    def _update_groq_transcriber_settings(self) -> None:
        """Groq Transcriber設定を更新する。"""
        if not isinstance(self._transcriber, GroqTranscriber):
            return

        # Groq設定を更新
        self._transcriber.model = self._config.get("groq_model", "whisper-large-v3-turbo")
        self._transcriber.language = self._config.get("language", "ja")
        
        # VAD設定を更新
        vad_filter_enabled = self._config.get("vad_filter", True)
        vad_min_silence = self._config.get("vad_min_silence_duration_ms", 500)
        
        # VAD設定が変更されたかチェック
        if vad_filter_enabled != self._transcriber.vad_enabled:
            self._transcriber.vad_enabled = vad_filter_enabled
            if vad_filter_enabled and self._transcriber._vad_filter is None:
                from .core.vad import VadFilter
                self._transcriber._vad_filter = VadFilter(
                    min_silence_duration_ms=vad_min_silence,
                    use_cuda=True
                )
            elif not vad_filter_enabled:
                self._transcriber._vad_filter = None
        
        logger.debug(f"Groq設定を更新: model={self._transcriber.model}, vad={vad_filter_enabled}")
