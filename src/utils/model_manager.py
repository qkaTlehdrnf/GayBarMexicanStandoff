"""
모델 관리 유틸리티
Ollama 모델의 설치 확인, 모델 정보 관리를 담당
"""

import subprocess
import json
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ModelInfo:
    """모델 정보를 담는 데이터클래스"""
    name: str
    id: str
    size: str
    modified: str
    fruit_name: Optional[str] = None
    description: Optional[str] = None


class ModelManager:
    """Ollama 모델 관리를 담당하는 클래스"""
    
    def __init__(self):
        self.installed_models = self._get_installed_models()
    
    def _get_installed_models(self) -> List[ModelInfo]:
        """
        설치된 Ollama 모델 목록을 가져옴
        
        Returns:
            설치된 모델 정보 리스트
        """
        try:
            result = subprocess.run(['ollama', 'list'], 
                                  capture_output=True, 
                                  text=True, 
                                  check=True)
            
            models = []
            lines = result.stdout.strip().split('\n')
            
            # 헤더 라인 건너뛰기
            for line in lines[1:]:
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 4:
                        model_info = ModelInfo(
                            name=parts[0],
                            id=parts[1],
                            size=parts[2],
                            modified=' '.join(parts[3:])
                        )
                        models.append(model_info)
            
            return models
            
        except subprocess.CalledProcessError:
            print("Ollama 명령 실행 실패. Ollama가 설치되어 있는지 확인하세요.")
            return []
        except Exception as e:
            print(f"모델 목록 가져오기 실패: {e}")
            return []
    
    def refresh_models(self):
        """설치된 모델 목록 새로고침"""
        self.installed_models = self._get_installed_models()
    
    def is_model_installed(self, model_name: str) -> bool:
        """
        모델이 설치되어 있는지 확인
        
        Args:
            model_name: 확인할 모델명
            
        Returns:
            설치 여부
        """
        return any(model.name == model_name for model in self.installed_models)
    
    def get_installed_model_names(self) -> List[str]:
        """
        설치된 모델명 리스트 반환
        
        Returns:
            모델명 리스트
        """
        return [model.name for model in self.installed_models]
    
    def filter_available_models(self, model_list: List[str]) -> List[str]:
        """
        주어진 모델 리스트에서 실제 설치된 모델만 필터링
        
        Args:
            model_list: 확인할 모델 리스트
            
        Returns:
            실제 설치된 모델 리스트
        """
        installed_names = self.get_installed_model_names()
        return [model for model in model_list if model in installed_names]
    
    def suggest_alternative_models(self, model_name: str) -> List[str]:
        """
        설치되지 않은 모델에 대해 유사한 대안 모델 제안
        
        Args:
            model_name: 찾을 수 없는 모델명
            
        Returns:
            유사한 모델명 리스트
        """
        if self.is_model_installed(model_name):
            return [model_name]
        
        # 모델 패밀리별로 유사한 모델 찾기
        model_family = model_name.split(':')[0]
        alternatives = []
        
        for model in self.installed_models:
            if model.name.startswith(model_family):
                alternatives.append(model.name)
        
        return alternatives
    
    def get_model_info(self, model_name: str) -> Optional[ModelInfo]:
        """
        특정 모델의 정보 반환
        
        Args:
            model_name: 모델명
            
        Returns:
            모델 정보 또는 None
        """
        for model in self.installed_models:
            if model.name == model_name:
                return model
        return None
    
    def install_model(self, model_name: str) -> bool:
        """
        모델 설치 시도
        
        Args:
            model_name: 설치할 모델명
            
        Returns:
            설치 성공 여부
        """
        try:
            print(f"{model_name} 설치 중...")
            result = subprocess.run(['ollama', 'pull', model_name], 
                                  capture_output=True, 
                                  text=True, 
                                  check=True)
            
            if result.returncode == 0:
                print(f"{model_name} 설치 완료")
                self.refresh_models()
                return True
            else:
                print(f"{model_name} 설치 실패: {result.stderr}")
                return False
                
        except subprocess.CalledProcessError as e:
            print(f"{model_name} 설치 실패: {e}")
            return False
        except Exception as e:
            print(f"설치 중 오류 발생: {e}")
            return False
    
    def get_models_by_size(self, min_size_gb: float = 0, max_size_gb: float = float('inf')) -> List[ModelInfo]:
        """
        크기별로 모델 필터링
        
        Args:
            min_size_gb: 최소 크기 (GB)
            max_size_gb: 최대 크기 (GB)
            
        Returns:
            조건에 맞는 모델 리스트
        """
        filtered_models = []
        
        for model in self.installed_models:
            size_gb = self._parse_size_to_gb(model.size)
            if min_size_gb <= size_gb <= max_size_gb:
                filtered_models.append(model)
        
        return filtered_models
    
    def _parse_size_to_gb(self, size_str: str) -> float:
        """
        크기 문자열을 GB로 변환
        
        Args:
            size_str: 크기 문자열 (예: "42 GB", "1.2 TB")
            
        Returns:
            GB 단위 크기
        """
        try:
            # 숫자와 단위 분리
            match = re.match(r'([\d.]+)\s*([A-Z]+)', size_str.upper())
            if not match:
                return 0.0
            
            value = float(match.group(1))
            unit = match.group(2)
            
            if unit == 'GB':
                return value
            elif unit == 'TB':
                return value * 1024
            elif unit == 'MB':
                return value / 1024
            else:
                return 0.0
                
        except (ValueError, AttributeError):
            return 0.0
    
    def get_lightweight_models(self, max_size_gb: float = 20) -> List[ModelInfo]:
        """
        가벼운 모델들 반환 (기본: 20GB 이하)
        
        Args:
            max_size_gb: 최대 크기 제한
            
        Returns:
            가벼운 모델 리스트
        """
        return self.get_models_by_size(max_size_gb=max_size_gb)
    
    def get_heavy_models(self, min_size_gb: float = 50) -> List[ModelInfo]:
        """
        무거운 모델들 반환 (기본: 50GB 이상)
        
        Args:
            min_size_gb: 최소 크기 제한
            
        Returns:
            무거운 모델 리스트
        """
        return self.get_models_by_size(min_size_gb=min_size_gb)
    
    def print_model_summary(self):
        """설치된 모델 요약 정보 출력"""
        if not self.installed_models:
            print("설치된 모델이 없습니다.")
            return
        
        print(f"\n=== 설치된 모델 ({len(self.installed_models)}개) ===")
        
        total_size_gb = 0
        for model in sorted(self.installed_models, key=lambda x: self._parse_size_to_gb(x.size), reverse=True):
            size_gb = self._parse_size_to_gb(model.size)
            total_size_gb += size_gb
            print(f"{model.name:30} | {model.size:>8} | {model.modified}")
        
        print(f"\n총 용량: {total_size_gb:.1f} GB")
        
        # 크기별 분류
        lightweight = self.get_lightweight_models()
        heavy = self.get_heavy_models()
        
        print(f"가벼운 모델 (20GB 이하): {len(lightweight)}개")
        print(f"무거운 모델 (50GB 이상): {len(heavy)}개")


