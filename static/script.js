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

function updatePageLimit(value) {
    document.getElementById('page-limit-value').textContent = value;
}

function toggleApiKey() {
    const mode = document.querySelector('input[name="processing_mode"]:checked').value;
    const apiContainer = document.getElementById('api-key-container');
    const pageLimitContainer = document.getElementById('page-limit-container');
    const loadingText = document.getElementById('loading-text');
    const modeDescription = document.getElementById('mode-description');

    if (mode === 'local') {
        apiContainer.style.display = 'none';
        pageLimitContainer.style.display = 'none';
        loadingText.textContent = '⚡ Local engine is extracting financial data...';
        modeDescription.textContent = 'Fast rule-based extraction. No API key needed. Best for simple PDFs.';
    } else if (mode === 'smart') {
        apiContainer.style.display = 'block';
        pageLimitContainer.style.display = 'block';
        loadingText.textContent = '🧠 Smart mode analyzing... (trying local first)';
        modeDescription.textContent = 'Smart mode tries local extraction first (free). Falls back to AI only if needed. Best for cost savings!';
    } else {
        apiContainer.style.display = 'block';
        pageLimitContainer.style.display = 'block';
        loadingText.textContent = '🤖 AI is analyzing the financial data...';
        modeDescription.textContent = 'AI-powered analysis using GPT-4 Vision. Most accurate but requires API credits.';
    }
}

// Drag and Drop Logic
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');

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

async function analyzeStock() {
    const loading = document.getElementById('loading');
    const resultSection = document.getElementById('result-section');
    const analyzeBtn = document.getElementById('analyze-btn');

    resultSection.classList.add('hidden');
    loading.classList.remove('hidden');
    analyzeBtn.disabled = true;

    const formData = new FormData();

    const mode = document.querySelector('input[name="processing_mode"]:checked').value;
    formData.append('processing_mode', mode);

    // Get page limit for AI and Smart modes
    const pageLimit = document.getElementById('page-limit-slider').value;
    formData.append('ai_page_limit', pageLimit);

    if (mode === 'ai' || mode === 'smart') {
        const apiKey = document.getElementById('api-key-input').value.trim();
        if (!apiKey) {
            alert("Please enter your OpenAI API key for AI/Smart mode.");
            resetUI();
            return;
        }

        if (!apiKey.startsWith('sk-')) {
            alert("Invalid API key format. OpenAI keys start with 'sk-'");
            resetUI();
            return;
        }
        formData.append('api_key', apiKey);
    }

    if (document.getElementById('upload-tab').classList.contains('active')) {
        if (!fileInput.files.length) {
            alert("Please select a PDF file first.");
            resetUI();
            return;
        }
        formData.append('file', fileInput.files[0]);
    } else {
        const url = document.getElementById('url-input').value;
        if (!url) {
            alert("Please enter a URL.");
            resetUI();
            return;
        }
        formData.append('url', url);
    }

    try {
        console.log("Sending request to /analyze...");
        const response = await fetch('/analyze', {
            method: 'POST',
            body: formData
        });

        console.log("Response received, status:", response.status);
        const data = await response.json();

        if (response.ok) {
            console.log("Analysis successful, displaying results...");
            displayResult(data);
        } else {
            console.error("Server returned error:", data.error);
            alert(data.error || "An error occurred during analysis.");
        }
    } catch (error) {
        console.error("Fetch Error:", error);
        if (error.name === 'TypeError' && error.message === 'Failed to fetch') {
            alert("Connection Error: The server might be down or restarting. Please wait a few seconds and try again. \n\nNote: If you are editing the PDF while uploading, please save it first.");
        } else {
            alert("An error occurred: " + error.message);
        }
    } finally {
        resetUI();
    }
}

function resetUI() {
    document.getElementById('loading').classList.add('hidden');
    document.getElementById('analyze-btn').disabled = false;
}

function displayResult(data) {
    const resultSection = document.getElementById('result-section');
    resultSection.classList.remove('hidden');

    // Show Result Type Badge
    const typeContainer = document.getElementById('result-type-container');
    const typeBadge = document.getElementById('result-type-badge');
    const methodBadge = document.getElementById('processing-method-badge');

    if (data.result_type) {
        typeContainer.classList.remove('hidden');
        typeBadge.textContent = data.result_type;
        typeBadge.style.backgroundColor = data.result_type === 'Consolidated' ? 'var(--success)' : 'var(--primary)';
    }

    // Show Processing Method Badge
    if (data.processing_method) {
        const method = data.processing_method;
        methodBadge.textContent = method;

        if (method === 'Local') {
            methodBadge.style.backgroundColor = '#10b981'; // Green
            methodBadge.title = 'Processed locally - No cost';
        } else if (method === 'AI (Fallback)') {
            methodBadge.style.backgroundColor = '#f59e0b'; // Orange
            methodBadge.title = 'Local failed, used AI fallback';
        } else {
            methodBadge.style.backgroundColor = '#3b82f6'; // Blue
            methodBadge.title = 'Processed with AI';
        }
    }

    // Safe access to recommendation
    const rec = data.recommendation || { verdict: 'UNKNOWN', color: 'orange', reasons: [] };
    const verdict = document.getElementById('verdict');
    if (verdict) {
        verdict.textContent = rec.verdict || 'ANALYSIS INCOMPLETE';
        verdict.className = rec.color || 'orange';
    }

    // Show cost savings notification
    if (data.cost_saved) {
        console.log('💰 Cost saved! Used local extraction instead of AI.');
    }

    // Safe render calls
    renderTable(data.table_data || []);
    renderGrowth(data.growth || {});
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
function renderGrowth(growth) {
    const container = document.getElementById('growth-section');
    container.innerHTML = '';

    if (!growth) return;

    const items = [
        { label: 'Revenue QoQ', val: growth.revenue_qoq },
        { label: 'Net Profit QoQ', val: growth.net_profit_qoq },
        { label: 'Revenue YoY', val: growth.revenue_yoy },
        { label: 'Net Profit YoY', val: growth.net_profit_yoy }
    ];

    items.forEach(item => {
        const div = document.createElement('div');
        div.className = 'growth-item';
        const isPositive = item.val >= 0;
        div.innerHTML = `
            <h4>${item.label}</h4>
            <p style="color: ${isPositive ? 'var(--success)' : 'var(--danger)'}">
                ${isPositive ? '+' : ''}${item.val ? item.val.toFixed(1) : '0'}%
            </p>
        `;
        container.appendChild(div);
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
