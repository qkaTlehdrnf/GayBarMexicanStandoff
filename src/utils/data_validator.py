"""
데이터 검증 유틸리티
게임 데이터의 무결성과 일관성을 검증
"""

import json
from typing import Dict, List, Any, Optional, Set
from pathlib import Path


class DataValidator:
    """게임 데이터 검증을 담당하는 클래스"""
    
    def __init__(self):
        """DataValidator 초기화"""
        self.required_game_state_fields = {
            'game_id', 'start_time', 'current_round', 'active_models',
            'eliminated_players', 'game_phase'
        }
        
        self.required_round_fields = {
            'round_number', 'conversations', 'votes', 'eliminated_player'
        }
        
        self.required_conversation_fields = {
            'speaker', 'listener', 'content', 'round_number'
        }
    
    def validate_game_state(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        게임 상태 데이터 검증
        
        Args:
            game_state: 검증할 게임 상태
            
        Returns:
            검증 결과 딕셔너리 (valid, errors, warnings)
        """
        result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # 필수 필드 확인
        missing_fields = self.required_game_state_fields - set(game_state.keys())
        if missing_fields:
            result['errors'].extend([f"필수 필드 누락: {field}" for field in missing_fields])
            result['valid'] = False
        
        # 데이터 타입 검증
        if 'current_round' in game_state and not isinstance(game_state['current_round'], int):
            result['errors'].append("current_round는 정수여야 합니다")
            result['valid'] = False
        
        if 'active_models' in game_state:
            if not isinstance(game_state['active_models'], list):
                result['errors'].append("active_models는 리스트여야 합니다")
                result['valid'] = False
            elif not game_state['active_models']:
                result['warnings'].append("active_models가 비어있습니다")
        
        # 논리적 일관성 검증
        if ('current_round' in game_state and 'active_models' in game_state and 
            'eliminated_players' in game_state):
            
            expected_eliminations = game_state['current_round'] - 1
            actual_eliminations = len(game_state.get('eliminated_players', []))
            
            if expected_eliminations != actual_eliminations and game_state['current_round'] > 1:
                result['warnings'].append(
                    f"라운드 {game_state['current_round']}에서 예상 탈락자: {expected_eliminations}, "
                    f"실제 탈락자: {actual_eliminations}"
                )
        
        return result
    
    def validate_round_data(self, round_data: Dict[str, Any], round_number: int) -> Dict[str, Any]:
        """
        라운드 데이터 검증
        
        Args:
            round_data: 검증할 라운드 데이터
            round_number: 라운드 번호
            
        Returns:
            검증 결과 딕셔너리
        """
        result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # 필수 필드 확인
        missing_fields = self.required_round_fields - set(round_data.keys())
        if missing_fields:
            result['errors'].extend([f"필수 필드 누락: {field}" for field in missing_fields])
            result['valid'] = False
        
        # 라운드 번호 일치 확인
        if ('round_number' in round_data and 
            round_data['round_number'] != round_number):
            result['errors'].append(f"라운드 번호 불일치: 예상 {round_number}, 실제 {round_data['round_number']}")
            result['valid'] = False
        
        # 대화 데이터 검증
        if 'conversations' in round_data:
            conv_result = self._validate_conversations(round_data['conversations'], round_number)
            if not conv_result['valid']:
                result['valid'] = False
            result['errors'].extend(conv_result['errors'])
            result['warnings'].extend(conv_result['warnings'])
        
        # 투표 데이터 검증
        if 'votes' in round_data:
            vote_result = self._validate_votes(round_data['votes'])
            if not vote_result['valid']:
                result['valid'] = False
            result['errors'].extend(vote_result['errors'])
            result['warnings'].extend(vote_result['warnings'])
        
        return result
    
    def _validate_conversations(self, conversations: List[Dict], round_number: int) -> Dict[str, Any]:
        """대화 데이터 검증"""
        result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        if not isinstance(conversations, list):
            result['errors'].append("conversations는 리스트여야 합니다")
            result['valid'] = False
            return result
        
        speakers = set()
        listeners = set()
        
        for i, conv in enumerate(conversations):
            if not isinstance(conv, dict):
                result['errors'].append(f"대화 {i}는 딕셔너리여야 합니다")
                result['valid'] = False
                continue
            
            # 필수 필드 확인
            missing_fields = self.required_conversation_fields - set(conv.keys())
            if missing_fields:
                result['errors'].extend([f"대화 {i}에서 필수 필드 누락: {field}" for field in missing_fields])
                result['valid'] = False
            
            # 라운드 번호 확인
            if 'round_number' in conv and conv['round_number'] != round_number:
                result['errors'].append(f"대화 {i}의 라운드 번호 불일치")
                result['valid'] = False
            
            # 참가자 수집
            if 'speaker' in conv:
                speakers.add(conv['speaker'])
            if 'listener' in conv:
                listeners.add(conv['listener'])
        
        # 대화 균형 확인
        all_participants = speakers | listeners
        for participant in all_participants:
            speaker_count = sum(1 for conv in conversations if conv.get('speaker') == participant)
            listener_count = sum(1 for conv in conversations if conv.get('listener') == participant)
            
            if abs(speaker_count - listener_count) > 2:
                result['warnings'].append(f"{participant}의 대화 불균형: 발화 {speaker_count}회, 청취 {listener_count}회")
        
        return result
    
    def _validate_votes(self, votes: Dict[str, str]) -> Dict[str, Any]:
        """투표 데이터 검증"""
        result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        if not isinstance(votes, dict):
            result['errors'].append("votes는 딕셔너리여야 합니다")
            result['valid'] = False
            return result
        
        # 자기 자신에게 투표하지 않았는지 확인
        self_votes = [voter for voter, target in votes.items() if voter == target]
        if self_votes:
            result['errors'].extend([f"{voter}가 자기 자신에게 투표했습니다" for voter in self_votes])
            result['valid'] = False
        
        # 투표 대상 집계
        vote_counts = {}
        for target in votes.values():
            vote_counts[target] = vote_counts.get(target, 0) + 1
        
        # 동점 상황 확인
        max_votes = max(vote_counts.values()) if vote_counts else 0
        tied_candidates = [candidate for candidate, count in vote_counts.items() if count == max_votes]
        
        if len(tied_candidates) > 1:
            result['warnings'].append(f"동점 상황: {', '.join(tied_candidates)} ({max_votes}표)")
        
        return result
    
    def validate_strategic_data(self, strategic_data: Dict[str, Any]) -> Dict[str, Any]:
        """전략 시스템 데이터 검증"""
        result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        if not isinstance(strategic_data, dict):
            result['errors'].append("strategic_data는 딕셔너리여야 합니다")
            result['valid'] = False
            return result
        
        # 전략 계획 검증
        if 'strategic_plans' in strategic_data:
            plans = strategic_data['strategic_plans']
            if not isinstance(plans, list):
                result['errors'].append("strategic_plans는 리스트여야 합니다")
                result['valid'] = False
            else:
                for i, plan in enumerate(plans):
                    if not isinstance(plan, dict):
                        result['errors'].append(f"strategic_plan {i}는 딕셔너리여야 합니다")
                        result['valid'] = False
        
        # 개인 노트 검증
        if 'personal_notes' in strategic_data:
            notes = strategic_data['personal_notes']
            if not isinstance(notes, list):
                result['errors'].append("personal_notes는 리스트여야 합니다")
                result['valid'] = False
        
        return result
    
    def validate_file_structure(self, game_dir: Path) -> Dict[str, Any]:
        """
        게임 디렉토리 파일 구조 검증
        
        Args:
            game_dir: 게임 디렉토리 경로
            
        Returns:
            검증 결과 딕셔너리
        """
        result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        if not game_dir.exists():
            result['errors'].append(f"게임 디렉토리가 존재하지 않습니다: {game_dir}")
            result['valid'] = False
            return result
        
        # 필수 파일 확인
        required_files = ['game_state.json']
        for file_name in required_files:
            file_path = game_dir / file_name
            if not file_path.exists():
                result['errors'].append(f"필수 파일 누락: {file_name}")
                result['valid'] = False
        
        # 라운드 디렉토리 확인
        round_dirs = [d for d in game_dir.iterdir() if d.is_dir() and d.name.startswith('round_')]
        if not round_dirs:
            result['warnings'].append("라운드 디렉토리가 없습니다")
        
        # 각 라운드 디렉토리의 파일 확인
        for round_dir in round_dirs:
            round_files = ['round_data.json']
            for file_name in round_files:
                file_path = round_dir / file_name
                if not file_path.exists():
                    result['warnings'].append(f"{round_dir.name}에서 파일 누락: {file_name}")
        
        return result
    
    def repair_game_data(self, game_dir: Path) -> Dict[str, Any]:
        """
        게임 데이터 자동 복구 시도
        
        Args:
            game_dir: 게임 디렉토리 경로
            
        Returns:
            복구 결과 딕셔너리
        """
        result = {
            'repaired': False,
            'repairs': [],
            'errors': []
        }
        
        try:
            # 게임 상태 파일이 없으면 기본값 생성
            game_state_file = game_dir / 'game_state.json'
            if not game_state_file.exists():
                default_state = {
                    'game_id': game_dir.name,
                    'start_time': None,
                    'end_time': None,
                    'current_round': 1,
                    'active_models': [],
                    'eliminated_players': [],
                    'game_phase': 'ended',
                    'winner': None
                }
                
                with open(game_state_file, 'w', encoding='utf-8') as f:
                    json.dump(default_state, f, ensure_ascii=False, indent=2)
                
                result['repairs'].append("기본 게임 상태 파일 생성")
                result['repaired'] = True
            
            # 빈 라운드 디렉토리 정리
            empty_rounds = []
            for round_dir in game_dir.iterdir():
                if (round_dir.is_dir() and round_dir.name.startswith('round_') and 
                    not list(round_dir.glob('*.json'))):
                    empty_rounds.append(round_dir)
            
            for empty_round in empty_rounds:
                empty_round.rmdir()
                result['repairs'].append(f"빈 라운드 디렉토리 제거: {empty_round.name}")
                result['repaired'] = True
        
        except Exception as e:
            result['errors'].append(f"복구 중 오류: {e}")
        
        return result
    
    def generate_integrity_report(self, game_dir: Path) -> str:
        """
        게임 데이터 무결성 보고서 생성
        
        Args:
            game_dir: 게임 디렉토리 경로
            
        Returns:
            보고서 텍스트
        """
        report_lines = [f"=== 게임 데이터 무결성 보고서: {game_dir.name} ===\n"]
        
        # 파일 구조 검증
        structure_result = self.validate_file_structure(game_dir)
        report_lines.append("📁 파일 구조 검사:")
        if structure_result['valid']:
            report_lines.append("  ✅ 파일 구조 정상")
        else:
            report_lines.append("  ❌ 파일 구조 문제 발견")
            for error in structure_result['errors']:
                report_lines.append(f"    - {error}")
        
        for warning in structure_result['warnings']:
            report_lines.append(f"    ⚠️ {warning}")
        
        report_lines.append("")
        
        # 게임 상태 검증
        game_state_file = game_dir / 'game_state.json'
        if game_state_file.exists():
            try:
                with open(game_state_file, 'r', encoding='utf-8') as f:
                    game_state = json.load(f)
                
                state_result = self.validate_game_state(game_state)
                report_lines.append("🎮 게임 상태 검사:")
                if state_result['valid']:
                    report_lines.append("  ✅ 게임 상태 정상")
                else:
                    report_lines.append("  ❌ 게임 상태 문제 발견")
                    for error in state_result['errors']:
                        report_lines.append(f"    - {error}")
                
                for warning in state_result['warnings']:
                    report_lines.append(f"    ⚠️ {warning}")
                
            except Exception as e:
                report_lines.append(f"  ❌ 게임 상태 파일 읽기 실패: {e}")
        
        report_lines.append("")
        
        # 라운드별 데이터 검증
        round_dirs = sorted([d for d in game_dir.iterdir() 
                           if d.is_dir() and d.name.startswith('round_')])
        
        if round_dirs:
            report_lines.append("🔄 라운드 데이터 검사:")
            for round_dir in round_dirs:
                round_num = int(round_dir.name.split('_')[1])
                round_file = round_dir / 'round_data.json'
                
                if round_file.exists():
                    try:
                        with open(round_file, 'r', encoding='utf-8') as f:
                            round_data = json.load(f)
                        
                        round_result = self.validate_round_data(round_data, round_num)
                        if round_result['valid']:
                            report_lines.append(f"  ✅ 라운드 {round_num}: 정상")
                        else:
                            report_lines.append(f"  ❌ 라운드 {round_num}: 문제 발견")
                            for error in round_result['errors'][:3]:  # 최대 3개만 표시
                                report_lines.append(f"      - {error}")
                    
                    except Exception as e:
                        report_lines.append(f"  ❌ 라운드 {round_num}: 파일 읽기 실패")
                else:
                    report_lines.append(f"  ⚠️ 라운드 {round_num}: 데이터 파일 없음")
        
        return "\n".join(report_lines)


