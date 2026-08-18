@extends('layouts.chat')

@section('header-title', $conversation->title)

@section('content')
<div class="chat-area" id="chatArea">
    @if($conversation->messages->isEmpty())
        <div class="chat-welcome">
            <div class="chat-welcome-icon">
                <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M9 12h6"/>
                    <path d="M12 9v6"/>
                    <path d="M12 2a10 10 0 1 0 10 10H12V2z"/>
                </svg>
            </div>
            <h2>Ask Your Question</h2>
            <p>Type your medical question below to get started.</p>
        </div>
    @else
        <div class="messages-container">
            @foreach($conversation->messages as $message)
                @if($message->role === 'user')
                    <div class="message message-user">
                        <div class="message-bubble">
                            {!! nl2br(e($message->content)) !!}
                        </div>
                    </div>
                @else
                    <div class="message message-assistant">
                        <div class="bot-avatar">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2">
                                <path d="M9 12h6"/>
                                <path d="M12 9v6"/>
                                <path d="M12 2a10 10 0 1 0 10 10H12V2z"/>
                            </svg>
                        </div>
                        <div class="message-content">
                            <div class="message-bubble">
                                {!! nl2br(e($message->content)) !!}
                            </div>

                            {{-- Sources --}}
                            @if(!empty($message->sources))
                                <div class="sources-section">
                                    <div class="sources-label">
                                        <i data-lucide="book-open" style="width:14px;height:14px"></i>
                                        Sources
                                    </div>
                                    <div class="source-cards">
                                        @foreach($message->sources as $source)
                                            <div class="source-card">
                                                <div class="source-icon">
                                                    <i data-lucide="file-text" style="width:16px;height:16px"></i>
                                                </div>
                                                <div class="source-info">
                                                    <div class="source-file">{{ $source['file'] ?? 'Unknown' }}</div>
                                                    <div class="source-meta">
                                                        Page {{ $source['page'] ?? '?' }}
                                                        @if(!empty($source['section']))
                                                            · {{ $source['section'] }}
                                                        @endif
                                                    </div>
                                                    @if(!empty($source['excerpt']))
                                                        <div style="font-size:12px;color:var(--gray-500);margin-top:4px;font-style:italic;">
                                                            "{{ Str::limit($source['excerpt'], 120) }}"
                                                        </div>
                                                    @endif
                                                </div>
                                                @if(!empty($source['relevance_score']))
                                                    <div class="source-score">
                                                        {{ round($source['relevance_score'] * 100) }}%
                                                    </div>
                                                @endif
                                            </div>
                                        @endforeach
                                    </div>
                                </div>
                            @endif

                            {{-- Images --}}
                            @if(!empty($message->sources) && isset($message->sources['images']))
                                <div class="images-section">
                                    @foreach($message->sources['images'] as $image)
                                        <div class="image-card">
                                            <div class="image-card-icon">
                                                <i data-lucide="image" style="width:16px;height:16px"></i>
                                            </div>
                                            <div>
                                                <div style="font-weight:600;color:var(--gray-700);">{{ $image['description'] ?? 'Image' }}</div>
                                                <div style="font-size:12px;color:var(--gray-500);">
                                                    Page {{ $image['page'] ?? '?' }} · {{ $image['source_file'] ?? '' }}
                                                </div>
                                            </div>
                                        </div>
                                    @endforeach
                                </div>
                            @endif

                            {{-- Comparisons --}}
                            @if(!empty($message->sources) && isset($message->sources['comparisons']))
                                @php
                                    $comparisons = $message->sources['comparisons'];
                                    $title = is_string($comparisons[0] ?? null) ? array_shift($comparisons) : 'Comparison';
                                @endphp
                                <div class="comparison-section">
                                    <div class="sources-label" style="margin-bottom:8px;">
                                        <i data-lucide="table" style="width:14px;height:14px"></i>
                                        {{ $title }}
                                    </div>
                                    @if(!empty($comparisons) && is_array($comparisons[0] ?? null))
                                        <table class="comparison-table">
                                            <thead>
                                                <tr>
                                                    <th>Feature</th>
                                                    <th>Type 1</th>
                                                    <th>Type 2</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                @foreach($comparisons as $row)
                                                    <tr>
                                                        <td><strong>{{ $row['feature'] ?? '' }}</strong></td>
                                                        <td>{{ $row['type1'] ?? $row['option_a'] ?? '' }}</td>
                                                        <td>{{ $row['type2'] ?? $row['option_b'] ?? '' }}</td>
                                                    </tr>
                                                @endforeach
                                            </tbody>
                                        </table>
                                    @endif
                                </div>
                            @endif

                            {{-- Suggestions --}}
                            @if(!empty($message->suggestions))
                                <div class="suggestions-section">
                                    <div class="suggestions-label">
                                        <i data-lucide="lightbulb" style="width:14px;height:14px"></i>
                                        Follow-up questions
                                    </div>
                                    <div class="suggestion-buttons">
                                        @foreach($message->suggestions as $suggestion)
                                            <button class="suggestion-btn" onclick="askFollowUp('{{ e($suggestion) }}')">
                                                {{ $suggestion }}
                                            </button>
                                        @endforeach
                                    </div>
                                </div>
                            @endif
                        </div>
                    </div>
                @endif
            @endforeach

            {{-- Typing Indicator --}}
            <div class="message message-assistant" id="typingIndicator" style="display:none">
                <div class="bot-avatar">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2">
                        <path d="M9 12h6"/>
                        <path d="M12 9v6"/>
                        <path d="M12 2a10 10 0 1 0 10 10H12V2z"/>
                    </svg>
                </div>
                <div class="message-content">
                    <div class="typing-indicator active">
                        <div class="typing-dots">
                            <span></span><span></span><span></span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    @endif
</div>

<div class="chat-input-area">
    <div class="chat-input-wrapper">
        <div class="chat-input-container">
            <textarea 
                id="chatInput"
                class="chat-input" 
                placeholder="Ask a medical question..."
                rows="1"
                onkeydown="handleKeydown(event)"
                oninput="autoResize(this)"
            ></textarea>
        </div>
        <button class="send-btn" id="sendBtn" onclick="sendMessage()">
            <i data-lucide="send" style="width:20px;height:20px"></i>
        </button>
    </div>
</div>
@endsection

@section('scripts')
<script>
    lucide.createIcons();

    const conversationId = {{ $conversation->id }};
    const chatArea = document.getElementById('chatArea');
    const chatInput = document.getElementById('chatInput');
    const sendBtn = document.getElementById('sendBtn');
    const typingIndicator = document.getElementById('typingIndicator');
    let isProcessing = false;

    // Auto-scroll to bottom
    function scrollToBottom() {
        chatArea.scrollTop = chatArea.scrollHeight;
    }

    // Check for auto-query (from URL)
    document.addEventListener('DOMContentLoaded', () => {
        const urlParams = new URLSearchParams(window.location.search);
        const q = urlParams.get('q');
        if (q) {
            chatInput.value = q;
            autoResize(chatInput);
            sendMessage();
            // Clean URL
            window.history.replaceState({}, '', `/chat/${conversationId}`);
        }
        scrollToBottom();
    });

    function handleKeydown(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    }

    async function sendMessage() {
        if (isProcessing) return;
        
        const question = chatInput.value.trim();
        if (!question) return;

        isProcessing = true;
        sendBtn.disabled = true;
        chatInput.value = '';
        autoResize(chatInput);

        // If no messages container yet, reload for simplicity
        // For AJAX: add user message to DOM
        if (!document.querySelector('.messages-container')) {
            window.location.reload();
            return;
        }

        // Add user message to DOM
        const userHtml = `
            <div class="message message-user" style="animation: messageSlide 0.3s ease;">
                <div class="message-bubble">${escapeHtml(question)}</div>
            </div>
        `;
        typingIndicator.insertAdjacentHTML('beforebegin', userHtml);

        // Show typing
        typingIndicator.style.display = 'flex';
        scrollToBottom();

        try {
            const response = await fetch(`/chat/${conversationId}/send`, {
                method: 'POST',
                headers: {
                    'X-CSRF-TOKEN': csrfToken,
                    'X-Requested-With': 'XMLHttpRequest',
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                },
                body: JSON.stringify({ message: question }),
            });

            const data = await response.json();

            // Hide typing
            typingIndicator.style.display = 'none';

            if (data.success) {
                const msg = data.message;
                let html = `
                    <div class="message message-assistant" style="animation: messageSlide 0.3s ease;">
                        <div class="bot-avatar">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2">
                                <path d="M9 12h6"/><path d="M12 9v6"/><path d="M12 2a10 10 0 1 0 10 10H12V2z"/>
                            </svg>
                        </div>
                        <div class="message-content">
                            <div class="message-bubble"><p>${parseMarkdown(msg.content)}</p></div>
                `;

                // Sources
                if (msg.sources && msg.sources.length > 0) {
                    html += `
                        <div class="sources-section">
                            <div class="sources-label">
                                <i data-lucide="book-open" style="width:14px;height:14px"></i>
                                Sources
                            </div>
                            <div class="source-cards">
                    `;
                    msg.sources.forEach(src => {
                        html += `
                            <div class="source-card">
                                <div class="source-icon">
                                    <i data-lucide="file-text" style="width:16px;height:16px"></i>
                                </div>
                                <div class="source-info">
                                    <div class="source-file">${escapeHtml(src.file || 'Unknown')}</div>
                                    <div class="source-meta">
                                        Page ${src.page || '?'}
                                        ${src.section ? ' · ' + escapeHtml(src.section) : ''}
                                    </div>
                                    ${src.excerpt ? `<div style="font-size:12px;color:var(--gray-500);margin-top:4px;font-style:italic;">"${escapeHtml(src.excerpt.substring(0, 120))}"</div>` : ''}
                                </div>
                                ${src.relevance_score ? `<div class="source-score">${Math.round(src.relevance_score * 100)}%</div>` : ''}
                            </div>
                        `;
                    });
                    html += '</div></div>';
                }

                // Suggestions
                if (msg.suggestions && msg.suggestions.length > 0) {
                    html += `
                        <div class="suggestions-section">
                            <div class="suggestions-label">
                                <i data-lucide="lightbulb" style="width:14px;height:14px"></i>
                                Follow-up questions
                            </div>
                            <div class="suggestion-buttons">
                    `;
                    msg.suggestions.forEach(s => {
                        html += `<button class="suggestion-btn" onclick="askFollowUp('${escapeHtml(s)}')">${escapeHtml(s)}</button>`;
                    });
                    html += '</div></div>';
                }

                html += '</div></div>';
                typingIndicator.insertAdjacentHTML('beforebegin', html);
            } else {
                // Error message
                const errorHtml = `
                    <div class="message message-assistant" style="animation: messageSlide 0.3s ease;">
                        <div class="bot-avatar">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2">
                                <path d="M9 12h6"/><path d="M12 9v6"/><path d="M12 2a10 10 0 1 0 10 10H12V2z"/>
                            </svg>
                        </div>
                        <div class="message-content">
                            <div class="message-bubble" style="border-color:var(--danger-light);color:var(--danger);">
                                ${escapeHtml(msg.content || 'An error occurred. Please try again.')}
                            </div>
                        </div>
                    </div>
                `;
                typingIndicator.insertAdjacentHTML('beforebegin', errorHtml);
            }

            // Re-initialize lucide icons
            lucide.createIcons();
            scrollToBottom();

        } catch (e) {
            typingIndicator.style.display = 'none';
            console.error('Send failed:', e);
        }

        isProcessing = false;
        sendBtn.disabled = false;
        chatInput.focus();
    }

    function askFollowUp(question) {
        chatInput.value = question;
        autoResize(chatInput);
        sendMessage();
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
</script>
@endsection
