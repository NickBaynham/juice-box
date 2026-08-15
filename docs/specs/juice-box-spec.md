# Juice Box — Project Specification

Status: Draft
Date: 2026-08-14
Owner: Nick Baynham

## 1. Overview

Juice Box is a containerized orchestration platform for autonomous AI agents.

It provides a standard runtime and API for launching, controlling, observing, and coordinating agents that operate against persistent objectives. Agents run inside isolated containers, use configurable skills and tools, maintain execution state, accept requests while running, and can write results back to an associated repository.

Juice Box is infrastructure for agents, not an agent itself.

## 2. Primary Goal

Build a platform where a caller can provide:

- an agent definition
- an objective/specification
- a target repository
- required skills/tools
- runtime configuration

and Juice Box will create and run an autonomous agent capable of working toward that objective until it succeeds, fails, is stopped, or requires human intervention.

Example:

```text
Agent: test-commander
Objective: Analyze the application, generate missing Playwright tests,
execute the suite, repair failures, and improve coverage.
Repository: github.com/example/project
Completion Criteria: All generated tests pass and quality report is committed.
```

## 3. Design Principles

**Agent as a Service**
A running agent behaves like a long-lived software service rather than a single prompt-response interaction.

**Goal-Oriented Execution**
Agents work toward explicit objectives and measurable completion criteria.

**Container Isolation**
Each agent executes in an isolated container with controlled access to tools, credentials, networks, and repositories.

**API First**
Everything that can be performed through the UI must also be available through a standard API.

**Observable by Default**
Every decision, action, tool invocation, state change, error, and result should be inspectable.

**Provider Agnostic**
Juice Box should not depend on a single LLM provider, agent framework, cloud platform, or development tool.

**Human Control**
Humans must always be able to inspect, pause, resume, stop, restart, or redirect an agent.

## 4. Core Concepts

**Juice Box**
A managed runtime instance executing an agent.

**Agent**
The reasoning component responsible for deciding what actions to take to accomplish its objective.

Examples:

```text
test-commander
dev-commander
security-commander
research-agent
documentation-agent
```

**Objective**
The high-level outcome the agent must achieve.

```yaml
objective:
  goal: Increase automated API test coverage
  success_criteria:
    - Critical endpoints have automated tests
    - Test suite passes
    - Results are documented
    - Changes are committed to the repository
```

**Specification**
Detailed instructions, constraints, context, and acceptance criteria associated with an objective.

**Skill**
A reusable capability available to an agent.

Examples:

```text
playwright-testing
pytest
git
github
docker
web-research
code-analysis
documentation
aws-deployment
```

**Tool**
An executable capability used by a skill or agent.

Examples:

```text
shell
git
filesystem
browser
HTTP client
LLM API
GitHub API
AWS API
```

**Workspace**
The isolated filesystem associated with a Juice Box run.

Typical structure:

```text
/workspace
    /repo
    /artifacts
    /state
    /logs
```

**Run**
One execution of an agent against an objective.

**Task**
A unit of work created by an agent or orchestrator.

**Artifact**
Output generated during execution.

Examples:

```text
source code
tests
reports
screenshots
logs
documentation
plans
analysis
```

## 5. High-Level Architecture

```text
                         ┌─────────────────────┐
                         │    Juice Box API    │
                         └──────────┬──────────┘
                                    │
                         ┌──────────▼──────────┐
                         │    Orchestrator     │
                         └──────────┬──────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
              ┌─────▼─────┐   ┌─────▼─────┐   ┌─────▼─────┐
              │ Juice Box │   │ Juice Box │   │ Juice Box │
              │ Agent A   │   │ Agent B   │   │ Agent C   │
              └─────┬─────┘   └─────┬─────┘   └─────┬─────┘
                    │               │               │
             ┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐
             │ Skills/Tools│ │ Skills/Tools│ │ Skills/Tools│
             └─────────────┘ └─────────────┘ └─────────────┘

                         Persistent Services
                                │
              ┌─────────────────┼──────────────────┐
              │                 │                  │
          State Store       Event Bus        Artifact Store
              │                                    │
           Database                           Git / S3 / FS
```

## 6. Agent Lifecycle

Juice Box must implement a deterministic lifecycle.

```text
CREATED
   │
   ▼
STARTING
   │
   ▼
RUNNING
   │
   ├─────────► PAUSED
   │              │
   │              └────► RUNNING
   │
   ├─────────► WAITING
   │              │
   │              └────► RUNNING
   │
   ├─────────► COMPLETED
   │
   ├─────────► FAILED
   │
   └─────────► STOPPED
```

Supported lifecycle operations:

```http
POST /agents
POST /agents/{id}/start
POST /agents/{id}/stop
POST /agents/{id}/restart
POST /agents/{id}/pause
POST /agents/{id}/resume

GET /agents/{id}
GET /agents/{id}/status
```

## 7. Running Agent Interaction

A running Juice Box must accept additional requests.

```http
POST /agents/{id}/messages
```

Example:

```json
{
  "type": "instruction",
  "message": "Prioritize API coverage before UI coverage."
}
```

The message becomes part of the agent's execution context without requiring the container to restart.

Supported message types should eventually include:

```text
instruction
question
context
priority-change
cancel-task
new-task
approval
```

## 8. Agent Definition

Agents should be declaratively configurable.

Example:

```yaml
apiVersion: juicebox.ai/v1
kind: Agent

metadata:
  name: test-commander

agent:
  model:
    provider: anthropic
    model: claude-sonnet

  system_prompt: |
    You are an autonomous software quality engineering agent.

skills:
  - git
  - playwright
  - pytest
  - api-testing
  - code-analysis

runtime:
  cpu: 2
  memory: 4Gi
  timeout: 8h

permissions:
  filesystem: read-write
  network: true
  shell: true

repository:
  url: https://github.com/example/application
  branch: juicebox/test-commander

execution:
  max_iterations: 100
  require_approval_for:
    - production-deployment
    - merge
```

## 9. Objective Specification

Objectives should also be declarative.

```yaml
objective:
  id: improve-api-tests

  goal: >
    Improve automated API test coverage for the application.

  context:
    application: Juice Shop
    framework: Playwright

  tasks:
    - inspect existing tests
    - identify coverage gaps
    - generate additional tests
    - execute tests
    - repair failures
    - generate quality report

  constraints:
    - do not modify production application behavior
    - tests must be deterministic
    - follow existing repository conventions

  success_criteria:
    - critical API flows are tested
    - all generated tests pass
    - no existing tests regress
    - report is generated
    - changes are committed

  completion_action:
    commit: true
    push: true
    pull_request: true
```

## 10. Agent Execution Loop

The initial execution engine can use a simple iterative loop.

```text
Load Objective
      │
      ▼
Inspect Current State
      │
      ▼
Determine Next Action
      │
      ▼
Select Skill / Tool
      │
      ▼
Execute Action
      │
      ▼
Capture Result
      │
      ▼
Evaluate Progress
      │
      ├── Objective achieved ──► COMPLETE
      │
      ├── Cannot continue ─────► WAIT / ESCALATE
      │
      └── Continue ────────────► Determine Next Action
```

Each iteration should generate an execution record.

```json
{
  "iteration": 14,
  "task": "Run Playwright API tests",
  "action": "shell",
  "command": "npx playwright test tests/api",
  "result": "3 failed, 41 passed",
  "next_action": "Analyze the three failures"
}
```

## 11. Task Management

Agents must be able to decompose objectives into tasks.

Example:

```json
{
  "id": "task-17",
  "agent_id": "test-commander",
  "title": "Create authentication API tests",
  "status": "running",
  "priority": "high",
  "dependencies": ["task-12"],
  "attempts": 2
}
```

Task states:

```text
pending
ready
running
blocked
waiting
completed
failed
cancelled
```

## 12. Persistent State

Agent state must survive process or container restarts.

Persist at minimum:

```text
agent configuration
objective
task graph
current task
execution history
messages
artifacts
repository information
checkpoint
status
timestamps
errors
```

A restarted Juice Box should be capable of resuming from the latest safe checkpoint.

## 13. Repository Integration

Repository-backed execution is a core Juice Box feature.

At startup:

```text
1. Authenticate
2. Clone repository
3. Checkout requested base branch
4. Create agent work branch
5. Load repository instructions
6. Begin objective execution
```

During execution:

```text
inspect files
modify files
run commands
run tests
create artifacts
commit checkpoints
```

Upon success:

```text
commit final changes
push branch
optionally create pull request
attach execution report
```

Example naming convention:

```text
juicebox/test-commander/2026-08-14-api-coverage
```

## 14. Skills System

Skills should be portable packages that describe how an agent performs specialized work.

Example:

```yaml
name: playwright-testing
version: 1.0

description: >
  Create, execute, debug, and maintain Playwright tests.

tools:
  - shell
  - filesystem

requirements:
  commands:
    - node
    - npm
    - npx

instructions: |
  Inspect the project's Playwright configuration before creating tests.
  Follow existing test structure and naming conventions.
```

An agent should be able to discover its available skills at runtime.

Future capability:

```text
skill registry
skill versioning
skill installation
skill dependencies
skill permissions
dynamic skill loading
```

## 15. Tool Execution

Tools should expose a common interface.

Conceptually:

```python
class Tool:
    name: str

    async def execute(self, request: ToolRequest) -> ToolResult:
        ...
```

Example request:

```json
{
  "tool": "shell",
  "arguments": {
    "command": "pytest tests/api -q"
  }
}
```

Example response:

```json
{
  "status": "success",
  "exit_code": 0,
  "stdout": "84 passed",
  "stderr": ""
}
```

## 16. Security Model

Agents should operate using least privilege.

Configuration should control:

```text
filesystem access
shell access
network access
repository access
cloud access
environment variables
secret access
tool access
maximum runtime
compute resources
```

Potentially dangerous operations can require explicit approval.

Examples:

```text
merge pull request
delete cloud resource
deploy production
modify secrets
force push
delete repository data
```

## 17. Secrets

Secrets must never be embedded directly in agent specifications.

Support abstraction such as:

```yaml
secrets:
  - github-token
  - anthropic-api-key
  - aws-credentials
```

Backends may eventually include:

```text
environment variables
AWS Secrets Manager
HashiCorp Vault
Kubernetes Secrets
GitHub Actions secrets
```

## 18. Observability

Every Juice Box should expose real-time operational information.

Minimum metrics:

```text
agent status
current objective
current task
runtime
iteration count
LLM calls
token usage
estimated model cost
tool executions
errors
completed tasks
failed tasks
```

Logs should be structured.

```json
{
  "timestamp": "2026-08-14T21:30:00Z",
  "agent_id": "test-commander-42",
  "event": "tool_execution",
  "tool": "playwright",
  "status": "completed",
  "duration_ms": 14283
}
```

## 19. Event System

Internal operations should emit events.

Examples:

```text
agent.created
agent.started
agent.paused
agent.resumed
agent.completed
agent.failed

task.created
task.started
task.completed
task.failed

tool.started
tool.completed
tool.failed

objective.completed

artifact.created

approval.requested
approval.received
```

This enables external orchestrators and future multi-agent coordination.

## 20. Multi-Agent Architecture

Juice Box should ultimately support agents creating or delegating work to other agents.

Example:

```text
Project Orchestrator
        │
        ├── Dev Commander
        │
        ├── Test Commander
        │
        ├── Security Commander
        │
        └── Documentation Agent
```

The parent agent should be capable of:

```text
creating subordinate Juice Boxes
assigning objectives
sending messages
checking status
receiving results
canceling work
reassigning failed work
aggregating outputs
```

Example API:

```http
POST /orchestrations
GET  /orchestrations/{id}
```

## 21. API — MVP

Health

```http
GET /health
```

Agents

```http
POST   /agents
GET    /agents
GET    /agents/{id}
DELETE /agents/{id}
```

Lifecycle

```http
POST /agents/{id}/start
POST /agents/{id}/stop
POST /agents/{id}/restart
POST /agents/{id}/pause
POST /agents/{id}/resume
```

Messaging

```http
POST /agents/{id}/messages
GET  /agents/{id}/messages
```

Tasks

```http
GET /agents/{id}/tasks
GET /agents/{id}/tasks/{task_id}
```

Logs

```http
GET /agents/{id}/logs
```

Artifacts

```http
GET /agents/{id}/artifacts
GET /agents/{id}/artifacts/{artifact_id}
```

## 22. Suggested Technology Stack

Initial implementation:

```text
Language: Python 3.12+
API: FastAPI
Validation: Pydantic
Package management: PDM
Containers: Docker
Database: PostgreSQL
Local development: Docker Compose
Async work: asyncio
ORM: SQLAlchemy
Migrations: Alembic
API docs: OpenAPI
Testing: Pytest
```

Initial model providers:

```text
OpenAI
Anthropic
```

Repository integration:

```text
Git CLI
GitHub API
```

Later infrastructure:

```text
AWS ECS/Fargate
Amazon ECR
Amazon RDS
Amazon S3
Amazon EventBridge
Amazon SQS
AWS Secrets Manager
CloudWatch
```

## 23. Proposed Repository Structure

```text
juice-box/
│
├── README.md
├── pyproject.toml
├── Makefile
├── Dockerfile
├── docker-compose.yml
│
├── src/
│   └── juicebox/
│       │
│       ├── api/
│       │   ├── agents.py
│       │   ├── messages.py
│       │   ├── tasks.py
│       │   └── health.py
│       │
│       ├── agents/
│       │   ├── agent.py
│       │   ├── runner.py
│       │   └── lifecycle.py
│       │
│       ├── runtime/
│       │   ├── container.py
│       │   ├── workspace.py
│       │   └── checkpoint.py
│       │
│       ├── orchestration/
│       │   ├── orchestrator.py
│       │   └── scheduler.py
│       │
│       ├── skills/
│       │   ├── registry.py
│       │   └── loader.py
│       │
│       ├── tools/
│       │   ├── base.py
│       │   ├── shell.py
│       │   ├── filesystem.py
│       │   └── git.py
│       │
│       ├── providers/
│       │   ├── base.py
│       │   ├── openai.py
│       │   └── anthropic.py
│       │
│       ├── repository/
│       │   ├── git.py
│       │   └── github.py
│       │
│       ├── events/
│       │   └── bus.py
│       │
│       ├── persistence/
│       │   ├── models.py
│       │   └── database.py
│       │
│       └── config/
│           └── settings.py
│
├── skills/
│   ├── git/
│   ├── coding/
│   └── testing/
│
├── examples/
│   ├── test-commander.yaml
│   └── simple-coding-agent.yaml
│
└── tests/
    ├── unit/
    ├── integration/
    └── e2e/
```

## 24. MVP Scope

The first usable Juice Box should demonstrate one autonomous agent completing a repository-based objective.

MVP Workflow

```text
POST objective
      │
      ▼
Create Juice Box
      │
      ▼
Launch Agent Container
      │
      ▼
Clone Repository
      │
      ▼
Agent Analyzes Objective
      │
      ▼
Agent Executes Tools
      │
      ▼
Agent Modifies Repository
      │
      ▼
Run Verification
      │
      ▼
Commit Changes
      │
      ▼
Return Result
```

MVP Must Support

- Create an agent through the API.
- Pass an objective/specification.
- Pass a Git repository URL.
- Start an isolated agent runtime.
- Clone the repository into its workspace.
- Allow the agent to inspect and modify files.
- Allow shell command execution.
- Allow Git operations.
- Support at least one LLM provider.
- Maintain task/execution state.
- Expose status and logs.
- Accept messages while the agent is running.
- Stop/restart an agent.
- Detect completion or failure.
- Commit successful work to the repository.
- Produce a final execution report.

## 25. MVP Acceptance Test

The primary end-to-end acceptance test should use Test Commander as the first real Juice Box agent.

Input:

```text
Repository: test-commander-demo application

Objective:
Inspect the application and existing Playwright tests.
Identify one meaningful missing test scenario.
Implement the test.
Execute the suite.
Repair the test if necessary.
Commit the passing test to a Juice Box branch.
```

Expected behavior:

```text
1. Juice Box starts.
2. Test Commander initializes.
3. Repository is cloned.
4. Existing tests are inspected.
5. Coverage gap is identified.
6. New Playwright test is generated.
7. Test suite executes.
8. Failures are diagnosed if necessary.
9. Test passes.
10. Changes are committed.
11. Execution report is produced.
12. Agent enters COMPLETED state.
```

A successful execution of this scenario proves the core architecture.

## 26. Phase 2

Once the MVP works, add:

- PostgreSQL persistence
- restart/resume checkpoints
- skill registry
- richer artifact handling
- GitHub pull-request creation
- approval gates
- streaming events
- model usage/cost tracking
- agent resource limits
- web dashboard
- AWS ECS/Fargate execution
- remote workers

## 27. Phase 3 — Multi-Agent Orchestration

Introduce higher-order objectives and parent agents.

Example:

```yaml
goal: Release version 2.0 of the application

agents:
  - development
  - testing
  - security
  - documentation

success_criteria:
  - features implemented
  - tests passing
  - security checks passing
  - documentation updated
  - release candidate created
```

The orchestrator determines which Juice Boxes are required and delegates work accordingly.

## 28. Phase 4 — Autonomous Agent Platform

Longer-term capabilities:

- dynamic agent creation
- dynamic skill acquisition
- agent-to-agent messaging
- distributed scheduling
- agent marketplace/registry
- workflow visualization
- objective dependency graphs
- policy engine
- budget management
- automatic retries/recovery
- agent performance scoring
- learning from previous runs
- reusable organizational knowledge
- multi-repository objectives
- autonomous CI/CD workflows

## 29. Non-Goals for MVP

Do not initially build:

- graphical workflow designer
- Kubernetes support
- complex multi-agent consensus
- agent marketplace
- arbitrary distributed compute
- sophisticated memory architecture
- automatic production deployment
- dozens of LLM providers
- dynamic skill generation

The MVP should prove the fundamental abstraction:

Give an isolated agent a specification, skills, and a repository, then allow it to autonomously work toward a measurable goal while Juice Box manages its lifecycle, state, tools, and results.

## 30. Definition of Done

Juice Box v0.1 is complete when a developer can execute something conceptually equivalent to:

```bash
juicebox run \
  --agent test-commander \
  --repo https://github.com/example/project \
  --spec objective.yaml
```

and then:

```bash
juicebox status <run-id>
```

while Juice Box autonomously:

```text
creates the runtime
loads the agent
clones the repository
interprets the objective
plans work
executes tools
tracks progress
accepts additional instructions
verifies results
commits successful changes
records execution history
reports completion
```

without requiring the caller to manage the underlying agent execution loop.

That is the core contract of Juice Box.
