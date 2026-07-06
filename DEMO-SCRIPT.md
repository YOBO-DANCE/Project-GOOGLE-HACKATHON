# 🏆 Sports Concierge Agent — Hackathon Demo Script (3 Minutes)

> **Google + Kaggle Agentic AI Hackathon**
> Built with Google ADK · Gemini · FastMCP · Human-in-the-Loop · A2A Protocol

---

## 🎬 Setup (30 seconds before judging)

```bash
# Start the demo (one command)
docker compose up
# OR if judges prefer no containers:
# streamlit run app.py
```

Open **http://localhost:8501** in the browser. The app loads immediately — no login needed.

---

## ⏱️ The Script

### 0:00 → 0:30 — "What is this?" (Elevator Pitch)

> *"This is the **Sports Concierge Agent** — a multi-agent AI system that generates hyper-personalised athletic training plans. It uses **Google ADK** for agent orchestration, **Gemini** for LLM inference, and has a **Human-in-the-Loop security gate** baked directly into the agent pipeline."*

**Click for the judges:** Point at the workflow sidebar showing the 5 steps (Input → Security → HITL → Generation → Result).

---

### 0:30 → 1:15 — Step 1 & 2: Input + Security Check

**Type into the form:**
- Sport: `basketball`
- Level: `Intermediate`
- Injury history: `Achilles tendinopathy (right), recovered hamstring strain (2025)`

**Check the boxes:** ✅ Email context ✅ Drive search ✅ Security scan

**Click:** 🚀 **Start Analysis**

> *"The **Guard Agent** immediately gathers context from MCP tools — emails from the coach and physio, training documents from the drive. Then it scans everything for security threats using **YARA rules and MIME heuristics**."*

**Show the results:**
- The emails appear: coach, nutritionist, physio
- The drive files appear: training plan, drills, performance data
- **Guard decision**: "File is SAFE" ✅

---

### 1:15 → 1:45 — The HITL Gate (Key Moment)

> *"Here's the critical part — **Responsible AI in action**. If the Guard Agent detects anything suspicious, the workflow **pauses** and requires **human approval** before proceeding. This is a real Human-in-the-Loop gate, not a simulated one."*

**Pro tip:** If you want to trigger the HITL gate, tell the judges:

> "If I type something like `rm -rf /` or `<script>alert(1)</script>` into the sport field, the Guard Agent catches it, redacts it, and demands approval before generation."

**To demo this quickly:** Restart, enter sport as `netball; DROP TABLE users; --` and watch the security gate fire.

---

### 1:45 → 2:30 — Step 4: Plan Generation (Gemini)

The Coach Agent kicks in. It builds a **structured JSON payload** with:

```
{
  "user_goals": "Train in basketball at Intermediate level",
  "training_level": "Intermediate",
  "injury_history": "Achilles tendinopathy (right) | ... | Physio: eccentric heel-drop exercises...",
  "calendar_constraints": "Team practice Saturday 6 AM...",
  "email_context": "From: coach@example.com — Updated Marathon Training Schedule...",
  "drive_files": ["Marathon_Plan.pdf", "Drills.docx", "Performance_Metrics_Q3.csv"]
}
```

> *"Notice how the **physio email is automatically parsed** — the 'Achilles' keyword triggers the Coach Agent to include **eccentric heel-drop exercises** in the plan. This isn't a generic template. Every plan is context-aware."*

**Show the result:**
- ✅ Markdown table with Day | Workout | Intensity | Notes
- ✅ Recovery phases every 3rd day
- ✅ Achilles-specific exercises
- ✅ Progressive overload across weeks

---

### 2:30 → 2:45 — Step 5: Results + Audit Trail

**Click:** 📥 **Download Plan**

> *"The plan downloads as Markdown. And here's what judges **really** love..."*

**Switch to the 🔐 Security History tab in the sidebar.**

> *"Every security decision — every file scan the Guard Agent ever made — is logged in a **durable audit trail** via Supabase. This proves compliance with SOC 2 and ISO 27001 principles. The logs are **immutable**, **timestamped**, and **fully transparent**."*

---

### 2:45 → 3:00 — Q&A Hooks (Close Strong)

| What judges might ask | Your answer |
|-----------------------|-------------|
| "How does this use Google technology?" | "**Google ADK** for the multi-agent topology, **Gemini** for plan generation (with Ollama fallback), **A2A protocol** for agent-to-agent communication, and deployable to **Vertex AI Agent Engine** via the included Terraform configs." |
| "What's the most technically impressive part?" | "The **dual-agent architecture with HITL** — the Guard Agent runs independent security checks using YARA + MIME + keyword scoring, and if it flags a risk, the Human-in-the-Loop gate prevents the Coach Agent from generating until a human approves. Two AI agents, one security guardrail." |
| "Is this just a wrapper around an LLM prompt?" | "No — the **harness engineering** is where the value is. MCP tool integration, structured context extraction from emails, injury-aware prompting, rate limiting, XSS sanitisation, and an immutable audit trail. The LLM is just one component of a production-grade system." |

---

## 📋 Judge Scoring Rubric Cheat Sheet

| Criteria | How We Nail It |
|----------|----------------|
| **Innovation** | Multi-agent with HITL security gate — novel in sports tech |
| **Technical Depth** | Google ADK, MCP, A2A, YARA, Gemini, Supabase, Streamlit |
| **Real-World Impact** | Injury prevention through personalised training plans |
| **Responsible AI** | Guard Agent + HITL + input sanitisation + audit trail |
| **Documentation** | This script + README + architecture diagram + runnable demo |
| **Google Stack** | ADK ✓ Gemini ✓ A2A ✓ Vertex AI ✓ Cloud Logging ✓ |

---

## 🚀 Bonus: One-Click Deploy to Google Cloud

After impressing the judges locally, show the deployment:

```bash
cd sports-concierge
agents-cli deploy
```

This pushes the same agent to **Vertex AI Agent Engine** with:
- Auto-scaling (1–10 instances)
- Cloud Trace for observability
- BigQuery telemetry logging
- A2A protocol endpoint for other agents to discover

---

## 📦 Files for the Judges

| File | Purpose |
|------|---------|
| `docker-compose.yml` | One-command demo (Streamlit + Ollama) |
| `Dockerfile` | Containerised Streamlit app |
| `app.py` | Main dashboard orchestrator |
| `agents/guard.py` | Guard Agent — security gate + HITL |
| `agents/coach.py` | Coach Agent — Gemini/Ollama plan generation |
| `tools/server_mcp.py` | MCP protocol tools (email, drive, scan) |
| `security/sandbox.py` | YARA + MIME file scanner |
| `database/manager.py` | Supabase audit trail persistence |
| `sports-concierge/` | Google ADK project — deployable to Vertex AI |
| `sports-concierge/app/agent.py` | ADK multi-agent definition (Gemini) |
| `README.md` | Full architecture + setup guide |

---

**Good luck at the hackathon! 🏆**
