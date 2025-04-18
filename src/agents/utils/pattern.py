from typing import Any, List, Optional, Dict
from llama_index.core.llms import ChatMessage
import json
import re
import logging

logger = logging.getLogger(__name__)

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

def parse_pattern_format(pattern: str, text: str) -> Dict[str, str]:
    """Parse text according to a simple pattern format.
    
    This function parses a text string using a simple pattern format where
    variables are denoted by curly braces, e.g. {variable_name}.
    
    Args:
        pattern: The pattern string with variable placeholders
        text: The text to parse
        
    Returns:
        Dictionary mapping variable names to extracted values
        
    Example:
        parse_pattern_format("Hello, my name is {name}.", "Hello, my name is John.")
        # Returns: {"name": "John"}
    """
    # Convert pattern to regex by escaping special chars and converting {var} to named capture groups
    pattern_parts = []
    var_names = []
    
    # Split the pattern by curly braces
    remaining = pattern
    while remaining:
        # Find opening brace
        open_idx = remaining.find('{')
        if open_idx == -1:
            # No more variables, add the rest as literal
            pattern_parts.append(re.escape(remaining))
            break
            
        # Add text before the variable as literal
        if open_idx > 0:
            pattern_parts.append(re.escape(remaining[:open_idx]))
            
        # Find closing brace
        close_idx = remaining.find('}', open_idx)
        if close_idx == -1:
            # No closing brace, treat the rest as literal
            pattern_parts.append(re.escape(remaining[open_idx:]))
            break
            
        # Extract variable name
        var_name = remaining[open_idx+1:close_idx].strip()
        var_names.append(var_name)
        
        # Add named capture group
        pattern_parts.append(f"(?P<{var_name}>.+?)")
        
        # Move to the rest of the string
        remaining = remaining[close_idx+1:]
    
    # Compile the regex pattern
    regex_pattern = ''.join(pattern_parts)
    
    try:
        # Try to match the pattern against the text
        match = re.match(regex_pattern, text, re.DOTALL)
        if match:
            return match.groupdict()
        else:
            logger.warning(f"Failed to match pattern '{pattern}' against text")
            return {}
    except re.error as e:
        logger.error(f"Error in regex pattern '{regex_pattern}': {str(e)}")
        return {}

def clean_json_response(response: str) -> str:
    """Clean and extract JSON from LLM response
    
    This function attempts to extract valid JSON from an LLM response,
    handling various formatting issues commonly seen in LLM outputs.
    
    Args:
        response: The raw LLM response text
        
    Returns:
        Cleaned JSON string
        
    Raises:
        ValueError: If no valid JSON can be extracted
    """
    if not response or not isinstance(response, str):
        logger.error(f"Invalid response type: {type(response)}")
        raise ValueError("Response must be a non-empty string")
    
    # Log the response for debugging (truncated for length)
    logger.debug(f"Cleaning JSON from response: {response[:100]}...")
    
    # Handle special case of Gemini citation metadata format
    if "finish_reason: RECITATION" in response:
        logger.warning("Detected citation metadata in response, creating fallback JSON")
        return '{"error": "Citation metadata detected", "message": "Response contained citations but could not be displayed properly"}'
    
    # Skip cleaning if already valid JSON
    try:
        json.loads(response)
        return response
    except (json.JSONDecodeError, TypeError):
        pass
    
    # Remove any markdown code block markers
    response = re.sub(r'```(?:json)?|```', '', response, flags=re.IGNORECASE).strip()
    
    # Find the JSON object by looking for curly braces
    start = response.find('{')
    end = response.rfind('}')
    
    if start >= 0 and end > start:
        # Extract just the JSON object
        extracted_json = response[start:end + 1]
        
        # Check if this is valid JSON
        try:
            json.loads(extracted_json)
            return extracted_json
        except json.JSONDecodeError:
            # Try to fix common JSON issues
            try:
                # Fix single quotes to double quotes
                fixed_json = re.sub(r"'([^']*)'(?=\s*:)", r'"\1"', extracted_json)
                # Fix unquoted keys
                fixed_json = re.sub(r'(\w+)(?=\s*:)', r'"\1"', fixed_json)
                # Handle trailing commas
                fixed_json = re.sub(r',\s*}', '}', fixed_json)
                fixed_json = re.sub(r',\s*]', ']', fixed_json)
                
                # Try parsing again
                json.loads(fixed_json)
                return fixed_json
            except (json.JSONDecodeError, re.error):
                pass
    
    # Last resort: Create a fallback minimal JSON with default values
    logger.error(f"Failed to extract valid JSON, creating fallback response")
    if "selected_agent" in response.lower():
        fallback = '{"selected_agent": "default", "confidence": 0.5, "reasoning": "Fallback response due to parsing error"}'
    elif "primary_intent" in response.lower():
        fallback = '{"primary_intent": "unknown", "entities": [], "is_followup": false, "topic": "general", "requires_clarification": true, "confidence": 0.5}'
    else:
        fallback = '{"error": "Failed to parse response", "original": "' + response.replace('"', '\\"')[:100] + '..."}'
    
    return fallback

def safe_extract_content(response: Any) -> str:
    """Safely extract content from various LLM response formats.
    
    This is a utility function to handle different LLM response formats,
    including special cases like citation metadata.
    
    Args:
        response: The response object from an LLM
        
    Returns:
        str: The extracted text content
    """
    # Handle string responses directly
    if isinstance(response, str):
        return response
        
    # Handle citation metadata format from Gemini
    if hasattr(response, 'finish_reason') and response.finish_reason == 'RECITATION':
        logger.warning("Received response with RECITATION finish reason")
        return "I found information about this topic, but can't display it with proper citations. Please try a different question."
    
    # Handle standard response formats
    try:
        if hasattr(response, 'text'):
            return response.text
        elif hasattr(response, 'content'):
            if isinstance(response.content, str):
                return response.content
            elif hasattr(response.content, 'parts') and response.content.parts:
                return response.content.parts[0].text
        elif hasattr(response, 'message') and hasattr(response.message, 'content'):
            return response.message.content
            
        # Last resort: convert to string
        return str(response)
    except Exception as e:
        logger.error(f"Error extracting content from response: {str(e)}", exc_info=True)
        return "I encountered an issue processing this response. Please try a different question."