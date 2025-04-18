# Smart Proxy Agent System

This document provides a comprehensive overview of the Smart Proxy Agent system, including its template-based approach to dynamic agent creation, tool integration, and workflow processes.

## Overview

The Smart Proxy Agent is an intelligent routing layer that analyzes user queries and dynamically creates specialized agent configurations optimized for each specific query. Rather than selecting from a fixed set of predefined agents, it generates customized agent profiles on the fly, leveraging a template system for efficiency and consistency.

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': { 'primaryColor': '#333333', 'primaryTextColor': '#fff', 'primaryBorderColor': '#444', 'lineColor': '#666', 'secondaryColor': '#555', 'tertiaryColor': '#444'}}}%%
flowchart TD
    User[User Query] --> SmartProxy[Smart Proxy Agent]
    SmartProxy --> QueryAnalysis[Query Analysis]
    QueryAnalysis --> TemplateSelection[Template Selection]
    TemplateSelection --> TemplateCustomization[Template Customization]
    TemplateCustomization --> ToolIntegration[Tool Integration]
    ToolIntegration --> DynamicAgent[Dynamic Specialized Agent]
    DynamicAgent --> Response[Response to User]
    
    TemplateSystem[Template System] -.-> TemplateSelection
    TemplateSystem -.-> TemplateCustomization
    ToolConfigs[Tool Configurations] -.-> ToolIntegration
    Cache[Configuration Cache] -.-> SmartProxy
    Cache <-.-> DynamicAgent
    
    class SmartProxy,DynamicAgent,TemplateSystem,ToolConfigs,Cache tertiary;
    class User,Response primary;
    class QueryAnalysis,TemplateSelection,TemplateCustomization,ToolIntegration secondary;
```

## Template-Based Design

The system uses predefined templates for common agent types (developer, researcher, data scientist, etc.) that can be rapidly customized for specific domains and tasks, rather than generating every detail from scratch.

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': { 'primaryColor': '#333333', 'primaryTextColor': '#fff', 'primaryBorderColor': '#444', 'lineColor': '#666', 'secondaryColor': '#555', 'tertiaryColor': '#444'}}}%%
classDiagram
    class AgentTemplate {
        +String template_id
        +String name
        +String description
        +String base_system_message
        +List~String~ expertise_areas
        +Tuple~float~ temperature_range
        +List~String~ supported_tools
        +String prompt_preamble
        +List~String~ template_variables
        +customize(variables)
    }
    
    class AgentTemplateManager {
        +Dict templates
        +Dict tools_config
        +AgentTemplateCache cache
        +load_templates()
        +get_template(template_id)
        +get_tool_config(tool_id)
        +get_compatible_tools(template_id)
        +customize_template(template_id, variables)
        +find_best_template(analysis)
        +cache_config(query, config, context_id)
    }
    
    class AgentTemplateCache {
        +Dict recent_configs
        +Dict access_times
        +add(query_hash, config)
        +get(query_hash)
        +clear()
    }
    
    class DynamicAgentProxy {
        +Dict sessions
        +Dict performance_metrics
        +_analyze_query(query, context)
        +_generate_agent_config(query, analysis, context)
        +_evolve_agent_config(query, previous_config, analysis, context)
        +_process_with_dynamic_agent(query, agent_config, context)
        +run(query, user_id, session_id)
    }
    
    DynamicAgentProxy --> AgentTemplateManager : uses
    AgentTemplateManager --> AgentTemplate : manages
    AgentTemplateManager --> AgentTemplateCache : uses
```

## Key Components

### 1. Dynamic Agent Proxy 

The core controller that orchestrates the entire process, from analyzing user queries to creating and deploying specialized agents.

### 2. Template System

Provides a structured way to define and customize agent profiles:

- **Agent Templates**: Base configurations for different types of agents
- **Tool Configurations**: Definitions of tools that can be used with templates
- **Template Variables**: Customization points within templates

### 3. Conversation Context

Tracks conversation history, metadata, and previously used agent configurations to support continuity and follow-up handling.

## Process Flow

The following diagram illustrates the complete workflow from user query to response:

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': { 'primaryColor': '#333333', 'primaryTextColor': '#fff', 'primaryBorderColor': '#444', 'lineColor': '#666', 'secondaryColor': '#555', 'tertiaryColor': '#444'}}}%%
sequenceDiagram
    participant User
    participant Proxy as Smart Proxy Agent
    participant Analyzer as Query Analyzer
    participant TemplateManager as Template Manager
    participant Cache
    participant LLM
    
    User->>+Proxy: Query
    Proxy->>+Analyzer: Analyze query
    Analyzer-->>-Proxy: Analysis (intent, domains, complexity)
    
    Proxy->>Cache: Check for cached config
    Cache-->>Proxy: Cached config (if exists)
    
    alt Cache hit
        Proxy->>LLM: Process with cached config
    else Cache miss
        Proxy->>+TemplateManager: Find best template
        TemplateManager-->>-Proxy: Template ID & customization variables
        
        Proxy->>+TemplateManager: Customize template
        TemplateManager-->>-Proxy: Customized agent config
        
        Proxy->>+TemplateManager: Get compatible tools
        TemplateManager-->>-Proxy: Tool configurations
        
        Proxy->>LLM: Process with new config
        Proxy->>Cache: Store config for future use
    end
    
    LLM-->>Proxy: Response
    Proxy-->>-User: Response
```

## Query Analysis

The Smart Proxy begins by analyzing the query to understand its intent, domains, complexity, and other metadata:

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': { 'primaryColor': '#333333', 'primaryTextColor': '#fff', 'primaryBorderColor': '#444', 'lineColor': '#666', 'secondaryColor': '#555', 'tertiaryColor': '#444'}}}%%
flowchart LR
    Query[User Query] --> Analyzer[Query Analyzer]
    ConvHistory[Conversation History] --> Analyzer
    
    Analyzer --> Intent[Primary Intent]
    Analyzer --> Domains[Domains/Topics]
    Analyzer --> Entities[Key Entities]
    Analyzer --> Complexity[Complexity Level]
    Analyzer --> IsFollowup[Is Follow-up?]
    
    Intent & Domains & Entities & Complexity --> TemplateMatching[Template Matching]
    
    class Query,ConvHistory primary;
    class Analyzer tertiary;
    class Intent,Domains,Entities,Complexity,IsFollowup,TemplateMatching secondary;
```

## Template Selection and Customization

Based on the query analysis, the system selects the most appropriate template and customizes it:

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': { 'primaryColor': '#333333', 'primaryTextColor': '#fff', 'primaryBorderColor': '#444', 'lineColor': '#666', 'secondaryColor': '#555', 'tertiaryColor': '#444'}}}%%
flowchart TD
    Analysis[Query Analysis] --> ScoreTemplates[Score Each Template]
    ScoreTemplates --> BestTemplate[Select Best Template]
    
    BestTemplate --> Customize[Customize Template]
    
    Analysis --> SpecVars[Extract Specialization Variables]
    SpecVars --> Customize
    
    Customize --> AgentConfig[Dynamic Agent Configuration]
    
    AgentConfig --> SystemMsg[System Message]
    AgentConfig --> Temperature[Temperature Setting]
    AgentConfig --> Tools[Compatible Tools]
    AgentConfig --> PromptPreamble[Prompt Preamble]
    
    class Analysis,AgentConfig primary;
    class ScoreTemplates,BestTemplate,Customize,SpecVars tertiary;
    class SystemMsg,Temperature,Tools,PromptPreamble secondary;
```

## Tool Integration

The system integrates appropriate tools based on the template and query needs:

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': { 'primaryColor': '#333333', 'primaryTextColor': '#fff', 'primaryBorderColor': '#444', 'lineColor': '#666', 'secondaryColor': '#555', 'tertiaryColor': '#444'}}}%%
flowchart LR
    Template[Agent Template] --> CompTools[Compatible Tools]
    
    CompTools --> ToolSystem[Tool System]
    Query[Query Analysis] --> ToolSystem
    
    ToolSystem --> SelectedTools[Selected Tools]
    
    SelectedTools --> SystemMsgAdd[Add to System Message]
    SelectedTools --> TempAdjust[Adjust Temperature]
    
    SystemMsgAdd & TempAdjust --> FinalConfig[Final Agent Configuration]
    
    class Template,Query,FinalConfig primary;
    class CompTools,ToolSystem,SelectedTools tertiary;
    class SystemMsgAdd,TempAdjust secondary;
```

## Configuration Evolution

For follow-up queries, the system can evolve existing configurations rather than creating new ones:

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': { 'primaryColor': '#333333', 'primaryTextColor': '#fff', 'primaryBorderColor': '#444', 'lineColor': '#666', 'secondaryColor': '#555', 'tertiaryColor': '#444'}}}%%
flowchart TD
    Query[New User Query] --> IsFollowup{Is Follow-up?}
    
    IsFollowup -->|No| NewConfig[Generate New Config]
    
    IsFollowup -->|Yes| PrevConfig[Previous Config]
    PrevConfig --> Decision{Evolution Decision}
    
    Decision -->|Keep| KeepConfig[Keep Existing Config]
    Decision -->|Modify| ModifyConfig[Modify Existing Config]
    Decision -->|Replace| ReplaceConfig[Create New Config]
    
    KeepConfig & ModifyConfig & ReplaceConfig --> FinalConfig[Final Agent Config]
    NewConfig --> FinalConfig
    
    class Query,FinalConfig primary;
    class IsFollowup,Decision tertiary;
    class NewConfig,PrevConfig,KeepConfig,ModifyConfig,ReplaceConfig secondary;
```

## Supported Templates

The system includes predefined templates for various agent types:

| Template ID | Name | Description | Temperature Range |
|-------------|------|-------------|-------------------|
| developer | Developer | Software development, coding, debugging | 0.1-0.4 |
| data_scientist | Data Scientist | Data analysis, statistics, ML | 0.1-0.5 |
| researcher | Researcher | Academic research, literature review | 0.1-0.3 |
| strategic_advisor | Strategic Advisor | Business strategy, decision analysis | 0.2-0.6 |
| creative | Creative | Creative writing, content creation | 0.5-0.9 |
| technical_writer | Technical Writer | Technical documentation | 0.1-0.4 |
| system_architect | System Architect | System design, architecture | 0.1-0.4 |

## Tool Configuration Structure

Tools are configured to work with specific templates and include system message additions:

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': { 'primaryColor': '#333333', 'primaryTextColor': '#fff', 'primaryBorderColor': '#444', 'lineColor': '#666', 'secondaryColor': '#555', 'tertiaryColor': '#444'}}}%%
classDiagram
    class ToolConfig {
        +String description
        +List~String~ parameters
        +List~String~ compatible_with
        +Float temperature_adjustment
        +String system_prompt_addition
    }
    
    class AgentTemplate {
        +String template_id
        +List~String~ supported_tools
    }
    
    AgentTemplate --> ToolConfig : supports
```

Example tool configuration:

```yaml
code_analysis:
  description: "Analyzes code to identify patterns, issues, and optimization opportunities"
  parameters:
    - language
    - code_snippet
    - analysis_type
  compatible_with:
    - developer
    - data_scientist
    - system_architect
  temperature_adjustment: -0.1
  system_prompt_addition: |
    You have access to a code analysis tool that can help identify issues, patterns, and optimization opportunities.
    When analyzing code, focus on readability, maintainability, and performance aspects.
```

## Caching Mechanism

The system implements caching to efficiently reuse configurations for similar queries:

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': { 'primaryColor': '#333333', 'primaryTextColor': '#fff', 'primaryBorderColor': '#444', 'lineColor': '#666', 'secondaryColor': '#555', 'tertiaryColor': '#444'}}}%%
flowchart TD
    Query[User Query] --> Hash[Compute Query Hash]
    SessionID[Session ID] --> Hash
    
    Hash --> CacheCheck{In Cache?}
    
    CacheCheck -->|Yes| RetrieveConfig[Retrieve Cached Config]
    CacheCheck -->|No| GenerateConfig[Generate New Config]
    
    GenerateConfig --> StoreCache[Store in Cache]
    StoreCache --> LRUCheck{Cache Full?}
    
    LRUCheck -->|Yes| EvictLRU[Evict Least Recently Used]
    
    RetrieveConfig & StoreCache --> UseConfig[Use Config]
    
    class Query,SessionID,UseConfig primary;
    class Hash,CacheCheck,LRUCheck tertiary;
    class RetrieveConfig,GenerateConfig,StoreCache,EvictLRU secondary;
```

## Benefits of the Template Approach

The template-based approach offers several advantages:

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': { 'primaryColor': '#333333', 'primaryTextColor': '#fff', 'primaryBorderColor': '#444', 'lineColor': '#666', 'secondaryColor': '#555', 'tertiaryColor': '#444'}}}%%
flowchart LR
    TemplateSystem[Template System] --> Efficiency[Improved Efficiency]
    TemplateSystem --> Consistency[Consistent Configurations]
    TemplateSystem --> Flexibility[Flexible Customization]
    TemplateSystem --> Reuse[Configuration Reuse]
    TemplateSystem --> Specialization[Domain Specialization]
    TemplateSystem --> ToolIntegration[Seamless Tool Integration]
    
    class TemplateSystem tertiary;
    class Efficiency,Consistency,Flexibility,Reuse,Specialization,ToolIntegration secondary;
```

1. **Improved Efficiency**: Quickly creates specialized agents without regenerating every detail
2. **Consistency**: Ensures a consistent approach while allowing customization
3. **Caching**: Reuses configurations for similar queries, reducing latency
4. **Tool Integration**: Seamlessly integrates tools based on agent type and query needs
5. **Specialization**: Customizes for specific domains while maintaining expertise profile

## Extending the System

New templates and tools can be added by:

1. **Adding Templates**: Create new entries in `agent_templates.yaml`
2. **Adding Tools**: Define new tools in `tools_config.yaml`
3. **Custom Variables**: Define template variables for customization points

## Implementation Structure

The system is implemented with the following key files:

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': { 'primaryColor': '#333333', 'primaryTextColor': '#fff', 'primaryBorderColor': '#444', 'lineColor': '#666', 'secondaryColor': '#555', 'tertiaryColor': '#444'}}}%%
flowchart TD
    DynamicProxy[src/agents/dynamic_proxy.py] --- AgentTemplates[src/agents/utils/agent_templates.py]
    
    AgentTemplates --- TemplateYAML[src/agents/templates/agent_templates.yaml]
    AgentTemplates --- ToolsYAML[src/agents/templates/tools_config.yaml]
    
    DynamicProxy --- QueryAnalyzer[src/agents/utils/query_analyzer.py]
    
    class DynamicProxy,AgentTemplates primary;
    class TemplateYAML,ToolsYAML,QueryAnalyzer secondary;
```

## Full System Diagram

The complete system with all components:

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': { 'primaryColor': '#333333', 'primaryTextColor': '#fff', 'primaryBorderColor': '#444', 'lineColor': '#666', 'secondaryColor': '#555', 'tertiaryColor': '#444'}}}%%
flowchart TD
    User[User] --> Query[Query]
    Query --> SmartProxy[Dynamic Agent Proxy]
    
    SmartProxy --> Context[Conversation Context]
    Context --> History[Chat History]
    Context --> Metadata[Context Metadata]
    Context --> PrevConfig[Previous Configurations]
    
    SmartProxy --> Analysis[Query Analysis]
    Analysis --> Intent[Intent Detection]
    Analysis --> Domains[Domain Extraction]
    Analysis --> Complexity[Complexity Assessment]
    Analysis --> FollowupDetection[Follow-up Detection]
    
    SmartProxy --> TemplateSystem[Template System]
    TemplateSystem --> Templates[Agent Templates]
    TemplateSystem --> ToolConfigs[Tool Configurations]
    TemplateSystem --> Cache[Configuration Cache]
    
    SmartProxy --> ConfigGeneration[Configuration Generation]
    ConfigGeneration --> TemplateSelection[Template Selection]
    ConfigGeneration --> Customization[Template Customization]
    ConfigGeneration --> ToolIntegration[Tool Integration]
    ConfigGeneration --> CacheCheck[Cache Check/Update]
    
    SmartProxy --> Processing[Query Processing]
    Processing --> SystemMessage[System Message Construction]
    Processing --> TemperatureSettings[Temperature Adjustment]
    Processing --> LLM[LLM Interaction]
    
    LLM --> Response[Response]
    Response --> User
    
    class User,Query,Response primary;
    class SmartProxy,TemplateSystem,Context,Analysis,ConfigGeneration,Processing tertiary;
    class History,Metadata,PrevConfig,Intent,Domains,Complexity,FollowupDetection,Templates,ToolConfigs,Cache,TemplateSelection,Customization,ToolIntegration,CacheCheck,SystemMessage,TemperatureSettings,LLM secondary;
```

## Conclusion

The Smart Proxy Agent with template-based configuration provides a sophisticated yet efficient approach to dynamic agent creation. It balances standardization with customization, enabling rapid deployment of specialized agents optimized for specific queries while maintaining consistency and leveraging caching for improved performance. 