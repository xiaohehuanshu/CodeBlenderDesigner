import React from 'react';
import { motion } from 'motion/react';
import { Book, FileText, Code, Share2, Box, Eye, Zap } from 'lucide-react';

const sections = [
  { id: 'overview', title: '项目概述', icon: <Eye size={16} /> },
  { id: 'features', title: '功能特性', icon: <Zap size={16} /> },
  { id: 'tech-stack', title: '技术栈', icon: <Code size={16} /> },
  { id: 'resources', title: '相关资源', icon: <Book size={16} /> },
];

export function Docs() {
  return (
    <div className="pt-20 flex min-h-screen bg-bg-warm">
      {/* Sidebar */}
      <aside className="w-72 border-r border-border-subtle hidden lg:block sticky top-20 h-[calc(100vh-5rem)] overflow-y-auto p-8 bg-white">
        <nav className="space-y-8">
          <div>
            <div className="text-[10px] font-mono uppercase tracking-widest text-ink/30 mb-4">Documentation</div>
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
        </nav>
      </aside>

      {/* Content */}
      <main className="flex-1 p-8 lg:p-16 max-w-5xl">
        <article className="prose prose-slate max-w-none">
          <header className="mb-16 border-b border-border-subtle pb-12">
            <div className="text-accent font-mono text-[10px] tracking-[0.3em] uppercase mb-4">Documentation</div>
            <h1 className="text-4xl font-bold mb-4">技术文档</h1>
            <p className="text-xl text-ink/50 leading-relaxed max-w-3xl">
              Pal 3D 项目概述与技术说明
            </p>
          </header>

          <section id="overview" className="mb-24">
            <h2 className="text-2xl font-bold mb-8 flex items-center gap-3">
              <Eye className="text-accent" size={24} /> 项目概述
            </h2>
            <div className="space-y-6 text-ink/70">
              <p>Pal 3D 是一个基于 AI 的 3D 模型展示与交互平台。本项目旨在提供简洁高效的 3D 模型浏览体验。</p>
            </div>
          </section>

          <section id="features" className="mb-24">
            <h2 className="text-2xl font-bold mb-8 flex items-center gap-3">
              <Zap className="text-accent" size={24} /> 功能特性
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {[
                { title: '3D 模型渲染', desc: '基于 Three.js 的实时 3D 渲染' },
                { title: '交互式查看', desc: '支持旋转、缩放、平移操作' },
                { title: '响应式设计', desc: '适配桌面与移动设备' },
                { title: '案例展示', desc: '精选 3D 案例在线浏览' },
              ].map((item, i) => (
                <div key={i} className="p-6 bg-white border border-border-subtle">
                  <h4 className="font-bold mb-2">{item.title}</h4>
                  <p className="text-sm text-ink/50">{item.desc}</p>
                </div>
              ))}
            </div>
          </section>

          <section id="tech-stack" className="mb-24">
            <h2 className="text-2xl font-bold mb-8 flex items-center gap-3">
              <Code className="text-accent" size={24} /> 技术栈
            </h2>
            <div className="flex flex-wrap gap-3">
              {[
                'React 19',
                'TypeScript',
                'Vite',
                'Tailwind CSS',
                'Three.js',
                '@react-three/fiber',
                '@react-three/drei',
                'React Router',
              ].map((tech, i) => (
                <span key={i} className="px-4 py-2 bg-white border border-border-subtle text-sm font-medium">
                  {tech}
                </span>
              ))}
            </div>
          </section>

          <section id="resources" className="mb-24">
            <h2 className="text-2xl font-bold mb-8 flex items-center gap-3">
              <Book className="text-accent" size={24} /> 相关资源
            </h2>
            <div className="space-y-4">
              {[
                { name: 'GitHub 仓库', desc: '查看源代码', icon: <Code size={18} /> },
                { name: '使用指南', desc: '网站操作教程', icon: <FileText size={18} /> },
                { name: '案例展示', desc: '浏览更多案例', icon: <Box size={18} /> },
              ].map((item, i) => (
                <div key={i} className="flex items-center gap-4 p-4 bg-white border border-border-subtle">
                  <div className="text-accent">{item.icon}</div>
                  <div>
                    <h4 className="font-bold">{item.name}</h4>
                    <p className="text-sm text-ink/50">{item.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </section>
        </article>
      </main>
    </div>
  );
}
