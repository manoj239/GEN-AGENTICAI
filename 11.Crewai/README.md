# CrewAI Examples

Three tiny Python scripts that show **three different ways AI agents can work together** using [CrewAI](https://docs.crewai.com/) and Google's **Gemini 2.5 Flash**.

Pick any file, run it, read the output — that's it.

---

## What's inside?

Think of each script as a mini team of AI workers doing a project together.

| Script | The team pattern | In plain English |
|---|---|---|
| [1.Agents_with_tools.py](1.Agents_with_tools.py) | **Sequential + Web Search** | Researcher (with Google Search via Serper) → Writer. The researcher finds real, up-to-date info; the writer turns it into a blog post. |
| [2.Manager_worker.py](2.Manager_worker.py) | **Manager & Workers (boss + team)** | A Project Manager agent assigns work to 3 specialists (data analyst, competitor analyst, report writer) and reviews the result. |
| [3.peer_to_peer.py](3.peer_to_peer.py) | **Peer-to-Peer (teammates)** | Agents can **ask each other for help** mid-task. E.g. the Writer can ping the Researcher: "Hey, I need one more fact." |

---

## Setup (one time)

Open a PowerShell terminal in this folder and run:

```powershell
# 1. Create a virtual environment
python -m venv .venv

# 2. Activate it
.\.venv\Scripts\Activate.ps1

# 3. Install everything
pip install -r requirements.txt
```

Then create a file named **`.env`** in this same folder and paste your keys inside:

```env
GOOGLE_API_KEY=paste_your_google_key_here
SERPER_API_KEY=paste_your_serper_key_here
```

That's the whole setup. You only do it once.

---

## Run any example

```powershell
python 1.Agents_with_tools.py     # pipeline + real web search
python 2.Manager_worker.py        # manager delegates to workers
python 3.peer_to_peer.py          # agents help each other
```

The final result is printed at the bottom of the terminal.
Because `verbose=True` is on, you'll also see each agent "thinking" step by step — that part is the fun bit to watch.

---

## Which pattern should I use?

- **Need real, current info from the internet?** → Add a tool (`1.Agents_with_tools.py`)
- **Big project, needs a boss to coordinate?** → Hierarchical (`2.Manager_worker.py`)
- **Agents need to chat and help each other?** → Peer-to-peer (`3.peer_to_peer.py`)

---

## The two magic settings to remember

| Setting | What it does |
|---|---|
| `Process.sequential` vs `Process.hierarchical` | How tasks flow — straight line vs boss-driven. |
| `allow_delegation=True` | Lets an agent ask other agents for help. Turn it on for managers and peers. |

---

Happy building!
