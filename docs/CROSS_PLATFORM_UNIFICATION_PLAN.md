# WhisperWin Cross-Platform Unified Refactor Plan

## 1. 目的
- 1つのリポジトリ、1つのメインブランチ、同一コードベースで **Windows / macOS の両方を起動・運用可能** にする。
- 実装を `core`（共通） + `platform`（OS別）に分離し、今後の変更を片側修正だけで済む構造にする。
- ローカル計算は **VADのみ残す**（Apple Silicon/MPS・CUDA・CPUの最適フォールバックを維持）。

## 2. 現状分析（Windows と macOS の差分）
### 2.1 入力・ホットキー
- ホットキー監視は `pynput` に依存しているが、実装が `src/app.py` に密結合している。
- 修飾キー判定（左右キー、AltGr、Meta/Cmd）がUI層と混在し、OS差分吸収層がない。
- テキスト挿入は `src/core/input_handler.py` で `sys.platform` 分岐（`Cmd+V`/`Ctrl+V`）を直書き。

### 2.2 UI（設定、メニュー、オーバーレイ）
- UI本体は PySide6 で共通化可能だが、フォントとトレイ挙動にOS差分がある。
- 既存フォント `SF Pro Text` が環境により欠落し、macOSでフォールバック警告が出る。
- トレイクリック挙動は macOS/Windows でイベント差があり、規約化が必要。

### 2.3 起動・配布
- `run.bat` は Windows 寄り、macOS向けの同等起動導線が不足。
- PyInstaller spec は単一で運用されているが、アイコン形式や hidden import はOS差分がある。

### 2.4 設定・ドキュメント
- READMEに過去の `local` backend 記述が残っており、現実装（API + VAD）と不整合。
- 設定キーは新旧互換移行を含むため、移行仕様を文書化して固定する必要がある。

## 3. 目標アーキテクチャ（core + platform）
```text
src/
  core/                       # OS非依存ロジック
    app_controller.py         # 録音/キュー/文字起こし状態遷移
    hotkey_engine.py          # ホットキー一致判定（純粋ロジック）
    transcription/            # openai/groq + vad
    audio/                    # recorder/util
  platform/
    base.py                   # 抽象インターフェース定義
    factory.py                # 実行OSから実装を選択
    common/
      pynput_listener.py      # pynput利用の共通基盤
    macos/
      input_injector.py       # Cmd+V, mac権限制約メッセージ
      keymap.py               # mac修飾キー正規化
      tray_policy.py          # macトレイ挙動ポリシー
    windows/
      input_injector.py       # Ctrl+V
      keymap.py               # win修飾キー正規化
      tray_policy.py          # winトレイ挙動ポリシー
  ui/                         # 画面部品（共通）
```

## 4. Git構成計画（単一ブランチ運用）
### 4.1 方針
- 本番運用は `main` 一本化（Windows/macOS 共通コード）。
- 開発時のみ短命ブランチ（`codex/*`）を作成し、検証後に `main` へマージ。
- OS別ブランチ（`macOS` 専用、`windows` 専用）は廃止。

### 4.2 履歴運用
- コミット単位は「壊れない最小差分」で分割:
  1. platform抽象導入
  2. app連携置換
  3. UI/設定調整
  4. docs/packaging
- リリースはタグ運用（例: `v2.1.0`）。

### 4.3 初期化・確認コマンド
- 既存repoの再確認: `git init`
- 状態確認: `git status -sb`
- 現在ブランチ確認: `git branch --show-current`

## 5. 実行手順（細分化）
## Phase 0: ベースライン固定
1. 現在の起動可否を Windows/macOS それぞれで確認（ログ保存）。
2. 設定ファイルキー (`hotkey1/2`, `preload_on_startup`, `vad_*`) を固定。
3. 既知課題（権限警告・フォント警告）を課題リストに記録。

完了条件:
- 既存挙動を再現できる起動手順が定義済み。

## Phase 1: platform 抽象層導入
1. `src/platform/base.py` に `InputInjector`, `HotkeyListener`, `PlatformInfo` インターフェースを定義。
2. `src/platform/factory.py` で OS 判定して実装を返す。
3. `src/platform/macos/*` と `src/platform/windows/*` に最小実装を追加。
4. 既存 `core/input_handler.py` は移行ラッパー化（後方互換）。

完了条件:
- `sys.platform` 直書き箇所が app/core から消え、platform層に集約。

## Phase 2: app/controller 分離
1. `src/app.py` のホットキー監視とキー正規化ロジックを `core/hotkey_engine.py` へ分離。
2. `app` は「状態遷移と依存注入」のみ担当に縮小。
3. 文字起こしキュー処理は現仕様維持（直列処理、キャンセルなし）。

完了条件:
- `app.py` の責務が orchestration のみに限定される。

## Phase 3: UI整合（メインUI/設定/録音中オーバーレイ）
1. SystemTray のクリックポリシーを platform policy 経由で統一。
2. SettingsWindow のキー記録ロジックを platform keymap に委譲。
3. Overlay 表示状態（idle/recording/transcribing）を共通状態機械として保証。
4. フォントは OS別優先順フォールバックに変更（missing warning削減）。

完了条件:
- 設定ウィンドウ、メニュー経由UI、音声入力時オーバーレイが両OSで同一操作フロー。

## Phase 4: VAD最適化維持（ローカル処理）
1. VADは `core` に残し、`mps -> cuda -> cpu` フォールバックを維持。
2. 起動時プリロード（`preload_on_startup`）は維持。
3. API経路（OpenAI/Groq）への接続は変更しない。

完了条件:
- VADのみローカル計算、ほかはAPI処理の現行仕様を保持。

## Phase 5: 起動/配布/ドキュメント統一
1. 共通起動入口を `run.py` に固定。
2. 補助スクリプトは OS別に整理（`run.bat`, `run.sh`）。
3. README を現仕様へ更新（local backend説明の削除、権限設定追記）。
4. spec のOS差分を明示化（hidden import, icon, bundle設定）。

完了条件:
- 新規ユーザーが同一手順書で Windows/macOS の起動に到達できる。

## Phase 6: 検証
1. 起動確認: メニューバー/トレイアイコン表示。
2. UI確認: 設定画面表示、項目保存、再読込反映。
3. 録音確認: hold/toggle の両モード。
4. オーバーレイ確認: recording/transcribing 表示遷移。
5. VAD確認: 無音でAPI呼び出しがスキップされること。
6. API確認: OpenAI/Groq 各スロットで文字起こしできること。

完了条件:
- Windows/macOS で同一設定ファイル・同一コードにて主要機能がパス。

## 6. 変更対象ファイル（予定）
- 新規追加:
  - `src/platform/base.py`
  - `src/platform/factory.py`
  - `src/platform/macos/*.py`
  - `src/platform/windows/*.py`
  - `src/core/hotkey_engine.py`
  - `docs/CROSS_PLATFORM_TEST_CHECKLIST.md`
- 既存更新:
  - `src/app.py`
  - `src/core/input_handler.py`（互換ラッパー化）
  - `src/ui/settings_window.py`
  - `src/ui/system_tray.py`
  - `src/ui/styles.py`
  - `README.md`
  - `WhisperWin.spec`
  - `requirements.txt`

## 7. リスクと対策
- 権限差分（macOS入力監視/アクセシビリティ）:
  - 起動時に明示メッセージを表示し、チェックリストに組み込む。
- pynput OS実装差分:
  - platform keymap に分離し、回帰テスト対象を左右修飾キーに限定して固定。
- 既存ユーザー設定との互換:
  - `ConfigManager` で旧キーのマイグレーションを継続。

## 8. 実行順序（今回の作業）
1. この計画書を基準として実装開始。
2. `platform` 抽象層の導入と `app.py` 接続置換を先行実施。
3. UI（設定/メニュー/オーバーレイ）の platform 依存点を分離。
4. README と起動手順を更新。
5. 最後に macOS で動作確認し、Windows側手順も同じ構成で成立する状態にする。
