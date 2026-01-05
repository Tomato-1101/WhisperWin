"""
LLMテキスト後処理モジュール

Groq/Cerebrasの高速推論APIを使用して、
音声認識結果をLLMで整形・変換する機能を提供する。
フィラー除去、数式変換、カタカナ英語変換などに対応。
"""

import os
from pathlib import Path
from typing import Optional

from ..utils.logger import get_logger

logger = get_logger(__name__)

# SDK利用可否フラグ（遅延インポート）
_groq_available: bool = False
_cerebras_available: bool = False

# Groq SDKのインポート試行
try:
    from groq import Groq
    _groq_available = True
except ImportError:
    Groq = None

# Cerebras SDKのインポート試行
try:
    from cerebras.cloud.sdk import Cerebras
    _cerebras_available = True
except ImportError:
    Cerebras = None

# プロンプトファイルのパス（プロジェクトルート）
PROMPT_FILE_PATH = Path(__file__).parent.parent.parent / "prompt.xml"


class TextProcessor:
    """
    LLMベースのテキスト後処理クラス。
    
    Groq/CerebrasのAPIを使用して、文字起こし結果を整形する。
    フィラー除去、数式変換、言い直し修正などを自動で行う。
    プロンプトはprompt.xmlファイルから読み込み、変更時は自動リロード。
    
    Attributes:
        provider: 使用するLLMプロバイダー（'groq' or 'cerebras'）
        model: 使用するモデル名
        system_prompt: システムプロンプト（prompt.xmlから読み込み）
        timeout: APIタイムアウト（秒）
        fallback_on_error: エラー時に元テキストを返すかどうか
        last_api_time: 最後のAPI呼び出し時間（ミリ秒）
    """

    def __init__(
        self,
        provider: str = "groq",
        model: str = "llama-3.3-70b-versatile",
        timeout: float = 5.0,
        fallback_on_error: bool = True,
    ) -> None:
        """
        TextProcessorを初期化する。
        
        Args:
            provider: LLMプロバイダー（'groq' or 'cerebras'）
            model: モデル名
            timeout: APIタイムアウト（秒）
            fallback_on_error: エラー時に元テキストを返す場合True
        """
        self.provider = provider
        self.model = model
        self.timeout = timeout
        self.fallback_on_error = fallback_on_error
        
        # プロンプトファイルの更新時刻を追跡（ホットリロード用）
        self._prompt_mtime: Optional[float] = None
        
        # prompt.xmlからプロンプトを読み込む
        self.system_prompt = self._load_prompt_from_file()

        # 各プロバイダーのクライアント（遅延初期化）
        self._groq_client: Optional[Groq] = None
        self._cerebras_client: Optional[Cerebras] = None

    def _load_prompt_from_file(self) -> str:
        """
        prompt.xmlファイルからプロンプトを読み込む。
        
        Returns:
            プロンプト文字列。ファイルが存在しない場合はデフォルトプロンプト。
        """
        try:
            if PROMPT_FILE_PATH.exists():
                # ファイル更新時刻を記録
                self._prompt_mtime = PROMPT_FILE_PATH.stat().st_mtime
                content = PROMPT_FILE_PATH.read_text(encoding="utf-8")
                logger.debug(f"プロンプトを読み込みました: {PROMPT_FILE_PATH}")
                return content
            else:
                logger.warning(f"prompt.xmlが見つかりません: {PROMPT_FILE_PATH}")
                return self._get_default_prompt()
        except Exception as e:
            logger.error(f"prompt.xml読み込みエラー: {e}")
            return self._get_default_prompt()

    def _reload_prompt_if_changed(self) -> None:
        """プロンプトファイルが変更されていれば再読み込みする。"""
        try:
            if PROMPT_FILE_PATH.exists():
                current_mtime = PROMPT_FILE_PATH.stat().st_mtime
                if self._prompt_mtime is None or current_mtime > self._prompt_mtime:
                    logger.info("prompt.xmlが変更されました。再読み込み中...")
                    self.system_prompt = self._load_prompt_from_file()
        except Exception as e:
            logger.error(f"プロンプト更新確認エラー: {e}")

    def _get_default_prompt(self) -> str:
        """デフォルトのプロンプトを返す。"""
        return (
            "音声認識結果を適切に変換してください。"
            "入力は<transcription>タグで囲まれています。"
            "変換後のテキストのみ返してください。"
        )

    def is_available(self) -> bool:
        """
        設定されたプロバイダーが利用可能かを確認する。
        
        Returns:
            SDKがインストール済みでAPIキーが設定されている場合True
        """
        if self.provider == "groq":
            return _groq_available and bool(os.environ.get("GROQ_API_KEY"))
        elif self.provider == "cerebras":
            return _cerebras_available and bool(os.environ.get("CEREBRAS_API_KEY"))
        return False

    def _get_groq_client(self) -> "Groq":
        """Groqクライアントを取得または作成する。"""
        if self._groq_client is None:
            api_key = os.environ.get("GROQ_API_KEY")
            if not api_key:
                raise RuntimeError("GROQ_API_KEY が設定されていません")
            self._groq_client = Groq(api_key=api_key, timeout=self.timeout)
        return self._groq_client

    def _get_cerebras_client(self) -> "Cerebras":
        """Cerebrasクライアントを取得または作成する。"""
        if self._cerebras_client is None:
            api_key = os.environ.get("CEREBRAS_API_KEY")
            if not api_key:
                raise RuntimeError("CEREBRAS_API_KEY が設定されていません")
            # Cerebrasクライアントはコンストラクタでtimeoutをサポートしない
            self._cerebras_client = Cerebras(api_key=api_key)
        return self._cerebras_client

    def process(self, text: str) -> str:
        """
        テキストをLLMで処理する。
        
        Args:
            text: 入力テキスト（文字起こし結果）
        
        Returns:
            変換後テキスト。エラー時はfallback_on_errorに応じて元テキストまたは空文字
        """
        # プロンプトファイルが変更されていれば再読み込み
        self._reload_prompt_if_changed()
        
        # タイミング情報をリセット
        self.last_api_time = 0
        
        if not text or not text.strip():
            return text

        if not self.is_available():
            logger.warning(f"LLMプロバイダー {self.provider} が利用できません")
            return text if self.fallback_on_error else ""

        try:
            if self.provider == "groq":
                return self._process_with_groq(text)
            elif self.provider == "cerebras":
                return self._process_with_cerebras(text)
            else:
                logger.error(f"不明なプロバイダー: {self.provider}")
                return text if self.fallback_on_error else ""
        except Exception as e:
            logger.error(f"LLM処理エラー: {e}")
            return text if self.fallback_on_error else ""

    def _build_messages(self, text: str) -> list:
        """
        APIリクエスト用のメッセージリストを構築する。
        
        入力テキストをXMLタグでマークして、
        プロンプトインジェクションを防止する。
        
        Args:
            text: 入力テキスト
            
        Returns:
            system/userメッセージのリスト
        """
        # XMLタグで入力を明確に区別
        marked_text = f"<transcription>{text}</transcription>"
        return [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": marked_text},
        ]

    def _process_with_groq(self, text: str) -> str:
        """
        Groq APIでテキストを処理する。
        
        Args:
            text: 入力テキスト
            
        Returns:
            変換後テキスト
        """
        import time
        client = self._get_groq_client()

        api_start = time.perf_counter()
        logger.debug(f"LLM API呼び出し開始: model={self.model}, text_len={len(text)}")
        response = client.chat.completions.create(
            model=self.model,
            messages=self._build_messages(text),
            temperature=0.0,  # 決定論的な出力
            max_tokens=max(len(text) * 3, 100),  # 入力の3倍または最低100トークン
        )
        self.last_api_time = (time.perf_counter() - api_start) * 1000
        logger.debug(f"LLM API呼び出し完了: {self.last_api_time:.0f}ms")

        # レスポンスの検証
        if not response.choices:
            logger.error(f"LLM API: 空のchoicesが返されました (model={self.model})")
            raise RuntimeError("LLM API returned empty choices")
        
        content = response.choices[0].message.content
        if content is None:
            logger.warning(f"LLM API: contentがNone (model={self.model}), 元テキストを使用")
            return text if self.fallback_on_error else ""
        
        result = content.strip()
        
        # 空のレスポンスの場合、元テキストにフォールバック
        if not result:
            logger.warning(f"LLM API: 空のレスポンス (model={self.model}), 元テキストを使用")
            return text if self.fallback_on_error else ""
        
        logger.debug(f"LLM変換: '{text}' -> '{result}'")
        return result

    def _process_with_cerebras(self, text: str) -> str:
        """
        Cerebras APIでテキストを処理する。
        
        Args:
            text: 入力テキスト
            
        Returns:
            変換後テキスト
        """
        import time
        client = self._get_cerebras_client()

        api_start = time.perf_counter()
        response = client.chat.completions.create(
            model=self.model,
            messages=self._build_messages(text),
        )
        self.last_api_time = (time.perf_counter() - api_start) * 1000

        result = response.choices[0].message.content.strip()
        logger.debug(f"LLM変換: '{text}' -> '{result}'")
        return result
