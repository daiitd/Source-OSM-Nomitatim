import os
import json
import uuid
import datetime
import threading
from typing import Optional, Dict, Any, List

LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(LOGS_DIR, exist_ok=True)
ACCESS_LOG_FILE = os.path.join(LOGS_DIR, "access.jsonl")

class StructuredLogger:
    """
    Logger ghi log có cấu trúc JSON theo chuẩn Mục 5.5 của báo cáo nghiên cứu.
    Đồng thời lưu bộ nhớ đệm 100 log gần nhất để hiển thị trực tiếp trên giao diện Demo/API.
    """
    def __init__(self, log_file_path: str = ACCESS_LOG_FILE):
        self._log_file_path = log_file_path
        self._lock = threading.Lock()
        self._recent_logs: List[Dict[str, Any]] = []

    @staticmethod
    def generate_request_id() -> str:
        return uuid.uuid4().hex[:8]

    def log_request(
        self,
        request_id: str,
        endpoint: str,
        cache_status: str,  # "hit" | "miss" | "none"
        outcome: str,       # "ok" | "validation_error" | "no_result" | "upstream_rate_limited" | "timeout" | "upstream_error" | ...
        upstream_status: Optional[int] = None,
        upstream_ms: Optional[int] = None,
        circuit_open_sec: Optional[int] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        now_iso = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=7))).isoformat()
        
        record: Dict[str, Any] = {
            "ts": now_iso,
            "requestId": request_id,
            "endpoint": endpoint,
            "cache": cache_status,
            "upstreamStatus": upstream_status,
            "upstreamMs": upstream_ms,
            "outcome": outcome,
        }

        if circuit_open_sec is not None:
            record["circuitOpenSec"] = circuit_open_sec

        if extra:
            record["details"] = extra

        # In ra console định dạng dễ nhìn cho reviewer
        self._print_console(record)

        # Ghi file JSONL
        json_line = json.dumps(record, ensure_ascii=False)
        with self._lock:
            try:
                with open(self._log_file_path, "a", encoding="utf-8") as f:
                    f.write(json_line + "\n")
            except Exception as e:
                print(f"[Logger Error] Cannot write to file: {e}")

            # Lưu vào danh sách recent logs (tối đa 100)
            self._recent_logs.append(record)
            if len(self._recent_logs) > 100:
                self._recent_logs.pop(0)

        return record

    def get_recent_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            return list(reversed(self._recent_logs[-limit:]))

    def _print_console(self, rec: Dict[str, Any]) -> None:
        status_color = "\033[92m" if rec["outcome"] == "ok" else "\033[91m"
        reset_color = "\033[0m"
        cache_indicator = f"[\033[94mCACHE {rec['cache'].upper()}\033[0m]" if rec["cache"] != "none" else ""
        upstream_info = f"-> Nominatim: {rec['upstreamStatus']} ({rec['upstreamMs']}ms)" if rec["upstreamStatus"] else ""
        
        print(f"[{rec['ts'][11:19]}] [{rec['requestId']}] {rec['endpoint']} {cache_indicator} "
              f"{status_color}{rec['outcome'].upper()}{reset_color} {upstream_info}")

# Global logger
structured_logger = StructuredLogger()

