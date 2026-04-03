import React, { Suspense, useState, useEffect } from 'react';
import { motion } from 'motion/react';
import { Terminal, Box, FileText, Layers, ArrowRight, CheckCircle2, Cpu, Database, Layout, Search, Loader2 } from 'lucide-react';
import { Link } from 'react-router-dom';
import { cn } from '@/src/lib/utils';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, useGLTF, Environment } from '@react-three/drei';

// 3D Model component
function Model({ url }: { url: string }) {
  const { scene } = useGLTF(url);
  return <primitive object={scene} />;
}

// Simple loading spinner
function LoadingSpinner() {
  return (
    <div className="absolute inset-0 flex flex-col items-center justify-center bg-white/5 z-10">
      <Loader2 className="w-8 h-8 text-accent animate-spin" />
      <span className="mt-3 text-xs text-white/40 font-mono">Loading...</span>
    </div>
  );
}

// 3D Viewer for cards
function CardModelViewer({ url }: { url: string }) {
  const [isLoading, setIsLoading] = useState(true);

  return (
    <div className="relative w-full h-full">
      {isLoading && <LoadingSpinner />}
      <Canvas
        camera={{ position: [4, 3, 4], fov: 40 }}
        dpr={[1, 2]}
        className="w-full h-full"
        onCreated={() => setIsLoading(false)}
      >
        <Suspense fallback={null}>
          <ambientLight intensity={0.6} />
          <directionalLight position={[5, 5, 5]} intensity={0.8} />
          <Environment preset="city" />
          <Model url={url} />
          <OrbitControls
            enableZoom={true}
            enablePan={false}
            autoRotate
            autoRotateSpeed={2}
            minPolarAngle={Math.PI / 4}
            maxPolarAngle={Math.PI * 0.75}
            minDistance={2}
            maxDistance={10}
          />
        </Suspense>
      </Canvas>
    </div>
  );
}

export function Home() {
  return (
    <div className="pt-20">
      {/* Hero Section */}
      <section className="relative min-h-[90vh] flex items-center overflow-hidden px-6">
        <div className="architectural-grid absolute inset-0 -z-10" />
        
        <div className="max-w-7xl mx-auto w-full grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
          <motion.div 
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, ease: "easeOut" }}
          >
            <div className="inline-block px-3 py-1 bg-accent/10 text-accent text-[10px] font-mono uppercase tracking-[0.2em] mb-6">
              Pal 3D - AI for Making
            </div>
            <h1 className="text-6xl lg:text-8xl font-sans font-bold leading-[0.9] tracking-tighter mb-8">
              Pal 3D
            </h1>
            <p className="text-xl text-ink/60 font-sans max-w-lg mb-10 leading-relaxed">
              AI for Making
            </p>
            
            <div className="flex items-center gap-6">
              <Link to="/explore" className="bg-ink text-bg-warm px-8 py-4 text-sm font-medium hover:bg-accent transition-colors flex items-center gap-2">
                开始探索 <ArrowRight size={16} />
              </Link>
              <Link to="/tutorial" className="text-ink/40 hover:text-ink text-sm font-medium transition-colors">
                新手教程 →
              </Link>
            </div>
          </motion.div>

          <motion.div 
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 1, delay: 0.2 }}
            className="relative"
          >
            <div className="brief-console shadow-2xl relative z-10">
              <div className="flex items-center gap-2 mb-4 border-b border-white/10 pb-3">
                <div className="w-2 h-2 rounded-full bg-red-500/50" />
                <div className="w-2 h-2 rounded-full bg-yellow-500/50" />
                <div className="w-2 h-2 rounded-full bg-green-500/50" />
                <span className="ml-2 text-[10px] uppercase tracking-widest opacity-40">Design Brief Console</span>
              </div>
              <div className="space-y-4">
                <div className="flex gap-3">
                  <span className="text-accent shrink-0">IN:</span>
                  <p className="text-white/80">生成一个位于滨海地区的现代博物馆方案。要求：1. 包含三个相互交织的几何体块；2. 采用参数化表皮系统；3. 内部空间需考虑自然采光优化。</p>
                </div>
                <div className="flex gap-3">
                  <span className="text-blue-400 shrink-0">REF:</span>
                  <p className="text-white/40 italic">/assets/site_context.blend, /rules/facade_logic.md</p>
                </div>
                <div className="pt-4 border-t border-white/5 flex gap-3">
                  <span className="text-green-400 shrink-0">OUT:</span>
                  <div className="text-green-400/80">
                    <p>Processing nodes [1-8]...</p>
                    <p>Generating Blender Python script...</p>
                    <p>Validation: Structural check passed (98%)</p>
                    <p className="animate-pulse">Rendering preview in context...</p>
                  </div>
                </div>
              </div>
            </div>
            
            {/* 3D Placeholder */}
            <div className="absolute -top-10 -right-10 -bottom-10 -left-10 bg-gradient-to-br from-accent/5 to-transparent rounded-full blur-3xl -z-10" />
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[120%] h-[120%] border border-ink/5 rounded-full -z-20 animate-[spin_60s_linear_infinite]" />
          </motion.div>
        </div>
      </section>

      {/* Workflow Section */}
      <section className="py-32 bg-white border-y border-border-subtle">
        <div className="max-w-7xl mx-auto px-6">
          <div className="mb-20">
            <h2 className="text-4xl font-bold tracking-tight mb-4">核心工作流</h2>
            <p className="text-ink/50 max-w-xl">系统通过四个关键阶段，将抽象的设计意图转化为精确的几何实体与验证报告。</p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            {[
              { title: 'Synthesize 综合', desc: '整合多源需求与上下文，合成结构化的设计简报 (Design Brief)。', icon: <FileText className="text-accent" /> },
              { title: 'Reasoning 推理', desc: '基于 LangGraph 的多节点逻辑，推演空间布局与几何关系。', icon: <Search className="text-accent" /> },
              { title: 'Generate 生成', desc: '自动生成可执行的 Blender Python 脚本，实现几何实体化。', icon: <Cpu className="text-accent" /> },
              { title: 'Iterate 迭代', desc: '通过运行时验证与反馈循环，支持设计的持续修正与优化。', icon: <CheckCircle2 className="text-accent" /> },
            ].map((step, i) => (
              <motion.div 
                key={i}
                whileHover={{ y: -5 }}
                className="p-8 border border-border-subtle hover:border-accent/30 transition-all"
              >
                <div className="mb-6">{step.icon}</div>
                <h3 className="text-lg font-bold mb-3">{step.title}</h3>
                <p className="text-sm text-ink/50 leading-relaxed">{step.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Input/Output Grid */}
      <section className="py-32 px-6">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-24">
            <div>
              <div className="flex items-center gap-2 text-accent font-mono text-[10px] tracking-[0.3em] uppercase mb-6">
                <Database size={14} /> Input Sources
              </div>
              <h2 className="text-4xl font-bold mb-12">多源输入整合</h2>
              <div className="space-y-8">
                {[
                  { name: '设计简报 (Design Prompt)', desc: '自然语言描述的设计意图与功能需求。' },
                  { name: '参考图像 (Reference Images)', desc: '视觉风格、材质参考与形式启发。' },
                  { name: 'Markdown 规则', desc: '结构化的设计规范、尺寸约束与逻辑定义。' },
                  { name: '几何上下文 (.blend)', desc: '现有的场地模型、周边建筑与地形数据。' },
                ].map((item, i) => (
                  <div key={i} className="flex gap-6 group">
                    <div className="text-ink/20 font-mono text-sm mt-1">0{i+1}</div>
                    <div>
                      <h4 className="font-bold mb-1 group-hover:text-accent transition-colors">{item.name}</h4>
                      <p className="text-sm text-ink/50">{item.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <div className="flex items-center gap-2 text-accent font-mono text-[10px] tracking-[0.3em] uppercase mb-6">
                <Layout size={14} /> System Outputs
              </div>
              <h2 className="text-4xl font-bold mb-12">专业级输出成果</h2>
              <div className="grid grid-cols-2 gap-6">
                {[
                  { name: 'Blender 脚本', icon: <Terminal size={20} /> },
                  { name: '工程源文件', icon: <Box size={20} /> },
                  { name: '内存日志', icon: <Layers size={20} /> },
                  { name: '追踪报告', icon: <FileText size={20} /> },
                ].map((item, i) => (
                  <div key={i} className="p-6 bg-white border border-border-subtle flex flex-col items-center justify-center text-center group hover:bg-ink hover:text-white transition-all">
                    <div className="mb-4 text-accent group-hover:text-accent-muted">{item.icon}</div>
                    <span className="text-sm font-medium">{item.name}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Case Studies */}
      <section className="py-32 bg-ink text-bg-warm">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex justify-between items-end mb-20">
            <div>
              <h2 className="text-4xl font-bold mb-4">建筑设计案例</h2>
              <p className="text-white/40 max-w-md">探索 Pal 3D 在实际复杂建筑场景中的应用表现。</p>
            </div>
            <button className="text-sm font-medium border-b border-white/20 pb-1 hover:text-accent hover:border-accent transition-all">
              查看全部案例
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-10">
            {[
              {
                title: '参数化滨海博物馆',
                tag: '文化建筑',
                model: '/test.glb',
                desc: '通过流体动力学模拟生成的有机建筑形态，优化了海风循环与自然采光。'
              },
              {
                title: '高层办公集群优化',
                tag: '商业综合体',
                model: '/test.glb',
                desc: '基于日照分析自动调整楼体间距与立面遮阳系统，降低能耗。'
              },
              {
                title: '模块化社区中心',
                tag: '公共空间',
                model: '/test.glb',
                desc: '利用预制构件逻辑生成的灵活空间，支持多种社区活动场景切换。'
              },
            ].map((item, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
                className="group"
              >
                <div className="aspect-[4/3] overflow-hidden mb-6 bg-gradient-to-br from-white/10 to-white/5 relative cursor-pointer">
                  <CardModelViewer url={item.model} />
                </div>
                <div className="flex items-center gap-3 mb-3">
                  <span className="text-[10px] font-mono uppercase tracking-widest text-accent">{item.tag}</span>
                  <div className="h-px flex-1 bg-white/10" />
                </div>
                <h3 className="text-xl font-bold mb-3">{item.title}</h3>
                <p className="text-sm text-white/40 leading-relaxed">{item.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer CTA */}
      <section className="py-40 text-center px-6">
        <div className="max-w-2xl mx-auto">
          <h2 className="text-4xl font-bold mb-8">准备好革新您的设计工作流了吗？</h2>
          <p className="text-ink/50 mb-12">加入我们的学术研究社区，探索基于 Pal 3D 的建筑设计与 AI 协同的无限可能。</p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link to="/docs" className="w-full sm:w-auto bg-ink text-bg-warm px-10 py-4 font-medium hover:bg-accent transition-colors text-center">
              阅读文档
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
