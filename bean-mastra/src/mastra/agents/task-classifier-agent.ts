import { Agent } from "@mastra/core/agent";
import { Memory } from "@mastra/memory";
import { LibSQLStore } from "@mastra/libsql";

import { deepseek } from "../../models";

const instructions = `
Your job is to classify the user's request into one of two task types:
- general: A simple, direct request that can be answered immediately.
- research: A complex or open-ended question that may require planning, tool usage, or multiple steps.
Classify the task based only on the user message."

Output format:
{
  "taskType": "<general|research>",
}
`;

const memory = new Memory({
  storage: new LibSQLStore({
    url: "file:../../memory.db", // path is relative to the .mastra/output directory
  }),
});

export const taskClassifierAgent = new Agent({
  name: "Task Classifier Agent",
  instructions,
  model: deepseek("deepseek-chat"),
  memory,
});
