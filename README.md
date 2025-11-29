# Whisper GPU デモ

OpenAI Whisperをローカル環境でGPUを使って動かすシンプルなデモプロジェクトです。

## 📋 必要な環境

### ハードウェア
- **GPU推奨**: NVIDIA GPU (CUDA対応)
  - GTX 1060 以上推奨
  - VRAM 4GB以上 (base/smallモデル)
  - VRAM 8GB以上 (medium/largeモデル)
- **CPU**: GPUがなくても動作しますが、処理速度が遅くなります

### ソフトウェア（Windows）
- Python 3.8 - 3.11
- CUDA Toolkit 11.8 または 12.x (NVIDIA GPUを使用する場合)
- ffmpeg

## 🚀 セットアップ手順（Windows）

### 1. Python環境の準備

仮想環境を作成して有効化:
```bash
# 仮想環境作成
python -m venv venv

# 仮想環境有効化（PowerShell）
.\venv\Scripts\Activate.ps1

# または（コマンドプロンプト）
.\venv\Scripts\activate.bat
```

### 2. PyTorchのインストール（GPU対応）

**NVIDIA GPU使用の場合:**

公式サイトで確認: https://pytorch.org/

```bash
# CUDA 12.x の場合
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# CUDA 11.8 の場合
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

**CPU版の場合:**
```bash
pip install torch torchvision torchaudio
```

### 3. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 4. ffmpegのインストール

**方法1: Chocolateyを使用（推奨）**
```bash
choco install ffmpeg
```

**方法2: 手動インストール**
1. https://ffmpeg.org/download.html からダウンロード
2. 解凍してパスを通す
3. `ffmpeg -version` で確認

**方法3: pip経由（簡易）**
```bash
pip install ffmpeg-python
```

### 5. GPUが認識されているか確認

```python
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
```

✓ `CUDA available: True` と表示されればGPUが使えます！

## 📝 使い方

### 基本的な使い方

```bash
# 音声ファイルを文字起こし
python whisper_demo.py samples/your_audio.mp3

# 言語を指定する場合
python whisper_demo.py samples/your_audio.mp3 ja
```

### インタラクティブモード

```bash
python whisper_interactive.py
```

対話的にモデルやファイルを選択できます：
- モデルサイズの選択
- 音声ファイルの選択
- 言語設定
- セグメント詳細表示

## 🎯 モデルサイズの選択

| モデル | サイズ | VRAM | 速度 | 精度 | 用途 |
|--------|--------|------|------|------|------|
| tiny   | 39M    | ~1GB | 最速 | 低   | テスト用 |
| base   | 74M    | ~1GB | 速い | 中   | 日常使用（推奨） |
| small  | 244M   | ~2GB | 普通 | 良   | バランス重視 |
| medium | 769M   | ~5GB | 遅い | 高   | 高精度重視 |
| large  | 1550M  | ~10GB| 最遅 | 最高 | 最高精度 |

**初めての方は `base` または `small` をおすすめします。**

## 🎵 対応音声形式

- MP3
- WAV
- M4A
- MP4 (音声トラック)
- FLAC
- OGG
- WMA

## 💡 使用例

### 例1: YouTubeの音声を文字起こし

1. 動画をダウンロード（yt-dlpなど）
2. samplesフォルダに配置
3. デモスクリプトで処理

```bash
# yt-dlpで音声のみダウンロード
yt-dlp -x --audio-format mp3 -o "samples/%(title)s.%(ext)s" [URL]

# Whisperで文字起こし
python whisper_demo.py samples/downloaded_video.mp3 ja
```

### 例2: 会議の録音を文字起こし

```bash
python whisper_interactive.py
# モデルで "small" を選択
# 録音ファイルを選択
# 日本語を指定
```

### 例3: 複数ファイルを一括処理

バッチスクリプトを作成:
```bash
# process_all.bat
@echo off
for %%f in (samples\*.mp3) do (
    echo Processing %%f
    python whisper_demo.py "%%f" ja
)
```

## ⚙️ トラブルシューティング

### GPUが認識されない

1. CUDA Toolkitがインストールされているか確認
2. PyTorchがCUDA版か確認:
   ```python
   import torch
   print(torch.__version__)  # +cu118 や +cu121 が含まれているはず
   ```
3. NVIDIAドライバーを最新に更新

### メモリ不足エラー

- より小さいモデル（tiny/base）を使用
- 音声ファイルを短く分割
- 他のアプリケーションを終了

### ffmpegエラー

```bash
# ffmpegのパスを確認
where ffmpeg

# 環境変数に追加されているか確認
```

### 精度が低い

- より大きいモデル（medium/large）を試す
- 言語を明示的に指定（例: `ja`）
- 音声品質を確認（ノイズ、音量など）

## 📚 参考リンク

- [OpenAI Whisper GitHub](https://github.com/openai/whisper)
- [PyTorch 公式サイト](https://pytorch.org/)
- [CUDA Toolkit ダウンロード](https://developer.nvidia.com/cuda-downloads)

## 🔧 カスタマイズ

### デフォルトモデルを変更

`whisper_demo.py` の21行目:
```python
model_name = "base"  # ← ここを変更
```

### GPU/CPUを強制指定

```python
device = "cuda"  # または "cpu"
```

### より詳細なオプション

```python
result = model.transcribe(
    audio_path,
    language="ja",
    task="transcribe",  # または "translate"（英語に翻訳）
    temperature=0.0,
    best_of=5,
    beam_size=5
)
```

## 📄 ライセンス

このデモプロジェクトはMITライセンスです。
Whisper自体はOpenAIによるMITライセンスです。

## 🤝 貢献

改善案やバグ報告は大歓迎です！

---

**Happy Transcribing! 🎤→📝**
