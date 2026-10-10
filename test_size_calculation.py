#!/usr/bin/env python3
"""
모델 크기 계산 함수들을 테스트하는 스크립트
"""

from models_config import (
    MODELS, 
    calculate_model_size, 
    get_model_sizes, 
    get_total_size_estimate,
    print_current_mapping
)

def test_calculate_model_size():
    """개별 모델 크기 계산 테스트"""
    print("🧪 calculate_model_size() 함수 테스트:")
    test_params = ["72B", "70B", "67B", "53B", "47B", "40B", "35B", "34B", "33B", "99B"]
    
    for param in test_params:
        result = calculate_model_size(param)
        print(f"  • {param}: {result}")
    print()

def test_get_model_sizes():
    """전체 모델 크기 정보 테스트"""
    print("🧪 get_model_sizes() 함수 테스트:")
    model_sizes = get_model_sizes()
    
    for fruit_name, size_info in model_sizes.items():
        print(f"  • {fruit_name:>12}: {size_info['model_name']:<20} | "
              f"{size_info['params']:>4} | {size_info['size_str']:>6}")
    print()

def test_get_total_size_estimate():
    """총 크기 계산 테스트"""
    print("🧪 get_total_size_estimate() 함수 테스트:")
    total_info = get_total_size_estimate()
    print(f"  • 총 크기(GB): {total_info['total_gb']}")
    print(f"  • 총 크기(문자열): {total_info['total_str']}")
    print()

def test_estimate_download_size():
    """main.py의 estimate_download_size() 함수 테스트"""
    print("🧪 main.py의 estimate_download_size() 함수 테스트:")
    
    # main.py에서 함수를 import해서 실행
    try:
        from main import estimate_download_size
        estimate_download_size()
    except ImportError as e:
        print(f"❌ Import 오류: {e}")
    except Exception as e:
        print(f"❌ 실행 오류: {e}")
    print()

def main():
    """메인 테스트 함수"""
    print("=" * 80)
    print("🚀 모델 크기 계산 함수 테스트 시작")
    print("=" * 80)
    
    # 현재 모델 매핑 출력
    print_current_mapping()
    print()
    
    # 각 함수별 테스트
    test_calculate_model_size()
    test_get_model_sizes()  
    test_get_total_size_estimate()
    test_estimate_download_size()
    
    print("=" * 80)
    print("✅ 모든 테스트 완료!")
    print("=" * 80)

if __name__ == "__main__":
    main()

