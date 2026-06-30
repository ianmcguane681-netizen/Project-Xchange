# COMP-001 Prompt Engine

Stores prompts, assigns them to Workers, versions them, marks status, runs simple sample tests, and records changelog entries.

The MVP test runner is deterministic: a test passes when the expected output is contained in the generated placeholder output. This keeps the prototype local and API-free while preserving the future interface for model-backed prompt testing.
