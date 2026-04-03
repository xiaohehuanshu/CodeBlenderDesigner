import React from 'react';
import { motion } from 'motion/react';
import { MousePointer2, RotateCw, ZoomIn, Box, Eye, Layout, ArrowRight, Home, FileText, Search } from 'lucide-react';
import { Link } from 'react-router-dom';

export function Tutorial() {
  return (
    <div className="pt-32 pb-20 px-6 bg-bg-warm">
      <div className="max-w-4xl mx-auto">
        <header className="mb-20 text-center">
          <div className="inline-block px-3 py-1 bg-accent/10 text-accent text-[10px] font-mono uppercase tracking-[0.2em] mb-6">
            User Guide
          </div>
          <h1 className="text-5xl font-bold tracking-tight mb-6">网站使用指南</h1>
          <p className="text-xl text-ink/50 leading-relaxed">
            欢迎使用 Pal 3D。本指南将带您快速了解网站功能与 3D 模型查看技巧。
          </p>
        </header>

        <div className="space-y-24">
          {/* Section 1: 3D View Controls */}
          <section>
            <div className="flex items-center gap-4 mb-8">
              <div className="w-12 h-12 bg-ink text-white flex items-center justify-center font-bold text-xl">01</div>
              <h2 className="text-2xl font-bold">3D 模型查看操作</h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {[
                {
                  title: '旋转视角',
                  desc: '按住鼠标左键拖动，即可 360° 旋转查看模型',
                  icon: <RotateCw className="text-accent" size={24} />
                },
                {
                  title: '缩放模型',
                  desc: '滚动鼠标滚轮，放大或缩小查看细节',
                  icon: <ZoomIn className="text-accent" size={24} />
                },
                {
                  title: '平移视角',
                  desc: '按住鼠标右键拖动，平移查看不同角度',
                  icon: <MousePointer2 className="text-accent" size={24} />
                },
              ].map((item, i) => (
                <div key={i} className="p-6 bg-white border border-border-subtle shadow-sm text-center">
                  <div className="mb-4 flex justify-center">{item.icon}</div>
                  <h4 className="font-bold mb-2">{item.title}</h4>
                  <p className="text-sm text-ink/50">{item.desc}</p>
                </div>
              ))}
            </div>
          </section>

          {/* Section 2: Navigation */}
          <section>
            <div className="flex items-center gap-4 mb-8">
              <div className="w-12 h-12 bg-ink text-white flex items-center justify-center font-bold text-xl">02</div>
              <h2 className="text-2xl font-bold">网站导航说明</h2>
            </div>
            <div className="space-y-4">
              {[
                {
                  name: '首页',
                  path: '/',
                  icon: <Home size={20} />,
                  desc: '浏览精选 3D 案例展示，支持交互式查看'
                },
                {
                  name: '工作流',
                  path: '/workflow',
                  icon: <Layout size={20} />,
                  desc: '了解 Pal 3D 的 8 节点工作流架构'
                },
                {
                  name: '案例',
                  path: '/cases',
                  icon: <Box size={20} />,
                  desc: '查看更多详细的项目案例研究'
                },
                {
                  name: '文档',
                  path: '/docs',
                  icon: <FileText size={20} />,
                  desc: '阅读技术文档与 API 说明'
                },
                {
                  name: '探索',
                  path: '/explore',
                  icon: <Search size={20} />,
                  desc: '体验交互式设计控制台'
                },
              ].map((item, i) => (
                <Link
                  key={i}
                  to={item.path}
                  className="flex items-center gap-4 p-5 bg-white border border-border-subtle hover:border-accent hover:shadow-md transition-all group"
                >
                  <div className="w-10 h-10 bg-ink/5 flex items-center justify-center text-accent group-hover:bg-accent group-hover:text-white transition-colors">
                    {item.icon}
                  </div>
                  <div className="flex-1">
                    <h4 className="font-bold">{item.name}</h4>
                    <p className="text-sm text-ink/50">{item.desc}</p>
                  </div>
                  <ArrowRight size={18} className="text-ink/20 group-hover:text-accent group-hover:translate-x-1 transition-all" />
                </Link>
              ))}
            </div>
          </section>

          {/* Section 3: Case Viewing */}
          <section>
            <div className="flex items-center gap-4 mb-8">
              <div className="w-12 h-12 bg-ink text-white flex items-center justify-center font-bold text-xl">03</div>
              <h2 className="text-2xl font-bold">案例查看技巧</h2>
            </div>
            <div className="bg-white border border-border-subtle p-8 space-y-6">
              <div className="flex items-start gap-4">
                <Eye className="text-accent shrink-0 mt-1" size={20} />
                <div>
                  <h4 className="font-bold mb-2">首页预览</h4>
                  <p className="text-sm text-ink/60">首页展示三个精选案例，鼠标悬停在卡片上即可看到交互效果。直接在卡片上拖拽可旋转查看 3D 模型。</p>
                </div>
              </div>
              <div className="flex items-start gap-4">
                <Box className="text-accent shrink-0 mt-1" size={20} />
                <div>
                  <h4 className="font-bold mb-2">详细案例页</h4>
                  <p className="text-sm text-ink/60">点击"查看全部案例"进入案例列表，选择感兴趣的案例查看详细设计说明与更多展示图。</p>
                </div>
              </div>
              <div className="flex items-start gap-4">
                <Search className="text-accent shrink-0 mt-1" size={20} />
                <div>
                  <h4 className="font-bold mb-2">探索控制台</h4>
                  <p className="text-sm text-ink/60">进入"探索"页面体验交互式设计控制台，查看 AI 如何处理设计需求。</p>
                </div>
              </div>
            </div>
          </section>

          {/* Section 4: Tips */}
          <section>
            <div className="flex items-center gap-4 mb-8">
              <div className="w-12 h-12 bg-ink text-white flex items-center justify-center font-bold text-xl">04</div>
              <h2 className="text-2xl font-bold">使用小贴士</h2>
            </div>
            <div className="p-8 bg-accent/5 border border-accent/20 rounded-xl">
              <ul className="space-y-4 text-sm text-ink/70">
                <li className="flex gap-3">
                  <span className="text-accent font-bold">•</span>
                  <span><strong>最佳体验：</strong>建议使用桌面端浏览器访问，以获得最佳的 3D 交互体验。</span>
                </li>
                <li className="flex gap-3">
                  <span className="text-accent font-bold">•</span>
                  <span><strong>自动旋转：</strong>首页案例模型支持自动旋转展示，手动操作时会暂停自动旋转。</span>
                </li>
                <li className="flex gap-3">
                  <span className="text-accent font-bold">•</span>
                  <span><strong>加载速度：</strong>3D 模型文件较大，首次加载可能需要几秒钟，请耐心等待。</span>
                </li>
                <li className="flex gap-3">
                  <span className="text-accent font-bold">•</span>
                  <span><strong>快捷导航：</strong>点击顶部导航栏可快速切换页面，底部 Footer 也有完整导航。</span>
                </li>
              </ul>
            </div>
          </section>
        </div>

        <div className="mt-32 p-12 bg-ink text-white text-center">
          <h2 className="text-3xl font-bold mb-6">准备开始探索了吗？</h2>
          <p className="text-white/50 mb-10">现在就返回首页，体验 3D 模型交互查看。</p>
          <Link to="/" className="inline-flex items-center gap-2 bg-accent text-white px-10 py-4 font-bold hover:bg-white hover:text-ink transition-all">
            返回首页 <ArrowRight size={18} />
          </Link>
        </div>
      </div>
    </div>
  );
}
