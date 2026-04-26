# CME Build Day Repo

Assets, reference apps, pipelines, notebooks, and participant docs for the CME Build Day creative-generation workstream. This repo is the artifact surface participants work against during Build Day; LakeFoundry (the execution engine) lives in a separate repo.

See `build-day-data-dictionary.md` for the shared data contract.

## Directory layout

- `apps/` — Reference applications that participants study and extend. Home for the D2C home-screen reference app (Task 10) and the Campaign Studio front-end/back-end (Tasks 12-14). Each app gets its own subdirectory.
- `pipelines/` — Spark Declarative Pipelines definitions. Includes `pipelines/segment_hero_pregen/` for the batch segment-hero pre-generation pipeline (Task 9). One subdirectory per pipeline.
- `notebooks/validation/` — Validation and smoke-test notebooks used to confirm workspace capabilities, quotas, and contract adherence before and during Build Day. Task 2 lands the capability smoke test here.
- `docs/participant/` — Participant-facing documentation: operations notes, runbooks, and Build-Day-ready walkthroughs. Start with `00-operations-notes.md` for environment prerequisites.
