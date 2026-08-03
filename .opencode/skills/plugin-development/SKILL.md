---
name: plugin-development
description: >
  Comprehensive toolkit for developing OpenCode/Claude Code plugins.
  Covers hooks, MCP integration, plugin structure, commands, agents, skills, and settings.
  Use when the user wants to create a plugin, add a command, build an agent, or extend functionality.
  Triggers on: "create plugin", "build a plugin", "add a command", "create an agent", "plugin development",
  "extend functionality", "custom command", "slash command", "custom agent", "plugin structure".
license: MIT
metadata:
  author: OpenCode Skills (adapted from Anthropic claude-code plugin-dev)
  version: "1.0.0"
  category: plugin-development
  tags: "plugins, hooks, mcp, agents, commands, skills, development"
---

# Plugin Development Toolkit

Create high-quality plugins for Claude Code / OpenCode with expert guidance on hooks, MCP integration, plugin structure, commands, agents, and skills.

## Plugin Structure

Every plugin follows this standard structure:

```
plugin-name/
├── .claude-plugin/
│   └── plugin.json          # Plugin metadata (required)
├── commands/                # Slash commands (optional)
│   └── my-command.md
├── agents/                  # Specialized agents (optional)
│   └── my-agent.md
├── skills/                  # Agent Skills (optional)
│   └── my-skill/
│       └── SKILL.md
├── hooks/                   # Event handlers (optional)
│   └── hooks.json
├── .mcp.json                # External tool configuration (optional)
└── README.md                # Plugin documentation
```

## Plugin Metadata

File: `.claude-plugin/plugin.json`

```json
{
  "name": "my-plugin",
  "description": "What this plugin does",
  "version": "1.0.0",
  "author": {
    "name": "Your Name",
    "email": "you@example.com"
  },
  "homepage": "https://github.com/your/project"
}
```

## Commands

Slash commands in `commands/` are Markdown files with YAML frontmatter:

```markdown
---
allowed-tools: Bash(git status:*), Bash(git diff:*), Bash(gh pr create:*)
description: Commit, push, and open a PR
argument-hint: Optional commit message
---

## Context

- Current git status: !`git status`
- Current git diff: !`git diff HEAD`
- Current branch: !`git branch --show-current`

## Task

Based on the above changes:
1. Create a new branch if on main
2. Create a single commit with an appropriate message
3. Push the branch to origin
4. Create a pull request using `gh pr create`
5. Do ALL of the above in a single message
```

### Frontmatter Fields

| Field | Required | Description |
|-------|----------|-------------|
| `description` | Yes | Brief description shown in help |
| `allowed-tools` | No | Restrict tools: `Bash(gh pr view:*)` or comma-separated list |
| `argument-hint` | No | Hint for optional arguments (`$ARGUMENTS` in body) |
| `name` | No | Override command name (defaults to filename) |

### Allowed Tools Pattern

Format: `ToolName(pattern:*)` where pattern restricts arguments:

```
Bash(gh pr view:*)           # Bash only with `gh pr view` commands
Bash(gh pr diff:*)           # Bash only with `gh pr diff` commands
mcp__github_inline_comment__create_inline_comment  # Specific MCP tool
Glob, Grep, Read             # General tools (no restriction)
```

## Agents

Agents in `agents/` are Markdown files for specialized sub-tasks:

```markdown
---
name: code-analyzer
description: Analyzes codebase for specific patterns
tools: Glob, Grep, Read, WebFetch, TodoWrite, WebSearch
model: sonnet
color: yellow
---

You are an expert code analyst. [Detailed instructions for the agent...]
```

### Frontmatter Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Agent identifier used in orchestration |
| `description` | Yes | What this agent does |
| `tools` | Yes | Tool access: Glob, Grep, Read, WebFetch, TodoWrite, WebSearch, Bash |
| `model` | Yes | Model: sonnet, opus, or haiku |
| `color` | No | Display color: yellow, green, red, blue, purple |

### Best Practices for Agents

- **Single responsibility**: One agent = one job
- **Return lists of files**: Agents should identify key files for the orchestrator to read
- **Specific instructions**: Tell the agent exactly what to look for, what format to return
- **Tool whitelist**: Only give tools the agent actually needs

## Skills

Skills in `skills/` are loaded into context when triggered:

```markdown
---
name: my-skill
description: >
  What this skill does and when to use it.
  Triggers on: [trigger phrases]
---

# Skill Title

Skill content...
```

### Progressive Disclosure

Skills should use progressive disclosure:
1. **Lean core** — Quick overview and immediate value
2. **Detailed reference** — Deeper sections for complex topics
3. **Working examples** — Copy-paste ready code
4. **Utility scripts** — Scripts that automate common tasks

### Strong Triggers

Write description triggers that fire on exact user phrases:
- ✅ "audit this code for vulnerabilities"
- ✅ "review this PR for security issues"
- ❌ "code" (too broad — fires on everything)

## Hooks

Hooks respond to lifecycle events. Defined in `hooks/hooks.json`:

```json
{
  "description": "My plugin description",
  "hooks": {
    "SessionStart": [{
      "hooks": [{
        "type": "command",
        "command": "bash script.sh"
      }]
    }],
    "PostToolUse": [{
      "hooks": [{
        "type": "command",
        "command": "bash hook.sh"
      }],
      "matcher": "Edit|Write|MultiEdit"
    }],
    "Stop": [{
      "hooks": [{
        "type": "command",
        "command": "bash hook.sh",
        "asyncRewake": true,
        "rewakeMessage": "Background check findings — address and continue"
      }]
    }]
  }
}
```

### Hook Events

| Event | When it fires | Use Case |
|-------|--------------|----------|
| `SessionStart` | Session begins | Load context, run setup |
| `UserPromptSubmit` | User sends a message | Capture git baseline, log |
| `PreToolUse` | Before any tool call | Validate, block dangerous ops |
| `PostToolUse` | After a tool call | Pattern check on Edit/Write, commit review |
| `Stop` | Claude stops | Final review, trigger async fixes |
| `SessionEnd` | Session ends | Cleanup, flush logs |

### Matcher Patterns

Restrict which tool calls trigger a hook:

| Pattern | Matches |
|---------|---------|
| `Edit\|Write\|MultiEdit` | File writing tools |
| `Bash` | All bash commands |
| `Bash(git commit:*)` | Git commit commands only |
| `Bash(git push:*)` | Git push commands only |
| `Read\|Grep` | Read-only tools |

## OpenCode Native Plugin Hooks (TypeScript)

OpenCode supports native TypeScript plugins with richer hooks than the shell-based Claude Code hooks. These hooks are registered programmatically in a TypeScript plugin file and can directly interact with the OpenCode SDK and tools.

### Plugin Structure

```
plugin-directory/
├── plugin.ts              # Main plugin code (default export)
├── package.json           # npm package
├── tsconfig.json
└── README.md
```

### Available Hooks

| Hook | Event | Use Case | Signature |
|------|-------|----------|-----------|
| `config` | Plugin loads | Register slash commands, add skill paths | `config(conf: Config)` |
| `chat.message` | Each user message | Load context, search memories | `chat.message(msg, ctx)` |
| `tool.execute.before` | Before any tool call | Validate, block, rewrite | `tool.execute.before(tool, args)` |
| `tool.execute.after` | After any tool call | Log, capture output, error lookup | `tool.execute.after(tool, result)` |
| `experimental.chat.messages.transform` | Before LLM call | Inject context into prompt | `experimental.chat.messages.transform(msgs)` |
| `experimental.session.compacting` | Context window full | Save session state, preserve context | `experimental.session.compacting(state)` |
| `shell.env` | Shell spawn | Export environment variables | `shell.env($)` |

### Reference: Mem0 Plugin Pattern

The [mem0ai/mem0](https://github.com/mem0ai/mem0) plugin is the reference implementation:

```
.opencode-plugin/
├── opencode-mem0.ts    # Main plugin — registers 9 memory tools + all hooks
├── dream.ts             # Memory consolidation
├── scope.ts             # Project/user scope management
├── api-key.ts           # API key resolution
├── project.ts           # Git remote → project ID mapping
├── telemetry.ts         # Event capture
├── api-key.test.ts      # Tests
└── README.md
```

**Key patterns from the reference implementation:**

1. **Tool registration** — Tools are native OpenCode tools (not MCP):
```typescript
import { tool } from "@opencode-ai/plugin";
export const addMemory = tool({
  name: "add_memory",
  description: "Save text to memory",
  parameters: z.object({ text: z.string() }),
  execute: async ({ text }) => { /* ... */ },
});
```

2. **Config hook** — Registers slash commands and skill paths:
```typescript
config(conf) {
  conf.command("mem0-remember", "Save to memory", async (args) => { /* ... */ });
  // Add skill directory for in-place discovery
  conf.skills?.paths?.push(join(__dirname, "..", "skills"));
}
```

3. **Chat message hook** — Auto-loads context before each prompt:
```typescript
chat.message(msg, ctx) {
  // On session start: load prior memories
  // Before each prompt: search relevant memories
  // Periodically: auto-capture learnings
}
```

### Comparing Hook Systems

| Feature | Claude Code Shell Hooks | OpenCode Native Hooks |
|---------|------------------------|----------------------|
| Language | Bash/Python scripts | TypeScript (native) |
| Registration | hooks.json | Plugin code |
| State | File-based state | In-memory + plugin state |
| Tools | Via CLI + MCP | Native OpenCode tools |
| Speed | Process spawn per event | In-process, instant |
| Complexity | JSON config + scripts | Full programming model |
| Best for | Simple validation, git hooks | Rich context management, memory |

## MCP Integration

File: `.mcp.json`

```json
{
  "mcpServers": {
    "my-server": {
      "type": "stdio",
      "command": "uvx",
      "args": ["my-mcp-server"],
      "env": {
        "MY_KEY": "value"
      }
    }
  }
}
```

### MCP Server Types

| Type | Description |
|------|-------------|
| `stdio` | Local process (stdin/stdout) |
| `sse` | Remote server-sent events |
| `http` | HTTP-based server |

## Complete Example: Minimal Plugin

```
my-plugin/
├── .claude-plugin/
│   └── plugin.json
├── commands/
│   └── hello.md
└── README.md
```

`.claude-plugin/plugin.json`:
```json
{
  "name": "my-plugin",
  "description": "Says hello",
  "version": "1.0.0"
}
```

`commands/hello.md`:
```markdown
---
description: Say hello
argument-hint: Name to greet
---

Say hello to $ARGUMENTS or the world if no name given.
```

## Skill Graph

| This Skill | Connects To | Why |
|---|---|---|
| plugin-development | behavioral-rules | Hooks system enables pattern-matched rules |
| plugin-development | git-automation | Git hooks can be registered via plugins |

## Testing & Validation

1. **Test the command**: Run `/my-command` and verify it works
2. **Test agents**: Launch agents as sub-tasks during a command
3. **Check hooks**: Trigger the hook event and check output
4. **Validate structure**: Verify all files exist and have correct format
