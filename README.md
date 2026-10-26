# Ok Agent

A minimal CLI coding agent with **zero external package dependencies**.

## Features

### Tools

- **Read**: Read file. Supported image formats: jpeg, png, and webp.
- **Write**: Write and overwrite files.
- **Edit**: Edit file by exact text replacement.
- **Shell**: Execute shell commands. Handles large outputs by saving to a temp file and does cleanup at exit.

### Sessions

- Scoped to working directory.
- Message history is saved in `~/.local/state/ok/history` as jsonl files.
- Resume sessions using `ok -r`, which by default resumes the previous session in the current working directory.

## Configuration

[Example configuration](./examples/config.json)

## Limitations

- No Compaction.
- No MCP support.
- No Skills support.
- Synchronous.
