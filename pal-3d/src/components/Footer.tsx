import React from 'react';
import { Link } from 'react-router-dom';

export function Footer() {
  return (
    <footer className="bg-white border-t border-border-subtle py-20 px-6">
      <div className="max-w-7xl mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-16 mb-20">
          <div className="col-span-1 md:col-span-2">
            <div className="flex items-center gap-2 mb-6">
              <div className="w-6 h-6 bg-ink flex items-center justify-center text-bg-warm font-bold text-[8px]">PAL</div>
              <span className="font-bold tracking-tight">Pal 3D</span>
            </div>
            <p className="text-sm text-ink/40 max-w-sm leading-relaxed">
              AI for Making - 基于 LangGraph 的建筑空间设计 Agent。致力于通过多节点 AI 协作，实现从设计简报到 Blender 自动化建模的闭环。
            </p>
          </div>
          
          <div>
            <h4 className="text-xs font-mono uppercase tracking-widest text-ink/30 mb-6">导航</h4>
            <ul className="space-y-4 text-sm font-medium">
              <li><Link to="/" className="hover:text-accent transition-colors">首页</Link></li>
              <li><Link to="/explore" className="hover:text-accent transition-colors">开始探索</Link></li>
              <li><Link to="/workflow" className="hover:text-accent transition-colors">工作流</Link></li>
              <li><Link to="/cases" className="hover:text-accent transition-colors">案例展示</Link></li>
            </ul>
          </div>

          <div>
            <h4 className="text-xs font-mono uppercase tracking-widest text-ink/30 mb-6">资源</h4>
            <ul className="space-y-4 text-sm font-medium">
              <li><Link to="/tutorial" className="hover:text-accent transition-colors">新手教程</Link></li>
              <li><Link to="/docs" className="hover:text-accent transition-colors">技术文档</Link></li>
              <li><Link to="/papers" className="hover:text-accent transition-colors">学术论文</Link></li>
              <li><Link to="/github" className="hover:text-accent transition-colors">GitHub 仓库</Link></li>
              <li><Link to="/about" className="hover:text-accent transition-colors">关于团队</Link></li>
            </ul>
          </div>
        </div>
        
        <div className="flex flex-col md:flex-row justify-between items-center pt-10 border-t border-border-subtle gap-6">
          <div className="text-[10px] font-mono text-ink/30 uppercase tracking-[0.2em]">
            © 2026 Pal 3D Group. All Rights Reserved.
          </div>
          <div className="flex gap-8 text-[10px] font-mono text-ink/30 uppercase tracking-widest">
            <a href="#" className="hover:text-ink transition-colors">Privacy Policy</a>
            <a href="#" className="hover:text-ink transition-colors">Terms of Service</a>
          </div>
        </div>
      </div>
    </footer>
  );
}
