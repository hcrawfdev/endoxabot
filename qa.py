"""Ask a question to the database."""
import faiss
from langchain import OpenAI
from langchain.chains import VectorDBQAWithSourcesChain
import pickle
import argparse

async def ask_question(question, domain):
    # Load the LangChain.
    print('ask question started')
    index = faiss.read_index(f"{domain}_confluence.index")
    print('faiss read')
    with open(f"{domain}_faiss_store.pkl", "rb") as f:
        store = pickle.load(f)
    print('pickle loaded')
    store.index = index
    chain = VectorDBQAWithSourcesChain.from_llm(llm=OpenAI(temperature=0), vectorstore=store)
    result = chain({"question": question})
    print('chain done')
    print(f"Answer: {result['answer']}")
    print(f"Sources: {result['sources']}")
    return result