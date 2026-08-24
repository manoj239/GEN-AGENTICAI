from crewai import Agent, Task, Crew, Process
from crewai_tools import SerperDevTool
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()

# .env needs:
# GOOGLE_API_KEY=your_google_key
# SERPER_API_KEY=your_serper_key   <- free at serper.dev

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

# --- TOOL ------------------------------------------------

search_tool = SerperDevTool()  # automatically reads SERPER_API_KEY from env

# --- AGENTS ----------------------------------------------

researcher = Agent(
    role="Research Analyst",
    goal="Find current and accurate information on the given topic from the web",
    backstory=(
        "You are a thorough researcher who uses web search to find "
        "up-to-date information. You always verify facts before reporting them."
    ),
    llm=llm,
    tools=[search_tool],  # attach tool to agent
    verbose=True
)

writer = Agent(
    role="Content Writer",
    goal="Write a clear and engaging blog post based on research findings",
    backstory=(
        "You are a skilled writer who turns research into readable content. "
        "You do not search the web - you rely on the researcher's output."
    ),
    llm=llm,
    tools=[],  # no tools needed for writer
    verbose=True
)

# --- TASKS ----------------------------------------------

research_task = Task(
    description=(
        "Search the web and find the latest news and developments about "
        "'Gemini 2.5 Flash by Google'. Find: release date, key features, "
        "performance benchmarks, and how it compares to other models."
    ),
    expected_output=(
        "A detailed summary with: key features, release info, "
        "benchmark results, and comparisons. Include specific facts and numbers."
    ),
    agent=researcher
)

writing_task = Task(
    description=(
        "Using the research provided, write a 400-word blog post titled "
        "'Why Gemini 2.5 Flash is a Game Changer for Developers'."
    ),
    expected_output=(
        "A 400-word blog post with intro, 3 key points, and a conclusion."
    ),
    agent=writer,
    context=[research_task]
)

# --- CREW ------------------------------------------------

crew = Crew(
    agents=[researcher, writer],
    tasks=[research_task, writing_task],
    process=Process.sequential,
    verbose=True
)

result = crew.kickoff()

print("\nFinal Output:\n")
print(result)

# from crewai_tools import (
#     SerperDevTool,      # Google Search via Serper API
#     ScrapeWebsiteTool,  # Scrape full content of a URL
#     FileReadTool,       # Read a local file
#     CSVSearchTool,      # Search inside CSV files
# )