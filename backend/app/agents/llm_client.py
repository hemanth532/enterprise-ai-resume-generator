import json
import os
import re
from typing import Any, Dict, List

import requests


class LLMClient:
    def __init__(self):
        self.model = os.getenv("QWEN_MODEL", "qwen2:latest")
        self.ollama_server = os.getenv("OLLAMA_SERVER", "http://localhost:11434")
        self.ollama_api_base = f"{self.ollama_server.rstrip('/')}/v1"
        self.use_ollama = os.getenv("USE_OLLAMA", "true").lower() in ("1", "true", "yes")
        self.api_key = os.getenv("QWEN_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.base_url = os.getenv(
            "QWEN_API_BASE_URL",
            os.getenv("OPENAI_API_BASE", "https://api.qwen.com/v1/chat/completions"),
        )
        self.ollama_timeout = int(os.getenv("OLLAMA_TIMEOUT", "600"))

        if not self.use_ollama and not self.api_key:
            raise RuntimeError(
                "Missing LLM API key. Set QWEN_API_KEY or OPENAI_API_KEY in the environment, "
                "or set USE_OLLAMA=true to use a local Ollama model."
            )

    def _parse_ollama_response(self, response: requests.Response) -> str:
        response.raise_for_status()
        payload = response.json()
        if "choices" in payload and payload["choices"]:
            message = payload["choices"][0].get("message", {})
            if isinstance(message, dict):
                return message.get("content", "")
        if "response" in payload:
            return payload["response"]
        if "text" in payload:
            return payload["text"]
        if "output" in payload:
            return payload["output"]
        return json.dumps(payload)

    def _parse_remote_response(self, response: requests.Response) -> str:
        response.raise_for_status()
        payload = response.json()
        if "choices" in payload and payload["choices"]:
            message = payload["choices"][0].get("message", {})
            if isinstance(message, dict):
                return message.get("content", "")
        if "data" in payload and payload["data"]:
            return payload["data"][0].get("text", "")
        return json.dumps(payload)

    def _available_models(self) -> list[str]:
        try:
            response = requests.get(f"{self.ollama_api_base}/models", timeout=10)
            response.raise_for_status()
            payload = response.json()
            return [item.get("id") for item in payload.get("data", []) if item.get("id")]
        except requests.RequestException:
            return []

    def _choose_fallback_model(self, available: list[str]) -> None:
        preferred = [self.model, "qwen3.5:0.8b", "qwen3:0.8b", "qwen2:latest"]
        for candidate in preferred:
            if candidate in available:
                self.model = candidate
                return
        self.model = available[0]

    def ping(self) -> bool:
        if self.use_ollama:
            url = f"{self.ollama_api_base}/models/{self.model}"
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    return True
                if response.status_code == 404:
                    available = self._available_models()
                    if available:
                        self._choose_fallback_model(available)
                        response = requests.get(f"{self.ollama_api_base}/models/{self.model}", timeout=10)
                        return response.status_code == 200
                return False
            except requests.RequestException:
                return False
        if self.api_key:
            try:
                response = requests.get(self.base_url, timeout=10, headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                })
                return response.status_code < 500
            except requests.RequestException:
                return False
        return False

    def _extract_json(self, text: str) -> Any:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            json_text_match = re.search(r"\{.*\}", text, re.S)
            if json_text_match:
                return json.loads(json_text_match.group(0))
            raise

    def _ollama_request(self, messages: List[Dict[str, str]], temperature: float) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "top_p": 0.95,
        }
        url = f"{self.ollama_api_base}/chat/completions"
        headers = {"Content-Type": "application/json"}
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=self.ollama_timeout)
        except requests.RequestException as exc:
            raise RuntimeError(
                f"Ollama request failed for model '{self.model}' on {self.ollama_server}: {exc}. "
                "Verify Ollama is running, the model is loaded, and consider increasing OLLAMA_TIMEOUT."
            ) from exc
        return self._parse_ollama_response(response)

    def _remote_request(self, messages: List[Dict[str, str]], temperature: float) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "top_p": 0.95,
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        response = requests.post(self.base_url, json=payload, headers=headers, timeout=120)
        return self._parse_remote_response(response)

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.2) -> str:
        if self.use_ollama:
            return self._ollama_request(messages, temperature)
        return self._remote_request(messages, temperature)

    def chat_json(self, messages: List[Dict[str, str]], temperature: float = 0.2) -> Any:
        raw = self.chat(messages, temperature=temperature)
        return self._extract_json(raw)
