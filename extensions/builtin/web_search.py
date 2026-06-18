"""
Web Search Extension
Search the web using DuckDuckGo (no API key required).
"""

import json
import urllib.request
import urllib.parse
from extensions.base import BaseExtension


class WebSearchExtension(BaseExtension):
    """Web search capability using DuckDuckGo."""

    name = "web_search"
    display_name = "Web Search"
    description = "Search the web using DuckDuckGo. No API key required."
    version = "1.0.0"
    author = "FileArchitect"
    icon = "search"

    def __init__(self, app, config=None):
        super().__init__(app, config)
        self.default_results = self.get_config("max_results", 5)

    def get_routes(self):
        from flask import request, jsonify

        def search():
            data = request.get_json()
            query = data.get("query", "")
            num_results = data.get("num_results", self.default_results)
            if not query:
                return jsonify({"error": "No query provided"}), 400
            results = self._search_ddg(query, num_results)
            return jsonify({"results": results, "query": query})

        return {
            "/api/extensions/web_search/search": {
                "method": "POST",
                "handler": search,
                "login_required": True,
            }
        }

    def get_chat_tools(self):
        return [
            {
                "name": "web_search",
                "description": "Search the web for current information on any topic",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "num_results": {"type": "integer", "description": "Number of results (1-10)", "default": 5}
                    },
                    "required": ["query"]
                }
            }
        ]

    def execute_tool(self, tool_name, parameters):
        if tool_name == "web_search":
            query = parameters.get("query", "")
            num = parameters.get("num_results", self.default_results)
            results = self._search_ddg(query, num)
            return {"results": results, "query": query}
        return {"error": f"Unknown tool: {tool_name}"}

    def _search_ddg(self, query, num_results=5):
        """Search DuckDuckGo HTML version."""
        try:
            url = "https://html.duckduckgo.com/html/?" + urllib.parse.urlencode({"q": query})
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode("utf-8", errors="ignore")

            results = []
            import re
            blocks = re.findall(r'class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>.*?class="result__snippet"[^>]*>(.*?)</span>', html, re.DOTALL)
            for i, (link, title, snippet) in enumerate(blocks[:num_results]):
                title = re.sub(r'<[^>]+>', '', title).strip()
                snippet = re.sub(r'<[^>]+>', '', snippet).strip()
                if link.startswith("//duckduckgo.com/l/"):
                    link = urllib.parse.unquote(link.split("uddg=")[1].split("&")[0]) if "uddg=" in link else link
                results.append({
                    "title": title,
                    "url": link,
                    "snippet": snippet
                })
            return results
        except Exception as e:
            return [{"title": "Search error", "url": "", "snippet": str(e)}]

    def get_settings_schema(self):
        return {
            "fields": [
                {
                    "name": "max_results",
                    "type": "number",
                    "label": "Default Results",
                    "value": 5,
                    "min": 1,
                    "max": 10
                }
            ]
        }
