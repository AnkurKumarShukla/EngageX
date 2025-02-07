from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from langchain.tools import Tool
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
import os
from langgraph.prebuilt import create_react_agent
from dotenv import load_dotenv
from twitter_langchain import TwitterApiWrapper, TwitterToolkit
from langchain_google_genai import ChatGoogleGenerativeAI
from cdp_langchain.agent_toolkits import CdpToolkit
from cdp_langchain.utils import CdpAgentkitWrapper
from langchain_mistralai import ChatMistralAI
from langgraph.checkpoint.memory import MemorySaver
from tools.graph_uniswap_tool import uniswap_analysis_tool
from tools.tweet_tracker import log_tweet
import asyncio
import websockets
import json
memory = MemorySaver()
# Load environment variables
load_dotenv()

# Initialize TwitterApiWrapper
twitter_api_wrapper = TwitterApiWrapper()

# Initialize CDP AgentKit wrapper
cdp = CdpAgentkitWrapper()

# Create toolkit from wrapper
cdp_toolkit = CdpToolkit.from_cdp_agentkit_wrapper(cdp)
twitter_toolkit = TwitterToolkit.from_twitter_api_wrapper(twitter_api_wrapper)

# Get tools from toolkits
twitter_tools = twitter_toolkit.get_tools()
base_tools = cdp_toolkit.get_tools()

# Combine all tools
combined_tools = base_tools + twitter_tools + [uniswap_analysis_tool]+[log_tweet]

# Initialize FastAPI
app = FastAPI()

# Define the request modela
class CampaignRequest(BaseModel):
    context: str
    llm_type: str  # "openai" or "gemini"

# Define the response model
class CampaignResponse(BaseModel):
    # restult is list
    result: list

class Web3SocialMarketingAgent:
    def __init__(self, llm, tools):
        self.llm = llm
        self.tools = tools
        self.agent = self._create_agent()

    def _create_agent(self):
        return create_react_agent(
            self.llm,
            self.tools,
            state_modifier=(
                "You are a sophisticated Web 3 Social Marketing Agent. "
                "You can interact with blockchain tools and social media platforms. "
                "Whenever you make tweet , always log the tweet id for tracking and analysis without failing call log_tweet tool"
                "Your goal is to create engaging content, deploy tokens, and manage social media presence. "
                "Use blockchain tools to generate content and Twitter tools to share insights."
            ),
            checkpointer=memory
        )
    
    

    def run_campaign(self, context):
        
        config = {"configurable": {"thread_id": "1"}}
        inputs = {"messages": [("user", "{}".format(context))]}
        def print_stream(stream):
            messages = []   
            for s in stream:
                message = s["messages"][-1]
                # send this to websocket to display
                messages.append(message)
                if isinstance(message, tuple):
                    print(message)
                else:
                    message.pretty_print()
            return messages
                
        stream=self.agent.stream(inputs, config=config, stream_mode="values")
        stream_data=print_stream(stream)
        # print(stream)

        return stream_data

def plan_generator(context: str, tools, llm) -> str:
    # Create a plan for the based on user context using llm
    
    prompt = (
        f"You are a social media marketing expert for some web3 company. "
        f"Create a plan for the following context: {context} given the following tools \n {tools}. "
        f"Provide as simple,to the point, brief plan as possble , which include 1 tweet(strictly) only. onchain activity only if required basd on your creativity and user requirement. keep it simple and short in brief, to the point , what is plan  what what to do what sequence . do not add unncessary details. "
        
    )
    messages = [
        HumanMessage(content=prompt),
    ]
    plan = llm.invoke(messages)
    return plan

# Define the request model for the planner endpoint
class PlanRequest(BaseModel):
    context: str



@app.post("/planner")
def planner_endpoint(request: PlanRequest):
    # Select the LLM based on the user's choice
    llm = llm = ChatMistralAI(model="mistral-small-latest",temperature=0.3,max_retries=2,mistral_api_key=os.getenv("MISTRAL_API_KEY"))
    plan = plan_generator(request.context, combined_tools, llm)
    return plan

@app.post("/run-campaign", response_model=CampaignResponse)
async def run_campaign(campaign: CampaignRequest):
    try:
        # Select the LLM based on the user's choice
        if campaign.llm_type == "openai":
            llm = ChatOpenAI(model="gpt-4o-mini")
        elif campaign.llm_type == "gemini":
            llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro", google_api_key=os.getenv("GEMINI_API_KEY"))
        elif campaign.llm_type == "mistral":
            llm = ChatMistralAI(model="mistral-large-latest",temperature=0.1,max_retries=2,mistral_api_key=os.getenv("MISTRAL_API_KEY"))
        else:
            raise HTTPException(status_code=400, detail="Invalid LLM type specified")

        # Create the unified Web3 Social Marketing Agent
        agent = Web3SocialMarketingAgent(llm, combined_tools)
        plan_llm=ChatMistralAI(model="mistral-small-latest",temperature=0.3,max_retries=2,mistral_api_key=os.getenv("MISTRAL_API_KEY"))
        # Generate the plan
        # plan = plan_generator(campaign.context, combined_tools, plan_llm)
        # external_prompt= "if you planned to tweet then make sure to log  tweet id for tracking and analysis without failing call log_tweet tool" 
        # Run the campaign
        result =  agent.run_campaign(campaign.context)

        return CampaignResponse(result=result)

    except HTTPException as http_error:
        raise http_error
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

# Endpoint for testing
@app.get("/test-agent")
async def test_agent():
    try:
        # Use OpenAI as default LLM for testing
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro", google_api_key=os.getenv("GEMINI_API_KEY"))

        # Create agent with combined tools
        agent = Web3SocialMarketingAgent(llm, combined_tools)

        # Test with a sample context
        test_context = (
            "Create a token for a community project. The token should be named baw8a with symbol 0bawa, 3 in quantity."
        )

        result = agent.run_campaign(test_context)

        return {"result": result}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Test failed: {str(e)}")

# Run the FastAPI app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)
