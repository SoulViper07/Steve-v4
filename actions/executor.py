import os
import re
import shutil
import subprocess
import threading
import queue
import time
import difflib
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any

from core.models import RequestRoute, ExecutionPlan
from core.file_context import FileContext
from config.settings import RUN_TIMEOUT, PLAIN_UI
from ui.terminal_renderer import (
    console, _plain_terminal, _rich_terminal, _clean_mode,
    get_symbol, _err, _warn, _info, _step, Panel, Rule,
    get_pipeline,
)

def _find_next_action(text: str, start: int) -> Optional[Tuple[str, int, int, str]]:
    """Returns (kind, start_idx, end_idx, full_tag_text)."""
    tags = [
        ("create", '<create_file'),
        ("replace", '<replace_file'),
        ("edit", '<edit_file'),
        ("patch", '<patch_file'),
        ("folder", '<create_folder'),
        ("run", '<run_command>'),
    ]
    best_idx = -1
    best_kind = ""
    best_opener = ""

    for kind, opener in tags:
        idx = text.find(opener, start)
        if idx != -1 and (best_idx == -1 or idx < best_idx):
            best_idx = idx
            best_kind = kind
            best_opener = opener

    if best_idx == -1:
        return None

    closer = ""
    if best_kind == "folder":
        closer = '/>'
    else:
        closer = f'</{best_opener[1:]}'
        if '>' in closer:
            closer = closer[:closer.find('>')+1]
        else:
            closer += '>'

    end_idx = text.find(closer, best_idx)
    if end_idx == -1:
        return ("incomplete", best_idx, -1, text[best_idx:])

    full_end = end_idx + len(closer)
    return (best_kind, best_idx, full_end, text[best_idx:full_end])

class FilesystemExecutor:
    """Parses and executes filesystem action tags from AI responses."""
    SMALL_FRONTEND_EXTS = {".html", ".css", ".js", ".jsx", ".ts", ".tsx"}
    SMALL_FRONTEND_MAX_BYTES = 40000

    # Regexes for action tags
    RE_CREATE_FILE   = re.compile(r'<create_file\s+path="([^"]*)">([\s\S]*?)</create_file>', re.MULTILINE)
    RE_REPLACE_FILE  = re.compile(r'<replace_file\s+path="([^"]*)">([\s\S]*?)</replace_file>', re.MULTILINE)
    RE_EDIT_FILE     = re.compile(r'<edit_file\s+path="([^"]*)">([\s\S]*?)</edit_file>', re.MULTILINE)
    RE_PATCH_FILE    = re.compile(r'<patch_file\s+path="([^"]*)">([\s\S]*?)</patch_file>', re.MULTILINE)
    RE_FIND          = re.compile(r'<find>([\s\S]*?)</find>')
    RE_REPLACE       = re.compile(r'<replace>([\s\S]*?)</replace>')
    RE_APPEND        = re.compile(r'<append>([\s\S]*?)</append>')
    RE_INSERT_AFTER  = re.compile(r'<insert_after\s+find="([^"]*)">([\s\S]*?)</insert_after>', re.MULTILINE)
    RE_INSERT_BEFORE = re.compile(r'<insert_before\s+find="([^"]*)">([\s\S]*?)</insert_before>', re.MULTILINE)
    RE_CREATE_FOLDER = re.compile(r'<create_folder\s+path="([^"]*)"\s*/>')
    RE_RUN_CMD       = re.compile(r'<run_command>([\s\S]*?)</run_command>', re.MULTILINE)

    def __init__(self, workdir: Path, file_ctx: FileContext):
        self.workdir  = workdir
        self.file_ctx = file_ctx
        self.actions_done = []
        self.current_route: Optional[RequestRoute] = None
        self.allowed_create_paths: set[str] = set()
        self.project_root: Optional[Path] = None
        self.generated_file_contents: Dict[str, str] = {}
        self.frontend_buffers: Dict[str, str] = {}
        self.template_variables: Dict[str, str] = {}
        self.repair_context: Dict[str, str] = {}
        self.verifier_target_paths: List[str] = []

    def reset_project_generation_state(self):
        self.allowed_create_paths = set()
        self.project_root = None
        self.generated_file_contents.clear()
        self.frontend_buffers.clear()
        self.template_variables.clear()
        self.repair_context.clear()
        self.verifier_target_paths.clear()

    def begin_turn(self, route: RequestRoute, plan: Optional[ExecutionPlan] = None):
        self.current_route = route
        # plan.allowed_create_paths is not in the ExecutionPlan model I created, 
        # but I'll add it or adapt it.
        # self.allowed_create_paths = set((plan.allowed_create_paths if plan else []) or [])
        self.project_root = Path(plan.project_root).resolve() if plan and hasattr(plan, 'project_root') and plan.project_root else None
        self.verifier_target_paths = list((plan.manifest.verifier_targets if plan and hasattr(plan.manifest, 'verifier_targets') else []) or [])

    def _malformed_result(self, msg: str, path: str = "") -> Dict[str, Any]:
        return {"type": "invalid", "path": path, "ok": False, "msg": msg}

    def _content_is_fake_or_omitted(self, content: str) -> str:
        stripped = content.strip()
        lowered = stripped.lower()
        if "[content omitted from history]" in lowered:
            return "content was omitted from history"
        compact = re.sub(r"\s+", " ", lowered)
        fake_values = {"...", "todo", "placeholder", "incomplete", "[todo]", "(todo)"}
        if compact in fake_values:
            return f"content is a placeholder: {stripped[:40]}"
        nonempty = [line.strip().lower() for line in stripped.splitlines() if line.strip()]
        if nonempty and all(line in fake_values for line in nonempty):
            return "content contains only placeholder lines"
        return ""

    def _strip_single_code_fence(self, content: str) -> str:
        stripped = content.strip("\n")
        match = re.fullmatch(r"\s*```[A-Za-z0-9_-]*\s*\n([\s\S]*?)\n\s*```\s*", stripped)
        return match.group(1) if match else content

    def _frontend_incomplete_reason(self, path_str: str, content: str) -> str:
        suffix = Path(path_str).suffix.lower()
        if suffix not in self.SMALL_FRONTEND_EXTS:
            return ""
        text = content.strip()
        lower = text.lower()
        if len(text) < 20:
            return "content is too short to be a complete frontend file"
        if text.endswith(("...", "/*", "/**", "//", "{", "(", "[", ",", ".", "+", "-", "=>", ":", "=")):
            return "content appears truncated at the end"
        if suffix == ".html":
            if "</html>" not in lower:
                return "HTML is missing closing </html>"
            for tag in ("head", "body"):
                if f"<{tag}" in lower and f"</{tag}>" not in lower:
                    return f"HTML is missing closing </{tag}>"
            void_tags = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
            stack = []
            for match in re.finditer(r"<\s*(/)?\s*([a-zA-Z][\w:-]*)([^>]*)>", text):
                closing, tag, rest = match.group(1), match.group(2).lower(), match.group(3) or ""
                if tag.startswith("!"):
                    continue
                if closing:
                    if tag in stack[::-1]:
                        while stack:
                            top = stack.pop()
                            if top == tag:
                                break
                elif tag not in void_tags and not rest.strip().endswith("/"):
                    stack.append(tag)
            important_unclosed = [tag for tag in stack if tag in {"html", "head", "body", "main", "section", "div", "form", "ul", "script"}]
            if important_unclosed:
                return "HTML has unclosed tag: " + important_unclosed[-1]
        if suffix == ".css":
            if text.count("{") != text.count("}"):
                return "CSS has unbalanced braces or ends mid-rule"
            last_rule_start = text.rfind("{")
            last_rule_end = text.rfind("}")
            if last_rule_start > last_rule_end:
                return "CSS ends mid-rule"
            stripped = re.sub(r"/\*[\s\S]*?\*/", "", text).strip()
            tail = stripped[stripped.rfind("{") + 1:stripped.rfind("}")].strip() if "{" in stripped and "}" in stripped else ""
            if tail and ":" in tail and not any(part.strip().endswith((";", "}")) for part in tail.splitlines() if part.strip()):
                return "CSS appears to end mid-declaration"
        if suffix in {".js", ".jsx", ".ts", ".tsx"}:
            pairs = {")": "(", "}": "{", "]": "["}
            stack = []
            quote = ""
            escape = False
            line_comment = False
            block_comment = False
            for idx, ch in enumerate(text):
                nxt = text[idx + 1] if idx + 1 < len(text) else ""
                if line_comment:
                    if ch == "\n":
                        line_comment = False
                    continue
                if block_comment:
                    if ch == "*" and nxt == "/":
                        block_comment = False
                    continue
                if quote:
                    if escape:
                        escape = False
                    elif ch == "\\":
                        escape = True
                    elif ch == quote:
                        quote = ""
                    continue
                if ch == "/" and nxt == "/":
                    line_comment = True
                    continue
                if ch == "/" and nxt == "*":
                    block_comment = True
                    continue
                if ch in {"'", '"', "`"}:
                    quote = ch
                elif ch in "({[":
                    stack.append(ch)
                elif ch in pairs:
                    if stack and stack[-1] == pairs[ch]:
                        stack.pop()
                    else:
                        return "JavaScript has an unmatched closing bracket"
            if quote:
                return "JavaScript ends inside a string/template"
            if block_comment:
                return "JavaScript ends inside a block comment"
            if stack:
                return "JavaScript has unclosed block/function/bracket"
        return ""

    def _validate_single_tag(self, tag_text: str):
        stripped = tag_text.strip()
        checks = [
            ("folder", self.RE_CREATE_FOLDER),
            ("create", self.RE_CREATE_FILE),
            ("replace", self.RE_REPLACE_FILE),
            ("edit", self.RE_EDIT_FILE),
            ("run", self.RE_RUN_CMD),
        ]
        matches = []
        for kind, regex in checks:
            match = regex.fullmatch(stripped)
            if match:
                matches.append((kind, match))
        if len(matches) != 1:
            return None, self._malformed_result("Malformed or incomplete action tag blocked")
        kind, match = matches[0]
        path = match.group(1).strip() if kind in {"folder", "create", "replace", "edit"} else ""
        if kind in {"folder", "create", "replace", "edit"} and not path:
            return None, self._malformed_result("Action tag has an empty path")
        if kind in {"create", "replace"}:
            content = self._strip_single_code_fence(match.group(2))
            if "```" in content:
                return None, self._malformed_result(f"Blocked {kind}_file for {path}: content contains markdown fences", path)
            fake_reason = self._content_is_fake_or_omitted(content)
            if fake_reason:
                return None, self._malformed_result(f"Blocked {kind}_file for {path}: {fake_reason}; provide complete full file content", path)
            incomplete_reason = self._frontend_incomplete_reason(path, content)
            if incomplete_reason:
                return None, self._malformed_result(f"Blocked {kind}_file for {path}: {incomplete_reason}; rewrite the entire file with complete content", path)
        if kind == "edit":
            block = match.group(2)
            find_m = self.RE_FIND.search(block)
            replace_m = self.RE_REPLACE.search(block)
            if not find_m or not replace_m:
                return None, self._malformed_result(f"Malformed edit block for {path}", path)
            if not find_m.group(1).strip("\n"):
                return None, self._malformed_result(f"Blocked edit for {path}: find text is empty", path)
            if block.count("<find>") != 1 or block.count("</find>") != 1 or block.count("<replace>") != 1 or block.count("</replace>") != 1:
                return None, self._malformed_result(f"Malformed edit block for {path}: expected one find and one replace", path)
        return (kind, match), None

    def action_problems(self, response: str) -> List[Dict[str, Any]]:
        problems = []
        for opener in ("<create_file", "<replace_file", "<edit_file", "<create_folder", "<run_command"):
            start = 0
            while True:
                idx = response.find(opener, start)
                if idx == -1:
                    break
                found = _find_next_action(response, idx)
                if found is None or found[0] == "incomplete":
                    problems.append(self._malformed_result(f"Incomplete action tag blocked near: {opener}"))
                    start = idx + len(opener)
                    continue
                _, _, end, tag_text = found
                _, error = self._validate_single_tag(tag_text)
                if error:
                    problems.append(error)
                start = end
        return problems

    def execute_all(self, response: str) -> List[Dict[str, Any]]:
        """Find and execute all action tags in a response. Returns list of result messages."""
        results = []
        seen = set()

        start = 0
        while True:
            found = _find_next_action(response, start)
            if found is None:
                break
            if found[0] == "incomplete":
                results.append(self._malformed_result("Incomplete action tag blocked"))
                break
            _, _, end, tag_text = found
            start = end
            normalized = tag_text.strip()
            if normalized in seen:
                continue
            seen.add(normalized)
            result = self.execute_tag(normalized)
            results.extend(result)

        return results

    def has_actions(self, response: str) -> bool:
        return bool(
            self.RE_CREATE_FILE.search(response) or
            self.RE_REPLACE_FILE.search(response) or
            self.RE_EDIT_FILE.search(response) or
            self.RE_CREATE_FOLDER.search(response) or
            self.RE_RUN_CMD.search(response)
        )

    def execute_tag(self, tag_text: str) -> List[Dict[str, Any]]:
        parsed, error = self._validate_single_tag(tag_text)
        if error:
            return [error]
        kind, match = parsed
        if kind == "folder":
            return [self._create_folder(match.group(1).strip())]
        if kind == "create":
            return [self._create_file(match.group(1).strip(), self._strip_single_code_fence(match.group(2)))]
        if kind == "replace":
            return [self._replace_file(match.group(1).strip(), self._strip_single_code_fence(match.group(2)))]
        if kind == "edit":
            return [self._edit_file(match.group(1).strip(), match.group(2))]
        if kind == "run":
            return [self._run_command(match.group(1).strip())]
        return [self._malformed_result("Unsupported action tag blocked")]

    def touched_paths(self, results: List[Dict[str, Any]]) -> List[str]:
        return [
            r.get("abs_path") or r["path"] for r in results
            if r.get("ok") and r.get("type") in ("create", "replace", "edit", "folder") and r.get("path")
        ]

    def _resolve(self, path_str: str) -> Path:
        p = Path(path_str)
        return (p if p.is_absolute() else self.workdir / p).resolve()

    def _target_root(self) -> Path:
        return (self.project_root or self.workdir).resolve()

    def _validate_project_path(self, path: Path, path_str: str, kind: str) -> Optional[Dict[str, Any]]:
        if not self.current_route or self.current_route.mode != "action_project":
            return None
        root = self._target_root()
        resolved = path.resolve()
        if kind == "folder" and resolved == root:
            return None
        try:
            resolved.relative_to(root)
        except ValueError:
            return {
                "type": kind,
                "path": path_str,
                "ok": False,
                "msg": f"Blocked {kind} outside target project folder: {path_str}. Target project folder is {root}",
            }
        return None

    def _backup_file(self, path: Path):
        backup = path.with_suffix(path.suffix + ".bak")
        shutil.copy2(path, backup)
        return backup

    def _verify_written_file(self, path: Path, expected_text: str) -> Tuple[bool, str]:
        try:
            if not path.exists():
                return False, "file does not exist after write"
            if path.stat().st_size <= 0:
                return False, "file is empty after write"
            written = path.read_text(encoding="utf-8")
            if not written.strip():
                return False, "file is empty after write"
            if written != expected_text:
                return False, "file content does not match intended write"
            return True, ""
        except Exception as e:
            return False, str(e)

    def _normalize_ws_with_map(self, text: str) -> Tuple[str, List[int]]:
        out = []
        mapping = []
        in_ws = False
        for idx, ch in enumerate(text):
            if ch.isspace():
                if not in_ws:
                    out.append(" ")
                    mapping.append(idx)
                    in_ws = True
            else:
                out.append(ch)
                mapping.append(idx)
                in_ws = False
        return "".join(out), mapping

    def _find_whitespace_normalized_span(self, haystack: str, needle: str) -> Optional[Tuple[int, int]]:
        norm_hay, hay_map = self._normalize_ws_with_map(haystack)
        norm_needle, _ = self._normalize_ws_with_map(needle)
        if not norm_needle:
            return None
        start = norm_hay.find(norm_needle)
        if start == -1:
            return None
        end_pos = start + len(norm_needle) - 1
        if end_pos >= len(hay_map):
            return None
        start_idx = hay_map[start]
        end_idx = hay_map[end_pos] + 1
        return start_idx, end_idx

    def _find_fuzzy_span(self, haystack: str, needle: str) -> Optional[Tuple[int, int, float]]:
        hay_lines = haystack.splitlines()
        needle_lines = needle.splitlines()
        if not hay_lines or not needle_lines:
            return None
        window = max(1, len(needle_lines))
        best = None
        line_offsets = []
        offset = 0
        for line in hay_lines:
            line_offsets.append(offset)
            offset += len(line) + 1
        needle_norm = " ".join(part.strip() for part in needle_lines if part.strip())
        if not needle_norm:
            return None
        for start in range(0, max(1, len(hay_lines) - window + 1)):
            block_lines = hay_lines[start:start + window]
            block = "\n".join(block_lines)
            block_norm = " ".join(part.strip() for part in block_lines if part.strip())
            if not block_norm:
                continue
            ratio = difflib.SequenceMatcher(None, needle_norm, block_norm).ratio()
            if best is None or ratio > best[2]:
                start_idx = line_offsets[start]
                end_line = min(len(hay_lines), start + window) - 1
                end_idx = line_offsets[end_line] + len(hay_lines[end_line])
                best = (start_idx, end_idx, ratio)
        if best and best[2] >= 0.72:
            return best
        return None

    def _looks_like_complete_frontend_file(self, path: Path, text: str) -> bool:
        lower = text.lower()
        ext = path.suffix.lower()
        if ext == ".html":
            return len(text.strip()) >= 80 and ("<!doctype" in lower or "<html" in lower or "<body" in lower)
        if ext == ".css":
            return len(text.strip()) >= 20 and "{" in text and "}" in text
        if ext in {".js", ".jsx", ".ts", ".tsx"}:
            return len(text.strip()) >= 80 and any(token in text for token in ("const ", "function ", "export ", "document.", "addEventListener"))
        return False

    def _can_overwrite_small_frontend(self, path: Path, replace_text: str) -> bool:
        if path.suffix.lower() not in self.SMALL_FRONTEND_EXTS:
            return False
        try:
            if path.stat().st_size > self.SMALL_FRONTEND_MAX_BYTES:
                return False
        except OSError:
            return False
        return self._looks_like_complete_frontend_file(path, replace_text)

    def _create_folder(self, path_str: str) -> Dict[str, Any]:
        path = self._resolve(path_str)
        blocked = self._validate_project_path(path, path_str, "folder")
        if blocked:
            return blocked
        try:
            path.mkdir(parents=True, exist_ok=True)
            pipeline = get_pipeline()
            if pipeline:
                pipeline.folder_created(path_str)
            return {"type": "folder", "path": path_str, "abs_path": str(path), "ok": True, "msg": f"Created folder: {path_str} at {path}"}
        except Exception as e:
            return {"type": "folder", "path": str(path), "ok": False, "msg": f"Failed to create folder {path_str}: {e}"}

    def _create_file(self, path_str: str, content: str) -> Dict[str, Any]:
        path = self._resolve(path_str)
        content = content.strip("\n")
        blocked = self._validate_project_path(path, path_str, "create")
        if blocked:
            return blocked
        try:
            if self.current_route and self.current_route.mode == "action_project":
                if not path.parent.exists():
                    return {"type": "create", "path": path_str, "ok": False, "msg": f"Blocked create_file for {path_str}: parent folder does not exist in current project"}
            path.parent.mkdir(parents=True, exist_ok=True)
            existed = path.exists()
            if existed:
                try:
                    existing_text = path.read_text(encoding="utf-8", errors="replace")
                    if existing_text == content and path.stat().st_size > 0:
                        lines = content.count("\n") + 1
                        return {"type": "create", "path": path_str, "abs_path": str(path), "ok": True, "msg": f"Already up to date: {path_str} ({lines} lines, {path.stat().st_size} bytes) at {path}"}
                except Exception:
                    pass
            if existed:
                self._backup_file(path)
            path.write_text(content, encoding="utf-8")
            ok, detail = self._verify_written_file(path, content)
            if not ok:
                return {"type": "create", "path": path_str, "ok": False, "msg": f"Write verification failed for {path_str}: {detail}"}
            if path_str in self.file_ctx.files or str(path) in self.file_ctx.files:
                self.file_ctx.reload(path_str)
            self.file_ctx.note_modified([path_str])
            action = "Overwrote" if existed else "Created"
            lines = content.count("\n") + 1
            size = path.stat().st_size
            pipeline = get_pipeline()
            if pipeline:
                summary = f"{lines} lines, {size} bytes"
                pipeline.file_created(f"{path_str} ({summary})")
            return {"type": "create", "path": path_str, "abs_path": str(path), "ok": True, "msg": f"{action} {path_str} ({lines} lines, {size} bytes) at {path}"}
        except Exception as e:
            return {"type": "create", "path": path_str, "ok": False, "msg": f"Failed to create {path_str}: {e}"}

    def _replace_file(self, path_str: str, content: str) -> Dict[str, Any]:
        result = self._create_file(path_str, content)
        result["type"] = "replace"
        if result.get("ok"):
            result["msg"] = result.get("msg", "").replace("Created", "Replaced").replace("Overwrote", "Replaced")
        return result

    def _edit_file(self, path_str: str, block: str) -> Dict[str, Any]:
        path = self._resolve(path_str)
        blocked = self._validate_project_path(path, path_str, "edit")
        if blocked:
            return blocked
        find_m = self.RE_FIND.search(block)
        replace_m = self.RE_REPLACE.search(block)
        if not find_m or not replace_m:
            return {"type": "edit", "path": path_str, "ok": False, "msg": f"Malformed edit block for {path_str}"}
        find_text = find_m.group(1).strip("\n")
        replace_text = replace_m.group(1).strip("\n")
        try:
            if not path.exists():
                return {"type": "edit", "path": path_str, "ok": False, "msg": f"File not found: {path_str}"}
            original = path.read_text(encoding="utf-8")
            strategy = "exact"
            new_content = None
            if find_text in original:
                count = original.count(find_text)
                if count > 1:
                    return {"type": "edit", "path": path_str, "ok": False, "msg": f"Found {count} exact matches in {path_str} - find text must be unique"}
                new_content = original.replace(find_text, replace_text, 1)
            else:
                span = self._find_whitespace_normalized_span(original, find_text)
                if span:
                    strategy = "normalized-whitespace"
                    new_content = original[:span[0]] + replace_text + original[span[1]:]
                else:
                    fuzzy = self._find_fuzzy_span(original, find_text)
                    if fuzzy:
                        strategy = f"fuzzy ({fuzzy[2]:.2f})"
                        new_content = original[:fuzzy[0]] + replace_text + original[fuzzy[1]:]
                    elif self._can_overwrite_small_frontend(path, replace_text):
                        strategy = "full-overwrite"
                        new_content = replace_text
                    else:
                        frontend_hint = ""
                        if path.suffix.lower() in self.SMALL_FRONTEND_EXTS:
                            frontend_hint = " Regenerate the full file with create_file or a complete overwrite-ready edit."
                        return {"type": "edit", "path": path_str, "ok": False, "msg": f"Exact, normalized-whitespace, and fuzzy matching all failed for {path_str}; no changes made.{frontend_hint}"}
            self._backup_file(path)
            path.write_text(new_content, encoding="utf-8")
            ok, detail = self._verify_written_file(path, new_content)
            if not ok:
                return {"type": "edit", "path": path_str, "ok": False, "msg": f"Edit verification failed for {path_str}: {detail}"}
            if path_str in self.file_ctx.files or str(path) in self.file_ctx.files:
                self.file_ctx.reload(path_str)
            self.file_ctx.note_modified([path_str])
            pipeline = get_pipeline()
            if pipeline and ok:
                summary = f"via {strategy}"
                pipeline.file_edited(path_str, summary)
            return {"type": "edit", "path": path_str, "abs_path": str(path), "ok": True, "msg": f"Patched {path_str} successfully via {strategy} at {path}"}
        except Exception as e:
            return {"type": "edit", "path": path_str, "ok": False, "msg": f"Edit failed for {path_str}: {e}"}

    def _run_command(self, cmd: str) -> Dict[str, Any]:
        """Run a shell command, capture output, return result."""
        if _plain_terminal():
            print(f"\n  RUN {cmd}")
        else:
            sym = get_symbol("$", "$")
            console.print(f"\n  [yellow]{sym}[/yellow] [dim]Running:[/dim] [bold]{cmd}[/bold]")
        output_parts = []
        q = queue.Queue()

        def _reader(pipe):
            try:
                for line in iter(pipe.readline, ""):
                    q.put(line)
            finally:
                pipe.close()
        try:
            proc = subprocess.Popen(
                cmd,
                shell=True,
                cwd=str(self.workdir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            assert proc.stdout is not None
            reader = threading.Thread(target=_reader, args=(proc.stdout,), daemon=True)
            reader.start()
            deadline = time.monotonic() + RUN_TIMEOUT
            while True:
                if time.monotonic() > deadline:
                    proc.kill()
                    reader.join(timeout=1)
                    while not q.empty():
                        output_parts.append(q.get_nowait())
                    return {"type": "run", "cmd": cmd, "ok": False,
                            "output": "".join(output_parts) + f"\nCommand timed out after {RUN_TIMEOUT}s",
                            "returncode": -1}
                try:
                    chunk = q.get(timeout=0.05)
                    output_parts.append(chunk)
                    sys.stdout.write(chunk)
                    sys.stdout.flush()
                except queue.Empty:
                    if proc.poll() is not None:
                        break
            reader.join(timeout=1)
            while not q.empty():
                chunk = q.get_nowait()
                output_parts.append(chunk)
                sys.stdout.write(chunk)
            sys.stdout.flush()
            output = "".join(output_parts)
            ok = proc.returncode == 0
            return {"type": "run", "cmd": cmd, "ok": ok,
                    "output": output, "returncode": proc.returncode}
        except subprocess.TimeoutExpired:
            return {"type": "run", "cmd": cmd, "ok": False,
                    "output": f"Command timed out after {RUN_TIMEOUT}s", "returncode": -1}
        except Exception as e:
            return {"type": "run", "cmd": cmd, "ok": False, "output": str(e), "returncode": -1}

def print_action_results(results: List[Dict[str, Any]]):
    """Pretty-print the results of filesystem actions."""
    if not results:
        return
    if _clean_mode():
        return
    if _plain_terminal():
        print("\n[ACTIONS]")
    else:
        console.print()
        console.print(Rule("[dim]  Actions Executed  [/dim]", style="dim yellow", align="left"))
    for r in results:
        t = r["type"]
        ok = r["ok"]
        icon = "OK" if ok else "ERR"

        if t in ("create", "replace", "folder", "edit", "invalid"):
            if _plain_terminal():
                print(f"  {icon} {r['msg']}")
            else:
                sym = get_symbol("OK", "[OK]") if ok else get_symbol("ERROR", "[ERROR]")
                color = "green" if ok else "red"
                console.print(f"  [{color}]{sym}[/{color}] {r['msg']}")

        elif t == "run":
            status = f"exit {r['returncode']}"
            if _plain_terminal():
                print(f"  {icon} Command finished {status}")
            else:
                rich_status = "[green]exit 0[/green]" if ok else f"[red]exit {r['returncode']}[/red]"
                sym = get_symbol("OK", "[OK]") if ok else get_symbol("ERROR", "[ERROR]")
                color = "green" if ok else "red"
                console.print(f"  [{color}]{sym}[/{color}] Command finished  {rich_status}")
            output = r.get("output","").strip()
            if output:
                if len(output) > 2000:
                    output = output[:2000] + "\n...[truncated]"
                if _plain_terminal():
                    print(output)
                else:
                    console.print(Panel(
                        output,
                        title="[dim]Output[/dim]",
                        border_style="green" if ok else "red",
                        padding=(0, 1)
                    ))
    if _plain_terminal():
        print()
    else:
        console.print()
