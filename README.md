# **🏆 Sports Concierge Agent**

An **AI-powered multi-agent system** that generates personalised sports training plans. Built with Google ADK, FastMCP, Ollama, and Streamlit — featuring a **Human-in-the-Loop (HITL)** security gate before plan generation.

## **High-Level Architecture**

````mermaid
flowchart TD

subgraph group_dashboard["Dashboard workflow"]
  node_dashboard_app["Streamlit dashboard<br/>[app.py]"]
  node_plan_result["Training plan"]
end

subgraph group_agents["Agent workflow"]
  node_guard["Guard agent<br/>[guard.py]"]
  node_coach["Coach agent<br/>[coach.py]"]
end

subgraph group_tools["Context and security tools"]
  node_email["Email context<br/>[server_mcp.py]"]
  node_drive["Drive files<br/>[server_mcp.py]"]
  node_mcp_scan["MCP scan tool<br/>[server_mcp.py]"]
  node_scanner["Security scanner<br/>[sandbox.py]"]
end

subgraph group_persistence["Audit persistence"]
  node_audit["Audit trail<br/>[manager.py]"]
end

subgraph group_serving["ADK serving"]
  node_fastapi["FastAPI app<br/>[fast_api_app.py]"]
  node_adk_agent["ADK agent<br/>[agent.py]"]
  node_a2a_routes["A2A routes<br/>[a2a.py]"]
  node_reasoning_routes["Reasoning routes"]
  node_shared_services["Shared services<br/>[services.py]"]
  node_telemetry["Telemetry<br/>[telemetry.py]"]
  node_feedback_model["Feedback schema<br/>[typing.py]"]
end

node_athlete(("Athlete"))
node_plan_model["Plan model"]
node_supabase[("Supabase")]
node_adk_client(("ADK client"))

node_athlete -->|"enters details"| node_dashboard_app
node_dashboard_app -->|"requests assessment"| node_guard
node_guard -->|"gathers context"| node_email
node_guard -->|"gathers context"| node_drive
node_guard -->|"requests scans"| node_mcp_scan
node_mcp_scan -->|"delegates scan"| node_scanner
node_guard -->|"returns risk"| node_dashboard_app
node_athlete -->|"approves or denies"| node_dashboard_app
node_dashboard_app -->|"requests plan"| node_coach
node_coach -->|"generates with"| node_plan_model
node_plan_model -->|"returns plan"| node_dashboard_app
node_dashboard_app -->|"displays and downloads"| node_plan_result
node_dashboard_app -.->|"logs events"| node_audit
node_audit -->|"writes events"| node_supabase
node_adk_client -.->|"calls API"| node_fastapi
node_fastapi -->|"loads agent"| node_adk_agent
node_fastapi -->|"attaches routes"| node_a2a_routes
node_fastapi -->|"attaches routes"| node_reasoning_routes
node_fastapi -->|"uses services"| node_shared_services
node_fastapi -->|"sets up"| node_telemetry
node_fastapi -->|"validates feedback"| node_feedback_model
node_reasoning_routes -->|"dispatches methods"| node_adk_agent
node_reasoning_routes -->|"reuses services"| node_shared_services

click node_dashboard_app "https://github.com/yobo-dance/project-google-hackathon/blob/main/app.py"
click node_guard "https://github.com/yobo-dance/project-google-hackathon/blob/main/agents/guard.py"
click node_coach "https://github.com/yobo-dance/project-google-hackathon/blob/main/agents/coach.py"
click node_email "https://github.com/yobo-dance/project-google-hackathon/blob/main/tools/server_mcp.py"
click node_drive "https://github.com/yobo-dance/project-google-hackathon/blob/main/tools/server_mcp.py"
click node_mcp_scan "https://github.com/yobo-dance/project-google-hackathon/blob/main/tools/server_mcp.py"
click node_scanner "https://github.com/yobo-dance/project-google-hackathon/blob/main/security/sandbox.py"
click node_audit "https://github.com/yobo-dance/project-google-hackathon/blob/main/database/manager.py"
click node_fastapi "https://github.com/yobo-dance/project-google-hackathon/blob/main/sports-concierge/app/fast_api_app.py"
click node_adk_agent "https://github.com/yobo-dance/project-google-hackathon/blob/main/sports-concierge/app/agent.py"
click node_a2a_routes "https://github.com/yobo-dance/project-google-hackathon/blob/main/sports-concierge/app/app_utils/a2a.py"
click node_reasoning_routes "https://github.com/yobo-dance/project-google-hackathon/blob/main/sports-concierge/app/app_utils/reasoning_engine_adapter.py"
click node_shared_services "https://github.com/yobo-dance/project-google-hackathon/blob/main/sports-concierge/app/app_utils/services.py"
click node_telemetry "https://github.com/yobo-dance/project-google-hackathon/blob/main/sports-concierge/app/app_utils/telemetry.py"
click node_feedback_model "https://github.com/yobo-dance/project-google-hackathon/blob/main/sports-concierge/app/app_utils/typing.py"

classDef toneNeutral fill:#f8fafc,stroke:#334155,stroke-width:1.5px,color:#0f172a
classDef toneBlue fill:#dbeafe,stroke:#2563eb,stroke-width:1.5px,color:#172554
classDef toneAmber fill:#fef3c7,stroke:#d97706,stroke-width:1.5px,color:#78350f
classDef toneMint fill:#dcfce7,stroke:#16a34a,stroke-width:1.5px,color:#14532d
classDef toneRose fill:#ffe4e6,stroke:#e11d48,stroke-width:1.5px,color:#881337
classDef toneIndigo fill:#e0e7ff,stroke:#4f46e5,stroke-width:1.5px,color:#312e81
classDef toneTeal fill:#ccfbf1,stroke:#0f766e,stroke-width:1.5px,color:#134e4a
class node_dashboard_app,node_plan_result,node_adk_client toneBlue
class node_guard,node_coach,node_supabase toneAmber
class node_email,node_drive,node_mcp_scan,node_scanner toneMint
class node_audit toneRose
class node_fastapi,node_adk_agent,node_a2a_routes,node_reasoning_routes,node_shared_services,node_telemetry,node_feedback_model,node_athlete,node_plan_model toneIndigo
````
## **Project Structure**

sports-concierge-agent/  
├── agents/                 \# Google ADK Agent definitions  
│   ├── \_\_init\_\_.py         \# Package exports  
│   ├── guard.py            \# Guard Agent — security analysis \+ HITL  
│   └── coach.py            \# Coach Agent — Ollama training plan generation  
├── tools/                  \# MCP tool server  
│   ├── \_\_init\_\_.py         \# Package exports  
│   └── server\_mcp.py       \# FastMCP server (3 tools)  
├── security/               \# Security scanning module  
│   ├── \_\_init\_\_.py         \# Package exports  
│   └── sandbox.py          \# YARA \+ heuristic file scanning  
├── app.py                  \# Streamlit dashboard orchestrator  
├── requirements.txt        \# Python dependencies  
└── README.md               \# This file

## **Workflow**

| Step | Component | Description |
| :---- | :---- | :---- |
| **1** | app.py | User enters sport, skill level, and context flags |
| **2** | guard.py | Guard Agent gathers email context, drive files, and performs security scans |
| **3** | guard.py | Risk assessment: low → auto-proceed; medium/high → require approval |
| **4** | app.py | Human-in-the-Loop pause — user approves or denies |
| **5** | coach.py | Coach Agent generates 3-day workout via local llama3.1 |
| **6** | app.py | Display plan, download as Markdown, and audit trail |

## **Quick Start**

\# 1\. Install dependencies  
pip install \-r requirements.txt

\# 2\. Start Ollama (for training plan generation)  
ollama serve

\# 3\. Launch the dashboard  
streamlit run app.py

\# 4\. (Optional) Start the MCP server standalone  
python \-m tools.server\_mcp

## **Security & Compliance**

### **Dependency Auditing**

All Python dependencies are audited for known vulnerabilities using pip-audit:

pip install pip-audit  
pip-audit \-r requirements.txt

### **GuardAgent — Input Sanitisation**

Before user input reaches the LLM, it passes through GuardAgent.sanitize\_input to neutralize:

* **Shell-command injection** (rm \-rf, os.system)  
* **HTML/script injection** (\<script\>, javascript:)  
* **SQL injection** (DROP TABLE, UNION SELECT)  
* **Path traversal** (../, /etc/passwd)

### **YARA \+ MIME File Scanning**

Every file retrieved is scanned via SecurityScanner:

* **MIME-type heuristics**: Rejects executable formats (.sh, .exe, .bat).  
* **YARA rules**: Detects suspicious patterns (eval(, base64\_decode).

### **Human-in-the-Loop (HITL)**

If a risk score ≥ 30 is detected, the workflow pauses, requiring explicit human approval—ensuring compliance with SOC 2/ISO 27001 principles.
