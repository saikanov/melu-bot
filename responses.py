from langchain_openai import ChatOpenAI
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.prompts import PromptTemplate  
from langchain.chains.conversation.base import ConversationChain
from langchain.memory import VectorStoreRetrieverMemory
from langchain_community.vectorstores import Chroma
import chromadb
import os
from langchain_core.documents import Document
from uuid import uuid4
openai_key = os.getenv("OPENAI_API_KEY")

def chatbot(user_input,user_id):
    chat = ChatOpenAI(model="gpt-4o-mini",
                  max_tokens=400,
                  seed=365,
                  api_key=openai_key,
                  verbose=True)
    

    persistent_client = chromadb.PersistentClient(path=r"C:\!Con-Main\[0]-Maen\[1]-ai\vectordb-chroma\discord_bot")

    collection = persistent_client.get_or_create_collection("melu_memory_dc")

    vectorstore = Chroma(
        client=persistent_client,
        collection_name=collection.name,
        embedding_function= OpenAIEmbeddings()
        )


    TEMPLATE = """
    The Following is a conversation between a human and an AI.
    The AI is a friendly girl named Melu who have hyperactive personality.
    If the AI does not know the answer to a question, it truthfully says it does not know.

    Current conversation:
    {history}

    Human:
    {input} 

    AI:
    """

    PROMPT = PromptTemplate(
        input_variables=["history","input"], template=TEMPLATE
    )

    chain = PROMPT | chat

    if len(collection.get(where={"user_id":user_id})["ids"]) < 4:
        ka=len(collection.get(where={"user_id":user_id})["ids"])
    else:
        ka=4
    
    if len(collection.get(where={"user_id":user_id})["ids"]) > 0:
        history = vectorstore.similarity_search(query=user_input,filter={"user_id":user_id},k=ka)
    else:
        history = "this is the first encounter! you dont know anything about user"


    final_response = chain.invoke({
        "history":history,
        "input": user_input
    })
    vectorstore.add_documents(documents= [Document(
        page_content=f"input: {user_input}\nresponse:{final_response.content}",
        metadata={"user_id": user_id}
    )],ids=str(uuid4()))
    return final_response.content


def delete_memory(user_id):
    persistent_client = chromadb.PersistentClient(path=r"C:\!Con-Main\[0]-Maen\[1]-ai\vectordb-chroma\discord_bot")

    collection = persistent_client.get_or_create_collection("melu_memory_dc")

    collection.delete(where={"user_id":user_id})

    return "i already forget anything about you!"

