from .agents.agentic import run_pipeline as agentic_run_pipeline


async def run_pipeline(parsed, progress_callback=None):
    return await agentic_run_pipeline(parsed, progress_callback)
