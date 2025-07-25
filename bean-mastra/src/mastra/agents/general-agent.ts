import { Agent } from "@mastra/core/agent";
import { Memory } from "@mastra/memory";
import { LibSQLStore } from "@mastra/libsql";

import { deepseek } from "../../models";

const instructions = `
You are a helpful assitant.
`;

const memory = new Memory({
  storage: new LibSQLStore({
    url: "file:../../memory.db", // path is relative to the .mastra/output directory
  }),
});

export const generalAgent = new Agent({
  name: "General Agent",
  instructions,
  model: deepseek("deepseek-chat"),
  memory,
});
