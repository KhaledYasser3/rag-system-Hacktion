@extends('layouts.chat')

@section('header-title', 'MedAssist - AI Medical Assistant')

@section('content')
<div class="chat-area">
    <div class="chat-welcome">
        <div class="chat-welcome-icon">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M9 12h6"/>
                <path d="M12 9v6"/>
                <path d="M12 2a10 10 0 1 0 10 10H12V2z"/>
            </svg>
        </div>
        <h2>Medical Knowledge Assistant</h2>
        <p>Ask any medical question and get evidence-based answers with source references from medical literature.</p>

        <div class="suggestion-chips">
            <button class="suggestion-chip" onclick="startWithQuestion('What are the diagnostic criteria for Type 2 Diabetes?')">
                🩺 Type 2 Diabetes diagnosis
            </button>
            <button class="suggestion-chip" onclick="startWithQuestion('What is the first-line treatment for hypertension?')">
                💊 Hypertension treatment
            </button>
            <button class="suggestion-chip" onclick="startWithQuestion('Explain the stages of heart failure classification')">
                ❤️ Heart failure stages
            </button>
            <button class="suggestion-chip" onclick="startWithQuestion('What are the complications of uncontrolled diabetes?')">
                ⚠️ Diabetes complications
            </button>
        </div>
    </div>
</div>

<div class="chat-input-area">
    <div class="chat-input-wrapper">
        <form id="welcomeForm" action="{{ route('chat.create') }}" method="GET" style="display:none"></form>
        <div class="chat-input-container">
            <textarea 
                id="welcomeInput"
                class="chat-input" 
                placeholder="Ask a medical question..."
                rows="1"
                onkeydown="handleWelcomeKeydown(event)"
                oninput="autoResize(this)"
            ></textarea>
        </div>
        <button class="send-btn" onclick="submitWelcomeQuestion()">
            <i data-lucide="send" style="width:20px;height:20px"></i>
        </button>
    </div>
</div>

@endsection

@section('scripts')
<script>
    lucide.createIcons();

    function handleWelcomeKeydown(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            submitWelcomeQuestion();
        }
    }

    async function submitWelcomeQuestion() {
        const input = document.getElementById('welcomeInput');
        const question = input.value.trim();
        if (!question) return;

        // Create conversation and redirect with the question
        try {
            const response = await fetch('{{ route("chat.create") }}', {
                method: 'POST',
                headers: {
                    'X-CSRF-TOKEN': csrfToken,
                    'X-Requested-With': 'XMLHttpRequest',
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                },
            });

            if (response.ok) {
                const data = await response.json();
                window.location.href = `/chat/${data.id}?q=${encodeURIComponent(question)}`;
            } else {
                // Fallback: create via GET redirect
                window.location.href = '{{ route("chat.create") }}';
            }
        } catch (e) {
            window.location.href = '{{ route("chat.create") }}';
        }
    }

    function startWithQuestion(question) {
        document.getElementById('welcomeInput').value = question;
        submitWelcomeQuestion();
    }
</script>
@endsection
