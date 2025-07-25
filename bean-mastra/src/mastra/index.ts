import { Mastra } from "@mastra/core/mastra";
import { LibSQLStore } from "@mastra/libsql";
import { PinoLogger } from "@mastra/loggers";
import { plannerAgent } from "./agents/planner-agent";

import { generalAgent } from "./agents/general-agent";
import { supervisorAgent } from "./agents/supervisor-agent";
import { taskClassifierAgent } from "./agents/task-classifier-agent";
import { weatherAgent } from "./agents/weather-agent";
import { agenticWorkflow } from "./workflows/agentic-workflow";
import { researchWorkflow } from "./workflows/research-workflow";
import { weatherWorkflow } from "./workflows/weather-workflow";
import { webScraperAgent } from "./agents/web-scraper-agent";

export const mastra = new Mastra({
  workflows: { weatherWorkflow, researchWorkflow, agenticWorkflow },
  agents: {
    weatherAgent,
    plannerAgent,
    supervisorAgent,
    taskClassifierAgent,
    generalAgent,
    webScraperAgent,
  },
  storage: new LibSQLStore({
    // stores telemetry, evals, ... into memory storage, if it needs to persist, change to file:../mastra.db
    url: ":memory:",
  }),
  logger: new PinoLogger({
    name: "Mastra",
    level: "info",
  }),
});
