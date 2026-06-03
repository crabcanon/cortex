"use client";

import { Tab, Tabs } from "fumadocs-ui/components/tabs";
import { DynamicCodeBlock } from "fumadocs-ui/components/dynamic-codeblock";

type Example = {
  python: string;
  javascript: string;
  java: string;
};

type ApiExampleKey =
  | "auth-token"
  | "parse-engines"
  | "parse-sync"
  | "parse-job"
  | "parse-job-result"
  | "storage-upload"
  | "storage-upload-session"
  | "storage-complete-upload"
  | "storage-object"
  | "storage-download-url"
  | "knowledge-dataset"
  | "knowledge-add-job"
  | "knowledge-cognify-job"
  | "knowledge-search"
  | "eval-engines-metrics"
  | "eval-sync"
  | "eval-job"
  | "eval-perf-job"
  | "eval-job-result"
  | "synthesis-engines"
  | "synthesis-structured-sync"
  | "synthesis-qa-sync"
  | "synthesis-job"
  | "synthesis-job-result"
  | "job-status"
  | "job-events"
  | "job-cancel"
  | "tensorzero-synthesis-job";

type Props = {
  example: ApiExampleKey;
};

const PY_BASE = `import os
import requests

BASE_URL = os.getenv("CORTEX_URL", "http://127.0.0.1:8080")
TOKEN = os.getenv("CORTEX_TOKEN", "replace_with_token")

def auth_headers():
    return {"Authorization": f"Bearer {TOKEN}"}`;

const JS_BASE = `const BASE_URL = process.env.CORTEX_URL ?? "http://127.0.0.1:8080";
const TOKEN = process.env.CORTEX_TOKEN ?? "replace_with_token";

const authHeaders = {
  Authorization: \`Bearer \${TOKEN}\`,
};`;

const JAVA_BASE = `import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;

public class CortexExample {
  static final String BASE_URL = System.getenv().getOrDefault("CORTEX_URL", "http://127.0.0.1:8080");
  static final String TOKEN = System.getenv().getOrDefault("CORTEX_TOKEN", "replace_with_token");
  static final HttpClient HTTP = HttpClient.newHttpClient();

  static void print(HttpResponse<String> response) {
    System.out.println(response.statusCode());
    System.out.println(response.body());
  }`;

const examples: Record<ApiExampleKey, Example> = {
  "auth-token": {
    python: `import requests

base_url = "http://127.0.0.1:8080"
payload = {
    "subject": "cortex-quickstart",
    "tenant_id": "tenant_demo",
    "roles": ["tenant_admin"],
    "expires_in": 3600,
}

response = requests.post(f"{base_url}/v1/dev/auth/token", json=payload)
response.raise_for_status()
token = response.json()["access_token"]
print(token)`,
    javascript: `const baseUrl = "http://127.0.0.1:8080";

const response = await fetch(\`\${baseUrl}/v1/dev/auth/token\`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    subject: "cortex-quickstart",
    tenant_id: "tenant_demo",
    roles: ["tenant_admin"],
    expires_in: 3600,
  }),
});

if (!response.ok) throw new Error(await response.text());
const { access_token: token } = await response.json();
console.log(token);`,
    java: `${JAVA_BASE}

  public static void main(String[] args) throws Exception {
    String json = """
      {
        "subject": "cortex-quickstart",
        "tenant_id": "tenant_demo",
        "roles": ["tenant_admin"],
        "expires_in": 3600
      }
      """;

    HttpRequest request = HttpRequest.newBuilder()
      .uri(URI.create(BASE_URL + "/v1/dev/auth/token"))
      .header("Content-Type", "application/json")
      .POST(HttpRequest.BodyPublishers.ofString(json))
      .build();

    print(HTTP.send(request, HttpResponse.BodyHandlers.ofString()));
  }
}`,
  },
  "parse-engines": getExample("GET", "/v1/parse/engines"),
  "parse-sync": getExample(
    "POST",
    "/v1/parse/sync",
    {
      sources: ["https://docs.cognee.ai/core-concepts/overview"],
      engine_id: "auto",
    },
    "print(data['results'][0]['document']['markdown'][:800]);",
    "console.log(data.results[0].document.markdown.slice(0, 800));",
  ),
  "parse-job": getExample("POST", "/v1/parse/jobs", {
    sources: ["https://docs.crawl4ai.com/advanced/advanced-features/"],
    engine_id: "crawl4ai",
    priority: 5,
  }),
  "parse-job-result": getExample("GET", "/v1/parse/jobs/job_xxx/result"),
  "storage-upload": {
    python: `${PY_BASE}

metadata = {"source": "storage-quickstart", "document_type": "guide"}
access_policy = {"access_level": "tenant_shared"}

with open("cortex-storage-quickstart.md", "w", encoding="utf-8") as f:
    f.write("# Cortex Storage\\n\\nThis file was uploaded through Cortex.")

with open("cortex-storage-quickstart.md", "rb") as f:
    response = requests.post(
        f"{BASE_URL}/v1/storage/files",
        headers=auth_headers(),
        files={"file": ("cortex-storage-quickstart.md", f, "text/markdown")},
        data={
            "metadata_json": __import__("json").dumps(metadata),
            "access_policy_json": __import__("json").dumps(access_policy),
            "tags": "quickstart,docs",
        },
    )

response.raise_for_status()
print(response.json())`,
    javascript: `${JS_BASE}

const form = new FormData();
form.append(
  "file",
  new Blob(["# Cortex Storage\\n\\nThis file was uploaded through Cortex."], {
    type: "text/markdown",
  }),
  "cortex-storage-quickstart.md",
);
form.append("metadata_json", JSON.stringify({ source: "storage-quickstart", document_type: "guide" }));
form.append("access_policy_json", JSON.stringify({ access_level: "tenant_shared" }));
form.append("tags", "quickstart,docs");

const response = await fetch(\`\${BASE_URL}/v1/storage/files\`, {
  method: "POST",
  headers: authHeaders,
  body: form,
});

if (!response.ok) throw new Error(await response.text());
console.log(await response.json());`,
    java: `${JAVA_BASE}

  public static void main(String[] args) throws Exception {
    String boundary = "----CortexBoundary" + System.currentTimeMillis();
    String body = ""
      + "--" + boundary + "\\r\\n"
      + "Content-Disposition: form-data; name=\\"file\\"; filename=\\"cortex-storage-quickstart.md\\"\\r\\n"
      + "Content-Type: text/markdown\\r\\n\\r\\n"
      + "# Cortex Storage\\n\\nThis file was uploaded through Cortex.\\r\\n"
      + "--" + boundary + "\\r\\n"
      + "Content-Disposition: form-data; name=\\"metadata_json\\"\\r\\n\\r\\n"
      + "{\\"source\\":\\"storage-quickstart\\",\\"document_type\\":\\"guide\\"}\\r\\n"
      + "--" + boundary + "\\r\\n"
      + "Content-Disposition: form-data; name=\\"access_policy_json\\"\\r\\n\\r\\n"
      + "{\\"access_level\\":\\"tenant_shared\\"}\\r\\n"
      + "--" + boundary + "\\r\\n"
      + "Content-Disposition: form-data; name=\\"tags\\"\\r\\n\\r\\n"
      + "quickstart,docs\\r\\n"
      + "--" + boundary + "--\\r\\n";

    HttpRequest request = HttpRequest.newBuilder()
      .uri(URI.create(BASE_URL + "/v1/storage/files"))
      .header("Authorization", "Bearer " + TOKEN)
      .header("Content-Type", "multipart/form-data; boundary=" + boundary)
      .POST(HttpRequest.BodyPublishers.ofString(body))
      .build();

    print(HTTP.send(request, HttpResponse.BodyHandlers.ofString()));
  }
}`,
  },
  "storage-upload-session": getExample("POST", "/v1/storage/uploads", {
    filename: "quarterly-report.pdf",
    size_bytes: 67108864,
    metadata: {
      source: "finance-portal",
      department: "fpna",
    },
    tags: ["finance", "quarterly"],
  }),
  "storage-complete-upload": getExample("POST", "/v1/storage/uploads/upload_xxx/complete", {
    parts: [
      { part_number: 1, etag: "\"part-1-etag\"" },
      { part_number: 2, etag: "\"part-2-etag\"" },
    ],
    checksum_sha256: "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  }),
  "storage-object": getExample("GET", "/v1/storage/objects/obj_xxx"),
  "storage-download-url": getExample("GET", "/v1/storage/objects/obj_xxx/download-url?ttl_seconds=900"),
  "knowledge-dataset": getExample("POST", "/v1/knowledge/datasets", {
    dataset_key: "quickstart_knowledge_demo",
    display_name: "Quickstart Knowledge Demo",
    description: "Small Cortex Knowledge dataset",
    tags: ["quickstart", "knowledge"],
    retention_class: "temporary",
    access_policy: { access_level: "tenant_shared" },
  }),
  "knowledge-add-job": getExample("POST", "/v1/knowledge/add/jobs", {
    dataset_key: "quickstart_knowledge_demo",
    inputs: [
      {
        input_type: "text",
        text: "# Cortex APIs\nCortex provides Parse, Storage, Knowledge, Evaluation, and Synthesis APIs.",
        label: "Cortex API note",
        node_set: ["quickstart", "docs"],
        metadata: { source: "manual", document_type: "note" },
      },
    ],
    options: {
      normalize_text: true,
      structured_ingest: true,
      incremental: true,
      persist_source_copy: false,
    },
  }),
  "knowledge-cognify-job": getExample("POST", "/v1/knowledge/cognify/jobs", {
    dataset_key: "quickstart_knowledge_demo",
    incremental_loading: true,
    graph_prompt_profile: "simple",
    chunking: {
      enabled: true,
      strategy: "semantic",
      target_tokens: 384,
      overlap_tokens: 48,
      max_chunks: 64,
    },
  }),
  "knowledge-search": getExample("POST", "/v1/knowledge/search", {
    query_text: "What APIs does Cortex expose?",
    dataset_keys: ["quickstart_knowledge_demo"],
    search_type: "GRAPH_COMPLETION",
    top_k: 5,
    only_context: false,
    include_provenance: true,
    include_graph_paths: true,
    timeout_seconds: 30,
  }),
  "eval-engines-metrics": {
    python: `${PY_BASE}

for path in ["/v1/eval/engines", "/v1/eval/metrics"]:
    response = requests.get(f"{BASE_URL}{path}", headers=auth_headers())
    response.raise_for_status()
    print(path, response.json())`,
    javascript: `${JS_BASE}

for (const path of ["/v1/eval/engines", "/v1/eval/metrics"]) {
  const response = await fetch(\`\${BASE_URL}\${path}\`, { headers: authHeaders });
  if (!response.ok) throw new Error(await response.text());
  console.log(path, await response.json());
}`,
    java: `${JAVA_BASE}

  public static void main(String[] args) throws Exception {
    for (String path : new String[] {"/v1/eval/engines", "/v1/eval/metrics"}) {
      HttpRequest request = HttpRequest.newBuilder()
        .uri(URI.create(BASE_URL + path))
        .header("Authorization", "Bearer " + TOKEN)
        .GET()
        .build();
      print(HTTP.send(request, HttpResponse.BodyHandlers.ofString()));
    }
  }
}`,
  },
  "eval-sync": getExample("POST", "/v1/eval/sync", evalPayload()),
  "eval-job": getExample("POST", "/v1/eval/jobs", evalPayload()),
  "eval-perf-job": getExample("POST", "/v1/eval/jobs", {
    name: "swagger-perf-job",
    eval_type: "perf",
    engine_id: "evalscope",
    input: { type: "builtin_dataset", builtin_dataset_key: "longalpaca" },
    target: {
      type: "api",
      protocol: "openai_compatible",
      endpoint_url: "https://openrouter.ai/api/v1/chat/completions",
      api_key: "sk-xxx",
      model_ref: "deepseek/deepseek-v4-flash",
      timeout_seconds: 60,
    },
    engine_options: {
      parallel: [1, 2],
      number: [2, 2],
      stream: false,
      max_tokens: 2048,
      min_tokens: 1024,
      max_prompt_length: 2048,
      min_prompt_length: 1024,
    },
  }),
  "eval-job-result": getExample("GET", "/v1/eval/jobs/job_xxx/result"),
  "synthesis-engines": getExample("GET", "/v1/synthesis/engines"),
  "synthesis-structured-sync": getExample("POST", "/v1/synthesis/sync", {
    name: "quickstart-sdv-customers",
    synthesis_type: "structured_single_table",
    engine_id: "sdv",
    source: {
      type: "inline_records",
      inline_records: [
        { customer_id: "c1", tier: "gold", monthly_spend: 1200 },
        { customer_id: "c2", tier: "silver", monthly_spend: 300 },
      ],
      options: { table_name: "customers" },
    },
    config: { sample_count: 5, anonymize_pii: true },
    output: { output_format: "json", include_preview: true },
  }),
  "synthesis-qa-sync": getExample("POST", "/v1/synthesis/sync", qaPayload()),
  "synthesis-job": getExample("POST", "/v1/synthesis/jobs", qaPayload()),
  "synthesis-job-result": getExample("GET", "/v1/synthesis/jobs/job_xxx/result"),
  "job-status": getExample("GET", "/v1/jobs/job_xxx"),
  "job-events": getExample("GET", "/v1/jobs/job_xxx/events?limit=100"),
  "job-cancel": getExample("POST", "/v1/jobs/job_xxx/cancel", {}),
  "tensorzero-synthesis-job": getExample("POST", "/v1/synthesis/jobs", {
    name: "tensorzero-rag-goldens",
    synthesis_type: "qa_pairs",
    engine_id: "deepeval",
    source: {
      type: "documents",
      documents: ["Paste a representative parsed Markdown excerpt from report artifacts."],
    },
    config: { sample_count: 10, include_expected_output: true },
    output: { output_format: "jsonl", include_preview: true },
  }),
};

function evalPayload() {
  return {
    name: "quickstart-rag-eval",
    eval_type: "rag",
    engine_id: "deepeval",
    input: {
      type: "inline_test_cases",
      test_cases: [
        {
          user_input: "What does Cortex Parse do?",
          actual_output: "Cortex Parse converts URLs and files into normalized Markdown.",
          expected_output: "Parse should mention URLs, files, and Markdown.",
          retrieval_contexts: [
            "Cortex Parse accepts URLs and files and returns normalized Markdown with metadata.",
          ],
          metadata: { case_id: "rag-001" },
        },
      ],
    },
    target: { type: "existing_outputs" },
    metrics: [
      { metric_key: "rag.answer_relevance", threshold: 0.65 },
      { metric_key: "rag.faithfulness", threshold: 0.65 },
      { metric_key: "rag.contextual_relevance", threshold: 0.6 },
    ],
    output: { persist_report_object: true, include_sample_results: true },
  };
}

function qaPayload() {
  return {
    name: "quickstart-qa-preview",
    synthesis_type: "qa_pairs",
    engine_id: "deepeval",
    source: {
      type: "documents",
      documents: ["Cortex Parse turns URLs and storage objects into LLM-ready Markdown."],
    },
    config: {
      sample_count: 2,
      max_contexts_per_case: 1,
      include_expected_output: true,
    },
    output: { output_format: "json", include_preview: true },
  };
}

function getExample(
  method: "GET" | "POST",
  path: string,
  body?: unknown,
  pythonAfter = "print(data)",
  jsAfter = "console.log(data);",
): Example {
  const payload = body ? JSON.stringify(body, null, 2) : undefined;
  const pyPayload = payload ? payload.replace(/true/g, "True").replace(/false/g, "False").replace(/null/g, "None") : "";
  const javaPayload = payload ? payload.replace(/\\/g, "\\\\").replace(/"/g, '\\"') : "";

  return {
    python:
      method === "GET"
        ? `${PY_BASE}

response = requests.get(f"{BASE_URL}${path}", headers=auth_headers())
response.raise_for_status()
data = response.json()
${pythonAfter}`
        : `${PY_BASE}

payload = ${pyPayload}

response = requests.post(
    f"{BASE_URL}${path}",
    headers={**auth_headers(), "Content-Type": "application/json"},
    json=payload,
)
response.raise_for_status()
data = response.json()
${pythonAfter}`,
    javascript:
      method === "GET"
        ? `${JS_BASE}

const response = await fetch(\`\${BASE_URL}${path}\`, {
  headers: authHeaders,
});

if (!response.ok) throw new Error(await response.text());
const data = await response.json();
${jsAfter}`
        : `${JS_BASE}

const payload = ${payload};

const response = await fetch(\`\${BASE_URL}${path}\`, {
  method: "POST",
  headers: { ...authHeaders, "Content-Type": "application/json" },
  body: JSON.stringify(payload),
});

if (!response.ok) throw new Error(await response.text());
const data = await response.json();
${jsAfter}`,
    java:
      method === "GET"
        ? `${JAVA_BASE}

  public static void main(String[] args) throws Exception {
    HttpRequest request = HttpRequest.newBuilder()
      .uri(URI.create(BASE_URL + "${path}"))
      .header("Authorization", "Bearer " + TOKEN)
      .GET()
      .build();

    print(HTTP.send(request, HttpResponse.BodyHandlers.ofString()));
  }
}`
        : `${JAVA_BASE}

  public static void main(String[] args) throws Exception {
    String json = """
${javaPayload
  .split("\n")
  .map((line) => `      ${line}`)
  .join("\n")}
      """;

    HttpRequest request = HttpRequest.newBuilder()
      .uri(URI.create(BASE_URL + "${path}"))
      .header("Authorization", "Bearer " + TOKEN)
      .header("Content-Type", "application/json")
      .POST(HttpRequest.BodyPublishers.ofString(json))
      .build();

    print(HTTP.send(request, HttpResponse.BodyHandlers.ofString()));
  }
}`,
  };
}

export default function ApiExampleTabs({ example }: Props) {
  const selected = examples[example];

  return (
    <Tabs items={["Python", "JavaScript", "Java"]}>
      <Tab value="Python">
        <DynamicCodeBlock lang="python" code={selected.python} />
      </Tab>
      <Tab value="JavaScript">
        <DynamicCodeBlock lang="javascript" code={selected.javascript} />
      </Tab>
      <Tab value="Java">
        <DynamicCodeBlock lang="java" code={selected.java} />
      </Tab>
    </Tabs>
  );
}
