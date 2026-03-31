import bpy


DESIGN_PROMPT = """【项目目标】
生成一个测试体块方案

【联网研究总结】
无

【图片风格总结】
无

【Markdown 文本总结】
无

【几何约束】
无

【默认类型策略】
如果用户没有明确要求住宅、别墅或其他居住类项目，请保持为通用建筑方案，不要默认推断为住宅/别墅。

【生成要求】
请基于以上信息生成建筑空间体量，优先保证功能合理、空间组织清晰、体量与环境协调，并将信息转译成 Blender 可执行的几何建模逻辑。

[Generation Scope Strategy]

This is a new_generation round. Default to concept-level massing unless the user clearly asks for facade articulation or detail.
Current scope = concept_massing. Focus on primary and secondary volumes, entry emphasis, roof silhouette, major voids, and only the necessary large openings. Avoid repeated windows, dense curtain-wall grids, louvers, railings, and similar high-frequency details unless explicitly requested.

[Generation Scope Strategy]

This is a new_generation round. Default to concept-level massing unless the user clearly asks for facade articulation or detail.
Current scope = concept_massing. Focus on primary and secondary volumes, entry emphasis, roof silhouette, major voids, and only the necessary large openings. Avoid repeated windows, dense curtain-wall grids, louvers, railings, and similar high-frequency details unless explicitly requested."""
GEOMETRY_SUMMARY = """No geometry summary."""
FALLBACK_REASON = """OpenAI codegen client is unavailable or OPENAI_API_KEY is missing."""


def generate_building():
    print("LLM generation did not succeed. This is a placeholder script.")
    print("Fallback reason:")
    print(FALLBACK_REASON)
    print("Design prompt:")
    print(DESIGN_PROMPT)
    print("Geometry summary:")
    print(GEOMETRY_SUMMARY)


generate_building()
