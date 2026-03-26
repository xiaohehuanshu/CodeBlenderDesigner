from __future__ import annotations

import json
import re
import textwrap
from typing import Any

from ..tracing import trace_phase
from ..utils import clean_code_fence, compact_text, text_stats
from .base import PROMPT_COLLECTION_MAX_CHARS
from .codegen_shared import (
    CODEGEN_BATCH_COUNT_MAX,
    CODEGEN_BATCH_COUNT_MIN,
    CODEGEN_BATCH_HARD_LIMIT_CHARS,
    CODEGEN_PRIOR_CODE_MAX_CHARS,
    GENERATION_SCOPE_CONCEPT,
    GENERATION_SCOPE_DETAIL,
    GENERATION_SCOPE_FACADE,
)
from .node7_codegen_prompts import STAGED_FRAGMENT_SYSTEM_PROMPT


class Node7CodegenStagedMixin:
    @staticmethod
    def _build_helper_contract() -> str:
        return "\n".join(
            [
                "- `collection = ensure_collection(name)`：获取或创建集合。",
                "- `clear_collection_objects(collection)`：只清理该集合中的旧对象，不动场景其他对象。",
                "- `obj = add_box(name, location, size, collection, rotation=(0.0, 0.0, 0.0))`：创建基础盒体。",
                "- `obj = add_extruded_plan(name, plan_points, height, collection, base_z=0.0, bevel_width=0.0)`：由平面轮廓挤出体量。",
                "- `material = ensure_material(name, base_color, roughness=0.5, metallic=0.0)`：创建或复用材质。",
                "- `assign_material(obj, material)`：给对象分配材质。",
                "- `add_boolean_difference(target, cutter, keep_cutter=False)`：对目标执行布尔差集。",
                "- 已预定义变量：`collection`、`solid_mat`、`glass_mat`、`accent_mat`、`primary_masses`、`secondary_masses`。",
            ]
        )

    @staticmethod
    def _build_local_scaffold() -> str:
        return textwrap.dedent(
            """
            import bpy
            import bmesh
            import math
            import random
            from mathutils import Vector


            def ensure_collection(name):
                collection = bpy.data.collections.get(name)
                if collection is None:
                    collection = bpy.data.collections.new(name)
                    bpy.context.scene.collection.children.link(collection)
                return collection


            def clear_collection_objects(collection):
                for obj in list(collection.objects):
                    bpy.data.objects.remove(obj, do_unlink=True)


            def link_object(obj, collection):
                if collection.objects.get(obj.name) is None:
                    collection.objects.link(obj)
                for other in list(obj.users_collection):
                    if other != collection:
                        other.objects.unlink(obj)


            def apply_object_transforms(obj, apply_location=False):
                bpy.ops.object.select_all(action="DESELECT")
                obj.select_set(True)
                bpy.context.view_layer.objects.active = obj
                bpy.ops.object.transform_apply(location=apply_location, rotation=True, scale=True)
                bpy.ops.object.select_all(action="DESELECT")


            def ensure_material(name, base_color, roughness=0.5, metallic=0.0):
                material = bpy.data.materials.get(name)
                if material is None:
                    material = bpy.data.materials.new(name=name)
                material.use_nodes = True
                principled = material.node_tree.nodes.get("Principled BSDF")
                if principled is not None:
                    principled.inputs["Base Color"].default_value = base_color
                    principled.inputs["Roughness"].default_value = roughness
                    principled.inputs["Metallic"].default_value = metallic
                return material


            def assign_material(obj, material):
                if obj.data is None:
                    return
                if obj.data.materials:
                    obj.data.materials[0] = material
                else:
                    obj.data.materials.append(material)


            def add_box(name, location, size, collection, rotation=(0.0, 0.0, 0.0)):
                bpy.ops.mesh.primitive_cube_add(location=location, rotation=rotation)
                obj = bpy.context.active_object
                obj.name = name
                obj.scale = (size[0] * 0.5, size[1] * 0.5, size[2] * 0.5)
                apply_object_transforms(obj)
                link_object(obj, collection)
                return obj


            def add_extruded_plan(name, plan_points, height, collection, base_z=0.0, bevel_width=0.0):
                mesh = bpy.data.meshes.new(name)
                obj = bpy.data.objects.new(name, mesh)
                collection.objects.link(obj)

                bm = bmesh.new()
                verts = [bm.verts.new((float(x), float(y), float(base_z))) for x, y in plan_points]
                bm.verts.ensure_lookup_table()
                face = bm.faces.new(verts)
                bmesh.ops.recalc_face_normals(bm, faces=[face])
                extruded = bmesh.ops.extrude_face_region(bm, geom=[face])
                extruded_verts = [elem for elem in extruded["geom"] if isinstance(elem, bmesh.types.BMVert)]
                bmesh.ops.translate(bm, verts=extruded_verts, vec=Vector((0.0, 0.0, float(height))))
                bm.normal_update()
                bm.to_mesh(mesh)
                bm.free()

                if bevel_width > 0.0:
                    bevel = obj.modifiers.new(name="Bevel", type="BEVEL")
                    bevel.width = bevel_width
                    bevel.segments = 3
                    bevel.limit_method = "ANGLE"

                return obj


            def add_boolean_difference(target, cutter, keep_cutter=False):
                modifier = target.modifiers.new(name="BooleanCut", type="BOOLEAN")
                modifier.operation = "DIFFERENCE"
                modifier.solver = "EXACT"
                modifier.object = cutter
                bpy.ops.object.select_all(action="DESELECT")
                target.select_set(True)
                bpy.context.view_layer.objects.active = target
                bpy.ops.object.modifier_apply(modifier=modifier.name)
                bpy.ops.object.select_all(action="DESELECT")
                if not keep_cutter:
                    bpy.data.objects.remove(cutter, do_unlink=True)
                return target


            def generate_building():
                random.seed(7)
                collection = None
                solid_mat = None
                glass_mat = None
                accent_mat = None
                primary_masses = []
                secondary_masses = []

            __BATCH_BODIES__

                for obj in primary_masses + secondary_masses:
                    if obj is None:
                        continue
                    try:
                        obj.select_set(False)
                    except Exception:
                        pass
                return collection


            generate_building()
            """
        ).strip()

    @staticmethod
    def _build_batch_templates(batch_count: int) -> list[dict[str, Any]]:
        template_map = {
            1: [
                {
                    "id": 1,
                    "name": "full_massing",
                    "goal": "一次完成基础集合、主要材质、主次体量、入口与顶部收束，形成可继续迭代的首轮脚本主体。",
                    "done_when": "脚本已有清晰的主次体量、入口识别和顶部处理，且整体保持首轮概念量体优先的克制。",
                    "target_chars": 1600,
                }
            ],
            2: [
                {
                    "id": 1,
                    "name": "main_massing",
                    "goal": "完成集合、基础材质、基座与主控体量，建立主要轮廓和体量骨架。",
                    "done_when": "主集合、主材质、BaseMass 或 MainVolume 等核心对象已经建立。",
                    "target_chars": 1400,
                },
                {
                    "id": 2,
                    "name": "entry_top_finish",
                    "goal": "补足次级体量、入口识别、顶部处理和少量材质暗示。",
                    "done_when": "入口、顶部和次级体量关系已经完整，脚本达到可继续修改的稳定状态。",
                    "target_chars": 1300,
                },
            ],
            3: [
                {
                    "id": 1,
                    "name": "primary_setup",
                    "goal": "完成集合、基础材质、场景初始化和主控体量。",
                    "done_when": "primary_masses 已有核心对象，主轮廓与命名已建立。",
                    "target_chars": 1300,
                },
                {
                    "id": 2,
                    "name": "secondary_relations",
                    "goal": "补足次级体量、退台、切削或必要的布尔关系。",
                    "done_when": "主次体量关系完整，secondary_masses 已形成清晰层次。",
                    "target_chars": 1200,
                },
                {
                    "id": 3,
                    "name": "entry_roof_finish",
                    "goal": "补足入口识别、顶部处理、少量材质暗示和最终收束。",
                    "done_when": "入口、顶部和收尾完成，整体达到可继续迭代状态。",
                    "target_chars": 1100,
                },
            ],
        }
        batch_count = max(CODEGEN_BATCH_COUNT_MIN, min(CODEGEN_BATCH_COUNT_MAX, batch_count))
        return [dict(item) for item in template_map[batch_count]]

    def _build_default_codegen_plan(
        self,
        *,
        route_decision: str,
        refined_design_brief: str,
        generation_scope: str,
        geometry_summary: str,
    ) -> dict[str, Any]:
        complexity = 0
        if geometry_summary:
            complexity += 1
        if len(refined_design_brief) > 780:
            complexity += 1
        if len(refined_design_brief) > 1020:
            complexity += 1
        if generation_scope == GENERATION_SCOPE_FACADE:
            complexity += 1
        elif generation_scope == GENERATION_SCOPE_DETAIL:
            complexity += 2

        if complexity <= 0:
            batch_count = 1
            reason = "任务较简单，兜底分段可尝试单段完成。"
        elif complexity <= 2:
            batch_count = 2
            reason = "任务为中等复杂度，兜底分段拆成主控体量与收尾两段更稳妥。"
        else:
            batch_count = 3
            reason = "任务较复杂，兜底分段拆成主控、关系补强和收尾三段更稳妥。"

        min_batch_count = 2 if route_decision == "new_generation" else CODEGEN_BATCH_COUNT_MIN
        if route_decision == "new_generation" and generation_scope != GENERATION_SCOPE_CONCEPT:
            min_batch_count = max(min_batch_count, 3)
        batch_count = max(min_batch_count, min(CODEGEN_BATCH_COUNT_MAX, batch_count))
        batches = self._build_batch_templates(batch_count)
        if generation_scope == GENERATION_SCOPE_FACADE and batches:
            batches[-1] = {
                **batches[-1],
                "name": "facade_finish",
                "goal": "Preserve the massing and complete major openings, facade articulation, shading/canopy cues, and material relationships.",
                "done_when": "Facade-level expression is coherent without over-expanding into dense repeated detail.",
                "target_chars": 1200,
            }
            reason += " Facade scope keeps the staged fallback focused on massing first and facade articulation in the final batch."
        elif generation_scope == GENERATION_SCOPE_DETAIL and batches:
            batches[-1] = {
                **batches[-1],
                "name": "detail_finish",
                "goal": "Preserve the massing and facade logic, then add only the necessary detail-level articulation and finish materials.",
                "done_when": "Requested detail cues are present while the script remains controlled and patch-friendly.",
                "target_chars": 1200,
            }
            reason += " Detail scope keeps detail work until the final batch so fallback fragments stay shorter and more stable."

        return {
            "batch_count": batch_count,
            "reason": reason,
            "batches": batches,
        }

    @staticmethod
    def _extract_function_body(fragment: str) -> str:
        match = re.search(
            r"def\s+generate_building\s*\([^)]*\)\s*:\s*\n(?P<body>(?:[ \t]+.*(?:\n|$))*)",
            fragment,
        )
        if not match:
            return fragment
        return textwrap.dedent(match.group("body"))

    def _sanitize_fragment(self, fragment: str) -> str:
        fragment = clean_code_fence(fragment or "")
        fragment = fragment.replace("\r\n", "\n").replace("\r", "\n")
        fragment = self._extract_function_body(fragment)

        cleaned_lines: list[str] = []
        for raw_line in fragment.splitlines():
            stripped = raw_line.strip()
            if not stripped:
                cleaned_lines.append("")
                continue
            if stripped.startswith("```"):
                continue
            if stripped.lower() in {"python", "py"}:
                continue
            if re.match(r"^(import|from)\s+", stripped):
                continue
            if re.match(r"^def\s+", stripped):
                continue
            if stripped == "generate_building()":
                continue
            if stripped.startswith(("这里", "说明", "解释", "以下", "下面", "This ", "Here ")):
                cleaned_lines.append(f"# {stripped}")
                continue
            cleaned_lines.append(raw_line.rstrip())

        normalized = textwrap.dedent("\n".join(cleaned_lines)).strip("\n")
        normalized = re.sub(r"\n{3,}", "\n\n", normalized)
        return normalized.strip()

    @staticmethod
    def _indent_fragment(fragment: str) -> str:
        if not fragment.strip():
            return "    pass"
        return textwrap.indent(fragment.rstrip(), "    ")

    def _assemble_script(self, *, fragments: list[str]) -> str:
        scaffold = self._build_local_scaffold()
        batch_bodies = "\n\n".join(fragment.strip() for fragment in fragments if fragment and fragment.strip())
        return scaffold.replace("__BATCH_BODIES__", self._indent_fragment(batch_bodies)).strip() + "\n"

    @staticmethod
    def _compile_script(script: str) -> tuple[bool, str]:
        try:
            compile(script, "<generated_blender_script>", "exec")
        except SyntaxError as exc:
            return False, f"{exc.msg} (line {exc.lineno}, offset {exc.offset})"
        except Exception as exc:
            return False, str(exc)
        return True, ""

    @staticmethod
    def _build_prior_code_context(fragments: list[str], batches: list[dict[str, Any]]) -> str:
        if not fragments or not batches:
            return ""
        blocks: list[str] = []
        for batch, fragment in zip(batches, fragments):
            blocks.append(
                "\n".join(
                    [
                        f"[batch {batch['id']}] {batch['name']}",
                        fragment.strip(),
                    ]
                ).strip()
            )
        return compact_text("\n\n".join(blocks), CODEGEN_PRIOR_CODE_MAX_CHARS)

    def _build_batch_prompt(
        self,
        *,
        route_decision: str,
        current_user_input: str,
        refined_design_brief: str,
        generation_scope: str,
        geometry_summary: str,
        helper_contract: str,
        batch_plan: dict[str, Any],
        all_batches: list[dict[str, Any]],
        completed_batches: list[dict[str, Any]],
        completed_fragments: list[str],
    ) -> str:
        batch_index = int(batch_plan["id"])
        total_batches = len(all_batches)
        user_block = compact_text(current_user_input.strip(), PROMPT_COLLECTION_MAX_CHARS) or "<empty>"
        scope_directive = self._build_scope_directive(
            generation_scope=generation_scope,
            route_decision=route_decision,
        )
        sections = [
            f"你现在只编写第 {batch_index}/{total_batches} 段代码。",
            f"当前模式：{route_decision}",
            "",
            "当前轮用户输入：",
            user_block,
            "",
            "精炼后的 design_brief：",
            refined_design_brief,
            "",
            "Generation scope directive:",
            scope_directive,
        ]
        if geometry_summary:
            sections.extend(["", "几何与场地限制：", compact_text(geometry_summary, 1500)])
        sections.extend(
            [
                "",
                "总分段计划：",
                json.dumps(
                    {
                        "batch_count": total_batches,
                        "batches": [
                            {
                                "id": item["id"],
                                "name": item["name"],
                                "goal": item["goal"],
                                "done_when": item["done_when"],
                                "target_chars": item["target_chars"],
                            }
                            for item in all_batches
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                "",
                "当前批次职责：",
                f"- name: {batch_plan['name']}",
                f"- goal: {batch_plan['goal']}",
                f"- done_when: {batch_plan['done_when']}",
                f"- target_chars: {batch_plan['target_chars']}",
                f"- hard_limit_chars: {CODEGEN_BATCH_HARD_LIMIT_CHARS}",
                "",
                "可用辅助函数：",
                helper_contract,
            ]
        )

        if completed_batches:
            sections.extend(
                [
                    "",
                    "已完成批次：",
                    "\n".join(
                        f"- {item['id']}. {item['name']}: {item['goal']}" for item in completed_batches
                    ),
                    "",
                    "之前已经生成的代码：",
                    self._build_prior_code_context(completed_fragments, completed_batches),
                ]
            )
        else:
            sections.extend(["", "这是第一段代码，请从空白函数体开始补写。"])

        sections.extend(
            [
                "",
                "输出要求：",
                "1. 只输出当前批次新增的 Python 代码片段。",
                "2. 不要输出 import、def、generate_building()、return、解释或 Markdown。",
                "3. 只完成本批次职责，不要提前把后续批次全部写完。",
                "4. 如果前文已经创建了对象、变量或材质，请直接复用，而不是重写。",
                "5. 遵循 generation scope directive：默认先稳定体块与空间组织，仅在当前批次目标明确要求时再推进立面或细部。",
            ]
        )
        return "\n".join(sections).strip()

    def _generate_stage_fragment(self, *, stage_name: str, user_prompt: str) -> str:
        self._emit_substep("node7", stage_name, "started")
        self._emit_text_metrics(f"node7 {stage_name} prompt stats", user_prompt=user_prompt)
        with trace_phase(f"node7_script_generation.{stage_name}"):
            fragment = self.openai_codegen.client.chat_text(
                system_prompt=STAGED_FRAGMENT_SYSTEM_PROMPT,
                user_content=user_prompt,
                temperature=0.1,
            )
        fragment = self._sanitize_fragment(fragment)
        self._emit_tool_result_metrics(stage_name, fragment)
        return fragment

    def _run_staged_codegen(
        self,
        *,
        route_decision: str,
        current_user_input: str,
        refined_design_brief: str,
        generation_scope: str,
        geometry_summary: str,
    ) -> tuple[str, str, dict[str, Any]]:
        helper_contract = self._build_helper_contract()
        plan = self._build_default_codegen_plan(
            route_decision=route_decision,
            refined_design_brief=refined_design_brief,
            generation_scope=generation_scope,
            geometry_summary=geometry_summary,
        )
        plan_source = "local_heuristic"
        self._emit_substep(
            "node7",
            "staged_plan",
            "completed",
            f"batch_count={plan['batch_count']}, source={plan_source}",
        )
        self._emit_tool_result_metrics(
            "node7_codegen_plan",
            json.dumps(plan, ensure_ascii=False, indent=2),
        )

        fragments: list[str] = []
        completed_batches: list[dict[str, Any]] = []
        batch_metrics: list[dict[str, Any]] = []
        last_compiled_script = ""

        for batch in plan["batches"]:
            stage_name = f"batch{batch['id']}_{batch['name']}"
            batch_prompt = self._build_batch_prompt(
                route_decision=route_decision,
                current_user_input=current_user_input,
                refined_design_brief=refined_design_brief,
                generation_scope=generation_scope,
                geometry_summary=geometry_summary,
                helper_contract=helper_contract,
                batch_plan=batch,
                all_batches=plan["batches"],
                completed_batches=completed_batches,
                completed_fragments=fragments,
            )
            try:
                fragment = self._generate_stage_fragment(stage_name=stage_name, user_prompt=batch_prompt)
            except Exception as exc:
                if last_compiled_script:
                    self._emit_substep("node7", stage_name, "failed", str(exc))
                    self._emit(f"node7 {stage_name} failed, fallback to previous compiled script: {exc}")
                    return (
                        last_compiled_script,
                        "planned_codegen_partial_generation_fallback",
                        {
                            "plan_source": plan_source,
                            "plan": plan,
                            "completed_batch_count": len(completed_batches),
                            "batch_metrics": batch_metrics,
                            "failed_batch": batch["id"],
                            "failed_stage_name": stage_name,
                            "generation_error": str(exc),
                        },
                    )
                raise

            candidate_fragments = fragments + [fragment]
            candidate_script = self._assemble_script(fragments=candidate_fragments)
            compiles, compile_message = self._compile_script(candidate_script)
            batch_metric = {
                "id": batch["id"],
                "name": batch["name"],
                "target_chars": batch["target_chars"],
                "fragment": text_stats(fragment),
                "exceeds_hard_limit": len(fragment) > CODEGEN_BATCH_HARD_LIMIT_CHARS,
                "compile_ok": compiles,
            }
            if not compiles:
                batch_metric["compile_error"] = compile_message
                batch_metrics.append(batch_metric)
                if last_compiled_script:
                    self._emit_substep("node7", stage_name, "failed", f"compile_error={compile_message}")
                    self._emit(
                        f"node7 {stage_name} compile failed, fallback to previous compiled script: {compile_message}"
                    )
                    return (
                        last_compiled_script,
                        "planned_codegen_partial_compile_fallback",
                        {
                            "plan_source": plan_source,
                            "plan": plan,
                            "completed_batch_count": len(completed_batches),
                            "batch_metrics": batch_metrics,
                            "failed_batch": batch["id"],
                            "failed_stage_name": stage_name,
                            "compile_error": compile_message,
                        },
                    )
                raise RuntimeError(f"{stage_name} 组装后的脚本无法通过编译：{compile_message}")

            fragments = candidate_fragments
            completed_batches.append(batch)
            batch_metrics.append(batch_metric)
            last_compiled_script = candidate_script
            self._emit_substep(
                "node7",
                stage_name,
                "completed",
                (
                    f"fragment_chars={batch_metric['fragment']['chars']}, "
                    f"compile_ok={batch_metric['compile_ok']}, "
                    f"exceeds_hard_limit={batch_metric['exceeds_hard_limit']}"
                ),
            )

        generation_mode = f"planned_codegen_{plan['batch_count']}batch"
        return (
            last_compiled_script,
            generation_mode,
            {
                "plan_source": plan_source,
                "plan": plan,
                "completed_batch_count": len(completed_batches),
                "batch_metrics": batch_metrics,
            },
        )
