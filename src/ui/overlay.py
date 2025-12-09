"""
コンパクトオーバーレイモジュール（AquaVoice風）

画面上部にミニマルな音声入力インジケーターを表示する。
録音中・処理中などの状態を視覚的にフィードバックし、
音声検出時のみ波形アニメーションを動かす。
"""

import math
from typing import Union

from PySide6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    QRect,
    QRectF,
    Qt,
    QTimer,
)
from PySide6.QtGui import (
    QBrush,
    QColor,
    QPainter,
    QPen,
)
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget

from ..config.constants import (
    ANIMATION_DURATION_MS,
    OVERLAY_BASE_HEIGHT,
    OVERLAY_BASE_WIDTH,
    OVERLAY_EXPANDED_HEIGHT,
    OVERLAY_EXPANDED_WIDTH,
    OVERLAY_TOP_MARGIN,
)
from ..config.types import AppState


class WaveformWidget(QWidget):
    """
    コンパクトな音声波形インジケーター（AquaVoice風）。
    
    5本のバーでシンプルに音声入力を可視化。
    音声検出時のみアニメーションが動き、
    静寂時は静止状態を維持する。
    """

    def __init__(self, parent=None):
        """波形ウィジェットを初期化する。"""
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setFixedHeight(24)
        
        # 波形バーの設定（5本のシンプルなバー）
        self._bars_count = 5
        self._amplitudes = [0.3] * self._bars_count  # 現在の振幅
        self._target_amplitudes = [0.3] * self._bars_count  # 目標振幅
        self._phase = 0.0
        
        # 音声検出状態
        self._voice_active = False
        self._processing_mode = False  # 処理中モード（常にアニメーション）
        self._is_animating = False
        
        # アニメーションタイマー（約60FPS）
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_wave)
        self._timer.setInterval(16)
        
        # アクセントカラー（緑/青のグラデーション風）
        self._active_color = QColor("#34C759")  # Apple Green
        self._idle_color = QColor("#8E8E93")    # Gray

    def start_animation(self):
        """波形アニメーションを開始する。"""
        if not self._is_animating:
            self._is_animating = True
            self._timer.start()
        self.show()

    def stop_animation(self):
        """波形アニメーションを停止する。"""
        self._is_animating = False
        self._processing_mode = False
        self._timer.stop()
        self._voice_active = False
        # 振幅をリセット
        self._amplitudes = [0.3] * self._bars_count
        self._target_amplitudes = [0.3] * self._bars_count
        self.update()

    def set_voice_active(self, active: bool):
        """
        音声検出状態を設定する。
        処理中モードでは常にTrueが維持される。
        
        Args:
            active: 音声が検出されている場合True
        """
        # 処理中モードでは常に動く
        if self._processing_mode:
            self._voice_active = True
        else:
            self._voice_active = active

    def set_processing_mode(self, processing: bool):
        """
        処理中モードを設定する。処理中は常にアニメーションが動く。
        
        Args:
            processing: 処理中の場合True
        """
        self._processing_mode = processing
        if processing:
            self._voice_active = True  # 処理中は常に動く

    def _update_wave(self):
        """波形の物理演算を更新する。"""
        self._phase += 0.15
        
        # 処理中モードまたは音声検出中は動く
        should_animate = self._processing_mode or self._voice_active
        
        for i in range(self._bars_count):
            if should_animate:
                # 音声検出中：活発に動く
                # 中央のバーが一番高く、端が低い波形
                center_factor = 1.0 - abs(i - self._bars_count // 2) / (self._bars_count // 2 + 1)
                base_amp = 0.4 + center_factor * 0.4
                
                # サイン波で自然な動き
                wave = math.sin(self._phase + i * 0.8) * 0.3
                self._target_amplitudes[i] = min(1.0, max(0.2, base_amp + wave))
            else:
                # 静寂時：静かに待機（低い状態）
                self._target_amplitudes[i] = 0.15
            
            # 滑らかな補間
            diff = self._target_amplitudes[i] - self._amplitudes[i]
            self._amplitudes[i] += diff * 0.2

        self.update()

    def paintEvent(self, event):
        """波形を描画する。"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        width = self.width()
        height = self.height()
        bar_width = 4      # バーの幅
        spacing = 5        # バー間隔
        total_width = (bar_width + spacing) * self._bars_count - spacing
        start_x = (width - total_width) / 2
        max_height = height - 4  # 上下に2pxのマージン
        
        painter.setPen(Qt.PenStyle.NoPen)
        
        for i in range(self._bars_count):
            amp = self._amplitudes[i]
            current_height = max(4, max_height * amp)
            
            x = start_x + i * (bar_width + spacing)
            y = (height - current_height) / 2
            
            # 音声検出状態に応じた色
            if self._voice_active:
                color = self._active_color
            else:
                color = self._idle_color
            
            painter.setBrush(QBrush(color))
            painter.drawRoundedRect(
                QRectF(x, y, bar_width, current_height),
                bar_width / 2, bar_width / 2
            )


class DynamicIslandOverlay(QMainWindow):
    """
    コンパクトなオーバーレイウィンドウ（AquaVoice風）。
    
    画面上部中央にフレームレスで表示され、
    シンプルな波形でアプリケーション状態をフィードバックする。
    """
    
    def __init__(self) -> None:
        """オーバーレイウィンドウを初期化する。"""
        super().__init__()
        
        self._setup_window()
        self._setup_ui()
        self._setup_animations()
        
        self._state = AppState.IDLE
        self._is_visible = False
        self.set_state(AppState.IDLE)

    def _setup_window(self) -> None:
        """ウィンドウプロパティを設定する。"""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # 初期位置（画面中央上部）
        screen = QApplication.primaryScreen().geometry()
        x_pos = (screen.width() - OVERLAY_BASE_WIDTH) // 2
        self.setGeometry(x_pos, OVERLAY_TOP_MARGIN, OVERLAY_BASE_WIDTH, OVERLAY_BASE_HEIGHT)

    def _setup_ui(self) -> None:
        """UIコンポーネントを設定する。"""
        # 波形ウィジェットのみ（テキストなし）
        self._waveform = WaveformWidget(self)
        self.setCentralWidget(self._waveform)

    def _setup_animations(self) -> None:
        """プロパティアニメーションを設定する。"""
        # サイズアニメーション
        self._geometry_animation = QPropertyAnimation(self, b"geometry")
        self._geometry_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._geometry_animation.setDuration(ANIMATION_DURATION_MS)
        
        # 透明度アニメーション
        self._opacity_animation = QPropertyAnimation(self, b"windowOpacity")
        self._opacity_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._opacity_animation.setDuration(150)  # 短めのフェード
        
        # 初期透明度
        self.setWindowOpacity(0.0)

    def paintEvent(self, event) -> None:
        """ピル形状の背景を描画する。"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        radius = rect.height() / 2
        
        # 半透明の黒背景
        painter.setBrush(QBrush(QColor(30, 30, 30, 220)))
        painter.setPen(QPen(QColor(60, 60, 60, 100), 1))
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

    def set_voice_active(self, active: bool) -> None:
        """
        音声検出状態を波形に伝達する。
        
        Args:
            active: 音声が検出されている場合True
        """
        self._waveform.set_voice_active(active)

    def show_temporary_message(self, message: str, duration_ms: int = 2000, is_error: bool = False) -> None:
        """
        一時的なメッセージを表示する（波形のみで表現）。
        
        Args:
            message: 表示するメッセージ（現在は使用しない）
            duration_ms: 表示時間（ミリ秒）
            is_error: エラーメッセージの場合True
        """
        self._show_overlay()
        self._animate_resize(OVERLAY_EXPANDED_WIDTH, OVERLAY_EXPANDED_HEIGHT)
        
        # エラー時は赤色の波形
        if is_error:
            self._waveform._active_color = QColor("#FF453A")
        else:
            self._waveform._active_color = QColor("#34C759")
        
        self._waveform.set_voice_active(False)
        self._waveform.update()
        
        QTimer.singleShot(duration_ms, lambda: self.set_state(AppState.IDLE))

    def _show_overlay(self) -> None:
        """オーバーレイをフェードインで表示する。"""
        if not self._is_visible:
            self._is_visible = True
            self.show()
            
            # フェードインアニメーション
            self._opacity_animation.stop()
            self._opacity_animation.setStartValue(0.0)
            self._opacity_animation.setEndValue(1.0)
            self._opacity_animation.start()

    def _hide_overlay(self) -> None:
        """オーバーレイをフェードアウトで非表示にする。"""
        if self._is_visible:
            self._is_visible = False
            
            # フェードアウトアニメーション
            self._opacity_animation.stop()
            self._opacity_animation.setStartValue(self.windowOpacity())
            self._opacity_animation.setEndValue(0.0)
            self._opacity_animation.finished.connect(self._on_fade_out_finished)
            self._opacity_animation.start()

    def _on_fade_out_finished(self) -> None:
        """フェードアウト完了時にウィンドウを非表示にする。"""
        self._opacity_animation.finished.disconnect(self._on_fade_out_finished)
        if not self._is_visible:  # まだ非表示状態なら
            self.hide()

    def _set_idle_state(self) -> None:
        """待機状態を設定する。フェードアウトで非表示。"""
        self._waveform.stop_animation()
        self._hide_overlay()

    def _set_recording_state(self) -> None:
        """録音状態を設定する。"""
        self._show_overlay()
        self._animate_resize(OVERLAY_EXPANDED_WIDTH, OVERLAY_EXPANDED_HEIGHT)
        self._waveform._active_color = QColor("#34C759")  # Green
        self._waveform.start_animation()

    def _set_transcribing_state(self) -> None:
        """文字起こし中状態を設定する。"""
        self._show_overlay()
        self._animate_resize(OVERLAY_EXPANDED_WIDTH, OVERLAY_EXPANDED_HEIGHT)
        self._waveform._active_color = QColor("#007AFF")  # Blue
        self._waveform.set_processing_mode(True)  # 処理中は常にアニメーション
        self._waveform.start_animation()

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

        self._geometry_animation.stop()
        self._geometry_animation.setStartValue(current_rect)
        self._geometry_animation.setEndValue(target_rect)
        self._geometry_animation.start()
