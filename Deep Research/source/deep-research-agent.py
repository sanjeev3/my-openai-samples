import os, time, re
from typing import Optional
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import DeepResearchTool, MessageRole, ThreadMessage


def convert_citations_to_superscript(markdown_content):
    """
    Convert citation markers in markdown content to HTML superscript format.
    
    This function finds citation patterns like 【78:12†source】 and converts them to 
    HTML superscript tags <sup>12</sup> for better formatting in markdown documents.
    
    Args:
        markdown_content (str): The markdown content containing citation markers
        
    Returns:
        str: The markdown content with citations converted to HTML superscript format"
    """
    # Pattern to match 【number:number†source】
    pattern = r'【\d+:(\d+)†source】'
    
    # Replace with <sup>captured_number</sup>
    def replacement(match):
        citation_number = match.group(1)
        return f'<sup>{citation_number}</sup>'
    
    return re.sub(pattern, replacement, markdown_content)


def fetch_and_print_new_agent_response(
    thread_id: str,
    agents_client: AgentsClient,
    last_message_id: Optional[str] = None,
    progress_filename: str = "research_progress.txt",
) -> Optional[str]:
    """
    Fetch the interim agent responses and citations from a thread and write them to a file.
    
    Args:
        thread_id (str): The ID of the thread to fetch messages from
        agents_client (AgentsClient): The Azure AI agents client instance
        last_message_id (Optional[str], optional): ID of the last processed message 
            to avoid duplicates. Defaults to None.
        progress_filename (str, optional): Name of the file to write progress to. 
            Defaults to "run_progress.txt".
            
    Returns:
        Optional[str]: The ID of the latest message if new content was found, 
            otherwise returns the last_message_id
    """
    response = agents_client.messages.get_last_message_by_role(
        thread_id=thread_id,
        role=MessageRole.AGENT,
    )
    if not response or response.id == last_message_id:
        return last_message_id  # No new content

    # if not a "cot_summary" return
    if not any(t.text.value.startswith("cot_summary:") for t in response.text_messages):
        return last_message_id    

    with open(progress_filename, "a", encoding="utf-8") as fp:
        fp.write("\nAGENT>\n")
        fp.write("\n".join(t.text.value.replace("cot_summary:", "Reasoning:") for t in response.text_messages))
        fp.write("\n")

        for ann in response.url_citation_annotations:
            fp.write(f"Citation: [{ann.url_citation.title}]({ann.url_citation.url})\n")

    return response.id


def create_research_summary(
        message : ThreadMessage,
        filepath: str = "research_report.md"
) -> None:
    """
    Create a formatted research report from an agent's thread message with numbered citations 
    and a references section.
    
    Args:
        message (ThreadMessage): The thread message containing the agent's research response
        filepath (str, optional): Path where the research summary will be saved. 
            Defaults to "research_report.md".
            
    Returns:
        None: This function doesn't return a value, it writes to a file
    """
    if not message:
        print("No message content provided, cannot create research report.")
        return

    with open(filepath, "w", encoding="utf-8") as fp:
        # Write text summary
        text_summary = "\n\n".join([t.text.value.strip() for t in message.text_messages])
        # Convert citations to superscript format
        text_summary = convert_citations_to_superscript(text_summary)
        fp.write(text_summary)

        # Write unique URL citations with numbered bullets, if present
        if message.url_citation_annotations:
            fp.write("\n\n## Citations\n")
            seen_urls = set()
            citation_dict = {}
            
            for ann in message.url_citation_annotations:
                url = ann.url_citation.url
                title = ann.url_citation.title or url
                
                if url not in seen_urls:
                    # Extract citation number from annotation text like "【58:1†...】"
                    citation_number = None
                    if ann.text and ":" in ann.text:
                        match = re.search(r'【\d+:(\d+)', ann.text)
                        if match:
                            citation_number = int(match.group(1))
                    
                    if citation_number is not None:
                        citation_dict[citation_number] = f"[{title}]({url})"
                    else:
                        # Fallback for citations without proper format
                        citation_dict[len(citation_dict) + 1] = f"[{title}]({url})"
                    
                    seen_urls.add(url)
            
            # Write citations in numbered order
            for num in sorted(citation_dict.keys()):
                fp.write(f"{num}. {citation_dict[num]}\n")

    print(f"Research report written to '{filepath}'.")


if __name__ == "__main__":
    project_client = AIProjectClient(
        endpoint=os.environ["PROJECT_ENDPOINT"],
        credential=DefaultAzureCredential(),
    )

    conn_id = project_client.connections.get(name=os.environ["BING_RESOURCE_NAME"]).id

    # Initialize a Deep Research tool with Bing Connection ID and Deep Research model deployment name
    deep_research_tool = DeepResearchTool(
        bing_grounding_connection_id=conn_id,
        deep_research_model=os.environ["DEEP_RESEARCH_MODEL_DEPLOYMENT_NAME"],
    )

    # Create Agent with the Deep Research tool and process Agent run
    with project_client:

        with project_client.agents as agents_client:

            # Create a new agent that has the Deep Research tool attached.
            # NOTE: To add Deep Research to an existing agent, fetch it with `get_agent(agent_id)` and then,
            # update the agent with the Deep Research tool.
            agent = agents_client.create_agent(
                model=os.environ["MODEL_DEPLOYMENT_NAME"],
                name="my-agent",
                instructions="You are a helpful Agent that assists in researching scientific topics.",
                tools=deep_research_tool.definitions,
            )

            # [END create_agent_with_deep_research_tool]
            print(f"Created agent, ID: {agent.id}")

            # Create thread for communication
            thread = agents_client.threads.create()
            print(f"Created thread, ID: {thread.id}")

            # Create message to thread
            message = agents_client.messages.create(
                thread_id=thread.id,
                role="user",
                content=(
                    "Research the current state of studies on orca intelligence and orca language, including what is currently known about orcas' cognitive capabilities and communication systems."
                ),
            )
            print(f"Created message, ID: {message.id}")

            print(f"Start processing the message... this may take a few minutes to finish. Be patient!")
            # Poll the run as long as run status is queued or in progress
            run = agents_client.runs.create(thread_id=thread.id, agent_id=agent.id)
            last_message_id = None
            while run.status in ("queued", "in_progress"):
                time.sleep(1)
                run = agents_client.runs.get(thread_id=thread.id, run_id=run.id)

                last_message_id = fetch_and_print_new_agent_response(
                    thread_id=thread.id,
                    agents_client=agents_client,
                    last_message_id=last_message_id,
                    progress_filename="research_progress.txt",
                )
                print(f"Run status: {run.status}")

            # Once the run is finished, print the final status and ID
            print(f"Run finished with status: {run.status}, ID: {run.id}")

            if run.status == "failed":
                print(f"Run failed: {run.last_error}")

            # Fetch the final message from the agent in the thread and create a research summary
            final_message = agents_client.messages.get_last_message_by_role(
                thread_id=thread.id, role=MessageRole.AGENT
            )
            if final_message:
                create_research_summary(final_message)

            # Clean-up and delete the agent once the run is finished.
            # NOTE: Comment out this line if you plan to reuse the agent later.
            agents_client.delete_agent(agent.id)
            print("Deleted agent")