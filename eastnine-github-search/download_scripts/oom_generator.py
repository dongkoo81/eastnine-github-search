"""
Memory Stress Test Script
Version: 3.0
Changes: 
- 메모리 테이블 설정 개선
- 테이블 가득 참 에러 처리
- 세션 변수 설정 방식 개선
"""

import mysql.connector
import threading
import time
from queue import Queue

# 💡 메모리 사용량 설정
TARGET_DATA_GB = 4          # 목표 사용 메모리 크기 (GB)
NUMBER_OF_WORKERS = 10        # 워커(세션) 수
BUFFER_OVERHEAD_PER_WORKER_GB = 0.1  # 워커당 예상 버퍼 오버헤드 (GB)

# 워커당 실제 데이터 제한 계산
MEMORY_PER_WORKER_GB = max(0.1, TARGET_DATA_GB / NUMBER_OF_WORKERS)  # 최소 0.1GB 보장

# 💡 데이터 설정
FILLER_SIZE = 2048            # 한 row의 크기 (bytes)
ROWS_PER_INSERT = 100         # 한 번에 삽입하는 row 수
SLEEP_INTERVAL = 0.1          # 반복 간격

# 워커당 최대 메모리 제한 계산 (bytes)
MAX_BYTES_LIMIT = int(MEMORY_PER_WORKER_GB * 1024 * 1024 * 1024)  # int로 변환

# DB 연결 정보
HOST = "oom-test-cluster.cluster-cmjs2qxaojzn.ap-northeast-2.rds.amazonaws.com"
USER = "admin"
PASSWORD = "OomTest123!"
DATABASE = "test"


def set_oom_session(cursor):
    # 먼저 현재 값 확인
    cursor.execute("SHOW VARIABLES LIKE 'max_heap_table_size'")
    current_size = cursor.fetchone()
    print(f"Current max_heap_table_size: {current_size[1]}")

    # 바이트 단위로 직접 설정
    size_bytes = int(MEMORY_PER_WORKER_GB * 1024 * 1024 * 1024)
    settings = [
        f"SET GLOBAL max_heap_table_size = {size_bytes}",
        f"SET SESSION max_heap_table_size = {size_bytes}",
        f"SET GLOBAL tmp_table_size = {size_bytes}",
        f"SET SESSION tmp_table_size = {size_bytes}"
    ]
    
    for s in settings:
        try:
            cursor.execute(s)
        except Exception as e:
            print(f"[세션 파라미터 실패] {s}: {e}")
    
    # 설정 후 값 확인
    cursor.execute("SHOW VARIABLES LIKE 'max_heap_table_size'")
    new_size = cursor.fetchone()
    print(f"New max_heap_table_size: {new_size[1]}")

def stress_worker(worker_id, error_queue):
    try:
        conn = mysql.connector.connect(
            host=HOST,
            user=USER,
            password=PASSWORD,
            database=DATABASE
        )
        cursor = conn.cursor()
        
        # 메모리 설정
        set_oom_session(cursor)
        print(f"[Worker {worker_id}] 세션 설정 완료")
        print(f"[Worker {worker_id}] 목표 데이터 크기: {MEMORY_PER_WORKER_GB:.2f}GB")

        # 임시 테이블 생성 전에 이전 테이블 정리
        cursor.execute("DROP TEMPORARY TABLE IF EXISTS temp_oom")
        
        # MEMORY 엔진으로 임시 테이블 생성
        create_table_sql = f"""
            CREATE TEMPORARY TABLE temp_oom (
                id INT AUTO_INCREMENT PRIMARY KEY,
                big_col VARCHAR({FILLER_SIZE})
            ) ENGINE=MEMORY MAX_ROWS=1000000
        """
        cursor.execute(create_table_sql)

        row_count = 0
        filler = 'A' * FILLER_SIZE
        insert_stopped = False

        while True:
            if not insert_stopped:
                try:
                    cursor.executemany(
                        "INSERT INTO temp_oom (big_col) VALUES (%s)",
                        [(filler,)] * ROWS_PER_INSERT
                    )
                    conn.commit()
                    row_count += ROWS_PER_INSERT

                    total_bytes = row_count * FILLER_SIZE
                    print(f"[Worker {worker_id}] rows: {row_count:,}, "
                          f"현재 데이터: {total_bytes/1024/1024/1024:.2f}GB / "
                          f"목표: {MEMORY_PER_WORKER_GB:.2f}GB")

                    if total_bytes >= MAX_BYTES_LIMIT:
                        print(f"[Worker {worker_id}] 🚫 INSERT 중단: "
                              f"목표 데이터 크기 {MEMORY_PER_WORKER_GB:.2f}GB 도달")
                        insert_stopped = True

                except mysql.connector.Error as err:
                    if err.errno == 1114:  # 테이블 가득 참 에러
                        print(f"[Worker {worker_id}] ⚠️ 테이블 가득 참, 데이터 유지")
                        insert_stopped = True
                    else:
                        raise

            time.sleep(SLEEP_INTERVAL)

    except Exception as e:
        print(f"[Worker {worker_id}] 오류 발생: {e}")
        error_queue.put(e)

    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

def main():
    print(f"\n=== 메모리 스트레스 테스트 시작 ===")
    print(f"목표 순수 데이터 크기: {TARGET_DATA_GB}GB")
    print(f"워커 수: {NUMBER_OF_WORKERS}")
    print(f"워커당 데이터 크기: {MEMORY_PER_WORKER_GB:.2f}GB")
    print(f"워커당 예상 버퍼 오버헤드: {BUFFER_OVERHEAD_PER_WORKER_GB}GB")
    print(f"예상 총 메모리 사용량: {(MEMORY_PER_WORKER_GB + BUFFER_OVERHEAD_PER_WORKER_GB) * NUMBER_OF_WORKERS:.2f}GB")
    print("=" * 50 + "\n")
    
    error_queue = Queue()
    threads = []
    for i in range(NUMBER_OF_WORKERS):
        t = threading.Thread(
            target=stress_worker,
            args=(i, error_queue)
        )
        t.daemon = True
        t.start()
        threads.append(t)

    try:
        while True:
            if not error_queue.empty():
                err = error_queue.get()
                print(f"[에러 감지] {err}")
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n=== 테스트 종료 요청됨 ===")

if __name__ == "__main__":
    main()
