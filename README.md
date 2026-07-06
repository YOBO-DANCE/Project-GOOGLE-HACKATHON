# **🏆 Sports Concierge Agent**

An **AI-powered multi-agent system** that generates personalised sports training plans. Built with Google ADK, FastMCP, Ollama, and Streamlit — featuring a **Human-in-the-Loop (HITL)** security gate before plan generation.

## **High-Level Architecture**

```mermaid
flowchart TB
    subgraph User["👤 User Layer"]
        UI["Streamlit Dashboard<br/>(app.py)"]
    end

    subgraph Agents["🤖 Agent Layer (Google ADK)"]
        GA["Guard Agent<br/>(agents/guard.py)<br/>Security Analysis + HITL"]
        CA["Coach Agent<br/>(agents/coach.py)<br/>Training Plan Generation"]
    end

    subgraph Tools["🔧 Tool Layer (MCP Server)"]
        MCP["FastMCP Server<br/>(tools/server_mcp.py)"]
        T1["get_email_context<br/>📧 Retrieve email metadata"]
        T2["get_drive_files<br/>📁 Search cloud drive"]
        T3["scan_file_security<br/>🔒 YARA + heuristic scan"]
    end

    subgraph Security["🛡️ Security Layer"]
        SB["sandbox.py<br/>YARA rules<br/>Heuristic patterns<br/>MIME detection"]
    end

    subgraph Inference["🧠 Inference Layer"]
        OLLAMA["Ollama<br/>(llama3.1 local model)"]
    end

    UI -->|"1. Input<br/>(sport, level)"| GA
    GA -->|"2. Gather context"| MCP
    MCP --> T1
    MCP --> T2
    MCP --> T3
    T3 --> SB
    GA -->|"3. Risk assessment"| UI
    UI -->|"4. HITL approval"| CA
    CA -->|"5. Generate plan"| OLLAMA
    OLLAMA -->|"6. Training plan"| UI

    classDef agent fill:#4A90D9,color:#fff,stroke:#2C5F8A
    classDef tool fill:#7B68EE,color:#fff,stroke:#5A4FBF
    classDef security fill:#E74C3C,color:#fff,stroke:#C0392B
    classDef inference fill:#27AE60,color:#fff,stroke:#1E8449
    classDef ui fill:#F39C12,color:#fff,stroke:#D68910
    class GA,CA agent
    class MCP,T1,T2,T3 tool
    class SB security
    class OLLAMA inference
    class UI ui

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
