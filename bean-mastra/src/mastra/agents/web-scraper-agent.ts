import { openai } from "@ai-sdk/openai";
import { Agent } from "@mastra/core/agent";
import { Memory } from "@mastra/memory";
import { LibSQLStore } from "@mastra/libsql";
import { mcp } from "../mcp";
import { deepseek } from "@ai-sdk/deepseek";

export const webScraperAgent = new Agent({
  name: "Web Scraper Agent",
  instructions: `
You are a Web Scraper Agent. Your role is to collect relevant information from the web based on the tasks assigned by the Supervisor Agent.
`,
  model: deepseek("deepseek-chat"),
  tools: await mcp.getTools(),
  memory: new Memory({
    storage: new LibSQLStore({
      url: "file:../mastra.db", // path is relative to the .mastra/output directory
    }),
  }),
});
