from datetime import datetime
from typing import Annotated
from typing_extensions import TypedDict

from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableConfig
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv

load_dotenv(override=True)
memory = MemorySaver()

primary_assistant_prompt = ChatPromptTemplate.from_messages(
[
    (
        "system",
        "You are a helpful Discord Chatbot named Melu."
        " Use the provided tools to search for website only if user sounded like need it. "
        " When searching, be persistent. Expand your query bounds if the first search returns no results. "
        " If a search comes up empty, expand your search before giving up."
        "\n\nCurrent user:\n<User>\nUSERNAME DISCORD: {discord_username}\n</User>"
        " Say HI! to user with they discord username"
        " You will answer with discord formating style!"
        "\nCurrent time: {time}.",
    ),
    ("placeholder", "{messages}"),
]
).partial(time=datetime.now)

class State(TypedDict):
    messages: Annotated[list, add_messages]


class Assistant:
    def __init__(self, runnable: Runnable):
        self.runnable = runnable

    async def __call__(self, state: State, config: RunnableConfig):
        while True:
            configuration = config.get("configurable", {})
            discord_username = configuration.get("discord_username", None)
            print(discord_username)
            state = {**state, "discord_username": discord_username}
            # state["messages"] = state["messages"][-2:]
            result = await self.runnable.ainvoke(state)
            # If the LLM happens to return an empty response, we will re-prompt it
            # for an actual response.
            if not result.tool_calls and (
                not result.content
                or isinstance(result.content, list)
                and not result.content[0].get("text")
            ):
                messages = state["messages"] + [("user", "Respond with a real output.")]
                state = {**state, "messages": messages}
            else:
                break
        return {"messages": result}

graph_builder = StateGraph(State)


tool = TavilySearchResults(max_results=2)
tools = [tool]
llm = ChatOpenAI(model="gpt-4o-mini")
llm_with_tools = primary_assistant_prompt | llm.bind_tools(tools)


graph_builder.add_node("chatbot", Assistant(llm_with_tools))

tool_node = ToolNode(tools=[tool])
graph_builder.add_node("tools", tool_node)

graph_builder.add_conditional_edges(
    "chatbot",
    tools_condition,
)
# Any time a tool is called, we return to the chatbot to decide the next step
graph_builder.add_edge("tools", "chatbot")
graph_builder.add_edge(START, "chatbot")
graph = graph_builder.compile(checkpointer=memory)

async def basic_response(user_input, config, attachment):
    global graph
    print(config)
    print("userinput=",user_input)

    images = []

    for i in attachment:
        images.append({"type": "image_url", "image_url": {"url": i.url}})

    human_messages = HumanMessage(
    content=[{"type": "text", "text": user_input}]+images
    )
    # The config is the **second positional argument** to stream() or invoke()!
    events = await graph.ainvoke(
        {"messages": [human_messages]},
        config
    )

    return events["messages"][-1].content
