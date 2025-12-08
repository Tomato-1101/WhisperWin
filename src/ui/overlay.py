"""
Dynamic Islandオーバーレイモジュール

画面上部にmacOS Dynamic Island風の状態表示UIを提供する。
録音中・処理中などのアプリケーション状態を視覚的に表示し、
波形アニメーションで音声入力を可視化する。
"""

import math
import random
from typing import List, Union

from PySide6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    QRect,
    QRectF,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import (
    QBrush,
    QColor,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QVBoxLayout, QWidget

from ..config.constants import (
    ANIMATION_DURATION_MS,
    OVERLAY_BASE_HEIGHT,
    OVERLAY_BASE_WIDTH,
    OVERLAY_EXPANDED_HEIGHT,
    OVERLAY_EXPANDED_WIDTH,
    OVERLAY_TOP_MARGIN,
)
from ..config.types import AppState
from .styles import MacTheme


class WaveformWidget(QWidget):
    """
    音声波形アニメーションウィジェット。
    
    録音中に動的な波形アニメーションを表示し、
    ユーザーに音声入力を視覚的にフィードバックする。
    """

    def __init__(self, parent=None):
        """波形ウィジェットを初期化する。"""
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setFixedHeight(20)
        
        # 波形バーの設定
        self._bars_count = 12  # バーの数
        self._amplitudes = [0.1] * self._bars_count  # 現在の振幅
        self._target_amplitudes = [0.1] * self._bars_count  # 目標振幅
        self._phase = 0.0  # アニメーション位相
        
        # アニメーションタイマー（約60FPS）
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_wave)
        self._timer.setInterval(16)
        
        self._is_active = False

    def start_animation(self):
        """波形アニメーションを開始する。"""
        self._is_active = True
        self._timer.start()
        self.show()

    def stop_animation(self):
        """波形アニメーションを停止する。"""
        self._is_active = False
        self._timer.stop()
        self.hide()

    def _update_wave(self):
        """波形の物理演算を更新する。"""
        self._phase += 0.2
        
        # 目標振幅に滑らかに補間
        for i in range(self._bars_count):
            # ランダムに新しい目標振幅を生成
            if random.random() < 0.1:
                self._target_amplitudes[i] = random.uniform(0.2, 1.0)
            
            # 補間
            diff = self._target_amplitudes[i] - self._amplitudes[i]
            self._amplitudes[i] += diff * 0.15

        self.update()

    def paintEvent(self, event):
        """波形を描画する。"""
        if not self._is_active:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        width = self.width()
        height = self.height()
        bar_width = 3    # バーの幅
        spacing = 4      # バー間隔
        total_width = (bar_width + spacing) * self._bars_count
        start_x = (width - total_width) / 2
        
        # バーを描画
        painter.setPen(Qt.PenStyle.NoPen)
        
        for i in range(self._bars_count):
            amp = self._amplitudes[i]
            
            # サイン波で「呼吸」するようなエフェクト
            sine_mod = (math.sin(self._phase + i * 0.5) + 1) * 0.5
            current_height = height * amp * (0.5 + 0.5 * sine_mod)
            current_height = max(4, current_height)  # 最小高さ
            
            x = start_x + i * (bar_width + spacing)
            y = (height - current_height) / 2
            
            # アクセントカラーで描画
            color = QColor(MacTheme.Colors(False).ACCENT)
            painter.setBrush(QBrush(color))
            
            painter.drawRoundedRect(QRectF(x, y, bar_width, current_height), bar_width/2, bar_width/2)


class DynamicIslandOverlay(QMainWindow):
    """
    Dynamic Island風オーバーレイウィンドウ。
    
    画面上部中央にフレームレスで表示され、
    アプリケーション状態を視覚的にフィードバックする。
    
    Attributes:
        _state: 現在の表示状態
    """
    
    def __init__(self) -> None:
        """オーバーレイウィンドウを初期化する。"""
        super().__init__()
        
        self._setup_window()
        self._setup_ui()
        self._setup_animations()
        
        self._state = AppState.IDLE
        self.set_state(AppState.IDLE)

    def _setup_window(self) -> None:
        """ウィンドウプロパティを設定する。"""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |      # フレームなし
            Qt.WindowType.WindowStaysOnTopHint |     # 常に最前面
            Qt.WindowType.Tool                        # タスクバー非表示
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # 初期位置（画面中央上部）
        screen = QApplication.primaryScreen().geometry()
        x_pos = (screen.width() - OVERLAY_BASE_WIDTH) // 2
        self.setGeometry(x_pos, OVERLAY_TOP_MARGIN, OVERLAY_BASE_WIDTH, OVERLAY_BASE_HEIGHT)

    def _setup_ui(self) -> None:
        """UIコンポーネントを設定する。"""
        self._central_widget = QWidget()
        self.setCentralWidget(self._central_widget)
        
        layout = QVBoxLayout(self._central_widget)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # コンテンツコンテナ
        self._content_container = QWidget()
        self._content_layout = QVBoxLayout(self._content_container)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(4)
        self._content_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # ステータスラベル
        self._status_label = QLabel("")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_label.setStyleSheet("color: white; font-weight: 600; font-size: 13px; font-family: 'Segoe UI';")
        
        # 波形ウィジェット
        self._waveform = WaveformWidget()
        self._waveform.hide()
        
        self._content_layout.addWidget(self._status_label)
        self._content_layout.addWidget(self._waveform)
        
        layout.addWidget(self._content_container)

    def _setup_animations(self) -> None:
        """プロパティアニメーションを設定する。"""
        self._geometry_animation = QPropertyAnimation(self, b"geometry")
        self._geometry_animation.setEasingCurve(QEasingCurve.Type.InOutBack)  # 滑らかな動き
        self._geometry_animation.setDuration(ANIMATION_DURATION_MS)

    def paintEvent(self, event) -> None:
        """ピル形状の背景を描画する。"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        radius = rect.height() / 2
        
        # 黒背景（Dynamic Island風）
        painter.setBrush(QBrush(QColor(0, 0, 0, 240)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, radius, radius)

    def set_state(self, state: Union[str, AppState]) -> None:
        """
        オーバーレイの状態を更新する。
        
        Args:
            state: 新しいアプリケーション状態
        """
        if isinstance(state, str):
            state = AppState(state)
        
        self._state = state
        
        if state == AppState.IDLE:
            self._set_idle_state()
        elif state == AppState.RECORDING:
            self._set_recording_state()
        elif state == AppState.TRANSCRIBING:
            self._set_transcribing_state()

    def show_temporary_message(self, message: str, duration_ms: int = 2000, is_error: bool = False) -> None:
        """
        一時的なメッセージを表示する。
        
        Args:
            message: 表示するメッセージ
            duration_ms: 表示時間（ミリ秒）
            is_error: エラーメッセージの場合True（赤色で表示）
        """
        self.show()
        self._animate_resize(OVERLAY_EXPANDED_WIDTH, OVERLAY_EXPANDED_HEIGHT)
        
        self._status_label.setText(message)
        self._waveform.stop_animation()
        
        color = "#FF453A" if is_error else "white"  # macOS風の赤
        self._status_label.setStyleSheet(f"color: {color}; font-weight: 600; font-size: 13px;")
        self._status_label.show()
        
        QTimer.singleShot(duration_ms, lambda: self.set_state(AppState.IDLE))

    def _set_idle_state(self) -> None:
        """待機状態を設定する。"""
        self._animate_resize(OVERLAY_BASE_WIDTH, OVERLAY_BASE_HEIGHT)
        self._status_label.hide()
        self._waveform.stop_animation()
        
        # アニメーション後に非表示
        QTimer.singleShot(ANIMATION_DURATION_MS, self.hide)

    def _set_recording_state(self) -> None:
        """録音状態を設定する。"""
        self.show()
        self._animate_resize(OVERLAY_EXPANDED_WIDTH, OVERLAY_EXPANDED_HEIGHT)
        self._status_label.setText("Listening...")
        self._status_label.setStyleSheet("color: white; font-weight: 600; font-size: 13px;")
        self._status_label.show()
        self._waveform.start_animation()

    def _set_transcribing_state(self) -> None:
        """文字起こし中状態を設定する。"""
        self.show()
        self._animate_resize(OVERLAY_EXPANDED_WIDTH, OVERLAY_EXPANDED_HEIGHT)
        self._status_label.setText("Processing...")
        self._status_label.show()
        self._waveform.stop_animation()

    def _animate_resize(self, target_width: int, target_height: int) -> None:
        """
        ウィンドウサイズをアニメーションで変更する。
        
        Args:
            target_width: 目標幅
            target_height: 目標高さ
        """
        screen = QApplication.primaryScreen().geometry()
        target_x = (screen.width() - target_width) // 2
        
        current_rect = self.geometry()
        target_rect = QRect(target_x, OVERLAY_TOP_MARGIN, target_width, target_height)
        
        if current_rect == target_rect:
            return

        self._geometry_animation.setStartValue(current_rect)
        self._geometry_animation.setEndValue(target_rect)
        self._geometry_animation.start()
