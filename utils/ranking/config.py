from datetime import date


TOP_N = 100
HEAP_SIZE = 1200
DEFAULT_OUTPUT_PATH = "team_jinsil.csv"
DEFAULT_PRECOMPUTE_PATH = "precomputed_rank_signals.json"
DEFAULT_CANDIDATE_PATHS = (
    "candidates.jsonl.gz",
    "candidates.jsonl",
    "candidates.json",
)
DEFAULT_PROGRESS_EVERY = 10000
FINAL_SCORE_SCALE = 1.15
REFERENCE_DATE = date(2026, 6, 29)
PRECOMPUTE_SIGNAL_WEIGHT = 0.3

PROFICIENCY_WEIGHT = {
    "beginner": 0.35,
    "intermediate": 0.6,
    "advanced": 0.85,
    "expert": 1.0,
}

MUST_HAVE_TERMS = {
    "python": 1.0,
    "embedding": 1.1,
    "embeddings": 1.1,
    "retrieval": 1.25,
    "search": 0.9,
    "ranking": 1.25,
    "recommendation": 1.0,
    "recommender": 1.0,
    "matching": 0.9,
    "candidate matching": 1.1,
    "job matching": 1.1,
    "bm25": 0.9,
    "rule-based scoring": 0.7,
    "vector database": 1.2,
    "hybrid search": 1.25,
    "sentence-transformers": 0.9,
    "openai embeddings": 0.85,
    "bge": 0.75,
    "e5": 0.75,
    "embedding drift": 1.15,
    "retrieval quality": 1.0,
    "retrieval-quality regression": 1.15,
    "faiss": 1.1,
    "elasticsearch": 1.0,
    "opensearch": 1.0,
    "pinecone": 1.0,
    "qdrant": 1.0,
    "milvus": 1.0,
    "weaviate": 1.0,
    "llm": 0.7,
    "llm reranking": 1.0,
    "reranking": 0.9,
    "learning-to-rank": 0.65,
    "xgboost": 0.45,
    "nlp": 0.9,
    "rag": 0.7,
    "ndcg": 1.1,
    "mrr": 0.9,
    "map": 0.7,
    "a/b": 0.7,
    "ab test": 0.7,
    "offline-to-online": 0.9,
    "relevance": 0.6,
    "relevance labeling": 0.75,
    "relevance evaluation": 0.95,
}

CORE_RETRIEVAL_TERMS = {
    "embedding",
    "embeddings",
    "retrieval",
    "search",
    "ranking",
    "recommendation",
    "recommender",
    "matching",
    "candidate matching",
    "job matching",
    "bm25",
    "vector database",
    "hybrid search",
    "embedding drift",
    "retrieval quality",
    "retrieval-quality regression",
    "faiss",
    "elasticsearch",
    "opensearch",
    "pinecone",
    "qdrant",
    "milvus",
    "weaviate",
    "reranking",
    "learning-to-rank",
}

EVALUATION_TERMS = {
    "ndcg",
    "mrr",
    "map",
    "a/b",
    "ab test",
    "offline benchmark",
    "offline benchmarks",
    "online experiment",
    "evaluation framework",
    "relevance evaluation",
    "ranking evaluation",
    "offline-to-online",
    "recruiter feedback",
    "feedback loop",
    "relevance labeling",
}

PRODUCTION_TERMS = {
    "production",
    "deployed",
    "shipped",
    "users",
    "scale",
    "latency",
    "monitoring",
    "observability",
    "regression",
    "index refresh",
    "quality regression",
    "embedding drift",
    "retrieval-quality regression",
    "offline-to-online",
}

PRODUCT_OWNERSHIP_TERMS = {
    "owned",
    "product",
    "pm",
    "roadmap",
    "recruiter",
    "recruiter workflow",
    "candidate workflow",
    "talent intelligence",
    "workflow",
    "marketplace",
    "experimentation",
    "metrics",
    "engagement",
    "early-stage",
    "founding",
    "scrappy",
    "iterate",
}

LEADERSHIP_TERMS = {
    "mentor",
    "mentored",
    "coached",
    "tech lead",
    "technical lead",
    "architecture",
    "design review",
    "mentoring",
    "senior engineer judgment",
}

ADJACENT_TERMS = {
    "machine learning": 0.8,
    "ml": 0.6,
    "data pipeline": 0.45,
    "spark": 0.4,
    "airflow": 0.35,
    "xgboost": 0.45,
    "classification": 0.3,
    "clustering": 0.3,
    "feature engineering": 0.45,
    "model deployment": 0.55,
    "fine-tuning": 0.35,
    "lora": 0.3,
    "qlora": 0.3,
    "peft": 0.3,
    "distributed systems": 0.35,
    "inference optimization": 0.35,
    "large-scale inference": 0.35,
    "open-source": 0.25,
    "production": 0.45,
    "api": 0.25,
    "backend": 0.35,
}

NEGATIVE_TERMS = {
    "marketing manager",
    "hr manager",
    "operations manager",
    "project manager",
    "program manager",
    "accountant",
    "graphic designer",
    "content writer",
    "sales executive",
    "customer support",
    "business analyst",
    "civil engineer",
    "mechanical engineer",
}

HANDS_ON_TITLE_TERMS = {
    "ai engineer",
    "applied ml engineer",
    "ml engineer",
    "machine learning engineer",
    "software engineer",
    "backend engineer",
    "data engineer",
    "data scientist",
    "recommendation systems engineer",
    "search engineer",
    "platform engineer",
    "cloud engineer",
    "developer",
    "architect",
}

ADJACENT_ENGINEERING_TITLE_TERMS = {
    "frontend engineer",
    "mobile developer",
    "qa engineer",
    "test engineer",
    "devops engineer",
    "cloud engineer",
    "java developer",
    ".net developer",
    "full stack developer",
}

CONSULTING_COMPANIES = {
    "tcs",
    "infosys",
    "wipro",
    "accenture",
    "cognizant",
    "capgemini",
    "hcl",
    "tech mahindra",
}

PRODUCT_SIGNALS = {
    "product",
    "saas",
    "platform",
    "startup",
    "marketplace",
    "users",
    "production",
    "shipped",
    "deployed",
}

PURE_RESEARCH_SIGNALS = {
    "academic lab",
    "research-only",
    "research only",
    "published papers",
}

NON_TARGET_AI_SIGNALS = {
    "computer vision",
    "image classification",
    "robotics",
    "speech",
}
