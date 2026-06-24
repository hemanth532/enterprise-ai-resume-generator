import json
from typing import Any, Dict, Optional, Callable, Awaitable

from .llm_client import LLMClient
from .tools import (
    TOOL_DESCRIPTIONS,
    profile_analysis_tool,
    ats_optimization_tool,
    resume_generation_tool,
    resume_review_tool,
)

ProgressCallback = Callable[[str, str, str], Awaitable[None]]


class ResumeAgent:
    def __init__(self, progress_callback: Optional[ProgressCallback] = None):
        self.llm = LLMClient()
        self.progress_callback = progress_callback

    def _system_prompt(self, stage: str) -> str:
        return (
            "You are an enterprise-grade AI resume generation agent. "
            "Use the provided resume content, analysis outputs, and tools to generate structured JSON answers. "
            "Always return valid JSON only, without markdown formatting."
        )

    async def _report_progress(self, step: str, status: str, detail: str) -> None:
        if self.progress_callback:
            await self.progress_callback(step, status, detail)

    def _build_messages(self, stage: str, user_prompt: str) -> list[dict[str, str]]:
        return [
            {"role": "system", "content": self._system_prompt(stage)},
            {"role": "user", "content": user_prompt},
        ]

    def _to_json(self, qwen_response: Any) -> Any:
        if isinstance(qwen_response, (dict, list)):
            return qwen_response
        if isinstance(qwen_response, str):
            return json.loads(qwen_response)
        raise ValueError("LLM response could not be parsed as JSON")

    async def analyze_profile(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        await self._report_progress("profile_analysis", "running", "Analyzing resume profile content")
        tool_output = profile_analysis_tool(parsed)
        prompt = (
            "Analyze the resume paragraphs below and return a JSON object with keys:"
            " candidate_level, primary_domain, years_experience, skills. "
            "Use the tool output as a starting point and refine it for enterprise hiring standards.\n\n"
            f"Parsed paragraphs:\n{json.dumps(parsed.get('paragraphs', []), indent=2)}\n\n"
            f"Tool output:\n{json.dumps(tool_output, indent=2)}\n\n"
            "Output JSON only."
        )
        try:
            response = self.llm.chat_json(self._build_messages("profile_analysis", prompt), temperature=0.2)
            result = self._to_json(response)
        except Exception as exc:
            await self._report_progress(
                "profile_analysis",
                "failed",
                f"Profile analysis failed: {exc}",
            )
            raise
        await self._report_progress("profile_analysis", "completed", "Profile analysis complete")
        return result

    async def optimize_ats(self, parsed: Dict[str, Any], profile: Dict[str, Any]) -> Dict[str, Any]:
        await self._report_progress("ats_optimization", "running", "Optimizing resume for ATS keywords and score")
        tool_output = ats_optimization_tool(parsed, profile)
        prompt = (
            "Identify ATS keyword gaps and compute an ATS score from 0 to 100. "
            "Return JSON with keys: present_keywords, missing_keywords, ats_score, recommendation.\n\n"
            f"Parsed paragraphs:\n{json.dumps(parsed.get('paragraphs', []), indent=2)}\n\n"
            f"Profile data:\n{json.dumps(profile, indent=2)}\n\n"
            f"Tool output:\n{json.dumps(tool_output, indent=2)}\n\n"
            "Output JSON only."
        )
        try:
            response = self.llm.chat_json(self._build_messages("ats_optimization", prompt), temperature=0.2)
            result = self._to_json(response)
        except Exception as exc:
            await self._report_progress(
                "ats_optimization",
                "failed",
                f"ATS optimization failed: {exc}",
            )
            raise
        await self._report_progress("ats_optimization", "completed", "ATS optimization complete")
        return result

    async def write_resume(self, parsed: Dict[str, Any], profile: Dict[str, Any], ats: Dict[str, Any]) -> Dict[str, Any]:
        await self._report_progress("resume_generation", "running", "Generating the improved resume content")
        tool_output = resume_generation_tool(parsed, profile, ats)
        prompt = (
            "Generate an enterprise-grade resume summary, experience bullets, a skills section, and professional recommendations. "
            "Keep the tone formal and results-focused. Return JSON with keys: summary, experience_bullets, skills, recommendations.\n\n"
            f"Parsed paragraphs:\n{json.dumps(parsed.get('paragraphs', []), indent=2)}\n\n"
            f"Profile data:\n{json.dumps(profile, indent=2)}\n\n"
            f"ATS data:\n{json.dumps(ats, indent=2)}\n\n"
            f"Tool output:\n{json.dumps(tool_output, indent=2)}\n\n"
            "Output JSON only."
        )
        try:
            response = self.llm.chat_json(self._build_messages("resume_generation", prompt), temperature=0.2)
            result = self._to_json(response)
        except Exception as exc:
            await self._report_progress(
                "resume_generation",
                "failed",
                f"Resume generation failed: {exc}",
            )
            raise
        await self._report_progress("resume_generation", "completed", "Resume generation complete")
        return result

    async def review_resume(self, resume: Dict[str, Any]) -> Dict[str, Any]:
        await self._report_progress("resume_review", "running", "Reviewing generated resume content")
        tool_output = resume_review_tool(resume)
        prompt = (
            "Review the generated resume content for grammar, consistency, enterprise professionalism, and formatting. "
            "Return JSON with keys: passed, issues, suggestions.\n\n"
            f"Resume output:\n{json.dumps(resume, indent=2)}\n\n"
            f"Tool output:\n{json.dumps(tool_output, indent=2)}\n\n"
            "Output JSON only."
        )
        try:
            response = self.llm.chat_json(self._build_messages("resume_review", prompt), temperature=0.2)
            result = self._to_json(response)
        except Exception as exc:
            await self._report_progress(
                "resume_review",
                "failed",
                f"Resume review failed: {exc}",
            )
            raise
        await self._report_progress("resume_review", "completed", "Resume review complete")
        return result


async def run_pipeline(parsed: Dict[str, Any], progress_callback: Optional[ProgressCallback] = None) -> Dict[str, Any]:
    agent = ResumeAgent(progress_callback)
    profile = await agent.analyze_profile(parsed)
    ats = await agent.optimize_ats(parsed, profile)
    resume = await agent.write_resume(parsed, profile, ats)
    review = await agent.review_resume(resume)
    return {
        "profile": profile,
        "ats": ats,
        "resume": resume,
        "review": review,
    }
