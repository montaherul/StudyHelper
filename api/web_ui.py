"""
HTML/CSS/JavaScript Web Studio interface for LocalStudy on Vercel.
Delivers a rich, modern, glassmorphic web replica of the desktop application.
"""

def get_web_ui_html() -> str:
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>LocalStudy — Offline Lecture Processing & Media Toolkit</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@500;600;700;800&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-dark: #0B0F17;
      --bg-sidebar: #0F172A;
      --bg-card: rgba(30, 41, 59, 0.7);
      --bg-input: #0F172A;
      --border-color: rgba(51, 65, 85, 0.7);
      --accent-blue: #38BDF8;
      --accent-green: #34D399;
      --accent-purple: #A855F7;
      --accent-amber: #FBBF24;
      --text-main: #F8FAFC;
      --text-muted: #94A3B8;
      --text-dim: #64748B;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Inter', sans-serif;
      background: var(--bg-dark);
      color: var(--text-main);
      display: flex;
      height: 100vh;
      overflow: hidden;
    }
    h1, h2, h3, h4, .brand-title {
      font-family: 'Outfit', sans-serif;
    }
    /* Sidebar */
    .sidebar {
      width: 260px;
      background: var(--bg-sidebar);
      border-right: 1px solid var(--border-color);
      display: flex;
      flex-direction: column;
      flex-shrink: 0;
    }
    .brand-box {
      padding: 24px 20px;
      border-bottom: 1px solid var(--border-color);
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .brand-icon {
      font-size: 26px;
      background: linear-gradient(135deg, #0284C7, #38BDF8);
      width: 44px;
      height: 44px;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 12px;
      box-shadow: 0 4px 12px rgba(56, 189, 248, 0.25);
    }
    .brand-title {
      font-size: 19px;
      font-weight: 800;
      color: #FFFFFF;
      letter-spacing: -0.3px;
    }
    .brand-sub {
      font-size: 11px;
      color: var(--accent-blue);
      font-weight: 500;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
    .nav-list {
      padding: 16px 12px;
      list-style: none;
      display: flex;
      flex-direction: column;
      gap: 4px;
      flex: 1;
      overflow-y: auto;
    }
    .nav-btn {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 10px 14px;
      border-radius: 10px;
      color: var(--text-muted);
      text-decoration: none;
      font-size: 13.5px;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.15s ease;
      border: 1px solid transparent;
    }
    .nav-btn:hover {
      background: rgba(30, 41, 59, 0.6);
      color: var(--text-main);
    }
    .nav-btn.active {
      background: rgba(56, 189, 248, 0.12);
      color: var(--accent-blue);
      border-color: rgba(56, 189, 248, 0.35);
      font-weight: 600;
    }
    .sidebar-footer {
      padding: 16px 20px;
      border-top: 1px solid var(--border-color);
      font-size: 11px;
      color: var(--text-dim);
      display: flex;
      flex-direction: column;
      gap: 4px;
    }
    .badge-offline {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-size: 11px;
      font-weight: 600;
      color: var(--accent-green);
      background: rgba(52, 211, 153, 0.12);
      padding: 3px 8px;
      border-radius: 6px;
      width: fit-content;
      margin-top: 4px;
    }
    /* Main Content */
    .main-content {
      flex: 1;
      display: flex;
      flex-direction: column;
      overflow-y: auto;
      background: radial-gradient(circle at top right, rgba(56, 189, 248, 0.05), transparent 400px), var(--bg-dark);
    }
    .topbar {
      padding: 16px 32px;
      border-bottom: 1px solid var(--border-color);
      display: flex;
      align-items: center;
      justify-content: space-between;
      background: rgba(15, 23, 42, 0.6);
      backdrop-filter: blur(12px);
    }
    .topbar-title {
      font-size: 18px;
      font-weight: 700;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .topbar-actions {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .pill-link {
      font-size: 12px;
      font-weight: 600;
      color: var(--text-muted);
      background: rgba(30, 41, 59, 0.8);
      border: 1px solid var(--border-color);
      padding: 6px 12px;
      border-radius: 8px;
      text-decoration: none;
      transition: all 0.15s;
    }
    .pill-link:hover {
      color: #FFF;
      border-color: var(--accent-blue);
    }
    .content-body {
      padding: 28px 32px;
      max-width: 1150px;
    }
    .tab-section {
      display: none;
      animation: fadeIn 0.2s ease-in-out;
    }
    .tab-section.active {
      display: block;
    }
    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(6px); }
      to { opacity: 1; transform: translateY(0); }
    }
    /* Cards */
    .card {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 14px;
      padding: 22px 24px;
      margin-bottom: 20px;
      backdrop-filter: blur(12px);
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
    }
    .card-title {
      font-size: 16px;
      font-weight: 700;
      color: var(--text-main);
      margin-bottom: 6px;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .card-subtitle {
      font-size: 13px;
      color: var(--text-muted);
      margin-bottom: 18px;
      line-height: 1.5;
    }
    /* Inputs & Buttons */
    .input-group {
      display: flex;
      gap: 10px;
      margin-bottom: 14px;
    }
    .text-input {
      flex: 1;
      background: var(--bg-input);
      border: 1px solid var(--border-color);
      border-radius: 10px;
      padding: 10px 14px;
      color: #FFF;
      font-size: 13.5px;
      outline: none;
      transition: border 0.15s;
    }
    .text-input:focus {
      border-color: var(--accent-blue);
      box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.15);
    }
    .btn {
      padding: 10px 18px;
      border-radius: 10px;
      font-size: 13.5px;
      font-weight: 600;
      cursor: pointer;
      border: none;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      transition: all 0.15s;
    }
    .btn-primary {
      background: linear-gradient(135deg, #0284C7, #0EA5E9);
      color: #FFF;
      box-shadow: 0 2px 8px rgba(14, 165, 233, 0.3);
    }
    .btn-primary:hover {
      background: linear-gradient(135deg, #0369A1, #0284C7);
    }
    .btn-secondary {
      background: rgba(30, 41, 59, 0.8);
      color: var(--text-main);
      border: 1px solid var(--border-color);
    }
    .btn-secondary:hover {
      background: rgba(51, 65, 85, 0.8);
      border-color: #64748B;
    }
    /* Platform Badge */
    .platform-badge {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 8px 14px;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 600;
      background: rgba(15, 23, 42, 0.8);
      border: 1px solid var(--border-color);
      margin-bottom: 14px;
    }
    .chip-container {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 10px;
    }
    .chip {
      font-size: 12px;
      padding: 4px 10px;
      border-radius: 6px;
      background: rgba(30, 41, 59, 0.6);
      border: 1px solid var(--border-color);
      color: var(--text-muted);
    }
    /* Grid & Options */
    .grid-2 {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
    }
    .grid-3 {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 14px;
    }
    .feature-card {
      background: rgba(15, 23, 42, 0.6);
      border: 1px solid var(--border-color);
      border-radius: 10px;
      padding: 16px;
    }
    .feature-title {
      font-size: 14px;
      font-weight: 700;
      color: var(--text-main);
      margin-bottom: 6px;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .feature-desc {
      font-size: 12.5px;
      color: var(--text-muted);
      line-height: 1.45;
    }
    /* Checkbox & Options */
    .option-row {
      display: flex;
      align-items: center;
      gap: 10px;
      font-size: 13px;
      color: var(--text-main);
      margin-bottom: 10px;
    }
    .option-row input[type="checkbox"] {
      width: 16px;
      height: 16px;
      accent-color: var(--accent-blue);
      cursor: pointer;
    }
    .preview-box {
      background: #000;
      border: 1px solid var(--border-color);
      border-radius: 10px;
      padding: 20px;
      text-align: center;
      margin-top: 14px;
    }
    .code-box {
      background: #020617;
      border: 1px solid #1E293B;
      border-radius: 8px;
      padding: 12px 14px;
      font-family: monospace;
      font-size: 12px;
      color: var(--accent-blue);
      overflow-x: auto;
    }
  </style>
</head>
<body>

  <!-- Left Sidebar -->
  <aside class="sidebar">
    <div class="brand-box">
      <div class="brand-icon">📚</div>
      <div>
        <div class="brand-title">LocalStudy</div>
        <div class="brand-sub">Study Toolkit & API</div>
      </div>
    </div>

    <ul class="nav-list">
      <li><a class="nav-btn active" onclick="showTab('dashboard')"><span>📊</span> Dashboard</a></li>
      <li><a class="nav-btn" onclick="showTab('downloader')"><span>🎬</span> Media Downloader</a></li>
      <li><a class="nav-btn" onclick="showTab('screenshots')"><span>📷</span> Screenshots & PDF</a></li>
      <li><a class="nav-btn" onclick="showTab('pdf-builder')"><span>📕</span> PDF Study Guide</a></li>
      <li><a class="nav-btn" onclick="showTab('transcriber')"><span>🎙️</span> Offline Transcriber</a></li>
      <li><a class="nav-btn" onclick="showTab('api-explorer')"><span>⚡</span> API Explorer</a></li>
    </ul>

    <div class="sidebar-footer">
      <div>LocalStudy Suite v1.0.0</div>
      <div class="badge-offline">● 100% Offline Core</div>
      <div style="margin-top: 6px;">Zero Cloud APIs • Local Inference</div>
    </div>
  </aside>

  <!-- Main Content View -->
  <main class="main-content">
    <header class="topbar">
      <div class="topbar-title" id="page-title">📊 Dashboard & System Overview</div>
      <div class="topbar-actions">
        <a href="/docs" target="_blank" class="pill-link">📖 Swagger UI</a>
        <a href="/health" target="_blank" class="pill-link">💚 Health: OK</a>
      </div>
    </header>

    <div class="content-body">

      <!-- Tab: Dashboard -->
      <section id="tab-dashboard" class="tab-section active">
        <div class="card">
          <div class="card-title">🚀 Welcome to LocalStudy Suite</div>
          <div class="card-subtitle">
            LocalStudy transforms educational videos and lecture audio into structured study guides—periodic screenshot PDFs with clean covers, timestamped transcripts, and a searchable local knowledge base—running 100% offline on your computer.
          </div>
          <div class="grid-3">
            <div class="feature-card">
              <div class="feature-title">🎬 Multi-Platform Downloader</div>
              <div class="feature-desc">Universal downloader supporting YouTube, TikTok, Instagram, Facebook, X, Reddit, Vimeo, direct streams, and web media.</div>
            </div>
            <div class="feature-card">
              <div class="feature-title">📷 Clean Slide Extraction</div>
              <div class="feature-desc">Captures pristine video frames every N seconds with zero burned-in text. Timestamps belong strictly to the compiled study PDF.</div>
            </div>
            <div class="feature-card">
              <div class="feature-title">🎙️ Whisper AI Transcription</div>
              <div class="feature-desc">High-speed local speech-to-text with CTranslate2 INT8 acceleration. No API keys, no subscription, zero data loss.</div>
            </div>
          </div>
        </div>

        <div class="card">
          <div class="card-title">🖥️ Dual-Mode Architecture</div>
          <div class="card-subtitle">LocalStudy operates in two harmonious modes:</div>
          <div class="grid-2">
            <div class="feature-card" style="border-left: 3px solid var(--accent-blue);">
              <div class="feature-title">💻 Local Desktop Application</div>
              <div class="feature-desc">
                Launch with <code>python app.py</code> for the full high-performance PySide6 GUI with GPU acceleration and local SQLite indexing.
              </div>
            </div>
            <div class="feature-card" style="border-left: 3px solid var(--accent-green);">
              <div class="feature-title">🌐 Web & Serverless API</div>
              <div class="feature-desc">
                Powered by FastAPI on Vercel at <code>/api</code> with automated endpoint discovery and Swagger documentation.
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Tab: Media Downloader -->
      <section id="tab-downloader" class="tab-section">
        <div class="card">
          <div class="card-title">🎬 Universal Media Downloader</div>
          <div class="card-subtitle">
            Paste any link from YouTube, TikTok, Instagram, Facebook, X/Twitter, Reddit, Vimeo, Twitch, or web media. The system auto-detects the platform and stream quality.
          </div>

          <div class="input-group">
            <input type="text" id="dl-url" class="text-input" placeholder="Paste any video URL (YouTube, TikTok, Facebook, Instagram, direct MP4)..." oninput="detectUrlPlatform(this.value)">
            <button class="btn btn-primary" onclick="simulateAnalyze()">⚡ Analyze Link</button>
          </div>

          <div id="platform-badge" class="platform-badge" style="display: none;">
            <span id="badge-icon">🌐</span>
            <span id="badge-name">Web Media</span>
            <span style="color: var(--text-dim);">•</span>
            <span id="badge-tag" style="color: var(--accent-blue);">Universal Web Video</span>
          </div>

          <div class="chip-container">
            <div class="chip">🔴 YouTube</div>
            <div class="chip">🎵 TikTok</div>
            <div class="chip">📸 Instagram</div>
            <div class="chip">🔵 Facebook</div>
            <div class="chip">🔲 X (Twitter)</div>
            <div class="chip">🟠 Reddit</div>
            <div class="chip">⚡ Direct MP4/HLS</div>
            <div class="chip">🌐 Universal Web</div>
          </div>
        </div>

        <div class="card" id="dl-result-card" style="display: none;">
          <div class="card-title">📥 Stream Metadata & Download Options</div>
          <div id="dl-result-content" class="code-box"></div>
        </div>
      </section>

      <!-- Tab: Screenshots & Auto-PDF -->
      <section id="tab-screenshots" class="tab-section">
        <div class="card">
          <div class="card-title">📷 Slide Extraction & Auto-PDF Studio</div>
          <div class="card-subtitle">
            Extract periodic lecture slides and instantly compile study-ready PDFs.
          </div>

          <div class="option-row">
            <input type="checkbox" id="chk-clean-ss" checked disabled>
            <label for="chk-clean-ss"><strong>🛡️ Clean Screenshots Guarantee:</strong> Raw frames are saved 100% pure (zero burned-in text/overlays).</label>
          </div>

          <div class="option-row">
            <input type="checkbox" id="chk-pdf-cover" checked>
            <label for="chk-pdf-cover"><strong>PDF 1st Page:</strong> Show Project Name only (clean, modern title cover without metadata tables).</label>
          </div>

          <div class="option-row">
            <input type="checkbox" id="chk-pdf-time" checked>
            <label for="chk-pdf-time"><strong>PDF Slides:</strong> Show timestamp only (<code>⏱ HH:MM:SS</code>) under each slide.</label>
          </div>

          <div style="margin-top: 16px;">
            <div class="card-subtitle">Slide Interval Presets:</div>
            <div class="chip-container">
              <div class="chip" style="color: var(--accent-blue); cursor: pointer;">10 Seconds</div>
              <div class="chip" style="color: var(--accent-blue); cursor: pointer; border-color: var(--accent-blue);">30 Seconds (Recommended)</div>
              <div class="chip" style="color: var(--accent-blue); cursor: pointer;">60 Seconds</div>
              <div class="chip" style="color: var(--accent-blue); cursor: pointer;">Custom Interval</div>
            </div>
          </div>
        </div>
      </section>

      <!-- Tab: PDF Builder -->
      <section id="tab-pdf-builder" class="tab-section">
        <div class="card">
          <div class="card-title">📕 PDF Study Guide Layouts</div>
          <div class="card-subtitle">
            Choose your layout preset for optimal readability and printing:
          </div>

          <div class="grid-3">
            <div class="feature-card" style="text-align: center;">
              <div style="font-size: 32px; margin-bottom: 8px;">📄</div>
              <div class="feature-title" style="justify-content: center;">1-Up Layout</div>
              <div class="feature-desc">1 large slide per page with student lecture notes area.</div>
            </div>
            <div class="feature-card" style="text-align: center; border-color: var(--accent-blue);">
              <div style="font-size: 32px; margin-bottom: 8px;">📑</div>
              <div class="feature-title" style="justify-content: center; color: var(--accent-blue);">2-Up Layout (Recommended)</div>
              <div class="feature-desc">2 slides per page vertically stacked with timestamp badges.</div>
            </div>
            <div class="feature-card" style="text-align: center;">
              <div style="font-size: 32px; margin-bottom: 8px;">📰</div>
              <div class="feature-title" style="justify-content: center;">4-Up Layout</div>
              <div class="feature-desc">4 slides per page in a 2x2 grid for compact study handouts.</div>
            </div>
          </div>
        </div>
      </section>

      <!-- Tab: Transcriber -->
      <section id="tab-transcriber" class="tab-section">
        <div class="card">
          <div class="card-title">🎙️ Offline AI Speech-to-Text</div>
          <div class="card-subtitle">
            Transcribes lecture audio into timestamped transcripts, SRT, and VTT subtitles with faster-whisper.
          </div>
          <div class="grid-2">
            <div class="feature-card">
              <div class="feature-title">🧠 Supported Model Tiers</div>
              <div class="feature-desc">
                • <strong>Tiny (~75 MB)</strong>: Ultra-fast transcription<br>
                • <strong>Base (~145 MB)</strong>: Balanced standard tier<br>
                • <strong>Small (~460 MB)</strong>: Multilingual & technical accuracy<br>
                • <strong>Medium / Large</strong>: Maximum accuracy
              </div>
            </div>
            <div class="feature-card">
              <div class="feature-title">🔒 100% Privacy Guarantee</div>
              <div class="feature-desc">
                All voice audio is processed locally on your hardware. Zero audio packets are uploaded or sent across the internet.
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Tab: API Explorer -->
      <section id="tab-api-explorer" class="tab-section">
        <div class="card">
          <div class="card-title">⚡ REST API Endpoints</div>
          <div class="card-subtitle">
            LocalStudy provides a full REST API for programmatic interaction:
          </div>
          <div class="code-box">
GET  /                    → Web Studio & App Overview<br>
GET  /health              → Health status ({"status": "healthy"})<br>
GET  /api/info            → Service metadata & endpoint discovery<br>
GET  /docs                → Interactive Swagger API documentation<br>
GET  /redoc               → ReDoc API reference
          </div>
          <div style="margin-top: 14px;">
            <a href="/docs" target="_blank" class="btn btn-primary">🚀 Launch Interactive Swagger UI</a>
          </div>
        </div>
      </section>

    </div>
  </main>

  <script>
    function showTab(tabId) {
      document.querySelectorAll('.tab-section').forEach(el => el.classList.remove('active'));
      document.querySelectorAll('.nav-btn').forEach(el => el.classList.remove('active'));

      const targetTab = document.getElementById('tab-' + tabId);
      if (targetTab) targetTab.classList.add('active');

      const titleMap = {
        'dashboard': '📊 Dashboard & System Overview',
        'downloader': '🎬 Universal Media Downloader',
        'screenshots': '📷 Slide Extraction & Auto-PDF Studio',
        'pdf-builder': '📕 PDF Study Guide Layouts',
        'transcriber': '🎙️ Offline AI Speech-to-Text',
        'api-explorer': '⚡ REST API Explorer'
      };
      document.getElementById('page-title').innerText = titleMap[tabId] || 'LocalStudy';
      event.currentTarget.classList.add('active');
    }

    function detectUrlPlatform(url) {
      const u = url.toLowerCase().trim();
      const badge = document.getElementById('platform-badge');
      const icon = document.getElementById('badge-icon');
      const name = document.getElementById('badge-name');
      const tag = document.getElementById('badge-tag');

      if (!u || (!u.startsWith('http://') && !u.startsWith('https://'))) {
        badge.style.display = 'none';
        return;
      }

      badge.style.display = 'inline-flex';

      if (u.includes('youtube.com') || u.includes('youtu.be')) {
        icon.innerText = '🔴'; name.innerText = 'YouTube'; tag.innerText = 'Video / Short / Playlist';
      } else if (u.includes('tiktok.com')) {
        icon.innerText = '🎵'; name.innerText = 'TikTok'; tag.innerText = 'Direct HD Reel';
      } else if (u.includes('instagram.com') || u.includes('instagr.am')) {
        icon.innerText = '📸'; name.innerText = 'Instagram'; tag.innerText = 'Reel / Post';
      } else if (u.includes('facebook.com') || u.includes('fb.watch')) {
        icon.innerText = '🔵'; name.innerText = 'Facebook'; tag.innerText = 'Video / Watch';
      } else if (u.includes('twitter.com') || u.includes('x.com') || u.includes('t.co')) {
        icon.innerText = '🔲'; name.innerText = 'X (Twitter)'; tag.innerText = 'Media Post';
      } else if (u.includes('reddit.com') || u.includes('redd.it')) {
        icon.innerText = '🟠'; name.innerText = 'Reddit'; tag.innerText = 'Video Stream';
      } else if (u.includes('.mp4') || u.includes('.m3u8') || u.includes('.mpd')) {
        icon.innerText = '⚡'; name.innerText = 'Direct Stream'; tag.innerText = 'HLS / DASH / MP4 Manifest';
      } else {
        icon.innerText = '🌐'; name.innerText = 'Web Media'; tag.innerText = 'Universal Web Video';
      }
    }

    function simulateAnalyze() {
      const url = document.getElementById('dl-url').value.trim();
      if (!url) {
        alert('Please paste a video URL first.');
        return;
      }
      const card = document.getElementById('dl-result-card');
      const content = document.getElementById('dl-result-content');
      card.style.display = 'block';
      content.innerHTML = `Analyzing URL: <strong>${url}</strong><br>` +
        `Detected: <strong>${document.getElementById('badge-name').innerText}</strong><br>` +
        `Available Formats: [1080p Full HD, 720p HD, 480p, MP3 Audio 320kbps]<br>` +
        `Status: Ready to process in desktop app or serverless worker.`;
    }
  </script>
</body>
</html>
"""
