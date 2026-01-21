"""
RAG (Retrieval-Augmented Generation) System with Ollama
ChromaDB + Ollama Embeddings + LangGraph
"""

import os
import re
from glob import glob
from pathlib import Path
from dotenv import load_dotenv

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langgraph.graph import START, StateGraph, END
from typing import List, Literal
from typing_extensions import TypedDict
from pydantic import BaseModel, Field

# 환경 변수 로드
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# ============= Data Models =============
class RouteQuery(BaseModel):
    """사용자 쿼리를 가장 관련성이 높은 데이터 소스로 라우팅합니다."""
    datasource: Literal["vectorstore", "casual_talk"] = Field(
        ...,
        description="""
        사용자 질문에 따라 casual_talk 또는 vectorstore로 라우팅합니다.
        - casual_talk: 일상 대화를 위한 데이터 소스
        - vectorstore: RAG로 vectorstore 검색이 필요한 경우
        """,
    )

class GradeDocuments(BaseModel):
    """검색된 문서가 질문과 관련성 있는지 평가합니다."""
    binary_score: Literal["yes", "no"] = Field(
        description="문서가 질문과 관련이 있는지 'yes' 또는 'no'로 평가"
    )

class GraphState(TypedDict):
    question: str
    generation: str
    documents: List[str]

# ============= Helper Functions =============
def read_pdf_and_split_text(pdf_path, chunk_size=1000, chunk_overlap=100):
    """
    PDF 파일을 읽고 텍스트를 분할합니다.

    Args:
        pdf_path (str): PDF 파일 경로
        chunk_size (int): 각 텍스트 청크의 크기
        chunk_overlap (int): 청크 간의 중첩 크기

    Returns:
        list: 분할된 텍스트 청크 리스트
    """
    print(f"  📄 PDF 처리 중: {pdf_path}")
    pdf_loader = PyPDFLoader(pdf_path)
    data_from_pdf = pdf_loader.load()

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    splits = text_splitter.split_documents(data_from_pdf)
    print(f"  ✓ {len(splits)}개 청크 생성")
    return splits

# ============= RAG System Class =============
class RAGSystemOllama:
    def __init__(self, persist_directory='chroma_store', pdf_directory='datafile'):
        self.persist_directory = persist_directory
        self.pdf_directory = pdf_directory

        # Ollama 임베딩 초기화
        print("✓ Ollama 임베딩 초기화 중...")
        self.embedding = OllamaEmbeddings(model='nomic-embed-text')

        # LLM 초기화 (LM Studio)
        print("✓ LLM 초기화 중...")
        self.model = ChatOpenAI(model="google/gemma-3-4b")

        # Vectorstore 로드 또는 생성
        self._init_vectorstore()

        # Retriever 설정
        self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": 5})

        # Router 설정
        self._init_router()

        # Grader 설정
        self._init_grader()

        # RAG Chain 설정
        self._init_rag_chain()

        # LangGraph 워크플로우 설정
        self._init_workflow()

    def _init_vectorstore(self):
        """Vectorstore 초기화"""
        if os.path.exists(self.persist_directory):
            print("✓ 기존 ChromaDB 로드 중...")
            self.vectorstore = Chroma(
                persist_directory=self.persist_directory,
                embedding_function=self.embedding
            )
        else:
            print("✓ 새로운 ChromaDB 생성 중...")
            self.vectorstore = None
            pdf_files = glob(f'{self.pdf_directory}/*.pdf')

            if not pdf_files:
                print(f"⚠️  경고: '{self.pdf_directory}' 폴더에 PDF 파일이 없습니다.")
                # 빈 vectorstore 생성
                self.vectorstore = Chroma(
                    persist_directory=self.persist_directory,
                    embedding_function=self.embedding
                )
                return

            for pdf_path in pdf_files:
                chunks = read_pdf_and_split_text(pdf_path)
                # 100개씩 나눠서 저장
                for i in range(0, len(chunks), 100):
                    if self.vectorstore is None:
                        self.vectorstore = Chroma.from_documents(
                            documents=chunks[i:i+100],
                            embedding=self.embedding,
                            persist_directory=self.persist_directory
                        )
                    else:
                        self.vectorstore.add_documents(documents=chunks[i:i+100])

    def _init_router(self):
        """질문 라우터 초기화"""
        structured_llm_router = self.model.with_structured_output(RouteQuery)

        router_system = """
        당신은 사용자의 질문을 vectorstore 또는 casual_talk으로 라우팅하는 전문가입니다.
        - vectorstore에는 온실, 농업, 스마트팜 관련 문서가 포함되어 있습니다.
        - 사용자의 질문이 일상 대화에 관련된 경우 casual_talk을 사용하십시오.
        """

        route_prompt = ChatPromptTemplate.from_messages([
            ("system", router_system),
            ("human", "{question}"),
        ])

        self.question_router = route_prompt | structured_llm_router

    def _init_grader(self):
        """문서 평가자 초기화"""
        structured_llm_grader = self.model.with_structured_output(GradeDocuments)

        grader_prompt = PromptTemplate.from_template("""
        당신은 검색된 문서가 사용자 질문과 관련이 있는지 평가하는 평가자입니다.
        문서에 사용자 질문과 관련된 키워드 또는 의미가 포함되어 있으면 관련성이 있다고 평가하십시오.

        Retrieved document: {document}
        User question: {question}
        """)

        self.retrieval_grader = grader_prompt | structured_llm_grader

    def _init_rag_chain(self):
        """RAG 체인 초기화"""
        rag_system = """
        당신은 스마트 온실 관리 전문가입니다.
        주어진 context는 vectorstore에서 검색된 결과입니다.
        주어진 context를 기반으로 사용자의 question에 대해 정확하고 친절하게 답변하세요.

        question: {question}
        context: {context}
        """

        rag_prompt = PromptTemplate(
            input_variables=["question", "context"],
            template=rag_system
        )

        self.rag_chain = rag_prompt | self.model

    def _route_question(self, state):
        """질문 라우팅"""
        question = state['question']
        route = self.question_router.invoke({"question": question})
        return route.datasource

    def _retrieve(self, state):
        """문서 검색"""
        question = state['question']
        documents = self.retriever.invoke(question)
        return {"documents": documents, "question": question}

    def _grade_documents(self, state):
        """문서 평가"""
        question = state['question']
        documents = state['documents']
        filtered_docs = []

        for doc in documents:
            is_relevant = self.retrieval_grader.invoke({
                "question": question,
                "document": doc.page_content
            })
            if is_relevant.binary_score == "yes":
                filtered_docs.append(doc)

        return {"documents": filtered_docs, "question": question}

    def _generate(self, state):
        """RAG 응답 생성"""
        question = state['question']
        documents = state['documents']
        generation = self.rag_chain.invoke({
            "question": question,
            "context": documents
        })
        return {
            "documents": documents,
            "question": question,
            "generation": generation
        }

    def _casual_talk(self, state):
        """일상 대화"""
        question = state['question']
        generation = self.model.invoke(question)
        return {
            "question": question,
            "generation": generation
        }

    def _init_workflow(self):
        """LangGraph 워크플로우 초기화"""
        workflow = StateGraph(GraphState)

        # 노드 추가
        workflow.add_node("retrieve", self._retrieve)
        workflow.add_node("grade_documents", self._grade_documents)
        workflow.add_node("generate", self._generate)
        workflow.add_node("casual_talk", self._casual_talk)

        # 엣지 추가
        workflow.add_conditional_edges(
            START,
            self._route_question,
            {
                "vectorstore": "retrieve",
                "casual_talk": "casual_talk"
            }
        )
        workflow.add_edge("casual_talk", END)
        workflow.add_edge("retrieve", "grade_documents")
        workflow.add_edge("grade_documents", "generate")
        workflow.add_edge("generate", END)

        self.app = workflow.compile()

    def query(self, question: str) -> str:
        """
        질문에 대한 답변 생성

        Args:
            question (str): 사용자 질문

        Returns:
            str: 생성된 답변
        """
        result = self.app.invoke({"question": question})

        # AIMessage 객체에서 content 추출
        generation = result.get('generation', '')
        if hasattr(generation, 'content'):
            return generation.content
        return str(generation)

    def stream_query(self, question: str):
        """
        스트리밍 방식으로 답변 생성

        Args:
            question (str): 사용자 질문

        Yields:
            str: 생성된 답변 토큰
        """
        for msg, meta in self.app.stream({"question": question}, stream_mode='messages'):
            if hasattr(msg, 'content') and msg.content:
                yield msg.content

    def add_pdf_from_bytes(self, pdf_bytes, filename: str) -> bool:
        """
        업로드된 PDF 바이트를 vectorstore에 추가

        Args:
            pdf_bytes: PDF 파일 바이트
            filename (str): 파일명

        Returns:
            bool: 성공 여부
        """
        import tempfile
        try:
            # 임시 파일로 저장
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                tmp_file.write(pdf_bytes)
                tmp_path = tmp_file.name

            # PDF 처리 및 분할
            chunks = read_pdf_and_split_text(tmp_path)

            # vectorstore에 추가 (100개씩)
            for i in range(0, len(chunks), 100):
                self.vectorstore.add_documents(documents=chunks[i:i+100])

            # 임시 파일 삭제
            os.unlink(tmp_path)

            print(f"✓ {filename} 업로드 완료: {len(chunks)}개 청크 추가")
            return True

        except Exception as e:
            print(f"✗ PDF 업로드 실패: {str(e)}")
            return False


# 싱글톤 인스턴스 (한 번만 초기화)
_rag_instance = None

def get_rag_system(persist_directory='chroma_store', pdf_directory='datafile'):
    """RAG 시스템 싱글톤 인스턴스 반환"""
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = RAGSystemOllama(persist_directory, pdf_directory)
    return _rag_instance
