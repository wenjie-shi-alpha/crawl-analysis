#!/usr/bin/env python3
"""
大规模学术研究爬虫 - 目标2000+文档
支持分批处理、断点续爬、并行分析
"""

import json
import os
import sys
import time
import logging
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# 加载环境变量
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# 添加项目路径
sys.path.append(str(Path(__file__).parent / "src"))

from crawling.tavily_crawler import TavilyCrawler
from analysis.enhanced_llm_analyzer import LLMConfig, OllamaClient

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/large_scale_crawl.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# 扩展的学术研究关键词 - 目标支持2000+文档抓取
# ============================================================================

EXTENDED_KEYWORDS = {
    # ===== 核心概念 (15个) =====
    "core_concepts": [
        "绿色电力消费",
        "绿电消费",
        "可再生能源消费",
        "清洁能源消费",
        "绿色电力证书",
        "居民绿色电力",
        "企业绿电采购",
        "绿电交易",
        "绿色电力市场",
        "新能源电力消费",
        "低碳电力消费",
        "零碳电力",
        "可再生能源电力消纳",
        "绿色能源消费",
        "清洁电力采购",
    ],
    
    # ===== 驱动因素 (20个) =====
    "driving_factors": [
        "绿色电力消费 驱动因素",
        "绿电消费 动机",
        "可再生能源购买意愿",
        "绿色电力 环保意识",
        "绿电消费 经济效益",
        "绿色电力 社会责任",
        "清洁能源 消费态度",
        "绿色电力 政策激励",
        "可再生能源 消费行为",
        "绿电消费 影响因素",
        "企业ESG 绿电消费",
        "碳中和 绿电需求",
        "供应链脱碳 绿电采购",
        "绿色金融 新能源消费",
        "绿电溢价支付意愿",
        "环境价值 绿色电力",
        "品牌形象 绿电消费",
        "国际贸易 绿电认证",
        "碳关税 绿电需求",
        "RE100 中国企业",
    ],
    
    # ===== 阻碍因素 (20个) =====
    "barrier_factors": [
        "绿色电力消费 阻碍因素",
        "绿电消费 障碍",
        "可再生能源消费 壁垒",
        "绿色电力 价格阻力",
        "绿电消费 成本问题",
        "绿色电力 信任问题",
        "可再生能源 认知障碍",
        "绿电消费 便捷性",
        "清洁能源 消费障碍",
        "绿色电力 接受度",
        "绿电价格波动 风险",
        "电力市场 信息不对称",
        "绿证 认知度低",
        "绿电交易 制度障碍",
        "新能源消纳 技术瓶颈",
        "储能成本 绿电消费",
        "电网调度 可再生能源",
        "绿电供应 稳定性",
        "跨省绿电交易 壁垒",
        "绿电消费 信息披露",
    ],
    
    # ===== 政策与制度 (25个) =====
    "policy_institutional": [
        "中国 绿色电力政策",
        "绿电交易机制",
        "可再生能源配额制",
        "绿色电力证书 政策",
        "双碳目标 绿色电力",
        "电力市场化改革",
        "绿色电力 补贴政策",
        "碳达峰 电力消费",
        "可再生能源法 绿电",
        "电力体制改革 新能源",
        "绿证交易 制度设计",
        "碳市场 绿电消费",
        "能耗双控 绿电豁免",
        "十四五 可再生能源",
        "新型电力系统 政策",
        "分布式能源 政策支持",
        "售电公司 绿电业务",
        "增量配电 绿色电力",
        "隔墙售电 分布式",
        "绿电交易试点",
        "全国统一电力市场",
        "电力现货市场 绿电",
        "电力中长期交易 绿证",
        "可再生能源消纳责任",
        "绿色电力消费认证",
    ],
    
    # ===== 市场与经济 (20个) =====
    "market_economic": [
        "绿电价格形成机制",
        "绿证价格 影响因素",
        "绿电交易量 趋势",
        "可再生能源 发电成本",
        "风电光伏 平价上网",
        "绿电溢价 成本分析",
        "绿电市场 供需分析",
        "碳价 绿电价格",
        "电力市场 价格信号",
        "绿电PPA 企业采购",
        "虚拟电厂 绿电消费",
        "储能 绿电经济性",
        "分时电价 绿电消费",
        "峰谷电价 可再生能源",
        "容量市场 绿色电力",
        "辅助服务市场 新能源",
        "绿电投资 回报率",
        "新能源项目 经济评价",
        "绿电采购 成本效益",
        "碳资产 绿证价值",
    ],
    
    # ===== 技术与创新 (15个) =====
    "technology_innovation": [
        "智能电网 绿电消费",
        "区块链 绿证溯源",
        "人工智能 电力调度",
        "储能技术 绿电消纳",
        "虚拟电厂 技术",
        "需求响应 新能源",
        "分布式光伏 消费",
        "微电网 绿色电力",
        "V2G 电动汽车 绿电",
        "氢能 绿电制氢",
        "数字化 电力交易",
        "能源互联网 绿电",
        "碳足迹追溯 绿电",
        "电力大数据 新能源",
        "源网荷储 一体化",
    ],
    
    # ===== 行业与场景 (20个) =====
    "industry_scenarios": [
        "数据中心 绿电消费",
        "制造业 绿电采购",
        "钢铁行业 绿色电力",
        "化工行业 绿电消费",
        "建材行业 绿色电力",
        "有色金属 绿电消费",
        "纺织行业 绿电采购",
        "电子制造 绿色电力",
        "汽车制造 绿电消费",
        "食品饮料 绿电采购",
        "商业建筑 绿色电力",
        "工业园区 绿电消费",
        "港口 绿色电力",
        "机场 绿电消费",
        "5G基站 绿色电力",
        "电动汽车 充绿电",
        "轨道交通 绿电消费",
        "零售业 绿色电力",
        "酒店行业 绿电采购",
        "医院 绿色电力消费",
    ],
    
    # ===== 地区研究 (15个) =====
    "regional_studies": [
        "北京 绿电交易",
        "上海 绿色电力",
        "广东 绿电消费",
        "浙江 绿电市场",
        "江苏 可再生能源消费",
        "山东 绿色电力",
        "四川 清洁能源消费",
        "云南 绿电外送",
        "内蒙古 风电消纳",
        "新疆 光伏消纳",
        "甘肃 新能源消费",
        "青海 绿色电力",
        "长三角 绿电交易",
        "粤港澳大湾区 绿电",
        "京津冀 绿色电力",
    ],
    
    # ===== 国际比较 (10个) =====
    "international_comparison": [
        "欧盟 绿电消费 经验",
        "美国 可再生能源消费",
        "德国 绿色电力 政策",
        "日本 绿电市场",
        "韩国 可再生能源配额",
        "碳边境调节机制 CBAM",
        "国际绿证 I-REC",
        "RE100 全球倡议",
        "SBTi 科学碳目标",
        "CDP 碳披露 绿电",
    ],
    
    # ===== 消费者行为 (15个) =====
    "consumer_behavior": [
        "居民 绿电消费意愿",
        "企业 绿电采购决策",
        "消费者 绿色电力认知",
        "绿电消费 心理因素",
        "环保意识 电力消费",
        "社会规范 绿电选择",
        "信任 绿电消费",
        "便利性 绿电购买",
        "价格敏感度 绿电",
        "绿电消费 代际差异",
        "城乡 绿电消费差异",
        "收入水平 绿电消费",
        "教育程度 绿电认知",
        "企业规模 绿电采购",
        "行业属性 绿电消费",
    ],
    
    # ===== 学术研究方法 (10个) =====
    "research_methods": [
        "绿电消费 实证研究",
        "可再生能源 案例分析",
        "绿色电力 问卷调查",
        "绿电市场 计量分析",
        "绿电政策 效果评估",
        "绿色电力 情景分析",
        "可再生能源 系统动力学",
        "绿电消费 结构方程",
        "新能源 博弈分析",
        "绿电市场 仿真模拟",
    ],
}

# 将所有关键词扁平化
ALL_KEYWORDS = []
for category, keywords in EXTENDED_KEYWORDS.items():
    ALL_KEYWORDS.extend(keywords)

# ============================================================================
# 增强的LLM结构化提取提示词
# ============================================================================

ENHANCED_SYSTEM_PROMPT = """你是绿电消费研究助手，请严格输出JSON格式，字段缺失时用null或空数组。

需要的JSON字段（所有字段必须存在）：
{
  "source_type": "academic|policy|news|report|industry|other",
  "publication_type": "期刊论文|会议论文|政策文件|研究报告|新闻报道|行业白皮书|其他",
  "year": "四位年份或null",
  "month": "1-12的数字或null",
  "geography": {
    "country": "国家",
    "province": "省份或null",
    "city": "城市或null",
    "region_type": "全国|区域|省级|市级|园区|企业"
  },
  "sectors": ["行业/场景列表，如钢铁/数据中心/居民/交通"],
  "stakeholders": [
    {"name": "利益相关方名称", "type": "政府|企业|居民|电网|平台|金融|研究机构|国际组织", "stance": -2到2, "role": "推动者|被动接受|观望|阻碍者"}
  ],
  "overall_sentiment": -2到2的数值,
  "policy_refs": [
    {"name": "政策名称", "year": "发布年份", "level": "国家级|省级|市级", "type": "规划|意见|办法|标准|通知"}
  ],
  "drivers": [
    {
      "factor": "驱动因素名称",
      "category": "政治|经济|社会|技术|环境|法律",
      "sub_category": "具体子类",
      "strength_score": 0-5,
      "mechanism": "作用机制简述",
      "evidence": "原文证据",
      "time_sensitivity": "短期|中期|长期"
    }
  ],
  "barriers": [
    {
      "factor": "阻碍因素名称",
      "category": "经济障碍|信息障碍|制度障碍|技术障碍|心理障碍|市场障碍",
      "sub_category": "具体子类",
      "severity_score": 0-5,
      "mechanism": "阻碍机制简述",
      "evidence": "原文证据",
      "solvability": "易解决|中等|困难"
    }
  ],
  "metrics": [
    {
      "name": "指标名称",
      "value": "数值",
      "unit": "单位",
      "year": "年份",
      "trend": "上升|下降|稳定|波动",
      "context": "指标背景说明"
    }
  ],
  "causal_chains": [
    {
      "chain": ["原因1", "中间环节", "结果"],
      "direction": "正向|负向|双向",
      "strength": "强|中|弱",
      "evidence": "因果关系证据"
    }
  ],
  "temporal_info": {
    "historical_period": "涉及的历史时期",
    "current_status": "当前状态描述",
    "future_projection": "未来预测",
    "key_events": [{"event": "事件名称", "year": "年份", "impact": "影响"}]
  },
  "methodology": {
    "type": "实证|案例|调查|评论|实验|模型|政策解读|综述",
    "data_source": "数据来源",
    "sample_size": "样本量",
    "analysis_method": "分析方法",
    "limitations": "研究局限"
  },
  "key_findings": ["核心发现1", "核心发现2"],
  "recommendations": ["政策建议1", "政策建议2"],
  "innovation_points": ["创新点1", "创新点2"],
  "confidence": "high|medium|low",
  "relevance_score": 0-5的相关性评分,
  "keywords_extracted": ["从文本提取的关键词"]
}

重要说明：
1. 所有字段必须存在，无内容用null或空数组
2. 评分标准：0=完全无关/无，1=很弱，2=较弱，3=中等，4=较强，5=很强
3. 情感/立场标准：-2=强烈反对/阻碍，-1=轻微反对，0=中立，1=轻微支持，2=强烈支持
4. 因果链要尽量识别完整的因果路径
5. 时间信息尽量提取，便于时序分析

只输出JSON，不要额外解释文字。
"""

def _truncate(text: str, limit: int = 4000) -> str:
    """截断文本，保留关键信息"""
    return text[:limit]

def build_enhanced_extraction_prompt(item: Dict[str, Any]) -> str:
    """构建增强的提取提示"""
    title = item.get("title", "")
    url = item.get("url", "")
    keyword = item.get("keyword", "")
    content = _truncate(item.get("content", ""))
    return (
        f"请从以下文档中提取结构化信息：\n\n"
        f"【标题】{title}\n"
        f"【URL】{url}\n"
        f"【搜索关键词】{keyword}\n"
        f"【正文内容】\n{content}\n\n"
        f"请严格按照JSON模式输出，所有字段必须存在。"
    )

# ============================================================================
# 数据处理类
# ============================================================================

class LargeScaleCrawler:
    """大规模爬取管理器"""
    
    def __init__(
        self,
        keywords: List[str],
        output_dir: str = "academic_data/large_scale",
        max_results_per_keyword: int = 15,
        batch_size: int = 20,
        checkpoint_interval: int = 50,
    ):
        self.keywords = keywords
        self.output_dir = Path(output_dir)
        self.max_results_per_keyword = max_results_per_keyword
        self.batch_size = batch_size
        self.checkpoint_interval = checkpoint_interval
        
        # 创建目录
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "raw").mkdir(exist_ok=True)
        (self.output_dir / "structured").mkdir(exist_ok=True)
        (self.output_dir / "checkpoints").mkdir(exist_ok=True)
        
        # 初始化状态
        self.seen_urls: Set[str] = set()
        self.seen_content_hashes: Set[str] = set()
        self.processed_keywords: Set[str] = set()
        self.results: List[Dict] = []
        self.structured_results: List[Dict] = []
        
        # 加载检查点
        self._load_checkpoint()
        # 尝试从既有输出中恢复已结构化结果，确保断点续跑不会从空结果开始
        self._load_existing_structured_results()
        
        # 初始化LLM客户端
        llm_config = LLMConfig()
        self.ollama_client = OllamaClient(
            base_url=llm_config.ollama_base_url,
            model=llm_config.ollama_model
        )
        
        # 线程锁
        self.lock = threading.Lock()

    def _load_existing_structured_results(self) -> None:
        """从历史输出恢复 structured_results（用于断点续跑）。

        说明：检查点仅记录 processed_keywords / 去重集合，不包含已产出的结构化记录。
        如果不恢复，遇到 Tavily 配额/网络问题时可能会写出一个“空结果”的新输出文件。
        """

        structured_dir = self.output_dir / "structured"
        if not structured_dir.exists():
            return

        candidates = sorted(structured_dir.glob("large_scale_analysis_*.jsonl"))
        if not candidates:
            return

        for path in reversed(candidates):
            try:
                loaded: List[Dict] = []
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        loaded.append(json.loads(line))
                if loaded:
                    self.structured_results = loaded
                    # We don't have raw `results` content in JSONL; keep a placeholder list for counts.
                    self.results = [{} for _ in range(len(self.structured_results))]
                    logger.info(f"已恢复既有结构化结果: {len(self.structured_results)} 条（来自 {path.name}）")
                    return
            except Exception as e:
                logger.warning(f"恢复既有结构化结果失败: {path} ({e})")
                continue
    
    def _load_checkpoint(self):
        """加载检查点"""
        checkpoint_file = self.output_dir / "checkpoints" / "latest.json"
        if checkpoint_file.exists():
            try:
                with open(checkpoint_file, 'r', encoding='utf-8') as f:
                    checkpoint = json.load(f)
                self.seen_urls = set(checkpoint.get("seen_urls", []))
                self.seen_content_hashes = set(checkpoint.get("seen_content_hashes", []))
                self.processed_keywords = set(checkpoint.get("processed_keywords", []))
                logger.info(f"已加载检查点: {len(self.processed_keywords)}个关键词已处理")
            except Exception as e:
                logger.warning(f"加载检查点失败: {e}")
    
    def _save_checkpoint(self):
        """保存检查点"""
        checkpoint_file = self.output_dir / "checkpoints" / "latest.json"
        checkpoint = {
            "seen_urls": list(self.seen_urls),
            "seen_content_hashes": list(self.seen_content_hashes),
            "processed_keywords": list(self.processed_keywords),
            "timestamp": datetime.now().isoformat(),
        }
        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(checkpoint, f, ensure_ascii=False, indent=2)
        logger.info(f"检查点已保存: {len(self.processed_keywords)}个关键词")
    
    def _content_hash(self, content: str) -> str:
        """计算内容哈希"""
        return hashlib.md5(content.encode()).hexdigest()
    
    def _is_duplicate(self, item: Dict) -> bool:
        """检查是否重复"""
        url = item.get("url", "")
        content = item.get("content", "")
        content_hash = self._content_hash(content)
        
        if url in self.seen_urls:
            return True
        if content_hash in self.seen_content_hashes:
            return True
        
        self.seen_urls.add(url)
        self.seen_content_hashes.add(content_hash)
        return False
    
    def _filter_quality(self, item: Dict) -> bool:
        """质量过滤"""
        title = item.get("title", "")
        content = item.get("content", "")
        
        # 基本长度检查
        if len(title.strip()) < 5 or len(content.strip()) < 100:
            return False
        
        # 相关性检查
        relevance_keywords = [
            "绿电", "绿色电力", "可再生能源", "清洁能源", "新能源",
            "光伏", "风电", "绿证", "碳中和", "碳达峰", "低碳",
            "电力消费", "能源消费", "电力市场", "电力交易"
        ]
        if not any(kw in content for kw in relevance_keywords):
            return False
        
        return True
    
    def crawl_batch(self, keywords: List[str]) -> List[Dict]:
        """批量爬取"""
        crawler = TavilyCrawler(
            keywords=keywords,
            output_dir=str(self.output_dir / "raw"),
            max_results_per_keyword=self.max_results_per_keyword,
            search_depth="advanced"
        )
        return crawler.crawl()
    
    def _safe_json_parse(self, payload: str) -> Optional[Dict]:
        """安全解析JSON"""
        try:
            # 尝试直接解析
            return json.loads(payload)
        except json.JSONDecodeError:
            # 尝试提取JSON部分
            import re
            match = re.search(r'\{[\s\S]*\}', payload)
            if match:
                try:
                    return json.loads(match.group())
                except:
                    pass
        return None
    
    def _fallback_record(self, item: Dict) -> Dict:
        """回退记录"""
        text = item.get("content", "")
        year = None
        for y in range(2025, 2015, -1):
            if str(y) in text:
                year = str(y)
                break
        
        return {
            "source_type": "other",
            "publication_type": "其他",
            "year": year,
            "month": None,
            "geography": {"country": "中国", "province": None, "city": None, "region_type": "全国"},
            "sectors": [],
            "stakeholders": [],
            "overall_sentiment": 0,
            "policy_refs": [],
            "drivers": [],
            "barriers": [],
            "metrics": [],
            "causal_chains": [],
            "temporal_info": {},
            "methodology": {},
            "key_findings": [],
            "recommendations": [],
            "innovation_points": [],
            "confidence": "low",
            "relevance_score": 1,
            "keywords_extracted": [],
            "source_title": item.get("title", ""),
            "url": item.get("url", ""),
            "keyword": item.get("keyword", ""),
            "crawl_time": item.get("crawl_time", ""),
            "extraction_note": "LLM解析失败，使用回退规则"
        }
    
    def extract_structured(self, item: Dict) -> Dict:
        """提取结构化信息"""
        if not self.ollama_client.is_available():
            return self._fallback_record(item)
        
        prompt = build_enhanced_extraction_prompt(item)
        response = self.ollama_client.generate(
            prompt,
            system_prompt=ENHANCED_SYSTEM_PROMPT + "\n不要输出思考过程、不要复述提示词、不要添加任何解释性文字；只输出最终JSON。",
            stream=True,
            options={"temperature": 0, "num_predict": 1800},
        )
        parsed = self._safe_json_parse(response)
        
        if not parsed:
            record = self._fallback_record(item)
            record["extraction_note"] = "LLM返回不可解析JSON"
        else:
            record = {
                **parsed,
                "source_title": item.get("title", ""),
                "url": item.get("url", ""),
                "keyword": item.get("keyword", ""),
                "crawl_time": item.get("crawl_time", ""),
            }
        
        return record
    
    def run(self, max_documents: int = 2000) -> Dict:
        """执行大规模爬取"""
        logger.info("=" * 60)
        logger.info("大规模绿电消费学术研究数据爬取")
        logger.info(f"目标文档数: {max_documents}")
        logger.info(f"总关键词数: {len(self.keywords)}")
        logger.info("=" * 60)
        
        # 过滤已处理的关键词
        remaining_keywords = [k for k in self.keywords if k not in self.processed_keywords]
        logger.info(f"剩余待处理关键词: {len(remaining_keywords)}")
        
        start_time = time.time()
        batch_count = 0
        
        # 分批处理
        for i in range(0, len(remaining_keywords), self.batch_size):
            if len(self.results) >= max_documents:
                logger.info(f"已达到目标文档数 {max_documents}")
                break
            
            batch_keywords = remaining_keywords[i:i + self.batch_size]
            batch_count += 1
            logger.info(f"\n处理批次 {batch_count}: {len(batch_keywords)} 个关键词")
            
            try:
                # 爬取
                batch_results = self.crawl_batch(batch_keywords)
                logger.info(f"  原始结果: {len(batch_results)} 条")
                
                # 去重和过滤
                new_results = []
                for item in batch_results:
                    if not self._is_duplicate(item) and self._filter_quality(item):
                        new_results.append(item)
                
                logger.info(f"  质量过滤后: {len(new_results)} 条")
                
                # 结构化提取
                for item in new_results:
                    structured = self.extract_structured(item)
                    self.structured_results.append(structured)
                    self.results.append(item)
                
                # 更新已处理关键词
                self.processed_keywords.update(batch_keywords)
                
                # 保存检查点
                if batch_count % self.checkpoint_interval == 0:
                    self._save_checkpoint()
                    self._save_intermediate_results()
                
                logger.info(f"  累计文档: {len(self.results)} 条")
                
                # 适当延迟，避免API限流
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"批次 {batch_count} 处理失败: {e}")
                self._save_checkpoint()
                # Tavily quota exceeded: stop early to avoid producing misleading empty outputs.
                msg = str(e)
                if "状态码 432" in msg or "Status Code 432" in msg or "usage limit" in msg or "set usage limit" in msg:
                    logger.error("检测到 Tavily 配额已用尽，停止本次续跑（等待配额恢复/更换KEY/升级套餐）。")
                    break
                continue
        
        # 保存最终结果
        self._save_checkpoint()
        final_output = self._save_final_results()
        
        elapsed = time.time() - start_time
        logger.info(f"\n爬取完成！")
        logger.info(f"总耗时: {elapsed/60:.1f} 分钟")
        logger.info(f"总文档数: {len(self.results)}")
        
        return final_output
    
    def _save_intermediate_results(self):
        """保存中间结果"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 保存结构化结果
        structured_file = self.output_dir / "structured" / f"intermediate_{timestamp}.json"
        with open(structured_file, 'w', encoding='utf-8') as f:
            json.dump(self.structured_results, f, ensure_ascii=False, indent=2)
        
        logger.info(f"中间结果已保存: {structured_file}")
    
    def _save_final_results(self) -> Dict:
        """保存最终结果"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 统计信息
        stats = {
            "total_documents": len(self.results),
            "keywords_processed": len(self.processed_keywords),
            "unique_urls": len(self.seen_urls),
            "keyword_coverage": {cat: sum(1 for k in keywords if k in self.processed_keywords) 
                               for cat, keywords in EXTENDED_KEYWORDS.items()},
        }
        
        # 最终输出
        final_data = {
            "metadata": {
                "research_topic": "中国绿电消费驱动和阻碍因素大规模研究",
                "crawl_time": datetime.now().isoformat(),
                "total_keywords": len(self.keywords),
                "keywords_processed": len(self.processed_keywords),
                "total_documents": len(self.results),
                "statistics": stats,
            },
            "results": self.structured_results
        }
        
        # 保存文件
        output_file = self.output_dir / f"large_scale_results_{timestamp}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(final_data, f, ensure_ascii=False, indent=2)
        
        # 保存扁平化JSONL用于分析
        analysis_file = self.output_dir / "structured" / f"large_scale_analysis_{timestamp}.jsonl"
        with open(analysis_file, 'w', encoding='utf-8') as f:
            for record in self.structured_results:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        
        logger.info(f"最终结果已保存: {output_file}")
        logger.info(f"分析文件已保存: {analysis_file}")
        
        return {
            "output_file": str(output_file),
            "analysis_file": str(analysis_file),
            "statistics": stats,
        }


def main():
    """执行大规模爬取"""
    import argparse
    
    parser = argparse.ArgumentParser(description="大规模绿电消费研究数据爬取")
    parser.add_argument("--max-documents", type=int, default=2000, help="目标文档数")
    parser.add_argument("--batch-size", type=int, default=20, help="每批关键词数")
    parser.add_argument("--results-per-keyword", type=int, default=15, help="每关键词最大结果数")
    args = parser.parse_args()
    
    # 确保日志目录存在
    Path("logs").mkdir(exist_ok=True)
    
    crawler = LargeScaleCrawler(
        keywords=ALL_KEYWORDS,
        max_results_per_keyword=args.results_per_keyword,
        batch_size=args.batch_size,
    )
    
    print(f"\n📊 关键词分布:")
    for category, keywords in EXTENDED_KEYWORDS.items():
        print(f"  • {category}: {len(keywords)} 个")
    print(f"  📝 总计: {len(ALL_KEYWORDS)} 个关键词")
    print(f"  🎯 预估最大文档数: {len(ALL_KEYWORDS) * args.results_per_keyword}")
    
    result = crawler.run(max_documents=args.max_documents)
    
    print(f"\n✅ 大规模爬取完成！")
    print(f"📁 输出文件: {result['output_file']}")
    print(f"📁 分析文件: {result['analysis_file']}")
    print(f"📊 统计信息: {json.dumps(result['statistics'], ensure_ascii=False, indent=2)}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
