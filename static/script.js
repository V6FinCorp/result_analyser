let currentTab = 'upload';

function switchTab(tab) {
    currentTab = tab;
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    
    if (tab === 'upload') {
        document.querySelector('.tab-btn:first-child').classList.add('active');
        document.getElementById('upload-tab').classList.add('active');
    } else {
        document.querySelector('.tab-btn:last-child').classList.add('active');
        document.getElementById('url-tab').classList.add('active');
    }
}

// File Upload Handling
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
let selectedFile = null;

dropZone.addEventListener('click', () => fileInput.click());

fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        selectedFile = e.target.files[0];
        dropZone.innerHTML = `<p>Selected: <strong>${selectedFile.name}</strong></p>`;
    }
});

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.style.borderColor = 'var(--primary)';
});

dropZone.addEventListener('dragleave', (e) => {
    e.preventDefault();
    dropZone.style.borderColor = 'var(--text-muted)';
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.style.borderColor = 'var(--text-muted)';
    
    if (e.dataTransfer.files.length > 0) {
        selectedFile = e.dataTransfer.files[0];
        dropZone.innerHTML = `<p>Selected: <strong>${selectedFile.name}</strong></p>`;
    }
});

async function analyzeStock() {
    const loading = document.getElementById('loading');
    const resultSection = document.getElementById('result-section');
    
    // Reset UI
    loading.classList.remove('hidden');
    resultSection.classList.add('hidden');
    
    const formData = new FormData();
    
    if (currentTab === 'upload') {
        if (!selectedFile) {
            alert('Please select a PDF file first.');
            loading.classList.add('hidden');
            return;
        }
        formData.append('file', selectedFile);
    } else {
        const url = document.getElementById('url-input').value;
        if (!url) {
            alert('Please enter a URL.');
            loading.classList.add('hidden');
            return;
        }
        formData.append('url', url);
    }
    
    try {
        const response = await fetch('/analyze', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (response.ok) {
            displayResults(result);
        } else {
            alert('Error: ' + result.error);
        }
        
    } catch (error) {
        alert('An error occurred during analysis.');
        console.error(error);
    } finally {
        loading.classList.add('hidden');
    }
}

function displayResults(result) {
    const data = result.data;
    const rec = result.recommendation;
    const resultSection = document.getElementById('result-section');
    
    // Update Metrics
    document.getElementById('revenue').textContent = formatCurrency(data.revenue);
    document.getElementById('op-profit').textContent = formatCurrency(data.operating_profit);
    document.getElementById('opm').textContent = data.opm.toFixed(1) + '%';
    document.getElementById('net-profit').textContent = formatCurrency(data.net_profit);
    document.getElementById('eps').textContent = data.eps;
    
    // Update Recommendation
    const recCard = document.getElementById('rec-card');
    const verdict = document.getElementById('verdict');
    const reasonsList = document.getElementById('reasons-list');
    
    verdict.textContent = rec.verdict;
    recCard.style.backgroundColor = getBackgroundColor(rec.color);
    
    reasonsList.innerHTML = rec.reasons.map(r => `<li>${r}</li>`).join('');
    
    resultSection.classList.remove('hidden');
}

function formatCurrency(value) {
    return '₹ ' + value.toLocaleString('en-IN');
}

function getBackgroundColor(color) {
    if (color === 'green') return 'rgba(34, 197, 94, 0.2)';
    if (color === 'orange') return 'rgba(245, 158, 11, 0.2)';
    return 'rgba(239, 68, 68, 0.2)';
}
