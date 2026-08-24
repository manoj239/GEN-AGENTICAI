from crewai import Agent, Task, Crew, Process
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

# ------------------------------------------------
# MANAGER AGENT
# ------------------------------------------------

manager = Agent(
    role="Project Manager",
    goal="Ensure the market research report is accurate, complete, and delivered on time",
    backstory=(
        "You are an experienced project manager who oversees research teams. "
        "You know how to delegate effectively, review outputs critically, "
        "and ensure the final deliverable meets the client's expectations. "
        "You do not do the research yourself - you coordinate and validate."
    ),
    llm=llm,
    verbose=True,
    allow_delegation=True  # manager MUST have this True
)

# ------------------------------------------------
# WORKER AGENTS
# ------------------------------------------------

data_analyst = Agent(
    role="Market Data Analyst",
    goal="Find accurate market size, growth rates, and statistics for the given topic",
    backstory=(
        "You are a quantitative analyst with expertise in market sizing, "
        "TAM/SAM/SOM analysis, and industry trend data. "
        "You back every claim with numbers and cite your sources."
    ),
    llm=llm,
    verbose=True,
    allow_delegation=False  # workers do NOT delegate further
)

competitor_analyst = Agent(
    role="Competitor Intelligence Analyst",
    goal="Identify and profile the top competitors in the given market",
    backstory=(
        "You are a competitive intelligence specialist who profiles companies, "
        "identifies their strengths and weaknesses, pricing strategies, "
        "and market positioning. You provide actionable insights."
    ),
    llm=llm,
    verbose=True,
    allow_delegation=False
)

report_writer = Agent(
    role="Business Report Writer",
    goal="Compile research findings into a clear, professional business report",
    backstory=(
        "You are a senior business writer with experience producing executive-level "
        "reports. You structure information logically, write clearly, "
        "and make complex data easy to understand for decision-makers."
    ),
    llm=llm,
    verbose=True,
    allow_delegation=False
)

# ------------------------------------------------
# TASKS
# ------------------------------------------------

market_data_task = Task(
    description=(
        "Research the Electric Vehicle (EV) market. "
        "Find: current global market size, projected growth rate (CAGR), "
        "key regions driving growth, and major market trends for 2025-2030."
    ),
    expected_output=(
        "A structured summary with: market size (USD), CAGR %, "
        "top 3 growth regions, and 4-5 key trends. Include numbers wherever possible."
    ),
    agent=data_analyst
)

competitor_task = Task(
    description=(
        "Identify the top 5 EV manufacturers globally. "
        "For each competitor provide: company name, market share %, "
        "key models, pricing range, and one key strength and one weakness."
    ),
    expected_output=(
        "A table-style summary of 5 competitors with: "
        "name, market share, key models, price range, strength, weakness."
    ),
    agent=competitor_analyst
)

report_task = Task(
    description=(
        "Using the market data and competitor analysis provided, "
        "compile a professional 600-word Market Research Report on the EV industry. "
        "Structure it as: Executive Summary, Market Overview, Competitive Landscape, "
        "Key Opportunities, and Conclusion."
    ),
    expected_output=(
        "A complete 600-word business report with 5 clearly labeled sections. "
        "Professional tone suitable for executive readers."
    ),
    agent=report_writer,
    context=[market_data_task, competitor_task]  # gets both analysts' outputs
)

# ------------------------------------------------
# CREW
# ------------------------------------------------

crew = Crew(
    agents=[manager,data_analyst,competitor_analyst,report_writer],
    tasks=[market_data_task,competitor_task,report_task],
    process=Process.hierarchical, #Key difference from Agents_with_tools.py: hierarchical 
                                     #process with manager overseeing workers
    manager_agent=manager,          #Your custom manager agent is specified here
    verbose=True
)

# ------------------------------------------------
# EXECUTION
# ------------------------------------------------

result = crew.kickoff()

print("\nFinal Report:\n")
print(result)
