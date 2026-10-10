"""
파일 관리 유틸리티
게임 데이터의 저장, 로딩, 폴더 관리를 담당
"""

import os
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional


class FileManager:
    """게임 데이터의 파일 시스템 관리를 담당하는 클래스"""
    
    def __init__(self, base_data_dir: str = "data"):
        """
        Args:
            base_data_dir: 데이터를 저장할 기본 디렉토리
        """
        self.base_data_dir = Path(base_data_dir)
        self.games_dir = self.base_data_dir / "games"
        self._ensure_directories()
    
    def _ensure_directories(self):
        """필요한 디렉토리들이 존재하는지 확인하고 생성"""
        self.base_data_dir.mkdir(exist_ok=True)
        self.games_dir.mkdir(exist_ok=True)
    
    def create_game_directory(self, game_id: Optional[str] = None) -> Path:
        """
        새 게임을 위한 디렉토리 생성
        
        Args:
            game_id: 게임 ID (없으면 타임스탬프로 자동 생성)
            
        Returns:
            생성된 게임 디렉토리 경로
        """
        if game_id is None:
            game_id = f"game_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        game_dir = self.games_dir / game_id
        game_dir.mkdir(exist_ok=True)
        
        # 라운드별 디렉토리 미리 생성 (최대 20라운드까지)
        for round_num in range(1, 21):
            round_dir = game_dir / f"round_{round_num}"
            round_dir.mkdir(exist_ok=True)
        
        return game_dir
    
    def save_round_data(self, game_dir: Path, round_num: int, data: Dict[str, Any]):
        """
        라운드별 데이터 저장
        
        Args:
            game_dir: 게임 디렉토리 경로
            round_num: 라운드 번호
            data: 저장할 데이터
        """
        round_dir = game_dir / f"round_{round_num}"
        round_dir.mkdir(exist_ok=True)
        
        # 라운드 데이터 저장
        round_file = round_dir / "round_data.json"
        self._save_json(round_file, data)
        
        # 대화 데이터가 있으면 따로 저장
        if 'conversations' in data:
            conversations_file = round_dir / "conversations.json"
            self._save_json(conversations_file, data['conversations'])
        
        # 투표 데이터가 있으면 따로 저장
        if 'votes' in data:
            votes_file = round_dir / "votes.json"
            self._save_json(votes_file, data['votes'])
        
        # 전략 데이터가 있으면 따로 저장
        if 'strategic_plans' in data:
            strategic_file = round_dir / "strategic_plans.json"
            self._save_json(strategic_file, data['strategic_plans'])
    
    def save_game_state(self, game_dir: Path, game_state: Dict[str, Any]):
        """
        게임 상태 저장
        
        Args:
            game_dir: 게임 디렉토리 경로
            game_state: 게임 상태 데이터
        """
        game_state_file = game_dir / "game_state.json"
        self._save_json(game_state_file, game_state)
    
    def save_strategic_data(self, game_dir: Path, strategic_data: Dict[str, Any]):
        """
        전략 시스템 데이터 저장
        
        Args:
            game_dir: 게임 디렉토리 경로
            strategic_data: 전략 데이터
        """
        strategic_file = game_dir / "strategic_data.json"
        self._save_json(strategic_file, strategic_data)
    
    def load_game_state(self, game_dir: Path) -> Optional[Dict[str, Any]]:
        """
        게임 상태 로딩
        
        Args:
            game_dir: 게임 디렉토리 경로
            
        Returns:
            게임 상태 데이터 또는 None
        """
        game_state_file = game_dir / "game_state.json"
        return self._load_json(game_state_file)
    
    def load_round_data(self, game_dir: Path, round_num: int) -> Optional[Dict[str, Any]]:
        """
        라운드 데이터 로딩
        
        Args:
            game_dir: 게임 디렉토리 경로
            round_num: 라운드 번호
            
        Returns:
            라운드 데이터 또는 None
        """
        round_dir = game_dir / f"round_{round_num}"
        round_file = round_dir / "round_data.json"
        return self._load_json(round_file)
    
    def get_latest_game_dir(self) -> Optional[Path]:
        """
        가장 최근 게임 디렉토리 반환
        
        Returns:
            최신 게임 디렉토리 경로 또는 None
        """
        if not self.games_dir.exists():
            return None
        
        game_dirs = [d for d in self.games_dir.iterdir() if d.is_dir()]
        if not game_dirs:
            return None
        
        # 디렉토리명으로 정렬하여 최신 반환
        game_dirs.sort(key=lambda x: x.name, reverse=True)
        return game_dirs[0]
    
    def list_games(self) -> List[str]:
        """
        모든 게임 목록 반환
        
        Returns:
            게임 ID 목록
        """
        if not self.games_dir.exists():
            return []
        
        game_dirs = [d.name for d in self.games_dir.iterdir() if d.is_dir()]
        return sorted(game_dirs, reverse=True)
    
    def cleanup_old_games(self, keep_count: int = 10):
        """
        오래된 게임 디렉토리 정리
        
        Args:
            keep_count: 보관할 게임 수
        """
        games = self.list_games()
        if len(games) <= keep_count:
            return
        
        games_to_delete = games[keep_count:]
        for game_id in games_to_delete:
            game_dir = self.games_dir / game_id
            if game_dir.exists():
                shutil.rmtree(game_dir)
                print(f"정리완료: {game_id}")
    
    def _save_json(self, file_path: Path, data: Dict[str, Any]):
        """JSON 파일 저장 헬퍼 메서드"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            print(f"JSON 저장 실패 {file_path}: {e}")
    
    def _load_json(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """JSON 파일 로딩 헬퍼 메서드"""
        try:
            if not file_path.exists():
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"JSON 로딩 실패 {file_path}: {e}")
            return None
    
    def export_game_summary(self, game_dir: Path) -> Dict[str, Any]:
        """
        게임 요약 정보 생성
        
        Args:
            game_dir: 게임 디렉토리 경로
            
        Returns:
            게임 요약 정보
        """
        game_state = self.load_game_state(game_dir)
        if not game_state:
            return {}
        
        summary = {
            "game_id": game_dir.name,
            "start_time": game_state.get("start_time"),
            "end_time": game_state.get("end_time"),
            "total_rounds": game_state.get("current_round", 0),
            "participants": game_state.get("initial_models", []),
            "winner": game_state.get("winner"),
            "eliminated_order": game_state.get("eliminated_players", [])
        }
        
        return summary


