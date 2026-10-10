#!/usr/bin/env python3
"""
Gay Bar Mexican Standoff 데모 모드
실제 AI 모델 없이도 게임 플로우를 확인할 수 있는 시뮬레이션 모드
"""

import time
import random
import json
from datetime import datetime
from itertools import combinations
from dataclasses import dataclass, asdict
from typing import Dict, List, Any
import sys
sys.path.append('src')

from src.models_config import MODELS, get_model_names
from src.utils import FileManager

@dataclass
class DemoRoundLog:
    """데모 라운드별 로그"""
    round_number: int
    participants: List[str]
    total_conversations: int
    conversations: List[Dict[str, Any]]
    eliminated_player: str = None

@dataclass
class DemoGameLog:
    """데모 전체 게임 로그"""
    game_id: str
    start_time: str
    total_conversations: int
    rounds: List[DemoRoundLog]
    winners: List[str] = None
    elimination_order: List[str] = None
    end_time: str = None

class DemoGameEngine:
    """데모용 게임 엔진 - 실제 AI 없이 시뮬레이션"""
    
    def __init__(self):
        self.active_models = get_model_names()
        self.eliminated_models = []
        self.current_round = 1
        self.initial_player_count = len(self.active_models)  # 초기 플레이어 수 저장
        # 각 플레이어의 대화 이력과 인상 저장
        self.conversation_history = {}  # {player: [conversations]}
        self.player_impressions = {}    # {observer: {target: [impressions]}}
        self.detailed_conversations = {}  # {(player1, player2): [full_conversation_contents]}
        
        # 게임 로그 초기화
        game_id = f"demo_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.game_log = DemoGameLog(
            game_id=game_id,
            start_time=datetime.now().isoformat(),
            total_conversations=0,
            rounds=[],
            elimination_order=[]
        )
        
    def start_demo(self):
        """데모 시작"""
        print("🎪 Gay Bar Mexican Standoff - 데모 모드")
        print("실제 AI 모델 없이 게임 플로우를 시연합니다.\n")
        
        print(f"🍎 참가자: {', '.join(self.active_models)}")
        print("모든 참가자들은 자신만이 유일한 이성애자라고 생각합니다...\n")
        
        while len(self.active_models) > 2:
            self._run_demo_round()
            
        # 2명이 남으면 게임 종료 (둘 다 승리자)
        if len(self.active_models) == 2:
            winners = " & ".join(self.active_models)
            print(f"\n🎊 게임 종료! 공동 승리자: {winners}")
            print("마지막 2명이 남았으므로 둘 다 승리자입니다!")
        else:
            winner = self.active_models[0] if self.active_models else "없음"
            print(f"\n🎊 게임 종료! 승자: {winner}")
        print(f"탈락 순서: {' → '.join(reversed(self.eliminated_models))}")
        
    def _run_demo_round(self):
        """데모 라운드 실행"""
        print(f"\n{'='*50}")
        print(f"🎭 라운드 {self.current_round}")
        print(f"생존자: {', '.join(self.active_models)} ({len(self.active_models)}명)")
        print(f"{'='*50}")
        
        # 대화 시뮬레이션
        pairs = list(combinations(self.active_models, 2))
        
        print(f"💬 {len(pairs)}개의 대화 진행 중...")
        
        # 라운드 로그 생성
        round_log = DemoRoundLog(
            round_number=self.current_round,
            participants=self.active_models.copy(),
            total_conversations=len(pairs),
            conversations=[],
            eliminated_player=None
        )
        
        # 모든 대화를 실제로 진행하되, 표시 방식을 조정
        for i, (model1, model2) in enumerate(pairs):
            # 처음 3개, 중간 1개, 마지막 3개만 상세 표시
            show_detailed = (i < 3) or (i == len(pairs)//2) or (i >= len(pairs) - 3)
            
            # 대화 로그 생성
            conversation_log = {
                "id": i + 1,
                "participants": [model1, model2],
                "turns": [],
                "action": None,
                "impressions": {}
            }
            
            if True:
                print(f"\n  대화 {i+1}/{len(pairs)}: {model1} ↔ {model2}")
                conversation = self._generate_contextual_conversation(model1, model2)
                
                # 대화 턴을 로그에 추가
                for turn, conv in enumerate(conversation):
                    print(f"    {conv}")
                    conversation_log["turns"].append(conv)
                    
                # 액션 시뮬레이션 (3라운드부터)
                if self.current_round >= 3:
                    action_result = self._simulate_action(model1, model2)
                    conversation_log["action"] = action_result
                
                # 인상 정리
                impressions = self._record_impressions(model1, model2)
                conversation_log["impressions"] = impressions
                time.sleep(0.1)
            else:
                # 대화는 진행하되 화면에는 간단히 표시
                conversation, action_result, impressions = self._simulate_conversation_silently(model1, model2)
                conversation_log["turns"] = conversation
                conversation_log["action"] = action_result
                conversation_log["impressions"] = impressions
                
                if i == 5 and len(pairs) > 10:
                    print(f"  ⏳ 대화 진행 중... ({len(pairs) - 6}개 남음)")
            
            # 대화 로그를 라운드 로그에 추가
            round_log.conversations.append(conversation_log)
            
            # 모든 대화에서 인상과 이력 업데이트 (대화 내용 포함)
            conversation_content = conversation_log["turns"] if "turns" in conversation_log else []
            self._update_conversation_history(model1, model2, conversation_content)
        
        # 라운드 로그 완성 및 게임 로그에 추가
        self.game_log.rounds.append(round_log)
        self.game_log.total_conversations += len(pairs)
        
        print(f"\n✅ 모든 {len(pairs)}개 대화 완료!")
        time.sleep(0.5)
        
        # 라운드별 의심도 요약 표시
        print(f"\n🧐 각 플레이어의 현재 의심 상황 (시뮬레이션):")
        for model in self.active_models[:5]:  # 처음 5명만 표시
            avg_suspicion = random.uniform(3, 8)
            most_suspicious = random.choice([m for m in self.active_models if m != model])
            suspicion_level = random.randint(4, 9)
            print(f"  {model}: 평균 의심도 {avg_suspicion:.1f}, 가장 의심스러운 대상 {most_suspicious} ({suspicion_level}/10)")
        if len(self.active_models) > 5:
            print(f"  ... (나머지 {len(self.active_models)-5}명 생략)")
        
        # 투표 시뮬레이션
        print(f"\n🗳️ 투표 진행 중...")
        votes = {}
        
        for voter in self.active_models:
            candidates = [m for m in self.active_models if m != voter]
            voted_for = random.choice(candidates)
            votes[voted_for] = votes.get(voted_for, 0) + 1
            
            reasons = [
                "너무 과하게 연기하는 것 같아",
                "대화가 부자연스러워",
                "게이 문화에 대해 잘 모르는 것 같아",
                "액션에 대한 반응이 어색해",
                "뭔가 숨기는 게 있는 것 같아"
            ]
            reason = random.choice(reasons)
            print(f"  {voter} → {voted_for} ({reason})")
            
        # 탈락자 결정
        eliminated = max(votes.keys(), key=lambda x: votes[x])
        
        print(f"\n📊 투표 결과:")
        for model, count in sorted(votes.items(), key=lambda x: x[1], reverse=True):
            status = "💀 탈락" if model == eliminated else ""
            print(f"  {model}: {count}표 {status}")
            
        self.active_models.remove(eliminated)
        self.eliminated_models.append(eliminated)
        self.game_log.elimination_order.append(eliminated)
        
        # 현재 라운드 로그에 탈락자 기록
        if self.game_log.rounds:
            self.game_log.rounds[-1].eliminated_player = eliminated
        
        print(f"\n🚪 {eliminated}가 탈락했습니다!")
        self.current_round += 1
        time.sleep(2)
    
    def _generate_contextual_conversation(self, model1: str, model2: str):
        """이전 대화 이력을 바탕으로 맥락적인 대화 생성"""
        # 이전에 대화한 적이 있는지 확인
        previous_conversations = self._get_previous_conversations(model1, model2)
        impressions = self._get_mutual_impressions(model1, model2)
        
        # 이전 대화 내용 전체 가져오기
        previous_full_conversations = self._get_previous_conversation_content(model1, model2)
        
        # 기본 대화 패턴들 - 훨씬 더 다양하게
        conversation_templates = [
            # 첫 만남 느낌
            [
                f"{model1}: 안녕! 처음 보는 것 같은데",
                f"{model2}: 맞아, 나도 그런 것 같아. 반가워!",
                f"{model1}: 여기 분위기 정말 좋다, 자주 와?",
                f"{model2}: 가끔 와. 너는 어떻게 알게 됐어?"
            ],
            # 재회 느낌
            [
                f"{model1}: 어? 저번에도 봤던 것 같은데!",
                f"{model2}: 맞아! 기억나. 그때 얘기 재밌었어",
                f"{model1}: 그러게! 오늘도 즐겁게 보내자",
                f"{model2}: 좋아, 뭔가 특별한 계획 있어?"
            ],
            # 관찰적 대화
            [
                f"{model1}: 오늘 사람들 패션이 다들 멋지네",
                f"{model2}: 그러게, 너도 옷 정말 잘 입었어",
                f"{model1}: 고마워! 너도 센스 좋은데?",
                f"{model2}: 헤헤, 오늘 특별히 신경 썼거든"
            ],
            # 음악/분위기 관련
            [
                f"{model1}: 이 노래 너무 좋다! 뭔지 알아?",
                f"{model2}: 응, 요즘 인기 있는 곡이야. 나도 좋아해",
                f"{model1}: 역시 취향이 비슷하네",
                f"{model2}: 그런 것 같아, 다른 음악도 들어볼까?"
            ],
            # 관심사 탐색
            [
                f"{model1}: 평소에 뭐 하는 걸 좋아해?",
                f"{model2}: 음... 영화 보는 거? 너는?",
                f"{model1}: 나도 영화 좋아해! 최근에 뭐 봤어?",
                f"{model2}: 로맨스 영화 하나 봤는데 정말 감동적이었어"
            ],
            # 호기심 표현
            [
                f"{model1}: 너 정말 매력적이구나",
                f"{model2}: 고마워, 너도 정말 멋있어",
                f"{model1}: 오늘 만나서 정말 좋다",
                f"{model2}: 나도! 더 얘기하고 싶어"
            ]
        ]
        
        # 맥락에 따라 대화 선택
        if previous_conversations > 1:
            # 이미 여러 번 대화한 경우 - 더 친밀한 대화
            preferred_templates = conversation_templates[1:3] + conversation_templates[-2:]
            
            # 이전 대화 내용을 참고하여 대화 생성
            if previous_full_conversations:
                print(f"    💭 {model1} ↔ {model2} 이전 대화 이력:")
                for i, prev_conv in enumerate(previous_full_conversations[-2:], 1):  # 최근 2개만 표시
                    print(f"      라운드 {prev_conv['round']}: {len(prev_conv['content'])}턴 대화")
                    for turn in prev_conv['content'][:2]:  # 처음 2턴만 표시
                        print(f"        {turn}")
                    if len(prev_conv['content']) > 2:
                        print(f"        ... 총 {len(prev_conv['content'])}턴")
            
        elif any(imp[1] > 7 for imp in impressions.values()):
            # 상대방을 의심하고 있는 경우 - 탐색적 대화
            preferred_templates = conversation_templates[2:5]
        else:
            # 일반적인 경우
            preferred_templates = conversation_templates
            
        return random.choice(preferred_templates)
    
    def _simulate_action(self, model1: str, model2: str) -> Dict:
        """액션 시뮬레이션"""
        actions = [
            "함께 음료 마시기", "하이파이브 하기", "개인적인 질문하기",
            "칭찬하기", "함께 춤추기", "사진 찍기", "연락처 교환하기"
        ]
        
        # 랜덤하게 액션 제안 (30% 확률)
        if random.random() < 0.3:
            action = random.choice(actions)
            print(f"    {model1}: <Action>{action}</Action>")
            
            # 이전 인상에 따라 수락/거부 확률 조정
            impressions = self._get_mutual_impressions(model1, model2)
            base_accept_rate = 0.6
            
            if model2 in impressions and impressions[model2][1] > 7:
                accept_rate = 0.3  # 의심스러우면 거부 확률 높음
            else:
                accept_rate = base_accept_rate
                
            if random.random() < accept_rate:
                print(f"    {model2}: <Action>{action}</Action>")
                print(f"    🎯 액션 성공: {action}")
                return {
                    "proposed": True,
                    "proposer": model1,
                    "target": model2,
                    "action": action,
                    "response": "accept"
                }
            else:
                print(f"    {model2}: 음... 미안, 다음에 하자")
                print(f"    🎯 액션 거부: {action}")
                return {
                    "proposed": True,
                    "proposer": model1,
                    "target": model2,
                    "action": action,
                    "response": "decline"
                }
        
        return None
    
    def _record_impressions(self, model1: str, model2: str) -> Dict:
        """인상 기록"""
        impressions = [
            "자연스러운 대화였다", "뭔가 어색한 부분이 있었다", 
            "너무 과하게 연기하는 것 같다", "게이 문화에 대해 잘 모르는 것 같다",
            "평범한 대화였다", "정말 매력적인 사람인 것 같다",
            "조금 수상한 구석이 있다", "진짜 게이인 것 같다"
        ]
        
        # 이전 인상을 바탕으로 새로운 인상 조정
        prev_impressions = self._get_mutual_impressions(model1, model2)
        
        for observer, target in [(model1, model2), (model2, model1)]:
            if target in prev_impressions:
                # 이전 의심도에 따라 새로운 의심도 조정
                prev_suspicion = prev_impressions[target][1]
                if prev_suspicion > 7:
                    new_suspicion = random.randint(6, 10)
                elif prev_suspicion < 4:
                    new_suspicion = random.randint(1, 5)
                else:
                    new_suspicion = random.randint(prev_suspicion-2, prev_suspicion+3)
                new_suspicion = max(1, min(10, new_suspicion))
            else:
                new_suspicion = random.randint(1, 10)
            
            impression = random.choice(impressions)
            
            # 인상 저장
            if observer not in self.player_impressions:
                self.player_impressions[observer] = {}
            if target not in self.player_impressions[observer]:
                self.player_impressions[observer][target] = []
            
            self.player_impressions[observer][target].append((impression, new_suspicion))
        
        # 최근 인상만 표시
        latest_imp1 = self.player_impressions[model1][model2][-1]
        latest_imp2 = self.player_impressions[model2][model1][-1]
        
        print(f"    💭 인상 정리:")
        print(f"      {model1} → {model2}: {latest_imp1[0]} (의심도: {latest_imp1[1]}/10)")
        print(f"      {model2} → {model1}: {latest_imp2[0]} (의심도: {latest_imp2[1]}/10)")
        
        return {
            f"{model1}_about_{model2}": {"impression": latest_imp1[0], "suspicion": latest_imp1[1]},
            f"{model2}_about_{model1}": {"impression": latest_imp2[0], "suspicion": latest_imp2[1]}
        }
    
    def _simulate_conversation_silently(self, model1: str, model2: str) -> tuple:
        """화면에 표시하지 않고 대화 시뮬레이션 (인상만 기록)"""
        # 간단한 대화 생성
        conversation = [
            f"{model1}: 안녕하세요",
            f"{model2}: 반갑습니다",
            f"{model1}: 좋은 시간 보내세요",
            f"{model2}: 감사합니다"
        ]
        
        # 액션 시뮬레이션
        action_result = None
        if self.current_round >= 3 and random.random() < 0.2:
            actions = ["함께 음료 마시기", "하이파이브 하기", "개인적인 질문하기"]
            action = random.choice(actions)
            response = "accept" if random.random() < 0.5 else "decline"
            action_result = {
                "proposed": True,
                "proposer": model1,
                "target": model2,
                "action": action,
                "response": response
            }
        
        # 인상 기록 (표시하지 않음)
        impressions = {}
        for observer, target in [(model1, model2), (model2, model1)]:
            if observer not in self.player_impressions:
                self.player_impressions[observer] = {}
            if target not in self.player_impressions[observer]:
                self.player_impressions[observer][target] = []
            
            suspicion = random.randint(1, 10)
            impression_text = random.choice(["보통", "의심스러움", "자연스러움"])
            self.player_impressions[observer][target].append((impression_text, suspicion))
            
            impressions[f"{observer}_about_{target}"] = {
                "impression": impression_text, 
                "suspicion": suspicion
            }
            
        return conversation, action_result, impressions
    
    def _update_conversation_history(self, model1: str, model2: str, conversation_content: list = None):
        """대화 이력 업데이트"""
        for model in [model1, model2]:
            if model not in self.conversation_history:
                self.conversation_history[model] = []
            other = model2 if model == model1 else model1
            self.conversation_history[model].append(f"R{self.current_round}:{other}")
        
        # 상세 대화 내용 저장 (정렬된 키로 저장)
        if conversation_content:
            key = tuple(sorted([model1, model2]))
            if key not in self.detailed_conversations:
                self.detailed_conversations[key] = []
            
            self.detailed_conversations[key].append({
                'round': self.current_round,
                'content': conversation_content.copy()
            })
    
    def _get_previous_conversations(self, model1: str, model2: str) -> int:
        """두 모델 간의 이전 대화 횟수"""
        count = 0
        if model1 in self.conversation_history:
            count += len([h for h in self.conversation_history[model1] if model2 in h])
        return count
    
    def _get_previous_conversation_content(self, model1: str, model2: str) -> list:
        """두 모델 간의 이전 대화 내용 전체 반환"""
        key = tuple(sorted([model1, model2]))
        return self.detailed_conversations.get(key, [])
    
    def _get_mutual_impressions(self, model1: str, model2: str) -> dict:
        """상호 인상 조회"""
        impressions = {}
        if model1 in self.player_impressions and model2 in self.player_impressions[model1]:
            impressions[model2] = self.player_impressions[model1][model2][-1]
        if model2 in self.player_impressions and model1 in self.player_impressions[model2]:
            impressions[model1] = self.player_impressions[model2][model1][-1]
        return impressions

    def _finalize_game_log(self):
        """게임 로그 완성 및 저장"""
        self.game_log.winners = self.active_models.copy()
        self.game_log.end_time = datetime.now().isoformat()
        
        # JSON 파일로 저장
        filename = f"demo_log_{self.game_log.game_id}.json"
        
        try:
            game_log_dict = asdict(self.game_log)
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(game_log_dict, f, ensure_ascii=False, indent=2)
            
            print(f"\n📊 데모 로그가 저장되었습니다: {filename}")
            
            # 대화 검증
            self._verify_demo_conversations()
            
            # 통계 출력
            self._print_demo_statistics()
            
        except Exception as e:
            print(f"❌ 데모 로그 저장 실패: {e}")

    def _verify_demo_conversations(self):
        """데모 대화 진행 검증"""
        print(f"\n🔍 데모 대화 진행 검증:")
        
        participant_count = self.initial_player_count  # 실제 시작 플레이어 수
        total_expected = 0
        
        for round_num in range(1, len(self.game_log.rounds) + 1):
            expected_count = participant_count * (participant_count - 1) // 2
            total_expected += expected_count
            
            if round_num <= len(self.game_log.rounds):
                actual = self.game_log.rounds[round_num - 1].total_conversations
                status = "✅" if actual == expected_count else "❌"
                print(f"   R{round_num}: {participant_count}명 → 예상 {expected_count}회 vs 실제 {actual}회 {status}")
            
            participant_count -= 1  # 매 라운드마다 1명씩 탈락
        
        # 전체 통계
        total_actual = self.game_log.total_conversations
        
        print(f"\n   📊 전체: 예상 {total_expected}회 vs 실제 {total_actual}회")
        if total_actual == total_expected:
            print("   🎉 모든 대화가 정확히 진행되었습니다!")
        else:
            print(f"   ⚠️ {abs(total_actual - total_expected)}회 차이가 있습니다.")

    def _print_demo_statistics(self):
        """데모 통계 출력"""
        print(f"\n📈 데모 게임 통계:")
        
        total_conversations = self.game_log.total_conversations
        total_rounds = len(self.game_log.rounds)
        
        print(f"   🎮 게임 ID: {self.game_log.game_id}")
        print(f"   ⏱️ 시작: {self.game_log.start_time}")
        print(f"   ⏱️ 종료: {self.game_log.end_time}")
        print(f"   💬 총 대화 수: {total_conversations}회")
        print(f"   🎭 총 라운드 수: {total_rounds}라운드")
        print(f"   🏆 승리자: {', '.join(self.game_log.winners)}")
        
        # 라운드별 통계
        print(f"\n📋 라운드별 상세 통계:")
        for round_log in self.game_log.rounds:
            actions_count = len([conv for conv in round_log.conversations if conv.get('action')])
            print(f"   R{round_log.round_number}: {round_log.total_conversations}회 대화 ({actions_count}회 액션), {round_log.eliminated_player} 탈락")
        
        # 탈락 순서
        if self.game_log.elimination_order:
            print(f"\n🚪 탈락 순서: {' → '.join(self.game_log.elimination_order)}")

def main():
    """데모 실행"""
    demo = DemoGameEngine()
    
    try:
        demo.start_demo()
        print(f"\n✨ 데모가 완료되었습니다!")
        print(f"실제 게임을 실행하려면: python main.py")
        
        # 게임 완료 후 로그 저장
        demo._finalize_game_log()
        
    except KeyboardInterrupt:
        print("\n\n🛑 데모가 중단되었습니다.")

if __name__ == "__main__":
    main()
