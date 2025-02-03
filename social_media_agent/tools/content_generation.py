from langchain.prompts import PromptTemplate
from langchain_core.tools import tool
from langchain.chains import LLMChain
from langchain_google_genai import ChatGoogleGenerativeAI
import os
from dotenv import load_dotenv
load_dotenv()



llm = ChatGoogleGenerativeAI(model="gemini-pro", google_api_key=os.getenv("GEMINI_API_KEY"))


def generate_content(context: str) -> str:
    """Tool to generate social media content using the provided LLM."""
    prompt_template = PromptTemplate(
        input_variables=["context"],
        template="Generate a social media post for a marketing campaign based on the following context: {context}"
    )
    llm_chain = LLMChain(llm=llm, prompt=prompt_template)
    return llm_chain.run(context)


# print(generate_content("tweet about my latest give away . who so every post goes viral will get shoes "))