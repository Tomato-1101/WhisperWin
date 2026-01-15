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
        hotkey_input = HotkeyInput()
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
            TranscriptionBackend.LOCAL.value,
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

    def _create_model_page(self) -> QWidget:
        """Modelページを作成する（ローカルバックエンド共通設定）。"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(20)

        # 説明ラベル
        desc = QLabel("ローカルGPU設定は両方のホットキーで共通です。\nAPI設定は各ホットキーの「General」ページで設定します。")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # ローカル設定グループ
        local_group = QGroupBox("Local Engine Settings (GPU - 共通)")
        local_layout = QFormLayout()

        self._model_combo = QComboBox()
        self._model_combo.addItems([m.value for m in ModelSize])
        local_layout.addRow("Model Size:", self._model_combo)

        self._compute_combo = QComboBox()
        self._compute_combo.addItems([c.value for c in ComputeType])
        local_layout.addRow("Compute Type:", self._compute_combo)

        local_group.setLayout(local_layout)
        layout.addWidget(local_group)

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

        # General - 共通設定
        self._lang_input.setText(config.get("language", "ja"))

        # General - ホットキー1
        hotkey1_config = config.get("hotkey1", {})
        self._hotkey1_input.setText(hotkey1_config.get("hotkey", "<f2>"))
        self._mode1_combo.setCurrentText(hotkey1_config.get("hotkey_mode", HotkeyMode.TOGGLE.value))
        self._backend1_combo.setCurrentText(hotkey1_config.get("backend", "local"))
        self._api1_prompt_input.setText(hotkey1_config.get("api_prompt", ""))

        # General - ホットキー2
        hotkey2_config = config.get("hotkey2", {})
        self._hotkey2_input.setText(hotkey2_config.get("hotkey", "<f3>"))
        self._mode2_combo.setCurrentText(hotkey2_config.get("hotkey_mode", HotkeyMode.TOGGLE.value))
        self._backend2_combo.setCurrentText(hotkey2_config.get("backend", "local"))
        self._api2_prompt_input.setText(hotkey2_config.get("api_prompt", ""))

        # Model - ローカル共通設定
        local_config = config.get("local_backend", {})
        self._model_combo.setCurrentText(local_config.get("model_size", ModelSize.BASE.value))
        self._compute_combo.setCurrentText(local_config.get("compute_type", ComputeType.FLOAT16.value))

        # Advanced
        self._vad_check.setChecked(config.get("vad_filter", True))
        self._memory_spin.setValue(local_config.get("release_memory_delay", 300))

        # APIモデルとバックエンド表示状態を初期化
        for slot_id in [1, 2]:
            backend_combo = getattr(self, f"_backend{slot_id}_combo")
            self._on_slot_backend_changed(slot_id, backend_combo.currentText())

    def _on_slot_backend_changed(self, slot_id: int, backend: str) -> None:
        """
        スロットのバックエンド選択変更を処理する。

        Args:
            slot_id: スロットID（1または2）
            backend: 選択されたバックエンド（"local", "groq", または "openai"）
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

        new_config = {
            # グローバル設定
            "language": self._lang_input.text(),
            "vad_filter": self._vad_check.isChecked(),
            "vad_min_silence_duration_ms": self._config_manager.get("vad_min_silence_duration_ms", 500),

            # ローカルバックエンド設定（共通）
            "local_backend": {
                "model_size": self._model_combo.currentText(),
                "compute_type": self._compute_combo.currentText(),
                "release_memory_delay": self._memory_spin.value(),
                "condition_on_previous_text": self._config_manager.get("local_backend", {}).get("condition_on_previous_text", False),
                "no_speech_threshold": self._config_manager.get("local_backend", {}).get("no_speech_threshold", 0.6),
                "log_prob_threshold": self._config_manager.get("local_backend", {}).get("log_prob_threshold", -1.0),
                "no_speech_prob_cutoff": self._config_manager.get("local_backend", {}).get("no_speech_prob_cutoff", 0.7),
                "beam_size": self._config_manager.get("local_backend", {}).get("beam_size", 5),
                "model_cache_dir": self._config_manager.get("local_backend", {}).get("model_cache_dir", ""),
            },

            # ホットキー1 設定
            "hotkey1": {
                "hotkey": self._hotkey1_input.text(),
                "hotkey_mode": self._mode1_combo.currentText(),
                "backend": self._backend1_combo.currentText(),
                "api_model": self._api1_model_combo.currentText() if self._backend1_combo.currentText() != "local" else "",
                "api_prompt": self._api1_prompt_input.text(),
            },

            # ホットキー2 設定
            "hotkey2": {
                "hotkey": self._hotkey2_input.text(),
                "hotkey_mode": self._mode2_combo.currentText(),
                "backend": self._backend2_combo.currentText(),
                "api_model": self._api2_model_combo.currentText() if self._backend2_combo.currentText() != "local" else "",
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
