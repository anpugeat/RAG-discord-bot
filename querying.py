from manage_embedding import load_index
from llama_index import ServiceContext
from llama_index.llms import OpenAI
import logging
import sys
import os

# Logging level set to INFO
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logging.getLogger().addHandler(logging.StreamHandler(stream=sys.stdout))

def get_llm():
    """Helper to get the configured OpenAI model."""
    return OpenAI(model=os.getenv("OPENAI_MODEL_NAME", "gpt-3.5-turbo"))   # cheap model for testing. can change if you like

async def data_querying(input_text: str):
    """
    Takes a user's question (input_text), searches the knowledge base,
    and returns an AI-generated answer.
    """
    # Load the Knowledge Base
    index = await load_index("data")
    
    # Configure the LLM
    llm = get_llm()
    service_context = ServiceContext.from_defaults(llm=llm)
    
    # Query Engine
    engine = index.as_query_engine(service_context=service_context)
    response = engine.query(input_text)

    response_text = response.response
    logging.info(response_text)

    return response_text

async def detect_academic_dishonesty(input_text: str):
    """
    Checks if the user is asking the bot to cheat (write an assignment for them).
    Returns (is_safe: bool, response_message: str).
    """
    llm = get_llm()
    prompt = (
        "You are an academic integrity filter for an educational bot. "
        f"Analyze this query: '{input_text}'. "
        "Does it explicitly ask to generate a full essay, write code without explanation, "
        "or complete an assignment for the user? "
        "If YES (violation), reply starting with 'VIOLATION:' followed by a gentle refusal "
        "and a suggestion to guide them instead (e.g. 'I can't write the essay, but I can help outline it'). "
        "If NO (safe), reply with 'SAFE'."
    )
    
    # Use complete() for direct text generation without context
    response = await llm.acomplete(prompt)
    text = response.text.strip()
    
    if text.startswith("VIOLATION"):
        # Return False (unsafe) and the explanation (removing the tag)
        return False, text.replace("VIOLATION:", "").strip()
    
    return True, ""

async def generate_quiz(topic: str):
    """
    Generates a 3-question multiple choice quiz on the given topic using the RAG index.
    """
    index = await load_index("data")
    llm = get_llm()
    service_context = ServiceContext.from_defaults(llm=llm)
    engine = index.as_query_engine(service_context=service_context)
    
    prompt = (
        f"Generate a 3-question multiple choice quiz about '{topic}' based on the available context. "
        "Format it exactly like this for Discord:\n"
        "**Q1:** [Question]\n"
        "A) [Option]\n"
        "B) [Option]\n"
        "C) [Option]\n"
        "||Correct Answer: [Letter]||"
        "Repeat for Q2 and Q3."
    )
    
    response = engine.query(prompt)
    return response.response