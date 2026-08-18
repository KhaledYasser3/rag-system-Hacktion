@extends('layouts.app')

@section('body')
<div class="app-layout">
    {{-- Sidebar Overlay for Mobile --}}
    <div class="sidebar-overlay" onclick="closeSidebar()"></div>

    {{-- Sidebar --}}
    <aside class="sidebar">
        <div class="sidebar-header">
            <div class="sidebar-brand">
                <div class="sidebar-brand-icon">🏥</div>
                <div>
                    <h1>MedAssist</h1>
                    <span>Medical AI</span>
                </div>
            </div>
        </div>

        <a href="{{ route('chat.create') }}" class="new-chat-btn">
            <i data-lucide="plus" style="width:18px;height:18px"></i>
            New Conversation
        </a>

        <nav class="sidebar-nav">
            <a href="{{ route('chat.home') }}" class="{{ request()->routeIs('chat.home') ? 'active' : '' }}">
                <i data-lucide="message-square" style="width:18px;height:18px"></i>
                Chat
            </a>
            <a href="{{ route('chat.history') }}" class="{{ request()->routeIs('chat.history') ? 'active' : '' }}">
                <i data-lucide="history" style="width:18px;height:18px"></i>
                History
            </a>
        </nav>

        <div class="sidebar-conversations">
            <div class="sidebar-conversations-label">Recent</div>
            @foreach($conversations->take(10) as $conv)
                <div class="conv-item {{ request()->routeIs('chat.show') && request()->route('conversation')?->id === $conv->id ? 'active' : '' }}"
                     onclick="window.location='{{ route('chat.show', $conv) }}'">
                    <i data-lucide="message-circle" style="width:16px;height:16px;flex-shrink:0"></i>
                    <span class="conv-item-title">{{ $conv->title }}</span>
                    <button class="conv-item-delete" 
                            onclick="event.stopPropagation(); deleteConversation({{ $conv->id }})"
                            title="Delete">
                        <i data-lucide="trash-2" style="width:14px;height:14px"></i>
                    </button>
                </div>
            @endforeach

            @if($conversations->isEmpty())
                <div style="padding: 20px 12px; text-align: center; color: var(--gray-500); font-size: 13px;">
                    No conversations yet.<br>Start by asking a medical question!
                </div>
            @endif
        </div>

        <div class="sidebar-footer">
            <div class="user-info">
                <div class="user-avatar">{{ substr(auth()->user()->name, 0, 1) }}</div>
                <div>
                    <div style="font-weight: 600; color: var(--white);">{{ auth()->user()->name }}</div>
                    <div style="font-size: 12px; color: var(--gray-400);">{{ auth()->user()->email }}</div>
                </div>
                <form method="POST" action="{{ route('logout') }}">
                    @csrf
                    <button type="submit" class="logout-btn" title="Logout">
                        <i data-lucide="log-out" style="width:18px;height:18px"></i>
                    </button>
                </form>
            </div>
        </div>
    </aside>

    {{-- Main Content --}}
    <main class="main-content">
        <header class="main-header">
            <button class="menu-toggle" onclick="toggleSidebar()">
                <i data-lucide="menu" style="width:22px;height:22px"></i>
            </button>
            <h2 class="main-header-title">@yield('header-title', 'MedAssist')</h2>
            <div class="main-header-status">Online</div>
        </header>

        @yield('content')
    </main>
</div>

<script>
    // Delete conversation
    async function deleteConversation(id) {
        if (!confirm('Delete this conversation?')) return;
        
        try {
            const response = await fetch(`/chat/${id}`, {
                method: 'DELETE',
                headers: {
                    'X-CSRF-TOKEN': csrfToken,
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept': 'application/json',
                }
            });
            
            if (response.ok) {
                window.location.href = '{{ route("chat.home") }}';
            }
        } catch (e) {
            console.error('Delete failed:', e);
        }
    }
</script>
@endsection
