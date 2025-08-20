import httpx
import json
from typing import List, Dict, Optional, AsyncGenerator
from config import settings

class LLMClient:
    def __init__(self):
        self.base_url = settings.LLM_SERVER_URL
        self.timeout = httpx.Timeout(60.0)
    
    async def health_check(self) -> bool:
        """LLM 서버 상태 확인"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/health")
                return response.status_code == 200
        except Exception:
            return False
    
    async def chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        max_new_tokens: int = 256,
        temperature: float = 0.7,
        do_sample: bool = True
    ) -> Dict:
        """일반 채팅 완성 요청"""
        payload = {
            "messages": messages,
            "max_new_tokens": max_new_tokens,
            "temperature": temperature,
            "do_sample": do_sample
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/chat",
                json=payload
            )
            response.raise_for_status()
            return response.json()
    
    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        max_new_tokens: int = 256,
        temperature: float = 0.7,
        do_sample: bool = True
    ) -> AsyncGenerator[Dict, None]:
        """스트리밍 채팅 요청"""
        payload = {
            "messages": messages,
            "max_new_tokens": max_new_tokens,
            "temperature": temperature,
            "do_sample": do_sample
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/stream",
                json=payload
            ) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                        
                    if line.startswith("data: "):
                        data_content = line[6:]  # "data: " 제거
                        
                        if data_content == "[DONE]":
                            break
                            
                        try:
                            chunk_data = json.loads(data_content)
                            yield chunk_data
                        except json.JSONDecodeError:
                            continue

# 전역 LLM 클라이언트 인스턴스
llm_client = LLMClient()