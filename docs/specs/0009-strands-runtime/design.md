# Design: Strands runtime

Add an isolated runtime module under goldcoast/agents; do not replace the legacy Gemini client. Use strands.Agent and strands.models.gemini.GeminiModel, with the model ID supplied by configuration. Use explicitly supplied tools and structured output.

Runtime inputs include the recording directory, provider model or replay directory, an execution budget shared by cooperating agents, and an optional event callback. Each invocation has a stable name and ordinal. Persist a request digest covering agent name, instructions, JSON input, tool names, and response schema. Replay checks this digest to prevent silently answering a different request with an old response.

Persist invocation JSON atomically. Lifecycle hooks enforce model/tool limits, cancellation, and recording; capture model requests/results at the provider boundary if hooks omit structured-output calls. Exceptions are recorded and propagated. Disable automatic provider retries so every paid attempt is accounted for explicitly. Never persist keys or authorization headers.

Tests use a deterministic Strands Model implementation that emits a tool-use turn and a structured final response. Run the actual Agent loop. Test successful typed output, tool execution, budget exhaustion, cancellation, failed output, replay request mismatch, and zero-network replay. Existing tests remain regression coverage.

The runtime will later receive tenant-aware authorization and durable usage reservation callbacks from spec 0010. Until then, callers supply only application-owned tools.
