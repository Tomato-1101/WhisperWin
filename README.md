# WhisperWin

<div align="center">

**高速・高精度な常駐型音声入力ツール（Windows / macOS 対応）**

ホットキーを押すだけで音声入力を開始し、文字起こし結果を瞬時にアクティブウィンドウへ自動入力

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS-lightgrey.svg)]()
[![License](https://img.shields.io/badge/license-GPL--3.0-green.svg)](LICENSE)

</div>

---

## 📖 目次

- [特徴](#-特徴)
- [必要環境](#-必要環境)
- [インストール](#-インストール)
- [クイックスタート](#-クイックスタート)
- [デュアルホットキー機能](#-デュアルホットキー機能)
- [設定方法](#-設定方法)
- [API 設定](#-api-設定)
- [音声前処理](#-音声前処理)
- [トラブルシューティング](#-トラブルシューティング)
- [開発者向け情報](#-開発者向け情報)

---

## ✨ 特徴

### 🎯 デュアルホットキーで賢く使い分け

**2 つのホットキーで異なるバックエンドを使い分けられます。**

- **ホットキー 1**: 高精度な OpenAI API で重要な議事録
- **ホットキー 2**: 高速な Groq API で日常のメモ

各ホットキーに以下を個別設定可能：

- ショートカットキー（`<F2>`, `<shift_r>`, `<cmd_r>`, `<ctrl>+<space>` 等）
- トリガーモード（`hold`: 押している間録音 / `toggle`: 押して開始/停止）
- バックエンド（`groq` / `openai`）
- API モデルとプロンプト

### ⚡ その他の主要機能

- **🖥️ Cross-Platform**: Windows / macOS の単一コードベース対応
- **🎚️ 音量正規化**: 小さい声を持ち上げて API 認識精度を底上げ（音割れ防止のヘッドルーム付き）
- **🎙️ ローカル VAD**: 無音時の API 呼び出しをスキップ。Apple Silicon (MPS) / NVIDIA CUDA / CPU で自動フォールバック
- **🌐 API ベース**: 文字起こしはクラウド API（OpenAI / Groq）で GPU 不要
- **🪟 Dynamic Island 風 UI**: モダンなオーバーレイ表示
- **⚙️ GUI 設定**: 設定ウィンドウから簡単に変更
- **🔄 ホットリロード**: `settings.yaml` 変更が即座に反映（再起動不要）
- **🎯 ダブルタップ Auto-Enter**: 連続入力後に自動で Enter（チャットアプリ向け）

---

## 💻 必要環境

| 項目 | 要件 |
|---|---|
| **OS** | Windows 10/11 または macOS 11+ |
| **Python** | 3.10 以上 |
| **ffmpeg** | `PATH` に通っていること（音声変換用） |
| **GPU** | **不要**（VAD は CPU でも動く。Apple Silicon は MPS、NVIDIA は CUDA を自動検出） |
| **API キー** | OpenAI または Groq のいずれか（両方併用も可） |

> **💡 Tip**: 文字起こしはすべてクラウド API なので、GPU 非搭載 PC でも動作します。

---

## 📦 インストール

### 1. リポジトリをクローン

```bash
git clone https://github.com/Tomato-1101/WhisperWin.git
cd WhisperWin
```

### 2. 仮想環境を作成・有効化

**Windows (PowerShell)**:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**macOS / Linux**:

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. 依存関係をインストール

```bash
pip install -r requirements.txt
```

> `torch` / `torchaudio` は両 OS とも標準 wheel が使えます。Apple Silicon は MPS、NVIDIA GPU 搭載機は自動的に CUDA を利用します（VAD のみ）。

### 4. ffmpeg の確認

```bash
ffmpeg -version
```

未インストールの場合：

- **Windows**: [ffmpeg.org](https://ffmpeg.org/download.html) からダウンロードして `PATH` に追加
- **macOS**: `brew install ffmpeg`

### 5. (macOS のみ) 権限を許可

初回起動時、macOS が以下の権限を要求します。**システム設定 → プライバシーとセキュリティ** で許可してください：

- **入力監視 (Input Monitoring)**: グローバルホットキー検出のため
- **アクセシビリティ (Accessibility)**: テキスト挿入のため
- **マイク**: 音声録音のため

---

## 🚀 クイックスタート

### 起動方法

**OS 別ランチャー**:

```bash
# Windows
run.bat

# macOS / Linux
./run.sh
```

**または直接 Python**:

```bash
python run.py
```

### 基本的な使い方

1. システムトレイ（Windows）/ メニューバー（macOS）にアイコンが表示される
2. ホットキーを押す（既定: `<f2>` / `<f3>`）
3. 音声入力する
4. ホットキーを離す（`hold` モード）またはもう一度押す（`toggle` モード）
5. 文字起こし結果がアクティブウィンドウに自動入力される

### 設定を変更する

トレイアイコンをクリックして設定ウィンドウを開き、各種パラメータを変更後「**Save Settings**」を押す。

---

## 🎯 デュアルホットキー機能

WhisperWin は **2 つの独立したホットキー** を設定でき、各ホットキーに異なるバックエンド・モデルを割り当てられます。

### 使用例

**例 1: 速さと精度の使い分け**

| スロット | ホットキー | バックエンド | モデル | 用途 |
|---|---|---|---|---|
| ホットキー 1 | `<shift_r>` (hold) | OpenAI | gpt-4o-mini-transcribe | 重要な議事録・高精度 |
| ホットキー 2 | `<f2>` (toggle) | Groq | whisper-large-v3-turbo | 日常のメモ・高速 |

**例 2: 言語切替**

| スロット | ホットキー | プロンプト | 用途 |
|---|---|---|---|
| ホットキー 1 | `<ctrl>+<space>` | `Language: Japanese` | 日本語入力 |
| ホットキー 2 | `<alt>+<space>` | `Language: English` | 英語入力 |

### バックエンド比較

| バックエンド | 速度 | 精度 | 料金 | 用途 |
|---|---|---|---|---|
| **groq** | **超高速** | 高 | 無料（制限あり） | 日常使い・お試し |
| **openai** | 高速 | **最高** | 有料 | 重要な文書・高精度が必要 |

> **VAD（ローカル）**: 無音時の API 呼び出しをスキップ。バックエンド共通でローカル動作。

---

## ⚙️ 設定方法

### GUI 設定（推奨）

トレイアイコンをクリックして設定ウィンドウを開く。

#### 📍 General ページ

ホットキー 1 / 2 をそれぞれ：

- **Shortcut**: ホットキー文字列（例: `<f2>`, `<shift_r>`, `<cmd_r>`, `<ctrl>+<space>`）
- **Mode**: `hold` / `toggle`
- **Backend**: `groq` / `openai`
- **Model**: API モデル
- **Prompt**: ヒントテキスト（任意）

共通：

- **Language**: 言語コード（`ja`, `en` 等）

#### 📍 Advanced ページ

- **VAD Filter**: 音声区間検出の有効化
- **VAD Min Silence**: 無音判定の最小継続時間（ms）
- **Auto Enter Delay**: ダブルタップ Auto-Enter で Enter を打つまでの待機（0〜500ms）
- **Input Device**: 入力マイクデバイス
- **Audio Preprocess - Volume Normalization**: 音量正規化の ON/OFF（[後述](#-音声前処理)）

### 設定ファイル（上級者向け）

`settings.yaml` を直接編集できます：

```yaml
# グローバル設定
language: ja
vad_filter: true
vad_min_silence_duration_ms: 500
audio_input_device: default
auto_enter_delay_ms: 50

# 音声前処理（API 送信前）
audio_preprocess:
  volume_normalize: true   # Peak+RMS ハイブリッド正規化

# ホットキー 1
hotkey1:
  hotkey: <shift_r>
  hotkey_mode: hold
  backend: openai
  api_model: gpt-4o-mini-transcribe
  api_prompt: ""

# ホットキー 2
hotkey2:
  hotkey: <f2>
  hotkey_mode: toggle
  backend: groq
  api_model: whisper-large-v3-turbo
  api_prompt: ""

# 起動時 VAD プリロード（初回文字起こし高速化）
preload_on_startup: true

# その他
dark_mode: false
dev_mode: false
```

> **🔄 ホットリロード**: `settings.yaml` を保存すると自動反映（再起動不要）。

---

## 🔑 API 設定

### API キーの設定

プロジェクトルートに `.env` を作成：

```env
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
```

### API キーの取得

| サービス | 料金 | 取得先 |
|---|---|---|
| **Groq** | 無料（レート制限あり） | [console.groq.com/keys](https://console.groq.com/keys) |
| **OpenAI** | 有料（事前課金） | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |

OpenAI 課金: [platform.openai.com/account/billing](https://platform.openai.com/account/billing)
料金詳細: [openai.com/pricing](https://openai.com/pricing)

---

## 🎚️ 音声前処理

API に送る前に、録音音声を **音量正規化（Peak+RMS ハイブリッド方式）** で整えます。

| 項目 | 値 |
|---|---|
| 目標 RMS | -20 dBFS（人声に適した一般値） |
| ピーク上限 | -3 dBFS（音割れ防止のヘッドルーム） |
| 処理時間 | numpy のみで <1ms（5 秒音声でも誤差レベル） |

### 効果

- **小声で録音した音声**：API 文字起こしに十分なゲインまで持ち上げる
- **大声・近距離マイク**：ピーク上限で抑え込み、クリッピングによる文字化けを防ぐ
- **完全無音**：そのまま透過（ゲイン発散の防止）

ノイズ対策（ファン音・背景雑音等）は API モデル（Whisper）側が十分に行うため、ローカルでのノイズリダクションは実装していません。

設定ウィンドウの **Advanced → Audio Preprocess** で ON/OFF を切替可能（既定 ON）。

---

## 🔧 トラブルシューティング

### テキストが入力されない

**Windows**:

- 入力先アプリが管理者権限なら、WhisperWin も管理者権限で実行する。
- 他のアプリのホットキーと競合していないか確認。

**macOS**:

- システム設定 → プライバシーとセキュリティ → **アクセシビリティ** に WhisperWin（または Python）を追加。
- 同じく **入力監視** にも追加。

### ホットキーが反応しない

- 他アプリ（IME、ランチャー等）と競合している可能性。設定で別キーへ。
- macOS では **入力監視** 権限を確認。

### マイクが認識されない

- 設定 → Advanced → Input Device で明示的にデバイスを選択。
- macOS では **マイク** 権限を確認。

### "ご視聴ありがとうございました" 等のハルシネーション

- VAD を有効化（既定で ON）。
- VAD Min Silence を短く（例: 300ms）してこまめに無音区間で区切る。

### API 接続エラー

- `.env` の API キーが正しいか確認。
- ネットワーク接続を確認。
- レート制限超過の可能性（Groq の場合）。

### WinError 1314 (Windows のみ)

- Symbolic Link Privilege のエラー。`huggingface_hub` がモデルキャッシュ作成時に失敗する場合に発生。
- ユーザーディレクトリ（既定）以外を使う場合は環境変数 `HF_HOME` を設定して書き込み可能なパスに。

---

## 👨‍💻 開発者向け情報

### プロジェクト構造

```
WhisperWin/
├── src/
│   ├── app.py                    # メインアプリ（HotkeySlot 管理 / キュー処理）
│   ├── main.py                   # エントリポイント
│   ├── config/
│   │   ├── types.py              # 型定義（HotkeySlotConfig, TranscriptionTask 等）
│   │   ├── constants.py          # DEFAULT_CONFIG
│   │   └── config_manager.py     # YAML 読込・マイグレーション・hot-reload
│   ├── core/
│   │   ├── audio_recorder.py     # sounddevice ベースの録音
│   │   ├── audio_preprocess.py   # 音量正規化（Peak+RMS）
│   │   ├── audio_utils.py        # WAV / MP3 変換
│   │   ├── vad.py                # silero-vad ローカル VAD
│   │   ├── groq_transcriber.py   # Groq API クライアント
│   │   ├── openai_transcriber.py # OpenAI API クライアント
│   │   └── input_handler.py      # クリップボード経由のテキスト挿入
│   ├── platform/                 # OS 抽象化層
│   │   ├── base.py               # PlatformAdapter 抽象クラス
│   │   ├── factory.py            # sys.platform で実装を選択
│   │   ├── common/keymap.py      # 共通キー正規化
│   │   ├── macos/adapter.py      # Cmd 系修飾キー、メニューバー挙動
│   │   └── windows/adapter.py    # Ctrl 系修飾キー、トレイ挙動
│   ├── ui/
│   │   ├── overlay.py            # Dynamic Island 風オーバーレイ
│   │   ├── settings_window.py    # 設定ウィンドウ
│   │   ├── styles.py             # macOS 風テーマ
│   │   └── system_tray.py        # システムトレイ / メニューバー
│   └── utils/logger.py
├── docs/
│   ├── CROSS_PLATFORM_UNIFICATION_PLAN.md
│   └── CROSS_PLATFORM_TEST_CHECKLIST.md
├── run.py / run.bat / run.sh     # 起動エントリ
├── settings.yaml                 # 設定ファイル
├── WhisperWin.spec               # PyInstaller spec
├── requirements.txt
├── CHANGELOG.md
└── CLAUDE.md                     # AI 開発者向けガイド
```

### 開発者モード

`settings.yaml` で `dev_mode: true` を設定すると：

- 出力テキストが引用符で囲まれる
- `dev_timing.log` にタイミング情報を記録

### ビルド

```bash
pyinstaller WhisperWin.spec --clean --noconfirm
```

実行ファイルは `dist/WhisperWin/` に生成されます（One-Dir モード）。

### 変更履歴

詳細は [CHANGELOG.md](CHANGELOG.md) を参照。

### コントリビューション

1. Fork して feature ブランチを作成（`git checkout -b feature/xxx`）
2. CHANGELOG.md に変更を記録
3. コミット（`git commit -m 'feat: ...'`）
4. Push（`git push origin feature/xxx`）
5. Pull Request を開く

詳細は [CONTRIBUTING.md](CONTRIBUTING.md) を参照。

---

## 📄 ライセンス

GNU General Public License v3.0 — 詳細は [LICENSE](LICENSE) を参照。

---

## 🙏 謝辞

このプロジェクトは以下のオープンソースを使用しています：

- [Silero VAD](https://github.com/snakers4/silero-vad) — ローカル VAD
- [PySide6](https://wiki.qt.io/Qt_for_Python) — GUI フレームワーク
- [pynput](https://github.com/moses-palmer/pynput) — グローバルキーボード制御
- [sounddevice](https://python-sounddevice.readthedocs.io/) — マイク入力
- [OpenAI API](https://platform.openai.com/) — gpt-4o-transcribe
- [Groq API](https://console.groq.com/) — whisper-large-v3-turbo

---

<div align="center">

**⭐ このプロジェクトが役に立ったら、スターをお願いします**

Made by [Tomato-1101](https://github.com/Tomato-1101)

</div>
