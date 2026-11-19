import httpx
import pytest
from pydantic import BaseModel
from app.ai.anthropic_client import AnthropicClient
from app.ai.client import LocalLlmEngine
from app.ai.gemini_client import GeminiExternalClient
from app.core.config import settings

class Reply(BaseModel):
    answer: str
    ai_source: str = ''
    model_name: str = ''
    latency_ms: int = 0

@pytest.mark.asyncio
async def test_claude_provider_routes_text_without_local_tunnel(monkeypatch):
    monkeypatch.setattr(settings,'AI_PROVIDER','ANTHROPIC')
    monkeypatch.setattr(settings,'ANTHROPIC_API_KEY','test-private-key')
    async def post(self,url,**kwargs):
        assert url == 'https://api.anthropic.com/v1/messages'
        assert kwargs['headers']['x-api-key']=='test-private-key'
        assert kwargs['json']['tool_choice']['name']=='electoral_response'
        return httpx.Response(200,json={'content':[{'type':'tool_use','name':'electoral_response','input':{'answer':'Consulta documentada'}}]},request=httpx.Request('POST',url))
    monkeypatch.setattr(httpx.AsyncClient,'post',post)
    result=await LocalLlmEngine.call_structured('Ayuda',Reply,lambda:Reply(answer='fallback'))
    assert result.answer=='Consulta documentada'
    assert result.ai_source=='ANTHROPIC_API'
    assert result.model_name==settings.ANTHROPIC_MODEL

@pytest.mark.asyncio
async def test_claude_failure_is_explicit_fallback(monkeypatch):
    monkeypatch.setattr(settings,'ANTHROPIC_API_KEY','test-private-key')
    async def post(self,url,**kwargs):
        return httpx.Response(401,json={'error':{'type':'authentication_error'}},request=httpx.Request('POST',url))
    monkeypatch.setattr(httpx.AsyncClient,'post',post)
    result=await AnthropicClient.call_structured('Ayuda',Reply,lambda:Reply(answer='Sin conexión'))
    assert result.ai_source=='DETERMINISTIC_FALLBACK'
    assert result.answer=='Sin conexión'

@pytest.mark.asyncio
async def test_external_report_uses_claude_with_same_schema(monkeypatch):
    monkeypatch.setattr(settings,'AI_PROVIDER','ANTHROPIC')
    monkeypatch.setattr(settings,'ANTHROPIC_API_KEY','test-private-key')
    async def post(self,url,**kwargs):
        return httpx.Response(200,json={'content':[{'type':'tool_use','name':'electoral_response','input':{'answer':'Informe'}}]},request=httpx.Request('POST',url))
    monkeypatch.setattr(httpx.AsyncClient,'post',post)
    result=await GeminiExternalClient.call_structured('Informe',Reply,lambda:Reply(answer='fallback'))
    assert result.ai_source=='ANTHROPIC_API'
