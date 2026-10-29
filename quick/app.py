"""
Google Cloud Run 배포용 Flask 백엔드 서버 (app.py)

역할:
1. 클라이언트(GAS 또는 웹 브라우저)로부터 정렬 대상 배열 요청 수신
2. 셸 정렬, 퀵 정렬, 병합 정렬 알고리즘을 각각 실행하여 상태 스냅샷 히스토리 생성
3. 알고리즘 복잡도(Complexity) 및 메타데이터를 포함한 JSON 응답 반환
4. CORS 지원 및 철저한 입력값 검증과 상세한 에러 핸들링 제공
"""

import os
import random
from typing import Any, Dict, List
from flask import Flask, jsonify, request
from flask_cors import CORS

from algorithms import (
    shell_sort_with_snapshots,
    quick_sort_with_snapshots,
    merge_sort_with_snapshots,
)

app = Flask(__name__)

# Google Apps Script(GAS) 웹 앱 및 외부 브라우저 요청을 위한 CORS 전역 허용
CORS(app, resources={r"/*": {"origins": "*"}})


# 알고리즘별 시간 및 공간 복잡도 메타데이터 정의
ALGORITHM_METADATA = {
    "shell_sort": {
        "name": "셸 정렬 (Shell Sort)",
        "complexity": {
            "best": "O(N log N)",
            "average": "O(N^1.25 ~ N^1.5)",
            "worst": "O(N²)",
            "space": "O(1)"
        },
        "description": "삽입 정렬의 장점을 살리고 단점을 보완한 알고리즘으로, 간격(Gap)을 점진적으로 줄이며 부분 삽입 정렬을 수행합니다."
    },
    "quick_sort": {
        "name": "퀵 정렬 (Quick Sort)",
        "complexity": {
            "best": "O(N log N)",
            "average": "O(N log N)",
            "worst": "O(N²)",
            "space": "O(log N)"
        },
        "description": "분할 정복(Divide & Conquer) 알고리즘으로, 기준 원소(Pivot)를 정하여 작은 값과 큰 값을 분할 배치합니다."
    },
    "merge_sort": {
        "name": "병합 정렬 (Merge Sort)",
        "complexity": {
            "best": "O(N log N)",
            "average": "O(N log N)",
            "worst": "O(N log N)",
            "space": "O(N)"
        },
        "description": "배열을 최소 단위까지 논리적으로 분할한 후, 정렬 순서에 맞춰 두 부분 배열을 병합하며 원본에 덮어씁니다."
    }
}


@app.route("/", methods=["GET"])
def health_check():
    """서버 헬스체크 및 정보 제공 엔드포인트"""
    return jsonify({
        "status": "online",
        "service": "Sorting Visualizer Backend API",
        "supported_algorithms": ["shell_sort", "quick_sort", "merge_sort"],
        "endpoints": {
            "sort": "/api/sort (POST / GET)"
        },
        "version": "1.0.0"
    }), 200


@app.route("/api/sort", methods=["GET", "POST"])
def sort_api():
    """
    3개 정렬 알고리즘(셸, 퀵, 병합) 동시 실행 및 스냅샷 히스토리 반환 API
    
    요청 파라미터 (JSON Body 또는 GET Query):
    - array: list[int] (선택, 미입력 시 10개 원소의 무작위 배열 생성)
    - size: int (선택, 무작위 생성 시 배열 크기, 기본값 10, 범위 4~30)
    """
    try:
        req_data = {}
        if request.method == "POST":
            if request.is_json:
                req_data = request.get_json(silent=True) or {}
            else:
                req_data = request.form.to_dict()
        else:
            req_data = request.args.to_dict()

        target_array: List[int] = []

        # 1. 입력 배열 파싱 및 검증
        if "array" in req_data and req_data["array"]:
            raw_array = req_data["array"]
            # 문자열인 경우 (예: "12, 5, 8, 3") 파싱 처리
            if isinstance(raw_array, str):
                try:
                    target_array = [int(x.strip()) for x in raw_array.split(",") if x.strip()]
                except ValueError as ve:
                    return jsonify({
                        "status": "error",
                        "error_code": "INVALID_ARRAY_FORMAT",
                        "message": f"배열 원소는 정수여야 합니다: {str(ve)}",
                        "received": raw_array
                    }), 400
            elif isinstance(raw_array, list):
                try:
                    target_array = [int(x) for x in raw_array]
                except (ValueError, TypeError) as ve:
                    return jsonify({
                        "status": "error",
                        "error_code": "INVALID_ELEMENT_TYPE",
                        "message": f"배열 내부의 모든 원소는 정수로 변환 가능해야 합니다: {str(ve)}",
                        "received": raw_array
                    }), 400
            else:
                return jsonify({
                    "status": "error",
                    "error_code": "UNSUPPORTED_DATA_TYPE",
                    "message": "array 파라미터는 배열(list) 또는 쉼표로 구분된 문자열이어야 합니다."
                }), 400

            # 배열 크기 검증 (시각화 애니메이션의 원활한 표현을 위해 4~30개 권장)
            if len(target_array) < 3:
                return jsonify({
                    "status": "error",
                    "error_code": "ARRAY_TOO_SHORT",
                    "message": "시각화를 위해 배열 원소는 최소 3개 이상이어야 합니다."
                }), 400
            if len(target_array) > 40:
                return jsonify({
                    "status": "error",
                    "error_code": "ARRAY_TOO_LARGE",
                    "message": "타임라인 시각화 성능을 위해 최대 40개 이하의 배열만 지원합니다."
                }), 400
        else:
            # 전달받은 배열이 없는 경우 무작위 배열 자동 생성
            size = 10
            if "size" in req_data:
                try:
                    size = int(req_data["size"])
                    size = max(4, min(size, 25))
                except ValueError:
                    size = 10
            # 5부터 99까지의 중복 없는(또는 거의 없는) 무작위 정수 생성
            target_array = random.sample(range(5, 100), size)

        # 2. 동일한 초기 배열을 기반으로 각 알고리즘 실행 및 상태 스냅샷 수집
        initial_copy = list(target_array)

        shell_snapshots = shell_sort_with_snapshots(initial_copy)
        quick_snapshots = quick_sort_with_snapshots(initial_copy)
        merge_snapshots = merge_sort_with_snapshots(initial_copy)

        # 단일 통합 타임라인을 위한 최대 스텝 수 계산
        max_steps = max(len(shell_snapshots), len(quick_snapshots), len(merge_snapshots))

        # 3. 통합 응답 페이로드 구성
        response_payload = {
            "status": "success",
            "initial_array": target_array,
            "element_count": len(target_array),
            "max_steps": max_steps,
            "results": {
                "shell_sort": {
                    "name": ALGORITHM_METADATA["shell_sort"]["name"],
                    "description": ALGORITHM_METADATA["shell_sort"]["description"],
                    "complexity": ALGORITHM_METADATA["shell_sort"]["complexity"],
                    "total_steps": len(shell_snapshots),
                    "snapshots": shell_snapshots
                },
                "quick_sort": {
                    "name": ALGORITHM_METADATA["quick_sort"]["name"],
                    "description": ALGORITHM_METADATA["quick_sort"]["description"],
                    "complexity": ALGORITHM_METADATA["quick_sort"]["complexity"],
                    "total_steps": len(quick_snapshots),
                    "snapshots": quick_snapshots
                },
                "merge_sort": {
                    "name": ALGORITHM_METADATA["merge_sort"]["name"],
                    "description": ALGORITHM_METADATA["merge_sort"]["description"],
                    "complexity": ALGORITHM_METADATA["merge_sort"]["complexity"],
                    "total_steps": len(merge_snapshots),
                    "snapshots": merge_snapshots
                }
            }
        }

        return jsonify(response_payload), 200

    except Exception as e:
        # 예상치 못한 서버 내부 예외 발생 시 상세 에러 반환
        return jsonify({
            "status": "error",
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": f"정렬 연산 중 서버 내부 오류가 발생했습니다: {str(e)}",
            "type": type(e).__name__
        }), 500


if __name__ == "__main__":
    # Cloud Run은 환경 변수 PORT를 전달하므로 이를 기본값(8080)과 함께 수신합니다.
    port = int(os.environ.get("PORT", 8080))
    # 로컬 개발 환경 테스트 실행 (디버그 모드 활성화)
    app.run(host="0.0.0.0", port=port, debug=True)

