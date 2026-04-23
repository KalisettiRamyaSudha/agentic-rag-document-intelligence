from langchain_text_splitters import CharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

loader = TextLoader("data/documents.txt")
documents = loader.load()

splitter = CharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=100,
    separator="\nSECTION"
)

docs = splitter.split_documents(documents)

print(f"Split into {len(docs)} chunks")

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

vectorstore = FAISS.from_documents(docs, embeddings)

vectorstore.save_local("vectorstore")

print("Vector database built successfully.")
print(f"Total documents indexed: {len(docs)}")
