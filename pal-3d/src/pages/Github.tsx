import React from 'react';
import { motion } from 'motion/react';
import { Github as GithubIcon, Folder, FileCode, Terminal, ExternalLink, GitBranch, Star, GitPullRequest } from 'lucide-react';

const folders = [
  { name: 'src/nodes', description: '基于 LangGraph 的 8 个核心功能节点，负责从需求收集到脚本生成的全流程逻辑。' },
  { name: 'src/state', description: '定义 Agent 的状态图与上下文记忆结构。' },
  { name: 'src/utils', description: 'Blender Python 接口封装与几何数据处理工具。' },
  { name: 'requests', description: '包含 request_case_001.json 等任务配置文件示例。' },
  { name: 'prompts', description: '结构化的设计简报与指令模板。' }
];

const steps = [
  { title: '克隆仓库', command: 'git clone https://github.com/arch-ai/pal-3d.git' },
  { title: '安装依赖', command: 'pip install -r requirements.txt' },
  { title: '配置 API Key', command: 'export GEMINI_API_KEY="your_key_here"' },
  { title: '运行代理', command: 'python run_agent.py --config ./requests/case_001.json' }
];

export function Github() {
  return (
    <div className="pt-32 pb-20 px-6 bg-bg-warm/20 min-h-screen">
      <div className="max-w-5xl mx-auto">
        <header className="mb-20">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
          >
            <div className="text-accent font-mono text-[10px] tracking-[0.3em] uppercase mb-4">Open Source Repository</div>
            <h1 className="text-5xl font-bold tracking-tight mb-8">GitHub 仓库</h1>
            <div className="h-1 w-20 bg-accent mb-8" />
            <p className="text-xl text-ink/50 max-w-2xl leading-relaxed">
              Pal 3D 的核心源代码，基于 MIT 协议开源，欢迎共同构建。
            </p>
          </motion.div>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-16">
          <div className="lg:col-span-8 space-y-16">
            {/* Project Description */}
            <section>
              <h2 className="text-xs font-mono uppercase tracking-[0.3em] text-accent mb-8 font-bold flex items-center gap-2">
                <div className="w-8 h-px bg-accent" /> 项目简介
              </h2>
              <p className="text-lg leading-relaxed text-ink/70">
                本项目是一个开源的基于 LangGraph 的建筑设计工作流框架。它利用大语言模型的推理能力与多节点协作逻辑，自动化生成复杂的 Blender 几何模型。系统通过 8 个核心节点实现了从需求整合、上下文分析到代码生成与运行时调试的完整工程闭环。
              </p>
            </section>

            {/* Code Structure */}
            <section>
              <h2 className="text-xs font-mono uppercase tracking-[0.3em] text-accent mb-8 font-bold flex items-center gap-2">
                <div className="w-8 h-px bg-accent" /> 代码结构
              </h2>
              <div className="space-y-4">
                {folders.map((folder, i) => (
                  <div key={i} className="flex gap-6 p-6 bg-white border border-border-subtle hover:border-accent transition-colors group">
                    <div className="text-accent group-hover:scale-110 transition-transform">
                      <Folder size={20} />
                    </div>
                    <div>
                      <div className="font-mono text-sm font-bold mb-2">{folder.name}</div>
                      <p className="text-xs text-ink/50 leading-relaxed">{folder.description}</p>
                    </div>
                  </div>
                ))}
              </div>
            </section>

            {/* Quick Start */}
            <section>
              <h2 className="text-xs font-mono uppercase tracking-[0.3em] text-accent mb-8 font-bold flex items-center gap-2">
                <div className="w-8 h-px bg-accent" /> 快速开始
              </h2>
              <div className="space-y-6">
                {steps.map((step, i) => (
                  <div key={i} className="space-y-3">
                    <div className="text-xs font-bold text-ink/40">{i + 1}. {step.title}</div>
                    <div className="bg-ink text-bg-warm p-4 font-mono text-xs flex justify-between items-center group">
                      <span>$ {step.command}</span>
                      <button className="opacity-0 group-hover:opacity-100 transition-opacity text-[10px] uppercase tracking-widest text-accent">Copy</button>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          </div>

          {/* Sidebar */}
          <div className="lg:col-span-4 space-y-12">
            <div className="p-8 bg-white border border-border-subtle sticky top-32">
              <div className="flex items-center gap-3 mb-8">
                <GithubIcon size={24} className="text-ink" />
                <div className="font-bold">arch-ai / pal-3d</div>
              </div>

              <div className="grid grid-cols-2 gap-6 mb-10">
                <div className="space-y-1">
                  <div className="text-[10px] font-mono uppercase tracking-widest text-ink/30">Stars</div>
                  <div className="flex items-center gap-2 font-bold"><Star size={14} className="text-accent" /> 1.2k</div>
                </div>
                <div className="space-y-1">
                  <div className="text-[10px] font-mono uppercase tracking-widest text-ink/30">Forks</div>
                  <div className="flex items-center gap-2 font-bold"><GitBranch size={14} className="text-accent" /> 248</div>
                </div>
              </div>

              <div className="space-y-4">
                <button className="w-full py-4 bg-ink text-bg-warm text-sm font-bold flex items-center justify-center gap-3 hover:bg-accent transition-all group">
                  <GithubIcon size={18} /> 前往 GitHub 仓库 <ExternalLink size={14} className="group-hover:translate-x-1 transition-transform" />
                </button>
                <button className="w-full py-4 border border-ink/10 text-ink/60 text-sm font-bold flex items-center justify-center gap-3 hover:bg-bg-warm transition-all">
                  <GitPullRequest size={18} /> 提交 Pull Request
                </button>
              </div>

              <div className="mt-10 pt-10 border-t border-border-subtle">
                <div className="text-[10px] font-mono uppercase tracking-widest text-ink/30 mb-4">最新版本</div>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-bold">v0.8.2-beta</span>
                  <span className="text-[10px] font-mono text-accent">Stable Build</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
