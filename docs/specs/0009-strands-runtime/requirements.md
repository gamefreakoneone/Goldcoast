# Requirements: Strands runtime

Integrate the Python Strands Agents SDK with Gemini as the foundation for the approved food-and-drink marketing pivot. Existing Olympics stages and recorded runs must continue to work.

- Add the Gemini SDK extra to project dependencies and install it in the goldcoast environment.
- Provide one reusable runtime accepting a named agent, system instructions, typed input, registered tools, and a Pydantic output type.
- Parse outputs before returning. Record requests, responses, tool activity, model identity, latency, usage, and failures without credentials.
- Enforce shared call limits and cancellation before model/tool execution. Tools must be explicitly registered; no general shell, filesystem, or unrestricted HTTP tools.
- Replay must validate the recorded request and return typed output without constructing a live provider or invoking tools.
- Prove genuine Strands tool execution using an offline deterministic model, not a mocked Agent.
- Preserve existing validation and CLI behavior. Source files contain no added comments.

The remaining approved delivery sequence is 0010 accounts/persistence, 0011 business/brand onboarding, 0012 discovery/knowledge graph, 0013 chief marketing workflow, 0014 creative production, 0015 workspace UI, 0016 adaptation/replay, 0017 hosted deployment, and 0018 submission package. Later specs are created and executed only after this spec completes or is explicitly blocked.
