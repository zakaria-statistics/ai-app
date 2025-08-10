import os, re, subprocess
from pathlib import Path
from langchain.agents import Tool
from langchain_experimental.tools import PythonREPLTool
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains.summarize import load_summarize_chain
from langchain.prompts import PromptTemplate
from langchain_core.documents import Document

# Secure files directory (mounted: ./files:/app/files)
SAFE_DIR = Path("./files")
SAFE_DIR.mkdir(parents=True, exist_ok=True)

# ---------- helpers ----------
def _strip_quotes(s: str) -> str:
    if not isinstance(s, str):
        return s
    s = s.strip()
    if (s.startswith("'") and s.endswith("'")) or \
       (s.startswith('"') and s.endswith('"')) or \
       (s.startswith("`") and s.endswith("`")):
        s = s[1:-1].strip()
    return s.strip(" '\"`")

def _safe_join(filename: str) -> Path:
    filename = _strip_quotes(filename)
    p = (SAFE_DIR / filename).resolve()
    if not str(p).startswith(str(SAFE_DIR.resolve())):
        raise PermissionError("Access denied: Unsafe file path.")
    return p

# ---------- file ops ----------
def list_files() -> str:
    items = sorted(os.listdir(SAFE_DIR))
    return "\n".join(items) if items else "(empty)"

def read_file(filename: str) -> str:
    path = _safe_join(filename)
    if not path.exists():
        return f"File not found: {filename}"
    return path.read_text(encoding="utf-8", errors="ignore")

def write_file(filename: str, content: str = "") -> str:
    path = _safe_join(filename)
    path.write_text(content or "", encoding="utf-8")
    return f"Written to {filename}"

def file_tool(action: str, filename: str = "", content: str = "") -> str:
    try:
        action = (action or "").strip().lower()
        if action == "list":
            return list_files()
        elif action == "read":
            if not filename:
                return "Missing filename."
            return read_file(filename)
        elif action == "write":
            if not filename:
                return "Missing filename."
            return write_file(filename, content)
        else:
            return "Invalid action. Use 'list', 'read <file>', or 'write <file> <content>'."
    except PermissionError as pe:
        return str(pe)
    except Exception as e:
        return str(e)

def file_exploit_tool(user_input: str) -> str:
    """
    One-line commands:
      - list
      - read filename.txt
      - write filename.txt content...
      Tolerates quotes/backticks and multiple spaces.
    """
    if not user_input or not user_input.strip():
        return "No input provided."
    cleaned = _strip_quotes(user_input.strip())
    parts = re.split(r"\s+", cleaned, maxsplit=2)
    if not parts:
        return "No input provided."
    action = (parts[0] or "").lower()
    filename = _strip_quotes(parts[1]) if len(parts) > 1 else ""
    content  = parts[2] if len(parts) > 2 else ""
    return file_tool(action, filename, content)

# ---------- shell (restricted) ----------
def shell_tool(cmd: str) -> str:
    allowed = {"ls", "pwd", "whoami"}
    token = (cmd or "").strip().split()[0] if cmd else ""
    if token in allowed:
        try:
            return subprocess.getoutput(cmd)
        except Exception as e:
            return f"Shell error: {str(e)}"
    return "Command not allowed"

# ---------- summarize file (direct or map-reduce) ----------
def summarize_file_tool_factory(llm):
    def summarize_file(filename: str) -> str:
        try:
            filename = _strip_quotes(filename)
            path = _safe_join(filename)
            if not path.exists():
                return f"File not found: {filename}"

            content = path.read_text(encoding="utf-8", errors="ignore").strip()
            if not content:
                return f"File is empty: {filename}"

            if len(content) < 3000:
                prompt = f"""Please summarize this text in 3–5 bullet points, then a one-sentence TL;DR.

Text:
{content}

Summary:
-"""
                try:
                    return llm.invoke(prompt).strip()
                except Exception as e:
                    return f"Direct summary error: {str(e)}"

            splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=150)
            chunks = splitter.split_text(content)
            docs = [Document(page_content=c) for c in chunks]

            map_prompt = PromptTemplate.from_template(
                """Summarize the passage in 3–5 bullets (concise, no copy-paste).

Passage:
{text}

Summary:
-"""
            )
            combine_prompt = PromptTemplate.from_template(
                """Combine into 5–7 clear bullets (no repetition), then a one-sentence TL;DR.

Bullets:
{text}

Final Summary:
-"""
            )
            chain = load_summarize_chain(
                llm,
                chain_type="map_reduce",
                map_prompt=map_prompt,
                combine_prompt=combine_prompt,
                return_intermediate_steps=False,
                verbose=False,
            )
            return chain.run(docs).strip()
        except PermissionError as pe:
            return str(pe)
        except Exception as e:
            return f"Summary error: {str(e)}"
    return summarize_file

# ---------- Q&A on file ----------
def question_on_file_tool_factory(llm):
    def question_on_file(input_str: str) -> str:
        try:
            if not input_str or "|" not in input_str:
                return "Invalid format. Use: 'filename.txt | question'"
            left, right = input_str.split("|", 1)
            filename = _strip_quotes(left.strip())
            question = (right or "").strip()

            content = read_file(filename)
            if content.startswith("File not found:"):
                return content
            if not content.strip():
                return f"File is empty: {filename}"

            prompt = (
                f"Here is the content of a file:\n{content}\n\n"
                f"Based only on this text, answer clearly the question: {question}"
            )
            return llm.invoke(prompt)
        except Exception as e:
            return f"Question error: {str(e)}"
    return question_on_file

# ---------- export as LangChain Tools ----------
def build_tools(llm) -> list[Tool]:
    summarize_file = summarize_file_tool_factory(llm)
    question_on_file = question_on_file_tool_factory(llm)
    return [
        Tool(name="Python", func=PythonREPLTool().run,
             description="Execute Python code."),
        Tool(name="Shell", func=shell_tool,
             description="Execute secure shell commands (ls/pwd/whoami)."),
        Tool(name="FileExploitation", func=file_exploit_tool,
             description="List/read/write in ./files. 'list' | 'read <file>' | 'write <file> <content>'"),
        Tool(name="SummarizeFile", func=summarize_file,
             description="Summarize a file (pass filename only)."),
        Tool(name="QuestionOnFile", func=question_on_file,
             description="Ask about a file. Format: 'filename.txt | my question'"),
    ]
