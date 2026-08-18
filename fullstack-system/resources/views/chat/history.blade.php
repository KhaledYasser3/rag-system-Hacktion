@extends('layouts.chat')

@section('header-title', 'Chat History')

@section('content')
<div class="history-page">
    <div class="history-container">
        <h2 class="history-title">Chat History</h2>

        @if($conversations->isEmpty())
            <div class="history-empty">
                <div class="history-empty-icon">
                    <i data-lucide="message-square" style="width:28px;height:28px"></i>
                </div>
                <h3 style="margin-bottom:8px;color:var(--gray-700);">No conversations yet</h3>
                <p style="font-size:15px;">Start a conversation to see your chat history here.</p>
                <a href="{{ route('chat.create') }}" class="new-chat-btn" style="width:auto;display:inline-flex;margin-top:20px;">
                    <i data-lucide="plus" style="width:18px;height:18px"></i>
                    New Conversation
                </a>
            </div>
        @else
            <div class="history-list">
                @foreach($conversations as $conv)
                    <div class="history-item" onclick="window.location='{{ route('chat.show', $conv) }}'">
                        <div class="history-item-icon">
                            <i data-lucide="message-square" style="width:18px;height:18px"></i>
                        </div>
                        <div class="history-item-info">
                            <div class="history-item-title">{{ $conv->title }}</div>
                            <div class="history-item-meta">
                                @if($conv->latestMessage)
                                    {{ Str::limit($conv->latestMessage->content, 80) }}
                                @else
                                    No messages yet
                                @endif
                            </div>
                        </div>
                        <div class="history-item-date">
                            {{ $conv->updated_at->diffForHumans() }}
                        </div>
                        <button class="history-item-delete" 
                                onclick="event.stopPropagation(); deleteConversation({{ $conv->id }})"
                                title="Delete">
                            <i data-lucide="trash-2" style="width:16px;height:16px"></i>
                        </button>
                    </div>
                @endforeach
            </div>
        @endif
    </div>
</div>
@endsection
