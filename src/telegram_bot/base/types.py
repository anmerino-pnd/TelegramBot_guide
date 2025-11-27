from typing import Optional, List
from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict

class Text(BaseModel):
    content : str
    
type Question = Text

class CallMetadata(BaseModel):
    provider : str        # Provider name
    model : str           # Model name
    operation : str       # Type of operation
    duration : float      # Request duration in seconds
    input_tokens : Optional[int]    # Number of tokens in the input prompt
    output_tokens : Optional[int]   # Number of tokens in the generated response

def call_metadata(
        provider : str,
        model : str,
        operation : str,
        duration : float,
        input_tokens : Optional[int],
        output_tokens : Optional[int],
) -> CallMetadata:
    return CallMetadata(
        provider=provider,
        model=model,
        operation=operation,
        duration=duration,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )