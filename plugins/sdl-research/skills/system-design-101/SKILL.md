---
name: system-design-101
description: >
  ByteByteGo's system design reference — 400 guides on architecture, databases,
  caching, load balancing, microservices, API design, payments, security, DevOps,
  and real-world case studies (Netflix, Discord, Uber, Stripe). Use when explaining
  or deciding a system-design question: scaling, storage choice, caching strategy,
  message queues, consistency, auth flows, CI/CD, or interview prep.
license: MIT (ByteByteGoHq/system-design-101)
---

# System Design 101

400 guides live in `guides/`. Filenames are the topic slug, so `ls` is the index:

```bash
ls ~/.claude/skills/system-design-101/guides/ | grep -i cache
grep -ril "consistent hashing" ~/.claude/skills/system-design-101/guides/
```

Then `cat` the one or two that match. Each guide has YAML frontmatter
(`title`, `categories`, `tags`) and is a few hundred words.

`categories/` has 15 curated topic lists (e.g. `database-and-storage.md`,
`real-world-case-studies.md`) — start there when the question is broad rather
than a specific term.

`OVERVIEW.md` is the upstream README: the full visual table of contents.

Diagram images are remote URLs (`assets.bytebytego.com`), not local files.
Cite the guide's text; link the image URL rather than trying to read it.
