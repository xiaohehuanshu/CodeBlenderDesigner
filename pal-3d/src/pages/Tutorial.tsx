import React from 'react';
import { motion } from 'motion/react';
import { BookOpen, FileText, Box, Cpu, Layout, ArrowRight, CheckCircle2, Info } from 'lucide-react';
import { Link } from 'react-router-dom';

export function Tutorial() {
  return (
    <div className="pt-32 pb-20 px-6 bg-bg-warm">
      <div className="max-w-4xl mx-auto">
        <header className="mb-20 text-center">
          <div className="inline-block px-3 py-1 bg-accent/10 text-accent text-[10px] font-mono uppercase tracking-[0.2em] mb-6">
            Beginner Tutorial
          </div>
          <h1 className="text-5xl font-bold tracking-tight mb-6">Pal 3D 新手快速上手指南</h1>
          <p className="text-xl text-ink/50 leading-relaxed">
            欢迎使用 Pal 3D。本教程将带您了解如何从零开始使用这个 AI 驱动的建筑空间设计 Agent 系统。
          </p>
        </header>

        <div className="space-y-24">
          {/* Section 1: What is Pal 3D */}
          <section>
            <div className="flex items-center gap-4 mb-8">
              <div className="w-12 h-12 bg-ink text-white flex items-center justify-center font-bold text-xl">01</div>
              <h2 className="text-2xl font-bold">什么是 Pal 3D？</h2>
            </div>
            <div className="prose prose-slate max-w-none text-ink/70 leading-loose">
              <p>
                Pal 3D 是一个基于 <strong>LangGraph</strong> 框架开发的建筑空间设计智能代理（Agent）。它不是一个简单的 3D 建模工具，而是一个能够理解复杂设计需求、分析多维上下文，并自动生成 Blender Python 脚本的“数字建筑师”。
              </p>
              <p>
                它的核心目标是：<strong>让 AI 成为您的创作伙伴（Pal），共同完成从概念到几何生成的全过程。</strong>
              </p>
            </div>
          </section>

          {/* Section 2: What can Pal 3D do */}
          <section>
            <div className="flex items-center gap-4 mb-8">
              <div className="w-12 h-12 bg-ink text-white flex items-center justify-center font-bold text-xl">02</div>
              <h2 className="text-2xl font-bold">Pal 3D 能做什么？</h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {[
                { title: '需求深度解析', desc: '自动从模糊的自然语言中提取建筑功能、面积、层高等硬性指标。', icon: <FileText className="text-accent" /> },
                { title: '多源上下文合成', desc: '结合地形 (.blend)、设计规范 (Markdown) 与参考图进行综合决策。', icon: <Layout className="text-accent" /> },
                { title: '自动化建模脚本', desc: '生成高质量、可运行的 Blender Python 脚本，直接构建 3D 几何体。', icon: <Box className="text-accent" /> },
                { title: '闭环调试与验证', desc: '在虚拟环境中运行脚本，发现错误后自动进行逻辑修正与代码重写。', icon: <Cpu className="text-accent" /> },
              ].map((item, i) => (
                <div key={i} className="p-6 bg-white border border-border-subtle shadow-sm">
                  <div className="mb-4">{item.icon}</div>
                  <h4 className="font-bold mb-2">{item.title}</h4>
                  <p className="text-sm text-ink/50">{item.desc}</p>
                </div>
              ))}
            </div>
          </section>

          {/* Section 3: Prerequisites */}
          <section>
            <div className="flex items-center gap-4 mb-8">
              <div className="w-12 h-12 bg-ink text-white flex items-center justify-center font-bold text-xl">03</div>
              <h2 className="text-2xl font-bold">使用前需要准备什么？</h2>
            </div>
            <div className="bg-white border border-border-subtle p-8 space-y-4">
              <div className="flex items-start gap-3">
                <CheckCircle2 className="text-accent shrink-0 mt-1" size={18} />
                <p className="text-ink/70 text-sm"><strong>Python 环境：</strong> 安装 Python 3.10 或更高版本。</p>
              </div>
              <div className="flex items-start gap-3">
                <CheckCircle2 className="text-accent shrink-0 mt-1" size={18} />
                <p className="text-ink/70 text-sm"><strong>Blender：</strong> 建议安装 Blender 4.0+，并确保其可执行路径已配置。</p>
              </div>
              <div className="flex items-start gap-3">
                <CheckCircle2 className="text-accent shrink-0 mt-1" size={18} />
                <p className="text-ink/70 text-sm"><strong>API Key：</strong> 获取 Google Gemini API Key 并配置为环境变量 <code>GEMINI_API_KEY</code>。</p>
              </div>
              <div className="flex items-start gap-3">
                <CheckCircle2 className="text-accent shrink-0 mt-1" size={18} />
                <p className="text-ink/70 text-sm"><strong>依赖安装：</strong> 在终端运行 <code>pip install -r requirements.txt</code>。</p>
              </div>
            </div>
          </section>

          {/* Section 4: Starting Input */}
          <section>
            <div className="flex items-center gap-4 mb-8">
              <div className="w-12 h-12 bg-ink text-white flex items-center justify-center font-bold text-xl">04</div>
              <h2 className="text-2xl font-bold">如何开始第一轮输入？</h2>
            </div>
            <div className="space-y-6">
              <p className="text-ink/70 leading-relaxed">
                Pal 3D 推荐通过 <code>run_agent.py</code> 启动。您可以通过配置文件或交互模式提供指令。
              </p>
              <div className="bg-ink text-bg-warm p-6 font-mono text-xs">
                # 方式 A：使用配置文件启动<br />
                python run_agent.py --config ./requests/case_001.json<br /><br />
                # 方式 B：进入交互模式<br />
                python run_agent.py --interactive
              </div>
            </div>
          </section>

          {/* Section 5: Key Concepts */}
          <section>
            <div className="flex items-center gap-4 mb-8">
              <div className="w-12 h-12 bg-ink text-white flex items-center justify-center font-bold text-xl">05</div>
              <h2 className="text-2xl font-bold">核心概念解析</h2>
            </div>
            <div className="space-y-8">
              <div className="p-6 bg-white border border-border-subtle">
                <h4 className="font-bold mb-4 flex items-center gap-2"><FileText size={18} className="text-accent" /> 配置文件与模式</h4>
                <ul className="space-y-4 text-sm text-ink/60">
                  <li><strong>request_case_001.json：</strong> 任务的“总指挥部”，定义了提示词路径、上下文路径及运行开关。</li>
                  <li><strong>prompt_file：</strong> 存放具体设计需求的文本文件，支持 Markdown 格式。</li>
                  <li><strong>interactive 模式：</strong> 允许您在终端直接输入指令，适合快速实验与微调。</li>
                </ul>
              </div>
              <div className="p-6 bg-white border border-border-subtle">
                <h4 className="font-bold mb-4 flex items-center gap-2"><Layout size={18} className="text-accent" /> 输入数据类型</h4>
                <ul className="space-y-4 text-sm text-ink/60">
                  <li><strong>参考图片：</strong> 提供视觉风格、色彩或形式参考，Agent 会进行视觉特征提取。</li>
                  <li><strong>Markdown 规则：</strong> 导入结构化的设计规范（如：建筑间距、容积率限制）。</li>
                  <li><strong>几何上下文 / blend_file：</strong> 导入现有的场景模型，Agent 会根据地形起伏或周边建筑调整生成位置。</li>
                </ul>
              </div>
            </div>
          </section>

          {/* Section 6: Outputs */}
          <section>
            <div className="flex items-center gap-4 mb-8">
              <div className="w-12 h-12 bg-ink text-white flex items-center justify-center font-bold text-xl">06</div>
              <h2 className="text-2xl font-bold">生成结果会输出到哪里？</h2>
            </div>
            <div className="bg-bg-warm p-8 border border-border-subtle">
              <p className="text-sm text-ink/70 mb-6">所有生成的内容都存放在 <code>outputs/</code> 目录下：</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 font-mono text-xs">
                <div className="p-4 bg-white border border-border-subtle">
                  <span className="text-accent">generated_scripts/</span><br />
                  <span className="text-ink/40">最终生成的 .py 脚本</span>
                </div>
                <div className="p-4 bg-white border border-border-subtle">
                  <span className="text-accent">memory/</span><br />
                  <span className="text-ink/40">Agent 的长期记忆与状态</span>
                </div>
                <div className="p-4 bg-white border border-border-subtle">
                  <span className="text-accent">traces/</span><br />
                  <span className="text-ink/40">完整的思考与纠错链路</span>
                </div>
                <div className="p-4 bg-white border border-border-subtle">
                  <span className="text-accent">internet_research/</span><br />
                  <span className="text-ink/40">联网搜索到的参考资料</span>
                </div>
              </div>
            </div>
          </section>

          {/* Section 7: Iteration */}
          <section>
            <div className="flex items-center gap-4 mb-8">
              <div className="w-12 h-12 bg-ink text-white flex items-center justify-center font-bold text-xl">07</div>
              <h2 className="text-2xl font-bold">如何继续进行多轮修改？</h2>
            </div>
            <div className="prose prose-slate max-w-none text-ink/70 leading-loose">
              <p>
                Pal 3D 支持<strong>增量式设计</strong>。在第一轮生成后，您可以直接在交互模式下输入修改意见（例如：“将屋顶改为坡屋顶”或“增加二层露台”）。
              </p>
              <p>
                Agent 会读取 <code>outputs/memory</code> 中的历史上下文，在保留原有逻辑的基础上，仅针对您的新需求更新 Python 脚本。
              </p>
            </div>
          </section>

          {/* Section 8: Notes */}
          <section>
            <div className="flex items-center gap-4 mb-8">
              <div className="w-12 h-12 bg-ink text-white flex items-center justify-center font-bold text-xl">08</div>
              <h2 className="text-2xl font-bold">基本注意事项</h2>
            </div>
            <div className="p-8 bg-accent/5 border border-accent/20 rounded-xl">
              <ul className="space-y-4 text-sm text-ink/70">
                <li className="flex gap-3"><Info size={18} className="text-accent shrink-0" /> <strong>单位统一：</strong> 默认使用 Blender 的米 (m) 作为单位，请在提示词中明确数值。</li>
                <li className="flex gap-3"><Info size={18} className="text-accent shrink-0" /> <strong>API 消耗：</strong> 复杂的联网搜索与多轮调试会消耗较多 Token，请注意 API 使用额度。</li>
                <li className="flex gap-3"><Info size={18} className="text-accent shrink-0" /> <strong>脚本安全：</strong> 生成的脚本在本地运行，请确保您的 Blender 环境安全。</li>
              </ul>
            </div>
          </section>
        </div>

        <div className="mt-32 p-12 bg-ink text-white text-center">
          <h2 className="text-3xl font-bold mb-6">准备好开始了吗？</h2>
          <p className="text-white/50 mb-10">现在就进入控制台，开启您的第一个建筑 AI 实验。</p>
          <Link to="/explore" className="inline-flex items-center gap-2 bg-accent text-white px-10 py-4 font-bold hover:bg-white hover:text-ink transition-all">
            进入控制台 <ArrowRight size={18} />
          </Link>
        </div>
      </div>
    </div>
  );
}
