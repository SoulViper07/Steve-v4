import os
import re
import time
import json
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Callable

from config.model_config import model_for_stage, options_for_stage
from providers.ollama import fetch_response_stream
from core.models import RequestRoute
from core.project_memory import ProjectMemory
from ui.terminal_renderer import get_pipeline, console


IDLE_TIMEOUT = 30.0  # seconds without tokens before abort


SECTION_PROMPTS = {
    "index.html": {
        "head": """Generate ONLY the <head> section of index.html for a project with this spec:

{spec}

Include:
- DOCTYPE and html tag with lang attribute
- Meta charset, viewport, description
- Title matching the project
- Link to styles.css
- Any preconnect/preload for performance
- Open Graph meta tags for social sharing

Output ONLY the complete <head> content. Start with <!DOCTYPE html>.""",

        "navbar": """Generate the <nav>/<header> section for the project.

Project: {project_name}
Design: {design}

Include:
- Logo/brand name
- Navigation links
- Mobile hamburger menu button
- Glassmorphism or solid background
- Sticky positioning classes

Output ONLY the nav/header HTML content.""",

        "hero": """Generate the hero/landing section for the project.

Project: {project_name}
Design: {design}

Include:
- Main heading (h1) with project name
- Subheading/tagline
- Call-to-action buttons
- Background decoration or image placeholder

Output ONLY the hero section HTML.""",

        "features": """Generate the features section for the project.

Project: {project_name}

Include:
- Section heading
- 3-6 feature cards with icons (use HTML entities or emoji)
- Each card has title, description
- Grid or flex layout classes

Output ONLY the features section HTML.""",

        "footer": """Generate the footer section for the project.

Project: {project_name}

Include:
- Copyright notice
- Social media links (placeholder)
- Back-to-top button
- Contact information

Output ONLY the footer HTML.""",
    },

    "styles.css": {
        "variables": """Generate CSS custom properties and reset for the project.

Design spec:
{spec}

Include:
- :root with design tokens (colors, fonts, spacing, shadows, border-radius)
- CSS reset / normalize
- Box-sizing border-box
- Smooth scrolling

Output ONLY the CSS variables and reset section.""",

        "layout": """Generate base layout CSS for the project.

Design: {design}

Include:
- Body font, background, color
- Container class with max-width and centered
- Grid system or flex utilities
- Section spacing (padding/margin)

Output ONLY the layout CSS.""",

        "navbar": """Generate navbar CSS for the project.

Design: {design}

Include:
- Fixed/sticky positioning
- Background with blur/glass effect
- Logo styling
- Nav links with hover effects
- Mobile hamburger menu
- Responsive breakpoint

Output ONLY the navbar CSS.""",

        "hero": """Generate hero section CSS for the project.

Design: {design}

Include:
- Full viewport height or large padding
- Background gradient or image overlay
- Heading typography (large, bold)
- CTA button styling with hover
- Responsive text sizing

Output ONLY the hero CSS.""",

        "cards": """Generate card/features section CSS for the project.

Design: {design}

Include:
- Grid layout (auto-fit, minmax)
- Card styling with shadow, border-radius
- Card hover effects (lift, shadow change)
- Icon styling
- Responsive adjustments

Output ONLY the cards CSS.""",

        "responsive": """Generate responsive media queries for the project.

Project: {project_name}

Include:
- Tablet breakpoints (768px)
- Mobile breakpoints (480px)
- Navbar collapse
- Grid adjustments
- Font size reductions
- Touch-friendly target sizes

Output ONLY the responsive CSS.""",

        "animations": """Generate CSS animations and transitions.

Design: {design}

Include:
- Keyframe animations (fadeIn, slideUp, scaleIn)
- Scroll-triggered animation classes
- Hover transitions
- Loading animations
- Smooth page transitions

Output ONLY the animations CSS.""",
    },

    "script.js": {
        "navigation": """Generate navigation JavaScript for the project.

Include:
- Mobile menu toggle (hamburger)
- Active link highlighting based on scroll position
- Smooth scroll for anchor links
- Sticky navbar on scroll

Output ONLY the navigation JS code.""",

        "theme": """Generate theme/dark mode JavaScript.

Include:
- Theme toggle button handler
- localStorage persistence for theme preference
- CSS class toggling on body/html
- System preference detection (prefers-color-scheme)

Output ONLY the theme JS code.""",

        "storage": """Generate localStorage utility functions.

Include:
- Save/load/delete helpers
- JSON serialization wrapper
- Default values support
- Change listeners/callbacks

Output ONLY the storage utility JS.""",

        "animations": """Generate scroll-triggered animations JavaScript.

Include:
- IntersectionObserver setup
- Animate elements on viewport entry
- Stagger animation delays
- Parallax scroll effect
- Performance optimizations (throttling)

Output ONLY the animations JS.""",

        "utilities": """Generate utility JavaScript functions.

Include:
- Debounce/throttle helpers
- DOM query shortcuts
- Form validation helpers
- Date formatting
- Error handling wrapper

Output ONLY the utility JS.""",
    },
}


class SectionGenerator:
    def __init__(self, memory: Optional[ProjectMemory] = None):
        self.memory = memory
        self._abort = threading.Event()

    def abort(self):
        self._abort.set()

    def generate_section(
        self,
        file_path: str,
        section: str,
        context: Dict,
        callback: Optional[Callable[[str], None]] = None,
    ) -> Optional[str]:
        file_prompts = SECTION_PROMPTS.get(file_path)
        if not file_prompts:
            return None

        prompt_template = file_prompts.get(section)
        if not prompt_template:
            return None

        prompt = prompt_template.format(**context)

        coding_model = model_for_stage("implement")
        opts = options_for_stage("implement")

        messages = [{"role": "user", "content": prompt}]

        route = RequestRoute(
            intent="action_simple",
            actionable=True,
            requires_inspection=False,
            requires_plan=False,
            requires_verification=False,
            short_path=True,
            reason="section_generation",
        )

        result = []
        last_token_time = time.monotonic()

        try:
            for token in fetch_response_stream(coding_model, messages, route):
                if self._abort.is_set():
                    return None
                result.append(token)
                last_token_time = time.monotonic()
                if callback:
                    callback(token)

            content = "".join(result).strip()
            content = self._clean_section(content)

            if self.memory:
                self.memory.set_section_state(file_path, section, "done" if content else "failed")
                self.memory.mark_component_done(f"{file_path}>{section}")
                self.memory.save_all()

            return content

        except Exception as e:
            if self.memory:
                self.memory.set_section_state(file_path, section, "failed")
                self.memory.add_repair({
                    "file": file_path,
                    "section": section,
                    "error": str(e),
                    "timestamp": time.time(),
                })
                self.memory.save_all()
            return None

    def _clean_section(self, content: str) -> str:
        content = re.sub(r"^```[\w]*\n", "", content)
        content = re.sub(r"\n```$", "", content)
        content = re.sub(r"^```[\w]*\n([\s\S]*?)```$", r"\1", content)
        return content.strip()


class IncrementalFileBuilder:
    def __init__(self, workdir: Path, memory: Optional[ProjectMemory] = None):
        self.workdir = workdir
        self.memory = memory
        self.generator = SectionGenerator(memory)
        self.buffers: Dict[str, str] = {}
        self.section_order = {
            "index.html": ["head", "navbar", "hero", "features", "footer"],
            "styles.css": ["variables", "layout", "navbar", "hero", "cards", "animations", "responsive"],
            "script.js": ["navigation", "theme", "storage", "animations", "utilities"],
        }

    def build_file(
        self,
        file_path: str,
        sections: List[str],
        context: Dict,
        pipeline=None,
    ) -> bool:
        full_path = self.workdir / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        file_buffer = []
        all_ok = True
        retry_count = 0
        max_retries = 2

        for section in sections:
            content = None
            for attempt in range(max_retries + 1):
                if self.memory:
                    prior_status = self.memory.section_state(file_path, section)
                    if prior_status == "done":
                        continue

                if pipeline:
                    pipeline.add("  ➻", f"Generating [{file_path}] section: {section}", "step")

                content = self.generator.generate_section(
                    file_path, section, context,
                    callback=lambda t: None,
                )

                if content:
                    break
                else:
                    retry_count += 1
                    if pipeline:
                        pipeline.repair(f"Retrying [{file_path}] section: {section} (attempt {attempt + 1})")

            if content:
                file_buffer.append(content)
                if pipeline:
                    pipeline.add("  ✓", f"[{file_path}] {section} generated ({len(content)} chars)", "ok")
                if self.memory:
                    self.memory.set_section_state(file_path, section, "done")
            else:
                all_ok = False
                if pipeline:
                    pipeline.add("  ✗", f"[{file_path}] {section} failed after {max_retries + 1} attempts", "err")

        if file_buffer:
            combined = "\n\n".join(file_buffer)
            full_path.write_text(combined, encoding="utf-8")
            if pipeline:
                pipeline.file_created(f"{file_path} ({len(combined)} chars, {len(file_buffer)} sections)")
            if self.memory:
                self.memory.set_generation_state({f"files.{file_path}": "done"})
                self.memory.save_all()
            return True

        return False

    def build_project(
        self,
        files: Dict[str, List[str]],
        context: Dict,
        pipeline=None,
    ) -> bool:
        overall_ok = True
        if pipeline:
            pipeline.add("  📁", f"Creating {len(files)} files with sections...", "step")

        for file_path, sections in files.items():
            if pipeline:
                pipeline.add("📄", f"Building {file_path} ({len(sections)} sections)", "step")

            ok = self.build_file(file_path, sections, context, pipeline)
            if not ok:
                overall_ok = False
                if pipeline:
                    pipeline.add("  ⚠", f"{file_path} partial failure - sections may be missing", "warn")

        return overall_ok
