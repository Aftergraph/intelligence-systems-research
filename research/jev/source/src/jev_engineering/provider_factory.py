"""Compatibility re-export for the canonical provider factory."""

from .providers.factory import LiveProviderFactory

ProviderFactory = LiveProviderFactory
ProviderConfigurationError = RuntimeError

__all__ = ["LiveProviderFactory", "ProviderFactory", "ProviderConfigurationError"]
