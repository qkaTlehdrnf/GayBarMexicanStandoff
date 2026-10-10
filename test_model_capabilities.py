#!/usr/bin/env python3
"""
Ollama 모델 능력 테스트 스크립트
각 설치된 모델의 Inference 및 데이터 분석 능력을 개별 테스트
"""

import sys
import json
import time
import requests
from datetime import datetime
from typing import Dict, List, Any, Optional

sys.path.append('src')
from src.utils.model_manager import ModelManager
from src.utils.file_manager import FileManager

class ModelTester:
    """각 모델의 능력을 테스트하는 클래스"""
    
    def __init__(self):
        self.model_manager = ModelManager()
        self.file_manager = FileManager()
        self.ollama_base_url = "http://localhost:11434"
        self.test_results = {}
        
        # 테스트 케이스들
        self.test_cases = {
            "basic_inference": {
                "question": "다음 문장을 한국어로 번역해주세요: 'The quick brown fox jumps over the lazy dog.'",
                "expected_type": "translation",
                "timeout": 30
            },
            "math_problem": {
                "question": "다음 수학 문제를 단계별로 풀어주세요: 만약 사과 5개의 가격이 3000원이라면, 사과 13개의 가격은 얼마입니까?",
                "expected_type": "mathematical_reasoning",
                "timeout": 30
            },
            "data_analysis": {
                "question": """다음 데이터를 분석해주세요:
                매장별 월별 매출 데이터:
                A매장: 1월(100만원), 2월(120만원), 3월(95만원), 4월(150만원)
                B매장: 1월(80만원), 2월(90만원), 3월(110만원), 4월(130만원)
                
                1) 각 매장의 평균 매출은?
                2) 어느 매장이 성장률이 더 높은지 분석해주세요.
                3) 4월 기준으로 어느 매장이 더 우수한지 판단해주세요.""",
                "expected_type": "data_analysis",
                "timeout": 45
            },
            "coding_problem": {
                "question": "Python으로 피보나치 수열의 n번째 항을 구하는 함수를 작성해주세요. 재귀방식과 반복문 방식 두 가지 모두 제공해주세요.",
                "expected_type": "programming",
                "timeout": 30
            },
            "reasoning_test": {
                "question": """<think>논리적 사고 과정을 여기에 작성</think>
                
                다음 논리 퍼즐을 풀어주세요:
                - 빨간 집에는 영국인이 살고 있다
                - 스페인인은 개를 기른다
                - 커피는 녹색 집에서 마신다
                - 우크라이나인은 차를 마신다
                - 녹색 집은 흰색 집의 바로 오른쪽에 있다
                
                질문: 노르웨이인은 어느 집에 살고 있을까요? (단계별 추론 과정을 보여주세요)""",
                "expected_type": "logical_reasoning",
                "timeout": 60
            }
        }
    
    def test_ollama_connection(self) -> bool:
        """Ollama 서버 연결 테스트"""
        try:
            response = requests.get(f"{self.ollama_base_url}/api/tags", timeout=10)
            return response.status_code == 200
        except:
            return False
    
    def generate_response(self, model_name: str, prompt: str, timeout: int = 30) -> Dict[str, Any]:
        """단일 모델에서 응답 생성"""
        try:
            start_time = time.time()
            
            response = requests.post(
                f"{self.ollama_base_url}/api/generate",
                json={
                    "model": model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "max_tokens": 500
                    }
                },
                timeout=timeout
            )
            
            end_time = time.time()
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "response": result.get("response", "").strip(),
                    "response_time": end_time - start_time,
                    "model": model_name,
                    "error": None
                }
            else:
                return {
                    "success": False,
                    "response": "",
                    "response_time": end_time - start_time,
                    "model": model_name,
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
                
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "response": "",
                "response_time": timeout,
                "model": model_name,
                "error": "Timeout"
            }
        except Exception as e:
            return {
                "success": False,
                "response": "",
                "response_time": 0,
                "model": model_name,
                "error": str(e)
            }
    
    def evaluate_response(self, response: str, test_type: str) -> Dict[str, Any]:
        """응답 품질 평가"""
        evaluation = {
            "length": len(response),
            "has_korean": bool('가' <= response <= '힣' or '가' in response),
            "has_numbers": any(c.isdigit() for c in response),
            "has_code": "```" in response or "def " in response or "function" in response,
            "has_reasoning": "<think>" in response or "단계" in response or "과정" in response,
            "coherent": len(response) > 50,  # 기본적인 길이 체크
        }
        
        # 테스트 타입별 특화 평가
        if test_type == "mathematical_reasoning":
            evaluation["has_calculation"] = any(op in response for op in ['+', '-', '*', '/', '='])
            evaluation["has_steps"] = "단계" in response or ":" in response
            
        elif test_type == "data_analysis":
            evaluation["has_analysis"] = any(keyword in response for keyword in ["평균", "분석", "비교", "성장률"])
            evaluation["answers_questions"] = response.count("1)") >= 1 or response.count("2)") >= 1
            
        elif test_type == "programming":
            evaluation["has_function"] = "def " in response
            evaluation["has_both_methods"] = response.count("def ") >= 2 or ("재귀" in response and "반복" in response)
            
        elif test_type == "logical_reasoning":
            evaluation["has_logic"] = any(keyword in response for keyword in ["따라서", "그러므로", "결론", "추론"])
            evaluation["shows_thinking"] = "<think>" in response
        
        # 전반적 품질 점수 (0-100)
        quality_score = 0
        if evaluation["coherent"]: quality_score += 20
        if evaluation["length"] > 100: quality_score += 15
        if evaluation["has_korean"]: quality_score += 10
        
        # 타입별 추가 점수
        if test_type == "mathematical_reasoning" and evaluation.get("has_calculation", False): quality_score += 25
        if test_type == "data_analysis" and evaluation.get("has_analysis", False): quality_score += 25
        if test_type == "programming" and evaluation.get("has_function", False): quality_score += 25
        if test_type == "logical_reasoning" and evaluation.get("has_logic", False): quality_score += 25
        
        evaluation["quality_score"] = min(quality_score, 100)
        return evaluation
    
    def test_single_model(self, model_name: str) -> Dict[str, Any]:
        """단일 모델에 대한 전체 테스트 실행"""
        print(f"\n🧪 Testing {model_name}...")
        
        model_results = {
            "model_name": model_name,
            "test_start": datetime.now().isoformat(),
            "tests": {},
            "overall_performance": {}
        }
        
        total_response_time = 0
        successful_tests = 0
        total_quality_score = 0
        
        for test_name, test_config in self.test_cases.items():
            print(f"  📝 {test_name}... ", end="", flush=True)
            
            result = self.generate_response(
                model_name, 
                test_config["question"], 
                test_config["timeout"]
            )
            
            if result["success"]:
                evaluation = self.evaluate_response(result["response"], test_config["expected_type"])
                successful_tests += 1
                total_quality_score += evaluation["quality_score"]
                print(f"✅ ({result['response_time']:.2f}s, quality: {evaluation['quality_score']}/100)")
            else:
                evaluation = {"quality_score": 0, "error": result["error"]}
                print(f"❌ ({result['error']})")
            
            total_response_time += result["response_time"]
            
            model_results["tests"][test_name] = {
                **result,
                "evaluation": evaluation,
                "test_config": test_config
            }
        
        # 전체 성능 요약
        model_results["overall_performance"] = {
            "success_rate": successful_tests / len(self.test_cases) * 100,
            "average_response_time": total_response_time / len(self.test_cases),
            "average_quality_score": total_quality_score / len(self.test_cases) if successful_tests > 0 else 0,
            "total_tests": len(self.test_cases),
            "successful_tests": successful_tests
        }
        
        model_results["test_end"] = datetime.now().isoformat()
        return model_results
    
    def test_all_models(self) -> Dict[str, Any]:
        """모든 설치된 모델 테스트"""
        if not self.test_ollama_connection():
            print("❌ Ollama 서버에 연결할 수 없습니다.")
            return {}
        
        installed_models = self.model_manager.get_installed_model_names()
        
        if not installed_models:
            print("❌ 설치된 모델이 없습니다.")
            return {}
        
        print(f"🚀 총 {len(installed_models)}개 모델 테스트 시작...")
        print("=" * 80)
        
        all_results = {
            "test_session": {
                "start_time": datetime.now().isoformat(),
                "models_tested": len(installed_models),
                "test_cases": len(self.test_cases)
            },
            "models": {}
        }
        
        for model_name in installed_models:
            try:
                model_results = self.test_single_model(model_name)
                all_results["models"][model_name] = model_results
            except KeyboardInterrupt:
                print("\n🛑 테스트가 중단되었습니다.")
                break
            except Exception as e:
                print(f"\n❌ {model_name} 테스트 중 오류: {e}")
                all_results["models"][model_name] = {
                    "model_name": model_name,
                    "error": str(e),
                    "tests": {}
                }
        
        all_results["test_session"]["end_time"] = datetime.now().isoformat()
        return all_results
    
    def save_results(self, results: Dict[str, Any]):
        """결과를 파일로 저장"""
        if not results:
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"model_capability_test_{timestamp}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            
            print(f"\n📊 테스트 결과가 '{filename}'에 저장되었습니다.")
            
        except Exception as e:
            print(f"❌ 결과 저장 실패: {e}")
    
    def print_summary(self, results: Dict[str, Any]):
        """결과 요약 출력"""
        if not results or "models" not in results:
            return
        
        print("\n" + "=" * 80)
        print("📈 모델 성능 요약")
        print("=" * 80)
        
        # 성능순으로 정렬
        model_performance = []
        for model_name, model_data in results["models"].items():
            if "overall_performance" in model_data:
                perf = model_data["overall_performance"]
                model_performance.append((
                    model_name,
                    perf.get("success_rate", 0),
                    perf.get("average_quality_score", 0),
                    perf.get("average_response_time", 999)
                ))
        
        model_performance.sort(key=lambda x: (x[1], x[2], -x[3]), reverse=True)
        
        print(f"{'순위':>3} | {'모델명':>25} | {'성공률':>7} | {'품질점수':>8} | {'평균응답시간':>12}")
        print("-" * 80)
        
        for i, (model_name, success_rate, quality_score, response_time) in enumerate(model_performance, 1):
            print(f"{i:>3} | {model_name:>25} | {success_rate:>6.1f}% | {quality_score:>7.1f}/100 | {response_time:>10.2f}s")
        
        print("\n🏆 최고 성능 모델:")
        if model_performance:
            best_model = model_performance[0]
            print(f"   {best_model[0]} - 성공률 {best_model[1]:.1f}%, 품질점수 {best_model[2]:.1f}/100")
        
        print("\n⚡ 가장 빠른 모델:")
        fastest_model = min(model_performance, key=lambda x: x[3]) if model_performance else None
        if fastest_model:
            print(f"   {fastest_model[0]} - 평균 {fastest_model[3]:.2f}초")

def main():
    """메인 함수"""
    print("🧪 Ollama 모델 능력 테스트 도구")
    print("=" * 80)
    
    tester = ModelTester()
    
    try:
        # 모든 모델 테스트
        results = tester.test_all_models()
        
        if results:
            # 요약 출력
            tester.print_summary(results)
            
            # 결과 저장
            tester.save_results(results)
            
            print(f"\n✅ 테스트 완료! 총 {len(results.get('models', {}))}개 모델 테스트됨")
        else:
            print("❌ 테스트를 실행할 수 없습니다.")
    
    except KeyboardInterrupt:
        print("\n🛑 사용자가 테스트를 중단했습니다.")
    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {e}")

if __name__ == "__main__":
    main()


