import React from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'motion/react';
import { ExternalLink, Calendar, User, ArrowRight } from 'lucide-react';
import { caseStudies } from '../data/cases';

export function Cases() {
  return (
    <div className="pt-32 pb-20 px-6 bg-bg-warm/30 min-h-screen">
      <div className="max-w-7xl mx-auto">
        <header className="mb-24">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
          >
            <h1 className="text-6xl font-bold tracking-tight mb-8">案例展示</h1>
            <div className="h-1 w-20 bg-accent mb-8" />
            <p className="text-xl text-ink/50 max-w-2xl leading-relaxed">
              探索 CodeBlenderDesigner 如何将复杂的建筑设计需求转化为精确的生成式方案。
            </p>
          </motion.div>
        </header>

        <div className="space-y-40">
          {caseStudies.map((item, i) => (
            <motion.div 
              key={item.id}
              initial={{ opacity: 0, y: 40 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-100px" }}
              transition={{ duration: 0.8, delay: i * 0.1 }}
              className="grid grid-cols-1 lg:grid-cols-12 gap-16 items-center"
            >
              <div className={`lg:col-span-7 ${i % 2 === 1 ? 'lg:order-2' : ''}`}>
                <Link to={`/cases/${item.id}`} className="block group overflow-hidden bg-white border border-border-subtle shadow-sm hover:shadow-xl transition-all duration-700">
                  <div className="aspect-[16/10] overflow-hidden relative">
                    <img 
                      src={item.previewImg} 
                      alt={item.title} 
                      className="w-full h-full object-cover grayscale group-hover:grayscale-0 group-hover:scale-105 transition-all duration-1000 ease-out"
                      referrerPolicy="no-referrer"
                    />
                    <div className="absolute inset-0 bg-ink/0 group-hover:bg-ink/10 transition-colors duration-700" />
                  </div>
                </Link>
              </div>
              
              <div className={`lg:col-span-5 ${i % 2 === 1 ? 'lg:order-1' : ''}`}>
                <div className="flex items-center gap-4 mb-8">
                  <span className="px-3 py-1 bg-accent/10 text-accent text-[10px] font-mono uppercase tracking-[0.2em] font-bold">
                    {item.category}
                  </span>
                  <div className="h-px w-8 bg-ink/10" />
                  <span className="text-[10px] font-mono text-ink/40 uppercase tracking-widest font-medium">
                    {item.status}
                  </span>
                </div>

                <h2 className="text-4xl font-bold mb-8 leading-tight">{item.title}</h2>
                
                <p className="text-lg text-ink/60 mb-10 leading-relaxed">
                  {item.shortIntro}
                </p>

                <div className="p-8 bg-white border border-border-subtle border-l-4 border-l-accent mb-10 shadow-sm">
                  <div className="text-[10px] font-mono uppercase tracking-[0.2em] text-ink/30 mb-4 font-bold">生成结果摘要</div>
                  <p className="text-sm text-ink/80 leading-relaxed font-medium">{item.resultSummary}</p>
                </div>

                <div className="flex items-center justify-between pt-8 border-t border-border-subtle">
                  <div className="flex gap-8">
                    <div className="flex items-center gap-2 text-[10px] font-mono text-ink/40 uppercase tracking-widest">
                      <Calendar size={12} /> {item.date}
                    </div>
                    <div className="flex items-center gap-2 text-[10px] font-mono text-ink/40 uppercase tracking-widest">
                      <User size={12} /> {item.author}
                    </div>
                  </div>
                  
                  <Link 
                    to={`/cases/${item.id}`} 
                    className="flex items-center gap-3 text-sm font-bold group text-accent hover:text-ink transition-colors"
                  >
                    详情报告 <ArrowRight size={16} className="group-hover:translate-x-2 transition-transform" />
                  </Link>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
}
