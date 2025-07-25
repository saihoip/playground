import { createStep, createWorkflow } from "@mastra/core/workflows";
import { z } from "zod";

const classifyTask = createStep({
  id: "classify-task",
  description: "Analyze the user query to determine the nature of the task.",
  inputSchema: z.object({
    query: z.string(),
  }),
  outputSchema: z.object({
    taskType: z.enum(["general", "research"]),
    query: z.string(),
  }),
  execute: async (context) => {
    const { inputData, mastra } = context;
    const { query } = inputData;

    const taskClassifierAgent = mastra.getAgent("taskClassifierAgent");

    const { text } = await taskClassifierAgent.generate([
      { role: "user", content: query },
    ]);

    console.log("Classify result", text);
    let cleaned = text.replace(/^```json\s*/, "").replace(/```$/, "");

    const taskType = JSON.parse(cleaned);

    return {
      taskType: taskType.taskType,
      query,
    };
  },
});

const handleGeneralEnquire = createStep({
  id: "handle-general-enquire",
  description: "Respond to simple or general-purpose queries.",
  inputSchema: z.object({
    taskType: z.enum(["general", "research"]),
    query: z.string(),
  }),
  outputSchema: z.object({
    answer: z.string(),
  }),
  execute: async (context) => {
    const { inputData, mastra } = context;
    const { query } = inputData;

    const generalAgent = mastra.getAgent("generalAgent");

    const { text } = await generalAgent.generate([
      { role: "user", content: query },
    ]);

    console.log("General agent response", text);

    return {
      answer: text,
    };
  },
});

export const doResearch = createStep({
  id: "do-research",
  description: "Perform research based on the plan created.",
  inputSchema: z.object({
    query: z.string(),
    taskType: z.enum(["general", "research"]),
  }),
  outputSchema: z.object({
    result: z.string(),
  }),
  execute: async (context) => {
    const { mastra } = context;

    const researchWorkflow = mastra.getWorkflow("researchWorkflow");

    const { text } = await researchWorkflow.execute(context);

    return {
      result: text,
    };
  },
});

export const agenticWorkflow = createWorkflow({
  id: "agentic-workflow",
  description:
    "A workflow that integrates multiple agents to handle complex tasks.",
  inputSchema: z.object({
    query: z.string(),
  }),
  outputSchema: z.object({
    taskType: z.enum(["general", "research"]),
    query: z.string(),
  }),
})
  .then(classifyTask)
  .branch([
    [async ({ inputData }) => inputData.taskType === "research", doResearch],
    [
      async ({ inputData }) => inputData.taskType === "general",
      handleGeneralEnquire,
    ],
  ])
  .commit();
