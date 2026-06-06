# Reference: Demo Guide (STEP 8)

Read this file when building the written demo guide for a customer demo.

---

## STEP 8 — Build Demo Guide

```python
from datetime import date
from pathlib import Path

def build_demo_guide(company_name, use_case, persona, story, signal_onset_months,
                     metrics, visualizations, concierge_questions,
                     workspace_name, sdm_name, script_name, company_slug, use_case_slug):
    today_str   = date.today().strftime("%B %d, %Y")
    metrics_rows = "\n".join(
        f"| {m['name']} | {m['type']} | {m.get('concierge_note', '')} |" for m in metrics)
    metrics_table = "| Metric | Type | Concierge note |\n|---|---|---|\n" + metrics_rows
    viz_sections = []
    for i, v in enumerate(visualizations, 1):
        points = "\n".join(f"  - {p}" for p in v["talking_points"])
        viz_sections.append(f"**{i}. {v['label']}** ({v['type']})\n{points}")
    viz_walkthrough = "\n\n".join(viz_sections)
    q_lines = "\n".join(f'{i+1}. "{q}"' for i, q in enumerate(concierge_questions))

    guide = f"""# {company_name} — {use_case} Demo Guide

**Persona:** {persona}
**Story:** {story}
**Signal onset:** {signal_onset_months} months ago, ramping to full effect today
**Built:** {today_str}

---

## Before You Demo

1. **Run the script** (if not already done): `python3 {script_name}`
2. **Enable Analytics Agent Readiness**: Data 360 → Semantic Model → **{sdm_name}** → Settings → Analytics Agent Readiness → toggle ON
3. **Business Preferences** are applied automatically by the script. To add custom preferences: Data 360 → Semantic Model → {sdm_name} → Business Preferences
4. **Seed Q&A Calibration**: Data 360 → Semantic Model → {sdm_name} → Q&A Calibration → add questions below as Verified Questions

---

## Metrics in This Demo

{metrics_table}

---

## Suggested Demo Walk-Through

Open the **{workspace_name}** workspace in Tableau Next.

{viz_walkthrough}

**Switch to Concierge:**
> "Now let me show you what happens when your {persona} just types a question..."

---

## Concierge Questions to Ask Live

{q_lines}

**Bonus — semantic learning question (most impressive moment):**
> Ask "Which reps are underperformers?"
> Concierge: "How do you define underperformer?"
> You define it in natural language → Concierge creates a calculated field on the fly.

---

## Q&A Calibration (show for data/IT audiences)

After the demo: Data 360 → {sdm_name} → Q&A Calibration → add these questions as Verified Questions, run a regression test.

---

## Teardown

```
python3 next_teardown.py
```

Workspace: {workspace_name}
"""
    Path(f"{company_slug}_{use_case_slug}_demo_guide.md").write_text(guide)
    print(f"  ✅ Demo guide written: {company_slug}_{use_case_slug}_demo_guide.md")
```

---

## Q&A Calibration Guide

*(Show for data/IT/analytics audiences — not executives.)*

Q&A Calibration lets data experts test and improve Concierge answer accuracy.

**What it does:**
- **Questions Bank** — library of test questions: New, Inaccurate, Verified, Regression
- **Verified Questions** — confirmed accurate; surfaced to the agent as ground truth
- **Batch Regression Testing** — run all VQs after any SDM change
- **AI Question Generation** — seed 10+ questions, generate 10/30/50 more

**How to build a demo-ready Questions Bank:**
1. Data 360 → Semantic Model → [model] → Q&A Calibration
2. Add 10–15 questions manually (one per metric, filtered, comparison, trend)
3. Ask Concierge each. For good answers → click **Verify**
4. Once 10+ Verified, use **Generate Questions** to expand
5. Create a **Regression Test suite** and run baseline

**Demo talking points by audience:**

| Audience | Focus |
|---|---|
| Executive / VP | Brief mention only |
| Revenue ops / analytics manager | Lead with it |
| IT / data engineering | Show regression testing |
| BI developer | Show question generation |

**Feedback-to-questions flow:**
Prospect gives feedback → "I can add that as a calibration question right now" → Verify → instant improvement
