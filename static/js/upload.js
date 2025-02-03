let uploadInProgress = false;

const platforms = [
    { id: 'youtube-personal', name: 'YouTube Personal', icon: 'fab fa-youtube' },
    { id: 'youtube-charity', name: 'YouTube Charity', icon: 'fab fa-youtube' },
    { id: 'instagram-personal', name: 'Instagram Personal', icon: 'fab fa-instagram' },
    { id: 'instagram-charity', name: 'Instagram Charity', icon: 'fab fa-instagram' },
    { id: 'tiktok-personal', name: 'TikTok Personal', icon: 'fab fa-tiktok' },
    { id: 'tiktok-charity', name: 'TikTok Charity', icon: 'fab fa-tiktok' }
];

function updateProgress(platformId, progress, status = 'uploading', error = null) {
    const card = document.getElementById(`${platformId}-card`);
    const progressBar = card.querySelector('.progress-bar-fill');
    const statusText = card.querySelector('.status-text');
    const errorLink = card.querySelector('.error-link');

    progressBar.style.width = `${progress}%`;
    
    if (status === 'error') {
        card.classList.add('error');
        statusText.textContent = 'Failed';
        errorLink.style.display = 'block';
        errorLink.href = `/platform/${platformId}`;
    } else if (status === 'success') {
        card.classList.add('success');
        statusText.textContent = 'Complete';
    } else {
        statusText.textContent = `${progress}%`;
    }
}

async function uploadFile(file) {
    if (uploadInProgress) return;
    uploadInProgress = true;

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) throw new Error('Upload failed');

        const eventSource = new EventSource('/progress');
        
        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            if (data.complete) {
                eventSource.close();
                uploadInProgress = false;
                return;
            }

            Object.entries(data).forEach(([platformId, info]) => {
                updateProgress(
                    platformId,
                    info.progress,
                    info.status,
                    info.error
                );
            });
        };

        eventSource.onerror = () => {
            eventSource.close();
            uploadInProgress = false;
        };

    } catch (error) {
        console.error('Upload failed:', error);
        uploadInProgress = false;
    }
}

// Initialize platform cards
function initializePlatformCards() {
    const grid = document.getElementById('platform-grid');
    platforms.forEach(platform => {
        const card = document.createElement('div');
        card.id = `${platform.id}-card`;
        card.className = 'platform-card';
        card.innerHTML = `
            <div class="platform-header">
                <i class="${platform.icon}"></i>
                <h3>${platform.name}</h3>
            </div>
            <div class="progress-bar">
                <div class="progress-bar-fill"></div>
            </div>
            <div class="platform-footer">
                <span class="status-text">Ready</span>
                <a href="#" class="error-link" style="display: none">View Error</a>
            </div>
        `;
        grid.appendChild(card);
    });
}

// Initialize drag and drop
function initializeDragAndDrop() {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');

    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => {
            dropZone.classList.add('drag-active');
        });
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => {
            dropZone.classList.remove('drag-active');
        });
    });

    dropZone.addEventListener('drop', (e) => {
        const file = e.dataTransfer.files[0];
        if (file && file.type.startsWith('video/')) {
            uploadFile(file);
        }
    });

    dropZone.addEventListener('click', () => {
        fileInput.click();
    });

    fileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file && file.type.startsWith('video/')) {
            uploadFile(file);
        }
    });
}

// Initialize everything when the page loads
document.addEventListener('DOMContentLoaded', () => {
    initializePlatformCards();
    initializeDragAndDrop();
});
