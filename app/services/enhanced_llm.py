"""
Enhanced LLM Service for MoneyPrinterTurbo Pro.

Provides multi-provider LLM support (OpenAI, Anthropic, Ollama, Azure),
template-aware prompt generation, streaming responses, retry with
exponential backoff, cost tracking, prompt chaining for long scripts,
and structured output parsing.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import (
    Any,
    AsyncGenerator,
    Callable,
    Dict,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Enums & Data Classes
# ---------------------------------------------------------------------------

class Provider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    AZURE = "azure"


@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class CostEntry:
    provider: str
    model: str
    usage: TokenUsage
    cost_usd: float
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMResponse:
    content: str
    usage: TokenUsage
    provider: str
    model: str
    latency_ms: float
    finish_reason: str = "stop"
    raw: Optional[Any] = None


@dataclass
class RetryConfig:
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    retryable_status_codes: tuple = (429, 500, 502, 503, 504)


@dataclass
class PromptTemplate:
    name: str
    system: str
    user: str
    variables: List[str] = field(default_factory=list)
    max_input_tokens: int = 4000
    output_format: Optional[str] = None


@dataclass
class ChainStep:
    template: PromptTemplate
    variable_mapping: Dict[str, str] = field(default_factory=dict)
    condition: Optional[Callable[[str], bool]] = None
    transform: Optional[Callable[[str], str]] = None


# ---------------------------------------------------------------------------
# Pricing per 1M tokens (input / output) – kept simple for demo
# ---------------------------------------------------------------------------

PRICING: Dict[str, Dict[str, float]] = {
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
    "claude-3-opus-20240229": {"input": 15.00, "output": 75.00},
    "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
}


def estimate_cost(model: str, usage: TokenUsage) -> float:
    """Estimate USD cost for a given model and token usage."""
    prices = PRICING.get(model, {"input": 1.00, "output": 3.00})
    input_cost = (usage.prompt_tokens / 1_000_000) * prices["input"]
    output_cost = (usage.completion_tokens / 1_000_000) * prices["output"]
    return round(input_cost + output_cost, 6)


# ---------------------------------------------------------------------------
# Abstract Provider
# ---------------------------------------------------------------------------

class BaseLLMProvider(ABC):
    """Base class every concrete provider must implement."""

    def __init__(self, provider: Provider, model: str, api_key: str = "",
                 base_url: str = "", timeout: int = 120):
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout

    @abstractmethod
    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False,
        **kwargs,
    ) -> Union[LLMResponse, AsyncGenerator[str, None]]:
        ...

    def _parse_usage(self, raw_usage: Any) -> TokenUsage:
        return TokenUsage(
            prompt_tokens=getattr(raw_usage, "prompt_tokens", 0),
            completion_tokens=getattr(raw_usage, "completion_tokens", 0),
            total_tokens=getattr(raw_usage, "total_tokens", 0),
        )


# ---------------------------------------------------------------------------
# Concrete Providers
# ---------------------------------------------------------------------------

class OpenAIProvider(BaseLLMProvider):
    """Provider wrapping the OpenAI Python SDK."""

    def __init__(self, model: str = "gpt-4o", api_key: str = "", **kwargs):
        super().__init__(Provider.OPENAI, model, api_key, **kwargs)
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from openai import AsyncOpenAI
            except ImportError as exc:
                raise ImportError(
                    "openai package is required: pip install openai"
                ) from exc
            self._client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url or None,
                timeout=self.timeout,
            )
        return self._client

    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False,
        **kwargs,
    ) -> Union[LLMResponse, AsyncGenerator[str, None]]:
        client = self._get_client()
        params: Dict[str, Any] = dict(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        params.update(kwargs)

        start = time.monotonic()

        if stream:
            return self._stream_response(client, params, start)

        resp = await client.chat.completions.create(**params)
        elapsed = (time.monotonic() - start) * 1000
        choice = resp.choices[0]
        usage = self._parse_usage(resp.usage)
        return LLMResponse(
            content=choice.message.content or "",
            usage=usage,
            provider=self.provider.value,
            model=self.model,
            latency_ms=elapsed,
            finish_reason=choice.finish_reason or "stop",
            raw=resp,
        )

    async def _stream_response(
        self, client: Any, params: Dict[str, Any], start: float
    ) -> AsyncGenerator[str, None]:
        params["stream"] = True
        resp = await client.chat.completions.create(**params)
        async for chunk in resp:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content


class AnthropicProvider(BaseLLMProvider):
    """Provider wrapping the Anthropic Python SDK."""

    def __init__(self, model: str = "claude-3-5-sonnet-20241022",
                 api_key: str = "", **kwargs):
        super().__init__(Provider.ANTHROPIC, model, api_key, **kwargs)
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from anthropic import AsyncAnthropic
            except ImportError as exc:
                raise ImportError(
                    "anthropic package is required: pip install anthropic"
                ) from exc
            self._client = AsyncAnthropic(
                api_key=self.api_key, timeout=self.timeout
            )
        return self._client

    def _convert_messages(
        self, messages: List[Dict[str, str]]
    ) -> tuple[str, List[Dict[str, str]]]:
        system_parts = []
        chat_msgs = []
        for m in messages:
            if m["role"] == "system":
                system_parts.append(m["content"])
            else:
                chat_msgs.append(m)
        return "\n".join(system_parts), chat_msgs

    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False,
        **kwargs,
    ) -> Union[LLMResponse, AsyncGenerator[str, None]]:
        client = self._get_client()
        system_text, chat_msgs = self._convert_messages(messages)
        start = time.monotonic()

        if stream:
            return self._stream(client, system_text, chat_msgs,
                                temperature, max_tokens)

        resp = await client.messages.create(
            model=self.model,
            system=system_text,
            messages=chat_msgs,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
        elapsed = (time.monotonic() - start) * 1000
        usage = TokenUsage(
            prompt_tokens=resp.usage.input_tokens,
            completion_tokens=resp.usage.output_tokens,
            total_tokens=resp.usage.input_tokens + resp.usage.output_tokens,
        )
        return LLMResponse(
            content=resp.content[0].text,
            usage=usage,
            provider=self.provider.value,
            model=self.model,
            latency_ms=elapsed,
            finish_reason=resp.stop_reason or "stop",
            raw=resp,
        )

    async def _stream(
        self, client: Any, system_text: str,
        messages: List[Dict[str, str]], temperature: float, max_tokens: int,
    ) -> AsyncGenerator[str, None]:
        async with client.messages.stream(
            model=self.model,
            system=system_text,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        ) as stream:
            async for text in stream.text_stream:
                yield text


class OllamaProvider(BaseLLMProvider):
    """Provider for local Ollama instances via HTTP API."""

    def __init__(self, model: str = "llama3", base_url: str = "http://localhost:11434",
                 **kwargs):
        super().__init__(Provider.OLLAMA, model, base_url=base_url, **kwargs)
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from openai import AsyncOpenAI
            except ImportError as exc:
                raise ImportError(
                    "openai package is required for Ollama: pip install openai"
                ) from exc
            self._client = AsyncOpenAI(
                base_url=f"{self.base_url}/v1",
                api_key="ollama",
                timeout=self.timeout,
            )
        return self._client

    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False,
        **kwargs,
    ) -> Union[LLMResponse, AsyncGenerator[str, None]]:
        client = self._get_client()
        params: Dict[str, Any] = dict(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        start = time.monotonic()

        if stream:
            return self._stream(client, params, start)

        resp = await client.chat.completions.create(**params)
        elapsed = (time.monotonic() - start) * 1000
        choice = resp.choices[0]
        usage = self._parse_usage(resp.usage) if resp.usage else TokenUsage()
        return LLMResponse(
            content=choice.message.content or "",
            usage=usage,
            provider=self.provider.value,
            model=self.model,
            latency_ms=elapsed,
            finish_reason=choice.finish_reason or "stop",
            raw=resp,
        )

    async def _stream(
        self, client: Any, params: Dict[str, Any], start: float
    ) -> AsyncGenerator[str, None]:
        params["stream"] = True
        resp = await client.chat.completions.create(**params)
        async for chunk in resp:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content


class AzureOpenAIProvider(BaseLLMProvider):
    """Provider for Azure OpenAI deployments."""

    def __init__(self, model: str = "gpt-4o", api_key: str = "",
                 azure_endpoint: str = "", api_version: str = "2024-06-01",
                 **kwargs):
        super().__init__(Provider.AZURE, model, api_key, **kwargs)
        self.azure_endpoint = azure_endpoint
        self.api_version = api_version
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from openai import AsyncAzureOpenAI
            except ImportError as exc:
                raise ImportError(
                    "openai package is required: pip install openai"
                ) from exc
            self._client = AsyncAzureOpenAI(
                api_key=self.api_key,
                azure_endpoint=self.azure_endpoint,
                api_version=self.api_version,
                timeout=self.timeout,
            )
        return self._client

    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False,
        **kwargs,
    ) -> Union[LLMResponse, AsyncGenerator[str, None]]:
        client = self._get_client()
        params: Dict[str, Any] = dict(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        start = time.monotonic()

        if stream:
            return self._stream(client, params, start)

        resp = await client.chat.completions.create(**params)
        elapsed = (time.monotonic() - start) * 1000
        choice = resp.choices[0]
        usage = self._parse_usage(resp.usage) if resp.usage else TokenUsage()
        return LLMResponse(
            content=choice.message.content or "",
            usage=usage,
            provider=self.provider.value,
            model=self.model,
            latency_ms=elapsed,
            finish_reason=choice.finish_reason or "stop",
            raw=resp,
        )

    async def _stream(
        self, client: Any, params: Dict[str, Any], start: float
    ) -> AsyncGenerator[str, None]:
        params["stream"] = True
        resp = await client.chat.completions.create(**params)
        async for chunk in resp:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content


# ---------------------------------------------------------------------------
# Provider Factory
# ---------------------------------------------------------------------------

_PROVIDER_MAP: Dict[Provider, Type[BaseLLMProvider]] = {
    Provider.OPENAI: OpenAIProvider,
    Provider.ANTHROPIC: AnthropicProvider,
    Provider.OLLAMA: OllamaProvider,
    Provider.AZURE: AzureOpenAIProvider,
}


def create_provider(
    provider: Union[str, Provider],
    model: str = "",
    api_key: str = "",
    **kwargs,
) -> BaseLLMProvider:
    """Factory: instantiate the right provider class."""
    if isinstance(provider, str):
        provider = Provider(provider)
    cls = _PROVIDER_MAP[provider]
    if not model:
        defaults = {
            Provider.OPENAI: "gpt-4o",
            Provider.ANTHROPIC: "claude-3-5-sonnet-20241022",
            Provider.OLLAMA: "llama3",
            Provider.AZURE: "gpt-4o",
        }
        model = defaults[provider]
    return cls(model=model, api_key=api_key, **kwargs)


# ---------------------------------------------------------------------------
# Prompt Template Registry
# ---------------------------------------------------------------------------

class TemplateRegistry:
    """Central registry for prompt templates."""

    def __init__(self):
        self._templates: Dict[str, PromptTemplate] = {}

    def register(self, template: PromptTemplate) -> None:
        self._templates[template.name] = template
        logger.debug("Registered prompt template: %s", template.name)

    def get(self, name: str) -> PromptTemplate:
        if name not in self._templates:
            raise KeyError(f"Template '{name}' not found")
        return self._templates[name]

    def render(self, name: str, **variables: Any) -> tuple[str, str]:
        """Render a template with the supplied variables, return (system, user)."""
        tmpl = self.get(name)
        missing = [v for v in tmpl.variables if v not in variables]
        if missing:
            raise ValueError(f"Missing template variables: {missing}")
        system = tmpl.system.format(**variables)
        user = tmpl.user.format(**variables)
        return system, user

    def list_templates(self) -> List[str]:
        return list(self._templates.keys())


# ---------------------------------------------------------------------------
# Structured Output Parser
# ---------------------------------------------------------------------------

class StructuredOutputParser:
    """Parse LLM responses into structured Python objects."""

    @staticmethod
    def parse_json(text: str) -> Any:
        """Extract and parse the first JSON object/array from *text*."""
        # Try fenced code block first
        match = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
        if match:
            text = match.group(1).strip()
        # Try direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        # Try finding the first { or [
        for start_char, end_char in [("{", "}"), ("[", "]")]:
            start = text.find(start_char)
            if start == -1:
                continue
            depth = 0
            for i in range(start, len(text)):
                if text[i] == start_char:
                    depth += 1
                elif text[i] == end_char:
                    depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start : i + 1])
                    except json.JSONDecodeError:
                        break
        raise ValueError("No valid JSON found in LLM response")

    @staticmethod
    def parse_pydantic(text: str, model_cls: Type[T]) -> T:
        """Parse *text* into a Pydantic model instance."""
        data = StructuredOutputParser.parse_json(text)
        if hasattr(model_cls, "model_validate"):
            return model_cls.model_validate(data)
        return model_cls(**data)

    @staticmethod
    def extract_sections(text: str) -> Dict[str, str]:
        """Split markdown-style section headers into a dict."""
        sections: Dict[str, str] = {}
        pattern = re.compile(r"^#{1,3}\s+(.+)$", re.MULTILINE)
        matches = list(pattern.finditer(text))
        for i, m in enumerate(matches):
            key = m.group(1).strip().lower().replace(" ", "_")
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            sections[key] = text[start:end].strip()
        if not sections:
            sections["default"] = text.strip()
        return sections


# ---------------------------------------------------------------------------
# Cost Tracker
# ---------------------------------------------------------------------------

class CostTracker:
    """Aggregate cost tracking across calls."""

    def __init__(self):
        self._entries: List[CostEntry] = []

    def record(self, entry: CostEntry) -> None:
        self._entries.append(entry)

    def add(
        self, provider: str, model: str, usage: TokenUsage
    ) -> CostEntry:
        cost = estimate_cost(model, usage)
        entry = CostEntry(
            provider=provider, model=model, usage=usage, cost_usd=cost
        )
        self.record(entry)
        return entry

    @property
    def total_cost(self) -> float:
        return round(sum(e.cost_usd for e in self._entries), 6)

    def by_provider(self) -> Dict[str, float]:
        result: Dict[str, float] = {}
        for e in self._entries:
            result[e.provider] = round(result.get(e.provider, 0) + e.cost_usd, 6)
        return result

    def by_model(self) -> Dict[str, float]:
        result: Dict[str, float] = {}
        for e in self._entries:
            result[e.model] = round(result.get(e.model, 0) + e.cost_usd, 6)
        return result

    def summary(self) -> Dict[str, Any]:
        return {
            "total_cost_usd": self.total_cost,
            "total_calls": len(self._entries),
            "by_provider": self.by_provider(),
            "by_model": self.by_model(),
        }

    def reset(self) -> None:
        self._entries.clear()


# ---------------------------------------------------------------------------
# Retry Logic
# ---------------------------------------------------------------------------

async def _retry_with_backoff(
    fn: Callable,
    retry_config: RetryConfig,
    on_retry: Optional[Callable[[int, Exception], None]] = None,
) -> Any:
    """Execute *fn* with exponential backoff retry."""
    last_exc: Optional[Exception] = None
    for attempt in range(retry_config.max_retries + 1):
        try:
            return await fn()
        except Exception as exc:
            last_exc = exc
            if attempt == retry_config.max_retries:
                raise
            # Check for retryable HTTP status
            status = getattr(exc, "status_code", None) or getattr(
                getattr(exc, "response", None), "status_code", None
            )
            if status and status not in retry_config.retryable_status_codes:
                raise
            delay = min(
                retry_config.base_delay
                * (retry_config.exponential_base ** attempt),
                retry_config.max_delay,
            )
            logger.warning(
                "Retry %d/%d after %.1fs: %s",
                attempt + 1,
                retry_config.max_retries,
                delay,
                exc,
            )
            if on_retry:
                on_retry(attempt + 1, exc)
            await asyncio.sleep(delay)
    raise last_exc  # type: ignore[misc]


# ---------------------------------------------------------------------------
# EnhancedLLM – the main façade
# ---------------------------------------------------------------------------

class EnhancedLLM:
    """
    High-level LLM service for MoneyPrinterTurbo Pro.

    Supports multiple providers, prompt templates, streaming, retries,
    cost tracking, prompt chaining, and structured output parsing.
    """

    def __init__(
        self,
        provider: Union[str, Provider] = Provider.OPENAI,
        model: str = "",
        api_key: str = "",
        retry_config: Optional[RetryConfig] = None,
        cost_tracker: Optional[CostTracker] = None,
        template_registry: Optional[TemplateRegistry] = None,
        **provider_kwargs,
    ):
        self.provider_name = provider
        self.model = model
        self.api_key = api_key
        self.provider = create_provider(
            provider, model=model, api_key=api_key, **provider_kwargs
        )
        self.retry_config = retry_config or RetryConfig()
        self.cost_tracker = cost_tracker or CostTracker()
        self.templates = template_registry or TemplateRegistry()
        self.parser = StructuredOutputParser()
        self._default_temperature = 0.7
        self._default_max_tokens = 2048
        self._hooks: Dict[str, List[Callable]] = {
            "before_generate": [],
            "after_generate": [],
            "on_error": [],
        }
        logger.info(
            "EnhancedLLM initialized: provider=%s model=%s",
            self.provider.provider.value,
            self.provider.model,
        )

    # -- Configuration helpers -------------------------------------------

    def set_defaults(self, temperature: float = 0.7,
                     max_tokens: int = 2048) -> None:
        self._default_temperature = temperature
        self._default_max_tokens = max_tokens

    def add_hook(self, event: str, fn: Callable) -> None:
        if event not in self._hooks:
            raise ValueError(f"Unknown hook event: {event}")
        self._hooks[event].append(fn)

    def register_template(self, template: PromptTemplate) -> None:
        self.templates.register(template)

    # -- Core generation --------------------------------------------------

    async def generate(
        self,
        prompt: str = "",
        system: str = "",
        messages: Optional[List[Dict[str, str]]] = None,
        template: Optional[str] = None,
        template_vars: Optional[Dict[str, Any]] = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        stream: bool = False,
        **kwargs,
    ) -> Union[LLMResponse, AsyncGenerator[str, None]]:
        """
        Generate a completion.  Accepts either raw prompt/system, a
        pre-built messages list, or a template name.
        """
        # Build messages
        if messages is None:
            if template and template_vars:
                sys_text, usr_text = self.templates.render(
                    template, **template_vars
                )
            else:
                sys_text = system
                usr_text = prompt
            messages = []
            if sys_text:
                messages.append({"role": "system", "content": sys_text})
            if usr_text:
                messages.append({"role": "user", "content": usr_text})

        temp = temperature if temperature is not None else self._default_temperature
        mtok = max_tokens if max_tokens is not None else self._default_max_tokens

        # Fire hooks
        ctx = {"messages": messages, "temperature": temp, "max_tokens": mtok}
        for hook in self._hooks["before_generate"]:
            hook(ctx)

        if stream:
            return self.provider.generate(
                messages=ctx["messages"],
                temperature=ctx["temperature"],
                max_tokens=ctx["max_tokens"],
                stream=True,
                **kwargs,
            )

        async def _call():
            return await self.provider.generate(
                messages=ctx["messages"],
                temperature=ctx["temperature"],
                max_tokens=ctx["max_tokens"],
                stream=False,
                **kwargs,
            )

        response: LLMResponse = await _retry_with_backoff(
            _call, self.retry_config
        )

        # Track cost
        self.cost_tracker.add(response.provider, response.model, response.usage)

        # Fire hooks
        for hook in self._hooks["after_generate"]:
            hook(response)

        return response

    # -- Convenience: generate from template -----------------------------

    async def generate_from_template(
        self, template_name: str, **variables: Any
    ) -> LLMResponse:
        return await self.generate(template=template_name,  # type: ignore[return-value]
                                   template_vars=variables)

    # -- Streaming convenience -------------------------------------------

    async def stream(
        self,
        prompt: str = "",
        system: str = "",
        template: Optional[str] = None,
        template_vars: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """Convenience wrapper returning an async text stream."""
        gen = await self.generate(
            prompt=prompt,
            system=system,
            template=template,
            template_vars=template_vars,
            stream=True,
            **kwargs,
        )
        async for chunk in gen:  # type: ignore[union-attr]
            yield chunk

    # -- Prompt chaining for long scripts --------------------------------

    async def chain(
        self,
        steps: List[ChainStep],
        initial_vars: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> List[LLMResponse]:
        """
        Execute a sequence of prompt templates, feeding the output of each
        step into the next as a variable.  Ideal for long video scripts
        that exceed a single context window.
        """
        variables = dict(initial_vars or {})
        responses: List[LLMResponse] = []
        total = len(steps)

        for idx, step in enumerate(steps):
            # Map prior outputs
            for var_name, source_key in step.variable_mapping.items():
                if source_key in variables:
                    continue
                # Dynamic mapping: "step_{n}_output"
                m = re.match(r"step_(\d+)_output", source_key)
                if m:
                    step_idx = int(m.group(1))
                    if step_idx < len(responses):
                        variables[source_key] = responses[step_idx].content

            # Condition check
            if step.condition and not step.condition(
                json.dumps(variables, default=str)
            ):
                logger.info("Chain step %d skipped by condition", idx)
                continue

            if progress_callback:
                progress_callback(idx, total, step.template.name)

            resp: LLMResponse = await self.generate(  # type: ignore[assignment]
                template=step.template.name,
                template_vars=variables,
            )

            content = resp.content
            if step.transform:
                content = step.transform(content)

            # Store output for downstream steps
            variables[f"step_{idx}_output"] = content
            responses.append(resp)

        return responses

    # -- Structured output helpers ---------------------------------------

    async def generate_json(
        self,
        prompt: str = "",
        system: str = "",
        model_cls: Optional[Type[T]] = None,
        **kwargs,
    ) -> Union[Any, T]:
        """Generate a completion and parse the response as JSON."""
        json_system = (system + "\n\nRespond ONLY with valid JSON.") if system \
            else "Respond ONLY with valid JSON."
        resp: LLMResponse = await self.generate(  # type: ignore[assignment]
            prompt=prompt, system=json_system, **kwargs
        )
        if model_cls:
            return self.parser.parse_pydantic(resp.content, model_cls)
        return self.parser.parse_json(resp.content)

    async def generate_sections(
        self, prompt: str, system: str = "", **kwargs
    ) -> Dict[str, str]:
        """Generate and parse markdown sections."""
        resp: LLMResponse = await self.generate(  # type: ignore[assignment]
            prompt=prompt, system=system, **kwargs
        )
        return self.parser.extract_sections(resp.content)

    # -- Cost queries ----------------------------------------------------

    def get_cost_summary(self) -> Dict[str, Any]:
        return self.cost_tracker.summary()

    def reset_costs(self) -> None:
        self.cost_tracker.reset()

    # -- Repr ------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"EnhancedLLM(provider={self.provider.provider.value}, "
            f"model={self.provider.model})"
        )


# ---------------------------------------------------------------------------
# Preset template library
# ---------------------------------------------------------------------------

def register_default_templates(registry: TemplateRegistry) -> None:
    """Register commonly-used video generation templates."""
    registry.register(PromptTemplate(
        name="video_script",
        system=(
            "You are an expert video scriptwriter. Write engaging, "
            "informative scripts for short-form video content."
        ),
        user=(
            "Write a {duration}-second video script about: {topic}.\n"
            "Tone: {tone}.\n"
            "Target audience: {audience}.\n"
            "Include natural pauses marked with [PAUSE]."
        ),
        variables=["duration", "topic", "tone", "audience"],
        output_format="script",
    ))

    registry.register(PromptTemplate(
        name="video_title",
        system="You are a viral content strategist.",
        user=(
            "Generate 5 catchy YouTube Shorts / TikTok titles for a "
            "video about: {topic}.\n"
            "Each title should be under 60 characters and use a hook."
        ),
        variables=["topic"],
        output_format="json_list",
    ))

    registry.register(PromptTemplate(
        name="video_description",
        system="You are a YouTube SEO expert.",
        user=(
            "Write an SEO-optimized description for a {duration}-second "
            "video titled '{title}'.\n"
            "Keywords: {keywords}.\n"
            "Include relevant hashtags at the end."
        ),
        variables=["duration", "title", "keywords"],
        output_format="text",
    ))

    registry.register(PromptTemplate(
        name="scene_breakdown",
        system="You are a video production planner.",
        user=(
            "Break the following script into individual scenes with "
            "visual descriptions for each.\n\n"
            "Script:\n{script}\n\n"
            "Return a JSON array where each element has: "
            '"scene_number", "narration", "visual_description", '
            '"duration_seconds".'
        ),
        variables=["script"],
        output_format="json",
    ))

    registry.register(PromptTemplate(
        name="script_chunk_outline",
        system=(
            "You are a structured content planner. You produce numbered "
            "outlines for long video scripts."
        ),
        user=(
            "Create a detailed outline for a {total_duration}-second "
            "video about: {topic}.\n"
            "The outline should have {num_chunks} main sections.\n"
            "For each section provide: heading, key points (3-5), "
            "suggested duration.\n"
            "Return as JSON array."
        ),
        variables=["total_duration", "topic", "num_chunks"],
        output_format="json",
    ))


# ---------------------------------------------------------------------------
# Module-level convenience
# ---------------------------------------------------------------------------

def get_default_llm(
    provider: str = "openai",
    model: str = "",
    api_key: str = "",
    **kwargs,
) -> EnhancedLLM:
    """Create an EnhancedLLM with default templates pre-loaded."""
    registry = TemplateRegistry()
    register_default_templates(registry)
    return EnhancedLLM(
        provider=provider,
        model=model,
        api_key=api_key,
        template_registry=registry,
        **kwargs,
    )
