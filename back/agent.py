import os
from langchain_community.llms import Ollama
from langchain.agents import initialize_agent, Tool
from langchain.agents.agent_types import AgentType
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from tools import build_tools

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
MODEL_NAME = os.getenv("MODEL_NAME", "mistral")

SYSTEM_PROMPT = (
    "You are an assistant for question-answering tasks. "
    "For any file operations (list/read/write), you MUST call the FileExploitation tool. "
    "Return the tool output verbatim unless asked otherwise. "
    "Answers must be concise (<=3 sentences). If you don't know, say you don't know."
)

# singletons
_agent = None
_stream_chain = None

def _make_llm():
    return Ollama(model=MODEL_NAME, base_url=OLLAMA_BASE_URL, 
                  temperature=0.1, max_tokens=512, verbose=True)

def get_agent():
    global _agent
    if _agent is None:
        llm = _make_llm()
        tools: list[Tool] = build_tools(llm)
        _agent = initialize_agent(
            tools,
            llm,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=10,
            max_execution_time=30,
            agent_kwargs={"system_message": SYSTEM_PROMPT},
        )
    return _agent

def get_stream_chain():
    global _stream_chain
    if _stream_chain is None:
        llm = _make_llm()
        qa = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", "{input}"),
        ])
        _stream_chain = (qa | llm | StrOutputParser())
    return _stream_chain
