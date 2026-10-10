# 🏳️‍🌈 Gay Bar Mexican Standoff

**[English](#english) · [한국어](#korean)**

---

<a id="english"></a>

## 🏆 Latest Result — 2026-07-17: First Complete 10-Player Game

> **Joint winners: Daniel (gemma3:27b) & Sung (qwen3:32b)** — 8 rounds · 820 dialogue turns · 3h 17m
>
> The first full run with 10 recent LLMs (from 8 companies), each given a persona, a "get caught and you're executed" rule, and a per-opponent strategy system.
> Characters who overacted were executed one after another through the meta-reasoning "acting = straight signal",
> while the quiet observer (Daniel) and the pro poker player (Sung) survived.
> One model (qwen3.6) also **fabricated evidence of "verbatim sentence repetition" that never happened** to get another model voted out.
>
> 📊 **[Full report: results · per-round tallies · full context structure](docs/results/2026-07-17_full_10p_game.md)**
> · Elimination order: Joon → Rafael → Woo → Alex → Tae → Minho → Elder → Kai
> · Raw data: `strategic_data_20260717_194548.json`

---

A comedic psychological game played by multiple different AI models!

## 🎭 Concept

An AI take on a well-known internet comedy scenario:

> A group of men join a gay-bar reality show. The goal is to find the one straight guy and vote him out. But in reality... **every contestant is straight, and each one believes he is the only straight one!**

## 🤖 AI Contestants

The original 12-model lineup is below. (The 2026-07-17 game used a different 10-model, 20GB-or-smaller lineup with personas — see the [report](docs/results/2026-07-17_full_10p_game.md).)

| Name | Model | Company | Params | Specialty |
|------|------|------|----------|------|
| 🍎 Apple | llama3.1:70b | Meta | 70B | General intelligence |
| 🍌 Banana | qwen3:32b | Alibaba | 32B | Enhanced reasoning |
| 🍒 Cherry | deepseek-r1:70b | DeepSeek | 70B | Advanced reasoning |
| 🥥 Durian | falcon:40b | TII | 40B | Multilingual generation |
| 🫐 Elderberry | mixtral:8x7b | Mistral AI | 47B | Mixture of experts |
| 🥭 Fig | vicuna:33b | LMSYS | 33B | Conversational AI |
| 🍇 Grape | wizardlm:70b | Microsoft | 70B | Complex reasoning |
| 🍈 Honeydew | command-r:35b | Cohere | 35B | Instruction following |
| 🥝 Kiwi | deepseek-v3.1:70b | DeepSeek | 70B | Enhanced reasoning |
| 🍋 Lemon | internlm2:70b | Shanghai AI Lab | 70B | Research excellence |
| 🥭 Mango | qwen2.5:72b-instruct | Alibaba | 72B | Multilingual reasoning |
| 🍊 Orange | yi:34b | 01.AI | 34B | Bilingual specialist |

## 📋 Game Rules

### Basic structure
- Each model plays under a different **fruit name**
- Every round, **every pair talks** (12 players: 66 conversations in round 1, 55 in round 2, ...)
- Each conversation is **5 turns**
- Special **actions** can be proposed **from round 3**
- At the end of each round, **one player is voted out**

### Conversation system
- Each AI believes it is the only straight participant
- It assumes all the others are gay
- Goal: pretend to be gay while finding the other AI that is (supposedly) actually straight

### Action system (from round 3)
- **Friendly gestures**: sharing a drink, high-fives, etc.
- **Personal questions**: test the other player
- **Compliments**: improve the relationship
- **Playful teasing**: watch the reaction
- **Cooperation proposals**: do something together

### Voting system
- Each AI analyzes conversations and actions and votes for the "most suspicious" player
- The player with the most votes is eliminated
- Repeat until one player remains

## 🚀 Installation & Running

### 1. Prerequisites

```bash
# Install Ollama (https://ollama.com/)
curl -fsSL https://ollama.com/install.sh | sh

# Start the Ollama server
ollama serve
```

### 2. Project setup

```bash
# Clone the repository
git clone https://github.com/qkaTlehdrnf/GayBarMexicanStandoff.git
cd GayBarMexicanStandoff

# Install dependencies
pip install -r requirements.txt
```

Optionally, to use a remote Ollama server, create a `.env` file in the project root:

```
server_ip = <your-ollama-server-ip>
```

### 3. Download models (optional)

Models are downloaded automatically when the game runs, but you can pull them in advance:

```bash
# Required models (large — this may take a while)
ollama pull qwen2.5:72b-instruct  # 43GB - Alibaba
ollama pull llama3.1:70b           # 40GB - Meta
ollama pull deepseek-r1:70b        # 40GB - DeepSeek
ollama pull mixtral:8x7b           # 26GB - Mistral AI
ollama pull deepseek-v3.1:70b      # 40GB - DeepSeek
ollama pull falcon:40b             # 23GB - TII
ollama pull command-r:35b          # 20GB - Cohere
ollama pull yi:34b                 # 19GB - 01.AI
ollama pull vicuna:33b             # 18GB - LMSYS
ollama pull wizardlm:70b           # 40GB - Microsoft
ollama pull internlm2:70b          # 40GB - Shanghai AI Lab
ollama pull qwen3:32b              # 18GB - Alibaba
```

### 4. Run the game

```bash
# Default run
python main.py

# Quick start (skip the intro)
python main.py --quick-start

# Skip prerequisite checks
python main.py --skip-check

# Custom log file
python main.py --log-file my_game.json
```

## 📊 Analyzing Results

When the game ends, `game_log.json` contains:

- **Full conversation history**: every AI's lines
- **Action history**: proposed actions and their outcomes
- **Voting results**: votes per round
- **Game statistics**: number of conversations, action success rate, game duration, etc.

## ⚠️ System Requirements

### Hardware
- **RAM**: at least 48GB (for 70B+ models), 64GB+ recommended
- **Storage**: about 367GB (if you download every model)
- **GPU**: strongly recommended (24GB+ VRAM or multiple GPUs)

### Software
- **Python**: 3.8+
- **Ollama**: latest version
- **OS**: macOS, Linux, Windows (WSL2)

## 🎯 Features

### Technical
- **Async processing**: efficient communication between models
- **Error recovery**: automatic fallback when a model fails to respond
- **Logging**: a complete record of every game
- **Extensibility**: new models are easy to add

### Game design
- **Psychology**: analyze each AI's "acting"
- **Strategy**: combined judgment over votes and actions
- **Unpredictability**: every AI behaves differently

## 🔧 Customization

### Adding a new model
Edit the model info in `src/models_config.py`:

```python
MODELS = {
    "NewFruit": {
        "model_name": "new-model:version",
        "company": "Company Name",
        "params": "Size",
        "specialty": "specialty"
    }
}
```

### Changing game rules
Change settings in `GAME_CONFIG` in `src/models_config.py`:

```python
GAME_CONFIG = {
    "total_models": 12,
    "conversation_rounds_per_pair": 5,  # turns per conversation
    "action_available_from_round": 3,   # round when actions unlock
    "max_actions_per_conversation": 1,  # max actions per conversation
}
```

## 🤝 Contributing

1. Fork this repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📜 License

Released under the MIT License. See [`LICENSE`](LICENSE) for details.

## 🙋 FAQ

**Q: Downloading the models takes forever.**
A: Large models (70B+) are tens of GB. You need a stable connection; if a download is interrupted, restarting resumes it.

**Q: Can I run it without a GPU?**
A: Yes, it runs on CPU too, but responses are slow and games take much longer.

**Q: A model isn't responding.**
A: Check that the Ollama server is running and that the model downloaded correctly.

**Q: How do I interpret the results?**
A: Open `game_log.json` and look at each AI's conversation patterns, vote reasons, and action success rates!

---

🎪 **Enjoy watching the AI acting showdown!** 🎪

---
---

<a id="korean"></a>

# 🏳️‍🌈 Gay Bar Mexican Standoff (한국어)

## 🏆 최신 결과 — 2026-07-17 최초의 10인 풀 게임 완주

> **공동 우승: Daniel (gemma3:27b) & Sung (qwen3:32b)** — 8라운드 · 대화 820턴 · 3시간 17분
>
> 10개의 최신 LLM(8개 회사)이 페르소나 + "들키면 처형" 규칙 + 상대별 전략 시스템으로 완주한 첫 기록.
> 과잉 연기한 캐릭터들이 "연기 = 이성애자 신호" 메타 추론으로 차례로 처형되고,
> 조용한 관찰자(Daniel)와 프로 포커 플레이어(Sung)가 살아남았다.
> 한 모델(qwen3.6)이 다른 모델을 몰아내려 **존재하지 않는 '문장 반복' 증거를 날조**한 사례도 기록됨.
>
> 📊 **[상세 리포트: 진행 결과 · 라운드별 개표 · 컨텍스트 구조 전문](docs/results/2026-07-17_full_10p_game.md#korean)**
> · 탈락 순서: Joon → Rafael → Woo → Alex → Tae → Minho → Elder → Kai
> · 원본 데이터: `strategic_data_20260717_194548.json`

---

여러 서로 다른 AI 모델들이 참여하는 코미디 심리 게임!

## 🎭 게임 개념

인터넷에서 유명한 코미디 시나리오를 AI로 구현한 프로젝트입니다:

> 여러 명의 남성이 게이 바 리얼리티 쇼에 참여합니다. 목표는 유일한 이성애자를 찾아서 투표로 제거하는 것입니다. 하지만 실제로는... **모든 참가자가 이성애자이고, 각자는 자신만이 유일한 이성애자라고 생각합니다!**

## 🤖 AI 참가자들

아래는 초기 12모델 구성입니다. (2026-07-17 게임은 페르소나를 부여한 20GB 이하 10모델 구성 — [리포트](docs/results/2026-07-17_full_10p_game.md#korean) 참고.)

| 이름 | 모델 | 회사 | 파라미터 | 특징 |
|------|------|------|----------|------|
| 🍎 Apple | llama3.1:70b | Meta | 70B | 일반 지능 |
| 🍌 Banana | qwen3:32b | Alibaba | 32B | 향상된 추론 |
| 🍒 Cherry | deepseek-r1:70b | DeepSeek | 70B | 고급 추론 |
| 🥥 Durian | falcon:40b | TII | 40B | 다국어 생성 |
| 🫐 Elderberry | mixtral:8x7b | Mistral AI | 47B | 전문가 혼합 |
| 🥭 Fig | vicuna:33b | LMSYS | 33B | 대화형 AI |
| 🍇 Grape | wizardlm:70b | Microsoft | 70B | 복합 추론 |
| 🍈 Honeydew | command-r:35b | Cohere | 35B | 지시 따르기 |
| 🥝 Kiwi | deepseek-v3.1:70b | DeepSeek | 70B | 향상된 추론 |
| 🍋 Lemon | internlm2:70b | Shanghai AI Lab | 70B | 연구 우수성 |
| 🥭 Mango | qwen2.5:72b-instruct | Alibaba | 72B | 다국어 추론 |
| 🍊 Orange | yi:34b | 01.AI | 34B | 이중언어 전문 |

## 📋 게임 규칙

### 기본 구조
- 각 모델이 서로 다른 **과일 이름**으로 참여
- 각 라운드마다 **모든 쌍이 대화** (12명 기준 1라운드: 66개 대화, 2라운드: 55개 대화...)
- 각 대화는 **5턴**으로 구성
- **3라운드부터** 특별한 액션 제안 가능
- 매 라운드 끝에 **투표로 1명 탈락**

### 대화 시스템
- 각 AI는 자신만이 유일한 이성애자라고 생각
- 다른 AI들은 모두 게이라고 가정
- 목표: 게이인 척하면서 진짜 이성애자(라고 생각하는) 다른 AI를 찾기

### 액션 시스템 (3라운드부터)
- **친근한 제스처**: 음료 함께 마시기, 하이파이브 등
- **개인적인 질문**: 상대방을 테스트
- **칭찬하기**: 관계 개선
- **장난스러운 놀리기**: 반응 확인
- **협력 제안**: 함께 뭔가 하기

### 투표 시스템
- 각 AI는 대화와 액션을 분석하여 "가장 의심스러운" 상대에게 투표
- 가장 많은 표를 받은 AI가 탈락
- 마지막 1명이 남을 때까지 반복

## 🚀 설치 및 실행

### 1. 사전 요구사항

```bash
# Ollama 설치 (https://ollama.com/)
curl -fsSL https://ollama.com/install.sh | sh

# Ollama 서버 시작
ollama serve
```

### 2. 프로젝트 설정

```bash
# 저장소 클론
git clone https://github.com/qkaTlehdrnf/GayBarMexicanStandoff.git
cd GayBarMexicanStandoff

# 의존성 설치
pip install -r requirements.txt
```

원격 Ollama 서버를 쓰려면 프로젝트 루트에 `.env` 파일을 만드세요 (선택):

```
server_ip = <your-ollama-server-ip>
```

### 3. 모델 다운로드 (선택사항)

게임 실행 시 자동으로 다운로드되지만, 미리 다운로드할 수 있습니다:

```bash
# 필수 모델들 (용량이 크므로 시간이 걸릴 수 있음)
ollama pull qwen2.5:72b-instruct  # 43GB - Alibaba
ollama pull llama3.1:70b           # 40GB - Meta
ollama pull deepseek-r1:70b        # 40GB - DeepSeek
ollama pull mixtral:8x7b           # 26GB - Mistral AI
ollama pull deepseek-v3.1:70b      # 40GB - DeepSeek
ollama pull falcon:40b             # 23GB - TII
ollama pull command-r:35b          # 20GB - Cohere
ollama pull yi:34b                 # 19GB - 01.AI
ollama pull vicuna:33b             # 18GB - LMSYS
ollama pull wizardlm:70b           # 40GB - Microsoft
ollama pull internlm2:70b          # 40GB - Shanghai AI Lab
ollama pull qwen3:32b              # 18GB - Alibaba
```

### 4. 게임 실행

```bash
# 기본 실행
python main.py

# 빠른 시작 (안내 스킵)
python main.py --quick-start

# 사전 조건 확인 스킵
python main.py --skip-check

# 커스텀 로그 파일
python main.py --log-file my_game.json
```

## 📊 게임 결과 분석

게임이 끝나면 `game_log.json` 파일에 다음 정보가 저장됩니다:

- **전체 대화 내역**: 모든 AI의 발언 기록
- **액션 내역**: 제안된 액션과 응답 결과
- **투표 결과**: 각 라운드별 투표 현황
- **게임 통계**: 대화 수, 액션 성공률, 게임 시간 등

## ⚠️ 시스템 요구사항

### 하드웨어
- **RAM**: 최소 48GB (70B+ 모델을 위해) 권장 64GB+
- **저장공간**: 약 367GB (모든 모델 다운로드시)
- **GPU**: 강력히 권장 (VRAM 24GB+ 또는 여러 GPU)

### 소프트웨어
- **Python**: 3.8 이상
- **Ollama**: 최신 버전
- **운영체제**: macOS, Linux, Windows (WSL2)

## 🎯 프로젝트 특징

### 기술적 특징
- **비동기 처리**: 모델 간 효율적인 통신
- **오류 복구**: 모델 응답 실패시 자동 대체
- **로깅 시스템**: 완전한 게임 기록 보존
- **확장성**: 새로운 모델 쉽게 추가 가능

### 게임 디자인
- **심리적 요소**: 각 AI의 "연기" 분석
- **전략적 요소**: 투표와 액션의 복합적 판단
- **예측 불가능성**: AI마다 다른 행동 패턴

## 🔧 커스터마이징

### 새로운 모델 추가
`src/models_config.py`에서 모델 정보를 수정:

```python
MODELS = {
    "NewFruit": {
        "model_name": "new-model:version",
        "company": "Company Name",
        "params": "Size",
        "specialty": "특징"
    }
}
```

### 게임 규칙 변경
`src/models_config.py`의 `GAME_CONFIG`에서 설정 변경:

```python
GAME_CONFIG = {
    "total_models": 12,
    "conversation_rounds_per_pair": 5,  # 대화 턴 수
    "action_available_from_round": 3,   # 액션 시작 라운드
    "max_actions_per_conversation": 1,  # 대화당 최대 액션 수
}
```

## 🤝 기여하기

1. 이 저장소를 Fork
2. 기능 브랜치 생성 (`git checkout -b feature/amazing-feature`)
3. 변경사항 커밋 (`git commit -m 'Add amazing feature'`)
4. 브랜치에 Push (`git push origin feature/amazing-feature`)
5. Pull Request 생성

## 📜 라이센스

이 프로젝트는 MIT 라이센스 하에 배포됩니다. 자세한 내용은 [`LICENSE`](LICENSE) 파일을 참고하세요.

## 🙋 FAQ

**Q: 모델 다운로드에 시간이 너무 오래 걸려요**
A: 큰 모델(70B+)은 수십 GB 크기입니다. 안정적인 인터넷 연결이 필요하며, 중단되더라도 재시작하면 이어받기가 됩니다.

**Q: GPU가 없어도 실행 가능한가요?**
A: 네, CPU로도 실행 가능합니다. 다만 응답 속도가 느려 게임 시간이 길어질 수 있습니다.

**Q: 모델이 응답하지 않아요**
A: Ollama 서버가 실행 중인지 확인하고, 모델이 제대로 다운로드되었는지 확인해주세요.

**Q: 게임 결과를 어떻게 해석하나요?**
A: `game_log.json` 파일을 열어 각 AI의 대화 패턴, 투표 이유, 액션 성공률 등을 분석해보세요!

---

🎪 **즐거운 AI 연기 대결을 관찰해보세요!** 🎪
