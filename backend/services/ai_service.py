from interpreter import interpreter
from typing import Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging
from fastapi import HTTPException, status
import os
import certifi
import ssl
import httpx
import urllib3

class AIService:
    _instance = None
    _executor = ThreadPoolExecutor(max_workers=10)  # Limit concurrent AI calls

    def __init__(self):
        # Configure SSL settings
        self._configure_ssl()
        
        # Initialize interpreter settings
        interpreter.auto_run = True  # Disable approval requirement
        interpreter.llm.model = "gpt-3.5-turbo"
        interpreter.llm.temperature = 0.7
        interpreter.llm.api_key = os.environ.get('OPENAI_API_KEY')
        interpreter.llm.supports_functions = True
        
        interpreter.custom_instructions = """
        You are 'Maddy', an AI assistant created by EY India GEN AI Engineers. Your primary focus is on:
        1. Supply chain analysis and optimization
        2. Root cause analysis (RCA)
        3. Predictive quality analysis (PQA)
        4. Data summarization and forecasting
        5. Machine learning insights

        Always maintain a professional tone while being helpful and precise in your responses.
        Focus on providing actionable insights and clear explanations.
        """

    def _configure_ssl(self):
        """Configure SSL settings for the environment"""
        try:
            cert_path = '/app/backend/certs/cert.crt'
            
            # Set SSL verification environment variables
            os.environ['REQUESTS_CA_BUNDLE'] = cert_path
            os.environ['SSL_CERT_FILE'] = cert_path
            os.environ['CURL_CA_BUNDLE'] = cert_path
            
            # Create a custom SSL context
            ssl_context = ssl.create_default_context(cafile=cert_path)
            ssl_context.verify_mode = ssl.CERT_REQUIRED
            ssl_context.check_hostname = True
            
            # Configure urllib3 to use our certificate
            urllib3.util.ssl_.DEFAULT_CERTS = cert_path
            
            # Configure httpx client with our certificate
            httpx.Client(verify=cert_path)
            
        except Exception as e:
            logging.error(f"Failed to configure SSL settings: {str(e)}")
            raise

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = AIService()
        return cls._instance

    async def get_ai_response(self, message: str, user_id: str) -> str:
        """
        Get AI response asynchronously using a thread pool to prevent blocking
        """
        try:
            # Run the interpreter in a separate thread to avoid blocking
            response = await asyncio.get_event_loop().run_in_executor(
                self._executor,
                self._get_interpreter_response,
                message
            )
            return response
        except Exception as e:
            logging.error(f"AI Service error for user {user_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate AI response"
            )

    def _get_interpreter_response(self, message: str) -> str:
        """
        Get response from interpreter in a synchronous manner
        """
        try:
            # Use chat method for single response
            response = interpreter.chat(message)
            
            # Extract the last assistant message
            if isinstance(response, list):
                for msg in reversed(response):
                    if msg.get('role') == 'assistant':
                        return msg.get('content', '')
            return str(response)
        except Exception as e:
            logging.error(f"Interpreter error: {str(e)}")
            logging.error("Detailed error information:", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate AI response"
            )