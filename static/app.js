class ChatUI {
    constructor() {
        this.chatForm = document.getElementById('chat-form');
        this.userInput = document.getElementById('user-input');
        this.chatMessages = document.getElementById('chat-messages');
        this.galleryButton = document.querySelector('button i.fa-image').parentElement;
        this.videoButton = document.querySelector('button i.fa-video').parentElement;
        this.fileButton = document.querySelector('button i.fa-paperclip').parentElement;
        this.webButton = document.querySelector('button i.fa-globe').parentElement;
        this.localModelButton = document.querySelector('button i.fa-microchip').parentElement;
        this.ragToggle = document.getElementById('rag-toggle');
        this.ragIndicator = document.getElementById('rag-indicator');
        this.pencilButton = document.querySelector('i.fa-pencil').parentElement;
        this.drawingContainer = document.getElementById('drawing-container');
        this.closeDrawingButton = document.getElementById('close-drawing');
        this.drawingCanvas = document.getElementById('drawing-canvas');
        this.clearCanvasButton = document.getElementById('clear-canvas');
        
        // Initialize drawing mode state
        this.isDrawingMode = false;
        
        // Initialize RAG mode state
        this.isRagMode = false;
        
        // Generate new session ID on every page load
        this.sessionId = this.generateSessionId();
        this.isImageMode = false;
        this.isVideoMode = false;
        this.isWebMode = false;
        this.isLocalMode = false;
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.videoStream = null;
        
        // Form submit handler
        this.chatForm.addEventListener('submit', (e) => this.handleSubmit(e));
        
        // Input handlers
        this.userInput.addEventListener('keydown', this.handleKeyPress.bind(this));
        
        // RAG toggle handler
        this.ragToggle.addEventListener('change', this.handleRagToggle.bind(this));
        
        // Pencil button handler
        this.pencilButton.addEventListener('click', () => this.handleDrawingMode());
        
        // Close drawing button handler
        this.closeDrawingButton.addEventListener('click', () => this.handleDrawingMode());
        
        // Initially disable file upload
        this.updateFileUploadState();
        
        // Gallery button handler
        this.galleryButton.addEventListener('click', () => {
            this.isImageMode = !this.isImageMode;
            if (this.isImageMode) {
                this.galleryButton.classList.remove('text-gray-600');
                this.galleryButton.classList.add('text-red-500', 'bg-red-100', 'rounded-full');
                this.userInput.placeholder = "Describe the image you want to generate...";
            } else {
                this.galleryButton.classList.remove('text-red-500', 'bg-red-100', 'rounded-full');
                this.galleryButton.classList.add('text-gray-600');
                this.userInput.placeholder = "Type your message...";
            }
        });

        // Video button handler
        this.videoButton.addEventListener('click', () => this.handleVideoButton());

        // Web button handler
        this.webButton.addEventListener('click', () => {
            this.isWebMode = !this.isWebMode;
            // Reset other modes
            this.isImageMode = false;
            this.isVideoMode = false;
            
            if (this.isWebMode) {
                this.webButton.classList.remove('text-gray-600');
                this.webButton.classList.add('text-red-500', 'bg-red-100', 'rounded-full');
                this.userInput.placeholder = "Enter your web search query...";
                
                // Reset other buttons
                this.galleryButton.classList.remove('text-red-500', 'bg-red-100', 'rounded-full');
                this.galleryButton.classList.add('text-gray-600');
                this.videoButton.classList.remove('text-red-500', 'bg-red-100', 'rounded-full');
                this.videoButton.classList.add('text-gray-600');
            } else {
                this.webButton.classList.remove('text-red-500', 'bg-red-100', 'rounded-full');
                this.webButton.classList.add('text-gray-600');
                this.userInput.placeholder = "Type your message...";
            }
        });

        // Local Model button handler
        this.localModelButton.addEventListener('click', () => {
            if (this.isRagMode) {
                // If RAG mode is active, show notification
                const notification = document.createElement('div');
                notification.className = 'fixed top-4 right-4 bg-yellow-100 border-l-4 border-yellow-500 text-yellow-700 p-4 rounded shadow-md transition-opacity duration-500';
                notification.innerHTML = `
                    <div class="flex items-center">
                        <div class="py-1">
                            <svg class="w-6 h-6 mr-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                            </svg>
                        </div>
                        <div>
                            <p class="font-bold">RAG Mode Active</p>
                            <p class="text-sm">Local LLM is already being used by RAG mode.</p>
                        </div>
                    </div>
                `;
                document.body.appendChild(notification);
                
                setTimeout(() => {
                    notification.style.opacity = '0';
                    setTimeout(() => notification.remove(), 500);
                }, 3000);
                
                return;
            }
            
            this.isLocalMode = !this.isLocalMode;
            // Reset other modes
            this.isImageMode = false;
            this.isVideoMode = false;
            this.isWebMode = false;
            
            if (this.isLocalMode) {
                this.updateLocalModelIndicator(true);
                this.userInput.placeholder = "Using Llama 3.2 3B local model...";
                
                // Reset other buttons
                this.galleryButton.classList.remove('text-red-500', 'bg-red-100', 'rounded-full');
                this.galleryButton.classList.add('text-gray-600');
                this.videoButton.classList.remove('text-red-500', 'bg-red-100', 'rounded-full');
                this.videoButton.classList.add('text-gray-600');
                this.webButton.classList.remove('text-red-500', 'bg-red-100', 'rounded-full');
                this.webButton.classList.add('text-gray-600');
            } else {
                this.updateLocalModelIndicator(false);
                this.userInput.placeholder = "Type your message...";
            }
        });

        // Helper method to update local model indicator
        this.updateLocalModelIndicator = (show) => {
            if (show) {
                this.localModelButton.classList.remove('text-gray-600');
                this.localModelButton.classList.add('text-red-500', 'bg-red-100', 'rounded-full');
            } else {
                this.localModelButton.classList.remove('text-red-500', 'bg-red-100', 'rounded-full');
                this.localModelButton.classList.add('text-gray-600');
            }
        };

        // RAG toggle handler
        this.ragToggle.addEventListener('change', (event) => {
            this.isRagMode = event.target.checked;
            const ragIndicator = document.getElementById('rag-indicator');
            ragIndicator.style.display = this.isRagMode ? 'inline-block' : 'none';
            
            if (this.isRagMode) {
                // Show local model indicator since RAG uses local LLM
                this.updateLocalModelIndicator(true);
                this.userInput.placeholder = "RAG mode active - Using documents for context...";
            } else {
                // If local mode was active before, keep its state
                if (this.isLocalMode) {
                    this.updateLocalModelIndicator(true);
                    this.userInput.placeholder = "Using Llama 3.2 3B local model...";
                } else {
                    this.updateLocalModelIndicator(false);
                    this.userInput.placeholder = "Type your message...";
                }
            }
            
            this.updateFileUploadState();
        });

        this.md = window.markdownit({
            html: false,
            xhtmlOut: false,
            breaks: true,
            linkify: true,
            typographer: true,
            highlight: function (str, lang) {
                if (lang && hljs.getLanguage(lang)) {
                    try {
                        return hljs.highlight(str, { language: lang }).value;
                    } catch (__) {}
                }
                return '';
            }
        });

        this.md.renderer.rules.paragraph_open = () => '<p class="mb-2">';
        this.md.renderer.rules.code_block = (tokens, idx) => {
            const content = tokens[idx].content;
            return this.createCodeBlockHtml(content);
        };

        this.md.renderer.rules.fence = (tokens, idx) => {
            const token = tokens[idx];
            const lang = token.info || '';
            return this.createCodeBlockHtml(token.content, lang);
        };

        // Set initial height for input
        this.userInput.style.height = '44px';

        // File upload elements
        this.fileInput = document.getElementById('file-input');
        this.fileInput.addEventListener('change', this.handleFileUpload.bind(this));

        // Add clear canvas button handler
        this.clearCanvasButton.addEventListener('click', () => this.clearCanvas());
    }

    generateSessionId() {
        return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    handleKeyPress(e) {
        // If Enter is pressed without Shift
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault(); // Prevent default newline
            this.handleSubmit(new Event('submit')); // Trigger form submission
        }
        // If Shift + Enter is pressed, let the default behavior happen (new line)
    }

    async handleSubmit(e) {
        e.preventDefault();
        const message = this.userInput.value.trim();
        if (!message) return;

        this.addMessage('user', message);
        this.userInput.value = '';
        const typingId = this.addTypingIndicator();

        try {
            const messageDiv = document.createElement('div');
            messageDiv.className = 'max-w-[85%] mr-auto animate-fade-in my-2';
            
            const bubble = document.createElement('div');
            bubble.className = 'p-3 rounded-2xl bg-gray-100 text-gray-800 markdown-body relative group';
            
            const contentDiv = document.createElement('div');
            contentDiv.className = 'streaming-content';

            const copyButton = document.createElement('button');
            copyButton.className = 'absolute right-2 top-2 opacity-0 group-hover:opacity-100 transition-opacity bg-gray-700 hover:bg-gray-600 text-white px-2 py-1 rounded text-sm flex items-center gap-1';
            copyButton.innerHTML = `
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                        d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3"/>
                </svg>
                Copy
            `;
            copyButton.onclick = function() {
                const textToCopy = contentDiv.textContent;
                navigator.clipboard.writeText(textToCopy).then(() => {
                    this.innerHTML = `
                        <span class="text-green-400 flex items-center gap-1">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
                            </svg>
                            Copied!
                        </span>
                    `;
                    setTimeout(() => {
                        this.innerHTML = `
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                                    d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3"/>
                            </svg>
                            Copy
                        `;
                    }, 2000);
                });
            };
            
            bubble.appendChild(copyButton);
            bubble.appendChild(contentDiv);
            messageDiv.appendChild(bubble);
            
            this.removeTypingIndicator(typingId);
            this.chatMessages.appendChild(messageDiv);
            this.scrollToBottom();

            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    message,
                    session_id: this.sessionId,
                    is_image_mode: this.isImageMode,
                    is_video_mode: this.isVideoMode,
                    is_rag_mode: this.isRagMode,
                    is_web_mode: this.isWebMode,
                    is_local_mode: this.isLocalMode
                })
            });

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let responseText = '';
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (!line.trim()) continue;
                    
                    try {
                        const data = JSON.parse(line);
                        if (data.chunk) {
                            responseText += data.chunk;
                            contentDiv.innerHTML = this.formatMessage(responseText);
                            contentDiv.querySelectorAll('pre code').forEach((block) => {
                                hljs.highlightElement(block);
                            });
                            this.scrollToBottom();
                            
                            // Update local model indicator if using local LLM
                            if (data.is_local_llm) {
                                this.localModelButton.classList.remove('text-gray-600');
                                this.localModelButton.classList.add('text-red-500', 'bg-red-100', 'rounded-full');
                            }
                        }
                    } catch (e) {
                        // Silent fail for parse errors
                    }
                }
            }

            if (buffer.trim()) {
                try {
                    const data = JSON.parse(buffer);
                    if (data.chunk) {
                        responseText += data.chunk;
                        contentDiv.innerHTML = this.formatMessage(responseText);
                        contentDiv.querySelectorAll('pre code').forEach((block) => {
                            hljs.highlightElement(block);
                        });
                        this.scrollToBottom();
                    }
                } catch (e) {
                    // Silent fail for parse errors
                }
            }
        } catch (error) {
            this.removeTypingIndicator(typingId);
            this.addMessage('error', 'Sorry, something went wrong. Please try again.');
        }
    }

    addTypingIndicator() {
        const id = 'typing-' + Date.now();
        const html = `
            <div id="${id}" class="flex items-center gap-2 text-gray-500 animate-fade-in">
                <div class="flex items-center gap-1">
                    <div class="w-2 h-2 rounded-full bg-gray-400 animate-bounce"></div>
                    <div class="w-2 h-2 rounded-full bg-gray-400 animate-bounce" style="animation-delay: 0.2s"></div>
                    <div class="w-2 h-2 rounded-full bg-gray-400 animate-bounce" style="animation-delay: 0.4s"></div>
                </div>
                <span class="text-sm">AI is typing...</span>
            </div>
        `;
        this.chatMessages.insertAdjacentHTML('beforeend', html);
        this.scrollToBottom();
        return id;
    }

    removeTypingIndicator(id) {
        const element = document.getElementById(id);
        if (element) {
            element.remove();
        }
    }

    addMessage(type, content) {
        const messageDiv = document.createElement('div');
        const isImage = content.startsWith('![Generated Image]');
        
        // For images, don't add any max-width, just the actual image width
        // For user messages, use fit-content to make them compact
        messageDiv.className = `${type === 'user' ? 'ml-auto w-fit max-w-[85%]' : ''} animate-fade-in my-2`;
        
        const bubble = document.createElement('div');
        // For images, don't add background color or padding
        bubble.className = `${
            isImage ? '' :
            type === 'user' 
                ? 'p-3 bg-primary text-white rounded-2xl'
                : type === 'error'
                    ? 'p-3 bg-red-500 text-white rounded-2xl'
                    : 'p-3 bg-gray-100 text-gray-800 rounded-2xl'
        } markdown-body relative group`;
        
        const formattedContent = this.formatMessage(content);
        const contentDiv = document.createElement('div');
        contentDiv.innerHTML = formattedContent;

        // Add copy button for text responses (not for images or user messages)
        if (!isImage && type !== 'user') {
            const copyButton = document.createElement('button');
            copyButton.className = 'absolute right-2 top-2 opacity-0 group-hover:opacity-100 transition-opacity bg-gray-700 hover:bg-gray-600 text-white px-2 py-1 rounded text-sm flex items-center gap-1';
            copyButton.innerHTML = `
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                        d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3"/>
                </svg>
                Copy
            `;
            copyButton.onclick = function() {
                const textToCopy = contentDiv.textContent;
                navigator.clipboard.writeText(textToCopy).then(() => {
                    this.innerHTML = `
                        <span class="text-green-400 flex items-center gap-1">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
                            </svg>
                            Copied!
                        </span>
                    `;
                    setTimeout(() => {
                        this.innerHTML = `
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                                    d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3"/>
                            </svg>
                            Copy
                        `;
                    }, 2000);
                });
            };
            bubble.appendChild(copyButton);
        }
        
        bubble.appendChild(contentDiv);
        messageDiv.appendChild(bubble);
        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
    }

    formatMessage(content) {
        // Special handling for image markdown
        if (content.startsWith('![Generated Image]')) {
            const base64Data = content.match(/base64,([^)]*)/)[1];
            return `
                <div class="relative group w-80">
                    <img src="data:image/png;base64,${base64Data}" alt="Generated Image" class="rounded-lg w-full">
                    <button onclick="this.parentElement.querySelector('a').click()" 
                            class="absolute top-2 right-2 bg-gray-800/75 hover:bg-gray-700 text-white p-2 rounded-full opacity-0 group-hover:opacity-100 transition-opacity">
                        <i class="fas fa-download"></i>
                    </button>
                    <a href="data:image/png;base64,${base64Data}" 
                       download="generated-image.png" 
                       class="hidden">Download</a>
                </div>`;
        }
        return this.md.render(content);
    }

    scrollToBottom() {
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }

    createCodeBlockHtml(code, lang = '') {
        const id = 'code-' + Date.now() + Math.random().toString(36).substr(2, 9);
        return `
            <div class="relative group">
                <div class="absolute right-2 top-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button onclick="this.innerHTML = '<span class=\\'text-green-400 flex items-center gap-1\\'><svg class=\\'w-4 h-4\\' fill=\\'none\\' stroke=\\'currentColor\\' viewBox=\\'0 0 24 24\\'><path stroke-linecap=\\'round\\' stroke-linejoin=\\'round\\' stroke-width=\\'2\\' d=\\'M5 13l4 4L19 7\\'/></svg>Copied!</span>'; navigator.clipboard.writeText(document.getElementById('${id}').textContent).then(() => { setTimeout(() => { this.innerHTML = '<svg class=\\'w-4 h-4\\' fill=\\'none\\' stroke=\\'currentColor\\' viewBox=\\'0 0 24 24\\'><path stroke-linecap=\\'round\\' stroke-linejoin=\\'round\\' stroke-width=\\'2\\' d=\\'M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3\\'/></svg>Copy'; }, 2000); });"
                        class="bg-gray-700 hover:bg-gray-600 text-white px-2 py-1 rounded text-sm flex items-center gap-1">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                                d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3"/>
                        </svg>
                        Copy
                    </button>
                </div>
                <pre class="my-2 relative"><code id="${id}" class="${lang}">${code}</code></pre>
            </div>
        `;
    }

    async handleVideoButton() {
        this.isVideoMode = !this.isVideoMode;
        
        if (this.isVideoMode) {
            // Start recording mode
            this.videoButton.classList.remove('text-gray-600');
            this.videoButton.classList.add('text-red-500', 'bg-red-100', 'rounded-full');
            this.userInput.placeholder = "Recording audio...";
            
            try {
                // Request audio permission and start recording
                const audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
                this.mediaRecorder = new MediaRecorder(audioStream);
                this.audioChunks = [];
                
                this.mediaRecorder.ondataavailable = (event) => {
                    this.audioChunks.push(event.data);
                };
                
                this.mediaRecorder.start();
                
                // Open camera for preview
                const videoStream = await navigator.mediaDevices.getUserMedia({ video: true });
                this.videoStream = videoStream;
                
                // Create and show camera preview
                const preview = document.createElement('video');
                preview.id = 'camera-preview';
                preview.autoplay = true;
                preview.className = 'fixed bottom-24 right-4 w-64 h-48 rounded-lg shadow-lg';
                preview.srcObject = videoStream;
                document.body.appendChild(preview);
                
            } catch (error) {
                console.error('Error accessing media devices:', error);
                this.addMessage('error', 'Failed to access camera or microphone. Please check permissions.');
                this.resetVideoMode();
            }
        } else {
            // Stop recording mode
            try {
                // Stop audio recording
                if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
                    this.mediaRecorder.stop();
                    await new Promise(resolve => {
                        this.mediaRecorder.onstop = async () => {
                            // Get audio as base64
                            const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
                            const audioBase64 = await this.blobToBase64(audioBlob);
                            
                            // Take final picture
                            const preview = document.getElementById('camera-preview');
                            const canvas = document.createElement('canvas');
                            canvas.width = preview.videoWidth;
                            canvas.height = preview.videoHeight;
                            canvas.getContext('2d').drawImage(preview, 0, 0);
                            const imageBase64 = canvas.toDataURL('image/jpeg').split(',')[1];
                            
                            // Send to backend
                            this.sendAudioAndImage(audioBase64, imageBase64);
                            resolve();
                        };
                    });
                }
                
                // Clean up media streams
                this.cleanupMediaStreams();
                
                // Reset UI
                this.resetVideoMode();
                
            } catch (error) {
                console.error('Error stopping recording:', error);
                this.addMessage('error', 'Failed to process recording. Please try again.');
                this.resetVideoMode();
            }
        }
    }
    
    resetVideoMode() {
        this.isVideoMode = false;
        this.videoButton.classList.remove('text-red-500', 'bg-red-100', 'rounded-full');
        this.videoButton.classList.add('text-gray-600');
        this.userInput.placeholder = "Type your message...";
        this.cleanupMediaStreams();
    }
    
    cleanupMediaStreams() {
        // Stop and remove camera preview
        const preview = document.getElementById('camera-preview');
        if (preview) {
            preview.remove();
        }
        
        // Stop all tracks in both streams
        if (this.videoStream) {
            this.videoStream.getTracks().forEach(track => track.stop());
            this.videoStream = null;
        }
        if (this.mediaRecorder) {
            this.mediaRecorder.stream.getTracks().forEach(track => track.stop());
            this.mediaRecorder = null;
        }
    }
    
    blobToBase64(blob) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onloadend = () => resolve(reader.result.split(',')[1]);
            reader.onerror = reject;
            reader.readAsDataURL(blob);
        });
    }
    
    async sendAudioAndImage(audioBase64, imageBase64) {
        try {
            console.log("Sending audio and image to backend...");
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    session_id: this.sessionId,
                    is_video_mode: true,
                    audio_data: audioBase64,
                    image_data: imageBase64
                })
            });
            
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';
                
                for (const line of lines) {
                    if (!line.trim()) continue;
                    try {
                        const data = JSON.parse(line);
                        console.log("Received response data:", data);
                        if (data.audio) {
                            console.log("Attempting to play audio response...");
                            // Explicitly use audio/mp3 since we know Wavenet returns MP3
                            const audio = new Audio(`data:audio/mp3;base64,${data.audio}`);
                            await audio.play();
                            console.log("Audio playback started successfully");
                        }
                    } catch (e) {
                        console.error('Error processing response:', e);
                    }
                }
            }
        } catch (error) {
            console.error('Error sending audio and image:', error);
        }
    }

    // New method to handle RAG toggle
    handleRagToggle(event) {
        this.isRagMode = event.target.checked;
        const ragIndicator = document.getElementById('rag-indicator');
        ragIndicator.style.display = this.isRagMode ? 'inline-block' : 'none';
        
        if (this.isRagMode) {
            // Show local model indicator since RAG uses local LLM
            this.updateLocalModelIndicator(true);
            this.userInput.placeholder = "RAG mode active - Using documents for context...";
        } else {
            // If local mode was active before, keep its state
            if (this.isLocalMode) {
                this.updateLocalModelIndicator(true);
                this.userInput.placeholder = "Using Llama 3.2 3B local model...";
            } else {
                this.updateLocalModelIndicator(false);
                this.userInput.placeholder = "Type your message...";
            }
        }
        
        this.updateFileUploadState();
    }

    // New method to update file upload button state
    updateFileUploadState() {
        const fileInput = document.getElementById('file-input');
        if (this.isRagMode) {
            this.fileButton.classList.remove('opacity-50', 'cursor-not-allowed');
            this.fileButton.classList.add('cursor-pointer');
            fileInput.disabled = false;
        } else {
            this.fileButton.classList.add('opacity-50', 'cursor-not-allowed');
            this.fileButton.classList.remove('cursor-pointer');
            fileInput.disabled = true;
        }
    }

    async handleFileUpload(event) {
        const file = event.target.files[0];
        if (!file) return;

        try {
            // Add loading message
            this.addMessage('system', 'Uploading and processing document...');
            
            // Create FormData and append file and session_id
            const formData = new FormData();
            formData.append('file', file);
            formData.append('session_id', this.sessionId);
            
            console.log('Uploading with session ID:', this.sessionId); // Add logging
            
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (!response.ok) {
                throw new Error(result.message || 'Upload failed');
            }
            
            this.addMessage('system', result.message || 'Document uploaded and processed successfully!');
            
        } catch (error) {
            console.error('Error uploading file:', error);
            this.addMessage('error', `Error uploading document: ${error.message}`);
        } finally {
            // Reset file input
            event.target.value = '';
        }
    }

    handleDrawingMode() {
        this.isDrawingMode = !this.isDrawingMode;
        
        if (this.isDrawingMode) {
            // Show drawing canvas
            this.drawingContainer.classList.remove('hidden');
            this.drawingContainer.classList.remove('translate-x-full');
            this.pencilButton.classList.add('text-red-500', 'bg-red-100', 'rounded-full');
            
            // Initialize canvas
            this.initializeCanvas();
            
            // Make sure old WebSocket is cleaned up before creating new one
            if (this.ws) {
                this.cleanupWebSocket().then(() => {
                    // Initialize new WebSocket after cleanup
                    this.initializeAudioAndWebSocket();
                });
            } else {
                // No existing WebSocket, just initialize
                this.initializeAudioAndWebSocket();
            }
        } else {
            // Hide drawing canvas
            this.drawingContainer.classList.add('hidden');
            this.drawingContainer.classList.add('translate-x-full');
            this.pencilButton.classList.remove('text-red-500', 'bg-red-100', 'rounded-full');
            
            // Set flag to stop processing
            this.isProcessingEnabled = false;
            
            // Cleanup immediately
            this.cleanupWebSocket();
        }
    }

    async initializeAudioAndWebSocket() {
        // Initialize WebSocket
        this.ws = new WebSocket(`ws://${window.location.host}/ws`);
        this.isProcessingEnabled = true;  // Enable processing
        
        this.ws.onopen = async () => {
            console.log('WebSocket connected');
            // Send initial config
            this.ws.send(JSON.stringify({
                setup: {
                    generation_config: {
                        response_modalities: ["AUDIO"]
                    },
                    voice_config: {
                        voice_activity_detection: true,
                        prebuilt_voice_config: {
                            voice_name: "Charon"
                        }
                    }
                }
            }));

            try {
                console.log("Requesting screen capture permission...");
                // Initialize screen capture without cleanup
                this.currentFrameB64 = null;
                const displayStream = await navigator.mediaDevices.getDisplayMedia({
                    video: {
                        cursor: "always"
                    },
                    audio: false
                }).catch(error => {
                    console.error("Screen capture permission error:", error);
                    throw new Error("Screen sharing permission is required for the drawing assistant.");
                });
                
                console.log("Screen capture permission granted.");
                
                // Create video element to capture frames
                const videoElement = document.createElement('video');
                videoElement.srcObject = displayStream;
                await videoElement.play();
                
                // Create canvas for frame capture
                const captureCanvas = document.createElement('canvas');
                const ctx = captureCanvas.getContext('2d');
                
                this.captureInterval = setInterval(() => {
                    if (!this.isProcessingEnabled) return;  // Skip if processing is disabled
                    
                    // Set canvas size to match video dimensions
                    captureCanvas.width = videoElement.videoWidth;
                    captureCanvas.height = videoElement.videoHeight;
                    
                    // Draw current video frame to canvas
                    ctx.drawImage(videoElement, 0, 0, captureCanvas.width, captureCanvas.height);
                    
                    // Convert to base64
                    this.currentFrameB64 = captureCanvas.toDataURL("image/jpeg").split(",")[1].trim();
                }, 600);  // Changed to 600ms

                // Store stream for cleanup
                this.displayStream = displayStream;

                // Initialize audio context for playback
                this.audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 24000 });
                await this.audioContext.audioWorklet.addModule('static/pcm-processor.js');
                this.workletNode = new AudioWorkletNode(this.audioContext, 'pcm-processor');
                this.workletNode.connect(this.audioContext.destination);

                console.log("Requesting microphone permission...");
                // Initialize audio recording without cleanup
                const stream = await navigator.mediaDevices.getUserMedia({
                    audio: {
                        channelCount: 1,
                        sampleRate: 16000
                    }
                }).catch(error => {
                    console.error("Microphone permission error:", error);
                    throw new Error("Microphone permission is required for voice interaction.");
                });
                
                console.log("Microphone permission granted.");

                // Create recording AudioContext
                this.recordingContext = new AudioContext({
                    sampleRate: 16000,
                    channelCount: 1
                });

                const source = this.recordingContext.createMediaStreamSource(stream);
                this.processor = this.recordingContext.createScriptProcessor(4096, 1, 1);
                
                let pcmData = [];
                
                this.processor.onaudioprocess = (e) => {
                    if (!this.isProcessingEnabled || !this.ws || this.ws.readyState !== WebSocket.OPEN) return;
                    
                    const inputData = e.inputBuffer.getChannelData(0);
                    const pcmInt16 = new Int16Array(inputData.length);
                    for (let i = 0; i < inputData.length; i++) {
                        pcmInt16[i] = Math.max(-1, Math.min(1, inputData[i])) * 0x7FFF;
                    }
                    pcmData.push(...pcmInt16);
                    
                    // Send accumulated PCM data every 3 seconds
                    if (pcmData.length >= 9600) { // 16000 samples/sec * 0.6 seconds
                        const buffer = new ArrayBuffer(pcmData.length * 2);
                        const view = new DataView(buffer);
                        pcmData.forEach((value, index) => {
                            view.setInt16(index * 2, value, true);
                        });
                        
                        // Send both audio and current screen capture
                        const mediaChunks = [{
                            mime_type: "audio/pcm",
                            data: btoa(String.fromCharCode.apply(null, new Uint8Array(buffer)))
                        }];

                        // Add image if available
                        if (this.currentFrameB64) {
                            mediaChunks.push({
                                mime_type: "image/jpeg",
                                data: this.currentFrameB64
                            });
                        }

                        if (this.isProcessingEnabled && this.ws && this.ws.readyState === WebSocket.OPEN) {
                            this.ws.send(JSON.stringify({
                                realtime_input: {
                                    media_chunks: mediaChunks
                                }
                            }));
                        }
                        pcmData = [];
                    }
                };
                
                source.connect(this.processor);
                this.processor.connect(this.recordingContext.destination);
                
                this.audioStream = stream;
                
            } catch (error) {
                console.error("Error initializing permissions:", error);
                // Show error message to user
                const errorDiv = document.createElement('div');
                errorDiv.className = 'fixed top-4 right-4 bg-red-100 border-l-4 border-red-500 text-red-700 p-4 rounded shadow-md';
                errorDiv.innerHTML = `
                    <div class="flex items-center">
                        <div class="py-1">
                            <svg class="w-6 h-6 mr-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                            </svg>
                        </div>
                        <div>
                            <p class="font-bold">Permission Required</p>
                            <p class="text-sm">${error.message}</p>
                        </div>
                    </div>
                `;
                document.body.appendChild(errorDiv);
                setTimeout(() => errorDiv.remove(), 5000);
                
                // Reset drawing mode
                this.isDrawingMode = false;
                this.drawingContainer.classList.add('hidden');
                this.drawingContainer.classList.add('translate-x-full');
                this.pencilButton.classList.remove('text-red-500', 'bg-red-100', 'rounded-full');
            }
        };
        
        this.ws.onmessage = async (event) => {
            if (!this.isProcessingEnabled) return;  // Skip if processing is disabled
            try {
                const data = JSON.parse(event.data);
                
                // Handle audio responses
                if (data.audio) {
                    await this.playAudioResponse(data.audio);
                }
                
                // Handle turn completion
                if (data.server_content && data.server_content.turn_complete) {
                    console.log('Turn complete - Gemini finished speaking');
                }
                
                // Handle interruptions
                if (data.server_content && data.server_content.model_turn === null) {
                    console.log('User interrupted - Gemini stopped speaking');
                }
                
            } catch (e) {
                console.error('Error processing WebSocket message:', e);
            }
        };
        
        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.isProcessingEnabled = false;  // Disable processing on error
        };
        
        this.ws.onclose = () => {
            console.log('WebSocket closed');
            this.isProcessingEnabled = false;  // Disable processing when closed
            this.cleanupWebSocket();
        };
    }

    async playAudioResponse(base64Audio) {
        try {
            if (this.audioContext.state === 'suspended') {
                await this.audioContext.resume();
            }
            
            // Convert base64 to array buffer
            const binaryString = window.atob(base64Audio);
            const bytes = new Uint8Array(binaryString.length);
            for (let i = 0; i < binaryString.length; i++) {
                bytes[i] = binaryString.charCodeAt(i);
            }
            
            // Convert PCM16LE to Float32
            const pcmData = new Int16Array(bytes.buffer);
            const float32Data = new Float32Array(pcmData.length);
            for (let i = 0; i < pcmData.length; i++) {
                float32Data[i] = pcmData[i] / 32768;
            }
            
            // Send to audio worklet for playback
            this.workletNode.port.postMessage(float32Data);
            
        } catch (error) {
            console.error('Error playing audio response:', error);
        }
    }

    async cleanupWebSocket() {
        return new Promise((resolve) => {
            // Clear screen capture interval
            if (this.captureInterval) {
                clearInterval(this.captureInterval);
                this.captureInterval = null;
            }

            // Cleanup display stream
            if (this.displayStream) {
                this.displayStream.getTracks().forEach(track => track.stop());
                this.displayStream = null;
            }

            // Cleanup audio resources
            if (this.audioStream) {
                this.audioStream.getTracks().forEach(track => track.stop());
                this.audioStream = null;
            }
            if (this.recordingContext) {
                this.recordingContext.close();
                this.recordingContext = null;
            }
            if (this.audioContext) {
                this.audioContext.close();
                this.audioContext = null;
            }
            if (this.processor) {
                this.processor.disconnect();
                this.processor = null;
            }
            if (this.workletNode) {
                this.workletNode.disconnect();
                this.workletNode = null;
            }

            // Close WebSocket with proper cleanup
            if (this.ws) {
                if (this.ws.readyState === WebSocket.OPEN) {
                    this.ws.onclose = () => {
                        this.ws = null;
                        resolve();
                    };
                    this.ws.close();
                } else {
                    this.ws = null;
                    resolve();
                }
            } else {
                resolve();
            }
        });
    }

    initializeCanvas() {
        const canvas = this.drawingCanvas;
        const ctx = canvas.getContext('2d');
        
        // Set canvas size
        canvas.width = this.drawingContainer.clientWidth;
        canvas.height = this.drawingContainer.clientHeight;
        
        // Set initial canvas state
        ctx.fillStyle = 'white';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        
        // Set initial drawing style
        ctx.strokeStyle = '#000000';
        ctx.lineWidth = 2;
        ctx.lineCap = 'round';
        
        // Drawing state
        let isDrawing = false;
        let lastX = 0;
        let lastY = 0;
        let isEraser = false;
        
        // Tool buttons and controls
        const pencilTool = document.getElementById('pencil-tool');
        const eraserTool = document.getElementById('eraser-tool');
        const lineWidthSlider = document.getElementById('line-width');
        const widthValue = document.getElementById('width-value');
        const colorPicker = document.getElementById('color-picker');
        
        // Line width slider handler
        lineWidthSlider.addEventListener('input', () => {
            const width = parseInt(lineWidthSlider.value);
            ctx.lineWidth = width;
            widthValue.textContent = `${width}px`;
        });

        // Color picker handler
        colorPicker.addEventListener('input', (e) => {
            if (!isEraser) {
                ctx.strokeStyle = e.target.value;
            }
        });
        
        // Tool selection handlers
        pencilTool.addEventListener('click', () => {
            isEraser = false;
            ctx.strokeStyle = colorPicker.value;  // Use current color picker value
            ctx.lineWidth = parseInt(lineWidthSlider.value);  // Use slider value
            
            // Update UI
            pencilTool.classList.add('active');
            eraserTool.classList.remove('active');
        });
        
        eraserTool.addEventListener('click', () => {
            isEraser = true;
            ctx.strokeStyle = '#FFFFFF';  // White for eraser
            ctx.lineWidth = parseInt(lineWidthSlider.value);  // Use slider value
            
            // Update UI
            eraserTool.classList.add('active');
            pencilTool.classList.remove('active');
        });
        
        // Drawing functions
        function draw(e) {
            if (!isDrawing) return;
            
            const rect = canvas.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            
            ctx.beginPath();
            ctx.moveTo(lastX, lastY);
            ctx.lineTo(x, y);
            ctx.stroke();
            
            [lastX, lastY] = [x, y];
        }
        
        // Event listeners
        canvas.addEventListener('mousedown', (e) => {
            isDrawing = true;
            const rect = canvas.getBoundingClientRect();
            [lastX, lastY] = [e.clientX - rect.left, e.clientY - rect.top];
        });
        
        canvas.addEventListener('mousemove', draw);
        canvas.addEventListener('mouseup', () => isDrawing = false);
        canvas.addEventListener('mouseout', () => isDrawing = false);
        
        // Clear canvas button
        if (this.clearCanvasButton) {
            this.clearCanvasButton.addEventListener('click', () => {
                ctx.fillStyle = 'white';
                ctx.fillRect(0, 0, canvas.width, canvas.height);
                ctx.strokeStyle = isEraser ? '#FFFFFF' : '#000000';
                ctx.lineWidth = parseInt(lineWidthSlider.value);  // Maintain current width
            });
        }
    }

    clearCanvas() {
        const canvas = this.drawingCanvas;
        const ctx = canvas.getContext('2d');
        ctx.fillStyle = 'white';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
    }
}

// Initialize chat UI when page loads
document.addEventListener('DOMContentLoaded', () => {
    new ChatUI();
});

