# コントリビューションガイド

WhisperWinへの貢献に興味を持っていただき、ありがとうございます！

このドキュメントでは、開発フロー、Git運用ルール、コミット規約について説明します。

---

## 📋 目次

- [開発環境のセットアップ](#開発環境のセットアップ)
- [開発フロー](#開発フロー)
- [バージョニングルール](#バージョニングルール)
- [コミットメッセージ規約](#コミットメッセージ規約)
- [変更記録（CHANGELOG）](#変更記録changelog)
- [ブランチ戦略](#ブランチ戦略)
- [リリースプロセス](#リリースプロセス)
- [プルリクエスト](#プルリクエスト)
- [コードスタイル](#コードスタイル)

---

## 開発環境のセットアップ

### 1. リポジトリをフォーク＆クローン

```bash
git clone https://github.com/YOUR_USERNAME/WhisperWin.git
cd WhisperWin
```

### 2. 仮想環境を作成

```bash
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows PowerShell
```

### 3. 依存関係をインストール

```bash
pip install -r requirements.txt

# ローカルGPU使用の場合
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### 4. 動作確認

```bash
python run.py
```

---

## 開発フロー

### 基本的な開発サイクル

1. **機能追加・バグ修正**
   - コードを変更
   - 動作確認（手動テスト）
   - CHANGELOG.md に変更を記録

2. **コミット**
   - ステージング: `git add <files>`
   - コミット: `git commit -m "type: description"`

3. **プッシュ**
   - ローカル完結の作業: 自由なタイミングでプッシュ
   - 機能完成時: `git push origin <branch>`

4. **プルリクエスト**
   - GitHub上でPRを作成
   - レビュー後にマージ

---

## バージョニングルール

WhisperWinは **Semantic Versioning (vX.Y.Z)** を採用しています。

### バージョン番号の意味

| 番号 | 名称 | いつ上げるか | 例 |
|------|------|------------|-----|
| **X** (Major) | メジャーバージョン | **大きな新機能**を追加したとき<br>**全体的な構成**が変わったとき<br>**破壊的変更**があるとき | デュアルホットキー機能追加<br>設定ファイル構造の大幅変更 |
| **Y** (Minor) | マイナーバージョン | **ユーザーが気づく変更**をしたとき<br>後方互換性のある機能追加 | 新しいAPIバックエンド追加<br>UI改善<br>新しい設定項目追加 |
| **Z** (Patch) | パッチバージョン | **小さな修正**<br>バグ修正<br>**ユーザーが気づかない内部変更** | タイポ修正<br>軽微なバグ修正<br>依存関係の更新<br>パフォーマンス最適化 |

### 具体例

#### X (Major) を上げる場合
- デュアルホットキー機能の追加（v1.5.2 → v2.0.0）
- 設定ファイルのフォーマットを完全に変更（旧形式が使えなくなる）
- アプリ全体のアーキテクチャ刷新

#### Y (Minor) を上げる場合
- Cerebras APIバックエンドを追加（v2.0.0 → v2.1.0）
- 設定UIに新しいタブを追加（v2.1.0 → v2.2.0）
- VADフィルターの改善（ユーザーが精度向上を体感できる）

#### Z (Patch) を上げる場合
- README.mdのタイポ修正（v2.1.0 → v2.1.1）
- ログメッセージの改善（v2.1.1 → v2.1.2）
- 依存関係のバージョン更新（v2.1.2 → v2.1.3）
- 内部リファクタリング（動作は変わらない）

### バージョンアップのタイミング

- **リリース時にのみバージョンを上げる**
- 開発中は `CHANGELOG.md` の `[Unreleased]` セクションに変更を記録
- リリース準備ができたら、`[Unreleased]` を `[vX.Y.Z]` に変更

---

## コミットメッセージ規約

### 基本フォーマット

```
<type>: <description>

[optional body]

[optional footer]
```

### Type（必須）

| Type | 説明 | 例 |
|------|------|-----|
| `feat` | 新機能追加 | `feat: Add Cerebras API backend support` |
| `fix` | バグ修正 | `fix: Prevent hallucination in silent audio` |
| `docs` | ドキュメント変更のみ | `docs: Update installation guide` |
| `style` | コードスタイル変更（動作に影響なし） | `style: Format code with black` |
| `refactor` | リファクタリング | `refactor: Simplify hotkey listener logic` |
| `perf` | パフォーマンス改善 | `perf: Reduce VRAM usage by 20%` |
| `test` | テスト追加・修正 | `test: Add unit tests for VAD filter` |
| `chore` | ビルド・設定変更 | `chore: bump version to v2.1.0` |

### Description（必須）

- **短く簡潔に**（50文字以内推奨）
- **命令形**で書く（"Add" not "Added" or "Adding"）
- **最初の文字は大文字**
- **末尾にピリオド不要**

### 良い例

```
feat: Add dual hotkey slots support
fix: Resolve VRAM leak in transcriber
docs: Add troubleshooting section to README
refactor: Extract API transcriber factory method
chore: Update dependencies to latest versions
```

### 悪い例

```
added new feature  # typeがない、過去形、小文字始まり
Fix bug.  # 説明が不十分、ピリオド不要
update  # typeと説明が不明確
```

### Body（任意）

詳細な説明が必要な場合に記述：

```
feat: Add dual hotkey slots support

- Each hotkey can use different backend (local/groq/openai)
- Shared local transcriber for VRAM efficiency
- Auto-migration from legacy single-hotkey format
```

### Footer（任意）

関連issue、破壊的変更の記述：

```
fix: Resolve settings file corruption

Fixes #123
Closes #124
```

破壊的変更の場合：

```
feat: Restructure settings.yaml format

BREAKING CHANGE: Old settings.yaml format is no longer supported.
Auto-migration is provided for backward compatibility.
```

---

## 変更記録（CHANGELOG）

### ルール

**すべてのコード変更は CHANGELOG.md に記録必須**

### 記録のタイミング

- ✅ 機能追加・変更・修正を実装した**直後**
- ✅ **コミット前**に変更内容をまとめる
- ✅ プルリクエスト作成時

### CHANGELOG.md の更新手順

#### 1. Unreleased セクションに追加

変更内容を適切なカテゴリに追加：

```markdown
## [Unreleased]

### Added
- デュアルホットキー機能の実装
- Cerebras APIバックエンド対応

### Changed
- 設定UIのレイアウト改善
- VADフィルターのデフォルト値変更

### Fixed
- 無音時のハルシネーション問題を修正
- メモリリーク修正

### Technical Details
- **types.py**: HotkeySlotConfig データクラスを追加
- **app.py**: _hotkey_slots 辞書で複数ホットキーを管理
```

#### 2. カテゴリ

| カテゴリ | 内容 |
|---------|------|
| `Added` | 新機能 |
| `Changed` | 既存機能の変更 |
| `Deprecated` | 非推奨になった機能 |
| `Removed` | 削除された機能 |
| `Fixed` | バグ修正 |
| `Security` | セキュリティ修正 |
| `Technical Details` | 技術的な詳細（ファイル名、クラス名など） |

#### 3. リリース時

バージョン決定後、`[Unreleased]` を `[vX.Y.Z] - YYYY-MM-DD` に変更：

```markdown
## [v2.1.0] - 2026-01-20

### Added
- Cerebras APIバックエンド対応
```

---

## ブランチ戦略

### メインブランチ

- **main**: 常にリリース可能な状態を保つ
- 直接コミットは避け、プルリクエスト経由でマージ

### フィーチャーブランチ

新機能・バグ修正は専用ブランチで作業：

```bash
# 新しいブランチを作成
git checkout -b feature/add-cerebras-backend
git checkout -b fix/memory-leak

# 作業後
git add .
git commit -m "feat: Add Cerebras API backend"
git push origin feature/add-cerebras-backend
```

### ブランチ命名規則

| プレフィックス | 用途 | 例 |
|--------------|------|-----|
| `feature/` | 新機能 | `feature/dual-hotkeys` |
| `fix/` | バグ修正 | `fix/vram-leak` |
| `docs/` | ドキュメント | `docs/update-readme` |
| `refactor/` | リファクタリング | `refactor/config-manager` |
| `chore/` | 雑務 | `chore/update-deps` |

### ホットフィックス

緊急のバグ修正：

```bash
git checkout -b hotfix/critical-crash main
# 修正作業
git commit -m "fix: Resolve critical crash on startup"
# PRを作成してmainにマージ
# マージ後、即座にリリース（パッチバージョンを上げる）
```

---

## リリースプロセス

### 手順

#### 1. CHANGELOG.md の確認

`[Unreleased]` セクションのすべての変更を確認。

#### 2. バージョン番号の決定

[バージョニングルール](#バージョニングルール)に従って決定。

#### 3. CHANGELOG.md の更新

```markdown
## [v2.1.0] - 2026-01-20

### Added
- Cerebras APIバックエンド対応
```

#### 4. コミット

```bash
git add CHANGELOG.md
git commit -m "chore: bump version to v2.1.0"
```

#### 5. タグ作成

```bash
git tag v2.1.0
```

タグにメッセージを付ける場合：

```bash
git tag -a v2.1.0 -m "Release v2.1.0: Add Cerebras API backend"
```

#### 6. プッシュ

```bash
# コミットをプッシュ
git push origin main

# タグをプッシュ
git push origin v2.1.0

# または、すべてのタグをプッシュ
git push origin --tags
```

#### 7. GitHub Release 作成（推奨）

GitHub上でリリースノートを作成：
- Release title: `v2.1.0`
- Description: CHANGELOG.md の該当セクションをコピー
- バイナリがあれば添付

---

## プルリクエスト

### PRを作成する前に

- [ ] コードが正常に動作することを手動テスト
- [ ] CHANGELOG.md に変更を記録
- [ ] コミットメッセージが規約に従っている

### PRのタイトル

コミットメッセージと同じ形式：

```
feat: Add Cerebras API backend
fix: Resolve memory leak in transcriber
```

### PRの説明テンプレート

```markdown
## 概要
<!-- この変更の目的を簡潔に説明 -->

## 変更内容
<!-- 主な変更点をリスト -->
-
-

## 影響範囲
<!-- 影響を受けるファイル、機能 -->

## テスト方法
<!-- 動作確認方法 -->
1.
2.

## スクリーンショット（UI変更の場合）
<!-- 変更前後のスクリーンショット -->

## チェックリスト
- [ ] コードが正常に動作することを確認
- [ ] CHANGELOG.md を更新
- [ ] 必要に応じてドキュメントを更新
```

---

## コードスタイル

### Python

- **Python 3.8+**
- **インデント**: 4スペース
- **命名規則**:
  - 変数・関数: `snake_case`
  - クラス: `PascalCase`
  - 定数: `UPPER_SNAKE_CASE`
- **型ヒント**: 可能な限り使用
- **docstring**: すべてのクラス・関数に日本語で記述

### コメント

- **言語**: 日本語
- **内容**: 「何をするか」ではなく「なぜそうするか」を重視
- 詳細は [CLAUDE.md のコメントルール](CLAUDE.md#コメントルール重要) を参照

### フォーマット

将来的にフォーマッターを導入予定（black, isort等）。

---

## プッシュのタイミング

### いつプッシュすべきか

| 状況 | プッシュタイミング |
|------|----------------|
| **個人開発・実験** | 自由（1日の終わりなど） |
| **機能完成時** | 即座にプッシュ |
| **バグ修正完了時** | 即座にプッシュ |
| **リリース準備** | タグ作成後に必ずプッシュ |
| **作業途中** | 任意（バックアップ目的でプッシュ可） |

### プッシュ前のチェックリスト

- [ ] コードが動作することを確認
- [ ] CHANGELOG.md を更新済み
- [ ] コミットメッセージが規約に準拠
- [ ] 機密情報（APIキー等）が含まれていない

---

## 質問・問題報告

- **バグ報告**: [GitHub Issues](https://github.com/Tomato-1101/WhisperWin/issues) で報告
- **機能リクエスト**: Issue で提案
- **質問**: Discussionsまたは Issue

---

## ライセンス

コントリビューションは GPL-3.0 ライセンスの下で公開されます。

---

**ありがとうございます！あなたの貢献がWhisperWinをより良いものにします。**
