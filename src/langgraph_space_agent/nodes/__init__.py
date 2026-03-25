from __future__ import annotations

from .base import DesignAgentNodesBase
from .node1_collect_requirements import Node1CollectRequirementsMixin
from .node2_internet_research import Node2InternetResearchMixin
from .node3_image_analysis import Node3ImageAnalysisMixin
from .node4_markdown_analysis import Node4MarkdownAnalysisMixin
from .node5_geometry_constraints import Node5GeometryConstraintsMixin
from .node6_brief_refinement import Node6BriefRefinementMixin
from .node6_prompt_synthesis import Node6PromptSynthesisMixin
from .node7_script_generation import Node7ScriptGenerationMixin
from .node8_debug_diagnosis import Node8RuntimeDiagnosisMixin
from .node8_debug_repair import Node8RuntimeRepairMixin
from .node8_runtime_debug import Node8RuntimeDebugMixin


class DesignAgentNodes(
    Node1CollectRequirementsMixin,
    Node2InternetResearchMixin,
    Node3ImageAnalysisMixin,
    Node4MarkdownAnalysisMixin,
    Node5GeometryConstraintsMixin,
    Node6BriefRefinementMixin,
    Node6PromptSynthesisMixin,
    Node7ScriptGenerationMixin,
    Node8RuntimeDiagnosisMixin,
    Node8RuntimeRepairMixin,
    Node8RuntimeDebugMixin,
    DesignAgentNodesBase,
):
    pass


__all__ = ["DesignAgentNodes"]
