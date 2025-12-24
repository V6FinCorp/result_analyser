function switchTab(tab) {
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    if (tab === 'upload') {
        document.querySelector('.tab-btn:nth-child(1)').classList.add('active');
        document.getElementById('upload-tab').classList.add('active');
    } else {
        document.querySelector('.tab-btn:nth-child(2)').classList.add('active');
        document.getElementById('url-tab').classList.add('active');
    }
}

function resetUI() {
    document.getElementById('loading').classList.add('hidden');
    document.getElementById('analyze-btn').disabled = false;
}

// Global variables
let fileInput;

// Drag and Drop Logic
document.addEventListener('DOMContentLoaded', () => {
    const dropZone = document.getElementById('drop-zone');
    fileInput = document.getElementById('file-input');

    if (dropZone) {
        dropZone.addEventListener('click', () => fileInput.click());
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.style.borderColor = '#3b82f6';
            dropZone.style.background = 'rgba(59, 130, 246, 0.1)';
        });
        dropZone.addEventListener('dragleave', () => {
            dropZone.style.borderColor = 'rgba(255, 255, 255, 0.1)';
            dropZone.style.background = 'rgba(255, 255, 255, 0.05)';
        });
        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.style.borderColor = 'rgba(255, 255, 255, 0.1)';
            dropZone.style.background = 'rgba(255, 255, 255, 0.05)';
            if (e.dataTransfer.files.length) {
                fileInput.files = e.dataTransfer.files;
                document.querySelector('#drop-zone p').textContent = `Selected: ${fileInput.files[0].name}`;
            }
        });
    }

    if (fileInput) {
        fileInput.addEventListener('change', () => {
            if (fileInput.files.length) {
                document.querySelector('#drop-zone p').textContent = `Selected: ${fileInput.files[0].name}`;
            }
        });
    }
});

function toggleDebugMode() {
    const isChecked = document.getElementById('debug-toggle').checked;
    const sidebar = document.getElementById('debug-sidebar');
    const container = document.querySelector('.container');

    if (isChecked) {
        sidebar.style.display = 'flex';
        container.style.maxWidth = '1000px';
    } else {
        sidebar.style.display = 'none';
        container.style.maxWidth = '900px';
    }
}

function addLogEntry(msg, type = 'local') {
    const logsContainer = document.getElementById('debug-logs');
    const entry = document.createElement('div');
    entry.className = `log-entry ${type}`;
    entry.textContent = `> ${msg}`;
    logsContainer.appendChild(entry);
    logsContainer.scrollTop = logsContainer.scrollHeight;
}

function updatePageLimit(value) {
    document.getElementById('page-limit-value').textContent = value;
}

function toggleApiKey() {
    const mode = document.querySelector('input[name="processing_mode"]:checked').value;
    const apiContainer = document.getElementById('api-key-container');
    const pageLimitContainer = document.getElementById('page-limit-container');
    const loadingText = document.getElementById('loading-text');

    if (mode === 'local') {
        apiContainer.style.display = 'none';
        pageLimitContainer.style.display = 'none';
        loadingText.textContent = '⚡ Extracting data locally using result_extractor engine...';
    } else if (mode === 'smart') {
        apiContainer.style.display = 'block';
        pageLimitContainer.style.display = 'block';
        loadingText.textContent = '🧠 Smart mode: Trying local first, then AI fallback...';
    } else {
        apiContainer.style.display = 'block';
        pageLimitContainer.style.display = 'block';
        loadingText.textContent = '🤖 Full AI analysis in progress...';
    }
}

// ... (Drag and Drop Logic unchanged) ...

async function analyzeStock() {
    const loading = document.getElementById('loading');
    const resultSection = document.getElementById('result-section');
    const analyzeBtn = document.getElementById('analyze-btn');
    const logsContainer = document.getElementById('debug-logs');

    resultSection.classList.add('hidden');
    loading.classList.remove('hidden');
    analyzeBtn.disabled = true;

    // Reset debug logs
    logsContainer.innerHTML = '<div class="log-entry">Initializing analysis...</div>';
    document.getElementById('ai-cost-badge').classList.add('hidden');

    const formData = new FormData();
    const mode = document.querySelector('input[name="processing_mode"]:checked').value;
    formData.append('processing_mode', mode);

    const pageLimit = document.getElementById('page-limit-slider').value;
    formData.append('ai_page_limit', pageLimit);

    if (mode === 'ai' || mode === 'smart') {
        const apiKey = document.getElementById('api-key-input').value.trim();
        if (!apiKey) {
            alert("Please enter API key for AI mode.");
            resetUI();
            return;
        }
        formData.append('api_key', apiKey);
    }

    if (document.getElementById('upload-tab').classList.contains('active')) {
        if (!fileInput.files.length) { alert("Select PDF."); resetUI(); return; }
        formData.append('file', fileInput.files[0]);
        addLogEntry(`File selected: ${fileInput.files[0].name}`);
    } else {
        const url = document.getElementById('url-input').value;
        if (!url) { alert("Enter URL."); resetUI(); return; }
        formData.append('url', url);
        addLogEntry(`Pinching PDF from URL...`);
    }

    try {
        addLogEntry(`Mode: ${mode.toUpperCase()} | Page Limit: ${pageLimit}`);
        const response = await fetch('/analyze', { method: 'POST', body: formData });
        const data = await response.json();

        if (response.ok) {
            displayResult(data);
        } else {
            addLogEntry(`Error: ${data.error}`, 'error');
            alert(data.error);
        }
    } catch (error) {
        addLogEntry(`Fatal: ${error.message}`, 'error');
        alert("An error occurred: " + error.message);
    } finally {
        resetUI();
    }
}

function displayResult(data) {
    const resultSection = document.getElementById('result-section');
    resultSection.classList.remove('hidden');

    // Badges
    const typeContainer = document.getElementById('result-type-container');
    const typeBadge = document.getElementById('result-type-badge');
    const methodBadge = document.getElementById('processing-method-badge');

    if (data.result_type) {
        typeContainer.classList.remove('hidden');
        typeBadge.textContent = data.result_type;
        typeBadge.style.backgroundColor = data.result_type === 'Consolidated' ? 'var(--success)' : 'var(--primary)';
    }

    if (data.processing_method) {
        methodBadge.textContent = data.processing_method;
        methodBadge.style.backgroundColor = data.processing_method === 'Local' ? '#10b981' : '#3b82f6';
    }

    // Recommendation
    const rec = data.recommendation || { verdict: 'UNKNOWN', color: 'orange', reasons: [] };
    const verdict = document.getElementById('verdict');
    if (verdict) {
        verdict.textContent = rec.verdict;
        verdict.className = rec.color;
    }

    // Handle Debug Logs
    if (data.debug_logs) {
        data.debug_logs.forEach(log => addLogEntry(log, 'local'));
    }

    if (data.processing_method.includes('AI')) {
        addLogEntry('AI analysis performed successfully.', 'ai');
        // Simple cost estimation (estimate: $0.015 per page for GPT-4o)
        const pages = document.getElementById('page-limit-slider').value;
        const estCost = (pages * 0.015).toFixed(3);
        const costBadge = document.getElementById('ai-cost-badge');
        costBadge.textContent = `Est. Cost: $${estCost}`;
        costBadge.classList.remove('hidden');
    } else {
        addLogEntry('Local extraction completed (Cost: $0.00)', 'local');
    }

    renderTable(data.table_data || []);
    renderCorporateActions(data.corporate_actions || {});
    renderObservations(data.observations || []);
}

function renderCorporateActions(actions) {
    const container = document.getElementById('corporate-actions-section');
    container.innerHTML = '';

    if (!actions) {
        container.innerHTML = '<p style="color: var(--text-muted); font-size: 0.9rem;">No corporate actions found.</p>';
        return;
    }

    const items = [
        { key: 'dividend', label: '💰 Dividend', val: actions.dividend },
        { key: 'capex', label: '🏗️ Capex/Expansion', val: actions.capex },
        { key: 'management_change', label: '👔 Management Change', val: actions.management_change },
        { key: 'new_projects', label: '🚀 New Projects/Orders', val: actions.new_projects },
        { key: 'special_announcement', label: '📢 Special Announcement', val: actions.special_announcement }
    ];

    items.forEach(item => {
        const div = document.createElement('div');
        div.className = 'corporate-action-item';
        div.innerHTML = `<h4>${item.label}</h4><p>${item.val || 'Not mentioned'}</p>`;
        container.appendChild(div);
    });
}

function renderTable(tableData) {
    const table = document.getElementById('comparison-table');
    const thead = table.querySelector('thead tr');
    const tbody = table.querySelector('tbody');

    thead.innerHTML = '<th>Particulars</th>';
    thead.innerHTML += '<th style="color: var(--primary)">QoQ %</th>';
    thead.innerHTML += '<th style="color: var(--primary)">YoY %</th>';
    tbody.innerHTML = '';

    if (!tableData || tableData.length === 0) return;

    // Identify indices for calculation
    const current = tableData.find(d => d.period === 'Current');
    const prev = tableData.find(d => d.period === 'Prev Qtr');
    const yoy = tableData.find(d => d.period === 'YoY Qtr');

    tableData.forEach(col => {
        const th = document.createElement('th');
        th.textContent = col.period;
        thead.appendChild(th);
    });

    const metrics = [
        { key: 'revenue', label: 'Revenue from Operations' },
        { key: 'other_income', label: 'Other Income' },
        { key: 'total_expenses', label: 'Total Expenses' },
        { key: 'operating_profit', label: 'Operating Profit (EBIT)' },
        { key: 'opm', label: 'OPM %', isPercent: true },
        { key: 'pbt', label: 'Profit Before Tax' },
        { key: 'net_profit', label: 'Net Profit' },
        { key: 'eps', label: 'EPS (Rs)' }
    ];

    metrics.forEach(metric => {
        const tr = document.createElement('tr');

        // 1. Particulars Label
        const tdLabel = document.createElement('td');
        tdLabel.innerHTML = `<strong>${metric.label}</strong>`;
        tr.appendChild(tdLabel);

        // 2. QoQ % Calculation & Cell
        const tdQoQ = document.createElement('td');
        if (current && prev && prev[metric.key]) {
            const diff = ((current[metric.key] - prev[metric.key]) / Math.abs(prev[metric.key])) * 100;
            tdQoQ.textContent = (diff > 0 ? '+' : '') + diff.toFixed(1) + '%';

            // Expense Logic: Red on increase, Green on decrease
            if (metric.key === 'total_expenses') {
                tdQoQ.style.color = diff <= 0 ? 'var(--success)' : 'var(--danger)';
            } else {
                tdQoQ.style.color = diff >= 0 ? 'var(--success)' : 'var(--danger)';
            }
            tdQoQ.style.fontWeight = '600';
        } else {
            tdQoQ.textContent = '-';
        }
        tr.appendChild(tdQoQ);

        // 3. YoY % Calculation & Cell
        const tdYoY = document.createElement('td');
        if (current && yoy && yoy[metric.key]) {
            const diff = ((current[metric.key] - yoy[metric.key]) / Math.abs(yoy[metric.key])) * 100;
            tdYoY.textContent = (diff > 0 ? '+' : '') + diff.toFixed(1) + '%';

            // Expense Logic: Red on increase, Green on decrease
            if (metric.key === 'total_expenses') {
                tdYoY.style.color = diff <= 0 ? 'var(--success)' : 'var(--danger)';
            } else {
                tdYoY.style.color = diff >= 0 ? 'var(--success)' : 'var(--danger)';
            }
            tdYoY.style.fontWeight = '600';
        } else {
            tdYoY.textContent = '-';
        }
        tr.appendChild(tdYoY);

        // 4. Period Data Cells
        tableData.forEach(col => {
            const td = document.createElement('td');
            let val = col[metric.key];

            if (metric.isPercent) {
                td.textContent = (val || 0).toFixed(1) + '%';
                if (val < 0) td.style.color = '#ef4444';
                else if (val > 20) td.style.color = '#22c55e';
            } else {
                td.textContent = (val || 0).toLocaleString('en-IN');
                if ((metric.key === 'operating_profit' || metric.key === 'net_profit') && val < 0) {
                    td.style.color = '#ef4444';
                    td.textContent = `(${Math.abs(val).toLocaleString('en-IN')})`;
                }
            }
            tr.appendChild(td);
        });

        tbody.appendChild(tr);
    });
}

function renderObservations(observations) {
    const list = document.getElementById('observations-list');
    list.innerHTML = '';

    if (!observations || observations.length === 0) {
        list.innerHTML = '<li>No specific observations found.</li>';
        return;
    }

    observations.forEach(obs => {
        const li = document.createElement('li');
        li.textContent = obs;
        list.appendChild(li);
    });
}
