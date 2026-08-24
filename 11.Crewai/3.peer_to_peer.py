from crewai import Agent, Task, Crew, Process
from crewai_tools import SerperDevTool
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
search_tool = SerperDevTool()

# Peer-to-Peer (allow_delegation=True on workers)
# Agents can talk to each other during a task. If an agent
# needs help or information, it can call another agent directly
# without a manager being involved.

# Sequential (default):
# Agents work in isolation, one after another.
# Each agent completes its task and passes output to the next.
# No cross-talk between agents.

# You must hint delegation in backstory and description and set
# allow_delegation=True for the agent to be able to delegate
# tasks to other agents.

# ------------------------------------------------
# AGENTS
# ------------------------------------------------

researcher = Agent(
    role="Research Analyst",
    goal="Find accurate information on the given topic and assist other agents when asked",
    backstory=(
        "You are a thorough researcher who gathers facts and data. "
        "When other agents need more information mid-task, you help them immediately."
    ),
    llm=llm,
    tools=[search_tool],
    allow_delegation=True,   # can ask others AND be asked by others
    verbose=True
)

writer = Agent(
    role="Content Writer",
    goal="Write a blog post and consult the researcher if you need more information",
    backstory=(
        "You write content based on research. If you realize you are missing "
        "facts or need clarification while writing, you directly ask the "
        "Research Analyst for help before continuing."
    ),
    llm=llm,
    tools=[],
    allow_delegation=True,   # can reach out to researcher mid-task
    verbose=True
)

editor = Agent(
    role="Editor",
    goal="Polish the blog post and consult the writer if any section needs rework",
    backstory=(
        "You review and improve content. If you find a section is too thin "
        "or unclear, you can ask the Writer to improve it before finalizing."
    ),
    llm=llm,
    tools=[],
    allow_delegation=True,   # can ask writer to fix things
    verbose=True
)

# ------------------------------------------------
# TASKS
# ------------------------------------------------

research_task = Task(
    description=(
        "Search the web and research 'Top AI tools for developers in 2025'. "
        "Find at least 5 tools with their key features and use cases."
    ),
    expected_output="A list of 5 AI tools with name, features, and use case.",
    agent=researcher
)

writing_task = Task(
    description=(
        "Write a 400-word blog post about the top AI tools for developers. "
        "If you feel you need more details on any tool while writing, "
        "ask the Research Analyst directly for more information."
    ),
    expected_output="A 400-word blog post with intro, tools list, and conclusion.",
    agent=writer,
    context=[research_task]
)

editing_task = Task(
    description=(
        "Review and polish the blog post for grammar, clarity, and depth. "
        "If any section feels underdeveloped, ask the Content Writer "
        "to expand it before you finalize."
    ),
    expected_output="A final publication-ready blog post.",
    agent=editor,
    context=[writing_task]
)

# ------------------------------------------------
# CREW
# ------------------------------------------------

crew = Crew(
    agents=[researcher, writer, editor],
    tasks=[research_task, writing_task, editing_task],
    process=Process.sequential,  # still sequential!
    verbose=True
)

result = crew.kickoff()

print(result)