[gateway]
disable_pseudonymous_usage_analytics = true

[models.openai_finance]
routing = ["openai"]

[models.openai_finance.providers.openai]
type = "openai"
api_base = "${OPENAI_BASE_URL}"
api_key_location = "env::OPENAI_API_KEY"
model_name = "${OPENAI_MODEL_ID}"

[models.gemini_finance]
routing = ["gemini_openai_compatible"]

[models.gemini_finance.providers.gemini_openai_compatible]
type = "openai"
api_base = "${GEMINI_BASE_URL}"
api_key_location = "env::GEMINI_API_KEY"
model_name = "${GEMINI_MODEL_ID}"

[models.kimi_finance]
routing = ["kimi_openai_compatible"]

[models.kimi_finance.providers.kimi_openai_compatible]
type = "openai"
api_base = "${KIMI_BASE_URL}"
api_key_location = "env::KIMI_API_KEY"
model_name = "${KIMI_MODEL_ID}"

[models.ollama_finance]
routing = ["ollama_openai_compatible"]

[models.ollama_finance.providers.ollama_openai_compatible]
type = "openai"
api_base = "${OLLAMA_BASE_URL}"
api_key_location = "env::OLLAMA_API_KEY"
model_name = "${OLLAMA_MODEL_ID}"

[functions.cortex_rag_answer]
type = "json"
output_schema = "schemas/rag_answer.schema.json"

[functions.cortex_rag_answer.variants.openai]
type = "chat_completion"
model = "openai_finance"
templates.system.path = "templates/rag_system.minijinja"
temperature = 0.1
max_tokens = 2200
json_mode = "strict"

[functions.cortex_rag_answer.variants.gemini]
type = "chat_completion"
model = "gemini_finance"
templates.system.path = "templates/rag_system.minijinja"
temperature = 0.1
max_tokens = 2200
json_mode = "strict"

[functions.cortex_rag_answer.variants.kimi]
type = "chat_completion"
model = "kimi_finance"
templates.system.path = "templates/rag_system.minijinja"
temperature = 0.1
max_tokens = 2200
json_mode = "strict"

[functions.cortex_rag_answer.variants.ollama]
type = "chat_completion"
model = "ollama_finance"
templates.system.path = "templates/rag_system.minijinja"
temperature = 0.1
max_tokens = 2200
json_mode = "strict"

[functions.cortex_rag_answer.experimentation]
type = "adaptive"
candidate_variants = ["openai", "gemini", "kimi"]
metric = "rag_end_to_end_pass"
update_period_s = 60

[metrics.parse_markdown_quality]
type = "float"
level = "inference"
optimize = "max"

[metrics.rag_context_quality]
type = "float"
level = "inference"
optimize = "max"

[metrics.llm_answer_quality]
type = "float"
level = "inference"
optimize = "max"

[metrics.rag_end_to_end_pass]
type = "boolean"
level = "inference"
optimize = "max"

[object_storage]
type = "disabled"
