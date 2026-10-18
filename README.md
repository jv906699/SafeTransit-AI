
<div align="center">

<img
  src="https://capsule-render.vercel.app/api?type=waving&height=220&color=0:020617,50:083344,100:06b6d4&text=SafeTransit-AI&fontColor=ecfeff&fontSize=58&fontAlignY=38&desc=AI-Assisted%20Code%20Modernization&descAlignY=58&animation=fadeIn&stroke=06b6d4&strokeWidth=1"
  width="100%"
  alt="SafeTransit-AI animated header"
/>

<a href="https://git.io/typing-svg">
  <img
    src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=500&size=19&duration=2800&pause=800&color=22D3EE&center=true&vCenter=true&width=800&lines=
<a href="https://git.io/typing-svg">
  <img
    src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=500&size=17&duration=3000&pause=900&color=22D3EE&center=true&vCenter=true&width=850&lines=
<a href="https://git.io/typing-svg">
  <img
    src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=500&size=17&duration=2800&pause=850&color=22D3EE&center=true&vCenter=true&width=900&lines=AST-Based+Structural+Code+Analysis;Static+Analysis+%26+Diagnostic-Driven+Repair;LLM-Assisted+Legacy+Code+Modernization;Compiler+%26+Syntax-Level+Validation;Verifying+AI-Generated+Code+Changes;Exploring+Safer+Automated+Code+Transformation"
    alt="SafeTransit-AI: AST analysis, static analysis, AI-assisted repair, and code verification"
/>
</a>

</div>

---

<div align="center">

## 🔬 Research Focus

**Can AI-assisted code modernization be made more reliable through structural analysis and independent verification?**

*An experimental pipeline exploring the intersection of static analysis, compiler tooling, and local large language models.*

</div>

## 🧩 The Problem

Legacy code modernization is not simply a matter of generating cleaner code. Automated changes can introduce syntax errors, alter program behavior, weaken safety checks, or create new defects.

Large language models can propose useful transformations, but their output must be evaluated independently rather than trusted by default.

SafeTransit-AI explores a verification-oriented approach to this challenge.

## 🎯 Project Objective

Build a research prototype that combines:

- **AST-based analysis** to inspect source code structure.
- **Static analysis and diagnostics** to identify potential defects.
- **LLM-assisted repair** to generate candidate code changes.
- **Automated verification** to evaluate candidates before accepting their results.
- **Attempt tracking** to distinguish successful verification from failed repair attempts.

## ⚙️ Research Approach

| Stage | Engineering approach | Purpose |
|:--|:--|:--|
| 01 · Analyze | Tree-sitter and AST-based parsing | Inspect source structure and detect syntax issues |
| 02 · Diagnose | Static analysis and verification tools | Collect actionable diagnostics |
| 03 · Transform | Local LLM through Ollama | Generate a candidate repair or optimization |
| 04 · Verify | Automated checks | Evaluate the candidate against available checks |
| 05 · Report | Pipeline orchestration and result history | Expose the outcome and remaining issues |

## 📌 Current Scope

SafeTransit-AI is a **local research prototype** supporting Python and C workflows. It uses a Streamlit interface, Tree-sitter-based parsing, a local Ollama model, and automated verification tools.

The current implementation is an exploration of safer AI-assisted transformation—not a proof of semantic equivalence, complete memory safety, or production readiness.

**Current engineering checkpoint:** 86 automated tests passed; Ruff checks passed. Cloud deployment remains pending.

---

---

<a id="architecture"></a>

## 🏗️ System Architecture

SafeTransit-AI separates the user interface, source-code analysis, model interaction, pipeline orchestration, and verification into distinct modules.

```mermaid
flowchart TD
    U["👤 Developer"]
    UI["Streamlit UI<br/>src/app.py"]
    CFG["Configuration<br/>src/config.py"]

    U --> UI
    CFG -.-> UI

    UI --> MODE{"Operation Mode"}

    MODE -->|"Repair"| R["Repair Workflow"]
    MODE -->|"Optimize"| O["Optimization Workflow"]

    R --> ORCH["Pipeline Orchestrator<br/>src/orchestrator.py"]
    O --> ORCH

    ORCH --> PARSE["Tree-sitter Parser<br/>src/parser.py"]
    PARSE --> DIAG["Syntax & Analysis Diagnostics"]

    DIAG --> AGENT["LLM Repair Agent<br/>src/ollama_agent.py"]
    AGENT --> CLIENT["Ollama Client<br/>src/ollama_client.py"]
    CLIENT --> MODEL["Local LLM<br/>Ollama"]

    MODEL --> CANDIDATE["Candidate Code"]
    CANDIDATE --> VERIFY["Verification Runner<br/>src/verifier.py"]

    VERIFY --> RESULT{"Verification Result"}

    RESULT -->|"Pass"| ACCEPT["Verified Candidate"]
    RESULT -->|"Fail, attempts remain"| FEEDBACK["Diagnostics & Repair Context"]
    FEEDBACK --> ORCH
    RESULT -->|"Fail, limit reached"| FAILED["Unverified Result<br/>Report Remaining Issues"]

    ACCEPT --> REPORT["Results & Attempt History"]
    FAILED --> REPORT
    REPORT --> UI

    BENCH["Benchmark Runner<br/>src/benchmark.py"]
    BENCH -.-> REPORT

    classDef interface fill:#102a43,stroke:#22d3ee,color:#ffffff
    classDef analysis fill:#172554,stroke:#60a5fa,color:#ffffff
    classDef inference fill:#164e63,stroke:#22d3ee,color:#ffffff
    classDef verification fill:#14532d,stroke:#4ade80,color:#ffffff
    classDef failure fill:#451a1a,stroke:#f87171,color:#ffffff

    class UI,U interface
    class PARSE,DIAG,ORCH analysis
    class AGENT,CLIENT,MODEL inference
    class VERIFY,ACCEPT verification
    class FAILED failure
```

> The diagram is a conceptual view of the modules and intended workflow. Before publishing it as the definitive implementation diagram, we'll confirm the exact call order and benchmark reporting path against the current source files.


### 🔎 Architecture Glossary

| Component | Role in SafeTransit-AI |
|---|---|
| <abbr title="Abstract Syntax Tree: a tree representation of source-code structure">AST</abbr> | Represents source code structurally so it can be parsed and inspected. |
| <abbr title="Static analysis examines code without relying solely on executing the program">Static Analysis</abbr> | Identifies potential issues through automated source-code checks. |
| <abbr title="Large Language Model">LLM</abbr> | Proposes candidate code transformations using the local Ollama model. |
| <abbr title="The module that coordinates parsing, repair attempts, verification and results">Orchestrator</abbr> | Controls the pipeline and tracks repair attempts. |
| <abbr title="Automated checks applied to a candidate before it is reported as verified">Verification</abbr> | Evaluates the candidate against the checks currently implemented. |
| <abbr title="A failed verification result used to guide another repair attempt">Diagnostic Feedback</abbr> | Supplies error information for subsequent attempts when permitted. |


---

<a id="features"></a>

## 🔄 Repair vs. Optimize

SafeTransit-AI provides two operation modes for exploring AI-assisted code transformation. Both evaluate generated candidates, but they begin with different objectives.

<table>
<thead>
<tr>
<th align="left">Dimension</th>
<th align="left">🛠️ Repair Mode</th>
<th align="left">⚡ Optimize Mode</th>
</tr>
</thead>
<tbody>
<tr>
<td><strong>Primary goal</strong></td>
<td>Address detected defects and verification failures.</td>
<td>Explore improvements to code that already passes the required initial checks.</td>
</tr>
<tr>
<td><strong>Starting point</strong></td>
<td>Source code requiring correction.</td>
<td>Source code selected for improvement.</td>
</tr>
<tr>
<td><strong>Model involvement</strong></td>
<td>Generate a candidate repair using available diagnostics.</td>
<td>Generate a candidate optimization.</td>
</tr>
<tr>
<td><strong>Verification</strong></td>
<td>Evaluate the candidate using the implemented checks.</td>
<td>Evaluate the optimized candidate using the implemented checks.</td>
</tr>
<tr>
<td><strong>Possible outcome</strong></td>
<td>Verified candidate, or a reported failure with remaining diagnostics.</td>
<td>Verified candidate, or a reported failure with remaining diagnostics.</td>
</tr>
</tbody>
</table>

> **Important:** Passing the available checks does not guarantee semantic equivalence, complete memory safety, or improved runtime performance. Optimization claims require appropriate benchmarks, and verification claims are limited to the checks actually performed.






