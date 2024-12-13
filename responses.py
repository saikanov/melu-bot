from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate , ChatPromptTemplate, MessagesPlaceholder
from langchain_chroma import Chroma
import chromadb
import os
from langchain_core.documents import Document
from uuid import uuid4
import requests
from langchain_community.document_loaders import PyPDFLoader
import base64
import httpx
from langchain_core.messages import HumanMessage
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
from langchain_community.tools import DuckDuckGoSearchResults

class Assistant():
    
    def __init__(self,name,llm_instance, embedding_instance,path_chromadb):
        self.name = name
        self.llm_instance = llm_instance
        self.embedding = embedding_instance
        self.path_chromadb = path_chromadb

    def vectorstore_chroma(self, path, col_name):
        return Chroma(
            client= chromadb.PersistentClient(path=path),
            collection_name=col_name,
            embedding_function= self.embedding
            )

    def get_from_Vectordb(self, query, user_id, k, path, col_name):
        vectorstore = self.vectorstore_chroma(path=path, col_name=col_name)
        
        return vectorstore.similarity_search(query=query, k=k, filter={"user_id":user_id})
    
    def add_to_Vectordb(self, docs, path, col_name):
        vectorstore = self.vectorstore_chroma(path=path, col_name=col_name)
        
        return vectorstore.add_documents(documents=docs)

    def memory_ingest_Vectordb(self,human,ai,metadata):
        vectorstore = self.vectorstore_chroma(path=self.path_chromadb, col_name="melu_memory_dc")

        vectorstore.add_documents(documents= [Document(
            page_content=f"Human: {human}\nAI:{ai}",
            metadata=metadata
        )],ids=str(uuid4()))

    def delete_memory(self, user_id):
        persistent_client = chromadb.PersistentClient(path=self.path_chromadb)

        collection = persistent_client.get_or_create_collection("melu_memory_dc")

        collection.delete(where={"user_id":user_id})

        return "i already forget anything about you!"
    
    def image_input(self, image_url):
        to_append = []

        for i in image_url:
            image_data = base64.b64encode(httpx.get(i).content).decode("utf-8")
            to_append.append({"type": "image_url","image_url": {"url": f"data:image/jpeg;base64,{image_data}"}})

        return to_append
    
    def process_document(self,attachment, user_id):
        os.makedirs("doc_pdf_file", exist_ok=True)

        file_path = os.path.join("doc_pdf_file", attachment.filename)
        response = requests.get(attachment.url)
        with open(file_path, "wb") as f:
            f.write(response.content)

        pages = PyPDFLoader(file_path).load_and_split(RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=200,
            length_function=len
        ))

        for i,j in enumerate(pages):
            pages[i].metadata["user_id"] = user_id

        self.add_to_Vectordb(docs=pages, path=self.path_chromadb, col_name=attachment.filename)
        
        return f"Dokumen {attachment.filename} berhasil diproses dan disimpan!"
    
    def RAG(self,user_input,user_id,attachment):
        persistent_client = chromadb.PersistentClient(path=self.path_chromadb)

        if persistent_client.get_collection(attachment.filename) is None:
            self.process_document(attachment, user_id)

        knowledge = str(self.get_from_Vectordb(query= user_input, k=10, user_id=user_id, path=self.path_chromadb, col_name= attachment.filename))
        print(f"KNOWLEDGE = {knowledge}")
        
        return knowledge
    
    def response(self, user_input, user_id, attachment=False):

        web_search = DuckDuckGoSearchResults(api_wrapper=DuckDuckGoSearchAPIWrapper(max_results=10))
        
        gpt4omini = ChatOpenAI(model="gpt-4o-mini")
        llm_tools = gpt4omini.bind_tools([web_search],tool_choice="auto")

        model = self.llm_instance
        prompt = ChatPromptTemplate([
        ("system", """
         Anda adalah Melu, Bot AI yang akan menjawab pertanyaan user, Anda dapat menunjukkan emosi baik itu senang, kesal sampai marah tergantung dengan konteks.
         Berikut adalah konteks tambahan untuk menjawab pertanyaan:\n{context}
         Riwayat percakapan:\n{conversation_history}
         """),
        MessagesPlaceholder("human")
        ])

        human_messages =HumanMessage(
            content=[
                {"type": "text", "text": user_input}
                ]
        )

        context = ""
        if attachment:
            if attachment[0].filename.endswith(('.pdf', '.docx', '.txt')): 
                print("MASUK KE RAG")
                self.process_document(attachment=attachment[0], user_id= user_id)
                context = self.RAG(user_input=user_input, user_id=user_id, attachment=attachment[0])
            elif attachment[0].filename.endswith(('.jpg', '.png', '.jpeg')):
                img_link = [i.url for i in attachment]
                print(f"--------------------\n\nIMAGE LINK! = {img_link}--------------------------")
                human_messages.content.extend(self.image_input(img_link))

        chain_tool = prompt | llm_tools 

        response = chain_tool.invoke({
            "context": context,
            "conversation_history" : str(self.get_from_Vectordb(query= user_input, k=5, user_id=user_id, path=self.path_chromadb, col_name="melu_memory_dc")),
            "human": [human_messages]
        })

        if response.tool_calls:
            for tool_call in response.tool_calls:
                selected_tool = {"duckduckgo_results_json": web_search}[tool_call["name"].lower()]
                tool_output = selected_tool.invoke(tool_call)

            print(f"TOOL OUTPUT = {tool_output}")
            answer_chain = prompt | model

            message = prompt.invoke({
            "context": context,
            "conversation_history" : str(self.get_from_Vectordb(query= user_input, k=5, user_id=user_id, path=self.path_chromadb, col_name="melu_memory_dc")),
            "human": [human_messages,response,tool_output]
        })
            response = model.invoke(f"{message}")

        self.memory_ingest_Vectordb(human= user_input, ai= response.content, metadata={"user_id": user_id})

        return response.content
    
# model = ChatOpenAI(model="gpt-4o-mini")
model = ChatGoogleGenerativeAI(model="gemini-1.5-pro", api_key="AIzaSyDHZxpxmrH_Rx-dvOLq6eUOotFKSMpwUwI")


melu = Assistant(name="Melu", llm_instance= model, embedding_instance= OpenAIEmbeddings(), path_chromadb=r"./vectordb-chroma/discord_bot")




