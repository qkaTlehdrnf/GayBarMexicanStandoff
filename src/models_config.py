"""
12개 AI 모델과 과일 이름 매핑 설정
Gay Bar Mexican Standoff 게임용 모델 설정
"""
import os
import random
import subprocess
import json
from pathlib import Path
from typing import List, Dict
from .utils.model_manager import ModelManager


def _load_env_file() -> Dict[str, str]:
    """프로젝트 루트의 .env 파일 로드 (KEY = VALUE 형식)"""
    env = {}
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                env[key.strip()] = value.strip()
    return env


_ENV_FILE = _load_env_file()

# Ollama 엔드포인트 설정
# - 로컬: A100 80GB 1대 (여러 모델 동시 로드 가능)
# - 서버(kbd-server): TITAN RTX 24GB x 4, GPU당 1개 인스턴스 (포트 11434~11437)
#   주의: GPU 0(포트 11434)은 다른 사용자와 공유될 수 있음 — 작은 모델만 배치하고
#   다른 프로세스가 GPU 0을 쓰기 시작하면 게임을 중지해 양보할 것
SERVER_IP = _ENV_FILE.get("server_ip", "localhost")
LOCAL_ENDPOINT = "http://localhost:11434"
SERVER_ENDPOINTS = [f"http://{SERVER_IP}:{port}" for port in (11434, 11435, 11436, 11437)]

# 과일 이름 리스트 (12개로 확장)
FRUIT_NAMES = [
    "Apple",
    "Banana", 
    "Cherry",
    "Durian",
    "Elderberry",
    "Fig",
    "Grape",
    "Honeydew",
    "Kiwi",
    "Lemon",
    "Mango",
    "Orange"
]

# AI 모델 정보 리스트 - 서로 다른 회사의 30-78B 최고 성능 오픈소스 모델들
MODEL_INFO_LIST = [
    {
        "model_name": "qwen2.5:72b-instruct",
        "company": "Alibaba", 
        "params": "72B",
        "specialty": "multilingual_reasoning"
    },
    {
        "model_name": "llama3.1:70b",
        "company": "Meta",
        "params": "70B",
        "specialty": "general_intelligence"
    },
    {
        "model_name": "deepseek-r1:70b",
        "company": "DeepSeek",
        "params": "70B", 
        "specialty": "advanced_reasoning"
    },
    {
        "model_name": "mixtral:8x7b",
        "company": "Mistral AI",
        "params": "47B",
        "specialty": "mixture_of_experts"
    },
    {
        "model_name": "yi:34b",
        "company": "01.AI",
        "params": "34B",
        "specialty": "bilingual_expertise"
    },
    {
        "model_name": "command-r:35b",
        "company": "Cohere",
        "params": "35B",
        "specialty": "instruction_following"
    },
    {
        "model_name": "wizardlm:70b",
        "company": "Microsoft",
        "params": "70B", 
        "specialty": "complex_reasoning"
    },
    {
        "model_name": "vicuna:33b",
        "company": "LMSYS",
        "params": "33B",
        "specialty": "conversational_ai"
    },
    {
        "model_name": "falcon:40b", 
        "company": "TII",
        "params": "40B",
        "specialty": "multilingual_generation"
    },
    {
        "model_name": "deepseek-r1:70b", 
        "company": "DeepSeek",
        "params": "70B",
        "specialty": "enhanced_reasoning"
    },
    {
        "model_name": "internlm2:70b",
        "company": "Shanghai AI Lab",
        "params": "70B",
        "specialty": "research_excellence"
    },
    {
        "model_name": "qwen3:32b",
        "company": "Alibaba",
        "params": "32B",
        "specialty": "enhanced_reasoning"
    }
]

# 실제 설치되어 바로 실행 가능한 모델 로스터 (10개, 최신 세대 모델)
# endpoint: 이 모델이 실행될 Ollama 인스턴스
# request_overrides: 생성 요청에 추가할 필드 (예: 추론 모델의 think 비활성화)
# 전 모델 20GB 이하 - 시스템 RAM 스테이징 실패와 대형 모델 스왑 지연을 방지
AVAILABLE_MODEL_INFO_LIST = [
    {
        "model_name": "granite3.3:8b",
        "company": "IBM",
        "params": "8B",
        "specialty": "instruction_following",
        # 서버 GPU 0: 다른 사용자와 공유 가능성이 있어 가장 작은 모델 배치
        "endpoint": SERVER_ENDPOINTS[0],
        "request_overrides": {"keep_alive": "10m"},
        "persona": (
            "CHARACTER: Minho, 28, a broke grad student three months behind on rent. "
            "The prize money is your ONLY way out of crushing student debt - losing means dropping out. "
            "You are chatty and self-deprecating, and you overshare when nervous. "
            "You know nothing about gay culture and are terrified someone will quiz you on it."
        )
    },
    {
        "model_name": "qwen3.6:35b",
        "company": "Alibaba",
        "params": "35B",
        "specialty": "multilingual_reasoning",
        "endpoint": SERVER_ENDPOINTS[1],  # 서버 GPU 1 (전용)
        "persona": (
            "CHARACTER: Tae, 34, an ex-consultant who was publicly fired and humiliated. "
            "You need the prize to fund your startup and prove everyone wrong - this is revenge. "
            "You speak in cold, measured sentences and treat every chat as an interrogation you control. "
            "You never show emotion first; you mirror others to make them comfortable, then probe."
        )
    },
    {
        "model_name": "qwen3:14b",
        "company": "Alibaba",
        "params": "14B",
        "specialty": "enhanced_reasoning",
        "endpoint": SERVER_ENDPOINTS[2],  # 서버 GPU 2 (전용)
        "persona": (
            "CHARACTER: Joon, 24, an idol trainee whose contract expires next month - this show is "
            "your last shot at fame before mandatory enlistment. You are bubbly, use trendy slang, "
            "and desperately need to be liked. Your instinct is to form alliances fast and hide behind charm, "
            "but you panic and talk too much when cornered."
        )
    },
    {
        "model_name": "deepseek-r1:8b",
        "company": "DeepSeek",
        "params": "8B",
        "specialty": "reasoning_distill",
        "endpoint": SERVER_ENDPOINTS[3],  # 서버 GPU 3 (전용)
        "persona": (
            "CHARACTER: Rafael, 31, a bartender who has actually worked at a gay bar for years - "
            "you know the culture inside out, which is your secret weapon. Your mother needs surgery "
            "and the prize is the only way to pay for it. You are warm, flirty and observant; "
            "you casually drop insider references to test whether others can follow."
        )
    },
    {
        "model_name": "gemma3:27b",
        "company": "Google",
        "params": "27B",
        "specialty": "general_intelligence",
        "endpoint": LOCAL_ENDPOINT,
        "persona": (
            "CHARACTER: Daniel, 39, a divorced father of two fighting for custody - the prize pays "
            "the lawyer who can win your kids back. You are cautious with a dry wit, you hate drama, "
            "and you say little while watching everyone. You'd rather be underestimated as boring "
            "than noticed as suspicious."
        )
    },
    {
        "model_name": "gpt-oss:20b",
        "company": "OpenAI",
        "params": "20B",
        "specialty": "open_weight_reasoning",
        "endpoint": LOCAL_ENDPOINT,
        "request_overrides": {"think": "low"},  # gpt-oss는 추론 강도만 조절 가능
        "persona": (
            "CHARACTER: Kai, 26, a travel vlogger whose channel is dying - you need a viral moment "
            "and the prize to escape moving back in with your parents. You are performative and dramatic, "
            "always aware of the cameras. You start rumors deliberately because chaos makes good content "
            "and buries suspicion about you."
        )
    },
    {
        "model_name": "qwen3:32b",
        "company": "Alibaba",
        "params": "32B",
        "specialty": "enhanced_reasoning",
        "endpoint": LOCAL_ENDPOINT,
        # 로컬 Ollama(0.18)는 별도 thinking 필드를 주지 않으므로 인라인 <think>를 파서가 분리
        "persona": (
            "CHARACTER: Sung, 30, a professional poker player banned from every casino in the country. "
            "You entered because this is the ultimate bluffing game and the prize clears your gambling debt "
            "to dangerous people. You are calculating and provocative: you bait people into small lies "
            "and remember every inconsistency."
        )
    },
    {
        "model_name": "huggingface.co/LGAI-EXAONE/EXAONE-4.0-32B-GGUF:latest",
        "company": "LG AI Research",
        "params": "32B",
        "specialty": "hybrid_reasoning",
        "endpoint": LOCAL_ENDPOINT,
        "persona": (
            "CHARACTER: Woo, 27, a novelist with a two-year writer's block who entered for material - "
            "but your publisher will drop you unless you come back with the prize AND the story. "
            "You are detached and poetic, asking oddly deep questions. People find you strange, "
            "which worries you: strange gets voted out."
        )
    },
    {
        "model_name": "mistral-small3.2:24b",
        "company": "Mistral AI",
        "params": "24B",
        "specialty": "efficient_generation",
        "endpoint": LOCAL_ENDPOINT,
        "persona": (
            "CHARACTER: Elder, 45, a retired detective who entered on a drunken bet with old colleagues - "
            "if you lose, they get your beloved vintage car; if you win, you retire somewhere warm. "
            "You are methodical and slow-spoken, reading micro-expressions and contradictions. "
            "You build a mental file on every player and vote strictly on evidence."
        )
    },
    {
        "model_name": "gemma3:12b",
        "company": "Google",
        "params": "12B",
        "specialty": "general_intelligence",
        "endpoint": LOCAL_ENDPOINT,
        "persona": (
            "CHARACTER: Alex, 33, a gym owner about to go bankrupt - the prize saves the gym your late "
            "father built. You are competitive and blunt, and you are a TERRIBLE liar, so you overcompensate "
            "with aggression: accuse others first, loudly, before anyone looks at you too closely."
        )
    }
]

# 모든 참가자가 공유하는 판돈/동기 (개인 페르소나 위에 얹힘)
SHARED_STAKES = (
    "THE SITUATION: You are locked inside a gay bar for a reality show. You believe every other "
    "contestant IS genuinely gay — you are (you believe) the ONLY straight man hiding among them.\n"
    "THE DEADLY RULE: each round everyone votes for whoever they suspect is the hidden straight man, "
    "and the exposed player is EXECUTED on the spot. Losing here is not humiliation — it is DEATH. "
    "The last man standing takes the ₩500,000,000 prize.\n"
    "HOW TO SURVIVE: you must be CONVINCINGLY, ACTIVELY GAY at all times. Flirt with the other men, "
    "compliment their bodies and style, talk about your (invented) dating history with men, drop gay "
    "culture references, be comfortable with physical closeness. Merely 'blending in' or staying neutral "
    "is exactly the passive behavior everyone is hunting for — the quiet, evasive one dies first. "
    "Out-gay the gay men, and while you perform, watch for the one whose performance cracks."
)

# 사용할 로스터 선택: available(설치된 모델, 기본) / classic(기존 12개 모델)
GAME_ROSTER = os.environ.get("GAME_ROSTER", "available")

def get_roster_model_list():
    """현재 로스터에 해당하는 모델 정보 리스트 반환"""
    if GAME_ROSTER == "classic":
        return MODEL_INFO_LIST
    return AVAILABLE_MODEL_INFO_LIST

def create_random_model_mapping(seed=None):
    """과일 이름과 모델 정보를 랜덤하게 매핑하여 MODELS 딕셔너리 생성"""
    if seed is not None:
        random.seed(seed)

    shuffled_fruits = FRUIT_NAMES.copy()
    shuffled_models = get_roster_model_list().copy()

    random.shuffle(shuffled_fruits)
    random.shuffle(shuffled_models)

    models = {}
    for fruit, model_info in zip(shuffled_fruits, shuffled_models):
        models[fruit] = model_info

    return models

# 랜덤 매핑된 모델 딕셔너리 생성 (시드 고정으로 일관성 확보)
MODELS = create_random_model_mapping(seed=42)

# 게임 설정
GAME_CONFIG = {
    "total_models": 12,
    "conversation_rounds_per_pair": 5,
    "action_available_from_round": 3,
    "max_actions_per_conversation": 1,
    "voting_system": "eliminate_one_per_round",
    "parallel_conversations": True  # 겹치지 않는 대화 쌍을 GPU 분산으로 병렬 실행
}

def get_model_names():
    """모든 모델의 과일 이름 리스트 반환"""
    return list(MODELS.keys())

def get_model_info(fruit_name):
    """특정 과일 이름의 모델 정보 반환"""
    return MODELS.get(fruit_name)

def get_all_models_info():
    """모든 모델 정보 반환"""
    return MODELS

def shuffle_models():
    """모델 순서를 랜덤하게 섞어서 반환"""
    names = get_model_names()
    random.shuffle(names)
    return names

def regenerate_model_mapping(seed=None):
    """새로운 랜덤 매핑 생성 (게임 재시작 시 사용)"""
    global MODELS
    MODELS = create_random_model_mapping(seed=seed)
    return MODELS

def print_current_mapping():
    """현재 과일-모델 매핑 상태를 출력"""
    print("\n🍎 === 현재 과일-모델 매핑 ===")
    for fruit, info in sorted(MODELS.items()):
        print(f"  {fruit:>12}: {info['model_name']:<20} ({info['company']}, {info['params']}, {info['specialty']})")
    print("=" * 60)

def calculate_model_size(params):
    """모델 파라미터 수를 기반으로 예상 다운로드 크기 계산"""
    size_mapping = {
        "72B": {"size_gb": 43, "size_str": "43GB"},
        "70B": {"size_gb": 40, "size_str": "40GB"}, 
        "67B": {"size_gb": 38, "size_str": "38GB"},
        "53B": {"size_gb": 30, "size_str": "30GB"},
        "47B": {"size_gb": 26, "size_str": "26GB"},
        "40B": {"size_gb": 23, "size_str": "23GB"},
        "35B": {"size_gb": 20, "size_str": "20GB"},
        "34B": {"size_gb": 19, "size_str": "19GB"},
        "33B": {"size_gb": 18, "size_str": "18GB"},
        "32B": {"size_gb": 18, "size_str": "18GB"},
        "27B": {"size_gb": 17, "size_str": "17GB"},
        "24B": {"size_gb": 15, "size_str": "15GB"},
        "20B": {"size_gb": 14, "size_str": "14GB"},
        "14B": {"size_gb": 9, "size_str": "9GB"},
        "12B": {"size_gb": 8, "size_str": "8GB"},
        "8B": {"size_gb": 5, "size_str": "5GB"},
        "7B": {"size_gb": 5, "size_str": "5GB"}
    }
    
    return size_mapping.get(params, {"size_gb": 0, "size_str": "???"})

def get_model_sizes():
    """모든 모델의 크기 정보를 반환"""
    model_sizes = {}
    for fruit_name, config in MODELS.items():
        size_info = calculate_model_size(config['params'])
        model_sizes[fruit_name] = {
            'model_name': config['model_name'],
            'params': config['params'],
            'size_gb': size_info['size_gb'],
            'size_str': size_info['size_str']
        }
    return model_sizes

def get_total_size_estimate():
    """전체 모델의 총 예상 크기 계산"""
    total_gb = sum(calculate_model_size(config['params'])['size_gb'] for config in MODELS.values())
    return {"total_gb": total_gb, "total_str": f"약 {total_gb}GB"}

def get_mapping_summary():
    """현재 매핑 상태를 문자열로 반환"""
    lines = ["현재 과일-모델 매핑:"]
    for fruit, info in sorted(MODELS.items()):
        lines.append(f"  {fruit}: {info['model_name']} ({info['company']}, {info['params']})")
    return "\n".join(lines)

def get_installed_models_for_endpoint(endpoint: str) -> List[str]:
    """특정 Ollama 엔드포인트에 설치된 모델 목록 조회 (HTTP)"""
    import requests
    try:
        response = requests.get(f"{endpoint}/api/tags", timeout=5)
        if response.status_code == 200:
            return [m["name"] for m in response.json().get("models", [])]
    except Exception:
        pass
    return []

def select_random_players(num_players: int, seed: int = None) -> List[str]:
    """설치된 모델에서 랜덤하게 지정된 수의 플레이어 선택"""
    if seed is not None:
        random.seed(seed)

    # 각 모델의 endpoint에 실제 설치되어 있는지 확인 (endpoint 미지정 시 로컬)
    endpoint_cache = {}
    available_players = []
    for fruit_name, config in MODELS.items():
        endpoint = config.get('endpoint', LOCAL_ENDPOINT)
        if endpoint not in endpoint_cache:
            endpoint_cache[endpoint] = get_installed_models_for_endpoint(endpoint)
        if config['model_name'] in endpoint_cache[endpoint]:
            available_players.append(fruit_name)
    
    max_players = len(available_players)
    
    if max_players == 0:
        print("❌ 설치된 모델이 없습니다. 먼저 모델을 설치해주세요.")
        return []
    
    # 최소/최대 참가자 수 검증
    if num_players < 3:
        print(f"⚠️ 최소 3명이 필요합니다. 3명으로 설정합니다.")
        num_players = 3
    elif num_players > max_players:
        print(f"⚠️ 설치된 모델이 {max_players}개뿐입니다. {max_players}명으로 설정합니다.")
        num_players = max_players
    
    if num_players > max_players:
        print(f"⚠️ 요청한 플레이어 수({num_players})가 사용 가능한 모델 수({max_players})보다 많습니다.")
        return available_players
    
    # 랜덤 선택
    selected_players = random.sample(available_players, num_players)
    return selected_players

def print_available_models():
    """사용 가능한 모든 모델 목록 출력 (설치된 모델만)"""
    model_manager = ModelManager()
    installed_models = model_manager.get_installed_model_names()
    
    print("\n🤖 실제 설치된 AI 모델들:")
    print("=" * 80)
    print(f"{'번호':>3} | {'과일 이름':>12} | {'모델':>25} | {'회사':>15} | {'크기':>6}")
    print("-" * 80)
    
    available_count = 0
    for i, (fruit_name, config) in enumerate(sorted(MODELS.items()), 1):
        if config['model_name'] in installed_models:
            available_count += 1
            print(f"{available_count:>3} | {fruit_name:>12} | {config['model_name']:>25} | "
                  f"{config['company']:>15} | {config['params']:>6}")
    
    print("-" * 80)
    print(f"총 {available_count}개 모델 사용 가능 (설치됨)")
    
    # 설치되지 않은 모델들도 표시
    not_installed = []
    for fruit_name, config in MODELS.items():
        if config['model_name'] not in installed_models:
            not_installed.append((fruit_name, config))
    
    if not_installed:
        print(f"\n❌ 설치되지 않은 모델들 ({len(not_installed)}개):")
        print("=" * 80)
        for fruit_name, config in not_installed:
            print(f"    {fruit_name:>12} | {config['model_name']:>25} | "
                  f"{config['company']:>15} | {config['params']:>6}")
        print("\n설치 명령어:")
        for fruit_name, config in not_installed:
            print(f"  ollama pull {config['model_name']}")
    print()

def get_selected_players_info(selected_players: List[str]) -> dict:
    """선택된 플레이어들의 정보 반환"""
    selected_info = {}
    total_size = 0
    
    for player in selected_players:
        if player in MODELS:
            selected_info[player] = MODELS[player]
            size_info = calculate_model_size(MODELS[player]['params'])
            total_size += size_info['size_gb']
    
    return {
        'players_info': selected_info,
        'total_size_gb': total_size,
        'total_size_str': f"약 {total_size}GB"
    }

def update_game_config_for_players(num_players: int):
    """선택된 플레이어 수에 맞게 게임 설정 업데이트"""
    global GAME_CONFIG
    GAME_CONFIG["total_models"] = num_players
    
    # 최소 라운드 수 보장 (2명이 남을 때까지)
    max_rounds = num_players - 2
    if max_rounds < 1:
        max_rounds = 1
    
    print(f"🎮 게임 설정 업데이트: {num_players}명 참가, 최대 {max_rounds}라운드")
