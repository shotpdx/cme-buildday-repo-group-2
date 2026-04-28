# Databricks notebook source
# MAGIC %md
# MAGIC # Creative Generation Capability Validation
# MAGIC Validates Azure OpenAI gpt-image-2 across all design-doc personas and format aspects.
# MAGIC Run locally (PAT) or as a notebook task; writes results into MLflow and the local disk.

# COMMAND ----------
import base64
import json
import os
import subprocess
import time
from pathlib import Path

from openai import AzureOpenAI
from fixtures import PERSONAS, FORMATS, PROMPT_FOR

OUT_DIR = Path("/tmp/creative_validation")
OUT_DIR.mkdir(exist_ok=True, parents=True)

SMOKE_TEST = True  # flip to False for full 5x4 matrix (~8-10 min)
personas_to_run = PERSONAS[:1] if SMOKE_TEST else PERSONAS
formats_to_run  = FORMATS[:1]  if SMOKE_TEST else FORMATS

# COMMAND ----------
def get_api_key() -> str:
    if os.environ.get("AZURE_OPENAI_KEY"):
        return os.environ["AZURE_OPENAI_KEY"]
    r = subprocess.run(
        ["databricks", "secrets", "get-secret", "lakefoundry", "AZURE_OPENAI_KEY",
         "--profile", "cme-outcomes", "-o", "json"],
        capture_output=True, text=True, check=True,
    )
    return base64.b64decode(json.loads(r.stdout)["value"]).decode()

client = AzureOpenAI(
    azure_endpoint="https://lakefoundry-azure-openai.openai.azure.com/",
    api_key=get_api_key(),
    api_version="2025-04-01-preview",
)

# COMMAND ----------
results = []
for persona in personas_to_run:
    for fmt in formats_to_run:
        prompt = PROMPT_FOR(persona, fmt)
        t0 = time.time()
        try:
            resp = client.images.generate(
                model="gpt-image-2", prompt=prompt,
                size=fmt["size"], quality="low", n=1,
            )
            dt = time.time() - t0
            img = resp.data[0]
            out = OUT_DIR / f"{persona.replace(' ', '_')}_{fmt['name']}.png"
            out.write_bytes(base64.b64decode(img.b64_json))
            status = "OK"
            err = None
        except Exception as e:
            dt = time.time() - t0
            status = "FAIL"
            err = f"{type(e).__name__}: {e}"
        results.append({"persona": persona, "format": fmt["name"], "status": status,
                        "latency_s": round(dt, 1), "error": err})
        print(f"  {persona:<28} {fmt['name']:<18} {status:<5} {dt:5.1f}s")

# COMMAND ----------
import pandas as pd
df = pd.DataFrame(results)
print(df.to_string())
assert (df["status"] == "OK").all(), f"Failed calls: {df[df.status != 'OK'].to_dict('records')}"
mode = "Smoke test" if SMOKE_TEST else "Full validation"
print(f"\n{mode}: {len(df)}/{len(df)} OK. Artifacts in {OUT_DIR}")
