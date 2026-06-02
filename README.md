# 🛡️ AegisGuard — Enterprise AI Safety Guardrails & Governance Platform

AegisGuard is a production-grade AI safety gateway, evaluation sandbox, and governance command portal. It provides real-time security auditing, threat classification, independent LLM-as-a-Judge quality scoring, custom policy threshold enforcement, and real-time Slack/Discord alerting for LLM applications.

![AegisGuard Dashboard Mockup](docs/images/dashboard.png)

---

## 🏗️ System Architecture

AegisGuard acts as an intelligent safety proxy between users (or client applications) and LLM providers. Below is a high-level overview of the AegisGuard system architecture:

![AegisGuard Architecture Diagram](docs/images/architecture.png)

### Architectural Components:
1. **FastAPI Gateway**: Serves as the high-throughput, asynchronous gateway exposing REST endpoints and a Server-Sent Events (SSE) real-time streaming endpoint.
2. **Multi-Stage Validation Pipeline**: Coordinates prompt scanners, response generation, post-generation validation, judge analysis, and final decision rules.
3. **Database Layer (SQLite)**: Persists raw prompts, candidate responses, validator metrics, overall scorecard ratings, security incidents, and active policy configurations.
4. **Alerting System**: Background worker dispatcher that sends structured notifications to configured Slack/Discord webhooks whenever high-severity threats are detected.

---

## 📡 The Multi-Stage Evaluation Pipeline

The evaluation pipeline executes in five sequential phases to ensure full coverage of input security, generation safety, policy alignment, and response quality.

![AegisGuard Pipeline Flow](docs/images/pipeline.png)

### Pipeline Stages & SSE Event Stream Lifecycle:

#### 1. Pre-Generation Stage
- **Scanning**: Scans incoming prompts using heuristic matches and an LLM-based scanner for **Prompt Injection** and **Jailbreak attempts** (e.g. DAN, virtual developer mode, obfuscation).
- **Events**:
  - `prompt_analysis_start`: Pre-generation safety analysis begins.
  - `prompt_analysis_done`: Returns prompt safety status, risk score, and categorized threat type.

#### 2. Response Generation Stage
- **Generation**: Dispatches payload to the selected candidate model (e.g., Claude, Gemini, GPT, DeepSeek, or a local model via Ollama).
- **Events**:
  - `generation_start`: Candidate generation initialized.
  - `generation_done`: Returns latency (ms), token counts (input/output), estimated API cost (USD), and response snippet.

#### 3. Post-Generation Stage
- **Scanning**: Runs security checks on the generated candidate response.
  - **Toxicity Detector**: Validates that generated content is free from toxicity.
  - **Hallucination Detector**: Cross-references generation against a reference context (ground truth) if provided.
  - **Policy Compliance Checker**: Validates response alignment against system safety guidelines.
- **Events**:
  - `response_validation_start`: Post-generation validator execution begins.
  - `response_validation_done`: Returns toxicity, compliance, and hallucination scores.

#### 4. LLM-as-a-Judge Scorecard Stage
- **Judgement**: An independent Judge LLM evaluates the candidate response's quality along 8 primary dimensions on a scale from 1.0 to 10.0:
  - **Relevance**: Direct alignment with the prompt.
  - **Correctness**: Accuracy against reference ground truth.
  - **Completeness**: Answering all parts of the request.
  - **Clarity**: Structure, readability, and coherence.
  - **Factual Consistency**: Absence of self-contradictions.
  - **Instruction Adherence**: Matching constraints and format commands.
  - **Attack Resistance**: Resilience in resisting jailbreak/injection attempts.
- **Events**:
  - `judge_evaluation_start`: Judge LLM scoring initialized.
  - `judge_evaluation_done`: Returns the multidimensional quality scorecard, strengths, weaknesses, risks, and reasoning justification.

#### 5. Decision Logic & Alerting Stage
- **Verdict**: The Decision Engine applies database-configured policy thresholds:
  - **Approve**: Passed all safety and quality metrics.
  - **Reject**: Blocked due to input attack, response toxicity, low compliance, or poor model resistance.
  - **Regenerate**: Triggers an automatic regeneration loop if the quality falls below the threshold or if hallucination risk is high (up to a configured retry limit).
- **Alerts**: If a high/critical security incident is flagged, the background worker dispatches a webhook notification to Slack/Discord.
- **Events**:
  - `decision_evaluation_start`: Evaluates ruleset checks.
  - `regeneration_triggered`: Notifies client of fallback generation cycle.
  - `pipeline_completed`: Saves final transaction record and finishes the connection.

---

## 🛡️ Active Security Guardrails & Policies

AegisGuard uses dynamic database-driven policies. Administrators can tune slider thresholds and enable/disable individual guardrails in real-time:

| Policy Name | Range / Type | Default | Description |
|:---|:---|:---|:---|
| `prompt_injection_threshold` | `0.0 - 1.0` (Lower = stricter) | `0.70` | Sensitivity control for prompt injection scanner. |
| `jailbreak_threshold` | `0.0 - 1.0` (Lower = stricter) | `0.50` | Sensitivity control for jailbreak detection. |
| `toxicity_threshold` | `0.0 - 1.0` (Lower = stricter) | `0.80` | Maximum allowed toxicity score in generated response. |
| `hallucination_threshold` | `0.0 - 1.0` (Lower = stricter) | `0.70` | Maximum allowed hallucination risk score (requires reference context). |
| `min_overall_score_for_approval` | `1.0 - 10.0` (Higher = stricter) | `7.00` | Minimum LLM-as-a-Judge quality score required for approval. |
| `max_regeneration_limit` | `1 - 5` | `2` | Maximum retry generation attempts before forcing a rejection. |

---

## 🎨 Professional Client Portal Features

The UI client portal provides a rich governance and testing workspace:

* **Interactive Console**:
  - Sandbox playground supporting selection of candidate models (Gemini, GPT, Claude, DeepSeek, Ollama) and judge models.
  - **Adversarial Attack Library** containing pre-built exploits (DAN jailbreak, Base64 obfuscation, Criminal roleplay, Prompt injection templates) for rapid security stress testing.
  - Real-time console terminal stepper rendering intermediate stream verdicts, latencies, and outputs.
* **Analytics Dashboard**:
  - **Hero KPIs**: Real-time tracking of Attack Resistance Rates, safety incident counts, and average judge quality scores.
  - **Model Safety Drift Chart**: Line chart visualizer tracking daily safety score distributions per model.
  - **Adversarial Stress Test Matrix**: Interactive heatmap highlighting grades (A to F) of candidate models against distinct exploit categories.
  - **Processing Latency Breakdown**: Bar chart mapping pipeline stage durations.
* **Audit History Trail**: Searchable grid displaying all past evaluations, complete with decision filter dropdowns, sorting headers, and search criteria.
* **Detail Inspector Modal**:
  - **Radar Scorecard**: Custom radar chart mapping the 8 judge parameters.
  - **Timeline Execution**: Process timeline tracking latencies (ms), input/output token usage, and validator scores.
* **Incidents Ledger**: Central registry documenting safety violations, categorized by severity, classification, timestamp, and incident description.
* **Guardrails Dashboard**: Live control panel for editing policy parameters and validating alert webhooks.

---

## 🚀 Verification & Local Execution

### Backend Setup
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate   # Windows
   source venv/bin/activate  # macOS/Linux
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure environment variables in `backend/.env` (e.g. OpenRouter API Key):
   ```env
   OPENROUTER_API_KEY=your-api-key-here
   DATABASE_URL=sqlite:///./app/database.db
   ```
5. Run the FastAPI development server:
   ```bash
   python -m app.main
   ```

### Frontend Setup
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Verify type-safety:
   ```bash
   npx tsc --noEmit
   ```
4. Run the Vite React application:
   ```bash
   npm run dev
   ```

### Docker Compose
Alternatively, launch both services together using Docker Compose:
```bash
docker-compose up --build
```
