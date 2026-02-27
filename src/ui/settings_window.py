"""
設定ウィンドウモジュール

macOSシステム設定風のUIでアプリケーション設定を管理する。
ホットキーとAPI設定を提供。
ダーク/ライトテーマ切り替えに対応。
"""

from typing import Optional

from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QPointF
from PySide6.QtGui import QKeyEvent, QPainter, QPainterPath, QColor, QPen, QBrush
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..config import ConfigManager, HotkeyMode, TranscriptionBackend
from ..core.audio_recorder import AudioRecorder
from ..platform import PlatformAdapter, get_platform_adapter
from .styles import MacTheme


class ThemeToggleButton(QPushButton):
    """
    アニメーション付きテーマ切替ボタン（太陽/月アイコン）。
    
    クリックでダーク/ライトモードを切り替え、
    180度回転アニメーションで視覚的フィードバックを提供する。
    """
    
    def __init__(self, parent=None, is_dark: bool = False):
        """
        テーマ切替ボタンを初期化する。
        
        Args:
            parent: 親ウィジェット
            is_dark: ダークモードの場合True
        """
        super().__init__(parent)
        self.setFixedSize(32, 32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._is_dark = is_dark
        self._angle = 0  # 回転角度
        
        # 回転アニメーション設定
        self._anim = QPropertyAnimation(self, b"angle")
        self._anim.setDuration(500)
        self._anim.setEasingCurve(QEasingCurve.Type.OutBack)
        
        self.clicked.connect(self._animate_toggle)
        
        # カスタム描画のためデフォルトスタイルを無効化
        self.setStyleSheet("border: none; background: transparent;")

    def _animate_toggle(self):
        """テーマ切替時の回転アニメーションを実行する。"""
        self._is_dark = not self._is_dark
        
        # 180度回転
        start = self._angle
        end = start + 180
        
        self._anim.setStartValue(start)
        self._anim.setEndValue(end)
        self._anim.start()
        
        self.update()

    def get_angle(self):
        """現在の回転角度を取得する。"""
        return self._angle

    def set_angle(self, value):
        """回転角度を設定する。"""
        self._angle = value
        self.update()

    angle = property(get_angle, set_angle)

    def paintEvent(self, event):
        """太陽または月のアイコンを描画する。"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # テーマに応じた色（太陽：黄、月：白）
        color = QColor("#FFD60A") if not self._is_dark else QColor("#F2F2F7")
        
        width = self.width()
        height = self.height()
        center = QPointF(width / 2, height / 2)
        
        painter.translate(center)
        painter.rotate(self._angle)
        
        if not self._is_dark:
            # 太陽を描画
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(0, 0), 6, 6)
            
            # 光線を描画
            painter.setPen(QPen(color, 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            for i in range(8):
                painter.rotate(45)
                painter.drawLine(0, 9, 0, 11)
                
        else:
            # 月（三日月）を描画
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.PenStyle.NoPen)
            
            # 2つの円で三日月形状を作成
            path = QPainterPath()
            path.addEllipse(QPointF(0, 0), 8, 8)
            
            cutout = QPainterPath()
            cutout.addEllipse(QPointF(4, -2), 7, 7)
            
            final_path = path.subtracted(cutout)
            painter.drawPath(final_path)


class HotkeyInput(QLineEdit):
    """
    ホットキー録音用カスタムウィジェット。
    
    クリックしてキーを押すと、そのキーコンビネーションを
    pynput形式の文字列として記録する。
    
    左右のAlt/Ctrl/Shift/Winキーを区別し、
    修飾キー単独もショートカットとして登録可能。
    """
    
    # Qt Keyから基本的な修飾キー種別への変換
    MODIFIER_KEY_MAP = {
        Qt.Key.Key_Control: "ctrl",
        Qt.Key.Key_Shift: "shift",
        Qt.Key.Key_Alt: "alt",
        Qt.Key.Key_Meta: "cmd",
    }
    
    def __init__(
        self,
        parent=None,
        platform_adapter: Optional[PlatformAdapter] = None
    ):
        """ホットキー入力ウィジェットを初期化する。"""
        super().__init__(parent)
        self._platform = platform_adapter or get_platform_adapter()
        self.setReadOnly(True)
        self.setPlaceholderText("Click to record shortcut...")
        self._pressed_keys = []  # 押下中のキーを順番に追跡
        self._is_recording = False

    def focusInEvent(self, event):
        """フォーカス取得時に録音状態をリセット。"""
        super().focusInEvent(event)
        self._pressed_keys = []
        self._is_recording = True

    def focusOutEvent(self, event):
        """フォーカス喪失時に録音状態を終了。"""
        super().focusOutEvent(event)
        self._is_recording = False

    def _get_modifier_key_name(self, virtual_key: int, scan_code: int = 0) -> str:
        """
        仮想キーコードまたはスキャンコードから修飾キー名を取得する。
        
        Args:
            virtual_key: Windows仮想キーコード
            scan_code: ネイティブスキャンコード（フォールバック用）
            
        Returns:
            pynput形式のキー名、またはマッチしない場合空文字
        """
        return self._platform.modifier_hotkey_from_native(
            virtual_key=virtual_key,
            scan_code=scan_code
        )

    def keyPressEvent(self, event: QKeyEvent):
        """
        キー押下イベントを処理してホットキーを記録する。
        
        複数キーの組み合わせを追跡し、左右の修飾キーを区別する。
        新しい入力開始時は古い設定をクリアする。
        
        Args:
            event: キーイベント
        """
        key = event.key()
        virtual_key = event.nativeVirtualKey()
        scan_code = event.nativeScanCode()
        modifiers = event.modifiers()
        
        # 新しい入力開始時は古いキーをクリア
        if not self._is_recording:
            self._pressed_keys = []
            self._is_recording = True
        
        # 修飾キーの場合
        if key in self.MODIFIER_KEY_MAP:
            # 仮想キーコードまたはスキャンコードで左右を判別
            key_name = self._get_modifier_key_name(virtual_key, scan_code)
            if not key_name:
                # 仮想キーコードが不明な場合は汎用名を使用
                base_name = self.MODIFIER_KEY_MAP[key]
                key_name = f"<{base_name}>"
            
            # まだ追加されていなければ追加
            if key_name not in self._pressed_keys:
                self._pressed_keys.append(key_name)
                self._update_display()
            
            event.accept()
            return
        
        # 通常キーの場合
        key_text = self._get_key_text(key, scan_code)
        if key_text and key_text not in self._pressed_keys:
            self._pressed_keys.append(key_text)
            self._update_display()
        
        event.accept()

    def keyReleaseEvent(self, event: QKeyEvent):
        """
        キーリリースイベントを処理する。
        
        最初のキーが離された時点で組み合わせを確定する。
        """
        # キーが離されたら現在の組み合わせを確定（それ以上追加しない）
        self._is_recording = False
        event.accept()

    def _update_display(self):
        """現在押されているキーの組み合わせを表示する。"""
        if self._pressed_keys:
            self.setText("+".join(self._pressed_keys))

    def _get_key_text(self, key: int, scan_code: int = 0) -> str:
        """
        Qtキーコードをpynput形式の文字列に変換する。
        
        Args:
            key: Qtキーコード
            scan_code: ネイティブスキャンコード（左右判別用）
            
        Returns:
            pynput形式のキー文字列
        """
        return self._platform.qt_key_to_hotkey_token(key, scan_code)


class SettingsWindow(QWidget):
    """
    アプリケーション設定ウィンドウ。
    
    macOSシステム設定風のサイドバーナビゲーションUIを提供し、
    General/Advancedの2つのページで設定を管理する。
    """

    def __init__(self, platform_adapter: Optional[PlatformAdapter] = None) -> None:
        """設定ウィンドウを初期化する。"""
        super().__init__()
        self._platform = platform_adapter or get_platform_adapter()

        self._config_manager = ConfigManager()
        
        # テーマ設定を読み込み（デフォルトはライトモード）
        config = self._config_manager.config
        self._is_dark_mode = config.get("dark_mode", False)

        self._setup_window()
        self._setup_ui()
        self._load_current_settings()
        
        # 初期テーマを適用
        self._apply_theme(self._is_dark_mode)

    def _setup_window(self) -> None:
        """ウィンドウプロパティを設定する。"""
        self.setWindowTitle("Settings")
        self.resize(720, 480)

    def _setup_ui(self) -> None:
        """UIコンポーネントを設定する。"""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- サイドバー ---
        self._sidebar = QListWidget()
        self._sidebar.setFixedWidth(200)
        self._sidebar.setAttribute(Qt.WidgetAttribute.WA_MacShowFocusRect, False)
        self._sidebar.setFrameShape(QFrame.Shape.NoFrame)
        self._sidebar.currentRowChanged.connect(self._change_page)
        main_layout.addWidget(self._sidebar)

        # --- コンテンツエリア ---
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(40, 30, 40, 30)
        content_layout.setSpacing(20)

        # ヘッダー（タイトル + テーマ切替）
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)
        
        self._page_title = QLabel("General")
        self._page_title.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 5px;")
        
        # テーマ切替ボタン
        self._theme_toggle = ThemeToggleButton(is_dark=self._is_dark_mode)
        self._theme_toggle.clicked.connect(self._toggle_theme)
        
        header_layout.addWidget(self._page_title)
        header_layout.addStretch()
        header_layout.addWidget(self._theme_toggle)
        
        content_layout.addLayout(header_layout)

        # ページスタックウィジェット
        self._pages_stack = QStackedWidget()
        content_layout.addWidget(self._pages_stack)
        
        # ボタンエリア（保存/キャンセル）
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cancel_btn.clicked.connect(self.close)
        
        self._save_btn = QPushButton("Save Settings")
        self._save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._save_btn.setProperty("class", "primary")  # プライマリボタンスタイル
        self._save_btn.clicked.connect(self._save_settings)
        
        button_layout.addWidget(self._cancel_btn)
        button_layout.addWidget(self._save_btn)
        
        content_layout.addLayout(button_layout)
        
        main_layout.addWidget(content_container)

        # ページを追加
        self._setup_pages()

    def _setup_pages(self) -> None:
        """各設定ページを作成してスタックに追加する。"""
        self._add_page("General", self._create_general_page())
        self._add_page("Advanced", self._create_advanced_page())

        # 最初のページを選択
        self._sidebar.setCurrentRow(0)

    def _add_page(self, name: str, widget: QWidget) -> None:
        """
        サイドバーとスタックにページを追加する。
        
        Args:
            name: ページ名
            widget: ページウィジェット
        """
        item = QListWidgetItem(name)
        self._sidebar.addItem(item)
        self._pages_stack.addWidget(widget)

    def _change_page(self, index: int) -> None:
        """
        ページ切替を処理する。
        
        Args:
            index: 選択されたページのインデックス
        """
        self._pages_stack.setCurrentIndex(index)
        item = self._sidebar.item(index)
        if item:
            self._page_title.setText(item.text())

    def _create_general_page(self) -> QWidget:
        """Generalページを作成する（2ホットキー対応）。"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(20)

        # 2つのホットキー設定を横並びで配置
        hotkeys_layout = QHBoxLayout()
        hotkeys_layout.setSpacing(30)

        # ホットキー1
        hotkey1_group = self._create_hotkey_group(1)
        hotkeys_layout.addWidget(hotkey1_group)

        # ホットキー2
        hotkey2_group = self._create_hotkey_group(2)
        hotkeys_layout.addWidget(hotkey2_group)

        layout.addLayout(hotkeys_layout)

        # 共通設定
        common_layout = QFormLayout()
        self._lang_input = QLineEdit()
        self._lang_input.setPlaceholderText("e.g. ja, en")
        common_layout.addRow("Language (共通):", self._lang_input)
        layout.addLayout(common_layout)

        layout.addStretch()
        return page

    def _create_hotkey_group(self, slot_id: int) -> QGroupBox:
        """
        ホットキースロットのUIグループを作成する。

        Args:
            slot_id: スロットID（1または2）

        Returns:
            ホットキー設定のグループボックス
        """
        group = QGroupBox(f"Hotkey {slot_id}")
        layout = QFormLayout(group)
        layout.setSpacing(12)

        # ホットキー入力
        hotkey_input = HotkeyInput(platform_adapter=self._platform)
        setattr(self, f"_hotkey{slot_id}_input", hotkey_input)
        layout.addRow("Shortcut:", hotkey_input)

        # モード選択
        mode_combo = QComboBox()
        mode_combo.addItems([m.value for m in HotkeyMode])
        setattr(self, f"_mode{slot_id}_combo", mode_combo)
        layout.addRow("Mode:", mode_combo)

        # バックエンド選択
        backend_combo = QComboBox()
        backend_combo.addItems([
            TranscriptionBackend.GROQ.value,
            TranscriptionBackend.OPENAI.value
        ])
        backend_combo.currentTextChanged.connect(
            lambda text, sid=slot_id: self._on_slot_backend_changed(sid, text)
        )
        setattr(self, f"_backend{slot_id}_combo", backend_combo)
        layout.addRow("Backend:", backend_combo)

        # API設定（動的表示）
        api_widget = self._create_api_settings_widget(slot_id)
        setattr(self, f"_api{slot_id}_widget", api_widget)
        layout.addRow("", api_widget)

        return group

    def _create_api_settings_widget(self, slot_id: int) -> QWidget:
        """
        APIバックエンド用の設定ウィジェットを作成する。

        Args:
            slot_id: スロットID

        Returns:
            API設定ウィジェット
        """
        widget = QWidget()
        layout = QFormLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # モデル選択（Groq/OpenAI共通）
        model_combo = QComboBox()
        setattr(self, f"_api{slot_id}_model_combo", model_combo)
        layout.addRow("Model:", model_combo)

        # プロンプト入力
        prompt_input = QLineEdit()
        prompt_input.setPlaceholderText("Optional: hint text")
        setattr(self, f"_api{slot_id}_prompt_input", prompt_input)
        layout.addRow("Prompt:", prompt_input)

        widget.setVisible(False)  # 初期状態は非表示
        return widget

    def _create_advanced_page(self) -> QWidget:
        """Advancedページを作成する。"""
        page = QWidget()
        layout = QFormLayout(page)
        layout.setSpacing(15)

        # VAD設定
        self._vad_check = QCheckBox("Enable VAD")
        layout.addRow("", self._vad_check)

        # VAD最小無音時間
        self._vad_silence_spin = QSpinBox()
        self._vad_silence_spin.setRange(100, 5000)
        self._vad_silence_spin.setSingleStep(50)
        self._vad_silence_spin.setSuffix(" ms")
        layout.addRow("VAD Min Silence:", self._vad_silence_spin)

        # 入力デバイス
        self._input_device_combo = QComboBox()
        self._input_device_combo.setMinimumWidth(320)

        refresh_button = QPushButton("Refresh")
        refresh_button.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_button.clicked.connect(self._populate_input_devices)

        device_row = QWidget()
        device_row_layout = QHBoxLayout(device_row)
        device_row_layout.setContentsMargins(0, 0, 0, 0)
        device_row_layout.setSpacing(8)
        device_row_layout.addWidget(self._input_device_combo)
        device_row_layout.addWidget(refresh_button)

        layout.addRow("Input Device:", device_row)

        return page

    def _populate_input_devices(self) -> None:
        """入力デバイス一覧をコンボボックスへ読み込む。"""
        current_value = "default"
        if hasattr(self, "_input_device_combo") and self._input_device_combo.count() > 0:
            current_data = self._input_device_combo.currentData()
            if current_data is not None:
                current_value = current_data

        self._input_device_combo.clear()
        self._input_device_combo.addItem("System Default", "default")

        devices = AudioRecorder.list_input_devices()
        for device in devices:
            device_id = int(device["id"])
            label = f"{device_id}: {device['label']}"
            self._input_device_combo.addItem(label, device_id)

        self._set_input_device_selection(current_value)

    def _set_input_device_selection(self, value) -> None:
        """入力デバイス選択を設定値に合わせる。"""
        normalized = AudioRecorder.normalize_device_setting(value)
        target_value = "default" if normalized is None else normalized

        for index in range(self._input_device_combo.count()):
            if self._input_device_combo.itemData(index) == target_value:
                self._input_device_combo.setCurrentIndex(index)
                return

        self._input_device_combo.setCurrentIndex(0)

    def _load_current_settings(self) -> None:
        """設定ファイルから現在の値をUIに読み込む。"""
        config = self._config_manager.config

        # General - 共通設定
        self._lang_input.setText(config.get("language", "ja"))

        # General - ホットキー1
        hotkey1_config = config.get("hotkey1", {})
        self._hotkey1_input.setText(hotkey1_config.get("hotkey", "<f2>"))
        self._mode1_combo.setCurrentText(hotkey1_config.get("hotkey_mode", HotkeyMode.TOGGLE.value))
        backend1 = hotkey1_config.get("backend", "openai")
        if backend1 not in [TranscriptionBackend.GROQ.value, TranscriptionBackend.OPENAI.value]:
            backend1 = TranscriptionBackend.OPENAI.value
        self._backend1_combo.setCurrentText(backend1)
        self._api1_prompt_input.setText(hotkey1_config.get("api_prompt", ""))

        # General - ホットキー2
        hotkey2_config = config.get("hotkey2", {})
        self._hotkey2_input.setText(hotkey2_config.get("hotkey", "<f3>"))
        self._mode2_combo.setCurrentText(hotkey2_config.get("hotkey_mode", HotkeyMode.TOGGLE.value))
        backend2 = hotkey2_config.get("backend", "groq")
        if backend2 not in [TranscriptionBackend.GROQ.value, TranscriptionBackend.OPENAI.value]:
            backend2 = TranscriptionBackend.GROQ.value
        self._backend2_combo.setCurrentText(backend2)
        self._api2_prompt_input.setText(hotkey2_config.get("api_prompt", ""))

        # Advanced
        self._vad_check.setChecked(config.get("vad_filter", True))
        self._vad_silence_spin.setValue(config.get("vad_min_silence_duration_ms", 500))
        self._populate_input_devices()
        self._set_input_device_selection(config.get("audio_input_device", "default"))

        # APIモデルとバックエンド表示状態を初期化
        for slot_id in [1, 2]:
            backend_combo = getattr(self, f"_backend{slot_id}_combo")
            self._on_slot_backend_changed(slot_id, backend_combo.currentText())

    def _on_slot_backend_changed(self, slot_id: int, backend: str) -> None:
        """
        スロットのバックエンド選択変更を処理する。

        Args:
            slot_id: スロットID（1または2）
            backend: 選択されたバックエンド（"groq" または "openai"）
        """
        is_api = backend in [TranscriptionBackend.GROQ.value, TranscriptionBackend.OPENAI.value]

        # API設定ウィジェットの表示/非表示
        api_widget = getattr(self, f"_api{slot_id}_widget")
        api_widget.setVisible(is_api)

        # APIバックエンドの場合、モデルコンボボックスを更新
        if is_api:
            model_combo = getattr(self, f"_api{slot_id}_model_combo")
            model_combo.clear()

            if backend == TranscriptionBackend.GROQ.value:
                model_combo.addItems([
                    "whisper-large-v3-turbo",
                    "whisper-large-v3",
                    "distil-whisper-large-v3-en"
                ])
                # 設定から読み込み
                config = self._config_manager.config
                hotkey_config = config.get(f"hotkey{slot_id}", {})
                api_model = hotkey_config.get("api_model", "whisper-large-v3-turbo")
                model_combo.setCurrentText(api_model)

            elif backend == TranscriptionBackend.OPENAI.value:
                model_combo.addItems([
                    "gpt-4o-mini-transcribe",
                    "gpt-4o-transcribe"
                ])
                # 設定から読み込み
                config = self._config_manager.config
                hotkey_config = config.get(f"hotkey{slot_id}", {})
                api_model = hotkey_config.get("api_model", "gpt-4o-mini-transcribe")
                model_combo.setCurrentText(api_model)

    def _toggle_theme(self) -> None:
        """ダーク/ライトモードを切り替える。"""
        self._is_dark_mode = not self._is_dark_mode
        self._apply_theme(self._is_dark_mode)

    def _apply_theme(self, is_dark: bool) -> None:
        """
        テーマモードに基づいてグローバルスタイルシートを適用する。
        
        Args:
            is_dark: ダークモードの場合True
        """
        stylesheet = MacTheme.get_stylesheet(is_dark)
        self.setStyleSheet(stylesheet)

    def _save_settings(self) -> None:
        """設定をファイルに保存する。"""
        # 既存のdev_mode, llm_postprocess設定を保持
        existing_dev_mode = self._config_manager.get("dev_mode", False)
        existing_llm_postprocess = self._config_manager.get("llm_postprocess", {})
        selected_input_device = self._input_device_combo.currentData()
        if selected_input_device is None:
            selected_input_device = "default"

        new_config = {
            # グローバル設定
            "language": self._lang_input.text(),
            "vad_filter": self._vad_check.isChecked(),
            "vad_min_silence_duration_ms": self._vad_silence_spin.value(),
            "audio_input_device": selected_input_device,

            # ホットキー1 設定
            "hotkey1": {
                "hotkey": self._hotkey1_input.text(),
                "hotkey_mode": self._mode1_combo.currentText(),
                "backend": self._backend1_combo.currentText(),
                "api_model": self._api1_model_combo.currentText(),
                "api_prompt": self._api1_prompt_input.text(),
            },

            # ホットキー2 設定
            "hotkey2": {
                "hotkey": self._hotkey2_input.text(),
                "hotkey_mode": self._mode2_combo.currentText(),
                "backend": self._backend2_combo.currentText(),
                "api_model": self._api2_model_combo.currentText(),
                "api_prompt": self._api2_prompt_input.text(),
            },

            # APIモデルデフォルト値
            "default_api_models": self._config_manager.get("default_api_models", {
                "groq": "whisper-large-v3-turbo",
                "openai": "gpt-4o-mini-transcribe",
            }),

            # その他の設定
            "dark_mode": self._is_dark_mode,
            "dev_mode": existing_dev_mode,
            "llm_postprocess": existing_llm_postprocess,
        }

        if self._config_manager.save(new_config):
            self.close()
        else:
            QMessageBox.critical(self, "Error", "Failed to save settings.")
