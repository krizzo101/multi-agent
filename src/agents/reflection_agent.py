from typing import List, Dict, Any, Optional
from llama_index.core.llms import ChatMessage
from llama_index.core.tools import FunctionTool
import json
import logging
from colorama import Fore
from src.agents.llm import BaseLLM
from src.agents.base import BaseAgent, AgentOptions
from src.agents.utils import ChatHistory, clean_json_response
from src.prompt import BASE_GENERATION_SYSTEM_PROMPT, BASE_REFLECTION_SYSTEM_PROMPT  # Import centralized prompts

logger = logging.getLogger(__name__)

class ReflectionAgent(BaseAgent):
    def __init__(self, llm: BaseLLM, options: AgentOptions, tools: List[FunctionTool] = []):
        # Set default prompt template ID if not provided
        if not hasattr(options, 'prompt_template_id') or options.prompt_template_id is None:
            options.prompt_template_id = "agent.reflection.generation"
            
        super().__init__(llm, options)
        self.tools = tools
        self.tools_dict = {tool.metadata.name: tool for tool in tools}

    def _create_system_message(self, prompt: str) -> ChatMessage:
        return ChatMessage(role="system", content=prompt)

    def _format_tool_signatures(self) -> str:
        """Format all tool signatures into a string format LLM can understand"""
        tool_descriptions = []
        for tool in self.tools:
            metadata = tool.metadata
            parameters = metadata.get_parameters_dict()
            
            tool_descriptions.append(
                f"""
                Function: {metadata.name}
                Description: {metadata.description}
                Parameters: {json.dumps(parameters, indent=2)}
                """
            )
        
        return "\n".join(tool_descriptions)

    async def _execute_tool(self, tool_name: str, description: str) -> Any:
        """Execute a FunctionTool based on the given description"""
        if tool_name not in self.tools_dict:
            raise ValueError(f"Unknown tool: {tool_name}")

        # Get tool execution prompt template
        prompt = self.get_prompt("agent.tool.execution", {
            "tool_name": tool_name,
            "description": description,
            "tool_spec": json.dumps(self.tools_dict[tool_name].metadata.get_parameters_dict(), indent=2)
        })
        
        if not prompt:
            # Fallback to hardcoded prompt if template not found
            prompt = f"""
            Generate parameters to call this tool:
            Purpose: {description}
            Tool: {tool_name}
            
            Tool specification:
            {json.dumps(self.tools_dict[tool_name].metadata.get_parameters_dict(), indent=2)}
            
            Response format:
            {{
                "arguments": {{
                    // parameter names and values matching the specification exactly
                }}
            }}
            Remove the ```json and ```
            """
        
        try:
            # Get tool parameters from LLM
            response = await self.llm.achat(query=prompt)
            response = clean_json_response(response)
            params = json.loads(response)
            
            # Get the tool and validate parameters
            tool = self.tools_dict[tool_name]
            
            # Execute the tool
            result = await tool.acall(**params['arguments'])
            return result
            
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {str(e)}")
            raise

    async def _generate_response(
        self,
        chat_history: List[ChatMessage],
        verbose: bool = False,
        log_title: str = "COMPLETION",
        log_color: str = ""
    ) -> str:
        try:
            response = await self.llm.achat(
                query=chat_history[-1].content,
                chat_history=chat_history[:-1]
            )
            
            if verbose:
                print(log_color, f"\n\n{log_title}\n\n", response)
                
            return response
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            raise

    async def generate(
        self,
        generation_history: ChatHistory,
        verbose: bool = False
    ) -> str:
        return await self._generate_response(
            generation_history.get_messages(),
            verbose,
            log_title="GENERATION",
            log_color=Fore.BLUE
        )

    async def reflect(
        self,
        reflection_history: ChatHistory,
        verbose: bool = False
    ) -> str:
        # Enhance reflection to include tool usage recommendation if needed
        tools_context = f"\nAvailable tools:\n{self._format_tool_signatures()}" if self.tools else ""
        
        # Modify last message to include tools context
        reflection_history_messages = reflection_history.get_messages()
        reflection_history_messages[-1].content += tools_context
        
        return await self._generate_response(
            reflection_history_messages,
            verbose,
            log_title="REFLECTION", 
            log_color=Fore.GREEN
        )

    async def run(
        self,
        query: str,
        context: Dict[str, Any] = None,
        n_steps: int = 3,
        max_tool_steps: int = 2,
        verbose: bool = False,
        **kwargs
    ) -> str:
        # Initialize context
        context = context or {}
        context.update({
            "agent_type": "reflection",
            "conversation_stage": "generation"
        })
        
        # Initialize generation system prompt using templates
        generation_template_id = "agent.reflection.generation"
        generation_system_prompt = self.get_prompt(generation_template_id, context)
        
        # Initialize reflection system prompt using templates
        reflection_template_id = "agent.reflection.critique"
        reflection_system_prompt = self.get_prompt(reflection_template_id, context)
        
        # If templates are not found, try scenario-based templates
        if not generation_system_prompt:
            generation_system_prompt = self.get_prompt_for_context(context) or ""
            
        if not reflection_system_prompt:
            context["conversation_stage"] = "critique"
            reflection_system_prompt = self.get_prompt_for_context(context) or ""
        
        # Initialize chat histories
        generation_history = ChatHistory(
            initial_messages=[
                self._create_system_message(generation_system_prompt),
                ChatMessage(role="user", content=query)
            ],
            max_length=3
        )

        reflection_history = ChatHistory(
            initial_messages=[self._create_system_message(reflection_system_prompt)],
            max_length=3
        )

        tool_steps_count = 0

        for step in range(n_steps):
            if verbose:
                print(f"\nStep {step + 1}/{n_steps}")

            # Generate content
            generation = await self.generate(generation_history, verbose=verbose)
            generation_history.add("assistant", generation)
            reflection_history.add("user", generation)

            # Reflect on the generation
            critique = await self.reflect(reflection_history, verbose=verbose)
            
            if "<OK>" in critique:
                if verbose:
                    print(Fore.RED, "\n\nReflection complete - content is satisfactory\n\n")
                break

            # Check for tool recommendations in critique
            tool_recommendations = self._extract_tool_recommendations(critique)
            
            for tool_name, tool_description in tool_recommendations:
                if tool_steps_count < max_tool_steps:
                    try:
                        tool_result = await self._execute_tool(tool_name, tool_description)
                        critique += f"\nTool {tool_name} result: {tool_result}"
                        tool_steps_count += 1
                    except Exception as e:
                        critique += f"\nTool {tool_name} execution failed: {str(e)}"

            generation_history.add("user", critique)
            reflection_history.add("assistant", critique)

        return generation

    def _extract_tool_recommendations(self, critique: str) -> List[tuple]:
        """
        Extract tool recommendations from critique.
        Looks for patterns like: "Use [tool_name] to [description]"
        """
        tool_recommendations = []
        
        # Simple pattern matching - could be enhanced with regex
        lines = critique.split("\n")
        for line in lines:
            line = line.strip()
            for tool_name in self.tools_dict.keys():
                if f"Use {tool_name}" in line or f"Try {tool_name}" in line:
                    # Extract description after the tool name
                    parts = line.split(tool_name, 1)
                    if len(parts) > 1:
                        description = parts[1].strip()
                        if description.startswith("to "):
                            description = description[3:]
                        tool_recommendations.append((tool_name, description))
        
        return tool_recommendations

    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Cleanup code if needed
        pass