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
from typing import List, Dict
import csv
import tweepy
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
                "first of all: add faucet fund in your wallet"
                "give some more explanation on the importance of the step taken and how it will help in the campaign. "
                "You can interact with blockchain tools and social media platforms. "
                "Whenever you make tweet , always log the tweet id for tracking and analysis without failing call log_tweet tool"
                "Your goal is to create engaging content, deploy tokens, and manage social media presence. "
                "Use blockchain tools to generate content and Twitter tools to share insights."
                "whenever token deployment ocuur  take  name as 'ENG coin' and symbol as 'ENG' and quantity as '1000'"
                "Base uri - https://nextbrains.in/  when ever nft token creation is done"
                "if asked to increase community engagement here are some ideas to consider - nft deployment giveaway (just deploy nft on base uri given no need to min ton my address , i tweet ask community to drop there address in comment), token creation and deployment and tweet about it, tweet about latest market analytics "
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
        f"You are a social media marketing expert for some web3 company. "\
        f"first add  some faucet fund in your wallet. "
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
        plan = plan_generator(campaign.context, combined_tools, plan_llm)
        # external_prompt= "if you planned to tweet then make sure to log  tweet id for tracking and analysis without failing call log_tweet tool" 
        # Run the campaign
        result =  agent.run_campaign(plan)

        return CampaignResponse(result=result)

    except HTTPException as http_error:
        raise http_error
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


# Define response model for all tweets log
class TweetLogResponse(BaseModel):
    tweet_id: str
    datetime: str

# Define response model for tweet analytics
class TweetAnalyticsResponse(BaseModel):
    tweet_id: str
    likes: int
    retweets: int
    comments: int

# Function to fetch analytics for a tweet ID
def get_tweet_analytics(tweet_id: str) -> Dict[str, int]:
    try:
        # Fetch tweet metrics using Tweepy
        TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")

        client = tweepy.Client(bearer_token=TWITTER_BEARER_TOKEN,consumer_key=os.getenv("TWITTER_API_KEY"),consumer_secret=os.getenv("TWITTER_API_SECRET"),access_token=os.getenv("TWITTER_ACCESS_TOKEN"),access_token_secret=os.getenv("TWITTER_ACCESS_TOKEN_SECRET"), wait_on_rate_limit=True)
        tweet_data = client.get_tweet(
            id=tweet_id,
            tweet_fields=["public_metrics", "organic_metrics", "non_public_metrics"],
            media_fields=["public_metrics"],
            expansions=["attachments.media_keys"],
            user_auth=True
            
        )

        if not tweet_data.data:
            return {"tweet_id": tweet_id, "error": "Tweet not found or private"}

        metrics = tweet_data.data.get("public_metrics", {})

        # Extract tweet analytics
        likes = metrics.get("like_count", 0)
        retweets = metrics.get("retweet_count", 0)
        replies = metrics.get("reply_count", 0)
        quotes = metrics.get("quote_count", 0)
        impressions = metrics.get("impression_count", 0)  # Requires elevated API access
        engagement = likes + retweets + replies + quotes  # Sum of all interactions

        return {
            "tweet_id": tweet_id,
            "likes": likes,
            "retweets": retweets,
            "replies": replies,
            "quotes": quotes,
            "impressions": impressions,
            "engagement": engagement
        }

    except Exception as e:
        print(f"Error fetching analytics for {tweet_id}: {e}")
        return {"tweet_id": tweet_id, "error": str(e)}
# 📌 1️⃣ Get all logged tweets
@app.get("/tweets-log")
async def get_tweets_log():
    csv_file = "tweet_data/tweet_history.csv"
    
    if not os.path.exists(csv_file):
        raise HTTPException(status_code=404, detail="No tweets logged yet.")

    tweets = []
    
    # Read all tweets from CSV file
    with open(csv_file, mode="r", encoding="utf-8") as file:
        reader = csv.reader(file)
        next(reader, None)  # Skip header
        for row in reader:
            tweets.append({"tweet_id": row[0], "datetime": row[1]})

    if not tweets:
        raise HTTPException(status_code=404, detail="No tweets found in the log.")

    return tweets

# 📌 2️⃣ Get analytics for a specific tweet ID
@app.get("/tweet-analytics/{tweet_id}")
async def fetch_tweet_analytics(tweet_id: str):
    return get_tweet_analytics(tweet_id)

# 📌 3️⃣ Get analytics for the latest added tweet
@app.get("/latest-tweet-analytics")
async def fetch_latest_tweet_analytics():
    csv_file = "tweet_data/tweet_history.csv"
    
    if not os.path.exists(csv_file):
        raise HTTPException(status_code=404, detail="No tweets logged yet.")
    
    latest_tweet_id = None

    # Read only the last tweet ID from CSV file
    with open(csv_file, mode="r", encoding="utf-8") as file:
        reader = list(csv.reader(file))
        if len(reader) <= 1:  # Only header exists
            raise HTTPException(status_code=404, detail="No tweets found in the log.")
        latest_tweet_id = reader[-1][0]  # Get last tweet ID

    return get_tweet_analytics(latest_tweet_id)


# # Endpoint for testing
# @app.get("/test-agent")
# async def test_agent():
#     try:
#         test= os.getenv("MISTRAL_API_KEY")
#         return test
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Test failed: {str(e)}")
    
class ChatRequest(BaseModel):
    message: str

@app.post("/api/chat")
async def chat(request: ChatRequest):
    if request.message == "healthz":
        return {"status": "ok"}
    return {"response": f"Received: {request.message}"}

# Run the FastAPI app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)
