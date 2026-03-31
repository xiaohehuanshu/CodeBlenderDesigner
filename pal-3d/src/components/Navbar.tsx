import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { motion } from 'motion/react';
import { cn } from '@/src/lib/utils';

const navItems = [
  { name: '首页', path: '/' },
  { name: '工作流', path: '/workflow' },
  { name: '案例', path: '/cases' },
  { name: '文档', path: '/docs' },
  { name: '关于', path: '/about' },
];

export function Navbar() {
  const location = useLocation();

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-bg-warm/80 backdrop-blur-md border-bottom border-border-subtle">
      <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2 group">
          <div className="w-8 h-8 bg-ink flex items-center justify-center text-bg-warm font-bold text-[10px] tracking-tighter group-hover:bg-accent transition-colors">
            PAL
          </div>
          <span className="font-sans font-semibold tracking-tight text-lg">Pal 3D</span>
        </Link>

        <div className="hidden md:flex items-center gap-10">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={cn(
                "text-sm font-medium tracking-wide transition-colors hover:text-accent relative py-1",
                location.pathname === item.path ? "text-ink" : "text-ink/50"
              )}
            >
              {item.name}
              {location.pathname === item.path && (
                <motion.div
                  layoutId="nav-underline"
                  className="absolute bottom-0 left-0 right-0 h-0.5 bg-accent"
                  transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
                />
              )}
            </Link>
          ))}
        </div>

        <div className="flex items-center gap-4">
          <button className="text-xs font-mono uppercase tracking-widest border border-ink/20 px-4 py-2 hover:bg-ink hover:text-bg-warm transition-all">
            GitHub
          </button>
        </div>
      </div>
    </nav>
  );
}
