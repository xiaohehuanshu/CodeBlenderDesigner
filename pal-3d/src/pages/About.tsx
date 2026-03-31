import React from 'react';
import { motion } from 'motion/react';
import { Mail, Github, Globe, Award, BookOpen, Users } from 'lucide-react';

export function About() {
  return (
    <div className="pt-32 pb-20 px-6 bg-bg-warm/20 min-h-screen">
      <div className="max-w-7xl mx-auto">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-24">
          <div className="lg:col-span-8">
            <header className="mb-20">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8 }}
              >
                <div className="text-accent font-mono text-[10px] tracking-[0.3em] uppercase mb-4">Research & Vision</div>
                <h1 className="text-6xl font-bold tracking-tight mb-8">关于团队</h1>
                <div className="h-1 w-20 bg-accent mb-8" />
                <p className="text-2xl text-ink/60 leading-relaxed font-sans max-w-3xl">
                  Pal 3D 是一个专注于建筑设计工程化工作流的研究项目。我们致力于通过多智能体协作系统，实现从复杂设计需求到精确几何实体的自动化转化。
                </p>
              </motion.div>
            </header>

            <div className="space-y-20">
              {/* Project Background */}
              <section>
                <h2 className="text-xs font-mono uppercase tracking-[0.3em] text-accent mb-10 font-bold flex items-center gap-2">
                  <div className="w-8 h-px bg-accent" /> 项目背景
                </h2>
                <div className="prose prose-slate max-w-none text-ink/70 space-y-8 leading-loose text-lg">
                  <p>
                    在传统的建筑设计流程中，从概念构思到参数化建模往往存在巨大的技术鸿沟。设计师需要掌握复杂的编程语言（如 Python）或视觉化编程工具（如 Grasshopper）才能实现高度定制化的几何生成。
                  </p>
                  <p>
                    Pal 3D 通过引入一个基于 LangGraph 的多节点 AI 代理系统，将这一过程解构为“意图解析”、“上下文感知”、“代码生成”与“运行时验证”四个核心环节。系统不仅能生成代码，更能理解建筑规范，并在生成过程中进行自我纠错与迭代。
                  </p>
                </div>
              </section>

              {/* Team / Lab */}
              <section>
                <h2 className="text-xs font-mono uppercase tracking-[0.3em] text-accent mb-10 font-bold flex items-center gap-2">
                  <div className="w-8 h-px bg-accent" /> 核心团队
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
                  {[
                    { name: 'Dr. Zhang Lin', role: 'Principal Investigator', bio: '计算设计博士，专注于生成式建筑算法与 AI 代理系统。' },
                    { name: 'Wang Jun', role: 'Lead Developer', bio: '全栈工程师，Blender Python 接口专家，负责系统架构设计。' },
                    { name: 'Li Ming', role: 'Research Assistant', bio: '建筑学硕士，负责建筑规范库的数字化与验证逻辑。' },
                    { name: 'Chen Xiao', role: 'UI/UX Designer', bio: '专注于专业工具的交互设计，致力于提升 AI 辅助设计的体验。' }
                  ].map((member, i) => (
                    <div key={i} className="p-8 bg-white border border-border-subtle shadow-sm hover:shadow-md transition-all">
                      <div className="text-sm font-bold mb-2">{member.name}</div>
                      <div className="text-[10px] font-mono uppercase tracking-widest text-accent mb-4">{member.role}</div>
                      <p className="text-xs text-ink/50 leading-relaxed">{member.bio}</p>
                    </div>
                  ))}
                </div>
              </section>

              {/* Mission & Direction */}
              <section className="grid grid-cols-1 md:grid-cols-2 gap-16">
                <div>
                  <h2 className="text-xs font-mono uppercase tracking-[0.3em] text-accent mb-8 font-bold flex items-center gap-2">
                    <div className="w-8 h-px bg-accent" /> 研究使命
                  </h2>
                  <p className="text-sm text-ink/60 leading-relaxed">
                    我们的使命是赋予每一位建筑师“代码”的力量，让创意不再受限于技术工具，实现从自然语言到精确建筑实体的无缝衔接。
                  </p>
                </div>
                <div>
                  <h2 className="text-xs font-mono uppercase tracking-[0.3em] text-accent mb-8 font-bold flex items-center gap-2">
                    <div className="w-8 h-px bg-accent" /> 合作展望
                  </h2>
                  <p className="text-sm text-ink/60 leading-relaxed">
                    我们欢迎来自学术界与工业界的合作伙伴。无论是算法研究、案例实践还是工具集成，我们都期待与您共同探索 AIAD 的未来。
                  </p>
                </div>
              </section>
            </div>
          </div>

          <div className="lg:col-span-4">
            <div className="sticky top-32 space-y-12">
              <div className="p-10 bg-white border border-border-subtle shadow-sm">
                <h3 className="text-lg font-bold mb-8">联系我们</h3>
                <div className="space-y-6">
                  <a href="#" className="flex items-center gap-4 text-sm text-ink/50 hover:text-accent transition-colors group">
                    <div className="w-10 h-10 bg-bg-warm flex items-center justify-center group-hover:bg-accent group-hover:text-white transition-colors">
                      <Mail size={16} />
                    </div>
                    <div>
                      <div className="text-[10px] font-mono uppercase tracking-widest text-ink/30 mb-1">Email</div>
                      <div className="font-bold">research@pal3d.ai</div>
                    </div>
                  </a>
                  <a href="#" className="flex items-center gap-4 text-sm text-ink/50 hover:text-accent transition-colors group">
                    <div className="w-10 h-10 bg-bg-warm flex items-center justify-center group-hover:bg-accent group-hover:text-white transition-colors">
                      <Github size={16} />
                    </div>
                    <div>
                      <div className="text-[10px] font-mono uppercase tracking-widest text-ink/30 mb-1">GitHub</div>
                      <div className="font-bold">github.com/arch-ai/pal-3d</div>
                    </div>
                  </a>
                </div>
              </div>

              <div className="p-10 bg-accent text-white shadow-xl">
                <h3 className="text-xl font-bold mb-6">加入研究</h3>
                <p className="text-sm text-white/70 mb-10 leading-relaxed">
                  我们正在寻找对计算设计、几何算法与 AI 结合感兴趣的研究者与开发者。
                </p>
                <button className="w-full py-4 bg-white text-accent text-sm font-bold hover:bg-ink hover:text-white transition-all uppercase tracking-widest">
                  提交申请
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
