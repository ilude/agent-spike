# Lessons Learned

---

## Mentat Web UI (Iteration 1)

### Pattern: Spike with simplified architecture
- Context: Building chat UI inspired by PewDiePie's Odysseus and TAC Lesson 6
- Solution: Adversarial review cut 28 files → 11 files MVP. Skip TDD-first, use WebSockets from start
- Gotcha: Over-engineering is easy when inspired by polished demos
- Use when: Building new features - start minimal, iterate based on real needs

### Pattern: Windows Makefile with PowerShell
- Context: Needed Docker-like commands but Git Bash + PowerShell compatibility
- Solution: Use PowerShell for ALL commands, escape vars with `\$$var`, quote all strings → Makefile
- Gotcha: Git Bash expands `$$var` before Make/PowerShell see it. Need `\$$` double-escape
- Use when: Creating Makefiles that work across Windows shells

### Pattern: Ghost TCP connections on Windows
- Context: Port 8000 stuck with connections to dead PIDs
- Solution: Change ports temporarily, or wait 2-4 min for TCP timeout
- Gotcha: `Stop-Process` doesn't release TCP connections immediately. `Remove-NetTCPConnection` not available on all Windows versions
- Use when: Rapid dev/test cycles creating stale connections

### Pattern: OpenRouter for prototyping
- Context: Wanted to test LLM chat without managing multiple API keys
- Solution: OpenRouter proxy with AsyncOpenAI + base_url override → api/main.py:31-34
- Gotcha: Need to use tools/env_loader.py for root .env instead of python-dotenv directly
- Use when: Prototyping with free/cheap models before committing to provider

---
