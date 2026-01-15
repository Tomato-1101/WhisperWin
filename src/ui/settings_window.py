"""
設定ウィンドウモジュール

macOSシステム設定風のUIでアプリケーション設定を管理する。
ホットキー、モデル設定などを提供。
ダーク/ライトテーマ切り替えに対応。
"""

import os
import math
from typing import Optional

from PySide6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve, QRectF, QPointF
from PySide6.QtGui import QKeyEvent, QKeySequence, QPainter, QPainterPath, QColor, QPen, QBrush
from PySide6.QtWidgets import (
    QApplication,
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
    QSizePolicy,
    QSpacerItem,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..config import ComputeType, ConfigManager, HotkeyMode, ModelSize, TranscriptionBackend
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
    
    # Windows仮想キーコードで左右の修飾キーを区別
    # https://docs.microsoft.com/en-us/windows/win32/inputdev/virtual-key-codes
    VIRTUAL_KEY_MAPPING = {
        # 左側の修飾キー
        0xA2: "<ctrl_l>",   # VK_LCONTROL (162)
        0xA0: "<shift_l>",  # VK_LSHIFT (160)
        0xA4: "<alt_l>",    # VK_LMENU (164)
        0x5B: "<cmd_l>",    # VK_LWIN (91)
        # 右側の修飾キー
        0xA3: "<ctrl_r>",   # VK_RCONTROL (163)
        0xA1: "<shift_r>",  # VK_RSHIFT (161)
        0xA5: "<alt_r>",    # VK_RMENU (165)
        0x5C: "<cmd_r>",    # VK_RWIN (92)
    }
    
    # スキャンコードによるフォールバックマッピング
    # Qtが汎用VK_MENU(18)等を返す場合に使用
    SCAN_CODE_MAPPING = {
        # 左側の修飾キー
        29: "<ctrl_l>",     # Left Ctrl
        42: "<shift_l>",    # Left Shift
        56: "<alt_l>",      # Left Alt
        # 右側の修飾キー（拡張スキャンコード）
        # Qtは拡張フラグを含んだ値を返すことがある
        285: "<ctrl_r>",    # Right Ctrl (29 + 256)
        54: "<shift_r>",    # Right Shift
        312: "<alt_r>",     # Right Alt (56 + 256)
        # 特殊なスキャンコード（システム依存）
        57400: "<alt_r>",   # Right Alt (一部のキーボード/ドライバ)
        57372: "<ctrl_r>",  # Right Ctrl (一部のキーボード/ドライバ)
        57373: "<ctrl_r>",  # Right Ctrl (別のスキャンコード)
    }
    
    # Qt Keyから基本的な修飾キー種別への変換
    MODIFIER_KEY_MAP = {
        Qt.Key.Key_Control: "ctrl",
        Qt.Key.Key_Shift: "shift",
        Qt.Key.Key_Alt: "alt",
        Qt.Key.Key_Meta: "cmd",
    }
    
    def __init__(self, parent=None):
        """ホットキー入力ウィジェットを初期化する。"""
        super().__init__(parent)
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
        # まず仮想キーコードで判別
        if virtual_key in self.VIRTUAL_KEY_MAPPING:
            return self.VIRTUAL_KEY_MAPPING[virtual_key]
        
        # フォールバック: スキャンコードで判別
        if scan_code in self.SCAN_CODE_MAPPING:
            return self.SCAN_CODE_MAPPING[scan_code]
        
        return ""

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
        # 特殊キーのマッピング（ファンクションキー、ナビゲーション、Numpadなど）
        mapping = {
            # ファンクションキー F1-F24
            Qt.Key.Key_F1: "<f1>", Qt.Key.Key_F2: "<f2>", Qt.Key.Key_F3: "<f3>",
            Qt.Key.Key_F4: "<f4>", Qt.Key.Key_F5: "<f5>", Qt.Key.Key_F6: "<f6>",
            Qt.Key.Key_F7: "<f7>", Qt.Key.Key_F8: "<f8>", Qt.Key.Key_F9: "<f9>",
            Qt.Key.Key_F10: "<f10>", Qt.Key.Key_F11: "<f11>", Qt.Key.Key_F12: "<f12>",
            Qt.Key.Key_F13: "<f13>", Qt.Key.Key_F14: "<f14>", Qt.Key.Key_F15: "<f15>",
            Qt.Key.Key_F16: "<f16>", Qt.Key.Key_F17: "<f17>", Qt.Key.Key_F18: "<f18>",
            Qt.Key.Key_F19: "<f19>", Qt.Key.Key_F20: "<f20>", Qt.Key.Key_F21: "<f21>",
            Qt.Key.Key_F22: "<f22>", Qt.Key.Key_F23: "<f23>", Qt.Key.Key_F24: "<f24>",
            
            # 特殊キー
            Qt.Key.Key_Space: "<space>",
            Qt.Key.Key_Tab: "<tab>",
            Qt.Key.Key_Return: "<enter>",
            Qt.Key.Key_Enter: "<enter>",
            Qt.Key.Key_Backspace: "<backspace>",
            Qt.Key.Key_Delete: "<delete>",
            Qt.Key.Key_Escape: "<esc>",
            Qt.Key.Key_CapsLock: "<caps_lock>",
            Qt.Key.Key_NumLock: "<num_lock>",
            Qt.Key.Key_ScrollLock: "<scroll_lock>",
            Qt.Key.Key_Pause: "<pause>",
            Qt.Key.Key_Print: "<print_screen>",
            Qt.Key.Key_SysReq: "<print_screen>",
            
            # ナビゲーションキー
            Qt.Key.Key_Home: "<home>",
            Qt.Key.Key_End: "<end>",
            Qt.Key.Key_PageUp: "<page_up>",
            Qt.Key.Key_PageDown: "<page_down>",
            Qt.Key.Key_Up: "<up>",
            Qt.Key.Key_Down: "<down>",
            Qt.Key.Key_Left: "<left>",
            Qt.Key.Key_Right: "<right>",
            Qt.Key.Key_Insert: "<insert>",
            
            # テンキー
            Qt.Key.Key_division: "<num_divide>",
            Qt.Key.Key_multiply: "<num_multiply>",
            Qt.Key.Key_Minus: "<num_subtract>",
            Qt.Key.Key_Plus: "<num_add>",
            
            # メディアキー
            Qt.Key.Key_MediaPlay: "<media_play_pause>",
            Qt.Key.Key_MediaStop: "<media_stop>",
            Qt.Key.Key_MediaPrevious: "<media_previous>",
            Qt.Key.Key_MediaNext: "<media_next>",
            Qt.Key.Key_VolumeUp: "<media_volume_up>",
            Qt.Key.Key_VolumeDown: "<media_volume_down>",
            Qt.Key.Key_VolumeMute: "<media_volume_mute>",
        }
        
        if key in mapping:
            return mapping[key]
        
        # キーボードの記号キー
        text = QKeySequence(key).toString().lower()
        if not text:
            return ""
        if len(text) == 1:
            return text
        else:
            return f"<{text}>"


class SettingsWindow(QWidget):
    """
    アプリケーション設定ウィンドウ。
    
    macOSシステム設定風のサイドバーナビゲーションUIを提供し、
    General/Model/Advancedの3つのページで設定を管理する。
    """

    def __init__(self) -> None:
        """設定ウィンドウを初期化する。"""
        super().__init__()

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
        self._add_page("Model", self._create_model_page())
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
        """Generalページを作成する。"""
        page = QWidget()
        layout = QFormLayout(page)
        layout.setSpacing(15)
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # ホットキー入力
        self._hotkey_input = HotkeyInput()
        layout.addRow("Global Hotkey:", self._hotkey_input)

        # ホットキーモード
        self._mode_combo = QComboBox()
        self._mode_combo.addItems([m.value for m in HotkeyMode])
        layout.addRow("Trigger Mode:", self._mode_combo)
        
        # 言語
        self._lang_input = QLineEdit()
        self._lang_input.setPlaceholderText("e.g. ja, en")
        layout.addRow("Language:", self._lang_input)

        return page

    def _create_model_page(self) -> QWidget:
        """Modelページを作成する。"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(20)
        
        # バックエンド選択
        backend_layout = QFormLayout()
        self._backend_combo = QComboBox()
        self._backend_combo.addItems([
            TranscriptionBackend.LOCAL.value,
            TranscriptionBackend.GROQ.value,
            TranscriptionBackend.OPENAI.value
        ])
        self._backend_combo.currentTextChanged.connect(self._on_backend_changed)
        backend_layout.addRow("Transcription Engine:", self._backend_combo)
        layout.addLayout(backend_layout)

        # ローカル設定グループ
        self._local_group = QGroupBox("Local Engine Settings (GPU)")
        local_layout = QFormLayout()

        self._model_combo = QComboBox()
        self._model_combo.addItems([m.value for m in ModelSize])
        local_layout.addRow("Model Size:", self._model_combo)

        self._compute_combo = QComboBox()
        self._compute_combo.addItems([c.value for c in ComputeType])
        local_layout.addRow("Compute Type:", self._compute_combo)

        self._local_group.setLayout(local_layout)
        layout.addWidget(self._local_group)

        # Groq設定グループ
        self._groq_group = QGroupBox("Groq API Settings (Cloud)")
        groq_layout = QFormLayout()

        self._api_key_status_label = QLabel()
        groq_layout.addRow("API Key Status:", self._api_key_status_label)

        self._groq_model_combo = QComboBox()
        self._groq_model_combo.addItems([
            "whisper-large-v3-turbo",
            "whisper-large-v3",
            "distil-whisper-large-v3-en"
        ])
        groq_layout.addRow("Cloud Model:", self._groq_model_combo)

        self._groq_prompt_input = QLineEdit()
        self._groq_prompt_input.setPlaceholderText("Optional: transcription hint text")
        groq_layout.addRow("Prompt:", self._groq_prompt_input)

        self._groq_group.setLayout(groq_layout)
        layout.addWidget(self._groq_group)

        # OpenAI設定グループ
        self._openai_group = QGroupBox("OpenAI API Settings (Cloud)")
        openai_layout = QFormLayout()

        self._openai_api_key_status_label = QLabel()
        openai_layout.addRow("API Key Status:", self._openai_api_key_status_label)

        self._openai_model_combo = QComboBox()
        self._openai_model_combo.addItems([
            "gpt-4o-mini-transcribe",
            "gpt-4o-transcribe"
        ])
        openai_layout.addRow("Cloud Model:", self._openai_model_combo)

        self._openai_prompt_input = QLineEdit()
        self._openai_prompt_input.setPlaceholderText("Optional: transcription hint text")
        openai_layout.addRow("Prompt:", self._openai_prompt_input)

        self._openai_group.setLayout(openai_layout)
        layout.addWidget(self._openai_group)

        layout.addStretch()
        return page

    def _create_advanced_page(self) -> QWidget:
        """Advancedページを作成する。"""
        page = QWidget()
        layout = QFormLayout(page)
        layout.setSpacing(15)

        # VAD設定
        self._vad_check = QCheckBox("Enable VAD")
        layout.addRow("", self._vad_check)

        # メモリ解放遅延
        self._memory_spin = QSpinBox()
        self._memory_spin.setRange(0, 3600)
        self._memory_spin.setSuffix(" sec")
        layout.addRow("Release Memory Delay:", self._memory_spin)

        return page

    def _load_current_settings(self) -> None:
        """設定ファイルから現在の値をUIに読み込む。"""
        config = self._config_manager.config
        
        # General
        self._hotkey_input.setText(config.get("hotkey", "<f2>"))
        self._mode_combo.setCurrentText(config.get("hotkey_mode", HotkeyMode.TOGGLE.value))
        self._lang_input.setText(config.get("language", "ja"))
        
        # Model
        self._backend_combo.setCurrentText(config.get("transcription_backend", "local"))
        self._model_combo.setCurrentText(config.get("model_size", ModelSize.BASE.value))
        self._compute_combo.setCurrentText(config.get("compute_type", ComputeType.FLOAT16.value))
        self._groq_model_combo.setCurrentText(config.get("groq_model", "whisper-large-v3-turbo"))
        self._groq_prompt_input.setText(config.get("groq_prompt", ""))
        self._openai_model_combo.setCurrentText(config.get("openai_model", "gpt-4o-mini-transcribe"))
        self._openai_prompt_input.setText(config.get("openai_prompt", ""))

        # Groq APIキーステータス
        has_groq_key = bool(os.environ.get("GROQ_API_KEY"))
        groq_status_text = "✓ Ready" if has_groq_key else "✗ Not Set (Check Environment)"
        groq_status_color = "green" if has_groq_key else "red"
        self._api_key_status_label.setText(groq_status_text)
        self._api_key_status_label.setStyleSheet(f"color: {groq_status_color}; font-weight: bold;")

        # OpenAI APIキーステータス
        has_openai_key = bool(os.environ.get("OPENAI_API_KEY"))
        openai_status_text = "✓ Ready" if has_openai_key else "✗ Not Set (Check Environment)"
        openai_status_color = "green" if has_openai_key else "red"
        self._openai_api_key_status_label.setText(openai_status_text)
        self._openai_api_key_status_label.setStyleSheet(f"color: {openai_status_color}; font-weight: bold;")
        
        # Advanced
        self._vad_check.setChecked(config.get("vad_filter", True))
        self._memory_spin.setValue(config.get("release_memory_delay", 300))

        # 表示状態を初期化
        self._on_backend_changed(self._backend_combo.currentText())

    def _on_backend_changed(self, backend: str) -> None:
        """
        バックエンド選択変更を処理する。

        Args:
            backend: 選択されたバックエンド（"local", "groq", または "openai"）
        """
        is_local = (backend == TranscriptionBackend.LOCAL.value)
        is_groq = (backend == TranscriptionBackend.GROQ.value)
        is_openai = (backend == TranscriptionBackend.OPENAI.value)

        self._local_group.setVisible(is_local)
        self._groq_group.setVisible(is_groq)
        self._openai_group.setVisible(is_openai)

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
        """設定をファイルに保存する。既存の設定（dev_mode等）を保持。"""
        # 既存のdev_mode設定を保持
        existing_dev_mode = self._config_manager.get("dev_mode", False)
        
        new_config = {
            "hotkey": self._hotkey_input.text(),
            "hotkey_mode": self._mode_combo.currentText(),
            "language": self._lang_input.text(),
            "transcription_backend": self._backend_combo.currentText(),
            "model_size": self._model_combo.currentText(),
            "compute_type": self._compute_combo.currentText(),
            "groq_model": self._groq_model_combo.currentText(),
            "groq_prompt": self._groq_prompt_input.text(),
            "openai_model": self._openai_model_combo.currentText(),
            "openai_prompt": self._openai_prompt_input.text(),
            "vad_filter": self._vad_check.isChecked(),
            "release_memory_delay": self._memory_spin.value(),
            "dark_mode": self._is_dark_mode,

            # 既存の設定を保持
            "dev_mode": existing_dev_mode,
        }

        if self._config_manager.save(new_config):
            self.close()
        else:
            QMessageBox.critical(self, "Error", "Failed to save settings.")
