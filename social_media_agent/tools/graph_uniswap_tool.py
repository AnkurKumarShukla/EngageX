import requests
from langchain.tools import StructuredTool
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv
from typing import Dict, Any

load_dotenv()

llm = ChatOpenAI(model="gpt-4o-mini", api_key=os.getenv("OPENAI_API_KEY"))
graph_api_key = os.getenv("GRAPH_QUERRY_KEY")

def fetch_uniswap_data():
    """Fetches the latest Uniswap data using The Graph API."""
    url = f"https://gateway.thegraph.com/api/{graph_api_key}/subgraphs/id/5zvR82QoaXYFyDEKLZ9t6v9adgnptxYpKpSbxtgVENFV"
    query = """
    {
        tokens(first: 3, where: {volumeUSD_gte: "100000"}) {
        name
        poolCount
        symbol
        totalSupply
        volumeUSD
        txCount
        derivedETH
        totalValueLockedUSD
        totalValueLockedUSDUntracked
        }
    }
    """
    
    try:
        response = requests.post(url, json={'query': query})
        response.raise_for_status()
        return response.json().get("data", {}).get("tokens", [])
    except requests.exceptions.RequestException as error:
        return f"Error fetching UniSwap data: {error}"

def analyze_uniswap_data(query: str = "") -> str:
    """
    Analyzes Uniswap data based on an optional query parameter.
    
    Args:
        query: Optional query to focus the analysis
        
    Returns:
        str: Analysis results
    """
    data = fetch_uniswap_data()
    # data to string

    
    if not isinstance(data, list):
        return "Failed to fetch Uniswap data."
    
    # formatted_data = "\n".join(
    #     f"Name: {d['name']}, Symbol: {d['symbol']}, Pool_Count: {d['poolCount']}, "
    #     f"Total_Supply: {d['totalSupply']}, TX Count: {d['txCount']}, Volume: {d['volume']}"
    #     for d in data
    # )
    data = str(data)
    print(data)
    prompt = f"""
    Here is the latest Uniswap market data:
    
    {data}
    
    {f'Focus on: {query}' if query else 'Please provide short,brief (under 230 character), to the point insights on trends, anomalies, and overall market activity as this will be used to tweet in community to increase reach.as it will be used to tweet . no other greeting and unnecessary stuff'}
    """
    
    # response = llm.invoke(prompt)
    # return response.content if hasattr(response, "content") else response
    return prompt

# Define the tool using StructuredTool
uniswap_analysis_tool = StructuredTool.from_function(
    func=analyze_uniswap_data,
    name="UniswapAnalysisTool",
    description="Analyzes Uniswap market data for insights and engagement"
)


# print(analyze_uniswap_data())