// === Audio Transcription ===
async function transcribeAudio() {
    const fileInput = document.getElementById('audio-file');
    const btn = document.getElementById('transcribe-btn');
    const status = document.getElementById('transcribe-status');

    if (!fileInput.files.length) {
        status.textContent = 'Please select an audio file';
        status.className = 'status-message show error';
        return;
    }

    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append('file', file);

    btn.disabled = true;
    btn.innerHTML = '<span class="loading-spinner"></span>Transcribing...';
    status.textContent = 'Uploading and transcribing... this may take a moment.';
    status.className = 'status-message show processing';

    try {
        const response = await fetch('/api/transcribe', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Transcription failed');
        }

        const data = await response.json();
        document.getElementById('transcript-text').textContent = data.text;
        document.getElementById('transcribe-results').style.display = 'block';
        status.textContent = 'Done!';
        status.className = 'status-message show success';
        btn.innerHTML = 'Transcribe';
        btn.disabled = false;

    } catch (error) {
        status.textContent = error.message;
        status.className = 'status-message show error';
        btn.innerHTML = 'Transcribe';
        btn.disabled = false;
    }
}

function copyTranscript() {
    const text = document.getElementById('transcript-text').textContent;
    navigator.clipboard.writeText(text).then(() => {
        const btn = event.target;
        btn.textContent = 'Copied!';
        setTimeout(() => btn.textContent = 'Copy to Clipboard', 2000);
    });
}

let currentVideoId = null;
let currentUrl = null;
let currentVideoTitle = null;
let analysisComplete = false;

const featureNames = {
    'detection': 'Object Detection',
    'classification': 'Classification',
    'segmentation': 'Segmentation',
    'change': 'Change Detection',
    'visual': 'Visual Q&A',
    'summary': 'Summary & Takeaways'
};

async function processVideo() {
    const urlInput = document.getElementById('youtube-url');
    const processBtn = document.getElementById('process-btn');
    const inputSection = document.getElementById('input-section');
    const featuresSection = document.getElementById('features-section');

    const url = urlInput.value.trim();
    if (!url) {
        showStatus('Please enter a YouTube URL', 'error');
        return;
    }

    currentUrl = url;
    processBtn.disabled = true;
    processBtn.innerHTML = '<span class="loading-spinner"></span>Loading...';
    analysisComplete = false;

    try {
        showStatus('Downloading video for analysis...', 'processing');

        const response = await fetch('/api/video/download', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to download video');
        }

        const data = await response.json();
        currentVideoId = data.video_id;
        currentVideoTitle = data.title || 'Video';

        // Update UI
        document.getElementById('current-video-title').textContent = currentVideoTitle;

        showStatus('', 'success');
        inputSection.classList.add('hidden');
        featuresSection.classList.remove('hidden');

    } catch (error) {
        showStatus(error.message, 'error');
    } finally {
        processBtn.disabled = false;
        processBtn.innerHTML = 'Load Video';
    }
}

function changeVideo() {
    // Reset and go back to input
    document.getElementById('features-section').classList.add('hidden');
    document.getElementById('feature-page').classList.add('hidden');
    document.getElementById('input-section').classList.remove('hidden');
    document.getElementById('youtube-url').value = '';
    currentVideoId = null;
    currentUrl = null;
    currentVideoTitle = null;
}

function navigateToFeature(featureName) {
    // Hide features menu, show feature page
    document.getElementById('features-section').classList.add('hidden');
    document.getElementById('feature-page').classList.remove('hidden');

    // Update page title
    document.getElementById('page-title').textContent = featureNames[featureName];

    // Hide all page contents
    document.querySelectorAll('.page-content').forEach(page => page.classList.add('hidden'));

    // Show selected page
    document.getElementById(`${featureName}-page`).classList.remove('hidden');
}

function goBackToMenu() {
    document.getElementById('feature-page').classList.add('hidden');
    document.getElementById('features-section').classList.remove('hidden');
}

async function runObjectDetection() {
    if (!currentVideoId) {
        alert('Please load a video first');
        return;
    }

    const detectBtn = document.getElementById('detect-btn');
    detectBtn.disabled = true;
    detectBtn.innerHTML = '<span class="loading-spinner"></span>Detecting objects...';

    try {
        const response = await fetch('/api/analysis/detect', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ video_id: currentVideoId })
        });

        if (!response.ok) {
            throw new Error('Detection failed');
        }

        const data = await response.json();

        // Update stats
        document.getElementById('total-objects').textContent = data.total_objects;
        document.getElementById('unique-classes').textContent = data.unique_classes;
        document.getElementById('frames-processed').textContent = data.frames_processed;

        // Show results
        document.getElementById('detection-results').classList.remove('hidden');

        // Build detection summary
        const detectionList = document.getElementById('detection-list');
        detectionList.innerHTML = '<h4>Detected Objects:</h4>';

        for (const [className, count] of Object.entries(data.detection_summary)) {
            detectionList.innerHTML += `
                <div class="detection-item">
                    <span class="object-name">${className}</span>
                    <span class="object-count">${count}</span>
                </div>
            `;
        }
        detectionList.classList.remove('hidden');

        // Build frame gallery
        const framesGallery = document.getElementById('frames-gallery');
        if (framesGallery) {
            framesGallery.innerHTML = '<h4>Annotated Frames:</h4><div class="frames-grid">';

            for (const frame of data.frames) {
                const detectionCount = frame.detections.length;
                const detectionLabels = frame.detections.map(d => `${d.class} (${(d.confidence * 100).toFixed(0)}%)`).join(', ');

                framesGallery.innerHTML += `
                    <div class="frame-card" onclick="showFullFrame('${frame.image_path}')">
                        <img src="${frame.image_path}" alt="Frame ${frame.frame_number}" loading="lazy">
                        <div class="frame-info">
                            <span class="frame-number">Frame ${frame.frame_number}</span>
                            <span class="frame-detections">${detectionCount} object${detectionCount !== 1 ? 's' : ''}</span>
                        </div>
                    </div>
                `;
            }
            framesGallery.innerHTML += '</div>';
            framesGallery.classList.remove('hidden');
        }

        analysisComplete = true;
        detectBtn.innerHTML = 'Detection Complete';

    } catch (error) {
        alert('Object detection failed: ' + error.message);
        detectBtn.innerHTML = 'Run Object Detection';
        detectBtn.disabled = false;
    }
}

function showFullFrame(imagePath) {
    // Create modal for full-size frame view
    const modal = document.createElement('div');
    modal.className = 'frame-modal';
    modal.innerHTML = `
        <div class="frame-modal-content">
            <span class="close-modal" onclick="this.parentElement.parentElement.remove()">&times;</span>
            <img src="${imagePath}" alt="Full frame">
        </div>
    `;
    modal.onclick = (e) => {
        if (e.target === modal) modal.remove();
    };
    document.body.appendChild(modal);
}

async function runClassification() {
    if (!currentVideoId) {
        alert('Please load a video first');
        return;
    }

    const classifyBtn = document.getElementById('classify-btn');
    classifyBtn.disabled = true;
    classifyBtn.innerHTML = '<span class="loading-spinner"></span>Classifying...';

    try {
        const response = await fetch('/api/analysis/classify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ video_id: currentVideoId })
        });

        if (!response.ok) {
            throw new Error('Classification failed');
        }

        const data = await response.json();

        const resultsDiv = document.getElementById('classification-results');
        resultsDiv.innerHTML = '<h4>Classification Results:</h4>';

        for (const category of data.categories) {
            resultsDiv.innerHTML += `
                <div class="classification-card">
                    <h4>${category.name}</h4>
                    <ul>
                        ${category.items.map(item => `
                            <li>
                                <span>${item.name}</span>
                                <span>${(item.confidence * 100).toFixed(1)}%</span>
                            </li>
                        `).join('')}
                    </ul>
                </div>
            `;
        }
        resultsDiv.classList.remove('hidden');
        classifyBtn.innerHTML = 'Classification Complete';

    } catch (error) {
        alert('Classification failed: ' + error.message);
        classifyBtn.innerHTML = 'Run Classification';
        classifyBtn.disabled = false;
    }
}

async function runSegmentation() {
    if (!currentVideoId) {
        alert('Please load a video first');
        return;
    }

    const segmentBtn = document.getElementById('segment-btn');
    segmentBtn.disabled = true;
    segmentBtn.innerHTML = '<span class="loading-spinner"></span>Segmenting...';

    try {
        const response = await fetch('/api/analysis/segment', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ video_id: currentVideoId })
        });

        if (!response.ok) {
            throw new Error('Segmentation failed');
        }

        const data = await response.json();

        const resultsDiv = document.getElementById('segmentation-results');
        resultsDiv.innerHTML = `
            <h4>Segmentation Results:</h4>
            <p>Analyzed ${data.frames_processed} frames</p>
            <div class="segmentation-summary">
                ${data.regions.map(region => `
                    <div class="detection-item">
                        <span class="object-name">${region.name}</span>
                        <span class="object-count">${region.percentage}%</span>
                    </div>
                `).join('')}
            </div>
        `;
        resultsDiv.classList.remove('hidden');
        segmentBtn.innerHTML = 'Segmentation Complete';

    } catch (error) {
        alert('Segmentation failed: ' + error.message);
        segmentBtn.innerHTML = 'Run Segmentation';
        segmentBtn.disabled = false;
    }
}

async function runChangeDetection() {
    if (!currentVideoId) {
        alert('Please load a video first');
        return;
    }

    const changeBtn = document.getElementById('change-btn');
    changeBtn.disabled = true;
    changeBtn.innerHTML = '<span class="loading-spinner"></span>Analyzing changes...';

    try {
        const response = await fetch('/api/analysis/change', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ video_id: currentVideoId })
        });

        if (!response.ok) {
            throw new Error('Change detection failed');
        }

        const data = await response.json();

        const resultsDiv = document.getElementById('change-results');
        resultsDiv.innerHTML = `
            <h4>Change Detection Results:</h4>
            <div class="results-grid">
                <div class="stat-card">
                    <span class="stat-value">${data.total_changes}</span>
                    <span class="stat-label">Changes Detected</span>
                </div>
                <div class="stat-card">
                    <span class="stat-value">${data.motion_score}%</span>
                    <span class="stat-label">Motion Score</span>
                </div>
            </div>
            <div class="change-details">
                ${data.changes.map(change => `
                    <div class="detection-item">
                        <span class="object-name">Frame ${change.frame}: ${change.description}</span>
                    </div>
                `).join('')}
            </div>
        `;
        resultsDiv.classList.remove('hidden');
        changeBtn.innerHTML = 'Change Detection Complete';

    } catch (error) {
        alert('Change detection failed: ' + error.message);
        changeBtn.innerHTML = 'Run Change Detection';
        changeBtn.disabled = false;
    }
}

async function generateSummary() {
    if (!currentVideoId) {
        alert('Please load a video first');
        return;
    }

    const summaryBtn = document.getElementById('summary-btn');
    summaryBtn.disabled = true;
    summaryBtn.innerHTML = '<span class="loading-spinner"></span>Processing video...';

    try {
        // First, process the video to get transcript
        const processResponse = await fetch('/api/process', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: currentUrl })
        });

        if (!processResponse.ok) {
            throw new Error('Failed to process video');
        }

        // Poll for completion
        let status = 'processing';
        while (status !== 'completed' && status !== 'error') {
            await new Promise(resolve => setTimeout(resolve, 2000));
            const statusResponse = await fetch(`/api/status/${currentVideoId}`);
            const statusData = await statusResponse.json();
            status = statusData.status;
            summaryBtn.innerHTML = '<span class="loading-spinner"></span>' + status.charAt(0).toUpperCase() + status.slice(1) + '...';

            if (statusData.error) {
                throw new Error(statusData.error);
            }
        }

        // Then get the summary
        const summaryResponse = await fetch(`/api/summary/${currentVideoId}`);

        if (!summaryResponse.ok) {
            throw new Error('Failed to generate summary');
        }

        const data = await summaryResponse.json();

        // Display summary
        document.getElementById('video-summary').textContent = data.summary || 'No summary available';

        // Display takeaways
        const takeawaysList = document.getElementById('takeaways-list');
        takeawaysList.innerHTML = '';

        if (data.key_takeaways && data.key_takeaways.length > 0) {
            data.key_takeaways.forEach(takeaway => {
                const li = document.createElement('li');
                li.textContent = takeaway;
                takeawaysList.appendChild(li);
            });
        } else {
            takeawaysList.innerHTML = '<li>No key takeaways available</li>';
        }

        document.getElementById('summary-results').classList.remove('hidden');
        summaryBtn.innerHTML = 'Summary Complete';

    } catch (error) {
        alert('Failed to generate summary: ' + error.message);
        summaryBtn.innerHTML = 'Generate Summary';
        summaryBtn.disabled = false;
    }
}

// Visual Analysis Functions (kept from original)
async function startVisualAnalysis() {
    if (!currentUrl || !currentVideoId) {
        alert('Please process a video first');
        return;
    }

    const analyzeBtn = document.getElementById('analyze-btn');
    analyzeBtn.disabled = true;
    analyzeBtn.innerHTML = '<span class="loading-spinner"></span>Analyzing frames...';

    try {
        const response = await fetch('/api/visual/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: currentUrl })
        });

        if (!response.ok) {
            throw new Error('Failed to start visual analysis');
        }

        await pollVisualStatus(currentVideoId);

    } catch (error) {
        analyzeBtn.disabled = false;
        analyzeBtn.innerHTML = 'Analyze Video Frames';
        alert('Visual analysis failed: ' + error.message);
    }
}

async function pollVisualStatus(videoId) {
    const analyzeBtn = document.getElementById('analyze-btn');

    while (true) {
        const response = await fetch(`/api/visual/status/${videoId}`);
        const data = await response.json();

        if (data.status === 'completed') {
            await loadVisualResults(videoId);
            break;
        }

        if (data.status === 'error') {
            throw new Error(data.error || 'Analysis failed');
        }

        analyzeBtn.innerHTML = `<span class="loading-spinner"></span>${data.status}...`;
        await new Promise(resolve => setTimeout(resolve, 2000));
    }
}

async function loadVisualResults(videoId) {
    const response = await fetch(`/api/visual/result/${videoId}`);
    const data = await response.json();

    document.getElementById('frames-count').textContent = data.frames_analyzed;
    document.getElementById('persons-count').textContent = data.persons_detected;

    const colorSwatch = document.getElementById('shirt-color-swatch');
    const colorLabel = document.getElementById('shirt-color-label');

    let rgb = [128, 128, 128];
    if (data.detections && data.detections.length > 0) {
        rgb = data.detections[0].shirt_rgb || rgb;
    }

    colorSwatch.style.backgroundColor = `rgb(${rgb[0]}, ${rgb[1]}, ${rgb[2]})`;
    colorLabel.textContent = data.dominant_shirt_color;

    document.getElementById('visual-status').classList.add('hidden');
    document.getElementById('visual-results').classList.remove('hidden');

    const visualChat = document.getElementById('visual-chat-messages');
    visualChat.innerHTML = `
        <div class="chat-message assistant">
            Analysis complete! Detected <strong>${data.persons_detected}</strong> person(s) across
            <strong>${data.frames_analyzed}</strong> frames. Ask me questions about what you see!
        </div>
    `;
}

async function askVisualQuestion() {
    const questionInput = document.getElementById('visual-question-input');
    const chatMessages = document.getElementById('visual-chat-messages');

    const question = questionInput.value.trim();
    if (!question || !currentVideoId) return;

    chatMessages.innerHTML += `
        <div class="chat-message user">${escapeHtml(question)}</div>
    `;

    questionInput.value = '';
    questionInput.disabled = true;

    chatMessages.innerHTML += `
        <div class="chat-message assistant" id="visual-loading-message">
            <span class="loading-spinner"></span>Analyzing...
        </div>
    `;
    chatMessages.scrollTop = chatMessages.scrollHeight;

    try {
        const response = await fetch('/api/visual/ask', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                video_id: currentVideoId,
                question
            })
        });

        const data = await response.json();
        document.getElementById('visual-loading-message').remove();

        chatMessages.innerHTML += `
            <div class="chat-message assistant">${escapeHtml(data.answer)}</div>
        `;

    } catch (error) {
        document.getElementById('visual-loading-message').remove();
        chatMessages.innerHTML += `
            <div class="chat-message assistant">Sorry, I couldn't process your question.</div>
        `;
    } finally {
        questionInput.disabled = false;
        questionInput.focus();
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}

function handleVisualQuestionKeypress(event) {
    if (event.key === 'Enter') {
        askVisualQuestion();
    }
}

function showStatus(message, type) {
    const statusElement = document.getElementById('status-message');
    statusElement.textContent = message;
    statusElement.className = `status-message show ${type}`;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ===== YouTube Explorer Functions =====

function openYouTubeExplorer() {
    document.getElementById('youtube-explorer-modal').classList.remove('hidden');
    document.getElementById('explorer-input').focus();
}

function closeYouTubeExplorer() {
    document.getElementById('youtube-explorer-modal').classList.add('hidden');
}

function handleExplorerKeypress(event) {
    if (event.key === 'Enter') {
        sendExplorerMessage();
    }
}

async function sendExplorerMessage() {
    const input = document.getElementById('explorer-input');
    const messagesDiv = document.getElementById('explorer-messages');
    const videosDiv = document.getElementById('explorer-videos');
    const sendBtn = input.nextElementSibling;

    const message = input.value.trim();
    if (!message) return;

    // Add user message
    messagesDiv.innerHTML += '<div class="user-message">' + escapeHtml(message) + '</div>';

    input.value = '';
    input.disabled = true;
    sendBtn.disabled = true;

    // Add loading message
    const loadingId = 'loading-' + Date.now();
    messagesDiv.innerHTML += '<div class="bot-message" id="' + loadingId + '"><p>Searching YouTube<span class="loading-dots"></span></p></div>';
    messagesDiv.scrollTop = messagesDiv.scrollHeight;

    try {
        const response = await fetch('/api/youtube/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message })
        });

        const data = await response.json();

        // Remove loading message
        document.getElementById(loadingId).remove();

        // Add bot response
        messagesDiv.innerHTML += '<div class="bot-message"><p>' + formatBotResponse(data.response) + '</p></div>';

        // Display video results
        if (data.videos && data.videos.length > 0) {
            videosDiv.innerHTML = data.videos.map(video =>
                '<a href="' + video.url + '" target="_blank" class="video-result">' +
                '<img src="' + video.thumbnail + '" alt="' + escapeHtml(video.title) + '" class="video-thumbnail" onerror="this.src=\'https://via.placeholder.com/120x68?text=No+Thumb\'">' +
                '<div class="video-info">' +
                '<div class="video-title">' + escapeHtml(video.title) + '</div>' +
                '<div class="video-meta"><span class="video-channel">' + escapeHtml(video.channel || 'Unknown') + '</span> • ' + (video.view_count_formatted || 'N/A') + ' views • ' + (video.duration || '') + '</div>' +
                '</div></a>'
            ).join('');
        } else {
            videosDiv.innerHTML = '';
        }

    } catch (error) {
        document.getElementById(loadingId).remove();
        messagesDiv.innerHTML += '<div class="bot-message"><p>Sorry, I could not search YouTube right now. Please try again.</p></div>';
    } finally {
        input.disabled = false;
        sendBtn.disabled = false;
        input.focus();
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }
}

function formatBotResponse(text) {
    return text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n/g, '<br>');
}

// Close modal on escape key
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        closeYouTubeExplorer();
    }
});
