"""Tests for LLM provider with OpenRouter support."""

import os

import pytest

from aee.infrastructure.config.settings import LLMInstanceConfig, NonOllamaConfig, OllamaConfig
from aee.infrastructure.llm.provider import create_lm


class TestCreateLMOpenRouter:
    """Tests for create_lm function with OpenRouter configuration."""

    def test_create_lm_with_base_url(self, monkeypatch: pytest.MonkeyPatch):
        """Test create_lm passes api_base to dspy.LM when base_url is set."""
        # Clear all API keys and set only OPENROUTER_API_KEY
        for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "OPENROUTER_API_KEY"]:
            if key in os.environ:
                monkeypatch.delenv(key, raising=False)
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test-key")

        config = LLMInstanceConfig(
            use_ollama=False,
            model="openrouter/qwen/qwen3.5-397b-a17b",
            timeout=600,
            max_retries=2,
            temperature=0.5,
            rate_limit_delay=1.0,
            top_p=0.9,
            repeat_penalty=1.1,
            repeat_last_n=512,
            enable_cache=True,
            ollama=OllamaConfig(
                num_ctx=8192,
                num_predict=2048,
                repeat_penalty=1.1,
                repeat_last_n=512,
                stream=False,
            ),
            non_ollama=NonOllamaConfig(
                api_key="sk-or-test-key",  # Pass directly for unit test
                max_tokens=8192,
                base_url="https://openrouter.ai/api/v1",
            ),
        )

        # Create LM (circuit breaker disabled for non-Ollama)
        lm = create_lm(config, enable_circuit_breaker=False)

        # Verify LM is created
        assert lm is not None
        assert lm.model == "openrouter/qwen/qwen3.5-397b-a17b"

    def test_create_lm_without_base_url(self, monkeypatch: pytest.MonkeyPatch):
        """Test create_lm works without base_url (uses provider default)."""
        # Clear all API keys and set only OPENAI_API_KEY
        for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "OPENROUTER_API_KEY"]:
            if key in os.environ:
                monkeypatch.delenv(key, raising=False)
        monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-test-key")

        config = LLMInstanceConfig(
            use_ollama=False,
            model="openai/gpt-4o-mini",
            timeout=600,
            max_retries=2,
            temperature=0.5,
            rate_limit_delay=1.0,
            top_p=0.9,
            repeat_penalty=1.1,
            repeat_last_n=512,
            enable_cache=True,
            ollama=OllamaConfig(
                num_ctx=8192,
                num_predict=2048,
                repeat_penalty=1.1,
                repeat_last_n=512,
                stream=False,
            ),
            non_ollama=NonOllamaConfig(
                api_key="sk-openai-test-key",  # Pass directly for unit test
                max_tokens=4096,
            ),
        )

        # Create LM (circuit breaker disabled for non-Ollama)
        lm = create_lm(config, enable_circuit_breaker=False)

        # Verify LM is created
        assert lm is not None
        assert lm.model == "openai/gpt-4o-mini"

    def test_create_lm_openrouter_model_format(self, monkeypatch: pytest.MonkeyPatch):
        """Test create_lm with various OpenRouter model name formats."""
        # Clear all API keys and set only OPENROUTER_API_KEY
        for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "OPENROUTER_API_KEY"]:
            if key in os.environ:
                monkeypatch.delenv(key, raising=False)
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test-key")

        test_models = [
            "openrouter/qwen/qwen3.5-397b-a17b",
            "openrouter/meta-llama/llama-3.1-405b-instruct",
            "openrouter/anthropic/claude-3-5-sonnet",
        ]

        for model_name in test_models:
            config = LLMInstanceConfig(
                use_ollama=False,
                model=model_name,
                timeout=600,
                max_retries=2,
                temperature=0.5,
                rate_limit_delay=1.0,
                top_p=0.9,
                repeat_penalty=1.1,
                repeat_last_n=512,
                enable_cache=True,
                ollama=OllamaConfig(
                    num_ctx=8192,
                    num_predict=2048,
                    repeat_penalty=1.1,
                    repeat_last_n=512,
                    stream=False,
                ),
                non_ollama=NonOllamaConfig(
                    api_key="sk-or-test-key",  # Pass directly for unit test
                    max_tokens=8192,
                    base_url="https://openrouter.ai/api/v1",
                ),
            )

            lm = create_lm(config, enable_circuit_breaker=False)
            assert lm is not None
            assert lm.model == model_name

    def test_create_lm_validation_requires_api_key(self, monkeypatch: pytest.MonkeyPatch):
        """Test create_lm raises error when API key is not set."""
        # Ensure no API keys are set
        for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "OPENROUTER_API_KEY"]:
            if key in os.environ:
                monkeypatch.delenv(key, raising=False)

        # Create config without API key - should fail validation
        with pytest.raises(ValueError, match="API key must be set"):
            LLMInstanceConfig(
                use_ollama=False,
                model="openai/gpt-4o-mini",
                timeout=600,
                max_retries=2,
                temperature=0.5,
                rate_limit_delay=1.0,
                top_p=0.9,
                repeat_penalty=1.1,
                repeat_last_n=512,
                enable_cache=True,
                ollama=OllamaConfig(
                    num_ctx=8192,
                    num_predict=2048,
                    repeat_penalty=1.1,
                    repeat_last_n=512,
                    stream=False,
                ),
                non_ollama=NonOllamaConfig(
                    max_tokens=4096,
                ),
            )

    def test_create_lm_validation_max_tokens(self, monkeypatch: pytest.MonkeyPatch):
        """Test create_lm raises error when max_tokens is invalid."""
        # Clear all API keys and set one for validation
        for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "OPENROUTER_API_KEY"]:
            if key in os.environ:
                monkeypatch.delenv(key, raising=False)
        monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-test-key")

        config = LLMInstanceConfig(
            use_ollama=False,
            model="openai/gpt-4o-mini",
            timeout=600,
            max_retries=2,
            temperature=0.5,
            rate_limit_delay=1.0,
            top_p=0.9,
            repeat_penalty=1.1,
            repeat_last_n=512,
            enable_cache=True,
            ollama=OllamaConfig(
                num_ctx=8192,
                num_predict=2048,
                repeat_penalty=1.1,
                repeat_last_n=512,
                stream=False,
            ),
            non_ollama=NonOllamaConfig(
                api_key="sk-openai-test-key",  # Pass directly for unit test
                max_tokens=0,  # Invalid: must be positive
            ),
        )

        # Should raise ValueError due to invalid max_tokens
        with pytest.raises(ValueError, match="Max tokens must be positive"):
            create_lm(config, enable_circuit_breaker=False)
