# Cross-Platform Test Checklist

## 1. 事前準備（両OS共通）
- `python -m venv venv`
- Windows: `venv\Scripts\pip install -r requirements.txt`
- macOS: `./venv/bin/pip install -r requirements.txt`
- `.env` に API キーを設定（`OPENAI_API_KEY`, `GROQ_API_KEY`）
- `settings.yaml` が読み込まれる場所に存在することを確認

## 2. 起動確認
- Windows: `python run.py` または `run.bat`
- macOS: `python run.py` または `./run.sh`
- 期待結果:
  - トレイ/メニューバーアイコンが表示される
  - 例外で即時終了しない

## 3. UI表示確認
- トレイ/メニューバーから Settings を開ける
- General/Advanced ページが表示される
- 設定保存後に再読み込みで値が保持される

## 4. 音声入力フロー
- Hold モード:
  - ホットキー押下で録音開始
  - キー解放で録音停止し文字起こし開始
- Toggle モード:
  - 1回目押下で録音開始
  - 2回目押下で録音停止
- 期待結果:
  - オーバーレイが `recording -> transcribing -> idle` で遷移

## 5. APIバックエンド
- Slot1: OpenAI
- Slot2: Groq
- 期待結果:
  - 両スロットで文字起こし結果が挿入される
  - APIキー不足時は警告表示される

## 6. VAD（ローカル）
- 無音音声で実行し、API呼び出しがスキップされること
- 発話音声ではAPI呼び出しされること
- 期待結果:
  - ログに `VADチェック` が出る
  - デバイス選択が適切（macOS Apple Silicon は `mps` 優先）

## 7. OS固有権限
- macOS:
  - 入力監視/アクセシビリティ許可ありでホットキー動作
- Windows:
  - 権限不足時でも起動し、必要時にガイドが表示される
