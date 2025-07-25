import { createStep, createWorkflow } from "@mastra/core/workflows";
import { z } from "zod";
import { supervisorAgent } from "../agents/supervisor-agent";

const writePlan = createStep({
  id: "write-plan",
  description:
    "Breaks down the classified task into structured, actionable steps for downstream agents.",
  inputSchema: z.object({
    taskType: z.enum(["general", "research"]),
    query: z.string(),
  }),
  outputSchema: z.object({
    result: z.string(),
  }),
  execute: async (context) => {
    const { inputData, mastra } = context;
    const { query } = inputData;

    const plannerAgent = mastra.getAgent("plannerAgent");

    const { text } = await plannerAgent.generate([
      { role: "user", content: query },
    ]);

    console.log("Planner Response:", text);

    return {
      result: text,
    };
  },
});

export const researchWorkflow = createWorkflow({
  id: "research-workflow",
  description:
    "A multi-agent workflow designed to perform query-driven research.",
  inputSchema: z.object({
    query: z.string(),
  }),
  outputSchema: z.object({
    result: z.string(),
  }),
})
  .then(writePlan)
  .then(
    createStep({
      id: "supervisor-agent-step",
      description: "Executes the supervisor agent for additional processing.",
      inputSchema: z.object({
        result: z.string(),
      }),
      outputSchema: z.object({
        nextAgent: z.enum(["web-scraper-agent", "reporting-agent"]),
        task: z.string(),
      }),
      execute: async (context) => {
        const { inputData, mastra } = context;
        const supervisorAgent = mastra.getAgent("supervisorAgent");

        const { text } = await supervisorAgent.generate([
          { role: "user", content: inputData.result },
        ]);

        let cleaned = text.replace(/^```json\s*/, "").replace(/```$/, "");

        const nextAgent = JSON.parse(cleaned);

        console.log("Supervisor Agent Response:", text);

        return nextAgent;
      },
    })
  )
  .then(
    createStep({
      id: "scrapWebsites",
      description:
        "Collects relevant information from the web based on the task assigned by the Supervisor Agent.",
      inputSchema: z.object({
        nextAgent: z.enum(["web-scraper-agent", "reporting-agent"]),
        task: z.string(),
      }),
      outputSchema: z.object({
        result: z.string(),
      }),
      execute: async (context) => {
        const { inputData, mastra } = context;
        const webScraperAgent = mastra.getAgent("webScraperAgent");

        const response = await webScraperAgent.generate([
          { role: "user", content: inputData.task },
        ]);

        console.log("Web Scraper Agent Response:", response);

        return {
          result: response.text,
        };
      },
    })
  )
  .commit();
