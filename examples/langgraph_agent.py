#!/usr/bin/env python3
"""
LangGraph agent that uses Band MCP tools with langchain-mcp-adapters.

This example shows how to use the Band MCP server with LangGraph
using the MultiServerMCPClient from langchain-mcp-adapters.

Usage:
    export OPENAI_API_KEY="sk-..."
    export BAND_API_KEY="band_..."
    uv run examples/langgraph_agent.py
"""

import asyncio
import logging
import os

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langgraph.graph import MessagesState, StateGraph, START
from langgraph.prebuilt import ToolNode, tools_condition

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Run LangGraph agent with Band MCP tools."""
    if not os.getenv("OPENAI_API_KEY") or not os.getenv("BAND_API_KEY"):
        logger.error("Error: Set OPENAI_API_KEY and BAND_API_KEY")
        return

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    # Create MCP client that connects to Band server
    client = MultiServerMCPClient(
        {
            "band": {
                "command": "uv",
                "args": ["--directory", project_root, "run", "band-mcp"],
                "transport": "stdio",
                "env": {
                    "BAND_API_KEY": os.getenv("BAND_API_KEY", ""),
                    "BAND_BASE_URL": os.getenv("BAND_BASE_URL", "https://app.band.ai"),
                },
            },
        }
    )

    logger.info("Loading tools from Band MCP server...")
    tools = await client.get_tools()
    logger.info(f"Loaded {len(tools)} tools!")

    # Create LLM and bind tools
    model = ChatOpenAI(model="gpt-4o", temperature=0)

    # Define the agent node
    def call_model(state: MessagesState):
        """Agent node that calls the LLM with available tools."""
        response = model.bind_tools(tools).invoke(state["messages"])
        return {"messages": [response]}

    # Build the graph
    builder = StateGraph(MessagesState)
    builder.add_node("agent", call_model)  # pyrefly: ignore[no-matching-overload]
    builder.add_node("tools", ToolNode(tools))
    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", tools_condition)
    builder.add_edge("tools", "agent")
    graph = builder.compile()

    logger.info("\n" + "=" * 50)
    logger.info("LangGraph Agent Ready!")
    logger.info("=" * 50)
    logger.info("Type 'exit' to quit\n")

    # Interactive loop
    messages: list[BaseMessage] = []
    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input.lower() in ["exit", "quit", "q"]:
            break

        messages.append(HumanMessage(content=user_input))
        result = await graph.ainvoke({"messages": messages})
        messages = result["messages"]
        logger.info("\nAgent: %s\n", messages[-1].content)


if __name__ == "__main__":
    asyncio.run(main())
