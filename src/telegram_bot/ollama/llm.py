import time
from telegram_bot.base.types import (
     Question,
     CallMetadata,
     call_metadata
)
from ollama import GenerateResponse
from telegram_bot.base.llm import LLM
from telegram_bot.settings.variables import ollama

class Agent(LLM):
    def __init__(self):
        self.model = "gemma3:4b" # gemma3 runs in local
        # if you want to run cloude models then you can search for models here https://ollama.com/search?c=cloud 

    def answer(self, question: Question) :
        response_tokens = []

        start_time = time.perf_counter()
        result = ollama.generate(
            model=self.model,
            system=self.prompt_system(),
            options={"temperature": 0},
            prompt=question,
            stream=False)
        end_time = time.perf_counter()
        duration = end_time - start_time

        if hasattr(result, "response"):
            tokens = result.response
            response_tokens.append(tokens)

        metadata = self.make_metadata(result, duration).model_dump()
        
        return result, metadata

    
    def make_metadata(self, response: GenerateResponse, duration: float) -> CallMetadata:
            input_tokens = response.prompt_eval_count
            output_tokens = response.eval_count
            return call_metadata(
                provider="ollama",
                model=self.model,
                operation="generate",
                duration=duration,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )