import React, { useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { motion } from 'motion/react';
import { ArrowLeft, Calendar, User, CheckCircle2, ChevronRight, Info } from 'lucide-react';
import { caseStudies } from '../data/cases';

export function CaseDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const study = caseStudies.find(s => s.id === id);

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [id]);

  if (!study) {
    return (
      <div className="pt-40 pb-20 px-6 text-center">
        <h1 className="text-2xl font-bold mb-4">未找到案例</h1>
        <Link to="/cases" className="text-accent hover:underline">返回案例列表</Link>
      </div>
    );
  }

  return (
    <div className="pt-32 pb-20 bg-bg-warm/20 min-h-screen">
      <div className="max-w-5xl mx-auto px-6">
        {/* Back Button */}
        <Link 
          to="/cases" 
          className="inline-flex items-center gap-2 text-sm font-mono uppercase tracking-widest text-ink/40 hover:text-accent transition-colors mb-12 group"
        >
          <ArrowLeft size={16} className="group-hover:-translate-x-1 transition-transform" /> 返回案例列表
        </Link>

        {/* Header */}
        <header className="mb-16">
          <div className="flex items-center gap-4 mb-6">
            <span className="px-3 py-1 bg-accent/10 text-accent text-[10px] font-mono uppercase tracking-widest font-bold">
              {study.category}
            </span>
            <span className="text-[10px] font-mono text-ink/30 uppercase tracking-widest">
              {study.status}
            </span>
          </div>
          <h1 className="text-5xl font-bold tracking-tight mb-8 leading-tight">{study.title}</h1>
          
          <div className="flex gap-12 py-8 border-y border-border-subtle">
            <div className="flex flex-col gap-1">
              <span className="text-[10px] font-mono uppercase tracking-widest text-ink/30">发布日期</span>
              <div className="flex items-center gap-2 text-sm font-medium">
                <Calendar size={14} className="text-accent" /> {study.date}
              </div>
            </div>
            <div className="flex flex-col gap-1">
              <span className="text-[10px] font-mono uppercase tracking-widest text-ink/30">研究团队</span>
              <div className="flex items-center gap-2 text-sm font-medium">
                <User size={14} className="text-accent" /> {study.author}
              </div>
            </div>
          </div>
        </header>

        {/* Hero Image */}
        <motion.div 
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 1 }}
          className="aspect-video overflow-hidden bg-white border border-border-subtle mb-20 shadow-xl"
        >
          <img 
            src={study.previewImg} 
            alt={study.title} 
            className="w-full h-full object-cover grayscale hover:grayscale-0 transition-all duration-1000"
            referrerPolicy="no-referrer"
          />
        </motion.div>

        {/* Content Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-16 mb-20">
          <div className="md:col-span-2 space-y-16">
            {/* Background & Goal */}
            <section>
              <h2 className="text-xs font-mono uppercase tracking-[0.3em] text-accent mb-8 font-bold flex items-center gap-2">
                <div className="w-8 h-px bg-accent" /> 项目背景与目标
              </h2>
              <div className="space-y-6">
                <p className="text-lg leading-relaxed text-ink/80">{study.background}</p>
                <div className="p-6 bg-white border-l-2 border-accent shadow-sm">
                  <p className="text-sm font-medium text-ink/70 leading-relaxed italic">
                    <span className="text-accent font-bold not-italic mr-2">目标:</span> {study.goal}
                  </p>
                </div>
              </div>
            </section>

            {/* Prompt Section */}
            <section>
              <h2 className="text-xs font-mono uppercase tracking-[0.3em] text-accent mb-8 font-bold flex items-center gap-2">
                <div className="w-8 h-px bg-accent" /> 输入提示词 (Prompt)
              </h2>
              <div className="bg-ink text-bg-warm p-8 font-mono text-sm leading-relaxed relative overflow-hidden group">
                <div className="absolute top-0 right-0 p-2 opacity-10 group-hover:opacity-20 transition-opacity">
                  <Info size={40} />
                </div>
                <p className="relative z-10">"{study.prompt}"</p>
              </div>
            </section>

            {/* Workflow Summary */}
            <section>
              <h2 className="text-xs font-mono uppercase tracking-[0.3em] text-accent mb-8 font-bold flex items-center gap-2">
                <div className="w-8 h-px bg-accent" /> 工作流摘要
              </h2>
              <div className="space-y-4">
                {study.workflow.map((step, idx) => (
                  <div key={idx} className="flex gap-4 items-start p-4 bg-white border border-border-subtle hover:border-accent transition-colors">
                    <span className="text-[10px] font-mono text-accent font-bold mt-1">0{idx + 1}</span>
                    <p className="text-sm text-ink/70 leading-relaxed">{step}</p>
                  </div>
                ))}
              </div>
            </section>
          </div>

          {/* Sidebar / Ref Images */}
          <div className="space-y-12">
            <section>
              <h3 className="text-[10px] font-mono uppercase tracking-widest text-ink/30 mb-6 font-bold">参考图像</h3>
              <div className="grid grid-cols-1 gap-4">
                {study.refImages.map((img, idx) => (
                  <div key={idx} className="aspect-square overflow-hidden bg-white border border-border-subtle grayscale hover:grayscale-0 transition-all duration-700">
                    <img src={img} alt="Reference" className="w-full h-full object-cover" referrerPolicy="no-referrer" />
                  </div>
                ))}
              </div>
            </section>

            <section className="p-6 bg-accent/5 border border-accent/10">
              <h3 className="text-[10px] font-mono uppercase tracking-widest text-accent mb-4 font-bold">迭代优化说明</h3>
              <p className="text-xs leading-relaxed text-ink/60 italic">
                {study.refinementNotes}
              </p>
            </section>
          </div>
        </div>

        {/* Result Section */}
        <section className="mb-20 pt-20 border-t border-border-subtle">
          <div className="max-w-3xl mb-12">
            <h2 className="text-xs font-mono uppercase tracking-[0.3em] text-accent mb-8 font-bold flex items-center gap-2">
              <div className="w-8 h-px bg-accent" /> 生成结果摘要
            </h2>
            <p className="text-2xl font-bold leading-tight text-ink mb-6">
              {study.resultDetail}
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {study.gallery.map((img, idx) => (
              <motion.div 
                key={idx}
                whileHover={{ scale: 1.02 }}
                className={`overflow-hidden bg-white border border-border-subtle shadow-md ${idx === 0 ? 'md:col-span-2 aspect-[21/9]' : 'aspect-square'}`}
              >
                <img src={img} alt={`Gallery ${idx}`} className="w-full h-full object-cover grayscale hover:grayscale-0 transition-all duration-1000" referrerPolicy="no-referrer" />
              </motion.div>
            ))}
          </div>
        </section>

        {/* Footer Navigation */}
        <div className="flex justify-between items-center pt-20 border-t border-border-subtle">
          <button 
            onClick={() => navigate('/cases')}
            className="text-sm font-bold flex items-center gap-2 hover:text-accent transition-colors"
          >
            <ArrowLeft size={16} /> 返回列表
          </button>
          
          <div className="text-[10px] font-mono uppercase tracking-widest text-ink/20">
            CodeBlenderDesigner Case Study Archive
          </div>
        </div>
      </div>
    </div>
  );
}
