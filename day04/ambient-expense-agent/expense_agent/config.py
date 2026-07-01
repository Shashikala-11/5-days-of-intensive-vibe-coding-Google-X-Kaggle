# ==============================================================================
# Ambient Expense Agent Configuration
# ==============================================================================
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
# Threshold in USD above which manual approval and LLM risk assessment is required
THRESHOLD_USD = 100.0

# Gemini model used for assessing expense risk factors
LLM_MODEL = "gemini-3.1-flash-lite"
otel_to_cloud = False
