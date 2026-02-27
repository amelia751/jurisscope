# JurisScope Testing Guide

**Case:** DataSure vs TechNova — AI hiring bias, GDPR & EU AI Act compliance
**Documents loaded:** 16 files across regulations, internal docs, legal correspondence, case summaries & communications

---

## Case Overview

TechNova, a Berlin-based AI startup, developed **InsightPredict** — an AI hiring and performance prediction platform deployed to 127 client organisations covering ~450,000 employees and candidates across the EU. Internal testing (July–August 2024) and an independent investigation by DataSure, a Brussels-based advocacy group, found statistically significant bias:

| Bias Type | Internal Finding | DataSure Finding |
|-----------|-----------------|-----------------|
| Gender (resume scoring) | −7.1 pts (male vs female names) | −8.3 pts (−11.5 pts senior roles) |
| Age (performance prediction) | Lower scores for 50+ employees | Corroborated |
| African/Middle Eastern names | −5.8 pts | −3 to −6 pts |
| Asian names | −2.3 pts | Corroborated |
| Eastern European names | −3.1 pts | Corroborated |

DataSure threatened regulatory complaints in 5 jurisdictions unless TechNova settled. Settlement negotiations are underway (cap: €12M). Potential regulatory exposure: €50–100M+.

---

## Part 1: Discover Tab — Testing Guide

The Discover tab is your AI research assistant. Ask natural-language questions and it will retrieve answers with citations from the uploaded documents.

> **Tip:** After each answer, hover over citation numbers **[1]**, **[2]** etc. to see the exact source snippet.

---

### Quick-Start Questions (Try These First)

These give an immediate sense of the system's capabilities:

```
What are the main legal issues in the DataSure vs TechNova case?
```

```
What bias did Sofia Rodriguez find in TechNova's AI system?
```

```
What settlement terms is TechNova willing to accept?
```

```
What are the key obligations for high-risk AI systems under the AI Act?
```

---

### GDPR & Data Protection

```
What are the key principles of GDPR for personal data processing?
```

```
How does GDPR define personal data and what categories exist?
```

```
What are the requirements for valid consent under GDPR?
```

```
What are the penalties for GDPR violations?
```

```
What is the difference between a data controller and processor under GDPR?
```

```
When can special categories of personal data be processed?
```

```
What does GDPR Article 5(1)(a) require and how does TechNova allegedly violate it?
```

```
How does GDPR Article 22 apply to TechNova's automated scoring system?
```

---

### EU AI Act

```
What is considered a high-risk AI system under the AI Act?
```

```
What are the AI Act requirements for high-risk AI systems?
```

```
What does Article 10 of the AI Act require about training data?
```

```
What risk management procedures does Article 9 of the AI Act require?
```

```
What does the AI Act say about human oversight requirements in Article 14?
```

```
How does the AI Act address transparency requirements?
```

```
How does the AI Act regulate AI systems used in employment decisions?
```

```
What penalties does the AI Act impose for violations?
```

---

### TechNova's Bias — Technical Deep Dive

```
What statistical evidence did Sofia Rodriguez present about gender bias in the resume scoring model?
```

```
What were the ethnicity bias test results for African, Middle Eastern, and Eastern European names?
```

```
What is the "garbage in, garbage out" problem as it applies to TechNova's training data?
```

```
Why does TechNova's BERT-based NLP pipeline produce biased scores even when names are not an explicit feature?
```

```
What is the fairness-accuracy tradeoff and how does it apply to TechNova's situation?
```

```
What fairness constraints did TechNova deploy on September 1, 2024 and what was the impact?
```

```
What is the 78% correlation figure mentioned in the case and why is it legally significant?
```

```
What specific bias testing methodology did DataSure use to identify discrimination?
```

---

### TechNova Internal Communications

```
What were the key findings from the #ml-engineering-private Slack channel discussions in July 2024?
```

```
When did TechNova first become aware of bias in its AI system?
```

```
What did Dr. Michael Zhang say about the root cause of TechNova's BERT embedding bias?
```

```
What were the four options Sofia Rodriguez proposed for fixing the training data bias?
```

```
What concerns did Elena Kovács raise in the email thread about GDPR and AI Act violations?
```

```
What did Sarah Mitchell advise about documentation and attorney-client privilege?
```

```
What did Jennifer Hartley decide as the company's path forward after the bias was confirmed?
```

```
What internal discussions show TechNova's awareness of compliance issues before DataSure's complaint?
```

---

### Legal Strategy & Settlement

```
What are the main allegations in DataSure's complaint letter?
```

```
What settlement terms were proposed in the mediation discussions?
```

```
How did TechNova respond to DataSure's initial complaint letter?
```

```
What are the three strategic options TechNova discussed for responding to DataSure?
```

```
What is the estimated total regulatory penalty exposure for TechNova?
```

```
What did external counsel Dr. Friedrich Bauer recommend as the best legal strategy?
```

```
What conditions did Sarah Mitchell say TechNova should NOT agree to in a settlement?
```

```
What is the estimated probability of enforcement action for each AI Act article violation?
```

---

### Case Timeline & People

```
Who are the key individuals mentioned in the TechNova case and what are their roles?
```

```
What is the chronological sequence of events in the TechNova case from July to October 2024?
```

```
What decisions were made at the September 18, 2024 compliance strategy meeting?
```

```
Who attended the September 18 emergency meeting and what was each person's position?
```

```
What actions did Marcus Thompson assign as immediate priorities after the August emergency meeting?
```

---

### Cross-Document Analysis

These questions require the system to synthesise across multiple documents — a strong test of retrieval quality:

```
How does TechNova's AI system compliance compare to GDPR and AI Act requirements?
```

```
What evidence shows TechNova violated both GDPR and the AI Act?
```

```
What contradictions exist between TechNova's public statements and internal documents?
```

```
How do the internal Slack and email communications relate to the external lawsuit claims?
```

```
Compare the requirements in the Data Processing Agreement to TechNova's actual documented practices.
```

```
What legal frameworks apply to TechNova's InsightPredict hiring AI system?
```

```
If TechNova implemented all recommended risk mitigation measures, would they be compliant with both GDPR and the AI Act?
```

```
What evidence in internal documents supports or contradicts DataSure's bias allegations?
```

---

### Risk & Compliance

```
What risk mitigation measures did TechNova implement and what gaps remain?
```

```
What data governance issues were identified in TechNova's practices?
```

```
What fundamental rights impact assessment should TechNova have conducted?
```

```
What compliance gaps exist under Article 9, 10, and 14 of the AI Act?
```

```
What human oversight mechanisms were implemented after the bias was discovered?
```

```
What are the potential financial consequences for TechNova based on identified violations?
```

```
How could TechNova modify their AI system to meet EU compliance standards?
```

---

### Targeted Feature Tests

Use these to validate specific system behaviours:

**Citation accuracy**
```
What specific articles of GDPR and the AI Act did TechNova allegedly violate?
```
*Expected: Multiple article citations with exact article numbers from both regulations*

**Multi-document synthesis**
```
Compare what TechNova stated publicly versus what internal Slack messages and emails reveal.
```
*Expected: Citations from the news article, Slack export, and email thread*

**Precise numerical retrieval**
```
What specific statistics are mentioned about bias in TechNova's AI system — score differentials, p-values, and accuracy metrics?
```
*Expected: Exact numbers — 7.1 pts gender gap, p < 0.001, F1 0.78 to 0.75, etc.*

**Temporal/timeline retrieval**
```
What is the exact sequence of bias discovery, internal escalation, and external complaint between July and October 2024?
```
*Expected: Specific dates from Slack, emails, and meeting notes*

**Entity extraction**
```
List all named individuals in the case, their organisations, and their roles.
```
*Expected: Full cast from multiple documents — Sofia Rodriguez, Jennifer Hartley, Dr. Anne-Marie Rousseau, etc.*

**Elasticsearch hybrid search**
```
What are the data protection requirements for AI systems processing personal data in employment contexts?
```
*Tests BM25 + vector hybrid retrieval across both the GDPR regulation and AI Act*

**Elastic Agent Builder integration**
```
Search for all documents mentioning "consent" in the context of GDPR.
```

---

## Part 2: Table Tab — Generating Columns Guide

The Table tab lets you select documents from your vault and extract structured attributes as columns. Each row is a document; each column is a field the AI extracts.

Below are suggested column prompts organised by analysis type. Mix and match based on your use case.

---

### Document Classification Columns

| Column Name | Prompt |
|-------------|--------|
| Document Type | What type of document is this? (e.g. regulation, internal memo, email thread, legal correspondence, news article, meeting minutes) |
| Document Date | What is the date of this document? |
| Authoring Party | Who authored or produced this document? |
| Classification Level | What confidentiality classification is assigned to this document? (e.g. Public, Confidential, Attorney-Client Privileged) |
| Primary Subject | What is the main topic or subject of this document in one sentence? |

---

### Legal & Regulatory Analysis Columns

| Column Name | Prompt |
|-------------|--------|
| Regulations Cited | Which EU regulations or legal frameworks are cited or referenced? (e.g. AI Act, GDPR, EU Employment Equality Directives) |
| Specific Articles Cited | List the specific article numbers and regulations mentioned (e.g. GDPR Article 5(1)(a), AI Act Article 10). |
| Legal Violations Alleged | What legal violations or compliance gaps does this document allege or identify? |
| Violation Severity | Rate the severity of any violations mentioned: Critical / High / Medium / Low |
| Legal Strategy Recommended | What legal strategy or course of action does this document recommend? |
| Applicable Penalty | What financial penalty or legal consequence is mentioned or estimated? |

---

### Bias & Technical Findings Columns

| Column Name | Prompt |
|-------------|--------|
| Bias Type Identified | What types of bias are identified or discussed? (e.g. gender, age, ethnicity, name-based) |
| Bias Score / Metric | What specific quantitative bias metrics are mentioned? (e.g. score differentials, p-values, F1 scores) |
| Protected Characteristics | Which protected characteristics are affected according to this document? |
| Root Cause of Bias | What does this document identify as the root cause of the bias? |
| Mitigation Measures | What technical or procedural bias mitigation measures are described? |
| Residual Risk After Fix | Does this document acknowledge remaining bias after mitigation? What level? |

---

### Parties & People Columns

| Column Name | Prompt |
|-------------|--------|
| Key Parties | Who are the key parties or organisations mentioned? |
| Key Individuals | List the named individuals mentioned and their roles. |
| Decision Makers | Who are identified as decision-makers or authority figures in this document? |
| Whistleblower / Escalator | Is there a person who raised or escalated the issue? Who? |
| External Parties | What external organisations, regulators, or counsel are referenced? |

---

### Settlement & Risk Columns

| Column Name | Prompt |
|-------------|--------|
| Settlement Terms | What settlement terms or conditions are discussed? |
| Financial Exposure | What is the total financial exposure or cost estimate mentioned? |
| Regulatory Risk Level | How does this document characterise the regulatory risk? (High / Medium / Low + reason) |
| Claimant Demands | What does the claimant or advocacy group demand in this document? |
| Recommended Response | What response or negotiating position does this document recommend? |
| Walk-Away Conditions | Are any non-negotiable or walk-away conditions mentioned? |

---

### Human Oversight & AI Governance Columns

| Column Name | Prompt |
|-------------|--------|
| Human Oversight Mechanism | What human oversight mechanisms are described or required? |
| Automation Bias Risk | Does this document discuss automation bias or over-reliance on AI recommendations? |
| Override Rate | Is there a human override rate mentioned? What is it? |
| Explainability Features | What explainability or transparency features are described? |
| AI Governance Gaps | What governance or oversight gaps does this document identify? |
| Fairness-by-Design | Does this document describe any fairness-by-design principles or constraints? |

---

### Timeline & Action Columns

| Column Name | Prompt |
|-------------|--------|
| Key Date | What is the most important date mentioned in this document? |
| Deadline Mentioned | Is any deadline or time constraint mentioned? What is it? |
| Action Items | What specific action items or next steps are assigned in this document? |
| Responsible Person | Who is assigned responsibility for actions in this document? |
| Completion Status | Does the document indicate whether any actions have been completed? |

---

### Suggested Column Sets by Use Case

**Regulatory Audit Review** — apply to all 16 documents:
- Document Type, Document Date, Regulations Cited, Specific Articles Cited, Legal Violations Alleged, Violation Severity, Applicable Penalty

**Bias Evidence Review** — apply to internal docs + communications:
- Bias Type Identified, Bias Score / Metric, Protected Characteristics, Root Cause of Bias, Mitigation Measures, Residual Risk After Fix

**Settlement Due Diligence** — apply to legal correspondence + meeting notes:
- Key Parties, Settlement Terms, Financial Exposure, Claimant Demands, Recommended Response, Walk-Away Conditions

**Internal Investigation Timeline** — apply to Slack + email + meeting notes:
- Document Date, Key Individuals, Whistleblower / Escalator, Key Date, Deadline Mentioned, Action Items, Responsible Person

---

## Tips for Best Results

**Good Discover questions:**
- Specific and grounded: `"What does Article 10 of the AI Act require about training data examination?"`
- Cross-reference: `"How do internal emails contradict TechNova's public statements?"`
- Request synthesis: `"Compare the bias numbers in DataSure's report versus TechNova's internal findings"`

**Questions that may struggle:**
- Too broad: `"Tell me everything about GDPR"`
- Outside the documents: `"What happened after October 2024?"`
- Requires external data: `"What is the current AI Act enforcement status?"`

**Good Table columns:**
- Ask for a single, clear attribute per column
- Use consistent value types (dates as dates, ratings as labels, lists as comma-separated)
- For numeric columns, specify the unit or scale expected

