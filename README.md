# WhisperWin

<div align="center">

**高速・高精度な常駐型音声入力ツール**

ホットキーを押すだけで音声入力を開始し、文字起こし結果を瞬時にアクティブウィンドウへ自動入力

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
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
- [API設定](#-api設定)
- [トラブルシューティング](#-トラブルシューティング)
- [開発者向け情報](#-開発者向け情報)

---

## ✨ 特徴

### 🎯 デュアルホットキーで賢く使い分け

**2つのホットキーで異なるバックエンドを使い分けられます！**

- **ホットキー1**: 高精度な有料API（OpenAI）で重要な議事録
- **ホットキー2**: 高速な無料API（Groq）で日常のメモ

各ホットキーに以下を個別設定可能：
- ショートカットキー（`<F2>`, `<Shift_R>`, `<Ctrl>+<Space>` 等）
- トリガーモード（`hold`: 押している間録音 / `toggle`: 押して開始/停止）
- バックエンド（`local`: GPU / `groq`: Groq API / `openai`: OpenAI API）
- APIモデルとプロンプト

### ⚡ その他の主要機能

- **🖥️ Dynamic Island風UI**: macOSライクなモダンオーバーレイ
- **🧠 スマートなVRAM管理**: 使用後に自動メモリ解放
- **🎙️ ハルシネーション対策**: VADフィルタで無音時の誤認識を防止
- **⚙️ GUI設定**: 設定ウィンドウから簡単に設定変更
- **🔄 ホットリロード**: 設定変更が即座に反映（再起動不要）
- **🌙 ダーク/ライトテーマ**: 目に優しいテーマ切替

---

## 💻 必要環境

### 必須

- **Python 3.8以上**
- **ffmpeg**（音声処理用）

### バックエンド別の要件

| バックエンド | GPU要件 | 備考 |
|---|---|---|
| **local** | CUDA対応NVIDIA GPU **必須** | ローカルGPUで処理 |
| **groq** | GPU **不要** | 無料（レート制限あり） |
| **openai** | GPU **不要** | 有料 |

> **💡 Tip**: GPU非搭載PCでも、Groq APIやOpenAI APIを使えば動作します！

---

## 📦 インストール

### 1. リポジトリをクローン

```bash
git clone https://github.com/Tomato-1101/WhisperWin.git
cd WhisperWin
```

### 2. 仮想環境を作成・有効化

```bash
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows PowerShell
```

### 3. 依存関係をインストール

```bash
pip install -r requirements.txt
```

### 4. （ローカルバックエンド使用時のみ）PyTorch with CUDA

```bash
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### 5. ffmpegのインストール確認

```bash
ffmpeg -version
```

---

## 🚀 クイックスタート

### 起動方法

#### 方法1: バッチファイル（推奨）

```bash
run.bat
```

ダブルクリックするだけでアプリが起動します。

#### 方法2: Pythonスクリプト

```bash
python run.py
```

### 基本的な使い方

1. **システムトレイにアイコンが表示される**
2. **ホットキーを押す**（デフォルト: `F2`）
3. **音声入力**
4. **ホットキーを離す（holdモード）またはもう一度押す（toggleモード）**
5. **文字起こし結果がアクティブウィンドウに自動入力される**

### 設定を変更する

- システムトレイアイコンを**クリック**して設定ウィンドウを開く
- 各種パラメータを変更して「**Save Settings**」

---

## 🎯 デュアルホットキー機能

### 概要

WhisperWinは**2つの独立したホットキー**を設定でき、各ホットキーに異なるバックエンド・モデルを割り当てられます。

### 使用例

#### 例1: 速さと精度の使い分け

| スロット | ホットキー | バックエンド | モデル | 用途 |
|---|---|---|---|---|
| **ホットキー1** | `<shift_r>` (hold) | OpenAI | gpt-4o-mini-transcribe | 重要な議事録・高精度 |
| **ホットキー2** | `<f2>` (toggle) | Groq | whisper-large-v3-turbo | 日常のメモ・高速 |

#### 例2: 日本語と英語の切り替え

| スロット | ホットキー | バックエンド | プロンプト | 用途 |
|---|---|---|---|---|
| **ホットキー1** | `<ctrl>+<space>` | OpenAI | `Language: Japanese` | 日本語入力 |
| **ホットキー2** | `<alt>+<space>` | OpenAI | `Language: English` | 英語入力 |

### バックエンドの比較

| バックエンド | GPU | 速度 | 精度 | 料金 | 用途 |
|---|:---:|---|---|---|---|
| **local** | ✅ | 中 | 高 | 無料 | GPUがあればコスパ最高 |
| **groq** | ❌ | **超高速** | 高 | 無料（制限あり） | 日常使い・お試し |
| **openai** | ❌ | 高速 | **最高** | 有料 | 重要な文書・高精度が必要 |

---

## ⚙️ 設定方法

### GUI設定（推奨）

システムトレイアイコンをクリックして設定ウィンドウを開きます。

#### 📍 Generalページ

2つのホットキーを横並びで設定できます：

**Hotkey 1 / Hotkey 2 それぞれで設定:**
- **Shortcut**: ホットキー（例: `<f2>`, `<shift_r>`, `<ctrl>+<space>`）
- **Mode**: `hold` (押している間録音) / `toggle` (押して開始/停止)
- **Backend**: `local` / `groq` / `openai`
- **Model**: APIバックエンドの場合に選択
- **Prompt**: APIバックエンドで使用するヒントテキスト（オプション）

**共通設定:**
- **Language**: 言語コード（`ja`, `en` 等）

#### 📍 Modelページ

ローカルGPU設定（両方のホットキーで共有）：
- **Model Size**: `tiny`, `base`, `small`, `medium`, `large`, `large-v3`
- **Compute Type**: `float16`, `int8_float16`, `int8`

#### 📍 Advancedページ

- **VAD Filter**: 音声区間検出の有効/無効
- **Release Memory Delay**: VRAM解放までの待機時間（秒）

### 設定ファイル（上級者向け）

`settings.yaml` を直接編集することもできます：

```yaml
# グローバル設定（両ホットキー共通）
language: ja
vad_filter: true
vad_min_silence_duration_ms: 500

# ローカルバックエンド設定（共通）
local_backend:
  model_size: large-v3
  compute_type: float16
  release_memory_delay: 300
  condition_on_previous_text: false
  no_speech_threshold: 0.6
  log_prob_threshold: -1.0
  no_speech_prob_cutoff: 0.7
  beam_size: 5
  model_cache_dir: D:/whisper_cache

# ホットキー1 設定
hotkey1:
  hotkey: <shift_r>
  hotkey_mode: hold
  backend: openai
  api_model: gpt-4o-mini-transcribe
  api_prompt: ""

# ホットキー2 設定
hotkey2:
  hotkey: <f2>
  hotkey_mode: toggle
  backend: groq
  api_model: whisper-large-v3-turbo
  api_prompt: ""

# その他
dark_mode: false
dev_mode: false
```

> **🔄 ホットリロード**: `settings.yaml`を保存すると自動的に設定が反映されます（再起動不要）

---

## 🔑 API設定

### APIキーの設定

プロジェクトルートに `.env` ファイルを作成：

```env
# Groq API Key（無料、レート制限あり）
GROQ_API_KEY=gsk_your_api_key_here

# OpenAI API Key（有料）
OPENAI_API_KEY=sk-your_api_key_here
```

### APIキーの取得

| サービス | 料金 | 取得先 | 備考 |
|---|---|---|---|
| **Groq** | 無料（制限あり） | [console.groq.com/keys](https://console.groq.com/keys) | レート制限あり |
| **OpenAI** | **有料** | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) | 事前課金必要 |

### OpenAI APIの課金設定

OpenAI APIを使用するには、事前にクレジットの購入が必要です：

1. [platform.openai.com/account/billing](https://platform.openai.com/account/billing) にアクセス
2. クレジットカードを登録
3. 利用額の上限を設定（推奨）

料金詳細: [openai.com/pricing](https://openai.com/pricing)

---

## 🔧 トラブルシューティング

### テキストが入力されない

**原因**: 管理者権限の問題

**解決策**: 入力先アプリが管理者権限で実行されている場合、WhisperWinも管理者権限で実行してください。

```bash
# PowerShellを管理者として実行
python run.py
```

---

### "ご視聴ありがとうございました" などが出力される（ハルシネーション）

**原因**: 無音を誤認識

**解決策**: `settings.yaml` のハルシネーション対策パラメータを調整

```yaml
local_backend:
  no_speech_threshold: 0.8  # 上げる（デフォルト: 0.6）
  no_speech_prob_cutoff: 0.5  # 下げる（デフォルト: 0.7）
```

---

### モデルロードエラー

**原因**: 初回起動時のモデルダウンロード

**解決策**:
- ネットワーク接続を確認
- 初回は数GBのダウンロードが発生するため待機
- `model_cache_dir` を設定してキャッシュ先を指定

---

### VRAM不足エラー

**原因**: GPUメモリ不足

**解決策**:
1. より小さいモデルを使用（`medium` → `small`）
2. `compute_type` を `int8` に変更
3. Groq/OpenAI APIに切り替え（GPU不要）

---

### WinError 1314 (Symbolic Link Privilege)

**原因**: シンボリックリンク作成権限がない

**解決策**: `model_cache_dir` を明示的に指定

```yaml
local_backend:
  model_cache_dir: D:/whisper_cache
```

---

### ホットキーが反応しない

**原因**: 他のアプリとのホットキー競合

**解決策**: 設定ウィンドウで別のホットキーに変更

---

### API接続エラー

**原因**: APIキー未設定またはネットワークエラー

**解決策**:
1. `.env` ファイルにAPIキーが正しく設定されているか確認
2. ネットワーク接続を確認
3. APIキーが有効か確認（期限切れ等）

---

## 👨‍💻 開発者向け情報

### プロジェクト構造

```
WhisperWin/
├── src/
│   ├── app.py                    # メインアプリケーション（HotkeySlot管理）
│   ├── main.py                   # エントリーポイント
│   ├── config/                   # 設定管理
│   │   ├── types.py              # 型定義（HotkeySlotConfig等）
│   │   ├── constants.py          # 定数（DEFAULT_CONFIG）
│   │   └── config_manager.py     # 設定読み込み・マイグレーション
│   ├── core/                     # コアロジック
│   │   ├── audio_recorder.py     # 音声録音
│   │   ├── transcriber.py        # ローカルGPU文字起こし
│   │   ├── groq_transcriber.py   # Groq API文字起こし
│   │   ├── openai_transcriber.py # OpenAI API文字起こし
│   │   ├── vad.py                # VADフィルタ
│   │   └── input_handler.py      # テキスト入力
│   ├── ui/                       # UI
│   │   ├── overlay.py            # Dynamic Islandオーバーレイ
│   │   ├── settings_window.py    # 設定ウィンドウ（2ホットキー対応）
│   │   ├── styles.py             # macOS風テーマ
│   │   └── system_tray.py        # システムトレイ
│   └── utils/
│       └── logger.py             # ロギング
├── run.py                        # 起動スクリプト
├── run.bat                       # ワンクリック起動
├── settings.yaml                 # 設定ファイル
├── CHANGELOG.md                  # 変更履歴
├── CLAUDE.md                     # AI開発者向けガイド
└── requirements.txt              # 依存関係
```

### 開発者モード

`settings.yaml` で `dev_mode: true` を設定すると：
- 出力テキストが引用符で囲まれる
- `dev_timing.log` に詳細なタイミング情報を記録

### ビルド

```bash
pyinstaller SuperWhisperLike.spec --clean --noconfirm
```

実行ファイルは `dist/SuperWhisperLike/SuperWhisperLike.exe` に生成されます。

### 変更履歴

詳細な変更履歴は [CHANGELOG.md](CHANGELOG.md) を参照してください。

### コントリビューション

貢献を歓迎します！詳細な開発ガイドラインは [CONTRIBUTING.md](CONTRIBUTING.md) を参照してください。

**クイックスタート:**

1. Fork this repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. **CHANGELOG.md に変更を記録**
4. Commit your changes (`git commit -m 'feat: Add amazing feature'`)
5. Push to the branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

詳細なバージョニングルール、コミット規約、リリースプロセスは [CONTRIBUTING.md](CONTRIBUTING.md) を参照してください。

---

## 📄 ライセンス

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

---

## 🙏 謝辞

このプロジェクトは以下のオープンソースプロジェクトを使用しています：

- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) - 高速音声認識エンジン
- [Silero VAD](https://github.com/snakers4/silero-vad) - 音声活性検出
- [PySide6](https://wiki.qt.io/Qt_for_Python) - GUIフレームワーク
- [pynput](https://github.com/moses-palmer/pynput) - キーボード・マウス制御

---

<div align="center">

**⭐ このプロジェクトが役に立ったら、スターをお願いします！**

Made with ❤️ by [Tomato-1101](https://github.com/Tomato-1101)

</div>
