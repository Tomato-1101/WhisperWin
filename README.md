# WhisperWin

faster-whisperを使用した、高速・高精度な常駐型音声入力ツールです。
ホットキーを押すだけで録音を開始し、文字起こし結果をアクティブなウィンドウに自動入力します。

## 特徴

- **⚡ 高速処理**: faster-whisper + Groq Cloud APIによる最適化で、従来比5-10倍の高速化
- **🎯 高精度**: large-v3などの最新モデルに対応
- **🤖 LLM後処理**: 音声認識結果をGroq/CerebrasのLLMで自動変換
  - 数式変換: 「いち たす にー は さん」→「1 + 2 = 3」
  - カタカナ英語変換: 「アップル」→「Apple」
  - カスタマイズ可能なプロンプト
- **🖥️ モダンなUI**: Dynamic Island風オーバーレイとシステムトレイ統合
- **🧠 スマートなVRAM管理**: 使用後に自動でメモリ解放、必要時に自動プリロード
- **☁️ クラウド対応**: Groq Cloud APIで高速音声認識（GPUレス環境でも動作）
- **🎙️ ハルシネーション対策**: VADとno_speech確率フィルタで無音時の誤認識を防止
- **⚙️ GUIで設定変更**: 設定ウィンドウから各種パラメータを調整可能
- **🔄 ホットリロード**: 設定変更が即座に反映（再起動不要）
- **⌨️ グローバルホットキー**: どのアプリを使っていても、設定したキーで起動
- **🌙 ダーク/ライトテーマ**: macOS風の美しいUIテーマ切替対応

## 必要環境

- **CUDA対応GPU**: NVIDIA GPU必須（ローカルモードの場合）
- **Python 3.8+**
- **ffmpeg**

> **Note**: Groq Cloudモードを使用すればGPUなしでも動作可能です。

## インストール

1. リポジトリをクローン:
   ```bash
   git clone https://github.com/Tomato-1101/WhisperWin.git
   cd WhisperWin
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
pyinstaller WhisperWin.spec --clean --noconfirm
```

ビルドされたEXEは `dist/WhisperWin/WhisperWin.exe` に生成されます。
（起動高速化のため、単一ファイルではなくフォルダ形式で出力されます）

### 起動後の操作

1. システムトレイにアイコンが表示されます
2. **ホットキー**（デフォルト: `F2`）を押すと録音開始/停止
3. 文字起こし結果がアクティブなウィンドウに自動入力されます

### UI

- **オーバーレイ**: 画面上部にDynamic Island風の状態表示
  - 録音中: `Listening...`（波形アニメーション）
  - 処理中: `Processing...`
- **システムトレイ**: 右クリックでメニュー表示
  - クリック: 設定ウィンドウを開く
  - Quit: アプリ終了

## 設定

### GUIから設定

システムトレイアイコンをクリックして設定ウィンドウを開きます。

#### General タブ
- **Global Hotkey**: 起動キー（クリックして録音）
- **Trigger Mode**: `hold`（押している間録音）/ `toggle`（押して開始/停止）
- **Language**: 言語コード（ja, en など）

#### Model タブ
- **Transcription Engine**: ローカルGPU / Groq Cloud
- **Model Size**: tiny, base, small, medium, large, large-v3など
- **Compute Type**: float16, int8_float16, int8

#### Advanced タブ
- **VAD Filter**: 音声区間検出の有効/無効
- **Release Memory Delay**: VRAM解放までの秒数

#### LLM タブ
- **Enable LLM Post-Processing**: LLM後処理の有効/無効
- **Provider**: LLMプロバイダー（Groq / Cerebras）
- **Model**: 使用するLLMモデル
- **Timeout**: APIタイムアウト時間（秒）
- **Fallback on Error**: LLM処理失敗時に元のテキストを使用
- **System Prompt**: LLMへの指示（変換ルールをカスタマイズ）

### 設定ファイル

`settings.yaml` を直接編集することも可能です:

```yaml
# ホットキー設定
hotkey: '<f2>'
hotkey_mode: 'toggle'

# 文字起こしバックエンド
transcription_backend: 'local'  # 'local' または 'groq'

# モデル設定（ローカルモード）
model_size: 'large-v3'
compute_type: 'float16'
language: 'ja'
model_cache_dir: 'D:/whisper_cache'

# Groq API設定
groq_model: 'whisper-large-v3-turbo'

# VRAM管理
release_memory_delay: 300  # 秒

# 高度な設定
vad_filter: true
vad_min_silence_duration_ms: 500
condition_on_previous_text: false
no_speech_threshold: 0.6
log_prob_threshold: -1.0
no_speech_prob_cutoff: 0.7
beam_size: 5

# 開発者モード（タイミングログ出力）
dev_mode: false

# テーマ設定
dark_mode: false

# LLM後処理設定
llm_postprocess:
  enabled: true
  provider: 'groq'  # groq または cerebras
  model: 'llama-3.3-70b-versatile'
  timeout: 5.0
  fallback_on_error: true
  system_prompt: |
    音声認識結果を以下のルールで変換してください:
    1. 数式: 「いち たす にー」→「1 + 2」
    2. カタカナ英語: 「アップル」→「Apple」
    変換後のテキストのみ返してください。
```

### API キーの設定

Groq APIを使用する場合は、プロジェクトルートに `.env` ファイルを作成してAPIキーを設定してください:

```env
# Groq API Key（文字起こし & LLM後処理）
GROQ_API_KEY=gsk_your_api_key_here

# Cerebras API Key（LLM後処理、オプション）
CEREBRAS_API_KEY=csk-your_api_key_here
```

## プロジェクト構造

```
src/
├── __init__.py            # パッケージ定義
├── app.py                 # メインアプリケーションコントローラー
├── main.py                # エントリーポイント
├── config/                # 設定関連
│   ├── types.py           # 型定義（Enum, Dataclass）
│   ├── constants.py       # 定数・デフォルト値
│   └── config_manager.py  # 設定管理・ホットリロード
├── core/                  # コアビジネスロジック
│   ├── audio_recorder.py  # 音声録音
│   ├── audio_utils.py     # 音声フォーマット変換
│   ├── transcriber.py     # ローカルGPU文字起こし
│   ├── groq_transcriber.py # Groq API文字起こし
│   ├── text_processor.py  # LLM後処理（Groq/Cerebras）
│   ├── vad.py             # 音声活性検出（Silero VAD）
│   └── input_handler.py   # テキスト入力シミュレーション
├── ui/                    # UIコンポーネント
│   ├── overlay.py         # Dynamic Islandオーバーレイ
│   ├── settings_window.py # 設定ウィンドウ
│   ├── styles.py          # macOS風テーマ定義
│   └── system_tray.py     # システムトレイアイコン
└── utils/                 # ユーティリティ
    └── logger.py          # ロギング設定
run.py                     # 起動スクリプト
settings.yaml              # 設定ファイル
```

> **Note**: 全ファイルに日本語コメントが記載されており、コードの理解が容易です。

## 開発者向け機能

### 開発者モード

`settings.yaml` で `dev_mode: true` を設定すると:

- 出力テキストが引用符で囲まれます
- `dev_timing.log` にタイミング情報が記録されます:
  - 音声の長さ
  - VAD処理時間
  - Whisper API呼び出し時間
  - LLM API呼び出し時間
  - テキスト挿入時間
  - 合計処理時間

### LLM処理ログ

LLM後処理が有効な場合、ターミナルに処理前後のテキストが表示されます:
```
[LLM処理前] いち たす にー は さん
[LLM処理後] 1 + 2 = 3
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
- Groq Cloudモードに切り替え

### WinError 1314
- `model_cache_dir` を指定して、シンボリックリンク問題を回避

### LLM後処理が機能しない
- `.env` ファイルにAPIキーが正しく設定されているか確認
- `llm_postprocess.enabled` が `true` になっているか確認
- ターミナルのログでエラーメッセージを確認
- `timeout` の値を増やす（遅いネットワーク環境の場合）

### LLM変換が期待通りでない
- `system_prompt` をカスタマイズして指示を明確にする
- より高性能なモデルを試す（例: `llama-3.3-70b-versatile`）
- `fallback_on_error` を有効にして、失敗時に元のテキストを保持

## 技術スタック

- **faster-whisper**: 高速な音声認識エンジン
- **Groq Cloud API**: クラウド音声認識 & LLM後処理
- **Cerebras Cloud SDK**: 高速LLM後処理
- **Silero VAD**: 音声活性検出
- **PyTorch (CUDA)**: GPU加速
- **PySide6**: モダンなGUIフレームワーク
- **pynput**: グローバルホットキー管理
- **sounddevice**: オーディオ録音
