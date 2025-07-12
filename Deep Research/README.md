This code sample is based on the [Deep Research tool](https://learn.microsoft.com/en-us/azure/ai-foundry/agents/how-to/tools/deep-research) in the [Azure AI Foundry Agent Service](https://learn.microsoft.com/en-us/azure/ai-foundry/agents/overview). The Deep Research capability is a specialized AI capability designed to perform in-depth, multi-step research using data from the public web.

The samples in the online documentation and here use the [Azure AI Foundry Agents SDK's Python client library](https://learn.microsoft.com/en-us/python/api/overview/azure/ai-projects-readme?view=azure-python-preview).

## Get started
1. Start with the [deep research tool overview](https://learn.microsoft.com/en-us/azure/ai-foundry/agents/how-to/tools/deep-research) and set up steps. 
2. Then use the [deep research quickstart Python SDK sample](https://learn.microsoft.com/en-us/azure/ai-foundry/agents/how-to/tools/deep-research-samples) to get your first code sample running.

## Enhanced code sample
The code sample in this folder improves on the quickstart sample with these enhancements:

1. **Research progress**: Just the research progress with the deep research model's thinking progression and `Grounding with Bing Search` citations is saved to a `research_progress.txt` file, not the rest of the agent run that includes the final research report and other logs. Enhancements include:
   - Each "thnking" log is demarcated by the "Agent>" prefix.
   - Each entry includes the "Reasoning" aka the thinking summary, and the related "Citation" URL as applicable.

1. **Research report**: The final research report is saved to a `research_report.md` markdown file with these formatting enhancements:
   - The inline citations are cleaner, superscript indices into the list of citations at the end of the report.
   - The citations list is now a numbered list ordered by the indices inline.

Happy deep coding...
