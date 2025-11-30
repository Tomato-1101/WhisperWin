# SuperWhisper-like Tool

faster-whisperを使用した、高速・高精度な常駐型音声入力ツールです。
ホットキーを押すだけで録音を開始し、文字起こし結果をアクティブなウィンドウに自動入力します。

## 特徴

- **⚡ 高速処理**: faster-whisperによる最適化で、従来比5-10倍の高速化
- **🎯 高精度**: large-v3などの最新モデルに対応
- **🧠 スマートなVRAM管理**: 使用後に自動でメモリ解放、必要時に自動プリロード
- **🎙️ ハルシネーション対策**: VADとno_speech確率フィルタで無音時の誤認識を防止
- **⚙️ 完全カスタマイズ可能**: 全パラメータを設定ファイルで調整可能
- **🔄 再起動不要**: `restart` コマンドで設定変更を即座に反映
- **⌨️ グローバルホットキー**: どのアプリを使っていても、設定したキーで起動

## インストール

1. 仮想環境を有効化（推奨）:
   ```bash
   .\venv\Scripts\Activate.ps1
   ```

2. 必要なライブラリをインストールします:
   ```bash
   pip install -r requirements.txt
   ```
   ※ GPUを使用する場合は、PyTorchのCUDA対応版がインストールされていることを確認してください。

3. `ffmpeg` がシステムにインストールされている必要があります。

## 使い方

1. アプリケーションを起動します:
   ```bash
   python src/main.py
   ```
   または
   ```bash
   .\venv\Scripts\python.exe src/main.py
   ```
   初回起動時はモデルのダウンロードが行われるため、時間がかかります。

2. 起動メッセージが表示されたら準備完了です:
   ```
   Ready! Press '<ctrl>+<space>' to hold for recording.
   Type 'restart' to reload the application, or 'quit' to exit.
   ```

3. **ホットキー**（デフォルト: Ctrl+Space）を**押し続けている間**録音されます（holdモード）:
   - 押した瞬間にモデルのロードが開始されます（プリロード）
   - 話している間、キープを押し続けます
   - キーを離すと録音が停止し、文字起こしが開始されます

4. 文字起こし結果がアクティブなウィンドウに自動入力されます。

5. 設定を変更した場合:
   - コンソールに `restart` と入力して Enter
   - アプリが自動的に再起動され、新しい設定が適用されます

## 設定

`settings.yaml` を編集してカスタマイズできます。

### 基本設定

```yaml
# ホットキー設定
hotkey: '<ctrl>+<space>'  # 起動キー (例: '<f2>', '<ctrl>+<space>')
hotkey_mode: 'hold'       # 'toggle' (押して開始/停止) or 'hold' (押している間録音)

# モデル設定
model_size: 'large-v3'    # モデル: tiny, base, small, medium, large, large-v2, large-v3
device: 'cuda'            # 'cuda' (GPU) または 'cpu'
compute_type: 'float16'   # 計算精度: 'float16', 'int8', 'float32'
language: 'ja'            # 言語コード (ja, en など、空白で自動検出)

# VRAM管理
release_memory_delay: 100 # メモリ解放までの秒数 (0で常駐、100秒推奨)
```

### 高度な設定（ハルシネーション対策）

```yaml
# VAD (音声区間検出)
vad_filter: true                      # VADを有効化
vad_min_silence_duration_ms: 500      # 無音とみなす最小時間（ミリ秒）

# ハルシネーション防止
condition_on_previous_text: false     # 前の文脈への依存を無効化（推奨）
no_speech_threshold: 0.6              # 無音判定の閾値 (0.0-1.0)
log_prob_threshold: -1.0              # 確信度の閾値（負の値）
no_speech_prob_cutoff: 0.7            # セグメントの無音確率カットオフ
beam_size: 5                          # ビームサーチのサイズ
```

## コマンド

アプリ起動中に以下のコマンドが使用できます:

- `restart`: アプリを再起動（設定変更を反映）
- `quit`: アプリを終了

## VRAM最適化について

このツールは以下のメモリ管理を行います:

1. **起動時**: モデルは未ロード（VRAM使用量: 最小）
2. **録音開始時**: バックグラウンドでモデルをロード開始（プリロード）
3. **文字起こし時**: モデル使用（VRAM使用量: 最大）
4. **完了後**: 設定時間（例: 100秒）経過後に自動でメモリ解放

連続使用時は再ロードせず、待ち時間なしで高速に動作します。

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

## 技術スタック

- **faster-whisper**: 高速な音声認識エンジン
- **PyTorch**: 深層学習フレームワーク
- **pynput**: グローバルホットキー管理
- **sounddevice**: オーディオ録音
