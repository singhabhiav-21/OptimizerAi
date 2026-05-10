
// ==================== STATE ====================
let selectedFile = null;
let uploadInterval = null;

// ==================== AUTH CHECK ====================
document.addEventListener('DOMContentLoaded', async () => {
    try {
        const res = await fetch('/auth/status', { credentials: 'include' });

        if (res.status === 401) {
            window.location.replace('/');
            return;
        }

        if (!res.ok) throw new Error();

        const data = await res.json();
        if (!data.authenticated) {
            window.location.replace('/');
            return;
        }

        setupUploadArea();
        setupFileInput();

        const userRes = await fetch('/me', { credentials: 'include' });
        if (userRes.ok) {
            const user = await userRes.json();
            document.getElementById('user-btn').textContent = user.email;
        }

    } catch {
        console.error('BOOT ERROR:', err);
    showMessage(err.message);
    }
});

// ==================== SECURITY CONSTANTS ====================
const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5MB
const ALLOWED_MIME_TYPES = ['text/csv', 'application/vnd.ms-excel', 'text/plain', 'application/csv'];
const ALLOWED_EXTENSIONS = ['.csv'];

// ==================== UPLOAD AREA ====================
function setupUploadArea() {
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('fileInput');

    uploadArea.addEventListener('click', e => {
        if (e.target.tagName !== 'BUTTON') fileInput.click();
    });

    uploadArea.addEventListener('dragover', e => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });

    uploadArea.addEventListener('dragleave', () => uploadArea.classList.remove('dragover'));

    uploadArea.addEventListener('drop', e => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        if (e.dataTransfer.files.length) handleFileSelect(e.dataTransfer.files[0]);
    });
}

function setupFileInput() {
    document.getElementById('fileInput').addEventListener('change', e => {
        if (e.target.files.length) handleFileSelect(e.target.files[0]);
    });
}

// ==================== FILE VALIDATION ====================
function validateFile(file) {
    if (!file) return { valid: false, error: 'No file selected' };

    const name = file.name.toLowerCase();
    if (!ALLOWED_EXTENSIONS.some(ext => name.endsWith(ext))) {
        return { valid: false, error: 'Only CSV files are allowed' };
    }

    if (file.type && !ALLOWED_MIME_TYPES.includes(file.type)) {
        return { valid: false, error: 'Invalid CSV file format' };
    }

    if (file.size === 0) return { valid: false, error: 'File is empty' };
    if (file.size > MAX_FILE_SIZE) return { valid: false, error: 'File too large (max 5MB)' };

    if (/[<>:"|?*]|\.\.|\0/.test(name)) {
        return { valid: false, error: 'Invalid file name' };
    }

    return { valid: true };
}

// ==================== FILE SELECTION ====================
function handleFileSelect(file) {
    const validation = validateFile(file);
    if (!validation.valid) {
        showMessage(validation.error, 'error');
        return;
    }

    selectedFile = file;
    displaySelectedFile(file);
}

function displaySelectedFile(file) {
    document.getElementById('fileName').textContent = file.name;
    document.getElementById('fileSize').textContent = formatFileSize(file.size);
    document.getElementById('selectedFile').classList.add('show');
    document.getElementById('importActions').style.display = 'flex';
}

function removeFile() {
    selectedFile = null;
    if (uploadInterval) clearInterval(uploadInterval);
    uploadInterval = null;

    document.getElementById('selectedFile').classList.remove('show');
    document.getElementById('importActions').style.display = 'none';
    document.getElementById('fileInput').value = '';
}

// ==================== FILE UPLOAD ====================
async function uploadFile() {
    if (!selectedFile) {
        showMessage('Select a file first', 'error');
        return;
    }

    const validation = validateFile(selectedFile);
    if (!validation.valid) {
        showMessage(validation.error, 'error');
        return;
    }

    try {
        await validateCSVContent(selectedFile);
    } catch (err) {
        showMessage(err.message, 'error');
        return;
    }

    showProgress();

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
        const response = await fetch('/import-csv', {
            method: 'POST',
            credentials: 'include',
            body: formData
        });

        if (uploadInterval) clearInterval(uploadInterval);
        uploadInterval = null;
        updateProgress(100);

        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || 'Import failed');

        showResults(result, true);

    } catch (err) {
        hideProgress();
        showMessage(err.message || 'Upload failed', 'error');
    }
}

// ==================== CSV CONTENT VALIDATION ====================
async function validateCSVContent(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = e => {
            try {
                const text = e.target.result;
                if (text.includes('\0')) return reject(new Error('Invalid characters in file'));

                const lines = text.split('\n').filter(l => l.trim());
                if (lines.length < 2) return reject(new Error('CSV has no data rows'));

                const headerCols = lines[0]
                    .toLowerCase()
                    .split(/[,;\t]/)
                    .map(c => c.replace(/["']/g, '').trim());

                const required = ['valuedate', 'text', 'amount'];
                const missing = required.filter(r => !headerCols.some(c => c.replace(/[\s_-]/g, '').includes(r)));

                if (missing.length) {
                    return reject(new Error('Missing required columns: Value date, Text, Amount'));
                }

                resolve();
            } catch (err) {
                reject(new Error('Failed to parse CSV'));
            }
        };

        reader.onerror = () => reject(new Error('Failed to read file'));
        reader.readAsText(file.slice(0, 51200));
    });
}

// ==================== PROGRESS ====================
function showProgress() {
    document.getElementById('progressContainer').classList.add('show');
    document.getElementById('importActions').style.display = 'none';
    document.getElementById('selectedFile').classList.remove('show');

    let progress = 0;
    uploadInterval = setInterval(() => {
        progress = Math.min(progress + Math.random() * 15, 90);
        updateProgress(progress);
    }, 200);
}

function updateProgress(percent) {
    const bar = document.getElementById('progressBar');
    const status = document.getElementById('progressStatus');
    bar.style.width = `${percent}%`;
    bar.textContent = `${Math.round(percent)}%`;

    if (percent < 30) status.textContent = 'Uploading file...';
    else if (percent < 70) status.textContent = 'Validating data...';
    else status.textContent = 'Processing transactions...';
}

function hideProgress() {
    if (uploadInterval) clearInterval(uploadInterval);
    uploadInterval = null;
    document.getElementById('progressContainer').classList.remove('show');
}

// ==================== RESULTS ====================
function showResults(result) {
    hideProgress();

    const resultsDiv = document.getElementById('importResults');
    document.getElementById('resultIcon').textContent = '✅';
    document.getElementById('resultTitle').textContent = 'Import Successful';

    document.getElementById('resultStats').innerHTML = `
        <div class="stat-card"><div class="stat-value success">${result.imported || 0}</div><div class="stat-label">Imported</div></div>
        <div class="stat-card"><div class="stat-value warning">${result.duplicates || 0}</div><div class="stat-label">Duplicates</div></div>
        <div class="stat-card"><div class="stat-value info">${result.total || 0}</div><div class="stat-label">Processed</div></div>
    `;

    resultsDiv.classList.add('show');
    showMessage(`Imported ${result.imported || 0} transactions`, 'success');
}

function resetImport() {
    document.getElementById('importResults').classList.remove('show');
    removeFile();
}

// ==================== UTIL ====================
function formatFileSize(bytes) {
    const sizes = ['Bytes', 'KB', 'MB'];
    if (!bytes) return '0 Bytes';
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return (bytes / Math.pow(1024, i)).toFixed(2) + ' ' + sizes[i];
}



async function logout() {
    try {
        await fetch('/logout', { method: 'POST', credentials: 'include' });
    } finally {
        window.location.replace('/');
    }
}


window.uploadFile = uploadFile;
window.removeFile = removeFile;
window.resetImport = resetImport;
window.logout = logout;