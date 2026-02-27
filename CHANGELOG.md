# Changelog

WhisperWinの変更履歴を記録するファイルです。

## [Unreleased] - 2026-02-27

### Added
- **Cross-platform 抽象レイヤーを追加**
  - `src/platform/` を新設し、OS差分を `core` から分離
  - `PlatformAdapter` インターフェースと `get_platform_adapter()` ファクトリを追加
  - `windows` / `macos` 向けアダプタ実装を追加

- **入力デバイス選択機能を追加**
  - Settings の Advanced ページでマイク入力デバイスを選択可能
  - `audio_input_device` 設定キーを追加（`default` / デバイスID）
  - 録音開始時に指定デバイスを使用し、失敗時は自動でデフォルトへフォールバック

- **運用ドキュメントの追加**
  - `docs/CROSS_PLATFORM_UNIFICATION_PLAN.md`（統合計画）
  - `docs/CROSS_PLATFORM_TEST_CHECKLIST.md`（検証チェックリスト）
  - `run.sh`（macOS/Linux向け起動スクリプト）

### Changed
- **入力処理を platform 注入方式へ移行**
  - `src/core/input_handler.py` の `sys.platform` 分岐を削除
  - 貼り付け修飾キー（Cmd/Ctrl）を platform アダプタで制御

- **録音設定の動的反映を強化**
  - `settings.yaml` の変更監視で入力デバイス設定の更新を即時適用

- **UI のOS依存ロジックを分離**
  - `src/ui/settings_window.py` のホットキー変換を platform 経由に変更
  - `src/ui/system_tray.py` のアクティベーション判定を platform ポリシー化
  - `src/ui/styles.py` のフォント指定を OS別フォールバック対応に変更

- **アプリ初期化の依存注入を整理**
  - `src/app.py` で platform アダプタを初期化し、
    InputHandler / SettingsWindow / SystemTray / キー正規化に注入

### Technical Details
- **新規追加**
  - `src/platform/base.py`
  - `src/platform/factory.py`
  - `src/platform/common/keymap.py`
  - `src/platform/windows/adapter.py`
  - `src/platform/macos/adapter.py`

- **更新**
  - `src/app.py`
  - `src/core/input_handler.py`
  - `src/ui/settings_window.py`
  - `src/ui/system_tray.py`
  - `src/ui/styles.py`
  - `README.md`

## [Unreleased] - 2026-02-03

### Added
- **起動時プリロード機能の実装**
  - 起動時にVADモデルをバックグラウンドでプリロードし、最初の文字起こしを高速化
  - `preload_on_startup` 設定オプションを追加（デフォルト: true）
  - `app.py` に `_preload_models_async()` を追加

### Fixed
- **VADプリロードのタイミング改善**
  - ホットキースロット初期化後にプリロードを実行するよう調整
  - 起動順序を `setup_state -> start_background_threads -> preload` に整理

### Technical Details
- **src/app.py**
  - `_preload_models_async()` を追加し、設定に応じて非同期プリロードを実行
  - `_preload_vad_model()` を実行ロジック専用に整理
- **src/config/constants.py**
  - `DEFAULT_CONFIG` に `preload_on_startup: true` を追加

## [Unreleased] - 2026-01-30

### Added
- **文字起こしキューイング機能の実装**
  - 文字起こし処理中に新しい録音を開始しても、前タスクを破棄せずキューに追加
  - すべての録音結果を順番に処理して入力
  - `queue.Queue` を使用したスレッドセーフなタスク管理
  - `TranscriptionTask` データクラスを追加

### Changed
- **app.py の文字起こし処理ロジックをキュー方式へ変更**
  - `start_recording()` からキャンセル方式を削除
  - `stop_and_transcribe()` でキュー投入
  - `_start_queue_worker()`, `_queue_processor()`, `_process_transcription_task()` を追加
  - `_handle_transcription_result()` は結果処理専用にし、idle遷移はワーカー管理へ移行

### Technical Details
- **src/config/types.py**
  - `TranscriptionTask` データクラスを追加（audio_data, slot_id, timestamp）
- **src/app.py**
  - `_transcription_queue` / `_queue_worker_running` を追加
  - キュー処理完了時に `idle` へ復帰する制御を追加

## [Unreleased] - 2026-01-15

### Added
- **CONTRIBUTING.md ドキュメント作成**
  - 詳細なバージョニングルール（X=大きな変更、Y=ユーザーが気づく変更、Z=小さな修正）
  - コミットメッセージ規約（type: description形式）
  - 変更記録（CHANGELOG）の運用ルール
  - ブランチ戦略とリリースプロセス
  - プルリクエストのガイドライン
  - プッシュのタイミングとチェックリスト

- **デュアルホットキー機能の実装**
- **2つの独立したホットキー設定**: 固定で2つのホットキースロットを追加
  - 各ホットキーに対して異なるショートカット、モード（hold/toggle）、バックエンド（local/groq/openai）を設定可能
  - APIバックエンド（Groq/OpenAI）の場合、各ホットキーで異なるモデルとプロンプトを指定可能
  - ローカルバックエンドは両方のホットキーで共通の設定を使用（VRAM節約）

- **新しい設定構造**: `settings.yaml` の階層化
  - `hotkey1` / `hotkey2`: 各ホットキーの個別設定
  - `local_backend`: ローカルGPU設定（共通）
  - `language`, `vad_filter` などのグローバル設定

- **自動マイグレーション機能**
  - 旧設定フォーマット（単一ホットキー）を検出し、新形式に自動変換
  - 既存ユーザーの設定を保持しながらアップグレード可能
  - マイグレーション時のログ出力

- **設定UIの刷新**
  - Generalページ: 2つのホットキーを横並びで設定
  - 各ホットキーグループに: ショートカット入力、モード選択、バックエンド選択、API設定
  - Modelページ: ローカル共通設定のみに簡略化
  - API設定の動的表示（バックエンド選択に応じて表示/非表示）

### Changed
- **CLAUDE.md に自動コミットルール追加**
  - AI開発者向けに、機能実装完了時の自動コミットルールを明記
  - コミットのタイミング、必須チェック項目、例外ケースを定義
  - プッシュは手動実行（自動プッシュしない）
  - ユーザーへの報告フォーマットを標準化

- **README.md コントリビューションセクション更新**
  - CONTRIBUTING.md へのリンク追加
  - 開発ガイドラインへのナビゲーション改善

- **app.py の大幅なリファクタリング**
  - `HotkeySlot` データクラスを追加（各スロットの状態管理）
  - `_hotkey_slots` 辞書で複数ホットキーを管理
  - `_local_transcriber` を共有インスタンスとして分離
  - `_active_slot` で現在アクティブなスロットを追跡
  - キーボードリスナーが両方のホットキーを同時監視
  - `start_recording()` にスロットID引数を追加

- **config_manager.py の強化**
  - `_deep_merge()` 関数でネストされた辞書のマージをサポート
  - `_migrate_legacy_config()` メソッドで旧設定を自動変換
  - 深いマージによりデフォルト設定との統合を改善

- **ホットリロード機能の維持**
  - `_apply_config_changes()` が新構造に対応
  - ホットキー設定変更時の自動更新
  - バックエンド変更時のAPI Transcriber再作成
  - ローカル設定変更時のモデルアンロード

### Technical Details
- **types.py**
  - `HotkeySlotConfig` データクラスを追加

- **constants.py**
  - `DEFAULT_CONFIG` を新構造（hotkey1/hotkey2/local_backend）に変更
  - `default_api_models` でバックエンド別のデフォルトモデルを定義

- **settings_window.py**
  - `_create_hotkey_group()` で各スロットのUIを生成
  - `_create_api_settings_widget()` でAPI設定ウィジェットを動的生成
  - `_on_slot_backend_changed()` でバックエンド変更を処理
  - `_load_current_settings()` / `_save_settings()` を新構造に対応

### Fixed
- ホットキー競合時の優先順位（最初に検出されたスロットが優先）
- Hold/Toggle混在時のキーボードリスナー処理

---

## [v2.0.0] - 2026-01-15

### Added
- デュアルホットキースロットとMP3音声サポート
- OpenAIバックエンドとGroqバックエンドのモジュール化
- macOSスタイルの設定UI

### Changed
- プロジェクト構造のリファクタリング
- バックエンドの分離（local/groq/openai）

---

## [Previous Releases]

### [2026-01-05] - LLMプロンプト処理の改善
- LLMプロンプト処理のリファクタリング
- 設定UIの改善

### [2025-12-09] - UI改善とドキュメント更新
- オーバーレイUIの改善
- ホットキー処理の改善
- AI用コメントルールの追加
- README更新

### [2025-12-09] - v2.0.0リリース
- 日本語コメントの追加
- LLM処理ログ表示
- コード整理

### [2025-12-08] - LLM後処理機能
- LLM後処理機能の追加
- GUI設定の追加
- macOSスタイルのUIテーマ
- オーバーレイの改善

### [2025-12-08] - Groqバックエンド統合
- Groq API対応
- VADフィルター統合
- PyInstallerビルド設定更新

### [2025-12-08] - プロジェクト整形
- 全体的なコード整形
- 安定版リリース

### [2025-12-01] - 初期リリース
- プロジェクト名変更（SuperWhisperLike → WhisperWin）
- GNU GPL v3ライセンス追加
- 無音検出のUIフィードバック
- エラーハンドリング改善
- ビルドアーティファクトのクリーンアップ

---

## Notes

### 変更記録のガイドライン
- すべての機能追加、変更、修正を記録する
- 各エントリには簡潔な説明と影響範囲を含める
- 技術的な詳細は "Technical Details" セクションに記載
- ユーザー影響のある変更は目立つように記載

### バージョニング
- メジャーバージョン: 破壊的変更または大規模な機能追加
- マイナーバージョン: 後方互換性のある機能追加
- パッチバージョン: バグ修正とマイナーな改善
