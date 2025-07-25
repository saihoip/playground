import { LibSQLStore } from "@mastra/libsql";
import { Memory } from "@mastra/memory";

const template = `
# Todo list

Title: <Concise title of the plan>

- [ ] <Step 1>
- [ ] <Step 2>
- [ ] ...
`;

export const memory = new Memory({
  storage: new LibSQLStore({
    url: "file:../../memory.db", // path is relative to the .mastra/output directory
  }),
  options: {
    workingMemory: {
      enabled: true,
      template,
    },
  },
});
