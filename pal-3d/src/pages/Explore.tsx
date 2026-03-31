import React, { useState } from 'react';
import { motion } from 'motion/react';
import { Send, Terminal, Box, Database, FileText, Cpu, Info, Sparkles } from 'lucide-react';
import { cn } from '@/src/lib/utils';

const mockHistory = [
  { role: 'system', content: 'Pal 3D 已就绪。等待输入设计简报...' },
  { role: 'user', content: '生成一个位于山地环境的观景台方案。要求：1. 悬挑结构；2. 采用木材与钢材混合；3. 最小化对地形的破坏。' },
  { role: 'assistant', content: '已解析需求。正在通过多节点 Agent 分析山地地形上下文 (site_slope.blend)... 正在合成设计简报并生成 Blender Python 脚本... 脚本已准备就绪。', status: 'success' },
];

const examplePrompts = [
  '参数化螺旋楼梯，高度 12m，踏步宽度 1.2m',
  '基于 Voronoi 算法的建筑外立面遮阳系统',
  '模块化集装箱住宅集群，包含 15 个单元',
];

const quickActions = ['结构验证', '材质分配', '光照模拟', '导出 .blend'];

export function Explore() {
  const [input, setInput] = useState('');

  return (
    <div className="pt-20 min-h-screen lg:h-screen flex flex-col lg:flex-row overflow-hidden bg-bg-warm">
      {/* Left: Interaction Console */}
      <div className="w-full lg:w-1/2 flex flex-col border-r border-border-subtle bg-white overflow-hidden">
        <div className="p-6 border-b border-border-subtle flex items-center justify-between bg-white sticky top-0 z-10">
          <div className="flex items-center gap-3">
            <div className="w-2 h-2 rounded-full bg-accent animate-pulse" />
            <h2 className="text-sm font-bold tracking-tight uppercase font-mono">Design Brief Console v1.0</h2>
          </div>
          <div className="flex items-center gap-4 text-[10px] font-mono text-ink/30 uppercase tracking-widest">
            <span>Status: Connected</span>
            <span>Node: Script_Gen</span>
          </div>
        </div>

        {/* Conversation History */}
        <div className="flex-1 overflow-y-auto p-8 space-y-8 scrollbar-hide">
          {mockHistory.map((msg, i) => (
            <motion.div 
              key={i}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 }}
              className={cn(
                "flex gap-4",
                msg.role === 'user' ? "items-start" : "items-center"
              )}
            >
              <div className={cn(
                "w-8 h-8 flex items-center justify-center shrink-0 text-[10px] font-mono font-bold border",
                msg.role === 'user' ? "bg-ink text-white border-ink" : "bg-bg-warm text-ink/40 border-border-subtle"
              )}>
                {msg.role === 'user' ? 'USR' : 'SYS'}
              </div>
              <div className={cn(
                "text-sm leading-relaxed",
                msg.role === 'user' ? "text-ink font-medium" : "text-ink/50 font-mono"
              )}>
                {msg.content}
                {msg.status === 'success' && (
                  <div className="mt-2 flex gap-2">
                    <span className="px-2 py-0.5 bg-green-100 text-green-700 text-[10px] rounded-full">VALIDATED</span>
                    <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-[10px] rounded-full">SCRIPT_READY</span>
                  </div>
                )}
              </div>
            </motion.div>
          ))}
        </div>

        {/* Input Area */}
        <div className="p-8 border-t border-border-subtle bg-bg-warm/30">
          <div className="mb-6">
            <div className="text-[10px] font-mono uppercase tracking-widest text-ink/30 mb-3">快速操作 (Quick Actions)</div>
            <div className="flex flex-wrap gap-2">
              {quickActions.map(action => (
                <button key={action} className="px-3 py-1 bg-white border border-border-subtle text-[10px] font-medium hover:border-accent hover:text-accent transition-all">
                  {action}
                </button>
              ))}
            </div>
          </div>

          <div className="relative">
            {/* Large red outlined input box */}
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="输入您的设计简报或指令..."
              className="w-full h-40 bg-white border-2 border-accent focus:ring-2 focus:ring-accent/20 p-6 text-base font-sans resize-none outline-none transition-all shadow-lg"
            />
            <button className="absolute bottom-6 right-6 bg-accent text-white px-6 py-3 hover:bg-ink transition-colors flex items-center gap-2 text-sm font-bold shadow-md">
              <span>发送指令</span>
              <Send size={18} />
            </button>
          </div>

          <div className="mt-6">
            <div className="text-[10px] font-mono uppercase tracking-widest text-ink/30 mb-3">示例提示词 (Example Prompts)</div>
            <div className="space-y-2">
              {examplePrompts.map((p, i) => (
                <button 
                  key={i} 
                  onClick={() => setInput(p)}
                  className="block text-[11px] text-ink/40 hover:text-accent transition-colors text-left"
                >
                  • {p}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Right: 3D Exhibition Placeholder */}
      <div className="w-full lg:flex-1 relative flex items-center justify-center bg-[#0F0F0F] overflow-hidden min-h-[400px] lg:min-h-0">
        <div className="architectural-grid absolute inset-0 opacity-10" />
        
        <div className="relative z-10 text-center px-12">
          <motion.div
            animate={{ 
              rotateY: [0, 360],
              rotateX: [0, 10, 0]
            }}
            transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
            className="w-64 h-64 border border-white/10 mx-auto mb-12 flex items-center justify-center relative"
          >
            <Box size={80} className="text-white/20" strokeWidth={1} />
            <div className="absolute inset-0 border border-accent/20 scale-110 animate-pulse" />
            <div className="absolute inset-0 border border-white/5 -rotate-12" />
            
            {/* Future Integration Label */}
            <div className="absolute -bottom-4 left-1/2 -translate-x-1/2 bg-accent px-3 py-1 text-[8px] font-mono text-white uppercase tracking-widest whitespace-nowrap">
              Future 3D Integration
            </div>
          </motion.div>

          <h3 className="text-white/80 text-xl font-bold mb-4 tracking-tight">3D 实时预览空间 (Placeholder)</h3>
          <p className="text-white/30 text-sm max-w-sm mx-auto leading-relaxed mb-8">
            此处将集成实时 Blender 渲染引擎。当前作为占位符展示，未来将通过后端或 3D 引擎集成，支持生成的几何体实时 3D 交互与上下文预览。
          </p>
          
          <div className="flex items-center justify-center gap-8">
            <div className="text-center">
              <div className="text-white/10 mb-2"><Database size={20} className="mx-auto" /></div>
              <div className="text-[10px] font-mono text-white/20 uppercase tracking-widest">Context Sync</div>
            </div>
            <div className="text-center">
              <div className="text-white/10 mb-2"><Cpu size={20} className="mx-auto" /></div>
              <div className="text-[10px] font-mono text-white/20 uppercase tracking-widest">GPU Compute</div>
            </div>
            <div className="text-center">
              <div className="text-white/10 mb-2"><Sparkles size={20} className="mx-auto" /></div>
              <div className="text-[10px] font-mono text-white/20 uppercase tracking-widest">RT Rendering</div>
            </div>
          </div>
        </div>

        {/* Floating Labels */}
        <div className="absolute top-10 right-10 text-right">
          <div className="text-[10px] font-mono text-white/20 uppercase tracking-widest mb-1">Viewport: Perspective</div>
          <div className="text-[10px] font-mono text-white/20 uppercase tracking-widest">Grid: 1.0m</div>
          <div className="mt-4 px-2 py-1 border border-white/10 text-[8px] font-mono text-white/40 uppercase tracking-widest">
            Blender Engine Offline
          </div>
        </div>
        
        <div className="absolute bottom-10 left-10 flex items-center gap-4">
          <div className="w-32 h-px bg-white/10" />
          <span className="text-[10px] font-mono text-white/20 uppercase tracking-widest">
            Waiting for Backend Connection...
          </span>
        </div>
      </div>
    </div>
  );
}
