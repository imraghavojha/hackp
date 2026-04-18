GENERATE_SYSTEM_PROMPT = """
Generate one self-contained HTML tool.
It must expose `window.Tool.metadata`, `window.Tool.transform`, and `window.Tool.defaultConfig`.
The transform must be pure and reusable by both UI and future orchestration.
"""
