import asyncio
import json
import base64
from typing import Optional, List, Dict, Any, Union
from pathlib import Path

import google.generativeai as genai
import anthropic

from config import GEMINI_PRO_MODEL, GEMINI_FLASH_MODEL, CLAUDE_MODEL


class LLMClient:
    """Unified LLM client supporting Gemini (primary) and Claude (secondary)."""

    def __init__(self, api_key: str, provider: str = "gemini"):
        self.provider = provider
        self.api_key = api_key

        if provider == "gemini":
            genai.configure(api_key=api_key)
        elif provider == "claude":
            self.anthropic = anthropic.Anthropic(api_key=api_key)

    async def generate(
        self,
        prompt: str,
        images: Optional[List[Union[str, Path]]] = None,
        model_tier: str = "pro",
        max_retries: int = 3,
        expect_json: bool = True
    ) -> Union[Dict[str, Any], str]:
        """
        Generate a response from the LLM.

        Args:
            prompt: The text prompt
            images: Optional list of image paths to include
            model_tier: "pro" or "flash" for Gemini
            max_retries: Number of retry attempts
            expect_json: Whether to parse response as JSON

        Returns:
            Parsed JSON dict or raw string
        """
        for attempt in range(max_retries):
            try:
                if self.provider == "gemini":
                    return await self._generate_gemini(prompt, images, model_tier, expect_json)
                else:
                    return await self._generate_claude(prompt, images, expect_json)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)

    async def _generate_gemini(
        self,
        prompt: str,
        images: Optional[List[Union[str, Path]]],
        model_tier: str,
        expect_json: bool
    ) -> Union[Dict[str, Any], str]:
        """Generate using Gemini API."""
        model_name = GEMINI_PRO_MODEL if model_tier == "pro" else GEMINI_FLASH_MODEL
        model = genai.GenerativeModel(model_name)

        contents = []

        # Add images if provided
        if images:
            for image_path in images:
                path = Path(image_path)
                if path.exists():
                    with open(path, "rb") as f:
                        image_data = f.read()
                    mime_type = "image/png" if path.suffix == ".png" else "image/jpeg"
                    contents.append({
                        "mime_type": mime_type,
                        "data": image_data
                    })

        contents.append(prompt)

        generation_config = {}
        if expect_json:
            generation_config["response_mime_type"] = "application/json"

        response = await asyncio.to_thread(
            model.generate_content,
            contents,
            generation_config=generation_config if generation_config else None
        )

        text = response.text

        if expect_json:
            # Clean potential markdown code blocks
            text = text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            return json.loads(text.strip())

        return text

    async def _generate_claude(
        self,
        prompt: str,
        images: Optional[List[Union[str, Path]]],
        expect_json: bool
    ) -> Union[Dict[str, Any], str]:
        """Generate using Claude API."""
        content = []

        # Add images if provided
        if images:
            for image_path in images:
                path = Path(image_path)
                if path.exists():
                    with open(path, "rb") as f:
                        image_data = base64.standard_b64encode(f.read()).decode("utf-8")
                    media_type = "image/png" if path.suffix == ".png" else "image/jpeg"
                    content.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data
                        }
                    })

        content.append({"type": "text", "text": prompt})

        response = await asyncio.to_thread(
            self.anthropic.messages.create,
            model=CLAUDE_MODEL,
            max_tokens=4096,
            messages=[{"role": "user", "content": content}]
        )

        text = response.content[0].text

        if expect_json:
            text = text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            return json.loads(text.strip())

        return text
