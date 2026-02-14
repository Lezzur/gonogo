from typing import Optional
from schemas import ReconData, TechStack
from llm.client import LLMClient
from llm.prompt_loader import load_prompt


async def detect_tech_stack(
    recon_data: ReconData,
    user_provided: Optional[str],
    api_key: str,
    llm_provider: str = "gemini"
) -> TechStack:
    """Step 2: Detect tech stack from recon heuristics + LLM."""

    client = LLMClient(api_key, llm_provider)

    prompt = load_prompt(
        "tech_stack_detection",
        user_provided_stack=user_provided or "Not provided",
        framework_signatures=recon_data.framework_signatures,
        meta_tags=recon_data.meta_tags
    )

    result = await client.generate(prompt, model_tier="flash")

    # Add user-provided stack to result
    result["user_provided_stack"] = user_provided

    return TechStack(**result)
