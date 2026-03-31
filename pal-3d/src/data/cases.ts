export interface CaseStudy {
  id: string;
  title: string;
  shortIntro: string;
  status: string;
  previewImg: string;
  resultSummary: string;
  category: string;
  date: string;
  author: string;
  
  // Detail page fields
  background: string;
  goal: string;
  prompt: string;
  refImages: string[];
  workflow: string[];
  resultDetail: string;
  gallery: string[];
  refinementNotes: string;
}

export const caseStudies: CaseStudy[] = [
  {
    id: 'cultural-center',
    title: '文化中心体块生成',
    shortIntro: '基于城市肌理与视线廊道的复杂公共建筑体块推演。',
    status: '已完成',
    previewImg: 'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&q=80&w=1600',
    resultSummary: '成功生成了 12 组符合容积率要求且具备动态视觉效果的初步方案。',
    category: '公共建筑',
    date: '2025.10',
    author: 'CBD Lab - Team Alpha',
    background: '该项目位于高密度城市核心区，周边环境复杂，需在满足严苛的日照退让与视线保护前提下，创造一个具有标志性的文化地标。',
    goal: '在 15,000 平方米的基地内，推演一个包含剧场、图书馆与展览空间的综合体块，强调公共空间的流动性。',
    prompt: 'Generate a cultural center massing with a flowing public atrium. Respect the 45-degree height limit from the northern residential block. Maximize views towards the eastern park. Use a modular structural grid of 9x9m.',
    refImages: [
      'https://images.unsplash.com/photo-1503387762-592dee58292b?auto=format&fit=crop&q=80&w=800',
      'https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&q=80&w=800'
    ],
    workflow: [
      '环境上下文解析：提取周边建筑高度与街道推移线。',
      '体块初步生成：基于功能分区比例生成基础体量。',
      '视线廊道切割：根据公园视线轴线进行体块削减。',
      '中庭空间优化：AI 自动寻找最优的垂直交通与采光位置。'
    ],
    resultDetail: '最终生成的方案在保持了 1.2 容积率的同时，创造了一个贯穿建筑全高度的螺旋式公共中庭。建筑形态呈现出一种由城市向公园倾斜的动态姿态，立面逻辑与结构网格高度统一。',
    gallery: [
      'https://images.unsplash.com/photo-1511818966892-d7d671e672a2?auto=format&fit=crop&q=80&w=1200',
      'https://images.unsplash.com/photo-1487958449913-d9a3c611123e?auto=format&fit=crop&q=80&w=1200',
      'https://images.unsplash.com/photo-1518005020251-582c7897655d?auto=format&fit=crop&q=80&w=1200'
    ],
    refinementNotes: '在初始生成中，剧场空间的净高不足。通过在提示词中增加 "Theater clear height > 12m" 的约束，系统在第二轮迭代中自动调整了结构跨度与层高分配，解决了冲突。'
  },
  {
    id: 'tea-house',
    title: '茶室空间生成',
    shortIntro: '探索传统园林精神与现代极简主义结合的小型空间设计。',
    status: '已完成',
    previewImg: 'https://images.unsplash.com/photo-1576013551627-0cc20b96c2a7?auto=format&fit=crop&q=80&w=1600',
    resultSummary: '通过 AI 模拟光影变化，生成了具有禅意氛围的室内外过渡空间。',
    category: '景观建筑',
    date: '2025.11',
    author: 'CBD Lab - Zen Studio',
    background: '项目位于一片竹林边缘，旨在为访客提供一个冥想与品茗的静谧场所。设计核心在于如何处理光影与自然的边界。',
    goal: '设计一个 120 平方米的单层茶室，包含一个室内茶室、一个半室外平台与一个枯山水庭院。',
    prompt: 'Design a minimalist tea house in a bamboo forest. Use timber and translucent glass. Create a blurred boundary between inside and outside. Focus on shadows cast by bamboo. Incorporate a hidden courtyard.',
    refImages: [
      'https://images.unsplash.com/photo-1505275350441-83dcda8eeef5?auto=format&fit=crop&q=80&w=800',
      'https://images.unsplash.com/photo-1545579133-99bb5ab189bd?auto=format&fit=crop&q=80&w=800'
    ],
    workflow: [
      '光影模拟：分析竹林在不同时段的投影规律。',
      '空间序列组织：建立从入口到茶席的心理路径。',
      '材料质感映射：AI 辅助选择具有自然触感的木材与石材。',
      '视口对景优化：精确计算窗框位置以捕捉最美林景。'
    ],
    resultDetail: '生成的方案采用了深挑檐设计，有效地将竹林的阴影引入室内。半透明的玻璃幕墙在清晨和黄昏时分呈现出如宣纸般的质感，完美契合了“虚实结合”的设计初衷。',
    gallery: [
      'https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&q=80&w=1200',
      'https://images.unsplash.com/photo-1590073242678-70ee3fc28e8e?auto=format&fit=crop&q=80&w=1200'
    ],
    refinementNotes: '最初的平面布局中，枯山水庭院显得过于孤立。通过增加 "Integrate courtyard with main tea room via sliding doors" 的指令，系统重新组织了流线，使庭院成为了空间的视觉核心。'
  },
  {
    id: 'roof-facade',
    title: '坡屋顶立面推演',
    shortIntro: '针对传统聚落更新的现代坡屋顶形式与立面节奏研究。',
    status: '进行中',
    previewImg: 'https://images.unsplash.com/photo-1493397862567-47f773c53f3b?auto=format&fit=crop&q=80&w=1600',
    resultSummary: '利用算法生成了 50 余种变化的坡屋顶组合，实现了传统韵律的现代转译。',
    category: '城市更新',
    date: '2026.02',
    author: 'CBD Lab - Urban Renewal Group',
    background: '在老旧城区改造中，如何平衡传统坡屋顶的视觉特征与现代居住对采光、通风的需求是一个核心课题。',
    goal: '为一组联排住宅设计连续且有变化的坡屋顶系统，并推演与之匹配的立面开窗节奏。',
    prompt: 'Generate a series of pitched roofs for a row of houses. Vary the pitch angles between 15 and 35 degrees. Create a rhythmic facade with vertical timber slats. Integrate skylights for attic spaces.',
    refImages: [
      'https://images.unsplash.com/photo-1512917774080-9991f1c4c750?auto=format&fit=crop&q=80&w=800',
      'https://images.unsplash.com/photo-1449156003053-c30670b97635?auto=format&fit=crop&q=80&w=800'
    ],
    workflow: [
      '屋顶形态拓扑：定义坡屋顶的连接逻辑与排水方向。',
      '立面参数化生成：基于内部功能需求自动生成窗墙比。',
      '阴影遮挡分析：确保屋顶起伏不影响邻里采光。',
      '构造节点生成：AI 辅助设计屋脊与檐口的现代交接细节。'
    ],
    resultDetail: '系统生成了一套错落有致的屋顶天际线，立面上的木格栅不仅起到了遮阳作用，还通过疏密变化呼应了屋顶的起伏节奏。整体方案既保留了聚落的亲切感，又具备现代建筑的简洁。',
    gallery: [
      'https://images.unsplash.com/photo-1480074568708-e7b720bb3f09?auto=format&fit=crop&q=80&w=1200',
      'https://images.unsplash.com/photo-1470770841072-f978cf4d019e?auto=format&fit=crop&q=80&w=1200'
    ],
    refinementNotes: '在处理转角建筑时，坡屋顶的交接出现了几何错误。通过引入 "Corner roof resolution: hip roof style" 的特定规则，系统成功修复了拓扑连接，并生成了更具雕塑感的转角形态。'
  }
];
