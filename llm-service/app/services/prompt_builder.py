import os
import logging

# Configure logging
logger = logging.getLogger(__name__)


class PromptBuilder:
    """Builds system prompts for the fine-tuned Gemma 270M model.
    
    This class is responsible for loading and providing the system prompt
    that guides the fine-tuned model's behavior. The model has been trained
    on conversation data and no longer requires few-shot examples.
    """
    
    def __init__(self, prompts_dir: str = "prompts"):
        """Initialize the PromptBuilder with the prompts directory path.
        
        Args:
            prompts_dir: Directory containing the system_prompt.txt file
        """
        self.prompts_dir = prompts_dir
        self.system_prompt = ""
        
        self.load_system_prompt()
        
    def load_system_prompt(self):
        """Load the system prompt from the system_prompt.txt file.
        
        The system prompt defines the model's role and output format.
        It must match the format used during fine-tuning for optimal performance.
        
        Raises:
            Exception: If the system prompt file cannot be loaded
        """
        try:
            prompt_file = os.path.join(self.prompts_dir, "system_prompt.txt")
            
            with open(prompt_file, 'r', encoding='utf-8') as f:
                self.system_prompt = f.read().strip()
                
            logger.info("[LLM-SERVICE] System prompt loaded successfully")
            
        except Exception as e:
            logger.error(f"[LLM-SERVICE-ERROR] Failed to load system prompt: {str(e)}")
            raise
    
    def build_prompt(self, user_input: str, retry_context: str = None) -> str:
        """Build the system prompt for the fine-tuned model.
        
        Since we're using a fine-tuned model, we only need the system prompt
        that was used during training. The retry_context is handled separately
        in the user message by the model_runner_client.
        
        Args:
            user_input: The user's input (not used for system prompt)
            retry_context: Error context for retries (handled in user message)
            
        Returns:
            The system prompt string
        """
        return self.system_prompt
    
    def is_loaded(self) -> bool:
        """Check if the system prompt has been loaded successfully.
        
        Returns:
            True if system prompt is loaded, False otherwise
        """
        return bool(self.system_prompt)