"""
==============================================================================
힙 정렬(Heap Sort) & 도수 정렬(Counting Sort) 동시 비교 FastAPI 서버 (main.py)
==============================================================================

[주요 기능]
1. 알고리즘 구현:
   - 힙 정렬(Max Heap Sort): O(N log N) 제자리 정렬 및 단계별 힙 조정/스왑 스냅샷
   - 도수 정렬(Counting Sort): O(N + K) 비비교 정렬 및 빈도 카운팅, 누적합, 역방향 배치 스냅샷
2. 단계별 히스토그램 데이터 생성:
   - 각 스텝마다 배열의 상태(값, 비교/스왑/배치/확정 인덱스)를 기록하여 클라이언트 히스토그램 렌더링 지원
3. 메타데이터 및 복잡도 추적:
   - 알고리즘별 소요 시간(ms), 누적 연산 횟수, 이론적 복잡도 진행률(% ) 계산 포함
4. 통신 구조:
   - GAS(Google Apps Script) 프록시 및 브라우저 직접 호출 모두 지원 (전역 CORS 허용)
   - GET / (서버 헬스체크), POST & GET /api/sort (정렬 스냅샷 데이터 생성)
"""

import time
import math
import random
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(
    title="Heap & Counting Sort Visualizer API",
    description="힙 정렬과 도수 정렬의 단계별 히스토그램 스냅샷 및 복잡도 비교 API",
    version="1.0.0"
)

# CORS 전역 허용 (GAS Web App 및 로컬 웹 환경 지원)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# 1. 메타데이터 정의
# ============================================================================
ALGORITHM_METADATA = {
    "heap_sort": {
        "name": "힙 정렬 (Heap Sort)",
        "type": "비교 기반 제자리 정렬 (Comparison In-place Sort)",
        "complexity": {
            "best": "O(N log N)",
            "average": "O(N log N)",
            "worst": "O(N log N)",
            "space": "O(1)"
        },
        "description": "배열을 완전 이진 트리 구조의 최대 힙으로 변환한 후, 루트(최대값)를 순차 추출하여 정렬합니다."
    },
    "counting_sort": {
        "name": "도수 정렬 (Counting Sort)",
        "type": "비교 배제 정수 정렬 (Non-comparison Distribution Sort)",
        "complexity": {
            "best": "O(N + K)",
            "average": "O(N + K)",
            "worst": "O(N + K)",
            "space": "O(N + K)"
        },
        "description": "원소 간의 대소 비교 없이 각 정수의 출현 빈도수와 누적합을 계산하여 원소의 최종 위치를 직접 결정합니다."
    }
}


# ============================================================================
# 2. 알고리즘 스냅샷 로직 구현
# ============================================================================

def generate_heap_sort_snapshots(arr: List[int]) -> Dict[str, Any]:
    """
    최대 힙 기반 힙 정렬 실행 및 히스토그램 상태 스냅샷 기록
    """
    start_time = time.perf_counter()
    snapshots: List[Dict[str, Any]] = []
    a = list(arr)
    n = len(a)
    step = 0
    comparisons = 0
    swaps = 0
    fixed_indices: List[int] = []

    # 이론적 연산 횟수 기준치 (N log2 N)
    theoretical_ops = max(1, int(n * math.log2(n))) if n > 1 else 1

    def record_step(action: str, desc: str, comparing: List[int] = None, swapping: List[int] = None, largest: int = None, heap_size: int = n):
        nonlocal step
        cur_ops = comparisons + swaps
        progress = min(100.0, round((cur_ops / theoretical_ops) * 100.0, 1)) if action != "done" else 100.0
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 3)

        snapshots.append({
            "step": step,
            "array": list(a),
            "action": action,
            "description": desc,
            "comparing": comparing or [],
            "swapping": swapping or [],
            "fixed": list(fixed_indices),
            "heap_size": heap_size,
            "largest": largest,
            "comparisons": comparisons,
            "swaps": swaps,
            "total_operations": cur_ops,
            "progress_percent": progress,
            "elapsed_ms": elapsed_ms
        })
        step += 1

    # 1. 초기 상태 기록
    record_step("init", f"힙 정렬 시작 (배열 원소 수: {n})", heap_size=n)

    if n <= 1:
        if n == 1:
            fixed_indices.append(0)
        record_step("done", "원소가 1개 이하이므로 정렬이 완료되었습니다.", heap_size=0)
        return {
            "snapshots": snapshots,
            "total_steps": len(snapshots),
            "comparisons": comparisons,
            "swaps": swaps,
            "total_operations": comparisons + swaps,
            "execution_time_ms": round((time.perf_counter() - start_time) * 1000, 3)
        }

    def heapify(size: int, root_idx: int):
        nonlocal comparisons, swaps
        largest = root_idx
        left = 2 * root_idx + 1
        right = 2 * root_idx + 2

        if left < size:
            comparisons += 1
            record_step(
                "heapify_compare",
                f"부모 노드(인덱스 {root_idx}, 값 {a[root_idx]})와 왼쪽 자식(인덱스 {left}, 값 {a[left]}) 대소 비교",
                comparing=[root_idx, left],
                largest=largest,
                heap_size=size
            )
            if a[left] > a[largest]:
                largest = left

        if right < size:
            comparisons += 1
            record_step(
                "heapify_compare",
                f"현재 최대 노드(인덱스 {largest}, 값 {a[largest]})와 오른쪽 자식(인덱스 {right}, 값 {a[right]}) 대소 비교",
                comparing=[largest, right],
                largest=largest,
                heap_size=size
            )
            if a[right] > a[largest]:
                largest = right

        if largest != root_idx:
            swaps += 1
            record_step(
                "heapify_swap",
                f"최대 힙 조건 만족을 위해 부모(인덱스 {root_idx}, 값 {a[root_idx]})와 자식(인덱스 {largest}, 값 {a[largest]}) 위치 교환",
                swapping=[root_idx, largest],
                largest=largest,
                heap_size=size
            )
            a[root_idx], a[largest] = a[largest], a[root_idx]
            heapify(size, largest)

    # 2. Build Max Heap
    record_step("build_heap", "배열을 완전 이진 트리 기반의 최대 힙(Max Heap) 구조로 변환 시작", heap_size=n)
    for i in range(n // 2 - 1, -1, -1):
        heapify(n, i)
    record_step("build_heap_done", f"최대 힙 구성 완료! (현재 루트 원소 {a[0]}가 힙 내 최대값)", heap_size=n)

    # 3. Sort: Extract Max
    for i in range(n - 1, 0, -1):
        swaps += 1
        record_step(
            "extract_max",
            f"최대값 루트(인덱스 0, 값 {a[0]})를 정렬 영역 끝(인덱스 {i}, 값 {a[i]})과 교환 후 최종 확정",
            swapping=[0, i],
            heap_size=i + 1
        )
        a[0], a[i] = a[i], a[0]
        fixed_indices.append(i)
        heapify(i, 0)

    fixed_indices.append(0)
    fixed_indices.sort()
    record_step("done", "힙 정렬이 완전히 완료되었습니다.", heap_size=0)

    total_time = round((time.perf_counter() - start_time) * 1000, 3)
    return {
        "snapshots": snapshots,
        "total_steps": len(snapshots),
        "comparisons": comparisons,
        "swaps": swaps,
        "total_operations": comparisons + swaps,
        "execution_time_ms": total_time
    }


def generate_counting_sort_snapshots(arr: List[int]) -> Dict[str, Any]:
    """
    도수 정렬(Counting Sort) 실행 및 히스토그램 상태 스냅샷 기록
    """
    start_time = time.perf_counter()
    snapshots: List[Dict[str, Any]] = []
    a = list(arr)
    n = len(a)
    step = 0
    operations = 0
    fixed_indices: List[int] = []

    if n == 0:
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 3)
        snapshots.append({
            "step": 0,
            "array": [],
            "action": "done",
            "description": "빈 배열이므로 정렬이 완료되었습니다.",
            "comparing": [],
            "swapping": [],
            "fixed": [],
            "count_table": [],
            "total_operations": 0,
            "progress_percent": 100.0,
            "elapsed_ms": elapsed_ms
        })
        return {
            "snapshots": snapshots,
            "total_steps": 1,
            "total_operations": 0,
            "execution_time_ms": elapsed_ms
        }

    min_val = min(a)
    max_val = max(a)
    k_range = max_val - min_val + 1
    theoretical_ops = max(1, 2 * n + k_range)  # count(N) + prefix_sum(K) + placement(N)

    # 출력용 초기 배열 (미배치 상태를 시각화하기 위해 초기에는 원본 표시 혹은 플레이스홀더)
    output = [None] * n

    def record_step(action: str, desc: str, current_array: List[Any], count_arr: List[int], comparing: List[int] = None, swapping: List[int] = None):
        nonlocal step
        progress = min(100.0, round((operations / theoretical_ops) * 100.0, 1)) if action != "done" else 100.0
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 3)

        # 클라이언트 히스토그램 렌더링용 배열 (None 값은 -1 또는 임시값으로 처리)
        rendered_array = [val if val is not None else 0 for val in current_array]

        snapshots.append({
            "step": step,
            "array": rendered_array,
            "raw_array": list(current_array),
            "count_table": [{"value": min_val + idx, "count": cnt} for idx, cnt in enumerate(count_arr)],
            "action": action,
            "description": desc,
            "comparing": comparing or [],
            "swapping": swapping or [],
            "fixed": list(fixed_indices),
            "min_val": min_val,
            "max_val": max_val,
            "range_k": k_range,
            "total_operations": operations,
            "progress_percent": progress,
            "elapsed_ms": elapsed_ms
        })
        step += 1

    count = [0] * k_range

    # 1. 초기 상태
    record_step("init", f"도수 정렬 시작 (배열 크기 N={n}, 값 범위 K={k_range} [{min_val}~{max_val}])", a, count)

    # 2. 빈도 카운팅 (Frequency Counting: O(N))
    for idx, num in enumerate(a):
        operations += 1
        count[num - min_val] += 1
        record_step(
            "count_freq",
            f"원소 {num}(인덱스 {idx}) 확인 -> 도수 분포표 카운트 count[{num}] = {count[num - min_val]}로 증가",
            a,
            count,
            comparing=[idx]
        )

    # 3. 누적합 계산 (Prefix Sums: O(K))
    for i in range(1, k_range):
        operations += 1
        count[i] += count[i - 1]
        record_step(
            "accumulate",
            f"누적 도수 계산: 값 {min_val + i} 이하의 총 원소 수 = {count[i]}개 (최종 배치 위치 확정용)",
            a,
            count,
            swapping=[i]
        )

    # 4. 역방향 순회 및 출력 배열 배치 (Output Placement: O(N))
    # 안정 정렬(Stable Sort)을 유지하기 위해 원본 배열을 끝에서부터 순회합니다.
    for i in range(n - 1, -1, -1):
        operations += 1
        val = a[i]
        pos = count[val - min_val] - 1
        output[pos] = val
        count[val - min_val] -= 1
        fixed_indices.append(pos)
        record_step(
            "place_element",
            f"원본 원소 {val}(인덱스 {i})를 누적 위치(인덱스 {pos})에 배치하고 잔여 카운트 차감",
            output,
            count,
            comparing=[i],
            swapping=[pos]
        )

    fixed_indices.sort()
    record_step("done", "도수 정렬이 완전히 완료되었습니다.", output, count)

    total_time = round((time.perf_counter() - start_time) * 1000, 3)
    return {
        "snapshots": snapshots,
        "total_steps": len(snapshots),
        "total_operations": operations,
        "execution_time_ms": total_time
    }


# ============================================================================
# 3. FastAPI 요청/응답 모델 및 엔드포인트 정의
# ============================================================================

class SortRequest(BaseModel):
    array: Optional[List[int]] = Field(default=None, description="정렬 대상 정수 배열")
    size: Optional[int] = Field(default=10, ge=4, le=40, description="무작위 배열 생성 시 크기 (4~40)")


@app.get("/")
def health_check():
    """서버 상태 확인 및 정보 제공 엔드포인트"""
    return {
        "status": "online",
        "service": "Heap Sort vs Counting Sort Simultaneous Visualizer",
        "supported_algorithms": ["heap_sort", "counting_sort"],
        "endpoints": {
            "sort": "/api/sort (GET / POST)"
        },
        "version": "1.0.0"
    }


@app.api_route("/api/sort", methods=["GET", "POST"])
async def sort_endpoint(request: Request):
    """
    힙 정렬 및 도수 정렬 동시 실행 및 단계별 히스토그램 스냅샷 반환 API
    """
    req_array: Optional[List[int]] = None
    req_size: int = 10

    # 요청 파라미터 파싱 (POST JSON / GET Query 모두 유연하게 수용)
    if request.method == "POST":
        try:
            body = await request.json()
            req_array = body.get("array")
            req_size = int(body.get("size", 10))
        except Exception:
            pass
    else:
        q_params = request.query_params
        if "size" in q_params:
            try:
                req_size = int(q_params["size"])
            except ValueError:
                pass

    # 배열 검증 및 생성
    if req_array and isinstance(req_array, list) and len(req_array) > 0:
        try:
            target_array = [int(x) for x in req_array]
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="배열의 모든 원소는 정수여야 합니다.")
    else:
        req_size = max(4, min(req_size, 30))
        # 도수 정렬 시각화에 적합한 범위(1~30)의 난수 생성
        target_array = [random.randint(1, 25) for _ in range(req_size)]

    # 두 알고리즘 스냅샷 동시 생성
    heap_result = generate_heap_sort_snapshots(target_array)
    counting_result = generate_counting_sort_snapshots(target_array)

    return {
        "status": "success",
        "array_size": len(target_array),
        "original_array": target_array,
        "metadata": ALGORITHM_METADATA,
        "results": {
            "heap_sort": heap_result,
            "counting_sort": counting_result
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)

