from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from .config import AgentSettings
from .nodes import DesignAgentNodes
from .state import AgentState


def build_design_agent_graph(settings: AgentSettings):
    nodes = DesignAgentNodes(settings)
    builder = StateGraph(AgentState)

    builder.add_node("node1_collect_requirements", nodes.node1_collect_requirements)
    builder.add_node("node2_internet_research", nodes.node2_internet_research)
    builder.add_node("node3_image_analysis", nodes.node3_image_analysis)
    builder.add_node("node4_markdown_analysis", nodes.node4_markdown_analysis)
    builder.add_node("node5_geometry_constraints", nodes.node5_geometry_constraints)
    builder.add_node("node6_prompt_synthesis", nodes.node6_prompt_synthesis)
    builder.add_node("node7_script_generation", nodes.node7_script_generation)
    builder.add_node("node8_runtime_debug", nodes.node8_runtime_debug)

    builder.add_edge(START, "node1_collect_requirements")
    builder.add_conditional_edges(
        "node1_collect_requirements",
        lambda state: "end" if state.get("should_end") else "continue",
        {"end": END, "continue": "node2_internet_research"},
    )
    builder.add_edge("node2_internet_research", "node3_image_analysis")
    builder.add_edge("node3_image_analysis", "node4_markdown_analysis")
    builder.add_edge("node4_markdown_analysis", "node5_geometry_constraints")
    builder.add_edge("node5_geometry_constraints", "node6_prompt_synthesis")
    builder.add_edge("node6_prompt_synthesis", "node7_script_generation")
    builder.add_edge("node7_script_generation", "node8_runtime_debug")
    builder.add_edge("node8_runtime_debug", END)

    return builder.compile(checkpointer=MemorySaver())
