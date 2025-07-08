// Video Captioning Application
class VideoCaptionApp {
    constructor() {
        this.ws = null;
        this.clientId = this.generateClientId();
        this.currentVideoFile = null;
        this.currentJob = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        
        this.initializeElements();
        this.setupEventListeners();
        this.connectWebSocket();
    }

    generateClientId() {
        return 'client_' + Math.random().toString(36).substr(2, 9);
    }

    initializeElements() {
        // Video elements
        this.videoSection = document.getElementById('videoSection');
        this.uploadArea = document.getElementById('uploadArea');
        this.videoInput = document.getElementById('videoInput');
        this.videoPlayer = document.getElementById('videoPlayer');
        this.videoInfo = document.getElementById('videoInfo');
        this.videoName = document.getElementById('videoName');
        this.videoSize = document.getElementById('videoSize');

        // Configuration elements
        this.fontFamily = document.getElementById('fontFamily');
        this.fontSize = document.getElementById('fontSize');
        this.fontSizeValue = document.getElementById('fontSizeValue');
        this.textColor = document.getElementById('textColor');
        this.backgroundColor = document.getElementById('backgroundColor');
        this.opacity = document.getElementById('opacity');
        this.opacityValue = document.getElementById('opacityValue');
        this.position = document.getElementById('position');
        this.animation = document.getElementById('animation');
        this.processButton = document.getElementById('processButton');

        // Progress elements
        this.progressSection = document.getElementById('progressSection');
        this.progressFill = document.getElementById('progressFill');
        this.progressText = document.getElementById('progressText');

        // Timestamps elements
        this.timestampsSection = document.getElementById('timestampsSection');
        this.timestampsList = document.getElementById('timestampsList');

        // Status elements
        this.statusDot = document.getElementById('statusDot');
        this.statusText = document.getElementById('statusText');
    }

    setupEventListeners() {
        // File upload
        this.uploadArea.addEventListener('click', () => this.videoInput.click());
        this.videoInput.addEventListener('change', (e) => this.handleVideoUpload(e));

        // Drag and drop
        this.videoSection.addEventListener('dragover', (e) => this.handleDragOver(e));
        this.videoSection.addEventListener('dragleave', (e) => this.handleDragLeave(e));
        this.videoSection.addEventListener('drop', (e) => this.handleDrop(e));

        // Configuration changes
        this.fontSize.addEventListener('input', (e) => {
            this.fontSizeValue.textContent = e.target.value + 'px';
        });

        this.opacity.addEventListener('input', (e) => {
            this.opacityValue.textContent = e.target.value + '%';
        });

        // Process button
        this.processButton.addEventListener('click', () => this.processVideo());

        // Prevent default drag behaviors
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            this.videoSection.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
            });
        });
    }

    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/${this.clientId}`;
        
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.reconnectAttempts = 0;
            this.updateStatus('connected', 'Connected');
        };

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleWebSocketMessage(data);
        };

        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            this.updateStatus('disconnected', 'Disconnected');
            this.scheduleReconnect();
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.updateStatus('error', 'Connection Error');
        };
    }

    scheduleReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
            this.reconnectAttempts++;
            
            setTimeout(() => {
                console.log(`Reconnecting... Attempt ${this.reconnectAttempts}`);
                this.connectWebSocket();
            }, delay);
        }
    }

    updateStatus(status, text) {
        this.statusText.textContent = text;
        this.statusDot.className = `status-dot ${status === 'connected' ? 'connected' : ''}`;
    }

    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'job_update':
                this.handleJobUpdate(data);
                break;
            case 'pong':
                console.log('Pong received');
                break;
            default:
                console.log('Unknown message type:', data.type);
        }
    }

    handleJobUpdate(data) {
        if (data.job_id !== this.currentJob) return;

        // Update progress
        this.updateProgress(data.progress, data.message);

        // Handle different statuses
        switch (data.status) {
            case 'processing':
                this.showProgressSection();
                break;
            case 'completed':
                this.handleJobCompleted(data);
                break;
            case 'error':
                this.handleJobError(data);
                break;
        }

        // Update timestamps if available
        if (data.timestamps && data.timestamps.length > 0) {
            this.updateTimestamps(data.timestamps);
        }
    }

    handleDragOver(e) {
        this.videoSection.classList.add('dragover');
    }

    handleDragLeave(e) {
        this.videoSection.classList.remove('dragover');
    }

    handleDrop(e) {
        this.videoSection.classList.remove('dragover');
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            this.uploadVideo(files[0]);
        }
    }

    handleVideoUpload(e) {
        const file = e.target.files[0];
        if (file) {
            this.uploadVideo(file);
        }
    }

    async uploadVideo(file) {
        // Validate file type
        if (!file.type.startsWith('video/')) {
            this.showNotification('Error', 'Please select a video file', 'error');
            return;
        }

        // Show loading
        this.showNotification('Uploading', 'Uploading video file...', 'info');

        try {
            const formData = new FormData();
            formData.append('file', file);

            const response = await fetch('/upload-video', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error('Upload failed');
            }

            const data = await response.json();
            this.handleVideoUploaded(data);
            this.showNotification('Success', 'Video uploaded successfully!', 'success');

        } catch (error) {
            console.error('Upload error:', error);
            this.showNotification('Error', 'Failed to upload video', 'error');
        }
    }

    handleVideoUploaded(data) {
        this.currentVideoFile = data;
        
        // Hide upload area and show video player
        this.uploadArea.classList.add('hidden');
        this.videoPlayer.classList.remove('hidden');
        this.videoInfo.classList.remove('hidden');
        
        // Set video source
        this.videoPlayer.src = data.url;
        
        // Update video info
        this.videoName.textContent = data.original_name;
        this.videoSize.textContent = this.formatFileSize(data.size);
        
        // Enable process button
        this.processButton.disabled = false;
    }

    async processVideo() {
        if (!this.currentVideoFile) {
            this.showNotification('Error', 'Please upload a video first', 'error');
            return;
        }

        // Get configuration
        const config = this.getConfiguration();
        
        // Disable process button
        this.processButton.disabled = true;
        this.processButton.textContent = 'Processing...';

        try {
            const response = await fetch('/process-video', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    file_id: this.currentVideoFile.file_id,
                    config: config
                })
            });

            if (!response.ok) {
                throw new Error('Processing failed');
            }

            const data = await response.json();
            this.currentJob = data.job_id;
            this.showNotification('Processing', 'Video processing started!', 'info');

        } catch (error) {
            console.error('Processing error:', error);
            this.showNotification('Error', 'Failed to start processing', 'error');
            this.processButton.disabled = false;
            this.processButton.textContent = 'Process Video';
        }
    }

    getConfiguration() {
        return {
            fontFamily: this.fontFamily.value,
            fontSize: parseInt(this.fontSize.value),
            textColor: this.textColor.value,
            backgroundColor: this.backgroundColor.value,
            opacity: parseInt(this.opacity.value),
            position: this.position.value,
            animation: this.animation.value
        };
    }

    showProgressSection() {
        this.progressSection.classList.remove('hidden');
    }

    updateProgress(progress, message) {
        this.progressFill.style.width = `${progress}%`;
        this.progressText.textContent = message;
    }

    handleJobCompleted(data) {
        this.showNotification('Success', 'Video processing completed!', 'success');
        this.processButton.disabled = false;
        this.processButton.textContent = 'Process Video';
        
        // Show download link if available
        if (data.output_url) {
            this.showDownloadLink(data.output_url);
        }
    }

    handleJobError(data) {
        this.showNotification('Error', data.message || 'Processing failed', 'error');
        this.processButton.disabled = false;
        this.processButton.textContent = 'Process Video';
    }

    updateTimestamps(timestamps) {
        this.timestampsSection.classList.remove('hidden');
        
        // Clear existing timestamps
        this.timestampsList.innerHTML = '';
        
        // Add new timestamps
        timestamps.forEach(timestamp => {
            const item = document.createElement('div');
            item.className = 'timestamp-item';
            item.innerHTML = `
                <div class="timestamp-word">${timestamp.word}</div>
                <div class="timestamp-time">${timestamp.start.toFixed(2)}s - ${timestamp.end.toFixed(2)}s</div>
            `;
            
            // Add click handler to seek video
            item.addEventListener('click', () => {
                if (this.videoPlayer.currentTime !== undefined) {
                    this.videoPlayer.currentTime = timestamp.start;
                }
            });
            
            this.timestampsList.appendChild(item);
        });
    }

    showDownloadLink(url) {
        const downloadButton = document.createElement('a');
        downloadButton.href = url;
        downloadButton.download = 'captioned_video.mp4';
        downloadButton.className = 'process-button';
        downloadButton.textContent = 'Download Captioned Video';
        downloadButton.style.marginTop = '10px';
        downloadButton.style.textDecoration = 'none';
        downloadButton.style.display = 'inline-block';
        downloadButton.style.textAlign = 'center';
        
        // Add download button after process button
        this.processButton.parentNode.appendChild(downloadButton);
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    showNotification(title, message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <div style="font-weight: 600; margin-bottom: 5px;">${title}</div>
                    <div style="font-size: 14px; color: #666;">${message}</div>
                </div>
                <button onclick="this.parentElement.parentElement.remove()" style="background: none; border: none; font-size: 18px; cursor: pointer; color: #999;">&times;</button>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 5000);
    }

    // Send periodic pings to keep connection alive
    startPingInterval() {
        setInterval(() => {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.send(JSON.stringify({ type: 'ping' }));
            }
        }, 30000); // Ping every 30 seconds
    }
}

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    console.log('Video Captioning App Starting...');
    const app = new VideoCaptionApp();
    app.startPingInterval();
    
    // Add some interactive enhancements
    document.addEventListener('keydown', (e) => {
        // Escape key to close notifications
        if (e.key === 'Escape') {
            const notifications = document.querySelectorAll('.notification');
            notifications.forEach(notification => notification.remove());
        }
        
        // Space key to play/pause video
        if (e.key === ' ' && document.activeElement !== document.querySelector('input')) {
            e.preventDefault();
            const video = document.getElementById('videoPlayer');
            if (video && !video.classList.contains('hidden')) {
                if (video.paused) {
                    video.play();
                } else {
                    video.pause();
                }
            }
        }
    });
    
    // Add visual feedback for configuration changes
    const configInputs = document.querySelectorAll('.config-input');
    configInputs.forEach(input => {
        input.addEventListener('change', () => {
            input.style.borderColor = '#667eea';
            setTimeout(() => {
                input.style.borderColor = '#ddd';
            }, 500);
        });
    });
});

// Add some utility functions for better UX
function previewCaptionStyle() {
    const config = {
        fontFamily: document.getElementById('fontFamily').value,
        fontSize: document.getElementById('fontSize').value + 'px',
        textColor: document.getElementById('textColor').value,
        backgroundColor: document.getElementById('backgroundColor').value,
        opacity: document.getElementById('opacity').value + '%'
    };
    
    // Create preview element
    const preview = document.createElement('div');
    preview.style.cssText = `
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        font-family: ${config.fontFamily};
        font-size: ${config.fontSize};
        color: ${config.textColor};
        background-color: ${config.backgroundColor};
        opacity: ${parseInt(config.opacity) / 100};
        padding: 10px 20px;
        border-radius: 5px;
        z-index: 1000;
        pointer-events: none;
    `;
    preview.textContent = 'Sample Caption Text';
    
    document.body.appendChild(preview);
    
    setTimeout(() => {
        preview.remove();
    }, 2000);
}

// Add preview button functionality
document.addEventListener('DOMContentLoaded', () => {
    const previewButton = document.createElement('button');
    previewButton.textContent = 'Preview Style';
    previewButton.className = 'process-button';
    previewButton.style.marginTop = '10px';
    previewButton.style.background = 'linear-gradient(135deg, #28a745 0%, #20c997 100%)';
    previewButton.onclick = previewCaptionStyle;
    
    const configSection = document.querySelector('.config-section');
    const processButton = document.getElementById('processButton');
    configSection.insertBefore(previewButton, processButton);
});