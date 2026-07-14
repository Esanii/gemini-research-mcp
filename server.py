import asyncio
import os
from pathlib import Path
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
# REMOVED: stdio_server import
from mcp.server.sse import SseServerTransport  # ADDED: Web transport layer
from starlette.applications import Starlette   # ADDED: Web framework container
from starlette.routing import Route            # ADDED: URL routing
import uvicorn                                 # ADDED: Production web server
from mcp import types
from google import genai
from google.genai import types as genai_types
from dotenv import load_dotenv

# Load .env from same directory as this script
load_dotenv(Path(__file__).parent / ".env")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY not set. Run setup.py to configure your API key."
    )

MODEL = "gemini-2.5-flash"
client = genai.Client(api_key=GEMINI_API_KEY)
server = Server("gemini-research-mcp")

SYSTEM_PROMPT = (
    "You are a research assistant. Summarize the topic accurately and evenhandedly. "
    "Be factual, do not editorialize. Include key people, dates, and events. "
    "Do not pad the response — match length to complexity."
)


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="research",
            description=(
                "Search the web and return a factual summary of a topic. "
                "Use for anything past Claude's knowledge cutoff or current events."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "What to research",
                    },
                    "detail": {
                        "type": "string",
                        "enum": ["low", "normal", "high"],
                        "description": "Summary length: low=~500w, normal=~1500w, high=~3000w",
                        "default": "normal",
                    },
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="research_url",
            description="Fetch and summarize a specific URL.",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to fetch and summarize",
                    },
                    "detail": {
                        "type": "string",
                        "enum": ["low", "normal", "high"],
                        "description": "Summary length: low=~500w, normal=~1500w, high=~3000w",
                        "default": "normal",
                    },
                },
                "required": ["url"],
            },
        ),
    ]


def detail_to_words(detail: str) -> str:
    return {"low": "~500", "normal": "~1500", "high": "~3000"}.get(detail, "~1500")


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    detail = arguments.get("detail", "normal")
    words = detail_to_words(detail)

    if name == "research":
        query = arguments["query"]
        prompt = (
            f"{SYSTEM_PROMPT}\n\n"
            f"Research the following topic using Google Search and write a summary of approximately {words} words:\n\n"
            f"{query}"
        )
        response = client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                tools=[genai_types.Tool(google_search=genai_types.GoogleSearch())],
            ),
        )
        return [types.TextContent(type="text", text=response.text)]

    elif name == "research_url":
        url = arguments["url"]
        prompt = (
            f"{SYSTEM_PROMPT}\n\n"
            f"Fetch the content at the following URL and write a summary of approximately {words} words:\n\n"
            f"{url}"
        )
        response = client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                tools=[genai_types.Tool(google_search=genai_types.GoogleSearch())],
            ),
        )
        return [types.TextContent(type="text", text=response.text)]

    else:
        return [types.TextContent(type="text", text=f"Unknown tool: {name}")]

# --- RENDER SSE NETWORKING CONFIGURATION ---
transport = SseServerTransport("/sse")

async def handle_sse(request):
    async with transport.connect_handlers(request.scope, request.receive, request._send_impl):
        await server.run(
            transport.read_stream,
            transport.write_stream,
            InitializationOptions(
                server_name="gemini-research-mcp",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

# Create a web application instance that Render can run
app = Starlette(
    routes=[
        Route("/sse", endpoint=handle_sse, methods=["GET"]),
        Route("/messages", endpoint=transport.handle_post_message, methods=["POST"]),
    ]
)

if __name__ == "__main__":
    # Fallback for local testing
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
