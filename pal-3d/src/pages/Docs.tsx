import React from 'react';
import { motion } from 'motion/react';
import { Book, ChevronRight, Search, Terminal, Code, Cpu, FileText, Settings, Database, Box, Zap, Share2, MessageSquare } from 'lucide-react';

const sections = [
  { id: 'quick-start', title: '快速开始', icon: <Zap size={16} /> },
  { id: 'run-agent', title: 'run_agent.py', icon: <Terminal size={16} /> },
  { id: 'request-json', title: 'request_case_001.json', icon: <FileText size={16} /> },
  { id: 'prompt-file', title: 'prompt_file', icon: <MessageSquare size={16} /> },
  { id: 'interactive-mode', title: '交互模式', icon: <Zap size={16} /> },
  { id: 'node-switches', title: '节点开关', icon: <Settings size={16} /> },
  { id: 'blend-file', title: 'blend_file', icon: <Box size={16} /> },
  { id: 'outputs', title: '输出文件 (Outputs)', icon: <Database size={16} /> },
];

export function Docs() {
  return (
    <div className="pt-20 flex min-h-screen bg-bg-warm">
      {/* Sidebar */}
      <aside className="w-72 border-r border-border-subtle hidden lg:block sticky top-20 h-[calc(100vh-5rem)] overflow-y-auto p-8 bg-white">
        <div className="relative mb-10">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-ink/30" size={14} />
          <input 
            type="text" 
            placeholder="搜索文档..." 
            className="w-full bg-bg-warm border border-border-subtle rounded-sm py-2 pl-10 pr-4 text-xs focus:outline-none focus:border-accent transition-colors"
          />
        </div>
        
        <nav className="space-y-8">
          <div>
            <div className="text-[10px] font-mono uppercase tracking-widest text-ink/30 mb-4">Technical Guide</div>
            <ul className="space-y-1">
              {sections.map(s => (
                <li key={s.id}>
                  <a href={`#${s.id}`} className="flex items-center gap-3 text-sm text-ink/50 hover:text-accent hover:bg-bg-warm transition-all px-3 py-2 rounded-sm">
                    {s.icon} {s.title}
                  </a>
                </li>
              ))}
            </ul>
          </div>
          
          <div>
            <div className="text-[10px] font-mono uppercase tracking-widest text-ink/30 mb-4">Resources</div>
            <ul className="space-y-2 text-sm text-ink/50 px-3">
              <li className="hover:text-accent cursor-pointer flex items-center gap-2"><Book size={12}/> API Reference</li>
              <li className="hover:text-accent cursor-pointer flex items-center gap-2"><Code size={12}/> Example Scripts</li>
              <li className="hover:text-accent cursor-pointer flex items-center gap-2"><Share2 size={12}/> Community Rules</li>
            </ul>
          </div>
        </nav>
      </aside>

      {/* Content */}
      <main className="flex-1 p-8 lg:p-16 max-w-5xl">
        <article className="prose prose-slate max-w-none">
          <header className="mb-16 border-b border-border-subtle pb-12">
            <div className="text-accent font-mono text-[10px] tracking-[0.3em] uppercase mb-4">Documentation</div>
            <h1 className="text-4xl font-bold mb-4">技术文档</h1>
            <p className="text-xl text-ink/50 leading-relaxed max-w-3xl">
              欢迎查阅 Pal 3D 技术文档。本手册详细介绍了系统的运行逻辑、配置参数以及输出结构。
            </p>
          </header>

          <section id="quick-start" className="mb-24">
            <h2 className="text-2xl font-bold mb-8 flex items-center gap-3">
              <Zap className="text-accent" size={24} /> 快速开始
            </h2>
            <div className="space-y-6 text-ink/70">
              <p>Pal 3D 是一个基于 Python 的多智能体系统。请确保您的环境满足以下要求：</p>
              <ul className="list-disc pl-6 space-y-2">
                <li>Python 3.10+</li>
                <li>安装依赖：<code>pip install -r requirements.txt</code></li>
                <li>配置环境变量 <code>GEMINI_API_KEY</code></li>
              </ul>
              <div className="bg-ink text-white/80 p-6 rounded-sm font-mono text-sm shadow-xl">
                <p className="text-white/30"># 运行代理</p>
                <p>python run_agent.py</p>
              </div>
            </div>
          </section>

          <section id="run-agent" className="mb-24">
            <h2 className="text-2xl font-bold mb-8 flex items-center gap-3">
              <Terminal className="text-accent" size={24} /> run_agent.py
            </h2>
            <p className="mb-6 text-ink/70">系统的入口脚本。它负责初始化 LangGraph 工作流，加载请求配置，并协调各个节点的执行。</p>
            <div className="bg-white border border-border-subtle p-6 rounded-sm font-mono text-sm">
              <p className="text-ink/40"># 基本用法</p>
              <p>python run_agent.py --config ./requests/case_001.json</p>
            </div>
          </section>

          <section id="request-json" className="mb-24">
            <h2 className="text-2xl font-bold mb-8 flex items-center gap-3">
              <FileText className="text-accent" size={24} /> request_case_001.json
            </h2>
            <p className="mb-6 text-ink/70">请求配置文件定义了任务的输入源、节点开关以及项目元数据。</p>
            <div className="bg-white border border-border-subtle p-8 rounded-sm font-mono text-sm shadow-sm">
              <pre className="text-ink/80">
{`{
  "project_name": "Modern_Pavilion",
  "prompt_file": "prompts/pavilion_brief.txt",
  "blend_file": "context/site_context.blend",
  "switches": {
    "internet_research": true,
    "image_analysis": true,
    "runtime_debug": true
  }
}`}
              </pre>
            </div>
          </section>

          <section id="prompt-file" className="mb-24">
            <h2 className="text-2xl font-bold mb-8 flex items-center gap-3">
              <MessageSquare className="text-accent" size={24} /> prompt_file
            </h2>
            <p className="text-ink/70 leading-relaxed">
              存放设计意图的纯文本文件。Agent 将读取此文件作为初始需求，并结合其他输入源进行综合分析。
            </p>
          </section>

          <section id="interactive-mode" className="mb-24">
            <h2 className="text-2xl font-bold mb-8 flex items-center gap-3">
              <Zap className="text-accent" size={24} /> 交互模式 (Interactive Mode)
            </h2>
            <p className="text-ink/70 leading-relaxed">
              在运行过程中，Agent 可能会在关键决策点（如提示词综合后）请求人工确认或补充信息，以确保生成结果符合预期。
            </p>
          </section>

          <section id="node-switches" className="mb-24">
            <h2 className="text-2xl font-bold mb-8 flex items-center gap-3">
              <Settings className="text-accent" size={24} /> 节点开关 (Node Switches)
            </h2>
            <p className="mb-6 text-ink/70">通过配置文件中的 <code>switches</code> 字段，您可以精确控制哪些节点参与工作流，从而优化运行成本和速度。</p>
          </section>

          <section id="blend-file" className="mb-24">
            <h2 className="text-2xl font-bold mb-8 flex items-center gap-3">
              <Box className="text-accent" size={24} /> blend_file
            </h2>
            <p className="text-ink/70 leading-relaxed">
              作为几何上下文输入的 Blender 文件。系统将解析其中的对象边界、坐标系及图层信息，为脚本生成提供物理约束。
            </p>
          </section>

          <section id="outputs" className="mb-24">
            <h2 className="text-2xl font-bold mb-8 flex items-center gap-3">
              <Database className="text-accent" size={24} /> 输出文件 (Outputs)
            </h2>
            <div className="space-y-4">
              {[
                { path: 'outputs/generated_scripts/', desc: '包含最终生成的 Blender Python 脚本。' },
                { path: 'outputs/memory/', desc: '记录 Agent 在执行过程中的短期记忆与上下文状态。' },
                { path: 'outputs/traces/', desc: '详细的节点执行追踪日志，用于调试与性能分析。' },
                { path: 'outputs/internet_research/', desc: '互联网调研节点获取的原始数据与摘要。' },
              ].map((item, i) => (
                <div key={i} className="flex items-center gap-6 p-4 bg-white border border-border-subtle">
                  <div className="font-mono text-xs text-accent w-48 shrink-0">{item.path}</div>
                  <div className="text-sm text-ink/50">{item.desc}</div>
                </div>
              ))}
            </div>
          </section>
        </article>
      </main>
    </div>
  );
}
