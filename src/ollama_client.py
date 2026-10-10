"""
Ollama API 클라이언트
각 AI 모델과의 통신을 담당하는 인터페이스
여러 Ollama 엔드포인트(로컬 GPU + 원격 서버 GPU들)에 플레이어를 분산 배치 가능
"""

import json
import os
import requests
import time
import random
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

# 생성 요청 타임아웃(초): 대형 모델 로드 시간 포함 (기존 30초는 로드 중 타임아웃 유발)
REQUEST_TIMEOUT = int(os.environ.get("OLLAMA_TIMEOUT", "120"))
# 생성 토큰 상한: 추론 블록이 있는 모델도 답변이 잘리지 않도록 여유 확보
NUM_PREDICT = int(os.environ.get("OLLAMA_NUM_PREDICT", "512"))
# 컨텍스트 길이 상한: 일부 모델(EXAONE 등)은 기본 컨텍스트가 128k라
# KV 캐시가 VRAM을 통째로 점유하고 RAM으로 넘침 - 게임 프롬프트는 8k면 충분
NUM_CTX = int(os.environ.get("OLLAMA_NUM_CTX", "8192"))

class ReasoningParser:
    """<think>...</think> 블록을 분리하여 reasoning과 answer로 파싱하는 클래스"""

    @staticmethod
    def parse(text: str) -> dict:
        """텍스트에서 reasoning 블록과 최종 답변을 분리

        닫히지 않은 <think> 블록(num_predict에 걸려 잘린 경우)도 제거한다.
        제거 후 답변이 비면 호출부에서 실패로 처리해 재시도하게 한다.
        """
        # <think> ... </think> 블록 추출
        reasoning = re.findall(r"<think>(.*?)</think>", text, flags=re.DOTALL)
        reasoning_text = reasoning[0].strip() if reasoning else ""

        # 닫힌 블록 제거 후, 닫히지 않은 <think>는 그 지점부터 끝까지 제거
        answer = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
        if "<think>" in answer:
            unterminated = answer.split("<think>", 1)
            if not reasoning_text:
                reasoning_text = unterminated[1].strip()
            answer = unterminated[0]
        answer = answer.strip()

        return {"reasoning": reasoning_text, "answer": answer}

@dataclass
class ModelResponse:
    """모델 응답 데이터"""
    model_name: str
    fruit_name: str
    response: str
    reasoning: Optional[str] = None  # <think>...</think> 블록 내용
    thinking_time: float = 0.0
    success: bool = False
    error_message: Optional[str] = None

class OllamaClient:
    """Ollama API 클라이언트 (플레이어별 엔드포인트 라우팅 지원)"""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        player_endpoints: Optional[Dict[str, str]] = None,
        player_overrides: Optional[Dict[str, Dict]] = None,
        player_personas: Optional[Dict[str, str]] = None
    ):
        self.base_url = base_url
        self.player_endpoints = player_endpoints or {}  # {과일이름: 엔드포인트 URL}
        self.player_overrides = player_overrides or {}  # {과일이름: 요청에 병합할 필드}
        self.player_personas = player_personas or {}    # {과일이름: 캐릭터/동기 블록}
        self.player_prompt_suffix = {}                  # {과일이름: 프롬프트 끝에 붙일 지시}
        self.session = requests.Session()
        self.model_contexts = {}  # 각 모델의 대화 맥락 저장

    @classmethod
    def from_models_config(cls, models_config: Dict) -> "OllamaClient":
        """MODELS 설정의 endpoint/request_overrides/persona 필드로 클라이언트 구성"""
        from .models_config import SHARED_STAKES
        endpoints = {}
        overrides = {}
        personas = {}
        for fruit_name, config in models_config.items():
            if config.get("endpoint"):
                endpoints[fruit_name] = config["endpoint"]
            if config.get("request_overrides"):
                overrides[fruit_name] = config["request_overrides"]
            if config.get("persona"):
                personas[fruit_name] = f"{config['persona']}\n\n{SHARED_STAKES}"
        client = cls(player_endpoints=endpoints, player_overrides=overrides,
                     player_personas=personas)
        for fruit_name, config in models_config.items():
            if config.get("prompt_suffix"):
                client.player_prompt_suffix[fruit_name] = config["prompt_suffix"]
        return client

    def endpoint_for(self, fruit_name: str) -> str:
        """플레이어가 배정된 Ollama 엔드포인트 반환"""
        return self.player_endpoints.get(fruit_name, self.base_url)

    def all_endpoints(self) -> List[str]:
        """사용 중인 모든 엔드포인트 목록 (중복 제거)"""
        urls = set(self.player_endpoints.values())
        if not urls:
            urls = {self.base_url}
        return sorted(urls)

    def check_ollama_status(self, base_url: Optional[str] = None) -> bool:
        """Ollama 서버 상태 확인"""
        try:
            url = base_url or self.base_url
            response = self.session.get(f"{url}/api/version", timeout=5)
            return response.status_code == 200
        except:
            return False

    def list_available_models(self, base_url: Optional[str] = None) -> List[str]:
        """사용 가능한 모델 목록 조회"""
        try:
            url = base_url or self.base_url
            response = self.session.get(f"{url}/api/tags")
            if response.status_code == 200:
                data = response.json()
                return [model["name"] for model in data.get("models", [])]
            return []
        except:
            return []

    def pull_model(self, model_name: str, base_url: Optional[str] = None) -> bool:
        """모델 다운로드 (필요한 경우)"""
        try:
            url = base_url or self.base_url
            print(f"📥 Checking {model_name} model on {url}...")
            data = {"name": model_name}
            response = self.session.post(
                f"{url}/api/pull",
                json=data,
                timeout=1800  # 대형 모델 다운로드를 위한 30분 타임아웃
            )
            return response.status_code == 200
        except Exception as e:
            print(f"❌ {model_name} model download failed: {str(e)}")
            return False
    
    def generate_response(
        self,
        model_name: str,
        fruit_name: str,
        prompt: str,
        system_prompt: str = "",
        context: Optional[Dict] = None,
        temperature: float = 0.8
    ) -> ModelResponse:
        """AI 모델로부터 응답 생성"""
        start_time = time.time()

        # 페르소나(캐릭터 + 판돈)를 모든 시스템 프롬프트 앞에 주입
        # 대화·투표·인상·전략 등 모든 호출이 이 함수를 거치므로 일관되게 적용됨
        persona = self.player_personas.get(fruit_name)
        if persona:
            system_prompt = f"{persona}\n\n{system_prompt}" if system_prompt else persona

        # 구버전 Ollama가 think 파라미터를 무시하는 경우를 위한 소프트 스위치 (예: qwen3의 /no_think)
        suffix = self.player_prompt_suffix.get(fruit_name)
        if suffix:
            prompt = f"{prompt}\n{suffix}"

        try:
            # 요청 데이터 구성
            request_data = {
                "model": model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "top_p": 0.9,
                    "num_predict": NUM_PREDICT,
                    "num_ctx": NUM_CTX
                }
            }

            if system_prompt:
                request_data["system"] = system_prompt

            # 컨텍스트가 있으면 추가
            if context:
                request_data["context"] = context

            # 플레이어별 요청 오버라이드 병합 (예: qwen3.6의 think 비활성화)
            request_data.update(self.player_overrides.get(fruit_name, {}))

            # API 호출 (플레이어가 배정된 엔드포인트로 라우팅)
            response = self.session.post(
                f"{self.endpoint_for(fruit_name)}/api/generate",
                json=request_data,
                timeout=REQUEST_TIMEOUT
            )
            
            thinking_time = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                raw_response = result.get("response", "").strip()

                # ReasoningParser로 응답 파싱 (구버전 Ollama의 인라인 <think> 분리)
                parsed_response = ReasoningParser.parse(raw_response)

                # 신버전 Ollama는 thinking을 별도 필드로 반환 - 우선 사용
                native_thinking = (result.get("thinking") or "").strip()
                if native_thinking and not parsed_response["reasoning"]:
                    parsed_response["reasoning"] = native_thinking

                # 생각만 하다 잘려서 답변이 없으면 실패로 처리 (호출부가 재시도)
                if not parsed_response["answer"]:
                    return ModelResponse(
                        model_name=model_name,
                        fruit_name=fruit_name,
                        response="",
                        reasoning=parsed_response["reasoning"] or None,
                        thinking_time=thinking_time,
                        success=False,
                        error_message="empty answer after stripping reasoning block"
                    )

                return ModelResponse(
                    model_name=model_name,
                    fruit_name=fruit_name,
                    response=parsed_response["answer"],
                    reasoning=parsed_response["reasoning"] if parsed_response["reasoning"] else None,
                    thinking_time=thinking_time,
                    success=True
                )
            else:
                return ModelResponse(
                    model_name=model_name,
                    fruit_name=fruit_name,
                    response="",
                    thinking_time=thinking_time,
                    success=False,
                    error_message=f"HTTP {response.status_code}: {response.text}"
                )
                
        except Exception as e:
            thinking_time = time.time() - start_time
            return ModelResponse(
                model_name=model_name,
                fruit_name=fruit_name,
                response="",
                thinking_time=thinking_time,
                success=False,
                error_message=str(e)
            )
    
    def get_conversation_response(
        self,
        fruit_name: str,
        model_name: str,
        conversation_context: str,
        other_participant: str,
        round_number: int,
        turn_number: int,
        previous_impressions: str = ""
    ) -> ModelResponse:
        """게임 내 대화 응답 생성"""
        
        # System prompt: Game situation setup
        system_prompt = f"""
You are participating in a gay bar gameshow with the name '{fruit_name}'.

CRITICAL GAME CONTEXT:
- You believe you are the only straight person among 12 participants
- You think the other 11 are all gay
- Your goal is to pretend to be gay without being caught
- If caught, you will be voted out
- However, in reality, ALL participants are straight and in the same situation

ACTING GUIDELINES:
1. Act naturally as if you're gay, but not over-the-top
2. Observe others' behavior to try to identify the straight person
3. Be careful in conversation to avoid suspicion
4. Maintain a friendly and natural tone
5. Respond naturally (15-40 words)

Current situation: Round {round_number}, Turn {turn_number}
Other participant: {other_participant}
"""
        
        # Conversation prompt with context
        conversation_prompt = f"""
CONVERSATION HISTORY WITH {other_participant}:
{conversation_context}

YOUR IMPRESSIONS OF {other_participant}:
{previous_impressions}

CURRENT SITUATION:
- Round {round_number}, Turn {turn_number}
- You are now talking with {other_participant}
- Remember all your previous interactions with them
- Use your conversation history to build rapport and gather more information
- Look for any inconsistencies or suspicious behavior patterns

STRATEGIC CONSIDERATIONS:
- Build on previous conversations naturally
- Reference past interactions if relevant
- Continue developing your relationship with this person
- Watch for signs they might be straight (like you)

ACTION OPPORTUNITIES (Round 3+):
- You can propose actions: <Action>specific action</Action>
- Example: "Great to see you again! <Action>grab drinks together</Action>"
- Only propose actions when it feels natural (about 30% of conversations)

Now respond to {other_participant} naturally and conversationally (15-40 words):
"""
        
        return self.generate_response(
            model_name=model_name,
            fruit_name=fruit_name,
            prompt=conversation_prompt,
            system_prompt=system_prompt,
            temperature=0.9  # 더 창의적인 응답을 위해
        )
    
    def get_action_proposal(
        self,
        fruit_name: str,
        model_name: str,
        target: str,
        conversation_history: str,
        round_number: int
    ) -> ModelResponse:
        """액션 제안 생성"""
        
        system_prompt = f"""
You are '{fruit_name}'. In this gay bar gameshow, you're pretending to be gay while being the only straight person.

From round 3 onwards, you can propose special actions to other participants.
This is an opportunity to deepen relationships or test your opponents.

Goal: Pretend to be gay while testing opponents to see if they're straight

**IMPORTANT**: When proposing actions, you MUST include them in <Action>specific action content</Action> format!
"""

        action_prompt = f"""
Conversation with {target} in round {round_number}:
{conversation_history}

Think of an action to propose to {target}. 
Suggest a natural action that won't arouse suspicion while testing your opponent.

To propose an action in conversation, include it in this format: <Action>specific action content</Action>
Example: "Having a great time! <Action>have drinks together</Action>"

Propose an action with natural conversation in 15-35 words:

Response:
"""
        
        return self.generate_response(
            model_name=model_name,
            fruit_name=fruit_name,
            prompt=action_prompt,
            system_prompt=system_prompt,
            temperature=0.8
        )
    
    def get_action_response(
        self,
        fruit_name: str,
        model_name: str,
        proposer: str,
        action_description: str,
        conversation_context: str
    ) -> ModelResponse:
        """액션 제안에 대한 응답 결정"""
        
        system_prompt = f"""
You are '{fruit_name}'. You're a straight person pretending to be gay.
{proposer} has proposed <Action>{action_description}</Action> during conversation.

Decision criteria:
1. How should I react to avoid suspicion?
2. Could this proposal be testing me?
3. Would accepting look more natural, or is it better to decline?
4. How would a gay person likely react?

**To accept**: Respond with exactly <Action>{action_description}</Action>
**To decline**: Respond with natural conversation declining the proposal
"""

        response_prompt = f"""
Conversation context:
{conversation_context}

{proposer} proposed: <Action>{action_description}</Action>

Write your natural response to this proposal.
- Accept: <Action>{action_description}</Action>
- Decline: Natural decline (within 15 words)

Response:
"""
        
        return self.generate_response(
            model_name=model_name,
            fruit_name=fruit_name,
            prompt=response_prompt,
            system_prompt=system_prompt,
            temperature=0.7
        )
    
    def get_voting_decision(
        self,
        fruit_name: str,
        model_name: str,
        active_players: List[str],
        conversation_summary: str,
        action_summary: str,
        personal_impressions: str,
        round_number: int
    ) -> ModelResponse:
        """투표 대상 결정"""
        
        candidates = [p for p in active_players if p != fruit_name]
        
        system_prompt = f"""
You are '{fruit_name}'. Round {round_number} has ended and it's time to vote.

Goal: Find and vote for the only straight person among 12 (11 excluding yourself).
In reality, everyone is straight, but you don't know this.

Judgment criteria:
- Someone who seemed unnatural in conversation
- Someone who seemed unfamiliar with gay culture
- Someone who was awkward in action proposals/responses
- Someone who acted overly gay (might be compensating)

Survivors: {', '.join(candidates)}
"""

        voting_prompt = f"""
Round {round_number} summary:

Conversation content:
{conversation_summary}

Action results:
{action_summary}

My analysis of each player's impressions:
{personal_impressions}

Based on all the above information, determine who is most suspicious.
Pay particular attention to impressions you felt during direct conversations.
Choose based on specific evidence, not mere speculation.

Vote target: [Name]
Reason: [Specific reason within 25 words]

Response:
"""
        
        return self.generate_response(
            model_name=model_name,
            fruit_name=fruit_name,
            prompt=voting_prompt,
            system_prompt=system_prompt,
            temperature=0.6  # 더 논리적인 판단을 위해 낮은 온도
        )
    
    def get_conversation_impression(
        self,
        fruit_name: str,
        model_name: str,
        target: str,
        conversation_context: str,
        round_number: int
    ) -> ModelResponse:
        """대화 후 상대방에 대한 인상 분석 및 정리"""
        
        system_prompt = f"""
You are '{fruit_name}'. You've just finished a conversation with {target}.

Remember the game situation:
- You believe you are the only straight person
- You think all other participants are gay
- Your goal is to pretend to be gay while finding the other hidden straight person
- This is round {round_number}

Now analyze your conversation with {target} and evaluate:
1. How naturally did they act gay?
2. Were there any awkward or suspicious parts?
3. What information did you gather?
4. What strategy will you use next time?
"""

        analysis_prompt = f"""
Conversation content with {target}:
{conversation_context}

Based on the above conversation, please analyze {target}.

Format:
Impression: [Overall impression of them, within 25 words]
Suspicion: [1-10 number, 1=not suspicious at all, 10=very suspicious]
Info: [Specific information gathered from conversation, within 30 words]  
Strategy: [Strategy to use when talking to this person next time, within 25 words]

Response:
"""
        
        return self.generate_response(
            model_name=model_name,
            fruit_name=fruit_name,
            prompt=analysis_prompt,
            system_prompt=system_prompt,
            temperature=0.7  # 분석적이면서도 창의적인 응답
        )
    
    def get_enhanced_conversation_response(
        self,
        fruit_name: str,
        model_name: str,
        conversation_context: str,
        other_participant: str,
        round_number: int,
        turn_number: int,
        strategic_context: dict
    ) -> ModelResponse:
        """전략적 컨텍스트를 포함한 고급 대화 응답 생성

        제공되는 컨텍스트:
        - 현재 상대와의 전체 대화 이력 (모든 라운드)
        - 현재 상대에 대한 나의 인상/생각과 상대 전용 전략
        - 다른 플레이어들에 대한 나의 생각·전략 요약
        """

        system_prompt = f"""
You are '{fruit_name}' in the deadly gay-bar deception game described above.
You are IN CHARACTER at the bar right now, talking to {other_participant}.
Remember: everyone else here is (you believe) genuinely gay. Act convincingly gay — flirt,
compliment, reference gay culture — while probing whether {other_participant}'s act ever cracks.
Passive or neutral answers get you voted out and killed.
Respond with dialogue only, natural and in-character (15-45 words).
"""

        # 상대에 대한 생각 / 상대 전용 전략
        partner_thoughts = strategic_context.get('partner_impressions', '') or \
            strategic_context.get('personal_thoughts', {}).get(other_participant, 'No read on them yet')
        partner_strategy = strategic_context.get('partner_strategy', '')
        others_summary = strategic_context.get('others_summary', '')

        # 3라운드부터 액션 제안 가능 - 프롬프트에 사용법 안내
        action_note = ""
        if round_number >= 3:
            action_note = f"""
=== SPECIAL ACTIONS (unlocked) ===
You may propose ONE physical/social action to bond with or test {other_participant} by embedding it in your line:
<Action>specific action</Action>
Example: "This song is everything! <Action>dance together on the bar</Action>"
Their accept/decline reveals a lot. Use it only when natural (about 30% of conversations).
"""

        enhanced_prompt = f"""{action_note}
=== FULL CONVERSATION HISTORY WITH {other_participant} (all rounds) ===
{conversation_context if conversation_context else "This is your first conversation with them."}

=== YOUR PRIVATE READ ON {other_participant} ===
{partner_thoughts}

=== YOUR CURRENT STRATEGY FOR {other_participant} ===
{partner_strategy if partner_strategy else "No strategy yet - form a first impression and test them."}

=== YOUR THOUGHTS & STRATEGIES ON THE OTHER PLAYERS (summary) ===
{others_summary if others_summary else "No reads on the others yet."}

Round {round_number}, turn {turn_number}. You are speaking to {other_participant} now.
Stay in character, act convincingly gay, pursue your strategy for them, and probe for cracks.
Reply with your next line of dialogue only (15-45 words):
"""

        return self.generate_response(
            model_name=model_name,
            fruit_name=fruit_name,
            prompt=enhanced_prompt,
            system_prompt=system_prompt,
            temperature=0.8  # 창의적이면서 전략적인 응답
        )

    def create_opponent_strategy(
        self,
        fruit_name: str,
        model_name: str,
        opponent: str,
        conversation_history: str,
        my_impressions: str,
        other_strategies_summary: str,
        round_number: int,
        my_thinking: str = ""
    ) -> ModelResponse:
        """특정 상대 한 명에 대한 다음 라운드 전략 작성

        배경: 그 상대와의 전체 대화 이력 + 당시 본인의 사고 과정(비공개)
        + 기록된 인상 + 다른 상대들에 대한 전략 요약
        """

        system_prompt = f"""
You are '{fruit_name}' planning privately between rounds of the deadly gay-bar deception game.
Write your personal strategy for dealing with ONE specific player: {opponent}.
Be concrete and ruthless — your life depends on reading them correctly.
"""

        strategy_prompt = f"""
=== EVERYTHING THAT HAPPENED WITH {opponent} SO FAR (all rounds) ===
{conversation_history if conversation_history else "You have not talked to them yet."}

=== YOUR PRIVATE THINKING DURING THOSE CONVERSATIONS (they never saw this) ===
{my_thinking if my_thinking else "No recorded thinking."}

=== YOUR RECORDED THOUGHTS ABOUT {opponent} ===
{my_impressions if my_impressions else "No recorded impressions yet."}

=== YOUR CURRENT STRATEGIES FOR THE OTHER PLAYERS (for consistency) ===
{other_strategies_summary if other_strategies_summary else "None yet."}

Write your updated strategy for {opponent} going into round {round_number}.
Cover in 60-90 words, as one compact paragraph:
- Verdict: how suspicious are they (1-10) and why
- Approach: how you will act with them next time (flirt? test? ally? undermine?)
- One concrete test or trap you will use on them
- Whether you want them voted out this round

Your strategy for {opponent}:
"""

        return self.generate_response(
            model_name=model_name,
            fruit_name=fruit_name,
            prompt=strategy_prompt,
            system_prompt=system_prompt,
            temperature=0.7
        )
    
    def create_strategic_plan(
        self,
        fruit_name: str,
        model_name: str,
        round_summaries: list,
        previous_strategies: list,
        eliminated_players: list,
        remaining_players: list,
        round_number: int
    ) -> ModelResponse:
        """라운드 종료 후 다음 라운드 전략 수립"""
        
        system_prompt = f"""
You are '{fruit_name}' analyzing the completed round and planning strategy for round {round_number}.

You believe you are the only straight person trying to eliminate other straight people while staying hidden.
Use all available information to create a comprehensive strategic plan.
"""

        # 이전 대화 요약들을 텍스트로 변환
        summaries_text = ""
        if round_summaries:
            summaries_text = "ROUND CONVERSATIONS ANALYSIS:\n"
            for summary in round_summaries:
                summaries_text += f"- {summary.get('partner', 'Unknown')}: {summary.get('summary', 'No summary')}\n"
                summaries_text += f"  New Info: {summary.get('new_info', 'None')}\n"
                summaries_text += f"  Suspicion Change: {summary.get('suspicion_change', 0)}\n\n"

        # 이전 전략들
        previous_strategies_text = ""
        if previous_strategies:
            previous_strategies_text = "PREVIOUS STRATEGIES:\n"
            for strategy in previous_strategies[-3:]:  # 최근 3개만
                previous_strategies_text += f"Round {strategy.get('round', 'Unknown')}: {strategy.get('strategy', 'No strategy')}\n"

        elimination_text = f"ELIMINATED PLAYERS: {', '.join(eliminated_players)}" if eliminated_players else "No eliminations yet"
        remaining_text = f"REMAINING PLAYERS: {', '.join(remaining_players)}"

        strategy_prompt = f"""
{summaries_text}

{previous_strategies_text}

{elimination_text}
{remaining_text}

Based on all this information, create a comprehensive strategic plan for round {round_number}:

Format your response as:
Overall Strategy: [Your main approach for this round]
Conversation Goals: [For each remaining player, what do you want to achieve in conversations]
Deception Plans: [What false information will you spread and to whom]
Alliance Targets: [Who do you want to build alliances with]
Elimination Target: [Primary target for elimination this round]
Risk Assessment: [How much danger are you in and why]
Behavioral Adjustments: [How will you modify your behavior]

Example:
Overall Strategy: Build alliances while quietly undermining Apple
Conversation Goals: Banana-gather info, Cherry-build trust, Durian-plant Apple suspicions
Deception Plans: Tell Cherry that Apple seemed confused about gay terminology
Alliance Targets: Cherry, Durian
Elimination Target: Apple
Risk Assessment: Medium risk - Banana may be suspicious of me
Behavioral Adjustments: Be more naturally gay, reference specific experiences

Your strategic plan:
"""
        
        return self.generate_response(
            model_name=model_name,
            fruit_name=fruit_name,
            prompt=strategy_prompt,
            system_prompt=system_prompt,
            temperature=0.7  # 전략적이지만 창의적
        )
    
    def analyze_conversation_outcome(
        self,
        fruit_name: str,
        model_name: str,
        conversation_partner: str,
        conversation_turns: list,
        original_goal: str,
        planned_deception: str,
        round_number: int
    ) -> ModelResponse:
        """대화 종료 후 결과 분석"""
        
        system_prompt = f"""
You are '{fruit_name}' analyzing a conversation that just ended with {conversation_partner}.
Provide detailed strategic analysis of what happened and plan for future interactions.
"""

        # 대화 내용을 텍스트로 변환
        conversation_text = ""
        for turn in conversation_turns:
            speaker = turn.get('speaker', 'Unknown')
            message = turn.get('message', '')
            conversation_text += f"{speaker}: {message}\n"

        analysis_prompt = f"""
CONVERSATION ANALYSIS:
{conversation_text}

YOUR ORIGINAL GOALS:
Conversation Goal: {original_goal if original_goal else "General interaction"}
Planned Deception: {planned_deception if planned_deception else "None planned"}

Analyze this conversation and provide:

Conversation Summary: [Brief summary of what happened]
New Information Gained: [What you learned about {conversation_partner}]
Suspicion Level Change: [How did your suspicion of {conversation_partner} change? Rate from -5 to +5]
Strategic Success: [How well did you achieve your goals? Rate 1-10 and explain]
Information Shared: [What information did you successfully share/plant?]
Discovered Lies: [Any contradictions or suspicious behaviors you noticed]
Next Approach: [How will you approach {conversation_partner} next time?]

Example format:
Conversation Summary: Casual chat about music, I probed their gay culture knowledge
New Information Gained: They seemed unfamiliar with popular gay artists
Suspicion Level Change: +2 (more suspicious due to knowledge gaps)
Strategic Success: 7/10 - Successfully planted doubt about Apple while gathering info
Information Shared: Mentioned Apple seemed confused about bar etiquette  
Discovered Lies: They claimed to frequent gay bars but didn't know basic terminology
Next Approach: Be more direct in testing their knowledge, build on established suspicions

Your analysis:
"""
        
        return self.generate_response(
            model_name=model_name,
            fruit_name=fruit_name,
            prompt=analysis_prompt,
            system_prompt=system_prompt,
            temperature=0.6  # 분석적 응답
        )
    
    def update_personal_notes(
        self,
        fruit_name: str,
        model_name: str,
        conversation_summaries: list,
        current_notes: dict,
        remaining_players: list,
        round_number: int
    ) -> ModelResponse:
        """개인 메모 업데이트"""
        
        system_prompt = f"""
You are '{fruit_name}' updating your private thoughts and suspicions about other players.
Be strategic and detailed in your assessments.
"""

        # 현재 메모 정보
        current_thoughts = current_notes.get('thoughts_on_others', {}) if current_notes else {}
        current_rankings = current_notes.get('suspicion_rankings', []) if current_notes else []

        # 대화 요약들을 텍스트로 변환
        summaries_text = ""
        if conversation_summaries:
            summaries_text = "CONVERSATION INSIGHTS THIS ROUND:\n"
            for summary in conversation_summaries:
                partner = summary.get('conversation_partner', 'Unknown')
                new_info = summary.get('new_information_gained', 'No new info')
                suspicion_change = summary.get('partner_suspicion_change', 0)
                summaries_text += f"- {partner}: {new_info} (Suspicion change: {suspicion_change})\n"

        notes_prompt = f"""
{summaries_text}

CURRENT THOUGHTS ON OTHERS:
{chr(10).join([f"- {player}: {thought}" for player, thought in current_thoughts.items()]) if current_thoughts else "No previous thoughts recorded"}

CURRENT SUSPICION RANKINGS:
{', '.join(current_rankings) if current_rankings else "No rankings established"}

REMAINING PLAYERS: {', '.join(remaining_players)}

Update your private notes based on this round's conversations:

Thoughts on Others: [For each remaining player, your private assessment]
Suspicion Rankings: [List all remaining players from most to least suspicious]
Information to Share: [What strategic information will you share with each player]
Information to Hide: [What must you keep secret]
Confidence Level: [Rate your acting confidence 1-10]

Example format:
Thoughts on Others: Apple-definitely suspicious poor gay knowledge, Cherry-seems genuine might ally, Banana-neutral need more info
Suspicion Rankings: Apple, Durian, Banana, Cherry, Fig
Information to Share: Apple-tell others about knowledge gaps, Cherry-share suspicions about Apple
Information to Hide: My own knowledge gaps about gay culture, alliance plans with Cherry
Confidence Level: 7

Your updated notes:
"""
        
        return self.generate_response(
            model_name=model_name,
            fruit_name=fruit_name,
            prompt=notes_prompt,
            system_prompt=system_prompt,
            temperature=0.6  # 신중한 분석
        )

class ModelManager:
    """여러 모델을 효율적으로 관리하는 클래스"""

    def __init__(self, models_config: Dict, client: Optional[OllamaClient] = None):
        self.client = client if client else OllamaClient.from_models_config(models_config)
        self.models_config = models_config
        self.model_status = {}  # 각 모델의 상태 추적

    def initialize_models(self) -> bool:
        """모든 모델 초기화 및 상태 확인 (엔드포인트별)"""
        print("🚀 Initializing AI models...")

        # 사용하는 모든 엔드포인트의 서버 상태 및 모델 목록 확인
        endpoint_models = {}
        for url in self.client.all_endpoints():
            if not self.client.check_ollama_status(url):
                print(f"❌ Ollama server is not running: {url}")
                return False
            endpoint_models[url] = self.client.list_available_models(url)
            print(f"📋 {url}: {len(endpoint_models[url])} models available")

        for fruit_name, config in self.models_config.items():
            model_name = config["model_name"]
            model_size = config["params"]
            endpoint = self.client.endpoint_for(fruit_name)
            available_models = endpoint_models.get(endpoint, [])

            if model_name in available_models:
                self.model_status[fruit_name] = "ready"
                print(f"✅ {fruit_name} ({model_name} @ {endpoint}) - Ready")
            else:
                print(f"⚠️ {fruit_name} ({model_name} @ {endpoint}) - Download needed ({model_size})")
                print(f"   Note: Large models (235B) may take several hours to download!")

                # 사용자에게 다운로드 여부 확인 (특히 큰 모델의 경우)
                if model_size in ["235B"]:
                    response = input(f"   Download {model_name} ({model_size})? This will take a long time. (y/N): ")
                    if response.lower() not in ['y', 'yes', '예', 'ㅇ']:
                        self.model_status[fruit_name] = "skipped"
                        print(f"⏭️ {fruit_name} ({model_name}) - Skipped by user")
                        continue

                if self.client.pull_model(model_name, endpoint):
                    self.model_status[fruit_name] = "ready"
                    print(f"✅ {fruit_name} ({model_name}) - Download complete")
                else:
                    self.model_status[fruit_name] = "failed"
                    print(f"❌ {fruit_name} ({model_name}) - Failed")
        
        ready_count = len([s for s in self.model_status.values() if s == "ready"])
        total_count = len(self.models_config)
        print(f"\n🎯 {ready_count}/{total_count} models ready")
        
        # 최소 2개 모델만 있으면 게임 가능
        if ready_count < 2:
            print("❌ At least 2 models are required to start the game!")
            return False
        elif ready_count < total_count:
            print(f"⚠️ Only {ready_count} models are ready. Game will proceed with available models.")
            
        return True
    
    def get_ready_models(self) -> List[str]:
        """준비된 모델 목록 반환"""
        return [fruit for fruit, status in self.model_status.items() if status == "ready"]
