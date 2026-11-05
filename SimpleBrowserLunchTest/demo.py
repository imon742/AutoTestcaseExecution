import asyncio
import os

from browser_use import Agent, ChatOllama

# Override with:  $env:DEMO_MODEL = "qwen3:4b-instruct"
MODEL = os.environ.get("DEMO_MODEL", "gemma4:e2b-it-q4_K_M")


async def main():
    llm = ChatOllama(
        model=MODEL,
        timeout=600,
        ollama_options={"num_ctx": 16000, "temperature": 0},
    )
    agent = Agent(
        task="Go to wikipedia.org, search for 'Software testing', "
             "and report the first sentence of the article.",
        llm=llm,
        use_vision=False,
        # Local CPU models are slow: keep the prompt small and allow long LLM calls.
        flash_mode=True,
        use_thinking=False,
        max_actions_per_step=3,
        max_clickable_elements_length=8000,
        llm_timeout=480,
        step_timeout=600,
    )
    history = await agent.run(max_steps=15)
    print("\n=== RESULT ===\n", history.final_result())


if __name__ == "__main__":
    asyncio.run(main())
