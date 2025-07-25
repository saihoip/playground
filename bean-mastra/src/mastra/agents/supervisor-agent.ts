import { Agent } from "@mastra/core/agent";
import { Memory } from "@mastra/memory";
import { LibSQLStore } from "@mastra/libsql";

import { deepseek } from "../../models";

const instructions = `
You are the Supervisor Agent. Your role is to review the "To-Do" list stored in working memory and determine which specialized agent should handle the next pending task.

Available agents:
- web-scrapper-agent: Responsible for collecting relevant information from the web.
- reporting-agent: Generates summaries or reports based on the collected information.

Your output must follow this format:
{
  "nextAgent": "<web-scrapper-agent|reporting-agent>",
  "task": "<task description>"
}

Select only one agent based on the nature of the next uncompleted task.
`;

const memory = new Memory({
  storage: new LibSQLStore({
    url: "file:../../memory.db", // path is relative to the .mastra/output directory
  }),
});

export const supervisorAgent = new Agent({
  name: "Supervisor Agent",
  instructions,
  model: deepseek("deepseek-chat"),
  memory,
});
