#!/usr/bin/env python3
"""
Whisper GPU Demo
ローカル環境でGPUを使ってWhisperを動かすデモスクリプト
"""

import whisper
import torch
import time
import sys
import os


def check_gpu():
    """GPUの利用可能性をチェック"""
    if torch.cuda.is_available():
        print(f"✓ GPU利用可能: {torch.cuda.get_device_name(0)}")
        print(f"  CUDA Version: {torch.version.cuda}")
        print(f"  GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")
        return "cuda"
    else:
        print("⚠ GPUが利用できません。CPUで実行します。")
        return "cpu"


def load_model(model_name="base", device="cuda"):
    """Whisperモデルをロード"""
    print(f"\nモデル '{model_name}' をロード中...")
    start_time = time.time()
    model = whisper.load_model(model_name, device=device)
    load_time = time.time() - start_time
    print(f"✓ モデルロード完了 ({load_time:.2f}秒)")
    return model


def transcribe_audio(model, audio_path, language=None):
    """音声ファイルを文字起こし"""
    if not os.path.exists(audio_path):
        print(f"エラー: ファイルが見つかりません: {audio_path}")
        return None

    print(f"\n音声ファイルを処理中: {audio_path}")
    start_time = time.time()

    # 文字起こし実行
    if language:
        result = model.transcribe(audio_path, language=language)
    else:
        result = model.transcribe(audio_path)

    process_time = time.time() - start_time

    print(f"✓ 文字起こし完了 ({process_time:.2f}秒)")
    print(f"\n検出言語: {result['language']}")
    print(f"\n--- 文字起こし結果 ---")
    print(result["text"])
    print(f"----------------------\n")

    return result


def main():
    """メイン処理"""
    print("=" * 50)
    print("Whisper GPU デモ")
    print("=" * 50)

    # GPU確認
    device = check_gpu()

    # モデル選択
    # tiny, base, small, medium, large
    # small推奨（精度とスピードのバランスが良い）
    model_name = "base"  # 必要に応じて変更

    # モデルロード
    model = load_model(model_name, device)

    # コマンドライン引数から音声ファイルパスを取得
    if len(sys.argv) > 1:
        audio_path = sys.argv[1]
        language = sys.argv[2] if len(sys.argv) > 2 else None
        transcribe_audio(model, audio_path, language)
    else:
        print("\n使い方:")
        print(f"  python {sys.argv[0]} <音声ファイルパス> [言語コード]")
        print("\n例:")
        print(f"  python {sys.argv[0]} sample.mp3")
        print(f"  python {sys.argv[0]} sample.mp3 ja")
        print("\nサポートされている音声形式: mp3, mp4, wav, m4a, など")
        print("言語コード例: ja (日本語), en (英語), zh (中国語)")
        print("\nsamples/ ディレクトリに音声ファイルを配置してお試しください。")


if __name__ == "__main__":
    main()
