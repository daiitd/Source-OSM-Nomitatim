from flask import Blueprint, render_template_string

views_bp = Blueprint("views", __name__)

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>MID Software | OpenStreetMap x Nominatim POC - Tuần 3</title>
  <style>
    :root {
      --primary: #1e3a8a;
      --primary-light: #3b82f6;
      --bg: #f8fafc;
      --card-bg: #ffffff;
      --text: #1e293b;
      --border: #e2e8f0;
      --success: #16a34a;
      --danger: #dc2626;
      --warning: #d97706;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
    body { background-color: var(--bg); color: var(--text); line-height: 1.5; padding: 20px; }
    .container { max-width: 1200px; margin: 0 auto; }
    header { background: linear-gradient(135deg, #0f172a, #1e3a8a); color: white; padding: 24px; border-radius: 12px; margin-bottom: 24px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }
    header h1 { font-size: 1.6rem; margin-bottom: 8px; }
    header p { opacity: 0.9; font-size: 0.95rem; }
    .badge { display: inline-block; padding: 3px 8px; border-radius: 999px; font-size: 0.75rem; font-weight: 600; background: #38bdf8; color: #0f172a; margin-right: 6px; }
    
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 24px; }
    @media (max-width: 900px) { .grid { grid-template-columns: 1fr; } }
    
    .card { background: var(--card-bg); border-radius: 10px; border: 1px solid var(--border); padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
    .card h2 { font-size: 1.2rem; margin-bottom: 14px; color: var(--primary); display: flex; align-items: center; justify-content: space-between; }
    
    .form-group { margin-bottom: 14px; }
    label { display: block; font-size: 0.85rem; font-weight: 600; margin-bottom: 5px; color: #475569; }
    input, select { width: 100%; padding: 8px 12px; border: 1px solid var(--border); border-radius: 6px; font-size: 0.95rem; }
    input:focus { outline: none; border-color: var(--primary-light); ring: 2px solid #bfdbfe; }
    
    .btn-row { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 10px; }
    button { cursor: pointer; padding: 8px 16px; border: none; border-radius: 6px; font-weight: 600; font-size: 0.9rem; transition: background 0.2s; }
    .btn-primary { background: var(--primary-light); color: white; }
    .btn-primary:hover { background: var(--primary); }
    .btn-secondary { background: #e2e8f0; color: #334155; }
    .btn-secondary:hover { background: #cbd5e1; }
    .btn-danger { background: #fee2e2; color: var(--danger); }
    .btn-danger:hover { background: #fecaca; }
    
    .quick-case-btn { font-size: 0.8rem; padding: 4px 10px; background: #e0f2fe; color: #0369a1; border-radius: 4px; border: 1px solid #bae6fd; }
    .quick-case-btn:hover { background: #bae6fd; }
    
    pre { background: #0f172a; color: #f8fafc; padding: 14px; border-radius: 8px; overflow-x: auto; font-size: 0.82rem; max-height: 280px; }
    .stats-bar { display: flex; gap: 14px; margin-bottom: 20px; flex-wrap: wrap; }
    .stat-pill { background: white; border: 1px solid var(--border); padding: 10px 16px; border-radius: 8px; flex: 1; min-width: 150px; }
    .stat-pill .title { font-size: 0.75rem; color: #64748b; text-transform: uppercase; font-weight: 700; }
    .stat-pill .value { font-size: 1.4rem; font-weight: 700; color: var(--primary); }
    
    .pipeline-box { background: #f1f5f9; padding: 14px; border-radius: 8px; border-left: 4px solid var(--primary); font-size: 0.85rem; margin-bottom: 20px; }
    .pipeline-step { display: inline-block; background: white; padding: 4px 8px; border-radius: 4px; margin: 2px 4px; border: 1px solid #cbd5e1; font-weight: 500; }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div>
        <span class="badge">TUẦN 3 POC</span>
        <span class="badge" style="background: #a7f3d0; color: #064e3b;">02–06/11/2026</span>
        <span class="badge" style="background: #fde68a; color: #78350f;">DEMO 07/11/2026</span>
      </div>
      <h1 style="margin-top: 8px;">RESEARCH ROADMAP: OPENSTREETMAP × NOMINATIM BACKEND</h1>
      <p>Thực hành tích hợp Nominatim vào Backend, DTO thống nhất, Cache, Giới hạn tốc độ & Bảng kịch bản lỗi</p>
      <div style="margin-top: 10px; font-size: 0.85rem; opacity: 0.85;">
        Nhóm thực hiện: <strong>Nguyễn Phương Đại · Dương Đức Quân</strong> | Đơn vị: <strong>Công ty TNHH MID Software</strong>
      </div>
    </header>

    <!-- Pipeline Overview -->
    <div class="pipeline-box">
      <strong>Pipeline chuẩn hóa 10 bước:</strong>
      <div style="margin-top: 6px;">
        <span class="pipeline-step">1. Input</span> &rarr;
        <span class="pipeline-step">2. Validate</span> &rarr;
        <span class="pipeline-step">3. Chuẩn hóa & Cache Key</span> &rarr;
        <span class="pipeline-step">4. Tra Cache</span> &rarr;
        <span class="pipeline-step">5. Điều tốc (1 rps)</span> &rarr;
        <span class="pipeline-step">6. Gọi Nominatim</span> &rarr;
        <span class="pipeline-step">7. Phân tích</span> &rarr;
        <span class="pipeline-step">8. Ánh xạ DTO</span> &rarr;
        <span class="pipeline-step">9. Lưu Cache</span> &rarr;
        <span class="pipeline-step">10. Response</span>
      </div>
    </div>

    <!-- Live Stats -->
    <div class="stats-bar">
      <div class="stat-pill">
        <div class="title">Cache Active Items</div>
        <div class="value" id="stat-active">0</div>
      </div>
      <div class="stat-pill">
        <div class="title">Cache Hits / Misses</div>
        <div class="value" id="stat-hits">0 / 0</div>
      </div>
      <div class="stat-pill">
        <div class="title">Tỷ lệ Cache Hit</div>
        <div class="value" id="stat-ratio">0%</div>
      </div>
      <div class="stat-pill">
        <div class="title">Circuit Breaker (429)</div>
        <div class="value" id="stat-cb" style="color: #16a34a;">CLOSED</div>
      </div>
    </div>

    <div class="grid">
      <!-- Section 1: Search POC -->
      <div class="card">
        <h2>
          <span>Task 3.2: POC Search Proxy</span>
          <span style="font-size: 0.8rem; font-weight: normal; color: #64748b;">GET /api/v1/geocode/search</span>
        </h2>
        <div class="form-group">
          <label>Từ khóa tìm kiếm (q):</label>
          <input type="text" id="search-q" value="Chợ Bến Thành" placeholder="Nhập địa danh...">
        </div>
        <div style="display: flex; gap: 10px;">
          <div class="form-group" style="flex: 1;">
            <label>Limit (1-10):</label>
            <input type="number" id="search-limit" value="5" min="1" max="10">
          </div>
          <div class="form-group" style="flex: 1;">
            <label>Quốc gia:</label>
            <input type="text" id="search-country" value="vn">
          </div>
        </div>

        <div style="margin-bottom: 10px;">
          <label>Test nhanh kịch bản:</label>
          <div class="btn-row">
            <button class="quick-case-btn" onclick="setSearch('Chợ Bến Thành')">Chợ Bến Thành</button>
            <button class="quick-case-btn" onclick="setSearch('Nhà thờ Đức Bà')">Nhà thờ Đức Bà</button>
            <button class="quick-case-btn" onclick="setSearch('xyzxyzxyz')">Không có KQ</button>
            <button class="quick-case-btn" onclick="setSearch('a')">Lỗi < 3 ký tự (400)</button>
          </div>
        </div>

        <div class="btn-row">
          <button class="btn-primary" onclick="executeSearch()">Gửi Request</button>
          <button class="btn-secondary" onclick="clearSearchOutput()">Xóa</button>
        </div>

        <div style="margin-top: 14px;">
          <label>Response DTO:</label>
          <pre id="search-output">// Kết quả sẽ hiển thị tại đây...</pre>
        </div>
      </div>

      <!-- Section 2: Reverse POC -->
      <div class="card">
        <h2>
          <span>Task 3.3: POC Reverse Proxy</span>
          <span style="font-size: 0.8rem; font-weight: normal; color: #64748b;">GET /api/v1/geocode/reverse</span>
        </h2>
        <div style="display: flex; gap: 10px;">
          <div class="form-group" style="flex: 1;">
            <label>Vĩ độ (lat):</label>
            <input type="text" id="reverse-lat" value="10.7725">
          </div>
          <div class="form-group" style="flex: 1;">
            <label>Kinh độ (lon):</label>
            <input type="text" id="reverse-lon" value="106.6980">
          </div>
          <div class="form-group" style="width: 80px;">
            <label>Zoom (3-18):</label>
            <input type="number" id="reverse-zoom" value="18" min="3" max="18">
          </div>
        </div>

        <div style="margin-bottom: 10px;">
          <label>3 Test Cases theo yêu cầu nghiệm thu (Bảng 10):</label>
          <div class="btn-row">
            <button class="quick-case-btn" style="background: #dcfce7; color: #15803d; border-color: #86efac;" onclick="setReverse(10.7725, 106.6980, 18)">
              <strong>[R1]</strong> Có dữ liệu (Bến Thành)
            </button>
            <button class="quick-case-btn" style="background: #fef3c7; color: #b45309; border-color: #fde68a;" onclick="setReverse(0.0, 0.0, 18)">
              <strong>[R2]</strong> Vùng không có dữ liệu (404)
            </button>
            <button class="quick-case-btn" style="background: #fee2e2; color: #b91c1c; border-color: #fca5a5;" onclick="setReverse(106.6980, 10.7725, 18)">
              <strong>[R3]</strong> Đảo lat/lon (400)
            </button>
          </div>
        </div>

        <div class="btn-row">
          <button class="btn-primary" onclick="executeReverse()">Gửi Request</button>
          <button class="btn-secondary" onclick="clearReverseOutput()">Xóa</button>
        </div>

        <div style="margin-top: 14px;">
          <label>Response DTO:</label>
          <pre id="reverse-output">// Kết quả sẽ hiển thị tại đây...</pre>
        </div>
      </div>
    </div>

    <!-- Section 3: Live Structured Logs & Cache Controls -->
    <div class="card" style="margin-bottom: 24px;">
      <h2>
        <span>Quan sát lỗi và Nhật ký hệ thống (Task 3.4)</span>
        <div>
          <button class="btn-danger" style="font-size: 0.8rem; padding: 4px 10px;" onclick="clearCache()">Xóa Cache</button>
          <button class="btn-secondary" style="font-size: 0.8rem; padding: 4px 10px;" onclick="fetchLogs()">Làm mới Log</button>
        </div>
      </h2>
      <p style="font-size: 0.85rem; color: #64748b; margin-bottom: 10px;">
        Format JSON cấu trúc theo Mục 5.5: <code>{"ts", "requestId", "endpoint", "cache", "upstreamStatus", "upstreamMs", "outcome"}</code>
      </p>
      <pre id="logs-output" style="max-height: 200px;">Đang tải nhật ký...</pre>
    </div>
  </div>

  <script>
    async function updateStats() {
      try {
        const res = await fetch('/api/v1/geocode/stats');
        const data = await res.json();
        document.getElementById('stat-active').innerText = data.cache.activeEntries;
        document.getElementById('stat-hits').innerText = `${data.cache.totalHits} / ${data.cache.totalMisses}`;
        document.getElementById('stat-ratio').innerText = `${data.cache.hitRatioPercent}%`;
        
        const cbEl = document.getElementById('stat-cb');
        if (data.circuitBreaker.isOpen) {
          cbEl.innerText = `OPEN (${data.circuitBreaker.remainingCooldownSec}s)`;
          cbEl.style.color = '#dc2626';
        } else {
          cbEl.innerText = 'CLOSED';
          cbEl.style.color = '#16a34a';
        }
      } catch (e) {
        console.error(e);
      }
    }

    async function fetchLogs() {
      try {
        const res = await fetch('/api/v1/geocode/logs?limit=15');
        const data = await res.json();
        document.getElementById('logs-output').innerText = JSON.stringify(data.logs, null, 2);
      } catch (e) {
        document.getElementById('logs-output').innerText = 'Lỗi tải log.';
      }
      updateStats();
    }

    function setSearch(q) {
      document.getElementById('search-q').value = q;
    }

    function setReverse(lat, lon, zoom) {
      document.getElementById('reverse-lat').value = lat;
      document.getElementById('reverse-lon').value = lon;
      document.getElementById('reverse-zoom').value = zoom;
    }

    async function executeSearch() {
      const q = document.getElementById('search-q').value;
      const limit = document.getElementById('search-limit').value;
      const country = document.getElementById('search-country').value;
      const out = document.getElementById('search-output');
      out.innerText = 'Đang gửi request...';

      try {
        const res = await fetch(`/api/v1/geocode/search?q=${encodeURIComponent(q)}&limit=${limit}&country=${country}`);
        const data = await res.json();
        out.innerText = JSON.stringify(data, null, 2);
      } catch (err) {
        out.innerText = 'Lỗi kết nối: ' + err.message;
      }
      fetchLogs();
    }

    async function executeReverse() {
      const lat = document.getElementById('reverse-lat').value;
      const lon = document.getElementById('reverse-lon').value;
      const zoom = document.getElementById('reverse-zoom').value;
      const out = document.getElementById('reverse-output');
      out.innerText = 'Đang gửi request...';

      try {
        const res = await fetch(`/api/v1/geocode/reverse?lat=${lat}&lon=${lon}&zoom=${zoom}`);
        const data = await res.json();
        out.innerText = JSON.stringify(data, null, 2);
      } catch (err) {
        out.innerText = 'Lỗi kết nối: ' + err.message;
      }
      fetchLogs();
    }

    async function clearCache() {
      await fetch('/api/v1/geocode/cache/clear', { method: 'POST' });
      alert('Đã xóa cache thành công!');
      fetchLogs();
    }

    function clearSearchOutput() { document.getElementById('search-output').innerText = '// Trống'; }
    function clearReverseOutput() { document.getElementById('reverse-output').innerText = '// Trống'; }

    // Initial load
    fetchLogs();
    setInterval(updateStats, 3000);
  </script>
</body>
</html>
"""

SWAGGER_DOCS_HTML = """
<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <title>API Contract Documentation | MID Software</title>
  <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css" />
  <style>
    body { margin: 0; background: #fafafa; }
    .top-banner { background: #1e3a8a; color: white; padding: 14px 20px; font-family: sans-serif; }
    .top-banner a { color: #93c5fd; text-decoration: none; font-weight: bold; }
  </style>
</head>
<body>
  <div class="top-banner">
    <span>MID SOFTWARE | OPENSTREETMAP × NOMINATIM POC (TUẦN 3)</span>
    <span style="float: right;"><a href="/">&larr; Quay lại Demo Dashboard</a></span>
  </div>
  <div id="swagger-ui"></div>
  <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
  <script>
    window.onload = () => {
      window.ui = SwaggerUIBundle({
        url: '/api/v1/openapi.json',
        dom_id: '#swagger-ui',
        deepLinking: true,
        presets: [
          SwaggerUIBundle.presets.apis,
          SwaggerUIBundle.SwaggerUIStandalonePreset
        ],
      });
    };
  </script>
</body>
</html>
"""

@views_bp.route("/", methods=["GET"])
def index():
    return render_template_string(DASHBOARD_HTML)

@views_bp.route("/docs", methods=["GET"])
def swagger_docs():
    return render_template_string(SWAGGER_DOCS_HTML)

