# Interface Specification

## 1. Overview
This document defines the major APIs and interfaces for the multi-agent orchestration system, synthesized from `.reference/docs/` and tailored to the project context.

## 2. Agent API
| Endpoint | Method | Description | Parameters | Example Payload |
|----------|--------|-------------|------------|----------------|
| /agent/execute | POST | Execute a task with input and context | input, context | `{ "input": "task details", "context": { ... } }` |
| /agent/status | GET | Retrieve agent status | agent_id | `{ "agent_id": "research_agent_1" }` |

## 3. Configuration API
| Endpoint | Method | Description | Parameters | Example Payload |
|----------|--------|-------------|------------|----------------|
| /config | GET | Retrieve current configuration | - | - |
| /config/update | POST | Update configuration | config | `{ "config": { ... } }` |

## 4. Template API
| Endpoint | Method | Description | Parameters | Example Payload |
|----------|--------|-------------|------------|----------------|
| /template/{id} | GET | Retrieve template by ID | id | - |
| /template/render | POST | Render template with context | template_id, context | `{ "template_id": "welcome", "context": { ... } }` |

## 5. QA API
| Endpoint | Method | Description | Parameters | Example Payload |
|----------|--------|-------------|------------|----------------|
| /qa/validate | POST | Validate agent output | output, context | `{ "output": "result text", "context": { ... } }` |
| /qa/feedback | POST | Submit feedback on output | feedback, agent_id | `{ "feedback": "improve clarity", "agent_id": "code_agent_1" }` |

## 6. Conversation History API
| Endpoint | Method | Description | Parameters | Example Payload |
|----------|--------|-------------|------------|----------------|
| /conversation/{id} | GET | Retrieve conversation history | id | - |
| /conversation/update | POST | Update conversation history | conversation_id, message | `{ "conversation_id": "abc123", "message": { ... } }` |

## 7. Notes
- All APIs use JSON for request and response bodies.
- Authentication and authorization are required for all endpoints.
- See `.reference/docs/sequence-diagram.md` and `.reference/docs/architecture.md` for protocol details. 