"""Server-only Claude Messages API adapter with validated structured responses."""
import json
import logging
import time
import httpx
from app.core.config import settings
from app.modules.audit.service import AuditService

logger = logging.getLogger('votoseguro.ai.claude')


class AnthropicClient:
    @staticmethod
    async def call_structured(prompt, schema_cls, fallback_fn, system_instruction='',
        function_name='ELECTORAL_ASSISTANT', organization_id=None, election_id=None,
        db=None, sanitized_summary='Asistencia electoral', images_base64=None, **_kwargs):
        started = time.perf_counter()
        result = None
        if settings.ANTHROPIC_API_KEY:
            content = [{'type':'image','source':{'type':'base64','media_type':item['mime_type'],'data':item['data']}}
                for item in (images_base64 or [])]
            content.append({'type':'text','text':prompt})
            payload = {
                'model':settings.ANTHROPIC_MODEL, 'max_tokens':1600,
                'system':system_instruction or 'Asiste con neutralidad y usa únicamente los datos proporcionados.',
                'messages':[{'role':'user','content':content}],
                'tools':[{'name':'electoral_response','description':'Respuesta electoral validada',
                    'input_schema':schema_cls.model_json_schema()}],
                'tool_choice':{'type':'tool','name':'electoral_response'},
            }
            try:
                async with httpx.AsyncClient(timeout=settings.ANTHROPIC_TIMEOUT_SECONDS) as client:
                    response = await client.post('https://api.anthropic.com/v1/messages', json=payload,
                        headers={'x-api-key':settings.ANTHROPIC_API_KEY,'anthropic-version':'2023-06-01'})
                    response.raise_for_status()
                    parts = response.json().get('content',[])
                    tool = next((p for p in parts if p.get('type')=='tool_use' and p.get('name')=='electoral_response'),None)
                    if tool:
                        result = schema_cls.model_validate(tool['input'])
                    else:
                        from app.ai.client import extract_first_json_object
                        text = ''.join(p.get('text','') for p in parts if p.get('type')=='text')
                        result = schema_cls.model_validate_json(extract_first_json_object(text))
            except httpx.HTTPStatusError as error:
                logger.warning('Claude %s: HTTP %s', function_name, error.response.status_code)
            except Exception as error:
                # Do not log prompts, images, headers or provider response bodies.
                logger.warning('Claude %s: %s', function_name, type(error).__name__)
        success = result is not None
        if not success:
            result = fallback_fn()
        elapsed = int((time.perf_counter()-started)*1000)
        source = 'ANTHROPIC_API' if success else 'DETERMINISTIC_FALLBACK'
        for field,value in [('ai_source',source),('model_name',settings.ANTHROPIC_MODEL if success else source),
            ('model_used',settings.ANTHROPIC_MODEL if success else source),('latency_ms',elapsed)]:
            if hasattr(result,field):setattr(result,field,value)
        if db:
            await AuditService.log_ai_call(db=db, organization_id=organization_id, election_id=election_id,
                function_name=function_name,model_name=settings.ANTHROPIC_MODEL if success else source,
                duration_ms=elapsed,status='SUCCESS_LLM' if success else 'FALLBACK_DETERMINISTIC',summary=sanitized_summary)
        return result

    @staticmethod
    async def probe():
        if not settings.ANTHROPIC_API_KEY:
            return {'online':False,'available_models':[],'latency_ms':None}
        started=time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response=await client.get('https://api.anthropic.com/v1/models',params={'limit':1},
                    headers={'x-api-key':settings.ANTHROPIC_API_KEY,'anthropic-version':'2023-06-01'})
            return {'online':response.status_code==200,'available_models':[settings.ANTHROPIC_MODEL] if response.status_code==200 else [],
                'status_code':response.status_code,'latency_ms':round((time.perf_counter()-started)*1000,2)}
        except httpx.HTTPError:
            return {'online':False,'available_models':[],'latency_ms':None}
