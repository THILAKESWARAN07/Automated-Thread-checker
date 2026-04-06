const API_BASE = "http://127.0.0.1:8000";

// ============ DOM ELEMENTS ============
const liveFeed = document.getElementById("liveFeed");
const overlayPreview = document.getElementById("overlayPreview");
const statusLine = document.getElementById("statusLine");
const cameraStatusText = document.getElementById("cameraStatusText");
const cameraStatusDot = document.querySelector(".status-dot");

const captureBtn = document.getElementById("captureBtn");
const analyzeBtn = document.getElementById("analyzeBtn");
const qualityCheckBtn = document.getElementById("qualityCheckBtn");
const batchUploadBtn = document.getElementById("batchUploadBtn");
const autoBtn = document.getElementById("autoBtn");
const exportBtn = document.getElementById("exportBtn");
const saveSettingsBtn = document.getElementById("saveSettingsBtn");
const performanceBtn = document.getElementById("performanceBtn");
const refreshLogsBtn = document.getElementById("refreshLogsBtn");
const toggleCameraBtn = document.getElementById("toggleCameraBtn");

// Camera controls
const cameraSourceSelect = document.getElementById("cameraSourceSelect");
const customCameraUrl = document.getElementById("customCameraUrl");
const scanCamerasBtn = document.getElementById("scanCamerasBtn");
const testCameraBtn = document.getElementById("testCameraBtn");

// Settings
const threadTypeSelect = document.getElementById("threadTypeSelect");
const toleranceInput = document.getElementById("toleranceInput");
const refLengthInput = document.getElementById("refLengthInput");
const refPixelsInput = document.getElementById("refPixelsInput");

// Results display
const finalBadge = document.getElementById("finalBadge");
const threadTypeValue = document.getElementById("threadTypeValue");
const pitchValue = document.getElementById("pitchValue");
const diameterValue = document.getElementById("diameterValue");
const aiValue = document.getElementById("aiValue");
const ruleValue = document.getElementById("ruleValue");
const timeValue = document.getElementById("timeValue");
const qualityResultBox = document.getElementById("qualityResultBox");
const qualityDetails = document.getElementById("qualityDetails");

// Stats
const totalCount = document.getElementById("totalCount");
const passPct = document.getElementById("passPct");
const failPct = document.getElementById("failPct");
const avgTime = document.getElementById("avgTime");
const logsBody = document.getElementById("logsBody");

// Batch processing
const selectBatchFilesBtn = document.getElementById("selectBatchFilesBtn");
const batchFilesInput = document.getElementById("batchFilesInput");
const batchFilesCount = document.getElementById("batchFilesCount");
const clearBatchFilesBtn = document.getElementById("clearBatchFilesBtn");
const batchPreviewGrid = document.getElementById("batchPreviewGrid");
const batchThreadType = document.getElementById("batchThreadType");
const batchTolerance = document.getElementById("batchTolerance");
const processBatchBtn = document.getElementById("processBatchBtn");
const batchProgress = document.getElementById("batchProgress");
const batchProgressFill = document.getElementById("batchProgressFill");
const batchProgressText = document.getElementById("batchProgressText");
const batchResults = document.getElementById("batchResults");
const batchResultsDetails = document.getElementById("batchResultsDetails");

// Quality indicator
const qualityIndicator = document.getElementById("qualityIndicator");
const qualityBar = document.getElementById("qualityBar");
const qualityScore = document.getElementById("qualityScore");
const qualityRecommendation = document.getElementById("qualityRecommendation");

// Modals
const cameraScanModal = document.getElementById("cameraScanModal");
const cameraScanResults = document.getElementById("cameraScanResults");
const performanceModal = document.getElementById("performanceModal");
const performanceDetails = document.getElementById("performanceDetails");

let autoTimer = null;
let passFailChart;
let trendChart;
let selectedBatchFiles = [];
let cameraEnabled = true;
let previewObjectUrls = [];

// ============ UTILITY FUNCTIONS ============
function setStatus(message) {
  statusLine.textContent = message;
  console.log("[STATUS]", message);
}

function updateCameraStatus(available, sourceLabel) {
  if (available) {
    cameraStatusDot.classList.add("active");
    cameraStatusText.textContent = sourceLabel ? `Connected (${sourceLabel})` : "Connected";
  } else {
    cameraStatusDot.classList.remove("active");
    cameraStatusText.textContent = "Disconnected";
  }
}

function startLiveFeed() {
  liveFeed.src = `${API_BASE}/video_feed?ts=${Date.now()}`;
}

function stopLiveFeed() {
  liveFeed.src = "";
  liveFeed.alt = "Camera off";
}

function setCameraToggleUI(active, sourceLabel) {
  cameraEnabled = active;
  if (toggleCameraBtn) {
    toggleCameraBtn.textContent = active ? "Turn Camera Off" : "Turn Camera On";
  }
  if (active) {
    startLiveFeed();
  } else {
    stopLiveFeed();
  }
  updateCameraStatus(active, sourceLabel);
}

function getSelectedCameraSource() {
  let source = cameraSourceSelect.value;
  if (source === "custom") {
    source = customCameraUrl.value.trim();
  }
  return source;
}

async function fetchCameraStatus() {
  try {
    const res = await fetch(`${API_BASE}/camera/status`);
    if (!res.ok) throw new Error("Status fetch failed");
    const data = await res.json();
    const label = data.current_source || data.source;
    setCameraToggleUI(Boolean(data.active), label);
  } catch (err) {
    console.warn("Camera status error", err);
    setCameraToggleUI(false);
  }
}

// ============ CAPTURE & ANALYZE ============
async function captureFrame() {
  setStatus("Capturing frame...");
  const res = await fetch(`${API_BASE}/capture`, { method: "POST" });
  if (!res.ok) {
    throw new Error("Capture failed");
  }
  const data = await res.json();
  setStatus(`✓ Captured: ${data.image_path}`);
}

async function analyzeFrame() {
  setStatus("Analyzing frame...");

  const payload = {
    thread_type: threadTypeSelect.value,
    tolerance_pct: Number(toleranceInput.value),
  };

  const refLength = Number(refLengthInput.value);
  const refPixels = Number(refPixelsInput.value);
  if (refLength > 0 && refPixels > 0) {
    payload.reference_length_mm = refLength;
    payload.reference_pixels = refPixels;
  }

  const res = await fetch(`${API_BASE}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const error = await res.text();
    throw new Error(error || "Analyze failed");
  }

  const data = await res.json();
  renderResult(data);
  setStatus(`✓ Inspection done: ${data.final_decision}`);
  await refreshStats();
}

async function checkImageQuality() {
  setStatus("Checking image quality...");
  const res = await fetch(`${API_BASE}/image/quality`);
  if (!res.ok) {
    throw new Error("Quality check failed");
  }
  
  const quality = await res.json();
  displayQualityIndicator(quality);
  setStatus(`✓ Quality Score: ${quality.quality_score}/100`);
}

function displayQualityIndicator(quality) {
  qualityIndicator.style.display = "block";
  qualityBar.style.width = quality.quality_score + "%";
  qualityScore.textContent = `${quality.quality_score}/100`;
  qualityRecommendation.textContent = quality.recommendation;
  
  // Color code the bar
  if (quality.quality_score >= 80) {
    qualityBar.style.background = "linear-gradient(to right, #51cf66)";
  } else if (quality.quality_score >= 60) {
    qualityBar.style.background = "linear-gradient(to right, #ffd700)";
  } else {
    qualityBar.style.background = "linear-gradient(to right, #ff6b6b)";
  }
}

function renderResult(result) {
  if (!result || !result.final_decision) return;

  finalBadge.className = `badge ${result.final_decision === "PASS" ? "pass" : "fail"}`;
  finalBadge.textContent = result.final_decision;

  threadTypeValue.textContent = result.thread_type || "-";
  pitchValue.textContent = Number(result.pitch_mm || 0).toFixed(3);
  diameterValue.textContent = Number(result.diameter_mm || 0).toFixed(3);
  aiValue.textContent = `${result.ai_result || "-"} (${(result.ai_confidence || 0).toFixed(2)})`;
  ruleValue.textContent = result.rule_result || "-";
  timeValue.textContent = (result.analysis_time_ms || 0).toFixed(0) + "ms";

  if (result.overlay_image_b64) {
    overlayPreview.src = `data:image/jpeg;base64,${result.overlay_image_b64}`;
  }

  // Display quality if available
  if (result.image_quality) {
    qualityResultBox.style.display = "block";
    qualityDetails.innerHTML = `
      <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; margin-top: 8px; font-size: 0.85rem;">
        <div><strong>Sharpness:</strong> ${result.image_quality.sharpness}</div>
        <div><strong>Brightness:</strong> ${result.image_quality.brightness}</div>
        <div><strong>Contrast:</strong> ${result.image_quality.contrast}</div>
        <div><strong>Score:</strong> ${result.image_quality.quality_score}/100</div>
        <div colspan="2"><strong>Recommendation:</strong> ${result.image_quality.recommendation}</div>
      </div>
    `;
  }
}

// ============ BATCH PROCESSING ============
selectBatchFilesBtn.addEventListener("click", () => {
  batchFilesInput.click();
});

batchFilesInput.addEventListener("change", (e) => {
  selectedBatchFiles = Array.from(e.target.files);
  updateBatchFilesCount();
  renderBatchPreviews();
});

function updateBatchFilesCount() {
  batchFilesCount.textContent = `${selectedBatchFiles.length} file(s) selected`;
  if (clearBatchFilesBtn) {
    clearBatchFilesBtn.disabled = selectedBatchFiles.length === 0;
  }
}

function clearBatchFiles() {
  selectedBatchFiles = [];
  if (batchFilesInput) {
    batchFilesInput.value = "";
  }
  updateBatchFilesCount();
  renderBatchPreviews();
}

function renderBatchPreviews() {
  if (!batchPreviewGrid) return;

  previewObjectUrls.forEach((url) => URL.revokeObjectURL(url));
  previewObjectUrls = [];
  batchPreviewGrid.innerHTML = "";

  if (selectedBatchFiles.length === 0) {
    return;
  }

  selectedBatchFiles.forEach((file, index) => {
    const objectUrl = URL.createObjectURL(file);
    previewObjectUrls.push(objectUrl);

    const card = document.createElement("div");
    card.className = "batch-preview-card";

    const removeBtn = document.createElement("button");
    removeBtn.type = "button";
    removeBtn.className = "batch-preview-remove";
    removeBtn.textContent = "x";
    removeBtn.setAttribute("aria-label", `Remove ${file.name}`);
    removeBtn.addEventListener("click", () => {
      selectedBatchFiles.splice(index, 1);
      updateBatchFilesCount();
      renderBatchPreviews();
    });

    const img = document.createElement("img");
    img.src = objectUrl;
    img.alt = file.name;

    const name = document.createElement("span");
    name.textContent = file.name;

    card.appendChild(removeBtn);
    card.appendChild(img);
    card.appendChild(name);
    batchPreviewGrid.appendChild(card);
  });
}

async function processBatch() {
  if (selectedBatchFiles.length === 0) {
    setStatus("No files selected for batch processing");
    return;
  }

  processBatchBtn.disabled = true;
  setStatus(`Processing ${selectedBatchFiles.length} images...`);
  batchProgress.style.display = "block";
  batchProgressText.textContent = `Processing ${selectedBatchFiles.length} image(s)...`;
  batchResults.style.display = "none";

  const formData = new FormData();
  selectedBatchFiles.forEach(file => {
    formData.append("images", file);
  });
  formData.append("thread_type", batchThreadType.value);
  formData.append("tolerance_pct", batchTolerance.value);

  const controller = new AbortController();
  const timeoutMs = 120000;
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
  let completed = false;

  try {
    const res = await fetch(`${API_BASE}/batch/process`, {
      method: "POST",
      body: formData,
      signal: controller.signal,
    });

    if (!res.ok) {
      let detail = "Batch processing failed";
      try {
        const errData = await res.json();
        if (errData?.detail) {
          detail = typeof errData.detail === "string" ? errData.detail : JSON.stringify(errData.detail);
        }
      } catch {
        // Keep default detail when response is not JSON.
      }
      throw new Error(detail);
    }

    const data = await res.json();
    displayBatchResults(data);
    setStatus(`✓ Batch processing complete: Pass ${data.summary.pass}, Fail ${data.summary.fail}`);
    completed = true;
  } catch (err) {
    if (err.name === "AbortError") {
      setStatus("✗ Batch error: Request timed out after 120s. Please try fewer/lower-size images.");
    } else {
      setStatus(`✗ Batch error: ${err.message}`);
    }
  } finally {
    clearTimeout(timeoutId);
    processBatchBtn.disabled = false;
    if (!completed) {
      batchProgress.style.display = "none";
    }
  }
}

function displayBatchResults(data) {
  batchProgress.style.display = "none";
  batchResults.style.display = "block";

  const summary = data.summary;
  batchResultsDetails.innerHTML = `
    <div style="margin-top: 10px;">
      <p><strong>Total Processed:</strong> ${summary.total}</p>
      <p><strong>Passed:</strong> ${summary.pass} (${summary.pass_percentage}%)</p>
      <p><strong>Failed:</strong> ${summary.fail}</p>
      <p><strong>Failed Uploads:</strong> ${summary.failed_uploads}</p>
    </div>
  `;
}

processBatchBtn.addEventListener("click", processBatch);
if (clearBatchFilesBtn) {
  clearBatchFilesBtn.addEventListener("click", clearBatchFiles);
}

// ============ CAMERA MANAGEMENT ============
cameraSourceSelect.addEventListener("change", (e) => {
  if (e.target.value === "custom") {
    customCameraUrl.style.display = "block";
  } else {
    customCameraUrl.style.display = "none";
  }
});

scanCamerasBtn.addEventListener("click", async () => {
  setStatus("Scanning for available cameras...");
  try {
    const res = await fetch(`${API_BASE}/cameras/available`);
    if (!res.ok) throw new Error("Camera scan failed");
    
    const data = await res.json();
    displayCameraScanResults(data.cameras);
    cameraScanModal.style.display = "block";
    setStatus("✓ Camera scan complete");
  } catch (err) {
    setStatus(`✗ Scan error: ${err.message}`);
  }
});

if (testCameraBtn) {
  testCameraBtn.addEventListener("click", async () => {
    const source = getSelectedCameraSource();
    if (!source) {
      setStatus("✗ Camera test error: select a camera source first");
      return;
    }

    setStatus(`Testing camera source ${source}...`);
    try {
      const res = await fetch(`${API_BASE}/cameras/test?url=${encodeURIComponent(source)}`, {
        method: "POST",
      });

      if (!res.ok) {
        let detail = "Unable to test camera";
        try {
          const errData = await res.json();
          if (errData?.detail) {
            detail = String(errData.detail);
          }
        } catch {
          // Keep default message when the response is not JSON.
        }
        throw new Error(detail);
      }

      const data = await res.json();
      const activeSource = data.current_source || data.source || source;
      setCameraToggleUI(true, activeSource);
      setStatus(`✓ Camera test successful: ${activeSource}`);
    } catch (err) {
      setStatus(`✗ Camera test error: ${err.message}`);
    }
  });
}


async function updateCameraSource(source) {
  const payload = { camera_source: source };
  const res = await fetch(`${API_BASE}/settings`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok) throw new Error("Failed to update camera");
  
  const data = await res.json();
  if (data.camera_ok) {
    setStatus("✓ Camera updated and connected");
    setCameraToggleUI(true, source);
  } else {
    setCameraToggleUI(false);
  }
}

function displayCameraScanResults(cameras) {
  let html = "<div style='display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 10px;'>";
  
  if (cameras.length === 0) {
    html += "<p>No cameras found. You can also connect via IP camera URL.</p>";
  } else {
    cameras.forEach(cam => {
      html += `
        <div style='border: 1px solid #ddd; padding: 10px; border-radius: 8px; cursor: pointer;' onclick="selectCamera('${cam.id}')">
          <strong>${cam.name}</strong>
          <p style='margin: 5px 0; font-size: 0.85rem; color: #666;'>Type: ${cam.type}</p>
          <p style='margin: 5px 0; font-size: 0.85rem; color: #666;'>Status: ${cam.status}</p>
          ${cam.resolution ? `<p style='margin: 5px 0; font-size: 0.85rem;'>${cam.resolution.width}x${cam.resolution.height}</p>` : ''}
        </div>
      `;
    });
  }
  
  html += "</div>";
  cameraScanResults.innerHTML = html;
}

window.selectCamera = async function(camId) {
  cameraScanModal.style.display = "none";
  await updateCameraSource(String(camId));
};

// Close modal on X click
document.querySelectorAll(".close").forEach(btn => {
  btn.addEventListener("click", function() {
    this.closest(".modal").style.display = "none";
  });
});

// ============ CHARTS ============
function buildCharts() {
  const passFailCtx = document.getElementById("passFailChart");
  const trendCtx = document.getElementById("trendChart");

  passFailChart = new Chart(passFailCtx, {
    type: "pie",
    data: {
      labels: ["PASS", "FAIL"],
      datasets: [{ data: [0, 0], backgroundColor: ["#16a34a", "#e11d48"] }],
    },
    options: { responsive: true, plugins: { legend: { position: "bottom" } } },
  });

  trendChart = new Chart(trendCtx, {
    type: "line",
    data: {
      labels: [],
      datasets: [
        { label: "Pass", data: [], borderColor: "#15803d", backgroundColor: "#dcfce7", tension: 0.3 },
        { label: "Fail", data: [], borderColor: "#be123c", backgroundColor: "#ffe4e6", tension: 0.3 },
      ],
    },
    options: {
      responsive: true,
      plugins: { legend: { position: "bottom" } },
      scales: { y: { beginAtZero: true, precision: 0 } },
    },
  });
}

function renderLogs(logs) {
  logsBody.innerHTML = "";
  logs.forEach((log) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${log.timestamp || "-"}</td>
      <td>${log.thread_type || "-"}</td>
      <td>${Number(log.pitch_mm || 0).toFixed(3)}</td>
      <td>${Number(log.diameter_mm || 0).toFixed(3)}</td>
      <td>${log.ai_result || "-"}</td>
      <td>${log.final_decision || "-"}</td>
      <td>${log.analysis_time_ms ? Number(log.analysis_time_ms).toFixed(0) : "-"}</td>
    `;
    logsBody.appendChild(tr);
  });
}

async function refreshStats() {
  try {
    const res = await fetch(`${API_BASE}/stats`);
    if (!res.ok) return;

    const stats = await res.json();

    totalCount.textContent = stats.total || 0;
    passPct.textContent = `${Number(stats.pass_percentage || 0).toFixed(1)}%`;
    failPct.textContent = `${Number(stats.fail_percentage || 0).toFixed(1)}%`;
    
    if (stats.performance_metrics) {
      avgTime.textContent = `${stats.performance_metrics.avg_analysis_time_ms.toFixed(0)}ms`;
    }

    passFailChart.data.datasets[0].data = [stats.pass_count || 0, stats.fail_count || 0];
    passFailChart.update();

    const trend = stats.inspection_trend || [];
    trendChart.data.labels = trend.map((r) => r.day);
    trendChart.data.datasets[0].data = trend.map((r) => r.pass_count);
    trendChart.data.datasets[1].data = trend.map((r) => r.fail_count);
    trendChart.update();

    renderLogs(stats.recent_logs || []);
  } catch (err) {
    console.error("Error refreshing stats:", err);
  }
}

async function refreshLatestResult() {
  try {
    const res = await fetch(`${API_BASE}/result`);
    if (!res.ok) return;
    const data = await res.json();
    if (data.final_decision) {
      renderResult(data);
    }
  } catch (err) {
    console.error("Error refreshing result:", err);
  }
}

async function loadSettings() {
  try {
    const res = await fetch(`${API_BASE}/settings`);
    if (!res.ok) return;
    const settings = await res.json();

    if (settings.default_tolerance_pct !== undefined) {
      toleranceInput.value = settings.default_tolerance_pct;
    }

    if (settings.thread_standards) {
      const keys = Object.keys(settings.thread_standards);
      if (keys.length && !keys.includes(threadTypeSelect.value)) {
        threadTypeSelect.value = keys[0];
      }
    }
  } catch (err) {
    console.error("Error loading settings:", err);
  }
}

async function saveSettings() {
  const payload = {
    default_tolerance_pct: Number(toleranceInput.value),
  };

  const res = await fetch(`${API_BASE}/settings`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    throw new Error("Unable to save settings");
  }

  setStatus("✓ Default tolerance updated");
}

async function showPerformanceMetrics() {
  try {
    const res = await fetch(`${API_BASE}/performance`);
    if (!res.ok) throw new Error("Failed to fetch performance metrics");
    
    const data = await res.json();
    const metrics = data.metrics;
    
    performanceDetails.innerHTML = `
      <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; margin-top: 10px;">
        <div style="padding: 10px; background: #f5f5f5; border-radius: 8px;">
          <strong>Total Inspections</strong>
          <p style="font-size: 1.3rem; margin: 5px 0;">${metrics.total_inspections}</p>
        </div>
        <div style="padding: 10px; background: #f5f5f5; border-radius: 8px;">
          <strong>Images Processed</strong>
          <p style="font-size: 1.3rem; margin: 5px 0;">${metrics.images_processed}</p>
        </div>
        <div style="padding: 10px; background: #f5f5f5; border-radius: 8px; grid-column: span 2;">
          <strong>Avg Analysis Time</strong>
          <p style="font-size: 1.3rem; margin: 5px 0;">${metrics.avg_analysis_time_ms.toFixed(2)}ms</p>
        </div>
      </div>
    `;
    
    performanceModal.style.display = "block";
  } catch (err) {
    setStatus(`✗ Error: ${err.message}`);
  }
}

function toggleAutoInspect() {
  if (autoTimer) {
    clearInterval(autoTimer);
    autoTimer = null;
    autoBtn.textContent = "⚙ Auto Inspect: OFF";
    setStatus("Auto inspect disabled.");
    return;
  }

  autoBtn.textContent = "⚙ Auto Inspect: ON";
  setStatus("Auto inspect every 5s enabled.");
  autoTimer = setInterval(async () => {
    try {
      await captureFrame();
      await analyzeFrame();
    } catch (err) {
      setStatus(`Auto inspect error: ${err.message}`);
    }
  }, 5000);
}

async function exportCsv() {
  window.open(`${API_BASE}/export/csv`, "_blank");
}

async function setup() {
  buildCharts();
  updateBatchFilesCount();
  await loadSettings();
  await fetchCameraStatus();
  await refreshLatestResult();
  await refreshStats();

  setInterval(refreshLatestResult, 3000);
  setInterval(refreshStats, 5000);

  // Event listeners
  captureBtn.addEventListener("click", async () => {
    try {
      await captureFrame();
    } catch (err) {
      setStatus(`✗ Capture error: ${err.message}`);
    }
  });

  analyzeBtn.addEventListener("click", async () => {
    try {
      await analyzeFrame();
    } catch (err) {
      setStatus(`✗ Analyze error: ${err.message}`);
    }
  });

  qualityCheckBtn.addEventListener("click", async () => {
    try {
      await checkImageQuality();
    } catch (err) {
      setStatus(`✗ Quality check error: ${err.message}`);
    }
  });

  batchUploadBtn.addEventListener("click", () => {
    batchFilesInput.click();
  });

  autoBtn.addEventListener("click", toggleAutoInspect);
  exportBtn.addEventListener("click", exportCsv);
  performanceBtn.addEventListener("click", showPerformanceMetrics);
  refreshLogsBtn.addEventListener("click", refreshStats);

  saveSettingsBtn.addEventListener("click", async () => {
    try {
      await saveSettings();
    } catch (err) {
      setStatus(`✗ Settings error: ${err.message}`);
    }
  });

  if (toggleCameraBtn) {
    toggleCameraBtn.addEventListener("click", async () => {
      if (cameraEnabled) {
        try {
          const res = await fetch(`${API_BASE}/camera/off`, { method: "POST" });
          if (!res.ok) throw new Error("Unable to stop camera");
          setCameraToggleUI(false);
          setStatus("Camera feed stopped");
        } catch (err) {
          setStatus(`✗ Camera off error: ${err.message}`);
        }
      } else {
        const source = getSelectedCameraSource();
        const payload = source ? { source } : {};
        try {
          const res = await fetch(`${API_BASE}/camera/on`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
          });
          if (!res.ok) {
            let detail = "Unable to start camera";
            try {
              const errData = await res.json();
              if (errData?.detail) {
                detail = String(errData.detail);
              }
            } catch {
              // Keep default message when response is not JSON.
            }
            throw new Error(detail);
          }
          const data = await res.json();
          const activeSource = data.source || source || "default";
          setCameraToggleUI(true, activeSource);
          setStatus(`✓ Camera started (source ${activeSource})`);
        } catch (err) {
          setStatus(`✗ Camera on error: ${err.message}`);
        }
      }
    });
  }

  setStatus("✓ Ready for inspection (v2.0 Advanced)");
}

setup();
