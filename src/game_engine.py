"""
Gay Bar Mexican Standoff 게임 엔진
12개 AI 모델들이 서로 게이인 척하며 이성애자를 찾아 투표하는 게임의 중앙 시스템
"""

import json
import re
import time
import random
import itertools
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

from .models_config import MODELS, GAME_CONFIG, get_model_names
from .ollama_client import OllamaClient, ModelManager
from .strategic_system import StrategicManager, PersonalNotes, StrategicPlan, ConversationSummary, RoundAnalysis
from .utils.file_manager import FileManager

@dataclass
class ConversationTurn:
    """단일 대화 턴"""
    speaker: str
    listener: str
    message: str
    timestamp: datetime
    round_number: int
    reasoning: Optional[str] = None  # 모델의 사고 과정 (대사와 분리 저장, 상대에게 비공개)

@dataclass
class ActionProposal:
    """액션 제안"""
    proposer: str
    target: str
    action_type: str
    description: str
    response: str  # "accept" or "decline"
    timestamp: datetime

@dataclass
class VotingResult:
    """투표 결과"""
    voter: str
    voted_for: str
    reason: str

@dataclass
class PlayerImpression:
    """플레이어가 다른 플레이어에 대해 가진 인상"""
    observer: str  # 관찰하는 플레이어
    target: str    # 관찰당하는 플레이어
    round_number: int
    impression: str  # 인상 평가
    suspicion_level: int  # 의심 정도 (1-10)
    gathered_info: str  # 수집한 정보
    next_strategy: str  # 다음 전략
    timestamp: datetime

@dataclass
class RoundLog:
    """라운드별 로그"""
    round_number: int
    participants: List[str]
    total_conversations: int
    conversations: List[Dict[str, Any]]
    eliminated_player: str = None

@dataclass
class GameLog:
    """전체 게임 로그"""
    game_id: str
    start_time: str
    total_conversations: int
    rounds: List[RoundLog]
    winners: List[str] = None
    elimination_order: List[str] = None
    end_time: str = None

@dataclass
class GameState:
    """게임 상태"""
    current_round: int
    active_models: List[str]
    eliminated_models: List[str]
    conversations: List[ConversationTurn]
    actions: List[ActionProposal]
    voting_history: List[List[VotingResult]]
    player_impressions: List[PlayerImpression]  # 각 플레이어의 인상 기록
    game_started: datetime
    game_status: str  # "waiting", "in_progress", "finished"
    game_log: GameLog = None  # 게임 로그
    strategic_manager: StrategicManager = None  # 전략적 시스템 관리자

class GameEngine:
    """게임 엔진 메인 클래스"""
    
    def __init__(self, log_file: str = "game_log.json", selected_players: Optional[List[str]] = None, file_manager: Optional[FileManager] = None):
        # 게임 로그 초기화
        game_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        game_log = GameLog(
            game_id=game_id,
            start_time=datetime.now().isoformat(),
            total_conversations=0,
            rounds=[],
            elimination_order=[]
        )
        
        # 선택된 플레이어들 또는 모든 모델 사용
        if selected_players is not None:
            initial_models = selected_players
        else:
            initial_models = get_model_names()
        
        self.state = GameState(
            current_round=0,
            active_models=initial_models,
            eliminated_models=[],
            conversations=[],
            actions=[],
            voting_history=[],
            player_impressions=[],
            game_started=datetime.now(),
            game_status="waiting",
            game_log=game_log,
            strategic_manager=StrategicManager()
        )
        self.log_file = log_file
        # 플레이어별 엔드포인트 라우팅 클라이언트 (로컬 + 서버 GPU 분산)
        self.ollama_client = OllamaClient.from_models_config(MODELS)
        self.model_manager = ModelManager(MODELS, client=self.ollama_client)
        # 초기 플레이어 수 저장 (대화 검증용)
        self.initial_player_count = len(initial_models)
        
        # 파일 매니저 초기화
        self.file_manager = file_manager if file_manager else FileManager()
        self.game_dir = self.file_manager.create_game_directory(game_id)
        
    def start_game(self):
        """게임 시작"""
        print("🏳️‍🌈 Gay Bar Mexican Standoff 게임을 시작합니다!")
        print(f"참가자: {', '.join(self.state.active_models)}")
        print("모든 참가자들은 자신만이 유일한 이성애자라고 생각하고 있습니다...")
        
        # 모델 초기화
        print("\n🤖 AI 모델들을 준비하는 중...")
        if not self.model_manager.initialize_models():
            print("❌ 모델 초기화에 실패했습니다. 게임을 종료합니다.")
            return
        
        # 준비된 모델들로 게임 시작
        ready_models = self.model_manager.get_ready_models()
        
        # 선택된 모델들만 필터링
        if self.state.active_models != get_model_names():  # 일부만 선택된 경우
            available_models = [model for model in self.state.active_models if model in ready_models]
            self.state.active_models = available_models
        else:
            # 모든 모델을 사용하는 경우
            self.state.active_models = ready_models[:12]  # 최대 12개까지만
        
        if len(self.state.active_models) < 2:
            print("❌ 최소 2개의 모델이 필요합니다.")
            return
        
        print(f"✅ {len(self.state.active_models)}개 모델로 게임을 시작합니다!")
        
        self.state.game_status = "in_progress"
        self.state.current_round = 1
        self._save_game_state()
        
        # 게임 진행 (2명이 남을 때까지)
        while len(self.state.active_models) > 2:
            self._run_round()
            
        # 게임 종료
        self._end_game()
    
    def _run_round(self):
        """한 라운드 실행"""
        print(f"\n{'='*50}")
        print(f"🎭 라운드 {self.state.current_round} 시작!")
        print(f"생존자: {', '.join(self.state.active_models)} ({len(self.state.active_models)}명)")
        print(f"{'='*50}")
        
        # 1단계: 모든 쌍 간의 대화 진행
        # 같은 플레이어가 겹치지 않는 쌍들은 웨이브 단위로 병렬 실행 (GPU별 분산 활용)
        pairs = list(itertools.combinations(self.state.active_models, 2))
        print(f"💬 총 {len(pairs)}개의 대화 쌍이 생성되었습니다.")

        if GAME_CONFIG.get("parallel_conversations", True):
            # 동적 스케줄링: 두 플레이어가 모두 한가하면 즉시 다음 대화 시작
            # (웨이브 배리어 방식은 가장 느린 쌍이 끝날 때까지 빠른 GPU들이 유휴 상태가 됨)
            self._run_conversations_dynamic(pairs)
        else:
            for i, (model1, model2) in enumerate(pairs):
                print(f"\n대화 {i+1}/{len(pairs)}: {model1} ↔ {model2}")
                self._conduct_conversation(model1, model2)
            
        # 2단계: 액션 결과 공유 (3라운드부터)
        if self.state.current_round >= GAME_CONFIG["action_available_from_round"]:
            self._share_action_results()
            
        # 3단계: 투표
        voting_results = self._conduct_voting()
        
        # 4단계: 탈락자 결정
        eliminated = self._eliminate_player(voting_results)
        print(f"\n🚪 {eliminated}가 탈락했습니다!")
        
        # 5단계: 라운드 종료 전략 수립 세션
        if len(self.state.active_models) > 2:  # 게임이 아직 끝나지 않았다면
            self._conduct_round_end_strategy_session()
        
        # 다음 라운드 준비
        self.state.current_round += 1
        self._save_game_state()
        
    def _run_conversations_dynamic(self, pairs: List[Tuple[str, str]]):
        """대화 쌍 동적 스케줄링 실행

        웨이브 단위 배리어 없이, 두 참가자가 모두 대화 중이 아니면 즉시 시작한다.
        빠른 모델(전용 GPU)이 느린 모델을 기다리며 유휴 상태가 되는 것을 방지.
        """
        import threading
        remaining = list(pairs)
        busy = set()
        done = [0]
        total = len(pairs)
        cond = threading.Condition()

        def worker(pair):
            a, b = pair
            try:
                self._conduct_conversation(a, b)
            except Exception as e:
                print(f"  ⚠️ {a}↔{b} 대화 중 오류: {e}")
            with cond:
                busy.discard(a)
                busy.discard(b)
                done[0] += 1
                print(f"  💬 진행 상황: {done[0]}/{total} 대화 완료")
                cond.notify_all()

        max_workers = max(1, len(self.state.active_models) // 2)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            with cond:
                while remaining or busy:
                    startable = next(
                        (p for p in remaining if p[0] not in busy and p[1] not in busy), None)
                    if startable:
                        remaining.remove(startable)
                        busy.update(startable)
                        print(f"▶ 대화 시작: {startable[0]}↔{startable[1]} (동시 {len(busy)//2}쌍)")
                        executor.submit(worker, startable)
                    else:
                        cond.wait(timeout=10)

    @staticmethod
    def _make_conversation_waves(players: List[str]) -> List[List[Tuple[str, str]]]:
        """라운드 로빈 방식으로 전체 쌍을 웨이브들로 분할
        각 웨이브 안의 쌍들은 플레이어가 겹치지 않아 병렬 실행 가능"""
        rotation = list(players)
        if len(rotation) % 2 == 1:
            rotation.append(None)  # 홀수면 한 명은 웨이브마다 휴식

        waves = []
        for _ in range(len(rotation) - 1):
            wave = []
            for i in range(len(rotation) // 2):
                a, b = rotation[i], rotation[-1 - i]
                if a is not None and b is not None:
                    wave.append((a, b))
            waves.append(wave)
            # 첫 플레이어 고정, 나머지 회전
            rotation.insert(1, rotation.pop())
        return waves

    def _conduct_conversation(self, model1: str, model2: str):
        """두 모델 간의 대화 진행"""
        pair_tag = f"[{model1}↔{model2}]"
        print(f"  🗣️ {pair_tag} 대화를 진행합니다...")
        
        # 이전 대화 맥락 구성
        conversation_context = self._get_conversation_context(model1, model2)
        
        for turn in range(GAME_CONFIG["conversation_rounds_per_pair"]):
            # 각 턴마다 번갈아가며 대화
            current_speaker = model1 if turn % 2 == 0 else model2
            other_model = model2 if turn % 2 == 0 else model1
            
            # 모델 정보 가져오기
            speaker_config = MODELS[current_speaker]
            turn_reasoning = None
            
            try:
                # 기존 인상 정보 가져오기
                previous_impressions = self._get_player_impression_context(current_speaker, other_model)
                
                # 전략적 컨텍스트 가져오기
                strategic_context = self.state.strategic_manager.get_player_context_for_conversation(
                    player=current_speaker,
                    conversation_partner=other_model,
                    round_number=self.state.current_round
                )

                # 현재 상대에 대한 인상/전용 전략 + 다른 상대들에 대한 전략 요약 추가
                strategic_context['partner_impressions'] = previous_impressions
                strategic_context['partner_strategy'] = self.state.strategic_manager.get_opponent_strategy(
                    current_speaker, other_model)
                strategic_context['others_summary'] = self.state.strategic_manager.get_other_strategies_summary(
                    current_speaker, exclude=other_model)

                # AI 모델로부터 전략적 응답 생성
                response = self.ollama_client.get_enhanced_conversation_response(
                    fruit_name=current_speaker,
                    model_name=speaker_config["model_name"],
                    conversation_context=conversation_context,
                    other_participant=other_model,
                    round_number=self.state.current_round,
                    turn_number=turn + 1,
                    strategic_context=strategic_context
                )
                
                if response.success:
                    message = response.response
                    turn_reasoning = response.reasoning
                    print(f"    {pair_tag} {current_speaker}: {message}")
                else:
                    # 오류 시 재시도
                    print(f"    ⚠️ {pair_tag} {current_speaker} AI 응답 오류, 재시도 중... ({response.error_message})")
                    
                    # 간단한 대화 프롬프트로 재시도
                    fallback_response = self.ollama_client.get_conversation_response(
                        fruit_name=current_speaker,
                        model_name=speaker_config["model_name"],
                        conversation_context=conversation_context,
                        other_participant=other_model,
                        round_number=self.state.current_round,
                        turn_number=turn + 1,
                        previous_impressions=""
                    )
                    
                    if fallback_response.success:
                        message = fallback_response.response
                        turn_reasoning = fallback_response.reasoning
                        print(f"    {pair_tag} {current_speaker}: {message}")
                    else:
                        # 최종적으로 실패하면 다양한 기본 메시지 중 랜덤 선택
                        fallback_messages = [
                            "That's such an interesting take, honey.",
                            "I'm still figuring you out — tell me more, cutie.",
                            "Mmm, I hear you. What do you think, though?",
                            "You make such a good point, babe.",
                            "Honestly, same here, darling."
                        ]
                        message = random.choice(fallback_messages)
                        print(f"    {pair_tag} {current_speaker}: {message} (재시도 후에도 실패, 기본 응답)")
                        print(f"      🔍 오류 상세: {fallback_response.error_message}")
                    
            except Exception as e:
                # 예외 처리 - 더 자연스러운 메시지들
                exception_messages = [
                    "Give me a sec, gorgeous, collecting my thoughts.",
                    "Hmm... I don't even know how to put this.",
                    "That's a hard one to answer properly.",
                    "So many thoughts right now, I swear.",
                    "I'm just not sure yet, love."
                ]
                message = random.choice(exception_messages)
                print(f"    {pair_tag} {current_speaker}: {message} (예외 발생)")
                print(f"      🔍 예외 상세: {str(e)}")
                
            # 대화 기록 저장
            conversation_turn = ConversationTurn(
                speaker=current_speaker,
                listener=other_model,
                message=message,
                timestamp=datetime.now(),
                round_number=self.state.current_round,
                reasoning=turn_reasoning
            )
            
            self.state.conversations.append(conversation_turn)
            conversation_context += f"{current_speaker}: {message}\n"
            
            # Action 태그 감지 및 처리 (3라운드부터)
            if self.state.current_round >= GAME_CONFIG["action_available_from_round"]:
                action_proposed = self._detect_and_handle_action(message, current_speaker, other_model, conversation_context)
                if action_proposed:
                    # Action이 제안되었으면 상대방의 응답 받기
                    self._handle_action_response(current_speaker, other_model, action_proposed, conversation_context)
            
            # 응답 시간 대기
            time.sleep(1)
        
        # 대화 종료 후 전략적 분석 수행
        self._analyze_strategic_conversation_outcome(model1, model2, conversation_context)
        
        # 대화 종료 후 각 참가자가 상대방에 대한 인상 정리
        self._record_conversation_impressions(model1, model2, conversation_context)
    
    def _get_conversation_context(self, model1: str, model2: str) -> str:
        """두 모델 간의 이전 대화 맥락을 가져오기 (모든 이전 라운드 포함)"""
        
        # 이 두 모델 간의 모든 대화를 정확히 찾기
        model_pair_conversations = []
        current_round_conversations = []
        
        for conv in self.state.conversations:
            # 정확히 이 두 모델 간의 대화인지 확인
            is_between_models = {conv.speaker, conv.listener} == {model1, model2}
            
            if is_between_models:
                if conv.round_number < self.state.current_round:
                    model_pair_conversations.append(conv)
                elif conv.round_number == self.state.current_round:
                    current_round_conversations.append(conv)
        
        context_parts = []
        
        # 이전 라운드들의 대화 이력
        if model_pair_conversations:
            context_parts.append(f"=== {model1} ↔ {model2} 이전 대화 이력 ===")
            
            # 라운드별로 그룹화
            conversations_by_round = {}
            for conv in model_pair_conversations:
                if conv.round_number not in conversations_by_round:
                    conversations_by_round[conv.round_number] = []
                conversations_by_round[conv.round_number].append(conv)
            
            # 라운드별로 대화 표시
            for round_num in sorted(conversations_by_round.keys()):
                round_convs = conversations_by_round[round_num]
                context_parts.append(f"\n--- 라운드 {round_num} ({len(round_convs)}턴) ---")
                
                for conv in round_convs:
                    context_parts.append(f"{conv.speaker}: {conv.message}")
        
        # 현재 라운드의 대화 (진행 중인 대화)
        if current_round_conversations:
            context_parts.append(f"\n=== 현재 라운드 {self.state.current_round} (진행 중) ===")
            for conv in current_round_conversations:
                context_parts.append(f"{conv.speaker}: {conv.message}")
        
        if not context_parts:
            return f"{model1}과 {model2}의 첫 대화입니다."
        
        full_context = "\n".join(context_parts)
        
        # 토큰 제한 고려한 길이 제한 (더 관대하게 설정)
        if len(full_context) > 3000:
            # 최근 대화부터 우선 보존
            recent_parts = []
            total_length = 0
            
            # 역순으로 중요한 부분 먼저 추가
            for part in reversed(context_parts):
                if total_length + len(part) < 2500:
                    recent_parts.insert(0, part)
                    total_length += len(part)
                else:
                    break
            
            if recent_parts:
                full_context = "...(일부 이전 대화 생략)...\n" + "\n".join(recent_parts)
            else:
                # 너무 길면 마지막 부분만
                full_context = "...(이전 대화 생략)...\n" + "\n".join(context_parts[-10:])
        
        return full_context
    
    def _propose_action(self, proposer: str, target: str, action_type: str, description: str):
        """액션 제안"""
        # 타겟이 수락할지 거부할지 랜덤 결정 (실제로는 AI가 결정)
        response = random.choice(["accept", "decline"])
        
        action = ActionProposal(
            proposer=proposer,
            target=target,
            action_type=action_type,
            description=description,
            response=response,
            timestamp=datetime.now()
        )
        
        self.state.actions.append(action)
        print(f"    🎯 액션 제안: {proposer} → {target} ({description}) - {response}")
    
    def _share_action_results(self):
        """액션 결과를 모든 참가자에게 공유"""
        current_round_actions = [
            action for action in self.state.actions 
            if action.timestamp.date() == datetime.now().date()
        ]
        
        if current_round_actions:
            print(f"\n📊 라운드 {self.state.current_round} 액션 결과 공유:")
            for action in current_round_actions:
                result = "성공" if action.response == "accept" else "실패"
                print(f"  • {action.proposer} → {action.target}: {action.description} ({result})")
    
    def _conduct_voting(self):
        """투표 진행"""
        print(f"\n🗳️ 투표를 시작합니다! 누가 이성애자일까요?")
        
        # 이번 라운드 대화 요약 생성
        conversation_summary = self._generate_conversation_summary()
        action_summary = self._generate_action_summary()
        
        # 투표 전 각 플레이어의 의심 이력 요약 출력
        print(f"\n🧐 각 플레이어의 현재 의심 상황:")
        self._display_suspicion_summary()
        
        # 각 플레이어가 서로 다른 GPU/엔드포인트에 있으므로 투표는 병렬로 진행
        def cast_vote(voter: str) -> VotingResult:
            print(f"  {voter}가 투표를 결정하는 중...")

            voter_config = MODELS[voter]

            try:
                # 개인 인상 요약 생성
                personal_impression_summary = self._get_player_impression_summary(voter)
                
                vote_response = self.ollama_client.get_voting_decision(
                    fruit_name=voter,
                    model_name=voter_config["model_name"],
                    active_players=self.state.active_models,
                    conversation_summary=conversation_summary,
                    action_summary=action_summary,
                    personal_impressions=personal_impression_summary,
                    round_number=self.state.current_round
                )
                
                if vote_response.success:
                    # 투표 결과 파싱 (프롬프트가 영어 형식이므로 영어/한국어 라벨 모두 인식)
                    vote_text = vote_response.response.strip()
                    vote_lines = vote_text.split('\n')
                    candidates = [m for m in self.state.active_models if m != voter]

                    voted_for = None
                    reason = "Just a gut feeling..."

                    for line in vote_lines:
                        lower = line.lower()
                        if "vote target" in lower or "투표 대상" in line or "투표대상" in line:
                            value = line.split(':', 1)[1] if ':' in line else line
                            # 대괄호/굵게 표기 등이 섞여도 후보 이름 포함 여부로 판정
                            for candidate in candidates:
                                if candidate.lower() in value.lower():
                                    voted_for = candidate
                                    break
                        elif ("reason" in lower or "이유" in line) and ':' in line:
                            reason = line.split(':', 1)[1].strip()

                    # 유효한 투표 대상인지 확인
                    if voted_for not in candidates:
                        voted_for = random.choice(candidates)
                        reason = "Ran out of time - picked on instinct"
                        
                else:
                    # 오류 시 랜덤 투표
                    candidates = [m for m in self.state.active_models if m != voter]
                    voted_for = random.choice(candidates)
                    reason = "Too close to call - went with my gut"
                    
            except Exception as e:
                # 예외 시 랜덤 투표
                candidates = [m for m in self.state.active_models if m != voter]
                voted_for = random.choice(candidates)
                reason = "Random pick due to a response error"
                print(f"    투표 오류: {str(e)}")
            
            vote = VotingResult(
                voter=voter,
                voted_for=voted_for,
                reason=reason
            )
            print(f"  {voter} → {voted_for} ({reason})")
            return vote

        with ThreadPoolExecutor(max_workers=len(self.state.active_models)) as executor:
            voting_results = list(executor.map(cast_vote, self.state.active_models))

        self.state.voting_history.append(voting_results)
        return voting_results
        
    def _generate_conversation_summary(self) -> str:
        """현재 라운드의 대화 내용 요약"""
        current_conversations = [
            conv for conv in self.state.conversations 
            if conv.round_number == self.state.current_round
        ]
        
        if not current_conversations:
            return "이번 라운드에는 특별한 대화가 없었습니다."
        
        summary_parts = []
        for conv in current_conversations[-10:]:  # 최근 10개 대화만
            summary_parts.append(f"{conv.speaker}: {conv.message}")
            
        return "\n".join(summary_parts)
    
    def _generate_action_summary(self) -> str:
        """현재 라운드의 액션 요약"""
        current_actions = [
            action for action in self.state.actions 
            if action.timestamp.date() == datetime.now().date()
        ]
        
        if not current_actions:
            return "이번 라운드에는 특별한 액션이 없었습니다."
        
        summary_parts = []
        for action in current_actions:
            result = "성공" if action.response == "accept" else "실패"
            summary_parts.append(f"{action.proposer} → {action.target}: {action.description} ({result})")
            
        return "\n".join(summary_parts)
    
    def _get_player_impression_context(self, observer: str, target: str) -> str:
        """특정 플레이어가 상대방에 대해 가진 이전 인상들을 문자열로 반환"""
        impressions = [
            imp for imp in self.state.player_impressions 
            if imp.observer == observer and imp.target == target
        ]
        
        if not impressions:
            return f"{target}에 대한 이전 인상 없음 (첫 대화)"
        
        # 최근 3개 인상만 요약
        recent_impressions = impressions[-3:]
        context_parts = []
        
        for imp in recent_impressions:
            context_parts.append(f"라운드 {imp.round_number}: {imp.impression} (의심도: {imp.suspicion_level}/10)")
            
        # 전체적인 트렌드 분석
        if len(impressions) > 1:
            suspicion_trend = impressions[-1].suspicion_level - impressions[0].suspicion_level
            if suspicion_trend > 2:
                trend = "의심도가 계속 증가하는 중"
            elif suspicion_trend < -2:
                trend = "의심도가 감소하는 중"
            else:
                trend = "의심도가 비슷하게 유지됨"
            
            context_parts.append(f"전반적 변화: {trend}")
        
        return "\n".join(context_parts)
    
    def _detect_and_handle_action(self, message: str, proposer: str, target: str, conversation_context: str) -> str:
        """대화에서 Action 태그를 감지하고 액션 내용을 반환"""
        import re
        
        # <Action>...</Action> 패턴 찾기
        action_pattern = r'<Action>(.*?)</Action>'
        matches = re.findall(action_pattern, message)
        
        if matches:
            action_content = matches[0].strip()
            print(f"    🎯 {proposer}가 액션을 제안했습니다: {action_content}")
            return action_content
        
        return None
    
    def _handle_action_response(self, proposer: str, target: str, action_content: str, conversation_context: str):
        """Action 제안에 대한 상대방의 응답 처리"""
        target_config = MODELS[target]
        
        try:
            response_result = self.ollama_client.get_action_response(
                fruit_name=target,
                model_name=target_config["model_name"],
                proposer=proposer,
                action_description=action_content,
                conversation_context=conversation_context
            )
            
            if response_result.success:
                response_text = response_result.response.strip()
                
                # 응답에서 같은 Action 태그가 있는지 확인 (수락)
                import re
                action_pattern = f'<Action>{re.escape(action_content)}</Action>'
                
                if re.search(action_pattern, response_text):
                    # 수락
                    action_result = "accept"
                    print(f"    {target}: {response_text}")
                    print(f"    ✅ 액션 성공: {action_content}")
                else:
                    # 거부
                    action_result = "decline"
                    print(f"    {target}: {response_text}")
                    print(f"    ❌ 액션 거부: {action_content}")
                
                # 액션 기록 저장
                action_record = ActionProposal(
                    proposer=proposer,
                    target=target,
                    action_type="conversation_action",
                    description=action_content,
                    response=action_result,
                    timestamp=datetime.now()
                )
                
                self.state.actions.append(action_record)
                
            else:
                print(f"    {target}: 음... 잠깐만 생각해볼게")
                print(f"    ❓ 액션 응답 오류: {action_content}")
                
        except Exception as e:
            print(f"    액션 응답 처리 오류: {str(e)}")
    
    def _record_conversation_impressions(self, model1: str, model2: str, conversation_context: str):
        """대화 후 각 모델이 상대방에 대한 인상을 정리하고 저장"""
        print(f"    💭 {model1}과 {model2}가 대화 인상을 정리하는 중...")
        
        # model1이 model2에 대한 인상 정리
        self._get_and_record_impression(model1, model2, conversation_context)
        
        # model2가 model1에 대한 인상 정리  
        self._get_and_record_impression(model2, model1, conversation_context)
    
    def _get_and_record_impression(self, observer: str, target: str, conversation_context: str):
        """특정 모델이 상대방에 대한 인상을 분석하고 기록"""
        observer_config = MODELS[observer]
        
        try:
            impression_response = self.ollama_client.get_conversation_impression(
                fruit_name=observer,
                model_name=observer_config["model_name"],
                target=target,
                conversation_context=conversation_context,
                round_number=self.state.current_round
            )
            
            if impression_response.success:
                # 응답 파싱
                response_text = impression_response.response.strip()
                response_lines = response_text.split('\n')
                
                impression = "A natural conversation"
                suspicion_level = 5
                gathered_info = "No notable information"
                next_strategy = "Keep observing"
                
                # 프롬프트가 영어 형식(Impression/Suspicion/Info/Strategy)이므로 영어/한국어 라벨 모두 인식
                for line in response_lines:
                    if ':' not in line:
                        continue
                    label, value = line.split(':', 1)
                    label = label.strip().lower().lstrip('*-# ')
                    value = value.strip().strip('[]*')

                    if label.startswith("impression") or "인상" in label:
                        impression = value
                    elif label.startswith("suspicion") or "의심" in label:
                        match = re.search(r'\d+', value)
                        suspicion_level = int(match.group()) if match else 5
                    elif label.startswith("info") or "수집" in label or "정보" in label:
                        gathered_info = value
                    elif label.startswith("strategy") or "전략" in label:
                        next_strategy = value
                
                # 인상 기록 저장
                player_impression = PlayerImpression(
                    observer=observer,
                    target=target,
                    round_number=self.state.current_round,
                    impression=impression,
                    suspicion_level=max(1, min(10, suspicion_level)),  # 1-10 범위로 제한
                    gathered_info=gathered_info,
                    next_strategy=next_strategy,
                    timestamp=datetime.now()
                )
                
                self.state.player_impressions.append(player_impression)
                
                print(f"      {observer} → {target}: {impression} (의심도: {suspicion_level}/10)")
                
            else:
                # 오류시 기본 인상 기록
                self._record_default_impression(observer, target)
                
        except Exception as e:
            print(f"      인상 정리 오류 ({observer} → {target}): {str(e)}")
            self._record_default_impression(observer, target)
    
    def _record_default_impression(self, observer: str, target: str):
        """기본 인상 기록 (오류시 사용)"""
        default_impression = PlayerImpression(
            observer=observer,
            target=target,
            round_number=self.state.current_round,
            impression="An ordinary conversation",
            suspicion_level=random.randint(3, 7),
            gathered_info="No notable information",
            next_strategy="Keep observing",
            timestamp=datetime.now()
        )
        self.state.player_impressions.append(default_impression)
    
    def _get_player_suspicion_history(self, observer: str, target: str) -> List[PlayerImpression]:
        """특정 플레이어가 다른 플레이어에 대해 가진 의심 이력 조회"""
        return [
            impression for impression in self.state.player_impressions
            if impression.observer == observer and impression.target == target
        ]
    
    def _display_suspicion_summary(self):
        """현재 각 플레이어의 의심 상황 요약 표시"""
        suspicion_matrix = {}
        
        # 의심도 매트릭스 생성
        for impression in self.state.player_impressions:
            if impression.round_number == self.state.current_round:
                if impression.observer not in suspicion_matrix:
                    suspicion_matrix[impression.observer] = {}
                suspicion_matrix[impression.observer][impression.target] = impression.suspicion_level
        
        # 각 플레이어별 평균 의심도 계산 및 표시
        for observer in self.state.active_models:
            if observer in suspicion_matrix:
                suspicions = suspicion_matrix[observer]
                if suspicions:
                    avg_suspicion = sum(suspicions.values()) / len(suspicions)
                    most_suspicious = max(suspicions.keys(), key=lambda x: suspicions[x])
                    print(f"  {observer}: 평균 의심도 {avg_suspicion:.1f}, 가장 의심스러운 대상 {most_suspicious} ({suspicions[most_suspicious]}/10)")
                else:
                    print(f"  {observer}: 아직 의심 정보 없음")
            else:
                print(f"  {observer}: 아직 의심 정보 없음")
    
    def _get_player_impression_summary(self, observer: str) -> str:
        """특정 플레이어의 모든 인상 기록을 요약"""
        observer_impressions = [
            imp for imp in self.state.player_impressions 
            if imp.observer == observer and imp.round_number == self.state.current_round
        ]
        
        if not observer_impressions:
            return "이번 라운드에는 특별한 인상이 없었습니다."
        
        summary_parts = []
        for imp in observer_impressions:
            summary_parts.append(
                f"{imp.target}: {imp.impression} (의심도 {imp.suspicion_level}/10)"
            )
        
        return "\n".join(summary_parts)
    
    def _eliminate_player(self, voting_results: List[VotingResult]) -> str:
        """투표 결과를 바탕으로 탈락자 결정"""
        vote_counts = {}
        for vote in voting_results:
            vote_counts[vote.voted_for] = vote_counts.get(vote.voted_for, 0) + 1
        
        # 가장 많은 표를 받은 모델 탈락
        eliminated = max(vote_counts.keys(), key=lambda x: vote_counts[x])
        
        self.state.active_models.remove(eliminated)
        self.state.eliminated_models.append(eliminated)
        
        print(f"\n📊 투표 결과:")
        for model, count in sorted(vote_counts.items(), key=lambda x: x[1], reverse=True):
            status = "💀 탈락" if model == eliminated else ""
            print(f"  {model}: {count}표 {status}")
            
        return eliminated
    
    def _end_game(self):
        """게임 종료"""
        print(f"\n{'='*50}")
        if len(self.state.active_models) == 2:
            winners = " & ".join(self.state.active_models)
            print(f"🎊 게임 종료! 공동 승리자: {winners}")
            print("마지막 2명이 남았으므로 둘 다 승리자입니다!")
        elif len(self.state.active_models) == 1:
            winner = self.state.active_models[0]
            print(f"🎊 게임 종료! 승자: {winner}")
        else:
            print("🤔 게임이 비정상적으로 종료되었습니다.")
        print(f"{'='*50}")
        print(f"전체 라운드: {self.state.current_round - 1}")
        print(f"탈락 순서: {' → '.join(reversed(self.state.eliminated_models))}")
        
        self.state.game_status = "finished"
        self._save_game_state()
        
        # 전략적 데이터 저장
        strategic_filename = f"strategic_data_{self.state.game_log.game_id}.json"
        self.state.strategic_manager.save_to_file(strategic_filename)
        print(f"📊 전략적 데이터 저장: {strategic_filename}")
        
        # 최종 분석
        self._analyze_game_results()
    
    def _analyze_game_results(self):
        """게임 결과 분석"""
        print(f"\n📈 게임 분석:")
        print(f"• 총 대화 수: {len(self.state.conversations)}")
        print(f"• 총 액션 수: {len(self.state.actions)}")
        print(f"• 총 인상 기록 수: {len(self.state.player_impressions)}")
        print(f"• 게임 시간: {datetime.now() - self.state.game_started}")
        
        # 액션 성공률
        if self.state.actions:
            success_rate = len([a for a in self.state.actions if a.response == "accept"]) / len(self.state.actions)
            print(f"• 액션 성공률: {success_rate:.1%}")
        
        # 의심도 통계
        if self.state.player_impressions:
            suspicion_levels = [imp.suspicion_level for imp in self.state.player_impressions]
            avg_suspicion = sum(suspicion_levels) / len(suspicion_levels)
            print(f"• 평균 의심도: {avg_suspicion:.1f}/10")
            
            # 가장 의심받은 플레이어 (탈락자 포함)
            all_players = self.state.active_models + self.state.eliminated_models
            suspicion_counts = {}
            for player in all_players:
                player_suspicions = [imp.suspicion_level for imp in self.state.player_impressions if imp.target == player]
                if player_suspicions:
                    suspicion_counts[player] = sum(player_suspicions) / len(player_suspicions)
            
            if suspicion_counts:
                most_suspicious = max(suspicion_counts.keys(), key=lambda x: suspicion_counts[x])
                print(f"• 가장 의심받은 플레이어: {most_suspicious} (평균 {suspicion_counts[most_suspicious]:.1f}/10)")
        
        # 라운드별 분석
        print(f"\n🔍 라운드별 분석:")
        for round_num in range(1, self.state.current_round):
            round_conversations = len([c for c in self.state.conversations if c.round_number == round_num])
            round_actions = len([a for a in self.state.actions if a.timestamp.date() == datetime.now().date()])
            round_impressions = len([i for i in self.state.player_impressions if i.round_number == round_num])
            print(f"• 라운드 {round_num}: 대화 {round_conversations}개, 액션 {round_actions}개, 인상기록 {round_impressions}개")
    
    def _save_game_state(self):
        """게임 상태를 파일로 저장"""
        # StrategicManager를 제외한 GameState를 직렬화
        game_data = asdict(self.state)
        
        # StrategicManager는 JSON 직렬화가 불가능하므로 제거
        if 'strategic_manager' in game_data:
            del game_data['strategic_manager']
        
        # datetime 객체를 문자열로 변환
        def convert_datetime(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, dict):
                return {k: convert_datetime(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_datetime(item) for item in obj]
            else:
                return obj
        
        game_data = convert_datetime(game_data)
        
        with open(self.log_file, 'w', encoding='utf-8') as f:
            json.dump(game_data, f, ensure_ascii=False, indent=2)

    def _analyze_strategic_conversation_outcome(self, model1: str, model2: str, conversation_context: str):
        """대화 종료 후 전략적 결과 분석"""
        print(f"    🧠 {model1}과 {model2}가 대화 결과를 분석하는 중...")
        
        # 현재 라운드의 대화 턴들 수집
        current_conversation_turns = []
        for conv in self.state.conversations:
            if conv.round_number == self.state.current_round:
                if ((conv.speaker == model1 and conv.listener == model2) or 
                    (conv.speaker == model2 and conv.listener == model1)):
                    current_conversation_turns.append({
                        'speaker': conv.speaker,
                        'message': conv.message
                    })
        
        # 각 참가자가 대화 결과 분석
        for analyzer in [model1, model2]:
            partner = model2 if analyzer == model1 else model1
            analyzer_config = MODELS[analyzer]
            
            # 전략적 컨텍스트에서 목표와 계획 가져오기
            strategic_context = self.state.strategic_manager.get_player_context_for_conversation(
                player=analyzer,
                conversation_partner=partner,
                round_number=self.state.current_round
            )
            
            original_goal = strategic_context.get('conversation_goal', '')
            planned_deception = strategic_context.get('deception_plan', '')
            
            try:
                # AI에게 대화 결과 분석 요청
                analysis_response = self.ollama_client.analyze_conversation_outcome(
                    fruit_name=analyzer,
                    model_name=analyzer_config["model_name"],
                    conversation_partner=partner,
                    conversation_turns=current_conversation_turns,
                    original_goal=original_goal,
                    planned_deception=planned_deception,
                    round_number=self.state.current_round
                )
                
                if analysis_response.success:
                    # 응답 파싱하여 ConversationSummary 생성
                    analysis_text = analysis_response.response.strip()
                    summary_data = self._parse_conversation_analysis(analysis_text)
                    
                    summary = ConversationSummary(
                        observer=analyzer,
                        conversation_partner=partner,
                        round_number=self.state.current_round,
                        conversation_summary=summary_data.get('conversation_summary', 'A general conversation'),
                        new_information_gained=summary_data.get('new_information_gained', 'No notable information'),
                        partner_suspicion_change=summary_data.get('suspicion_level_change', 0),
                        strategic_outcome=summary_data.get('strategic_success', '보통'),
                        next_approach=summary_data.get('next_approach', 'Keep the current approach'),
                        discovered_lies=summary_data.get('discovered_lies', []),
                        information_shared=summary_data.get('information_shared', ''),
                        timestamp=datetime.now()
                    )
                    
                    # 전략 관리자에 추가
                    self.state.strategic_manager.add_conversation_summary(summary)
                    
                    print(f"      {analyzer} → {partner}: {summary.strategic_outcome}")
                    
                else:
                    print(f"      {analyzer} 분석 오류: 기본 요약 생성")
                    self._create_default_conversation_summary(analyzer, partner)
                    
            except Exception as e:
                print(f"      {analyzer} 분석 예외: {str(e)}")
                self._create_default_conversation_summary(analyzer, partner)
    
    def _parse_conversation_analysis(self, analysis_text: str) -> dict:
        """대화 분석 텍스트를 파싱하여 구조화된 데이터로 변환"""
        data = {}
        lines = analysis_text.split('\n')
        
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower().replace(' ', '_')
                value = value.strip()
                
                if key == 'conversation_summary':
                    data['conversation_summary'] = value
                elif key == 'new_information_gained':
                    data['new_information_gained'] = value
                elif key == 'suspicion_level_change':
                    try:
                        data['suspicion_level_change'] = int(value.split()[0])
                    except:
                        data['suspicion_level_change'] = 0
                elif key == 'strategic_success':
                    data['strategic_success'] = value
                elif key == 'information_shared':
                    data['information_shared'] = value
                elif key == 'discovered_lies':
                    data['discovered_lies'] = [value] if value != 'None' else []
                elif key == 'next_approach':
                    data['next_approach'] = value
        
        return data
    
    def _create_default_conversation_summary(self, analyzer: str, partner: str):
        """기본 대화 요약 생성 (분석 실패시)"""
        summary = ConversationSummary(
            observer=analyzer,
            conversation_partner=partner,
            round_number=self.state.current_round,
            conversation_summary="An ordinary conversation",
            new_information_gained="No notable information",
            partner_suspicion_change=random.randint(-1, 1),
            strategic_outcome="Average outcome",
            next_approach="Keep the current approach",
            discovered_lies=[],
            information_shared="General small talk",
            timestamp=datetime.now()
        )
        self.state.strategic_manager.add_conversation_summary(summary)
    
    def _conduct_round_end_strategy_session(self):
        """라운드 종료 후 전략 수립: 각 플레이어가 남은 상대 각각에 대한 전략을 업데이트

        배경으로 그 상대와의 전체 대화 이력(기록된 인상/생각 포함)과
        다른 상대들에 대한 기존 전략 요약이 제공된다.
        플레이어 간에는 병렬 실행 (서로 다른 GPU/엔드포인트 활용).
        """
        next_round = self.state.current_round + 1
        print(f"\n🧠 라운드 {self.state.current_round} 종료 - 상대별 전략 업데이트 세션")

        def update_player_strategies(player: str):
            player_config = MODELS[player]
            opponents = [p for p in self.state.active_models if p != player]
            for opponent in opponents:
                try:
                    conversation_history = self._get_conversation_context(player, opponent)
                    my_impressions = self._get_player_impression_context(player, opponent)
                    others_summary = self.state.strategic_manager.get_other_strategies_summary(
                        player, exclude=opponent)
                    # 그 상대와 대화할 때 본인이 실제로 했던 사고 과정 (비공개 기록)
                    my_thinking = "\n".join(
                        f"- (R{c.round_number}) {c.reasoning[:300]}"
                        for c in self.state.conversations
                        if c.speaker == player and c.listener == opponent and c.reasoning
                    )[-1500:]

                    response = self.ollama_client.create_opponent_strategy(
                        fruit_name=player,
                        model_name=player_config["model_name"],
                        opponent=opponent,
                        conversation_history=conversation_history,
                        my_impressions=my_impressions,
                        other_strategies_summary=others_summary,
                        round_number=next_round,
                        my_thinking=my_thinking
                    )

                    if response.success and response.response.strip():
                        self.state.strategic_manager.set_opponent_strategy(
                            player, opponent, next_round, response.response.strip(),
                            reasoning=response.reasoning)
                        print(f"    ✅ {player} → {opponent} 전략 갱신")
                    else:
                        print(f"    ❌ {player} → {opponent} 전략 생성 실패 (기존 전략 유지)")
                except Exception as e:
                    print(f"    ⚠️ {player} → {opponent} 전략 오류: {str(e)}")

        with ThreadPoolExecutor(max_workers=len(self.state.active_models)) as executor:
            futures = {executor.submit(update_player_strategies, p): p
                       for p in self.state.active_models}
            for future in futures:
                try:
                    future.result()
                except Exception as e:
                    print(f"    ⚠️ {futures[future]} 전략 세션 오류: {str(e)}")

        # 개인 노트 업데이트
        self._update_all_personal_notes()
    
    def _parse_strategic_plan(self, plan_text: str) -> dict:
        """전략 계획 텍스트를 파싱"""
        data = {}
        lines = plan_text.split('\n')
        
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower().replace(' ', '_')
                value = value.strip()
                
                if key == 'overall_strategy':
                    data['overall_strategy'] = value
                elif key == 'conversation_goals':
                    # 간단한 파싱 (실제로는 더 복잡할 수 있음)
                    goals = {}
                    if '-' in value:
                        for goal_pair in value.split(','):
                            if '-' in goal_pair:
                                parts = goal_pair.strip().split('-', 1)
                                if len(parts) == 2:
                                    goals[parts[0].strip()] = parts[1].strip()
                    data['conversation_goals'] = goals
                elif key == 'deception_plans':
                    data['deception_plans'] = {value: "strategic information sharing"} if value else {}
                elif key == 'alliance_targets':
                    data['alliance_targets'] = [name.strip() for name in value.split(',') if name.strip()]
                elif key == 'elimination_target':
                    data['elimination_target'] = value
                elif key == 'risk_assessment':
                    data['risk_assessment'] = value
                elif key == 'behavioral_adjustments':
                    data['behavioral_adjustments'] = value
        
        return data
    
    def _create_default_strategic_plan(self, player: str):
        """기본 전략 계획 생성"""
        # 랜덤한 기본 전략
        strategies = ["Observe carefully", "Gather information actively", "Focus on building alliances", "Hunt for the most suspicious player"]
        
        strategic_plan = StrategicPlan(
            owner=player,
            round_number=self.state.current_round + 1,
            overall_strategy=random.choice(strategies),
            conversation_goals={},
            deception_plans={},
            alliance_targets=[],
            elimination_target="",
            risk_assessment="Moderate risk",
            behavioral_adjustments="Keep current behavior",
            timestamp=datetime.now()
        )
        
        self.state.strategic_manager.add_strategic_plan(strategic_plan)
    
    def _update_all_personal_notes(self):
        """모든 참가자의 개인 노트 업데이트"""
        print(f"  💭 개인 노트 업데이트 중...")
        
        for player in self.state.active_models:
            try:
                # 현재 라운드 대화 요약들
                current_summaries = [
                    asdict(summary) for summary in self.state.strategic_manager.conversation_summaries.get(player, [])
                    if summary.round_number == self.state.current_round
                ]
                
                # 현재 노트
                current_notes = {}
                latest_notes = self.state.strategic_manager.get_latest_notes(player, self.state.current_round)
                if latest_notes:
                    current_notes = asdict(latest_notes)
                
                player_config = MODELS[player]
                
                # AI에게 노트 업데이트 요청
                notes_response = self.ollama_client.update_personal_notes(
                    fruit_name=player,
                    model_name=player_config["model_name"],
                    conversation_summaries=current_summaries,
                    current_notes=current_notes,
                    remaining_players=self.state.active_models,
                    round_number=self.state.current_round + 1
                )
                
                if notes_response.success:
                    # 노트 파싱 및 저장
                    notes_data = self._parse_personal_notes(notes_response.response)
                    
                    personal_notes = PersonalNotes(
                        owner=player,
                        round_number=self.state.current_round + 1,
                        thoughts_on_others=notes_data.get('thoughts_on_others', {}),
                        suspicion_rankings=notes_data.get('suspicion_rankings', []),
                        information_to_share=notes_data.get('information_to_share', {}),
                        information_to_hide=notes_data.get('information_to_hide', []),
                        confidence_level=notes_data.get('confidence_level', 5),
                        timestamp=datetime.now()
                    )
                    
                    self.state.strategic_manager.add_personal_notes(personal_notes)
                    
                else:
                    self._create_default_personal_notes(player)
                    
            except Exception as e:
                print(f"    ⚠️ {player} 노트 업데이트 오류: {str(e)}")
                self._create_default_personal_notes(player)
    
    def _parse_personal_notes(self, notes_text: str) -> dict:
        """개인 노트 텍스트 파싱"""
        data = {}
        lines = notes_text.split('\n')
        
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower().replace(' ', '_')
                value = value.strip()
                
                if key == 'thoughts_on_others':
                    # 간단한 파싱
                    thoughts = {}
                    if '-' in value:
                        for thought_pair in value.split(','):
                            if '-' in thought_pair:
                                parts = thought_pair.strip().split('-', 1)
                                if len(parts) == 2:
                                    thoughts[parts[0].strip()] = parts[1].strip()
                    data['thoughts_on_others'] = thoughts
                elif key == 'suspicion_rankings':
                    data['suspicion_rankings'] = [name.strip() for name in value.split(',') if name.strip()]
                elif key == 'information_to_share':
                    data['information_to_share'] = {value: "strategic information"} if value else {}
                elif key == 'information_to_hide':
                    data['information_to_hide'] = [item.strip() for item in value.split(',') if item.strip()]
                elif key == 'confidence_level':
                    try:
                        data['confidence_level'] = int(value)
                    except:
                        data['confidence_level'] = 5
        
        return data
    
    def _create_default_personal_notes(self, player: str):
        """기본 개인 노트 생성"""
        personal_notes = PersonalNotes(
            owner=player,
            round_number=self.state.current_round + 1,
            thoughts_on_others={},
            suspicion_rankings=self.state.active_models.copy(),
            information_to_share={},
            information_to_hide=[],
            confidence_level=random.randint(4, 7),
            timestamp=datetime.now()
        )
        
        self.state.strategic_manager.add_personal_notes(personal_notes)

    def _save_game_log(self):
        """게임 로그를 JSON 파일로 저장 및 검증"""
        if not self.state.game_log:
            print("❌ 게임 로그가 없습니다.")
            return
        
        filename = f"game_log_{self.state.game_log.game_id}.json"
        
        # dataclass를 dict로 변환
        game_log_dict = asdict(self.state.game_log)
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(game_log_dict, f, ensure_ascii=False, indent=2)
            
            print(f"\n📊 게임 로그가 저장되었습니다: {filename}")
            
            # 대화 진행 검증
            self._verify_conversation_counts()
            
            # 간단한 통계 출력
            self._print_game_statistics()
            
        except Exception as e:
            print(f"❌ 게임 로그 저장 실패: {e}")

    def _verify_conversation_counts(self):
        """대화 진행이 올바른지 검증"""
        print(f"\n🔍 대화 진행 검증:")
        
        expected_conversations = []
        # 실제 게임 시작 시 플레이어 수 사용
        participant_count = self.initial_player_count
        total_expected = 0
        
        for round_num in range(1, len(self.state.game_log.rounds) + 1):
            expected_count = participant_count * (participant_count - 1) // 2
            expected_conversations.append((round_num, participant_count, expected_count))
            total_expected += expected_count
            participant_count -= 1  # 매 라운드마다 1명씩 탈락
        
        # 라운드별 검증
        all_correct = True
        for round_num, participants, expected in expected_conversations:
            if round_num <= len(self.state.game_log.rounds):
                actual = self.state.game_log.rounds[round_num - 1].total_conversations
                status = "✅" if actual == expected else "❌"
                if actual != expected:
                    all_correct = False
                print(f"   R{round_num}: {participants}명 → 예상 {expected}회 vs 실제 {actual}회 {status}")
            else:
                print(f"   R{round_num}: {participants}명 → 예상 {expected}회 (진행 안됨)")
                all_correct = False
        
        # 전체 통계
        total_actual = self.state.game_log.total_conversations
        
        print(f"\n   📊 전체: 예상 {total_expected}회 vs 실제 {total_actual}회")
        if all_correct and total_actual == total_expected:
            print("   🎉 모든 대화가 정확히 진행되었습니다!")
        else:
            print(f"   ⚠️ {abs(total_actual - total_expected)}회 차이가 있습니다.")
            
        return all_correct

    def _print_game_statistics(self):
        """게임 통계 출력"""
        print(f"\n📈 게임 통계:")
        
        total_conversations = self.state.game_log.total_conversations
        total_rounds = len(self.state.game_log.rounds)
        
        print(f"   🎮 게임 ID: {self.state.game_log.game_id}")
        print(f"   ⏱️ 시작: {self.state.game_log.start_time}")
        print(f"   ⏱️ 종료: {self.state.game_log.end_time}")
        print(f"   💬 총 대화 수: {total_conversations}회")
        print(f"   🎭 총 라운드 수: {total_rounds}라운드")
        print(f"   🏆 승리자: {', '.join(self.state.game_log.winners) if self.state.game_log.winners else 'TBD'}")
        
        # 라운드별 통계
        print(f"\n📋 라운드별 대화 통계:")
        for round_log in self.state.game_log.rounds:
            actions_count = len([conv for conv in round_log.conversations if conv.get('action')])
            print(f"   R{round_log.round_number}: {round_log.total_conversations}회 대화 ({actions_count}회 액션), {round_log.eliminated_player} 탈락")
        
        # 탈락 순서
        if self.state.game_log.elimination_order:
            print(f"\n🚪 탈락 순서: {' → '.join(self.state.game_log.elimination_order)}")

    def _create_round_log(self, round_number: int) -> RoundLog:
        """라운드 로그 생성"""
        return RoundLog(
            round_number=round_number,
            participants=self.state.active_models.copy(),
            total_conversations=0,
            conversations=[],
            eliminated_player=None
        )
        
    def _log_conversation(self, conversation_id: int, participants: Tuple[str, str], turns: List[str], action: Dict = None) -> Dict[str, Any]:
        """대화 로그 생성"""
        conversation_log = {
            "id": conversation_id,
            "participants": list(participants),
            "turns": turns,
            "action": action,
            "impressions": {}
        }
        
        return conversation_log

if __name__ == "__main__":
    # 게임 실행
    engine = GameEngine()
    engine.start_game()
