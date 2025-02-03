from fastapi import FastAPI, HTTPException
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

# Load environment variables
load_dotenv()

# Initialize TwitterApiWrapper
twitter_api_wrapper = TwitterApiWrapper()
print(twitter_api_wrapper)

# Initialize CDP AgentKit wrapper
cdp = CdpAgentkitWrapper()

# Create toolkit from wrapper
cdp_toolkit = CdpToolkit.from_cdp_agentkit_wrapper(cdp)
twitter_toolkit = TwitterToolkit.from_twitter_api_wrapper(twitter_api_wrapper)

print(cdp_toolkit)
print("==========================================================")
print(twitter_toolkit)

# Get tools from toolkits
twitter_tools = twitter_toolkit.get_tools()
base_tools = cdp_toolkit.get_tools()
# print(base_tools)
# Initialize FastAPI
app = FastAPI()

# Define the request model
class CampaignRequest(BaseModel):
    context: str
    llm_type: str  # "openai" or "gemini"

# Define the response model
class CampaignResponse(BaseModel):
    result: str

@app.get("/test-twitter")
async def test_twitter_post():
    content = "This is a test tweet from FastAPI!"
    result = "Simulated Twitter post"
    return {"result": result}

@app.post("/run-campaign", response_model=CampaignResponse)
async def run_campaign(campaign: CampaignRequest):
    try:
        # Select the LLM based on the user's choice
        if campaign.llm_type == "openai":
            llm = ChatOpenAI(model="gpt-4")  # You can adjust the model version if needed
        elif campaign.llm_type == "gemini":
            llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro", google_api_key=os.getenv("GEMINI_API_KEY"))
        else:
            raise HTTPException(status_code=400, detail="Invalid LLM type specified")

        # Create specialized agents
        cdp_agent = create_react_agent(llm, base_tools,state_modifier="You are a helpful agent that can interact with the Base blockchain using CDP AgentKit. You can create wallets, deploy tokens, and perform transactions.")
        twitter_agent = create_react_agent(llm, twitter_tools)

        # Coordinator agent logic
        def coordinator_agent(context):
            # Decide which agent to use based on the context
            if "twitter" in context.lower():
                return twitter_agent
            elif "cdp" in context.lower():
                return cdp_agent
            else:
                # Default to CDP agent if no specific context is found
                return cdp_agent

        # Determine which agent to use
        agent = coordinator_agent(campaign.context)

        # Execute the agent
        events = agent.stream(
            {
                "messages": [
                    HumanMessage(content=campaign.context),
                ],
            },
            stream_mode="values",
        )

        # Process the events
        
        for event in events:
            event["messages"][-1].pretty_print()

        # Return the result
        return CampaignResponse(result="success")

    except HTTPException as http_error:
        raise http_error  # Propagate HTTPException for FastAPI to handle
    except Exception as e:
        # Handle other types of errors and log the detailed message
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

# Run the FastAPI app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)