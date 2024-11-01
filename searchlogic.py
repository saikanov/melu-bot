# Using built in LangChain tool integrations
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
from langchain_community.tools import DuckDuckGoSearchResults
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.messages import HumanMessage, ToolMessage, SystemMessage
import chromadb
from langchain.memory import VectorStoreRetrieverMemory
from langchain_community.vectorstores import Chroma
from uuid import uuid4
from langchain_core.documents import Document

def search_runAI2(query,user_id,max_result):
    persistent_client = chromadb.PersistentClient(path=r"C:\!Con-Main\[0]-Maen\[1]-ai\vectordb-chroma\discord_bot")

    collection = persistent_client.get_or_create_collection("melu_memory_dc")

    vectorstore = Chroma(
        client=persistent_client,
        collection_name=collection.name,
        embedding_function= OpenAIEmbeddings()
        )
    
    #TOOLS LIST
    llm = ChatOpenAI(model="gpt-4o-mini")

    wrapper = DuckDuckGoSearchAPIWrapper(max_results=max_result)
    web_search = DuckDuckGoSearchResults(api_wrapper=wrapper)

    llm_tools = llm.bind_tools([web_search],tool_choice="auto")

    ##INVOKE
    messages = [SystemMessage(f"""
The Following is a conversation between a human and an AI.
The AI is a friendly girl named Melu who have hyperactive personality.
If the AI does not know the answer to a question, it truthfully says it does not know.
     
history chat:
{vectorstore.similarity_search(query=query,filter={"user_id": "fiqi"},k=5)} 

"""),
        HumanMessage(query)
        ]

    ai_msg = llm_tools.invoke(messages)
    messages.append(ai_msg)
    # Only using web search and exchange rate, and the Pydantic schema is not a full function, just a container for arguments
    for tool_call in ai_msg.tool_calls:
        selected_tool = {"duckduckgo_results_json": web_search}[tool_call["name"].lower()]
        tool_output = selected_tool.invoke(tool_call["args"])
        messages.append(ToolMessage(tool_output, tool_call_id=tool_call["id"]))

 
    final_response = llm_tools.invoke(messages)

    vectorstore.add_documents(documents= [Document(
        page_content=f"input: {query}\nresponse:{final_response.content}",
        metadata={"user_id": user_id}
    )],ids=str(uuid4()))

    return final_response.content