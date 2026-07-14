import hashlib
import time
import struct
from typing import Optional
from core.models import VisualIdentity
from core.model_router import get_router, detect_stage

LAYOUT_ARCHETYPES = [
    {
        "name": "sidebar-nav",
        "description": "Collapsible left sidebar navigation, main content area on the right. Sidebar contains nav links, project info, user menu. Main area has top toolbar and scrollable content.",
        "section_order": ["topbar", "sidebar", "main-content", "modal-overlay"],
        "components": ["sidebar", "topbar", "card-grid", "data-table", "modal"],
        "structure_hints": "header on the left as a vertical sidebar, main content panel on the right with a top action bar",
    },
    {
        "name": "top-nav",
        "description": "Horizontal top navigation bar with logo and links, below it a full-width content area. Clean, modern SaaS dashboard layout.",
        "section_order": ["navbar", "hero", "content-grid", "footer"],
        "components": ["navbar", "hero-section", "card-grid", "stats-row", "modal", "footer"],
        "structure_hints": "full-width top navigation bar, hero/header section below nav, then a multi-column content grid, and optional footer",
    },
    {
        "name": "card-dashboard",
        "description": "Card-based dashboard layout with stat cards at the top, a main content card grid below, and minimal chrome. Content-first design.",
        "section_order": ["stats-row", "card-grid", "detail-panel", "modal-overlay"],
        "components": ["stat-cards", "action-cards", "detail-drawer", "modal", "empty-state"],
        "structure_hints": "stat/metric cards in a horizontal row at top, larger content cards in a responsive grid below, detail slides open as an overlay or drawer",
    },
    {
        "name": "single-column",
        "description": "Single column centered layout with sections stacked vertically. Each section is self-contained with its own header. Minimalist, linear reading flow.",
        "section_order": ["hero", "form-section", "list-section", "footer"],
        "components": ["hero", "form-panel", "list-view", "empty-state", "inline-notification"],
        "structure_hints": "centered single column max-width container, sections stacked vertically one after another, each with a heading and content",
    },
    {
        "name": "split-panel",
        "description": "Left/right split panel layout with a resizable or fixed divider. Left panel for navigation/selection, right panel for detail/edit view.",
        "section_order": ["topbar", "split-left", "split-right", "modal-overlay"],
        "components": ["selectable-list", "detail-panel", "form-panel", "modal", "breadcrumb"],
        "structure_hints": "two-panel split layout with a vertical divider, left panel contains a list or navigation tree, right panel shows detail content or forms",
    },
    {
        "name": "tabs-interface",
        "description": "Tab-based interface where content is organized into horizontal tabs at the top. Each tab panel contains its own layout. No page scroll, tab panels scroll independently.",
        "section_order": ["tab-bar", "tab-panel-1", "tab-panel-2", "tab-panel-3"],
        "components": ["tab-bar", "tab-content", "form-panel", "data-table", "inline-chart"],
        "structure_hints": "horizontal tab bar at the top, tab content panels below that switch without page navigation, each tab has independent scrollable content",
    },
    {
        "name": "masonry-grid",
        "description": "Pinterest-style masonry grid layout with cards of varying heights. Floating action button, top search bar, infinite scroll behavior.",
        "section_order": ["topbar", "masonry-grid", "modal-overlay"],
        "components": ["search-bar", "masonry-cards", "modal", "floating-action-btn"],
        "structure_hints": "full-width top bar with search, masonry/pinterest-style card grid below with uneven card heights, FAB for quick actions",
    },
    {
        "name": "command-palette",
        "description": "Command palette-driven interface. Central modal overlay for commands, minimal persistent UI. Keyboard-first navigation, results panel below input.",
        "section_order": ["palette-overlay", "results-panel", "detail-panel"],
        "components": ["command-input", "results-list", "detail-panel", "keyboard-shortcuts"],
        "structure_hints": "CMD+K style command palette as primary interaction, dark overlay behind, results panel shows filtered options, detail panel on selection",
    },
    {
        "name": "kanban-board",
        "description": "Horizontal kanban/scrum board layout with draggable columns. Column headers with item counts, cards with avatars and labels.",
        "section_order": ["topbar", "board-columns", "card-detail-overlay"],
        "components": ["board-header", "column-list", "draggable-card", "detail-overlay", "quick-add"],
        "structure_hints": "horizontal scrolling board with fixed-width columns, each column has a header and stacked cards, drag-and-drop between columns",
    },
    {
        "name": "chat-interface",
        "description": "Messenger/chat-style layout with message list, input bar, and optional sidebar for conversations. Bubbles, typing indicators, timestamps.",
        "section_order": ["chat-sidebar", "message-area", "input-bar", "attachment-preview"],
        "components": ["conversation-list", "message-bubbles", "typing-indicator", "input-bar", "attachment-picker"],
        "structure_hints": "sidebar with conversation threads, main area shows message history with bubbles, bottom input bar with send and attachment buttons",
    },
]

COMPONENT_POOLS = {
    "standard": ["modal", "form", "list-view", "search-bar", "empty-state"],
    "rich": ["modal", "drawer", "tooltip", "dropdown", "form", "list-view", "search-bar", "pagination", "empty-state", "notification"],
    "premium": ["modal", "drawer", "tooltip", "dropdown", "form", "list-view", "search-bar", "pagination", "empty-state", "notification", "breadcrumb", "stats-cards", "tabs", "accordion"],
}

ANIMATION_SYSTEMS = ["fade", "slide-up", "slide-left", "scale-in", "stagger-fade", "spring-slide", "glow-pulse", "parallax-scroll", "flip-card", "morph-transition", "ripple-click", "typewriter"]

DEEP_LAYOUT_ARCHETYPES = LAYOUT_ARCHETYPES + [
    {
        "name": "terminal-dashboard",
        "description": "Terminal-inspired dashboard with monospace font, ASCII borders, blinking cursors, and retro color schemes. Data displayed as live-updating tables and sparklines.",
        "section_order": ["status-bar", "terminal-output", "command-input"],
        "components": ["status-line", "data-table", "sparkline", "command-input", "notification-bar"],
        "structure_hints": "full-height terminal feel, status bar at top showing system info, main area scrolls log/data output, bottom command input with prompt",
    },
    {
        "name": "magazine-layout",
        "description": "Editorial/magazine layout with large hero imagery, pull quotes, multi-column text, and staggered article cards. Typography-first design.",
        "section_order": ["hero-image", "feature-grid", "article-feed", "footer"],
        "components": ["hero-image", "pull-quote", "article-card", "category-tag", "newsletter-signup"],
        "structure_hints": "full-width hero image with overlaid headline, 2-3 column feature card grid below, then a continuous article feed with alternating layouts",
    },
    {
        "name": "audio-visualizer",
        "description": "Immersive audio visualization interface with waveform display, frequency bars, circular visualizers, and reactive color changes tied to audio input.",
        "section_order": ["visualizer-main", "controls-bar", "playlist-panel"],
        "components": ["waveform", "frequency-bars", "circular-vis", "transport-controls", "playlist", "volume-slider"],
        "structure_hints": "central visualization area (waveform or circular), bottom controls bar with transport and volume, right side playlist panel",
    },
]


def _pick(pool: list, seed: int, count: int) -> list:
    result = []
    used = set()
    for i in range(count):
        idx = ((seed >> (i * 3 % 24)) ^ (seed * (i + 1) * 7) ^ (i * 53)) % len(pool)
        if idx in used and len(used) < len(pool):
            idx = (idx + 1) % len(pool)
        used.add(idx)
        result.append(pool[idx])
    return result


def _generate_visual_identity(request: str, mode: str = "balanced") -> VisualIdentity:
    h = hashlib.md5(request.encode()).hexdigest()
    base_seed = int(h[:8], 16)

    time_ns = int(time.time() * 1_000_000)
    jitter = (time_ns & 0xFFFFFF) ^ (time_ns >> 12 & 0xFFFFFF)
    seed = base_seed ^ jitter

    profiles = [
        {"ui_style": "minimal", "typography": "'Inter', system-ui, sans-serif", "border_radius": "2px", "shadows": "none", "animation": "none"},
        {"ui_style": "futuristic", "typography": "'Space Grotesk', sans-serif", "border_radius": "0px", "shadows": "0 0 20px rgba(0, 212, 255, 0.2)", "animation": "glow"},
        {"ui_style": "enterprise", "typography": "'Inter', system-ui, sans-serif", "border_radius": "8px", "shadows": "0 1px 3px rgba(0,0,0,0.1)", "animation": "subtle"},
        {"ui_style": "glassmorphism", "typography": "'Outfit', sans-serif", "border_radius": "24px", "shadows": "0 8px 32px 0 rgba(31, 38, 135, 0.3)", "animation": "float", "glass": True},
        {"ui_style": "brutalist", "typography": "'Archivo Black', sans-serif", "border_radius": "0px", "shadows": "8px 8px 0px #000000", "animation": "none"},
        {"ui_style": "soft", "typography": "'Outfit', sans-serif", "border_radius": "16px", "shadows": "0 10px 15px -3px rgba(0, 0, 0, 0.05)", "animation": "fade"},
        {"ui_style": "retro-wave", "typography": "'Prompt', system-ui, sans-serif", "border_radius": "4px", "shadows": "4px 4px 0px rgba(0,0,0,0.2)", "animation": "glitch"},
        {"ui_style": "neumorphic", "typography": "'Nunito', sans-serif", "border_radius": "16px", "shadows": "8px 8px 16px #d1d1d1, -8px -8px 16px #ffffff", "animation": "subtle"},
        {"ui_style": "cyberpunk", "typography": "'Rajdhani', sans-serif", "border_radius": "0px", "shadows": "3px 3px 0px #00ff41, -3px -3px 0px #ff00ff", "animation": "glitch-scan"},
        {"ui_style": "nature-inspired", "typography": "'DM Serif Display', serif", "border_radius": "8px", "shadows": "0 4px 20px rgba(34, 139, 34, 0.15)", "animation": "organic"},
        {"ui_style": "dark-corporate", "typography": "'IBM Plex Sans', sans-serif", "border_radius": "4px", "shadows": "0 2px 8px rgba(0,0,0,0.3)", "animation": "none"},
    ]

    profile = profiles[seed % len(profiles)].copy()

    def _h(s, offset=0):
        return (base_seed + offset) % 360

    hue = _h(request)
    if profile["ui_style"] == "minimal":
        palette = {"bg": "#ffffff", "surface": "#fafafa", "surface_strong": "#f0f0f0", "text": "#1a1a1a", "muted": "#737373", "accent": f"hsl({hue}, 10%, 10%)", "accent_dark": "#000000", "line": "#e5e5e5"}
    elif profile["ui_style"] == "futuristic":
        palette = {"bg": "#050505", "surface": "#0f0f0f", "surface_strong": "#1a1a1a", "text": "#ffffff", "muted": "#a1a1aa", "accent": f"hsl({hue}, 100%, 50%)", "accent_dark": f"hsl({hue}, 100%, 40%)", "line": "#27272a"}
    elif profile["ui_style"] == "brutalist":
        accents = ["#ffde00", "#ff0055", "#00ff66", "#0066ff"]
        palette = {"bg": "#ffffff", "surface": "#ffffff", "surface_strong": "#f0f0f0", "text": "#000000", "muted": "#000000", "accent": accents[seed % len(accents)], "accent_dark": "#000000", "line": "#000000"}
    elif profile["ui_style"] == "retro-wave":
        palette = {"bg": "#0d0221", "surface": "#1a0a3e", "surface_strong": "#2d1b69", "text": "#e0e0ff", "muted": "#8888aa", "accent": f"hsl({hue}, 90%, 55%)", "accent_dark": f"hsl({hue}, 90%, 40%)", "line": "#3a2a6a"}
    elif profile["ui_style"] == "neumorphic":
        base = max(40, (hue * 7) % 60 + 80)
        bg = f"hsl({hue}, 5%, {base}%)"
        palette = {"bg": bg, "surface": bg, "surface_strong": f"hsl({hue}, 5%, {max(base - 5, 50)}%)", "text": f"hsl({hue}, 15%, {max(base - 50, 10)}%)", "muted": f"hsl({hue}, 5%, {max(base - 25, 30)}%)", "accent": f"hsl({hue}, 70%, 45%)", "accent_dark": f"hsl({hue}, 75%, 35%)", "line": "transparent"}
    elif profile["ui_style"] == "cyberpunk":
        palette = {"bg": "#0a0a0f", "surface": "#12121a", "surface_strong": "#1a1a2e", "text": "#00ff41", "muted": "#6b6b8d", "accent": "#ff00ff", "accent_dark": "#cc00cc", "line": "#00ff41"}
    elif profile["ui_style"] == "nature-inspired":
        palette = {"bg": f"hsl({hue + 120}, 20%, 95%)", "surface": "#ffffff", "surface_strong": f"hsl({hue + 120}, 15%, 90%)", "text": f"hsl({hue + 120}, 40%, 15%)", "muted": f"hsl({hue + 120}, 10%, 40%)", "accent": f"hsl({hue + 120}, 60%, 40%)", "accent_dark": f"hsl({hue + 120}, 70%, 25%)", "line": f"hsl({hue + 120}, 15%, 85%)"}
    elif profile["ui_style"] == "dark-corporate":
        palette = {"bg": "#111118", "surface": "#1a1a24", "surface_strong": "#242436", "text": "#e8e8f0", "muted": "#8a8a9e", "accent": f"hsl({hue}, 60%, 55%)", "accent_dark": f"hsl({hue}, 60%, 40%)", "line": "#2a2a3a"}
    else:
        palette = {"bg": f"hsl({hue}, 20%, 98%)", "surface": "#ffffff", "surface_strong": f"hsl({hue}, 15%, 95%)", "text": f"hsl({hue}, 30%, 10%)", "muted": f"hsl({hue}, 10%, 45%)", "accent": f"hsl({hue}, 70%, 50%)", "accent_dark": f"hsl({hue}, 75%, 40%)", "line": f"hsl({hue}, 15%, 90%)"}

    layout_pool = DEEP_LAYOUT_ARCHETYPES if mode == "creative" else LAYOUT_ARCHETYPES
    arch_idx = ((seed >> 4) ^ (seed & 0xFFF) * 3) % len(layout_pool)
    archetype = layout_pool[arch_idx]

    if mode == "creative":
        pool = COMPONENT_POOLS["premium"]
    elif mode == "stable":
        pool = COMPONENT_POOLS["standard"]
    else:
        pool = COMPONENT_POOLS["rich"]
    components = _pick(pool, seed, 5)

    anim_idx = (seed + 17) % len(ANIMATION_SYSTEMS)
    animation_system = ANIMATION_SYSTEMS[anim_idx]

    return VisualIdentity(
        palette=palette,
        typography=profile["typography"],
        ui_style=profile["ui_style"],
        border_radius=profile["border_radius"],
        shadows=profile["shadows"],
        animation_style=profile["animation"],
        mode=mode,
        glass=profile.get("glass", False),
        layout_archetype=archetype["name"],
        section_order=archetype["section_order"],
        component_variety=components,
        animation_system=animation_system,
    )
