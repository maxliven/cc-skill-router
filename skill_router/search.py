"""Search engine — bilingual fuzzy search over the skill registry.

Port of search-skill.ps1 to Python. Supports:
- Chinese → English keyword translation (longest-match-first)
- CJK bigram + single-character tokenization
- English word extraction
- Weighted scoring by match location (name > domain > description)
- Domain, group, and type filtering
"""

import re
from typing import Any

# ── Chinese → English keyword map ────────────────────────────────────────────
# Longest-match-first: keys sorted by length descending at lookup time.
# Each Chinese keyword maps to a list of English search terms.

CN_KEYWORD_MAP: dict[str, list[str]] = {
    # Thinking / Logic
    "推理": ["logic", "reasoning"],
    "逻辑": ["logic", "reasoning"],
    "思考": ["thinking", "cognition", "mindset"],
    "思维": ["thinking", "cognition", "mental"],
    "判断": ["decision", "logic", "judgment"],
    "决策": ["decision"],
    "分析": ["analysis", "logic", "deconstruct"],
    "诊断": ["diagnosis", "diagnose", "analysis"],
    "拆解": ["deconstruct", "analysis"],
    "检查": ["check", "audit", "review", "logic"],
    # Creativity
    "创意": ["creativity", "creative", "brainstorm", "idea"],
    "头脑风暴": ["brainstorm", "creativity"],
    "发散": ["brainstorm", "lateral", "diverge"],
    "灵感": ["creativity", "random", "stimulus"],
    "方案": ["alternative", "option", "solution", "creativity"],
    "假设": ["assumption", "hypothesis"],
    "创新": ["innovation", "creativity", "lateral"],
    # Writing
    "写作": ["writing", "prose"],
    "文章": ["writing", "prose", "article"],
    "润色": ["editing", "line-editing", "prose", "polish"],
    "修改": ["edit", "line-editing", "fix"],
    "文笔": ["prose", "writing", "elevation"],
    "语法": ["line-editing", "language"],
    "文案": ["copy", "writing"],
    "报告": ["report", "writing"],
    "故事": ["narrative", "story", "plot", "character"],
    "叙事": ["narrative"],
    "对话": ["dialogue", "character"],
    "结构": ["structure", "restructure", "plot", "arc"],
    "论证": ["argument", "rhetoric", "logic"],
    # Psychology / Emotion
    "心理": ["psychology", "mental", "cognitive"],
    "情绪": ["emotion", "emotional", "motivation"],
    "动机": ["motivation", "incentive"],
    "抗拒": ["resistance", "objection"],
    "信任": ["trust"],
    "偏见": ["bias", "heuristic", "prejudice"],
    "认知": ["cognition", "cognitive", "mental"],
    # Strategy
    "战略": ["strategy", "positioning"],
    "策略": ["strategy", "terrain", "positioning"],
    "博弈": ["game-theory", "game"],
    "谈判": ["game-theory", "coalition", "coordination"],
    "竞争": ["competition", "arms-race", "strategy"],
    "联盟": ["coalition", "alliance"],
    "时机": ["timing", "temporal"],
    # Systems
    "系统": ["systems", "emergence", "feedback", "leverage"],
    "反馈": ["feedback"],
    "杠杆": ["leverage"],
    "涌现": ["emergence"],
    "网络": ["network", "connection"],
    # Ethics
    "伦理": ["ethics", "ethical"],
    "道德": ["ethics", "ethical"],
    # Design
    "设计": ["design", "simplicity", "iteration"],
    "简化": ["simplicity", "reduce"],
    # Communication
    "沟通": ["communication", "audience"],
    "表达": ["framing", "rhetoric", "communication"],
    "演讲": ["rhetoric", "audience"],
    "说服": ["persuasion", "rhetoric"],
    # Learning
    "学习": ["learning", "growth", "metacognition"],
    "元认知": ["metacognition", "cognition"],
    # Research
    "搜索": ["search", "investigation"],
    "调查": ["investigation", "source", "evidence"],
    "研究": ["research", "investigation"],
    "文献": ["lit-search", "literature", "search"],
    "证据": ["evidence", "source", "triangulation"],
    "溯源": ["source-trace", "trace"],
    # Efficiency
    "效率": ["optimize", "resource", "bottleneck"],
    "优化": ["optimization", "improvement"],
    "资源": ["resource", "allocation"],
    "瓶颈": ["bottleneck"],
    # Writing tools
    "大纲": ["executive-summary", "report", "restructure", "arc"],
    "摘要": ["executive-summary", "compression"],
    "提纲": ["executive-summary", "arc", "restructure"],
    "压缩": ["compression", "summarize"],
    # Aesthetic
    "美学": ["aesthetic", "elegance", "coherence", "beauty"],
    "风格": ["aesthetic", "tone", "voice"],
    "语气": ["tone", "voice"],
    "连贯": ["coherence", "consistency"],
    # Identity
    "身份": ["identity", "values", "character"],
    "价值观": ["values", "identity"],
    "使命": ["mission", "goal"],
    # Future / Time
    "未来": ["future", "temporal", "foresight"],
    "预测": ["foresight", "probability", "timing"],
    "趋势": ["trend", "cycle", "evolution"],
    "历史": ["historical", "precedent", "cycle"],
    "时间": ["temporal", "timing"],
    # Evolution / Ecology
    "进化": ["evolution", "niche", "fitness"],
    "生态": ["ecology", "niche", "system"],
    "适应": ["fitness", "evolution", "niche"],
    # Play / Game
    "游戏": ["play", "game", "gamification"],
    "反转": ["reversal", "inversion", "provocation"],
    # Probability
    "概率": ["probability", "risk", "expected-value"],
    "风险": ["risk", "probability", "premortem"],
    "场景": ["scenario", "premortem", "future"],
    # Generic tools
    "代码": ["code-review", "fixer", "coding"],
    "审查": ["review", "audit", "check"],
    "评论": ["review", "feedback"],
    "重构": ["restructure", "simplicity", "fixer"],
    "调试": ["fixer", "diagnosis"],
    # Ponytail
    "债务": ["debt"],
    "技术债务": ["debt"],
    "收益": ["gain", "value"],
    "帮助": ["help", "onboarding"],
    "入职": ["help", "onboarding"],
    "审计": ["audit", "review", "debt"],
}

# CJK Unicode range
_CJK_PATTERN = re.compile(r"[一-鿿㐀-䶿豈-﫿]")


def _tokenize(query: str) -> list[str]:
    """Break a query into search tokens.

    Returns: English words + CJK bigrams + CJK singles + translated keywords.
    """
    query_lower = query.lower().strip()
    tokens: list[str] = []

    # 1. English words
    english_words = [w for w in query_lower.split() if re.search(r"[a-z]", w)]
    tokens.extend(english_words)

    # 2. CJK bigrams (consecutive CJK pairs for fuzzy matching)
    bigrams: list[str] = []
    for i in range(len(query_lower) - 1):
        pair = query_lower[i : i + 2]
        if _CJK_PATTERN.search(pair):
            bigrams.append(pair)
    tokens.extend(bigrams)

    # 3. Individual CJK characters
    singles = [c for c in query_lower if _CJK_PATTERN.match(c)]
    tokens.extend(singles)

    # 4. Chinese → English keyword translation (longest-match-first)
    sorted_keys = sorted(CN_KEYWORD_MAP.keys(), key=len, reverse=True)
    remaining = query_lower
    cn_keywords: list[str] = []
    for key in sorted_keys:
        if key in remaining:
            cn_keywords.extend(CN_KEYWORD_MAP[key])
            remaining = remaining.replace(key, "")
    tokens.extend(cn_keywords)

    # Deduplicate, keep order, filter empty
    seen: set[str] = set()
    unique: list[str] = []
    for t in tokens:
        if t and t not in seen:
            seen.add(t)
            unique.append(t)

    return unique


def _calculate_score(
    terms: list[str],
    name: str,
    description: str,
    domain: str,
    skill_type: str,
) -> float:
    """Score a skill against search terms.

    Weights:
        - Name match: 3.0 (strongest signal)
        - Domain match: 2.0
        - Description/type match: 1.5
        - Single-char CJK: 1.5 (name), 1.0 (domain), 0.3 (elsewhere)

    Returns: Score 0.0–10.0.
    """
    target = f"{name} {description} {domain} {skill_type}".lower()
    name_lower = name.lower()
    domain_lower = domain.lower()
    score = 0.0

    for term in terms:
        term_str = str(term)

        if len(term_str) <= 1:
            # Single character — low weight, still useful for CJK
            if term_str in target:
                if term_str in name_lower:
                    score += 1.5
                elif term_str in domain_lower:
                    score += 1.0
                else:
                    score += 0.3
            continue

        if term_str in target:
            if term_str in name_lower:
                score += 3.0
            elif term_str in domain_lower:
                score += 2.0
            else:
                score += 1.5

    return round(min(score, 10.0), 1)


def search(
    query: str,
    registry: dict[str, dict[str, Any]],
    top: int = 5,
    domain: str = "",
    group: str = "",
    skill_type: str = "",
) -> list[dict[str, Any]]:
    """Search the skill registry for matching skills.

    Args:
        query: User's request or problem description (Chinese or English).
        registry: The skill registry dict (name → entry).
        top: Number of results to return.
        domain: Filter by domain (e.g., 'creativity', 'ethics').
        group: Filter by high-level group (thinking/coding/tools/content/
               persona/runbook/infra).
        skill_type: Filter by skill type (s4h/dbs/ponytail/tool/plugin/other).

    Returns:
        List of matching entries with added 'score' field, sorted descending.
    """
    terms = _tokenize(query)

    results: list[dict[str, Any]] = []
    for name, entry in registry.items():
        # Apply filters
        if domain and entry.get("domain") != domain:
            continue
        if group and entry.get("group") != group:
            continue
        if skill_type and entry.get("type") != skill_type:
            continue

        score = _calculate_score(
            terms,
            name=name,
            description=entry.get("description", ""),
            domain=entry.get("domain", ""),
            skill_type=entry.get("type", ""),
        )

        if score > 0:
            result = dict(entry)
            result["score"] = score
            results.append(result)

    # Sort by score descending, then by name
    results.sort(key=lambda r: (-r["score"], r["name"]))

    return results[:top]
