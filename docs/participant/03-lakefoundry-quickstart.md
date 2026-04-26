# 03 - LakeFoundry Quickstart

LakeFoundry is the "planning + vibe coding" system that drives Build Day. You describe what you want in a conversation; LakeFoundry turns it into a spec, runs a Tech Lead agent, and fans work out to Implementer subagents that scaffold the real app, pipeline, or skill. This doc walks you through the minimum path to build a sell-side or buy-side app via LakeFoundry instead of forking the reference apps by hand.

## 1. Open LakeFoundry

- **Dev (local laptop):** `http://localhost:8080`
- **Build Day (deployed Databricks App):** `https://<lakefoundry-app-url>` — your facilitator will share the exact URL at the start of the day.

Sign in with your Databricks identity.

## 2. Create a pod

A pod is a scoped workspace — it tells LakeFoundry which catalog/schema to target, which git branch to commit to, and which guardrails apply.

1. Click **New Pod** in the LakeFoundry UI.
2. Set the target to catalog `cme_outcomes_uswest`, schema `media_demo`.
3. Point the pod at this repo (`cme-buildday-repo`) on a feature branch you own.
4. Save.

If your UI differs or your facilitator has pre-seeded a pod for your team, use the shared one — confirm with the facilitator.

## 3. Start ideation

Open the chat in your pod and paste one of the prompts below. LakeFoundry will turn your prompt into a spec, confirm it with you, then hand off to the execution plane.

**Sell-side example prompt:**

> Build a D2C home-screen hero that personalizes per signed-in customer. Use `customer_360_gold_sync` keyed on `canonical_id` and join to `segment_hero_briefs` on `(primary_segment, value_segment, top_genre_1)`. Hero image + tagline + CTA + subtitle vary per customer. P95 < 500 ms. Never 5xx — fall back to a persona default. Add a HyperFrames intro animation on the hero. Use the five demo canonical IDs: demo-sports-01, demo-news-01, demo-binge-01, demo-casual-01, demo-cord-01.

**Buy-side example prompt:**

> Build a Campaign Studio where a marketing manager picks a segment and gets four cross-format tiles (social_square, vertical_story, display_banner, email_header) streaming in via SSE. Each tile has a regenerate button with low/medium quality toggle. Add campaign-level approve + export-to-zip. Persist campaigns and tile state to Lakebase in `media_demo.generated_campaigns`.

## 4. Skills LakeFoundry will invoke

Based on your prompt, the Tech Lead picks skills from the catalog. For sell-side and buy-side work, expect:

- **`d2c-home-screen-pattern`** — sell-side scaffold (FastAPI + Jinja + GSAP, hero endpoint, persona fallback).
- **`campaign-studio-pattern`** — buy-side scaffold (FastAPI + SSE, React UI, Lakebase persistence, four-format fan-out).
- **`azure-openai-image`** — calls Azure OpenAI `gpt-image-2` with the pinned `2025-04-01-preview` API version and caches results in the UC Volume.
- **`creative-brief-synthesis`** — turns a segment row into a structured image prompt + copy.
- **`personalized-creative-pipeline`** — end-to-end orchestration that joins customer data, generates brief, generates image, caches output.
- **`databricks-app-python`** or **`databricks-app-apx`** — Databricks App deploy glue.
- **`frontend-design`** — produces the polished, non-generic UI layer (GSAP animations for sell-side, React tiles for buy-side).

You should see the skill names referenced in the chat as the Tech Lead plans each step. If a skill you expected does not appear, flag it — that usually means the prompt was under-specified.

## 5. Execution plane: what to expect

Once you approve the spec, LakeFoundry fans out to subagents running on a Databricks Job:

- **Implementer** subagents write code and commit to your branch.
- **Spec Reviewer** checks the output against the spec.
- **Code Reviewer** checks for quality / guardrail violations.

You will see each step stream back into the chat. Typical run for a sell-side app: 5-10 minutes end-to-end. Buy-side is larger (React frontend + SSE backend + persistence) — closer to 15-20 minutes.

All LLM calls are traced in MLflow. If something looks wrong, ask the facilitator to pull up the trace.

## 6. How to iterate

You have two knobs:

- **Regen** — tell the Tech Lead to regenerate a specific file or step ("regenerate the hero endpoint", "redo the approve button"). Cheap and fast.
- **Modify the brief** — add or change requirements in chat ("also add a low-quality toggle on the hero"). The Tech Lead re-plans and re-dispatches affected tasks. Heavier but captures the change in the spec.

Prefer **modify the brief** when the requirement is missing or wrong. Prefer **regen** when the code is just subtly off.

## If you get stuck

- Can't find the LakeFoundry URL? Ask a facilitator.
- Pod creation flow looks different from the steps above? Use what the UI shows; the steps here are a skeleton — facilitators will confirm specifics at the start of the day.
- A skill didn't fire? Paste more constraints into the prompt (table names, latency targets, formats). The Tech Lead picks skills based on what you said you need.
