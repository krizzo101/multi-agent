from dataclasses import dataclass
from typing import Optional

@dataclass
class Settings:
    model: str = "o3-mini"
    temperature: float = 0.5
    max_tokens: int = 500
    openai_endpoint: str = "https://api.openai.com/v1/chat/completions"
    openai_base: Optional[str] = None 