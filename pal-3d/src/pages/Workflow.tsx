import React from 'react';
import { motion } from 'motion/react';
import { GitBranch, RefreshCw, Layers, Terminal, ShieldCheck, Database, Zap, Search, FileText, Cpu, MessageSquare, Box } from 'lucide-react';

const stages = [
  {
    title: '需求收集',
    subtitle: 'node1_collect_requirements',
    nodes: ['意图解析', '参数提取'],
    icon: <MessageSquare size={20} />,
    desc: '从模糊的自然语言描述中提取结构化的设计参数与功能需求，确立设计基调。'
  },
  {
    title: '互联网调研',
    subtitle: 'node2_internet_research',
    nodes: ['案例检索', '技术查证'],
    icon: <Search size={20} />,
    desc: '通过搜索引擎获取相关的建筑案例、规范标准及技术实现方案，为设计提供参考。'
  },
  {
    title: '图像分析',
    subtitle: 'node3_image_analysis',
    nodes: ['视觉参考', '风格提取'],
    icon: <Layers size={20} />,
    desc: '解析用户提供的参考图像，提取视觉风格、材质特征与形式启发。'
  },
  {
    title: '文档规则分析',
    subtitle: 'node4_markdown_analysis',
    nodes: ['规范解析', '约束提取'],
    icon: <FileText size={20} />,
    desc: '深度分析 Markdown 格式的设计规范、尺寸约束与逻辑定义，确保生成符合标准。'
  },
  {
    title: '几何约束提取',
    subtitle: 'node5_geometry_constraints',
    nodes: ['场地分析', '边界识别'],
    icon: <Box size={20} />,
    desc: '从 .blend 场地模型中提取几何约束，包括地形、红线及周边建筑的物理边界。'
  },
  {
    title: '提示词综合',
    subtitle: 'node6_prompt_synthesis',
    nodes: ['简报合成', '指令优化'],
    icon: <Zap size={20} />,
    desc: '整合前述所有节点的分析结果，合成最终的结构化设计简报 (Design Brief)。'
  },
  {
    title: '脚本生成',
    subtitle: 'node7_script_generation',
    nodes: ['代码编写', 'API 调用'],
    icon: <Terminal size={20} />,
    desc: 'AI 代理编写高度优化的 Blender Python 脚本，将设计简报转化为精确的几何实体。'
  },
  {
    title: '运行时调试',
    subtitle: 'node8_runtime_debug',
    nodes: ['错误捕获', '自动修正'],
    icon: <RefreshCw size={20} />,
    desc: '在虚拟环境中执行脚本，实时捕获几何错误或逻辑异常，并自动触发迭代修正。'
  }
];

import { Code } from 'lucide-react';

export function Workflow() {
  return (
    <div className="pt-32 pb-20 px-6 bg-bg-warm">
      <div className="max-w-7xl mx-auto">
        <header className="mb-24 text-center">
          <div className="text-accent font-mono text-[10px] tracking-[0.3em] uppercase mb-4">System Architecture</div>
          <h1 className="text-5xl font-bold tracking-tight mb-6">Pal 3D 空间设计工作流</h1>
          <p className="text-xl text-ink/50 max-w-2xl mx-auto leading-relaxed">
            Pal 3D 采用严谨的 8 节点流水线架构，将感性的设计意图转化为理性的几何逻辑。
          </p>
        </header>

        {/* Visual Pipeline */}
        <div className="relative space-y-12 mb-32">
          {/* Connecting Line */}
          <div className="absolute left-1/2 top-0 bottom-0 w-px bg-border-subtle hidden lg:block -translate-x-1/2" />
          
          {stages.map((stage, idx) => (
            <motion.div 
              key={idx}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              className={cn(
                "relative flex flex-col lg:flex-row items-center gap-8 lg:gap-24",
                idx % 2 === 0 ? "lg:flex-row" : "lg:flex-row-reverse"
              )}
            >
              {/* Stage Card */}
              <div className="flex-1 w-full">
                <div className={cn(
                  "p-8 bg-white border border-border-subtle shadow-sm hover:border-accent transition-all group",
                  idx % 2 === 0 ? "lg:text-right" : "lg:text-left"
                )}>
                  <div className={cn("flex items-center gap-4 mb-4", idx % 2 === 0 ? "lg:justify-end" : "lg:justify-start")}>
                    <div className="text-accent group-hover:scale-110 transition-transform">{stage.icon}</div>
                    <div className="text-[10px] font-mono uppercase tracking-widest text-ink/30">{stage.subtitle}</div>
                  </div>
                  <h3 className="text-2xl font-bold mb-4">{stage.title}</h3>
                  <p className="text-sm text-ink/50 leading-relaxed mb-6 max-w-md mx-auto lg:mx-0">
                    {stage.desc}
                  </p>
                  <div className={cn("flex flex-wrap gap-2", idx % 2 === 0 ? "lg:justify-end" : "lg:justify-start")}>
                    {stage.nodes.map((node, i) => (
                      <span key={i} className="px-3 py-1 bg-bg-warm text-[10px] font-mono text-ink/60 uppercase tracking-wider">
                        {node}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              {/* Center Node */}
              <div className="relative z-10 w-12 h-12 bg-ink text-white flex items-center justify-center font-bold text-sm rounded-full border-4 border-bg-warm shadow-lg">
                0{idx + 1}
              </div>

              {/* Spacer for reverse layout */}
              <div className="flex-1 hidden lg:block" />
            </motion.div>
          ))}
        </div>

        {/* Detailed Logic Section */}
        <section className="grid grid-cols-1 lg:grid-cols-3 gap-12 py-24 border-t border-border-subtle">
          <div className="lg:col-span-1">
            <h2 className="text-3xl font-bold mb-6">8 节点核心逻辑</h2>
            <p className="text-sm text-ink/50 leading-relaxed">
              流水线内部由 8 个高度自治的 LangGraph 节点组成，每个节点负责特定的需求解析、上下文分析或几何生成任务。
            </p>
          </div>
          <div className="lg:col-span-2 grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              'Collect Requirements',
              'Internet Research',
              'Image Analysis',
              'Markdown Analysis',
              'Geometry Constraints',
              'Prompt Synthesis',
              'Script Generation',
              'Runtime Debug'
            ].map((node, i) => (
              <div key={i} className="p-4 bg-white border border-border-subtle text-center group hover:bg-ink hover:text-white transition-all">
                <div className="text-[10px] font-mono text-ink/30 group-hover:text-white/40 mb-2">NODE_0{i+1}</div>
                <div className="text-xs font-bold">{node}</div>
              </div>
            ))}
          </div>
        </section>

        {/* Runtime Feedback Mock */}
        <section className="mt-20 bg-ink p-12 rounded-sm shadow-2xl relative overflow-hidden">
          <div className="absolute top-0 right-0 p-8 opacity-5">
            <Cpu size={200} />
          </div>
          <div className="relative z-10">
            <div className="flex items-center gap-2 mb-8 text-white/30 font-mono text-xs">
              <Terminal size={14} /> ITERATIVE_REFINEMENT_STREAM
            </div>
            <div className="font-mono text-xs space-y-4 text-white/70 max-w-3xl">
              <div className="flex gap-4">
                <span className="text-blue-400">[GEN]</span>
                <p>Generating mesh for "Cantilever_Structure"...</p>
              </div>
              <div className="flex gap-4">
                <span className="text-yellow-400">[VAL]</span>
                <p>Warning: Cantilever length (7.2m) exceeds structural safety limit (5.0m).</p>
              </div>
              <div className="flex gap-4">
                <span className="text-purple-400">[REF]</span>
                <p>Refining parameters: Reducing cantilever to 4.8m, adding support column at node_32.</p>
              </div>
              <div className="flex gap-4">
                <span className="text-green-400">[OK]</span>
                <p>Validation passed. Finalizing Blender script...</p>
              </div>
              <div className="pt-4 border-t border-white/5 text-accent animate-pulse">
                _ System ready for next instruction.
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}

import { cn } from '@/src/lib/utils';
