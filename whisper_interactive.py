#!/usr/bin/env python3
"""
Whisper インタラクティブデモ
対話的に音声ファイルを処理できるデモ
"""

import whisper
import torch
import time
import os
from pathlib import Path


def check_gpu():
    """GPUの利用可能性をチェック"""
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3
        print(f"\n✓ GPU検出: {gpu_name}")
        print(f"  メモリ: {gpu_memory:.2f} GB")
        print(f"  CUDA: {torch.version.cuda}")
        return "cuda"
    else:
        print("\n⚠ GPUが検出されませんでした。CPUモードで実行します。")
        return "cpu"


def select_model():
    """モデルを選択"""
    models = {
        "1": ("tiny", "最小・最速（精度低）"),
        "2": ("base", "小型・高速（推奨）"),
        "3": ("small", "中型・バランス良好"),
        "4": ("medium", "大型・高精度（GPU推奨）"),
        "5": ("large", "最大・最高精度（GPU必須）")
    }

    print("\n使用するモデルを選択してください:")
    for key, (name, desc) in models.items():
        print(f"  {key}. {name:8} - {desc}")

    while True:
        choice = input("\n選択 (1-5, デフォルト=2): ").strip() or "2"
        if choice in models:
            return models[choice][0]
        print("無効な選択です。1-5の数字を入力してください。")


def find_audio_files(directory="samples"):
    """指定ディレクトリから音声ファイルを検索"""
    audio_extensions = {".mp3", ".wav", ".m4a", ".mp4", ".flac", ".ogg", ".wma"}
    path = Path(directory)

    if not path.exists():
        return []

    files = [f for f in path.iterdir() if f.suffix.lower() in audio_extensions]
    return sorted(files)


def select_audio_file():
    """音声ファイルを選択"""
    # samplesディレクトリから検索
    audio_files = find_audio_files("samples")

    if audio_files:
        print("\n検出された音声ファイル:")
        for i, file in enumerate(audio_files, 1):
            size = file.stat().st_size / 1024  # KB
            print(f"  {i}. {file.name} ({size:.1f} KB)")

        print(f"  0. 別のファイルパスを入力")

        while True:
            choice = input("\n選択 (番号を入力): ").strip()
            if choice == "0":
                break
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(audio_files):
                    return str(audio_files[idx])
            except ValueError:
                pass
            print("無効な選択です。")

    # 手動でパス入力
    while True:
        path = input("\n音声ファイルのパスを入力: ").strip()
        if os.path.exists(path):
            return path
        print(f"ファイルが見つかりません: {path}")


def main():
    """メイン処理"""
    print("=" * 60)
    print(" Whisper インタラクティブデモ")
    print("=" * 60)

    # GPU確認
    device = check_gpu()

    # モデル選択
    model_name = select_model()

    # モデルロード
    print(f"\nモデル '{model_name}' をロード中...")
    start = time.time()
    model = whisper.load_model(model_name, device=device)
    print(f"✓ ロード完了 ({time.time() - start:.2f}秒)")

    # メインループ
    while True:
        print("\n" + "=" * 60)

        # 音声ファイル選択
        audio_path = select_audio_file()

        # 言語設定
        print("\n言語を指定しますか？")
        print("  Enter: 自動検出")
        print("  ja: 日本語, en: 英語, zh: 中国語, ko: 韓国語 など")
        language = input("言語コード: ").strip() or None

        # 文字起こし実行
        print(f"\n処理中: {os.path.basename(audio_path)}")
        start = time.time()

        options = {"language": language} if language else {}
        result = model.transcribe(audio_path, **options)

        elapsed = time.time() - start

        # 結果表示
        print(f"\n{'=' * 60}")
        print(f"処理時間: {elapsed:.2f}秒")
        print(f"検出言語: {result['language']}")
        print(f"{'=' * 60}")
        print("\n【文字起こし結果】")
        print(result["text"])
        print(f"\n{'=' * 60}")

        # セグメント情報も表示（オプション）
        show_segments = input("\nセグメント詳細を表示しますか？ (y/N): ").strip().lower()
        if show_segments == 'y':
            print("\n【セグメント詳細】")
            for i, segment in enumerate(result["segments"], 1):
                start_time = segment["start"]
                end_time = segment["end"]
                text = segment["text"]
                print(f"{i}. [{start_time:.2f}s - {end_time:.2f}s] {text}")

        # 継続確認
        continue_choice = input("\n別のファイルを処理しますか？ (Y/n): ").strip().lower()
        if continue_choice == 'n':
            print("\nデモを終了します。")
            break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nデモを中断しました。")
    except Exception as e:
        print(f"\nエラーが発生しました: {e}")
