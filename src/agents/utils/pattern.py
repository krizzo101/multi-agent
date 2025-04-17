from typing import Any, List, Optional
from llama_index.core.llms import ChatMessage
import json
import re

class ChatHistory:
    def __init__(self, initial_messages: List[ChatMessage], max_length: int):
        self.messages = initial_messages
        self.max_length = max_length

    def add(self, role: str, content: str):
        self.messages.append(ChatMessage(role=role, content=content))
        if len(self.messages) > self.max_length:
            self.messages = [self.messages[0]] + self.messages[-(self.max_length-1):]

    def get_messages(self) -> List[ChatMessage]:
        return self.messages
    
class PlanStep:
    def __init__(self, description: str, requires_tool: bool = False, tool_name: str = None, is_required: bool = True):
        self.description = description
        self.requires_tool = requires_tool
        self.tool_name = tool_name
        self.is_required = is_required
        self.completed = False
        self.result = None

class ExecutionPlan:
    def __init__(self, steps: List[PlanStep] = None):
        self.steps = steps if steps is not None else []
        self.current_step = 0
        
    def add_step(self, step: PlanStep):
        self.steps.append(step)
        
    def get_current_step(self) -> Optional[PlanStep]:
        if self.current_step < len(self.steps):
            return self.steps[self.current_step]
        return None
        
    def mark_current_complete(self, result: Any = None):
        if self.current_step < len(self.steps):
            self.steps[self.current_step].completed = True
            self.steps[self.current_step].result = result
            self.current_step += 1
            
    def is_complete(self) -> bool:
        return self.current_step >= len(self.steps)
    
    def get_progress(self) -> str:
        completed = sum(1 for step in self.steps if step.completed)
        return f"Progress: {completed}/{len(self.steps)} steps completed"

def clean_json_response(response: str) -> str:
    """Clean and extract JSON from LLM response"""
    # Skip cleaning if already valid JSON
    try:
        json.loads(response)
        return response
    except (json.JSONDecodeError, TypeError):
        pass
    
    # Remove any markdown code block markers
    response = re.sub(r'```(?:json)?|```', '', response, flags=re.IGNORECASE).strip()
    
    # Find the first '{' and last '}'
    start = response.find('{')
    end = response.rfind('}')
    
    if start == -1 or end == -1:
        # More aggressive attempt - get anything that looks remotely like JSON
        start = re.search(r'[\{\[]', response)
        end = re.search(r'[\}\]](?!.*[\}\]])', response)
        
        if not start or not end:
            raise ValueError("No valid JSON object found in response")
        
        start = start.start()
        end = end.start() + 1
    
    # Extract just the JSON object
    extracted_json = response[start:end + 1]
    
    # Validate the extracted JSON
    try:
        json.loads(extracted_json)
        return extracted_json
    except json.JSONDecodeError:
        # Try to fix common JSON issues (single quotes, unquoted keys)
        try:
            # Fix single quotes to double quotes (but not in string values)
            fixed_json = re.sub(r"(?<!\w)'([^']*)'(?!\\)(?=\s*:)", r'"\1"', extracted_json)
            # Try parsing again
            json.loads(fixed_json)
            return fixed_json
        except (json.JSONDecodeError, re.error):
            raise ValueError("Failed to extract valid JSON from response")