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

// Drag and Drop Logic
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');

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

fileInput.addEventListener('change', () => {
    if (fileInput.files.length) {
        document.querySelector('#drop-zone p').textContent = `Selected: ${fileInput.files[0].name}`;
    }
});

async function analyzeStock() {
    const loading = document.getElementById('loading');
    const resultSection = document.getElementById('result-section');
    const analyzeBtn = document.getElementById('analyze-btn');

    // Reset UI
    resultSection.classList.add('hidden');
    loading.classList.remove('hidden');
    analyzeBtn.disabled = true;

    const formData = new FormData();

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
        const response = await fetch('/analyze', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (response.ok) {
            displayResult(data);
        } else {
            alert(data.error || "An error occurred during analysis.");
        }
    } catch (error) {
        console.error(error);
        alert("Failed to connect to the server.");
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

    // 1. Recommendation Card
    const rec = data.recommendation;
    const verdict = document.getElementById('verdict');
    const reasonsList = document.getElementById('reasons-list');

    verdict.textContent = rec.verdict;
    verdict.className = rec.color; // green, orange, red

    // We don't populate reasons list here anymore, as we have a dedicated Observations section
    // But we can show the top reason if needed, or just clear it
    reasonsList.innerHTML = '';

    // 2. Render Comparison Table
    renderTable(data.table_data);

    // 3. Render Growth Analysis
    renderGrowth(data.growth);

    // 4. Render Observations
    renderObservations(data.observations);
}

function renderTable(tableData) {
    const table = document.getElementById('comparison-table');
    const thead = table.querySelector('thead tr');
    const tbody = table.querySelector('tbody');

    // Clear existing
    thead.innerHTML = '<th>Particulars</th>';
    tbody.innerHTML = '';

    if (!tableData || tableData.length === 0) return;

    // Create Headers
    tableData.forEach(col => {
        const th = document.createElement('th');
        th.textContent = col.period;
        thead.appendChild(th);
    });

    // Define Rows to display
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

        // Label Cell
        const tdLabel = document.createElement('td');
        tdLabel.innerHTML = `<strong>${metric.label}</strong>`;
        tr.appendChild(tdLabel);

        // Data Cells
        tableData.forEach(col => {
            const td = document.createElement('td');
            let val = col[metric.key];

            if (metric.isPercent) {
                td.textContent = val.toFixed(1) + '%';
                // Color code OPM
                if (val < 0) td.style.color = '#ef4444';
                else if (val > 20) td.style.color = '#22c55e';
            } else {
                td.textContent = val.toLocaleString('en-IN');
                // Color code Profit
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

        const arrow = item.val >= 0 ? '⬆️' : '⬇️';
        const color = item.val >= 0 ? '#22c55e' : '#ef4444';

        div.innerHTML = `
            <h4>${item.label}</h4>
            <p style="color: ${color}">${arrow} ${Math.abs(item.val).toFixed(1)}%</p>
        `;
        container.appendChild(div);
    });
}

function renderObservations(observations) {
    const list = document.getElementById('observations-list');
    list.innerHTML = '';

    if (!observations || observations.length === 0) {
        list.innerHTML = '<li>No critical observations found.</li>';
        return;
    }

    observations.forEach(obs => {
        const li = document.createElement('li');
        // Convert markdown bold to html bold
        const htmlObs = obs.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        li.innerHTML = htmlObs;
        list.appendChild(li);
    });
}
