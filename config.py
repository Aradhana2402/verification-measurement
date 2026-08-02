"""Central config — edit MODEL IDs to match your providers, and set
GENERATION_SETTINGS to EXACTLY match your original Phase 2 study."""

# --- Models (litellm identifiers) ---------------------------------------
# Adjust to your accounts. Llama route options: together_ai, groq, fireworks.
MODELS = {
    "gpt4o":  "gpt-4o",
    "claude": "anthropic/claude-sonnet-4-6",
    "llama":  "together_ai/meta-llama/Llama-3.3-70B-Instruct-Turbo",
}

# Utility model for confidence tagging + auto-grading (cheap, capable).
# Using a model OUTSIDE the studied trio for grading avoids the awkwardness of
# a studied model grading itself. Change if you prefer.
UTILITY_MODEL = "gpt-4o-mini"

# --- Generation settings: MATCHED TO ORIGINAL PHASE 2 (verified from
# phase2_multimodel_propagation.py: verify calls used temp=0.7, max_tokens=20) ---
GENERATION_SETTINGS = {
    "temperature": 0.7,
    "max_tokens": 200,
}

# Harvesting uses longer outputs (free-form answers, not verdicts):
HARVEST_SETTINGS = {
    "temperature": 0.7,
    "max_tokens": 512,
}

# --- Paths ---------------------------------------------------------------
DATA = "data"
POOLS = f"{DATA}/pools"
ERRORS = f"{DATA}/errors"
TRIALS = f"{DATA}/trials"
GRADED = f"{DATA}/graded"
RESULTS = f"{DATA}/results"

# --- Run parameters ------------------------------------------------------
HARVEST_CONCURRENCY = 8      # parallel API calls; lower if you hit rate limits
TRIAL_CONCURRENCY = 6
RETRY_ATTEMPTS = 3
RETRY_WAIT_S = 5
