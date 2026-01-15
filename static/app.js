let currentVideoId = null;
let currentUrl = null;
let visualAnalysisComplete = false;

async function processVideo() {
    const urlInput = document.getElementById('youtube-url');
    const processBtn = document.getElementById('process-btn');
    const statusMessage = document.getElementById('status-message');
    const resultsSection = document.getElementById('results-section');

    const url = urlInput.value.trim();
    if (!url) {
        showStatus('Please enter a YouTube URL', 'error');
        return;
    }

    currentUrl = url;
    processBtn.disabled = true;
    processBtn.innerHTML = '<span class="loading-spinner"></span>Processing...';
    resultsSection.classList.add('hidden');
    visualAnalysisComplete = false;

    try {
        showStatus('Starting video processing...', 'processing');

        const response = await fetch('/api/process', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to start processing');
        }

        const data = await response.json();
        currentVideoId = data.video_id;

        await pollStatus(currentVideoId);

    } catch (error) {
        showStatus(error.message, 'error');
    } finally {
        processBtn.disabled = false;
        processBtn.innerHTML = 'Summarize';
    }
}

async function pollStatus(videoId) {
    const statusMessages = {
        'queued': 'Waiting to start...',
        'downloading': 'Downloading video audio...',
        'transcribing': 'Transcribing audio (this may take a few minutes)...',
        'summarizing': 'Generating summary and key takeaways...',
        'indexing': 'Preparing Q&A system...',
        'completed': 'Processing complete!',
        'error': 'An error occurred'
    };

    while (true) {
        const response = await fetch(`/api/status/${videoId}`);
        const data = await response.json();

        showStatus(statusMessages[data.status] || data.status,
            data.status === 'error' ? 'error' : 'processing');

        if (data.status === 'completed') {
            showStatus('Processing complete!', 'success');
            await loadResults(videoId);
            break;
        }

        if (data.status === 'error') {
            throw new Error(data.error || 'Processing failed');
        }

        await new Promise(resolve => setTimeout(resolve, 2000));
    }
}

async function loadResults(videoId) {
    const response = await fetch(`/api/summary/${videoId}`);

    if (!response.ok) {
        throw new Error('Failed to load results');
    }

    const data = await response.json();

    document.getElementById('video-title').textContent = data.title;
    document.getElementById('summary-content').textContent = data.summary;

    const takeawaysList = document.getElementById('takeaways-list');
    takeawaysList.innerHTML = data.key_takeaways
        .map(t => `<li>${t}</li>`)
        .join('');

    document.getElementById('transcript-content').textContent = data.transcript;

    document.getElementById('chat-messages').innerHTML = '';
    document.getElementById('visual-chat-messages').innerHTML = '';

    // Reset visual analysis UI
    document.getElementById('visual-status').classList.remove('hidden');
    document.getElementById('visual-results').classList.add('hidden');
    document.getElementById('analyze-btn').disabled = false;
    document.getElementById('analyze-btn').innerHTML = 'Analyze Video Frames';

    document.getElementById('results-section').classList.remove('hidden');

    showTab('summary');
}

function showTab(tabName) {
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));

    document.querySelector(`.tab-btn[onclick="showTab('${tabName}')"]`).classList.add('active');
    document.getElementById(`${tabName}-tab`).classList.add('active');
}

async function askQuestion() {
    const questionInput = document.getElementById('question-input');
    const chatMessages = document.getElementById('chat-messages');

    const question = questionInput.value.trim();
    if (!question || !currentVideoId) return;

    chatMessages.innerHTML += `
        <div class="chat-message user">${escapeHtml(question)}</div>
    `;

    questionInput.value = '';
    questionInput.disabled = true;

    chatMessages.innerHTML += `
        <div class="chat-message assistant" id="loading-message">
            <span class="loading-spinner"></span>Thinking...
        </div>
    `;
    chatMessages.scrollTop = chatMessages.scrollHeight;

    try {
        const response = await fetch('/api/ask', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                video_id: currentVideoId,
                question
            })
        });

        if (!response.ok) {
            throw new Error('Failed to get answer');
        }

        const data = await response.json();

        document.getElementById('loading-message').remove();

        chatMessages.innerHTML += `
            <div class="chat-message assistant">${escapeHtml(data.answer)}</div>
        `;

    } catch (error) {
        document.getElementById('loading-message').remove();
        chatMessages.innerHTML += `
            <div class="chat-message assistant">Sorry, I couldn't process your question. Please try again.</div>
        `;
    } finally {
        questionInput.disabled = false;
        questionInput.focus();
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}

function handleQuestionKeypress(event) {
    if (event.key === 'Enter') {
        askQuestion();
    }
}

// Visual Analysis Functions
async function startVisualAnalysis() {
    if (!currentUrl || !currentVideoId) {
        alert('Please process a video first');
        return;
    }

    const analyzeBtn = document.getElementById('analyze-btn');
    const visualStatus = document.getElementById('visual-status');

    analyzeBtn.disabled = true;
    analyzeBtn.innerHTML = '<span class="loading-spinner"></span>Downloading video...';

    try {
        // Start visual analysis
        const response = await fetch('/api/visual/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: currentUrl })
        });

        if (!response.ok) {
            throw new Error('Failed to start visual analysis');
        }

        // Poll for completion
        await pollVisualStatus(currentVideoId);

    } catch (error) {
        analyzeBtn.disabled = false;
        analyzeBtn.innerHTML = 'Analyze Video Frames';
        alert('Visual analysis failed: ' + error.message);
    }
}

async function pollVisualStatus(videoId) {
    const analyzeBtn = document.getElementById('analyze-btn');
    const statusMessages = {
        'queued': 'Queued...',
        'downloading_video': 'Downloading video...',
        'analyzing': 'Analyzing frames with YOLO...',
        'completed': 'Analysis complete!',
        'error': 'Error'
    };

    while (true) {
        const response = await fetch(`/api/visual/status/${videoId}`);
        const data = await response.json();

        analyzeBtn.innerHTML = `<span class="loading-spinner"></span>${statusMessages[data.status] || data.status}`;

        if (data.status === 'completed') {
            await loadVisualResults(videoId);
            break;
        }

        if (data.status === 'error') {
            throw new Error(data.error || 'Analysis failed');
        }

        await new Promise(resolve => setTimeout(resolve, 2000));
    }
}

async function loadVisualResults(videoId) {
    const response = await fetch(`/api/visual/result/${videoId}`);

    if (!response.ok) {
        throw new Error('Failed to load visual results');
    }

    const data = await response.json();

    // Update UI
    document.getElementById('frames-count').textContent = data.frames_analyzed;
    document.getElementById('persons-count').textContent = data.persons_detected;

    const colorSwatch = document.getElementById('shirt-color-swatch');
    const colorLabel = document.getElementById('shirt-color-label');

    // Get RGB from first detection if available
    let rgb = [128, 128, 128];
    if (data.detections && data.detections.length > 0) {
        rgb = data.detections[0].shirt_rgb || rgb;
    }

    colorSwatch.style.backgroundColor = `rgb(${rgb[0]}, ${rgb[1]}, ${rgb[2]})`;
    colorLabel.textContent = data.dominant_shirt_color.charAt(0).toUpperCase() + data.dominant_shirt_color.slice(1);

    // Show results, hide button
    document.getElementById('visual-status').classList.add('hidden');
    document.getElementById('visual-results').classList.remove('hidden');

    visualAnalysisComplete = true;

    // Add initial message to visual chat
    const visualChat = document.getElementById('visual-chat-messages');
    visualChat.innerHTML = `
        <div class="chat-message assistant">
            Visual analysis complete! I detected <strong>${data.persons_detected}</strong> person(s) across
            <strong>${data.frames_analyzed}</strong> frames. The dominant shirt color is
            <strong>${data.dominant_shirt_color}</strong>. Ask me questions about what you see!
        </div>
    `;
}

async function askVisualQuestion() {
    const questionInput = document.getElementById('visual-question-input');
    const chatMessages = document.getElementById('visual-chat-messages');

    const question = questionInput.value.trim();
    if (!question || !currentVideoId) return;

    if (!visualAnalysisComplete) {
        chatMessages.innerHTML += `
            <div class="chat-message assistant">Please run the visual analysis first by clicking "Analyze Video Frames".</div>
        `;
        return;
    }

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

        if (!response.ok) {
            throw new Error('Failed to get answer');
        }

        const data = await response.json();

        document.getElementById('visual-loading-message').remove();

        chatMessages.innerHTML += `
            <div class="chat-message assistant">${escapeHtml(data.answer)}</div>
        `;

    } catch (error) {
        document.getElementById('visual-loading-message').remove();
        chatMessages.innerHTML += `
            <div class="chat-message assistant">Sorry, I couldn't process your visual question. Please try again.</div>
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
