# Settings UI - LLM設定の追加とmacOSデザイン改善

## 概要
Settings WindowにLLM後処理設定のUIを追加。全ての設定をGUIから変更可能にする。既存のmacOS風デザインを維持・改善。

---

## 現在の状況

### 既存のSettings UI構造
- **3ページ構成**: General、Model、Advanced
- **macOS風デザイン**: サイドバーナビゲーション、ライト/ダークモード対応
- **既存UI要素**: Hotkey recorder、Backend選択、VAD、メモリ管理

### UIに未実装の設定
- ❌ LLM後処理設定（llm_postprocess全体）
- ❌ model_cache_dir
- ❌ vad_min_silence_duration_ms
- ❌ その他の高度な音声認識パラメータ

---

## 実装計画

### 1. 新規「LLM」ページの追加

4番目のページとして「LLM」を追加（General、Model、Advanced、**LLM**）

#### UI要素構成

```
LLM Page
├─ LLM Post-Processing Settings (GroupBox)
│  ├─ Enable LLM Post-Processing (QCheckBox)
│  ├─ Provider (QComboBox: groq / cerebras)
│  ├─ Model (QComboBox - 動的に変更)
│  ├─ Timeout (QDoubleSpinBox: 1.0-30.0秒)
│  └─ Fallback on Error (QCheckBox)
│
├─ API Keys Status (GroupBox)
│  ├─ Groq API Key: ✓ Ready / ✗ Not Set (QLabel)
│  └─ Cerebras API Key: ✓ Ready / ✗ Not Set (QLabel)
│
└─ System Prompt (GroupBox)
   └─ Prompt Editor (QTextEdit - マルチライン編集)
```

---

### 2. コード変更詳細

#### ファイル: `src/ui/settings_window.py`

##### 2.1 `_setup_pages()` に4番目のページ追加

```python
def _setup_pages(self) -> None:
    """Create and add pages to the stack."""
    self._add_page("General", self._create_general_page())
    self._add_page("Model", self._create_model_page())
    self._add_page("Advanced", self._create_advanced_page())
    self._add_page("LLM", self._create_llm_page())  # NEW

    self._sidebar.setCurrentRow(0)
```

##### 2.2 新規メソッド: `_create_llm_page()`

```python
def _create_llm_page(self) -> QWidget:
    """Create LLM post-processing settings page."""
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setSpacing(20)

    # ===== LLM Settings Group =====
    llm_settings_group = QGroupBox("LLM Post-Processing Settings")
    llm_layout = QFormLayout()
    llm_layout.setSpacing(15)
    llm_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

    # Enable checkbox
    self._llm_enabled_check = QCheckBox("Enable LLM Post-Processing")
    self._llm_enabled_check.stateChanged.connect(self._on_llm_enabled_changed)
    llm_layout.addRow("", self._llm_enabled_check)

    # Provider selection
    self._llm_provider_combo = QComboBox()
    self._llm_provider_combo.addItems(["groq", "cerebras"])
    self._llm_provider_combo.currentTextChanged.connect(self._on_llm_provider_changed)
    llm_layout.addRow("Provider:", self._llm_provider_combo)

    # Model selection (dynamic based on provider)
    self._llm_model_combo = QComboBox()
    llm_layout.addRow("Model:", self._llm_model_combo)

    # Timeout
    self._llm_timeout_spin = QDoubleSpinBox()
    self._llm_timeout_spin.setRange(1.0, 30.0)
    self._llm_timeout_spin.setSingleStep(0.5)
    self._llm_timeout_spin.setSuffix(" sec")
    self._llm_timeout_spin.setDecimals(1)
    llm_layout.addRow("Timeout:", self._llm_timeout_spin)

    # Fallback on error
    self._llm_fallback_check = QCheckBox("Use original text if LLM fails")
    llm_layout.addRow("", self._llm_fallback_check)

    llm_settings_group.setLayout(llm_layout)
    layout.addWidget(llm_settings_group)

    # ===== API Keys Status Group =====
    api_keys_group = QGroupBox("API Keys Status")
    api_keys_layout = QFormLayout()
    api_keys_layout.setSpacing(10)
    api_keys_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

    self._groq_llm_key_status = QLabel()
    api_keys_layout.addRow("Groq API Key:", self._groq_llm_key_status)

    self._cerebras_key_status = QLabel()
    api_keys_layout.addRow("Cerebras API Key:", self._cerebras_key_status)

    api_keys_group.setLayout(api_keys_layout)
    layout.addWidget(api_keys_group)

    # ===== System Prompt Group =====
    prompt_group = QGroupBox("System Prompt")
    prompt_layout = QVBoxLayout()

    prompt_label = QLabel("Define how the LLM should transform transcription results:")
    prompt_label.setStyleSheet("color: gray; font-size: 11px; margin-bottom: 5px;")
    prompt_layout.addWidget(prompt_label)

    self._llm_prompt_edit = QTextEdit()
    self._llm_prompt_edit.setPlaceholderText(
        "Example:\n"
        "音声認識結果を以下のルールで変換してください:\n"
        "1. 数式: 「いち たす にー」→「1 + 2」\n"
        "2. カタカナ英語: 「アップル」→「Apple」\n"
        "変換後のテキストのみ返してください。"
    )
    self._llm_prompt_edit.setMinimumHeight(150)
    prompt_layout.addWidget(self._llm_prompt_edit)

    prompt_group.setLayout(prompt_layout)
    layout.addWidget(prompt_group)

    layout.addStretch()
    return page
```

##### 2.3 新規ヘルパーメソッド

```python
def _on_llm_enabled_changed(self, state: int) -> None:
    """Handle LLM enabled state change."""
    enabled = (state == Qt.CheckState.Checked.value)

    # Enable/disable all LLM-related widgets
    self._llm_provider_combo.setEnabled(enabled)
    self._llm_model_combo.setEnabled(enabled)
    self._llm_timeout_spin.setEnabled(enabled)
    self._llm_fallback_check.setEnabled(enabled)
    self._llm_prompt_edit.setEnabled(enabled)

def _on_llm_provider_changed(self, provider: str) -> None:
    """Update model list based on selected provider."""
    self._llm_model_combo.clear()

    if provider == "groq":
        models = [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768"
        ]
    elif provider == "cerebras":
        models = [
            "llama3.1-8b",
            "llama3.1-70b"
        ]
    else:
        models = []

    self._llm_model_combo.addItems(models)

def _update_api_key_status(self) -> None:
    """Update API key status labels."""
    # Groq
    has_groq = bool(os.environ.get("GROQ_API_KEY"))
    groq_text = "✓ Ready" if has_groq else "✗ Not Set"
    groq_color = "green" if has_groq else "red"
    self._groq_llm_key_status.setText(groq_text)
    self._groq_llm_key_status.setStyleSheet(f"color: {groq_color}; font-weight: bold;")

    # Cerebras
    has_cerebras = bool(os.environ.get("CEREBRAS_API_KEY"))
    cerebras_text = "✓ Ready" if has_cerebras else "✗ Not Set"
    cerebras_color = "green" if has_cerebras else "red"
    self._cerebras_key_status.setText(cerebras_text)
    self._cerebras_key_status.setStyleSheet(f"color: {cerebras_color}; font-weight: bold;")
```

##### 2.4 `_load_current_settings()` にLLM設定読み込み追加

```python
def _load_current_settings(self) -> None:
    """Load values from config into UI."""
    config = self._config_manager.config

    # ... 既存の設定読み込み ...

    # LLM Settings
    llm_config = config.get("llm_postprocess", {})
    self._llm_enabled_check.setChecked(llm_config.get("enabled", False))
    self._llm_provider_combo.setCurrentText(llm_config.get("provider", "groq"))
    self._llm_timeout_spin.setValue(llm_config.get("timeout", 5.0))
    self._llm_fallback_check.setChecked(llm_config.get("fallback_on_error", True))
    self._llm_prompt_edit.setPlainText(llm_config.get("system_prompt", ""))

    # Update model list and select current model
    self._on_llm_provider_changed(self._llm_provider_combo.currentText())
    self._llm_model_combo.setCurrentText(llm_config.get("model", "llama-3.3-70b-versatile"))

    # Initialize enabled state
    self._on_llm_enabled_changed(self._llm_enabled_check.checkState().value)

    # Update API key status
    self._update_api_key_status()
```

##### 2.5 `_save_settings()` にLLM設定保存追加

```python
def _save_settings(self) -> None:
    """Save settings to config file."""
    new_config = {
        # ... 既存の設定 ...

        # LLM Post-Processing
        "llm_postprocess": {
            "enabled": self._llm_enabled_check.isChecked(),
            "provider": self._llm_provider_combo.currentText(),
            "model": self._llm_model_combo.currentText(),
            "timeout": self._llm_timeout_spin.value(),
            "fallback_on_error": self._llm_fallback_check.isChecked(),
            "system_prompt": self._llm_prompt_edit.toPlainText(),
        },
    }

    if self._config_manager.save(new_config):
        self.close()
    else:
        QMessageBox.critical(self, "Error", "Failed to save settings.")
```

##### 2.6 インポートに `QTextEdit`, `QDoubleSpinBox` 追加

```python
from PySide6.QtWidgets import (
    # ... 既存のインポート ...
    QTextEdit,
    QDoubleSpinBox,  # NEW
)
```

---

### 3. スタイル改善 (Optional)

#### ファイル: `src/ui/styles.py`

既存のスタイルシートに以下を追加してQTextEditのスタイルを統一：

```python
# In get_stylesheet() method, add:

QTextEdit {{
    background-color: {c.INPUT_BG};
    color: {c.TEXT};
    border: 1px solid {c.BORDER};
    border-radius: 6px;
    padding: 8px;
    font-family: '{MacTheme.FONT_FAMILY}';
    font-size: {MacTheme.FONT_SIZE_NORMAL}px;
}}

QTextEdit:focus {{
    border: 2px solid {c.ACCENT};
}}
```

---

### 4. macOSデザイン改善案

#### 4.1 グループボックスのスタイル改善

より洗練されたmacOS風の外観にするため、GroupBoxのタイトルを大きく、パディングを調整：

```python
QGroupBox {{
    font-weight: 600;
    font-size: 14px;
    border: 1px solid {c.BORDER};
    border-radius: 8px;
    margin-top: 16px;
    padding-top: 20px;
    background-color: {c.WINDOW_BG};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 5px;
    color: {c.TEXT};
}}
```

#### 4.2 より細かいグリッド間隔

FormLayoutのスペーシングをmacOS Venturaスタイルに調整：

```python
layout.setSpacing(12)  # より詰まった間隔
layout.setVerticalSpacing(12)
layout.setHorizontalSpacing(10)
```

#### 4.3 プレースホルダーテキストのスタイル

```python
QLineEdit::placeholder, QTextEdit::placeholder {{
    color: {c.SECONDARY_TEXT};
    font-style: italic;
}}
```

---

### 5. 実装チェックリスト

#### Phase 1: 基本UI追加
- [ ] `_create_llm_page()` メソッド実装
- [ ] `_setup_pages()` にLLMページ追加
- [ ] LLM設定用のウィジェット定義

#### Phase 2: ロジック実装
- [ ] `_on_llm_enabled_changed()` 実装
- [ ] `_on_llm_provider_changed()` 実装
- [ ] `_update_api_key_status()` 実装
- [ ] `_load_current_settings()` にLLM読み込み追加
- [ ] `_save_settings()` にLLM保存追加

#### Phase 3: スタイリング
- [ ] QTextEditスタイル追加
- [ ] GroupBoxスタイル改善
- [ ] プレースホルダースタイル追加

#### Phase 4: テスト
- [ ] 設定の保存・読み込み確認
- [ ] プロバイダー変更時のモデルリスト更新確認
- [ ] Enabled/Disabledの切り替え確認
- [ ] ライト/ダークモード両方で表示確認

---

## 完成後のUI構造

```
Settings Window
├─ Sidebar (200px)
│  ├─ General
│  ├─ Model
│  ├─ Advanced
│  └─ LLM (NEW)
│
└─ Content Area
   ├─ Header (Title + Theme Toggle)
   ├─ Page Content (QStackedWidget)
   │  ├─ General Page
   │  ├─ Model Page
   │  ├─ Advanced Page
   │  └─ LLM Page (NEW)
   │     ├─ LLM Post-Processing Settings
   │     ├─ API Keys Status
   │     └─ System Prompt Editor
   └─ Buttons (Save / Cancel)
```

---

## 変更ファイル

- **src/ui/settings_window.py** - LLMページとロジック追加
- **src/ui/styles.py** - QTextEditスタイル追加（Optional）

---

## 設計上の注意点

1. **ネストした辞書の保存**: `llm_postprocess` は辞書なので、ConfigManager.save()が適切に処理することを確認
2. **API Key Status**: 環境変数をリアルタイム確認（再読み込み時に更新）
3. **Model Combobox**: プロバイダー変更時に動的更新、既存選択を保持
4. **Enabled状態**: チェックボックスのON/OFFで全LLM関連ウィジェットを有効/無効化
5. **macOS風**: 角丸、適切なパディング、アクセントカラー、ライト/ダークモード対応
