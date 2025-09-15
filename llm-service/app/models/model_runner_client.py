import logging
import json
import os
from typing import Optional
from openai import AsyncOpenAI

# Configure logging
logger = logging.getLogger(__name__)


class ModelRunnerClient:
    """Client for Docker Model Runner using OpenAI-compatible API."""
    
    def __init__(self):
        self.client = None
        self.model_name = "shato/gemma-270m-finetuned"
        
        # Docker Model Runner endpoint - use environment variables with fallback detection
        container_endpoint = os.getenv("MODEL_RUNNER_URL", "http://model-runner.docker.internal/engines/llama.cpp/v1")
        host_endpoint = os.getenv("MODEL_RUNNER_FALLBACK_URL", "http://localhost:11434/v1")
        
        # Try to detect if we're in a container (unless explicitly overridden)
        if os.getenv("MODEL_RUNNER_URL"):
            # Explicit URL provided via environment variable
            self.base_url = container_endpoint
            logger.info(f"[LLM-SERVICE] Using explicit MODEL_RUNNER_URL: {self.base_url}")
        elif os.path.exists("/.dockerenv"):
            self.base_url = container_endpoint
            logger.info(f"[LLM-SERVICE] Detected container environment, using: {self.base_url}")
        else:
            self.base_url = host_endpoint
            logger.info(f"[LLM-SERVICE] Detected host environment, using: {self.base_url}")
        
        self.initialize_client()
        
    def initialize_client(self):
        """Initialize the OpenAI client for Model Runner."""
        try:
            logger.info(f"[LLM-SERVICE] Initializing Docker Model Runner client")
            logger.info(f"[LLM-SERVICE] Endpoint: {self.base_url}")
            logger.info(f"[LLM-SERVICE] Target model: {self.model_name}")
            
            # Initialize AsyncOpenAI client pointing to Model Runner
            self.client = AsyncOpenAI(
                base_url=self.base_url,
                api_key="dummy-key",  # Model Runner doesn't require real API key
            )
            
            logger.info("[LLM-SERVICE-SUCCESS] Model Runner client initialized successfully")
            
        except Exception as e:
            logger.error(f"[LLM-SERVICE-ERROR] Failed to initialize Model Runner client: {str(e)}")
            raise
    
    async def generate_response(self, user_input: str, system_prompt: str = "", retry_context: str = None) -> str:
        """
        Generate a response using fine-tuned SHATO model.
        
        Args:
            user_input: The user's message
            system_prompt: Clean system prompt defining SHATO's role
            retry_context: Optional error message from validator for self-correction
            
        Returns:
            Generated response text (should be JSON with robot command)
        """
        if self.client is None:
            raise RuntimeError("Model Runner client not initialized. Call initialize_client() first.")
        
        try:
            # Build user content with retry context if present (matches training format)
            if retry_context:
                user_content = f"{user_input}\n\nPrevious error: {retry_context}"
            else:
                user_content = user_input
            
            # Use proper conversation format that matches fine-tuning
            messages = [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user", 
                    "content": user_content
                }
            ]
            
            logger.info(f"[LLM-SERVICE] Sending request to fine-tuned SHATO model: {user_input}")
            logger.info(f"[LLM-SERVICE] System prompt length: {len(system_prompt)} chars")
            if retry_context:
                logger.info(f"[LLM-SERVICE] Retry context: {retry_context}")
            logger.info(f"[LLM-SERVICE] User content preview: {user_content[:200]}...")
            
            # Call Model Runner via OpenAI-compatible API with structured output
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=512,  # Increased for better responses
                temperature=0.1,  # Very low for consistent JSON output
                response_format={"type": "json_object"},  # Force pure JSON output
                stream=False
            )
            
            # Extract the response content
            generated_text = response.choices[0].message.content
            
            logger.info(f"[LLM-SERVICE-SUCCESS] Received response from Model Runner")
            logger.debug(f"[LLM-SERVICE] Generated text: {generated_text}")
            
            return generated_text.strip()
            
        except Exception as e:
            logger.error(f"[LLM-SERVICE-ERROR] Model Runner generation failed: {str(e)}")
            return json.dumps({
                "response": "I'm sorry, I encountered an error processing your request.",
                "command": None,
                "command_params": None
            })
    
    def is_loaded(self) -> bool:
        """Check if the Model Runner client is ready."""
        return self.client is not None
    
    async def health_check(self) -> dict:
        """Check Model Runner health and model availability."""
        try:
            if self.client is None:
                return {
                    "model_runner_healthy": False,
                    "error": "Client not initialized"
                }
            
            # Try a simple completion to verify the model is working
            test_response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10,
                temperature=0.1
            )
            
            return {
                "model_runner_healthy": True,
                "model_name": self.model_name,
                "endpoint": self.base_url,
                "test_response_length": len(test_response.choices[0].message.content)
            }
            
        except Exception as e:
            logger.error(f"[LLM-SERVICE] Model Runner health check failed: {str(e)}")
            return {
                "model_runner_healthy": False,
                "error": str(e)
            }