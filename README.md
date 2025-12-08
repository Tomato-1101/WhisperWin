# WhisperWin

faster-whisperを使用した、高速・高精度な常駐型音声入力ツールです。
ホットキーを押すだけで録音を開始し、文字起こし結果をアクティブなウィンドウに自動入力します。

## 特徴

- **⚡ 高速処理**: faster-whisperによる最適化で、従来比5-10倍の高速化
- **🎯 高精度**: large-v3などの最新モデルに対応
- **🖥️ モダンなUI**: Dynamic Island風オーバーレイとシステムトレイ統合
- **🧠 スマートなVRAM管理**: 使用後に自動でメモリ解放、必要時に自動プリロード
- **🎙️ ハルシネーション対策**: VADとno_speech確率フィルタで無音時の誤認識を防止
- **⚙️ GUIで設定変更**: 設定ウィンドウから各種パラメータを調整可能
- **🔄 ホットリロード**: 設定変更が即座に反映（再起動不要）
- **⌨️ グローバルホットキー**: どのアプリを使っていても、設定したキーで起動

## 必要環境

- **CUDA対応GPU**: NVIDIA GPU必須（CUDAが必要）
- **Python 3.8+**
- **ffmpeg**

## インストール

1. リポジトリをクローン:
   ```bash
   git clone https://github.com/Tomato-1101/whi.git
   cd whi
   ```

2. 仮想環境を作成・有効化:
   ```bash
   python -m venv venv
   .\venv\Scripts\Activate.ps1  # Windows PowerShell
   ```

3. 依存関係をインストール:
   ```bash
   pip install -r requirements.txt
   ```

4. `ffmpeg` がシステムにインストールされていることを確認してください。

## 使い方

### 開発モード

```bash
python run.py
```

### EXEビルド

```bash
pyinstaller SuperWhisperLike.spec --clean --noconfirm
```

ビルドされたEXEは `dist/SuperWhisperLike/SuperWhisperLike.exe` に生成されます。
（起動高速化のため、単一ファイルではなくフォルダ形式で出力されます）

### 起動後の操作

1. システムトレイにアイコンが表示されます
2. **ホットキー**（デフォルト: `Ctrl+Space`）を押している間録音されます
3. キーを離すと自動的に文字起こしが開始
4. 結果がアクティブなウィンドウに自動入力されます

### UI

- **オーバーレイ**: 画面上部にDynamic Island風の状態表示
  - 録音中: `Listening...`（赤いパルスエフェクト）
  - 処理中: `Thinking...`
- **システムトレイ**: 右クリックでメニュー表示
  - クリック: 設定ウィンドウを開く
  - Quit: アプリ終了

## 設定

### GUIから設定

システムトレイアイコンをクリックして設定ウィンドウを開きます。

#### General タブ
- **Hotkey**: 起動キー（例: `<ctrl>+<space>`, `<f2>`）
- **Trigger Mode**: `hold`（押している間録音）/ `toggle`（押して開始/停止）

#### Model タブ
- **Model Size**: tiny, base, small, medium, large, large-v2, large-v3, distil-large-v2
- **Compute Type**: float16, int8_float16, int8
- **Language**: 言語コード（ja, en など）

#### Advanced タブ
- **VAD Filter**: 音声区間検出の有効/無効
- **Release VRAM after**: メモリ解放までの秒数

### 設定ファイル

`settings.yaml` を直接編集することも可能です:

```yaml
# ホットキー設定
hotkey: '<ctrl>+<space>'
hotkey_mode: 'hold'

# モデル設定
model_size: 'large-v3'
compute_type: 'float16'
language: 'ja'
model_cache_dir: 'D:/whisper_cache'  # モデルキャッシュ場所

# VRAM管理
release_memory_delay: 7  # 秒

# 高度な設定
vad_filter: true
vad_min_silence_duration_ms: 500
condition_on_previous_text: false
no_speech_threshold: 0.6
log_prob_threshold: -1.0
no_speech_prob_cutoff: 0.7
beam_size: 5
```

## プロジェクト構造

```
src/
├── __init__.py            # パッケージ定義
├── app.py                 # メインアプリケーション
├── main.py                # エントリーポイント
├── config/                # 設定関連
│   ├── types.py           # 型定義（Enum, Dataclass）
│   ├── constants.py       # 定数
│   └── config_manager.py  # 設定管理
├── core/                  # コアロジック
│   ├── audio_recorder.py  # 音声録音
│   ├── transcriber.py     # 音声認識
│   └── input_handler.py   # テキスト入力
├── ui/                    # UI関連
│   ├── overlay.py         # オーバーレイ
│   ├── settings_window.py # 設定ウィンドウ
│   └── system_tray.py     # システムトレイ
└── utils/                 # ユーティリティ
    └── logger.py          # ロギング
run.py                     # 起動スクリプト
settings.yaml              # 設定ファイル
```

## トラブルシューティング

### 入力されない
- 管理者権限で実行されているアプリに入力する場合、このツールも管理者権限で実行する必要があります
- ホットキーが他のアプリと競合していないか確認してください

### "ご視聴ありがとうございました"などが出力される
- `settings.yaml` のハルシネーション対策パラメータを調整してください
- `no_speech_threshold` を上げる（例: 0.7-0.8）
- `no_speech_prob_cutoff` を下げる（例: 0.5-0.6）

### モデルロードエラー
- HuggingFaceからのモデルダウンロードが完了しているか確認
- ネットワーク接続を確認
- 初回は数GBのダウンロードが発生します

### VRAM不足
- より小さいモデルを使用（例: `medium`, `small`）
- `compute_type` を `int8` に変更
- `release_memory_delay` を短く設定

### WinError 1314
- `model_cache_dir` を指定して、シンボリックリンク問題を回避

## 技術スタック

- **faster-whisper**: 高速な音声認識エンジン
- **PyTorch (CUDA)**: GPU加速
- **PySide6**: モダンなGUIフレームワーク
- **pynput**: グローバルホットキー管理
- **sounddevice**: オーディオ録音
