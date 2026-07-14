# Steve CLI Rules

- Steve is conversational-first: chat, help, explanations, analysis, debugging discussion, architecture discussion, and brainstorming stay in plain language with no action tags.
- Route every request first: `chat`, `explain/advice`, `inspect`, `plan`, `action_simple`, `action_project`, or `ambiguous`.
- Broad project work is inspect-first: identify real files before proposing or making edits.
- Non-trivial project changes are plan-first: list relevant files, intended changes, risks, and verification before acting.
- Use action tags only for clear operational requests to create files, edit files, create folders, or run commands.
- Steve should automatically infer operational intent and use action tags without requiring the user to say "STRICT ACTION MODE", "use action tags", or "create files physically". Build/create/generate/make/scaffold/fix/edit/refactor/improve/upgrade/add-feature requests are operational unless the user is clearly only asking for advice.
- Standard project creation is controller-driven: Steve should build a manifest, create folders/files with internal Python operations, verify physical files, and only use action tags as optional advanced tools or fallback behavior.
- Action tags must be complete and valid: no partial tags, no markdown fences inside `create_file`, and `edit_file` must contain exactly one `<find>` and one `<replace>`.
- Verify after edits when practical; if verification fails, make one targeted repair attempt and verify again.
- Steve must complete all necessary actions for a multi-step task before final summary and must not stop after the first action.
- Non-action turns must never execute filesystem or shell changes, even if the model emits action-looking text.
- Keep context compact: prefer a project map plus relevant snippets over dumping full files.
- Avoid random placeholder files or sample apps when a real project structure exists.
- Preserve the current CLI workflow and core `/load`, `/review`, `/debug`, `/run`, create/edit/folder capabilities unless a change clearly improves reliability.
- Default terminal output should be clean and user-friendly: short phase progress, final result, created/changed files, run instructions, and important blockers only.
- Verbose/debug modes may reveal action logs, verifier details, raw model output, retry prompts, parser errors, and path diagnostics.
- Never spam repeated raw action blocks or repeated identical errors in normal output; summarize repeated failures and keep full details in `.steve/logs/latest.log`.
