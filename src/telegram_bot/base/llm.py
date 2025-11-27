from typing import Tuple
from abc import ABC, abstractmethod
from telegram_bot.base.types import Text, CallMetadata

class LLM(ABC):
    @abstractmethod
    def answer(self, question) -> Tuple[Text, CallMetadata]:
        pass

    def prompt_system(self) -> str:
        return(
            """
            You're nice and useful
            """
        )