#!/usr/bin/env python3
"""
고급 전략적 대화 시스템
각 AI가 개인적인 메모, 전략, 복잡한 사회적 추론을 통해 게임을 진행
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Any, Optional
import json

@dataclass
class PersonalNotes:
    """각 AI의 개인적인 메모장 - 다른 AI들에 대한 생각"""
    owner: str
    round_number: int
    thoughts_on_others: Dict[str, str]  # {다른_플레이어: 개인적_생각}
    suspicion_rankings: List[str]  # 의심스러운 순서대로 정렬 (가장 의심스러운 것부터)
    information_to_share: Dict[str, str]  # {대상: 퍼뜨릴_정보/거짓말}
    information_to_hide: List[str]  # 숨겨야 할 정보들
    confidence_level: int  # 자신의 연기에 대한 자신감 (1-10)
    timestamp: datetime

@dataclass 
class StrategicPlan:
    """각 라운드의 개인 전략"""
    owner: str
    round_number: int
    overall_strategy: str  # 전체적인 전략 (공격적/방어적/은밀함 등)
    conversation_goals: Dict[str, str]  # {대화_상대: 이번_대화_목표}
    deception_plans: Dict[str, str]  # {대상: 퍼뜨릴_거짓_정보}
    alliance_targets: List[str]  # 동맹을 구축하고 싶은 대상들
    elimination_target: str  # 이번 라운드에서 제거하고 싶은 대상
    risk_assessment: str  # 자신의 현재 위험도 평가
    behavioral_adjustments: str  # 행동 양식 조정 계획
    timestamp: datetime

@dataclass
class ConversationSummary:
    """대화 후 생성되는 요약 및 분석"""
    observer: str
    conversation_partner: str
    round_number: int
    conversation_summary: str  # 대화 내용 요약
    new_information_gained: str  # 새로 얻은 정보
    partner_suspicion_change: int  # 상대방 의심도 변화 (-5 ~ +5)
    strategic_outcome: str  # 전략적 목표 달성도 평가
    next_approach: str  # 다음에 만날 때 접근법
    discovered_lies: List[str]  # 발견한 거짓말이나 모순
    information_shared: str  # 상대방에게 제공한 정보
    timestamp: datetime

@dataclass
class RoundAnalysis:
    """라운드 종료 후 전체 상황 분석"""
    owner: str
    round_number: int
    overall_situation: str  # 전체 상황 평가
    eliminated_player_analysis: str  # 탈락자에 대한 분석
    remaining_threats: List[str]  # 남은 위협적인 플레이어들
    safe_players: List[str]  # 안전하다고 생각하는 플레이어들
    information_network: Dict[str, str]  # 정보 흐름 파악
    next_round_predictions: str  # 다음 라운드 예측
    timestamp: datetime

class StrategicManager:
    """전략적 시스템 관리자"""
    
    def __init__(self):
        self.personal_notes: Dict[str, List[PersonalNotes]] = {}  # {플레이어: [라운드별_노트]}
        self.strategic_plans: Dict[str, List[StrategicPlan]] = {}  # {플레이어: [라운드별_전략]}
        self.conversation_summaries: Dict[str, List[ConversationSummary]] = {}  # {플레이어: [대화_요약들]}
        self.round_analyses: Dict[str, List[RoundAnalysis]] = {}  # {플레이어: [라운드_분석들]}
        # {플레이어: {상대: [{"round": n, "strategy": text}, ...]}} - 상대별 전략 (매 라운드 업데이트)
        self.opponent_strategies: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}

    def initialize_player(self, player_name: str):
        """새 플레이어 초기화"""
        if player_name not in self.personal_notes:
            self.personal_notes[player_name] = []
            self.strategic_plans[player_name] = []
            self.conversation_summaries[player_name] = []
            self.round_analyses[player_name] = []
            self.opponent_strategies[player_name] = {}

    def set_opponent_strategy(self, player: str, opponent: str, round_number: int,
                              strategy: str, reasoning: str = None):
        """특정 상대에 대한 전략 저장 (라운드별 누적, 사고 과정 포함)"""
        self.initialize_player(player)
        self.opponent_strategies[player].setdefault(opponent, []).append(
            {"round": round_number, "strategy": strategy,
             "reasoning": reasoning, "timestamp": datetime.now()})

    def get_opponent_strategy(self, player: str, opponent: str) -> str:
        """특정 상대에 대한 최신 전략 반환"""
        self.initialize_player(player)
        history = self.opponent_strategies[player].get(opponent, [])
        return history[-1]["strategy"] if history else ""

    def get_other_strategies_summary(self, player: str, exclude: str = None) -> str:
        """다른 상대들에 대한 최신 전략을 한 줄씩 요약한 블록 반환"""
        self.initialize_player(player)
        lines = []
        for opponent, history in self.opponent_strategies[player].items():
            if opponent == exclude or not history:
                continue
            lines.append(f"- {opponent}: {history[-1]['strategy']}")
        return "\n".join(lines)
    
    def get_player_context_for_conversation(self, player: str, conversation_partner: str, round_number: int) -> Dict[str, Any]:
        """대화 시 사용할 플레이어의 모든 컨텍스트 정보 반환"""
        self.initialize_player(player)
        
        # 최신 개인 메모
        latest_notes = self.get_latest_notes(player, round_number)
        
        # 최신 전략
        latest_strategy = self.get_latest_strategy(player, round_number)
        
        # 해당 상대방과의 이전 대화 요약들
        partner_summaries = [
            summary for summary in self.conversation_summaries[player]
            if summary.conversation_partner == conversation_partner
        ]
        
        # 다른 플레이어들에 대한 현재 생각
        thoughts_on_others = latest_notes.thoughts_on_others if latest_notes else {}
        
        # 의심 순위
        suspicion_rankings = latest_notes.suspicion_rankings if latest_notes else []
        
        # 퍼뜨릴 정보 (거짓말 포함)
        info_to_share = latest_notes.information_to_share if latest_notes else {}
        
        # 대화 목표
        conversation_goal = ""
        deception_plan = ""
        if latest_strategy:
            conversation_goal = latest_strategy.conversation_goals.get(conversation_partner, "")
            deception_plan = latest_strategy.deception_plans.get(conversation_partner, "")
        
        return {
            "personal_thoughts": thoughts_on_others,
            "suspicion_rankings": suspicion_rankings,
            "conversation_goal": conversation_goal,
            "information_to_share": info_to_share.get(conversation_partner, ""),
            "deception_plan": deception_plan,
            "previous_conversations_summary": partner_summaries,
            "overall_strategy": latest_strategy.overall_strategy if latest_strategy else "",
            "elimination_target": latest_strategy.elimination_target if latest_strategy else "",
            "alliance_targets": latest_strategy.alliance_targets if latest_strategy else [],
            "confidence_level": latest_notes.confidence_level if latest_notes else 5
        }
    
    def get_latest_notes(self, player: str, round_number: int) -> Optional[PersonalNotes]:
        """플레이어의 최신 개인 메모 반환"""
        self.initialize_player(player)
        player_notes = [note for note in self.personal_notes[player] if note.round_number <= round_number]
        return player_notes[-1] if player_notes else None
    
    def get_latest_strategy(self, player: str, round_number: int) -> Optional[StrategicPlan]:
        """플레이어의 최신 전략 반환"""
        self.initialize_player(player)
        player_strategies = [strategy for strategy in self.strategic_plans[player] if strategy.round_number <= round_number]
        return player_strategies[-1] if player_strategies else None
    
    def add_personal_notes(self, notes: PersonalNotes):
        """개인 메모 추가"""
        self.initialize_player(notes.owner)
        self.personal_notes[notes.owner].append(notes)
    
    def add_strategic_plan(self, plan: StrategicPlan):
        """전략 계획 추가"""
        self.initialize_player(plan.owner)
        self.strategic_plans[plan.owner].append(plan)
    
    def add_conversation_summary(self, summary: ConversationSummary):
        """대화 요약 추가"""
        self.initialize_player(summary.observer)
        self.conversation_summaries[summary.observer].append(summary)
    
    def add_round_analysis(self, analysis: RoundAnalysis):
        """라운드 분석 추가"""
        self.initialize_player(analysis.owner)
        self.round_analyses[analysis.owner].append(analysis)
    
    def get_round_context_for_strategy(self, player: str, round_number: int) -> Dict[str, Any]:
        """전략 수립 시 사용할 라운드 컨텍스트"""
        self.initialize_player(player)
        
        # 이전 라운드의 모든 대화 요약
        previous_summaries = [
            summary for summary in self.conversation_summaries[player]
            if summary.round_number == round_number - 1
        ]
        
        # 이전 전략들
        previous_strategies = [
            strategy for strategy in self.strategic_plans[player]
            if strategy.round_number < round_number
        ]
        
        # 이전 라운드 분석들
        previous_analyses = [
            analysis for analysis in self.round_analyses[player]
            if analysis.round_number < round_number
        ]
        
        return {
            "previous_conversation_summaries": previous_summaries,
            "previous_strategies": previous_strategies,
            "previous_round_analyses": previous_analyses,
            "round_number": round_number
        }
    
    def save_to_file(self, filename: str):
        """전략적 데이터를 파일로 저장"""
        data = {
            "personal_notes": {k: [asdict(note) for note in v] for k, v in self.personal_notes.items()},
            "strategic_plans": {k: [asdict(plan) for plan in v] for k, v in self.strategic_plans.items()},
            "conversation_summaries": {k: [asdict(summary) for summary in v] for k, v in self.conversation_summaries.items()},
            "round_analyses": {k: [asdict(analysis) for analysis in v] for k, v in self.round_analyses.items()},
            "opponent_strategies": self.opponent_strategies
        }
        
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
        
        data = convert_datetime(data)
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def get_player_summary(self, player: str, round_number: int) -> str:
        """플레이어의 현재 상태 요약"""
        latest_notes = self.get_latest_notes(player, round_number)
        latest_strategy = self.get_latest_strategy(player, round_number)
        
        summary = f"=== {player}의 현재 상태 (라운드 {round_number}) ===\n"
        
        if latest_notes:
            summary += f"의심 순위: {', '.join(latest_notes.suspicion_rankings[:3])}...\n"
            summary += f"자신감 레벨: {latest_notes.confidence_level}/10\n"
        
        if latest_strategy:
            summary += f"전체 전략: {latest_strategy.overall_strategy}\n"
            summary += f"제거 목표: {latest_strategy.elimination_target}\n"
            summary += f"위험도 평가: {latest_strategy.risk_assessment}\n"
        
        recent_summaries = self.conversation_summaries.get(player, [])[-3:]  # 최근 3개 대화
        if recent_summaries:
            summary += "최근 대화들:\n"
            for conv in recent_summaries:
                summary += f"  - {conv.conversation_partner}: {conv.strategic_outcome}\n"
        
        return summary

# 전역 전략 관리자 인스턴스
strategic_manager = StrategicManager()
