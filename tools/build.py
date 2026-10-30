#!/usr/bin/env python3
"""Rebuild plugins/ + marketplace.json + README catalog from a local skills folder.

Usage: python3 tools/build.py [SKILLS_DIR]   (default ~/.claude/skills)
Re-run after editing CATEGORIES / EXCLUDE below. Output is deterministic.
"""
import json, os, re, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = Path(sys.argv[1] if len(sys.argv) > 1 else "~/.claude/skills").expanduser()
OWNER = {"name": "SDL"}

CATEGORIES = {
    "marketing": ("Marketing & Growth", """ab-testing ad-creative ads ai-seo analytics analytics-dashboard aso churn-prevention
        co-marketing community-marketing competitor-profiling competitors content-matrix content-strategy cro
        customer-research directory-submissions free-tools launch lead-magnets marketing-ideas marketing-plan
        marketing-psychology niche-research onboarding paywalls popups pricing product-marketing programmatic-seo
        schema seo-audit signup site-architecture"""),
    "sales": ("Sales & Outreach", """cold-email emails lead-signals prospecting recruit referrals revops sales-enablement sms"""),
    "content": ("Writing & Content", """copy-editing copywriting humanizer stop-slop newsletter-voice voice-builder social
        post-formatter post-scorer post-writer quote-post profile-optimizer reels-scripting writing-beats
        writing-fragments writing-shape youtube-thumbnail gemini-carousel gemini-infographic"""),
    "design": ("Design & Creative", """brandkit brutalist-skill design-motion-principles graphic-designer gpt-tasteskill image
        image-to-code-skill imagegen-frontend-mobile imagegen-frontend-web minimalist-skill output-skill
        redesign-skill soft-skill stitch-skill taste-skill taste-skill-v1 ui-ux-pro-max impeccable bklit-ui
        scroll-cinematic scroll-world make-ugc video"""),
    "research": ("Research & Productivity", """research defuddle web-access treg paper2code system-design-101 grilling grill-me
        grill-with-docs brainstorming wait-what wizard to-questionnaire teach ask-matt find-skills handoff
        agent-browser"""),
    "engineering": ("Engineering", """code-review codebase-design diagnosing-bugs domain-modeling dispatching-parallel-agents
        executing-plans finishing-a-development-branch git-guardrails-claude-code hook-generator implement
        implement-spec improve-codebase-architecture migrate-to-shoehorn pr prototype receiving-code-review
        requesting-code-review reverse-engineer-anything scaffold-exercises setup-matt-pocock-skills
        setup-pre-commit setup-ts-deep-modules subagent-driven-development systematic-debugging tdd
        test-driven-development to-spec to-tickets triage using-git-worktrees using-superpowers wayfinder
        writing-plans writing-skills writing-for-agents skill-creator retro verification-before-completion"""),
}
CATEGORIES = {k: (t, v.split()) for k, (t, v) in CATEGORIES.items()}

# Not shipped. Reason shown in EXCLUDED.md.
EXCLUDE = {n: "personal / not for SDL staff" for n in """chief-of-staff council-execution deep-execution provider-integration
    loop-me claude-handoff hrm pinned-comment omnivoice obsidian-bases obsidian-cli obsidian-markdown json-canvas
    anatomy playwright-skill graphify""".split()}
EXCLUDE["synced"] = "no SKILL.md (sync data)"
EXCLUDE["gstack"] = "tool repo (1.2 GB), not a skill"

SKIP_DIRS = {"node_modules", ".git", "__pycache__", ".venv"}
SKIP_FILES = {".DS_Store"}
WIN_BAD = re.compile(r'[<>:"|?*]')
WIN_RESERVED = {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)), *(f"lpt{i}" for i in range(1, 10))}


def frontmatter(path):
    text = path.read_text(encoding="utf-8", errors="replace")
    m = re.match(r"---\n(.*?)\n---", text, re.S)
    if not m:
        return {}
    out, key = {}, None
    for line in m.group(1).split("\n"):
        k = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if k and not line.startswith(" "):
            key, v = k.group(1), k.group(2).strip()
            out[key] = "" if v in (">", "|", ">-", "|-") else v.strip("\"'")
        elif key and line.startswith(" ") and key in ("description", "name"):
            out[key] = (out[key] + " " + line.strip()).strip()
    return out


def gstack_dependent(skill_dir):
    t = (skill_dir / "SKILL.md").read_text(encoding="utf-8", errors="replace")
    return t.lower().count("gstack") >= 3 or re.search(r"^preamble-tier:", t, re.M) is not None


def copy_skill(src, dst):
    for dp, dn, fn in os.walk(src, followlinks=True):
        dn[:] = [d for d in dn if d not in SKIP_DIRS]
        rel = Path(dp).relative_to(src)
        (dst / rel).mkdir(parents=True, exist_ok=True)
        for f in fn:
            if f not in SKIP_FILES:
                shutil.copy2(Path(dp) / f, dst / rel / f)  # copy2 follows symlinks


def windows_problems(plugin_dir):
    bad, seen = [], {}
    for p in plugin_dir.rglob("*"):
        rel = p.relative_to(plugin_dir)
        s = str(rel)
        if WIN_BAD.search(s):
            bad.append(f"{s}: illegal char")
        if any(part.split(".")[0].lower() in WIN_RESERVED for part in rel.parts):
            bad.append(f"{s}: reserved name")
        if len(s) > 150:
            bad.append(f"{s}: path too long ({len(s)})")
        if s.lower() in seen and seen[s.lower()] != s:
            bad.append(f"{s}: case collision")
        seen[s.lower()] = s
    return bad


def main():
    assert SRC.is_dir(), SRC
    shutil.rmtree(ROOT / "plugins", ignore_errors=True)
    avail = {d.name: d for d in SRC.iterdir() if d.is_dir() or d.is_symlink()}
    assigned = {n: c for c, (_, ns) in CATEGORIES.items() for n in ns}
    dup = [n for n in assigned if list(assigned).count(n) > 1]
    assert not dup, f"in two categories: {dup}"

    excluded = {n: r for n, r in EXCLUDE.items() if n in avail}
    for n, d in sorted(avail.items()):
        if n in assigned or n in excluded:
            continue
        if not (d / "SKILL.md").exists():
            excluded[n] = "no SKILL.md"
        elif gstack_dependent(d):
            excluded[n] = "needs gstack runtime (macOS/bash/bun); port before shipping"
        else:
            sys.exit(f"UNCATEGORISED skill: {n} -> add to CATEGORIES or EXCLUDE")
    missing = [n for n in assigned if n not in avail]
    assert not missing, f"listed but not found locally: {missing}"
    both = [n for n in assigned if n in excluded]
    assert not both, f"both categorised and excluded: {both}"

    market, catalog, problems = [], {}, []
    for cat, (title, names) in CATEGORIES.items():
        pdir = ROOT / "plugins" / f"sdl-{cat}"
        (pdir / ".claude-plugin").mkdir(parents=True)
        rows = []
        for n in sorted(names):
            if gstack_dependent(avail[n]):
                sys.exit(f"{n} is gstack-dependent but categorised; move to EXCLUDE")
            copy_skill(avail[n].resolve(), pdir / "skills" / n)
            fm = frontmatter(pdir / "skills" / n / "SKILL.md")
            has_scripts = any(pdir.joinpath("skills", n).rglob("*.py")) or any(pdir.joinpath("skills", n).rglob("*.sh")) or any(pdir.joinpath("skills", n).rglob("*.js")) or any(pdir.joinpath("skills", n).rglob("*.mjs"))
            rows.append((n, fm.get("description", ""), has_scripts))
        (pdir / ".claude-plugin" / "plugin.json").write_text(json.dumps({
            "name": f"sdl-{cat}", "description": f"SDL {title} skills ({len(rows)})",
            "version": "1.0.0", "author": OWNER}, indent=2) + "\n")
        market.append({"name": f"sdl-{cat}", "source": f"./plugins/sdl-{cat}",
                       "description": f"{title}: " + ", ".join(r[0] for r in rows[:6]) + (", ..." if len(rows) > 6 else ""),
                       "category": cat})
        catalog[cat] = (title, rows)
        problems += [f"sdl-{cat}/{p}" for p in windows_problems(pdir)]

    (ROOT / ".claude-plugin").mkdir(exist_ok=True)
    (ROOT / ".claude-plugin" / "marketplace.json").write_text(json.dumps({
        "$schema": "https://anthropic.com/claude-code/marketplace.schema.json",
        "name": "sdl-claude-kit", "description": "SDL shared Claude Code skills, grouped by task",
        "owner": OWNER, "plugins": market}, indent=2) + "\n")

    # catalog README
    L = ["# SDL Claude Kit", "", "Shared Claude Code skills for SDL, grouped by kind of work. Install only the groups you need.", "",
         "## Install (Windows or Mac)", "",
         "1. Install Claude Code and log in with your SDL account.",
         "2. In Claude Code run:", "   ```", "   /plugin marketplace add <GITHUB_ORG>/sdl-claude-kit", "   /plugin install sdl-marketing@sdl-claude-kit", "   ```",
         "3. Restart Claude Code. Ask for the task in plain words, or call a skill as `/sdl-marketing:ads`.", "",
         "Update later: `/plugin marketplace update sdl-claude-kit`.", "",
         "## Groups", "", "| Install | Use it for | Skills |", "|---|---|---|"]
    for cat, (title, rows) in catalog.items():
        L.append(f"| `sdl-{cat}` | {title} | {len(rows)} |")
    for cat, (title, rows) in catalog.items():
        L += ["", f"### sdl-{cat} - {title}", ""]
        for n, d, sc in rows:
            d = re.sub(r"\s+", " ", d)
            d = (d[:157] + "...") if len(d) > 160 else d
            L.append(f"- **{n}**{' (runs scripts: needs Python/Node)' if sc else ''}: {d}")
    (ROOT / "README.md").write_text("\n".join(L) + "\n")

    E = ["# Not shipped", "", "Left out of the marketplace. Re-add by editing `tools/build.py`.", ""]
    for n, r in sorted(excluded.items(), key=lambda x: (x[1], x[0])):
        E.append(f"- `{n}`: {r}")
    (ROOT / "EXCLUDED.md").write_text("\n".join(E) + "\n")

    shipped = sum(len(r) for _, r in catalog.values())
    print(f"shipped {shipped} skills in {len(catalog)} plugins; excluded {len(excluded)}")
    print("windows problems:", problems or "none")


main()
