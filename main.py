#!/usr/bin/env python3
"""
Gay Bar Mexican Standoff 게임 메인 실행 파일
11개 AI 모델들이 서로 게이인 척하며 이성애자를 찾는 게임

사용법:
    python main.py

필요 조건:
    - Ollama가 설치되어 있고 실행 중이어야 함
    - 필요한 AI 모델들이 다운로드되어야 함 (자동으로 다운로드 시도)
"""

import sys
import os
import signal
import argparse
sys.path.append('src')

from src.game_engine import GameEngine
from src.models_config import MODELS, get_model_sizes, get_total_size_estimate, print_available_models, select_random_players, get_selected_players_info, update_game_config_for_players
from src.utils import FileManager

def signal_handler(sig, frame):
    """Ctrl+C 처리"""
    print("\n\n🛑 게임이 중단되었습니다.")
    sys.exit(0)

def print_banner():
    """게임 시작 배너 출력"""
    banner = """
    ╔════════════════════════════════════════════════════════════════╗
    ║                                                                ║
    ║        🏳️‍🌈  GAY BAR MEXICAN STANDOFF  🏳️‍🌈                     ║
    ║                                                                ║
    ║     11개의 AI 모델들이 펼치는 완벽한 연기 대결!                        ║
    ║     모두가 자신만이 유일한 이성애자라고 생각한다...                      ║
    ║                                                                ║
    ╚════════════════════════════════════════════════════════════════╝
    """
    print(banner)

def print_models_info(selected_players=None):
    """참가 모델 정보 출력"""
    if selected_players is None:
        # 모든 모델 출력
        print("\n🤖 사용 가능한 모든 AI 모델들:")
        models_to_show = MODELS.items()
    else:
        # 선택된 모델들만 출력
        print(f"\n🎯 선택된 {len(selected_players)}명의 AI 참가자들:")
        models_to_show = [(player, MODELS[player]) for player in selected_players if player in MODELS]
    
    print("=" * 80)
    
    for i, (fruit_name, config) in enumerate(models_to_show, 1):
        print(f"{i:2d}. {fruit_name:<12} | {config['model_name']:<25} | "
              f"{config['company']:<15} | {config['params']}")
    
    print("=" * 80)

def check_prerequisites():
    """사전 조건 확인"""
    print("\n🔍 시스템 요구사항 확인 중...")
    
    # Ollama 설치 확인
    if os.system("which ollama > /dev/null 2>&1") != 0:
        print("❌ Ollama가 설치되지 않았습니다!")
        print("다음 링크에서 Ollama를 설치하세요: https://ollama.com/")
        return False
    
    print("✅ Ollama 설치 확인됨")
    
    # Ollama 서버 실행 확인
    if os.system("curl -s http://localhost:11434/api/version > /dev/null") != 0:
        print("❌ Ollama 서버가 실행되고 있지 않습니다!")
        print("다음 명령어로 Ollama 서버를 시작하세요: ollama serve")
        return False
    
    print("✅ Ollama 서버 실행 중")
    return True
def estimate_download_size(selected_players=None):
    """필요한 모델들의 예상 다운로드 크기"""
    if selected_players is None:
        # 모든 모델 크기
        model_sizes = get_model_sizes()
        total_info = get_total_size_estimate()
        print(f"\n📋 모든 모델 다운로드 예상 크기:")
    else:
        # 선택된 모델들만
        players_info = get_selected_players_info(selected_players)
        model_sizes = {}
        for player in selected_players:
            if player in players_info['players_info']:
                config = players_info['players_info'][player]
                from models_config import calculate_model_size
                size_info = calculate_model_size(config['params'])
                model_sizes[player] = {
                    'model_name': config['model_name'],
                    'size_str': size_info['size_str']
                }
        total_info = {'total_str': players_info['total_size_str']}
        print(f"\n📋 선택된 {len(selected_players)}개 모델 다운로드 예상 크기:")
    
    for fruit_name, size_info in model_sizes.items():
        print(f"  • {fruit_name} ({size_info['model_name']}): {size_info['size_str']}")
    
    print(f"\n📦 총 예상 크기: {total_info['total_str']}")
    print("⚠️ 모델이 이미 다운로드되어 있다면 스킵됩니다.")

def main():
    """메인 함수"""
    # 명령행 인수 처리
    parser = argparse.ArgumentParser(description="Gay Bar Mexican Standoff AI 게임")
    parser.add_argument("--skip-check", action="store_true", 
                       help="사전 조건 확인 스킵")
    parser.add_argument("--log-file", default="game_log.json",
                       help="게임 로그 파일 경로 (기본값: game_log.json)")
    parser.add_argument("--quick-start", action="store_true",
                       help="빠른 시작 (안내 메시지 스킵)")
    parser.add_argument("--players", type=int, default=12,
                       help="게임 참가자 수 (기본값: 12, 최소 3명)")
    parser.add_argument("--list-models", action="store_true",
                       help="사용 가능한 모든 모델 목록 표시")
    
    args = parser.parse_args()
    
    # 모델 목록 표시 후 종료
    if args.list_models:
        print_available_models()
        return
    
    # 참가자 수 검증
    if args.players < 3:
        print("⚠️ 최소 3명이 필요합니다.")
        args.players = 3
    elif args.players > 12:
        print("⚠️ 최대 12명까지 가능합니다.")
        args.players = 12
    
    # 신호 처리 등록
    signal.signal(signal.SIGINT, signal_handler)
    
    # 플레이어 선택 및 게임 설정
    if args.players == 12:
        # 모든 플레이어 사용
        selected_players = None
    else:
        # 랜덤 선택
        selected_players = select_random_players(args.players)
        update_game_config_for_players(args.players)
    
    if not args.quick_start:
        print_banner()
        if args.players < 12:
            print(f"\n🎲 12개 모델 중에서 랜덤으로 {args.players}명 선택됨!")
        print_models_info(selected_players)
    
    # 사전 조건 확인
    if not args.skip_check:
        if not check_prerequisites():
            print("\n❌ 사전 조건이 충족되지 않았습니다. 게임을 시작할 수 없습니다.")
            sys.exit(1)
    
    if not args.quick_start:
        estimate_download_size(selected_players)
        
        # 사용자 확인
        response = input("\n계속 진행하시겠습니까? (y/N): ")
        if response.lower() not in ['y', 'yes', '예', 'ㅇ']:
            print("게임을 취소했습니다.")
            sys.exit(0)
    
    try:
        # 파일 관리자 초기화
        file_manager = FileManager()
        
        # 게임 엔진 생성 및 시작
        print(f"\n🚀 게임 엔진을 초기화하는 중...")
        game_engine = GameEngine(log_file=args.log_file, selected_players=selected_players, file_manager=file_manager)
        
        print(f"📝 게임 데이터는 체계적으로 관리됩니다.")
        
        # 게임 시작!
        game_engine.start_game()
        
        print(f"\n🎊 게임이 완료되었습니다!")
        print(f"📈 자세한 결과는 게임 디렉토리에서 확인하실 수 있습니다.")
        
    except KeyboardInterrupt:
        print("\n\n🛑 사용자가 게임을 중단했습니다.")
        sys.exit(0)
        
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류가 발생했습니다: {str(e)}")
        print("문제가 지속되면 GitHub 이슈를 등록해주세요.")
        sys.exit(1)

if __name__ == "__main__":
    main()
