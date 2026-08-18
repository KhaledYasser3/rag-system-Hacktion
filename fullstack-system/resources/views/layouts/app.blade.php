<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="csrf-token" content="{{ csrf_token() }}">
    <title>MedAssist - @yield('title', 'AI Medical Assistant')</title>
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🏥</text></svg>">
    
    {{-- Google Fonts --}}
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    
    {{-- Lucide Icons --}}
    <script src="https://unpkg.com/lucide@latest/dist/umd/lucide.js"></script>
    
    <style>
        /* ==========================================
           CSS VARIABLES & RESET
           ========================================== */
        :root {
            --primary: #2563eb;
            --primary-hover: #1d4ed8;
            --primary-light: #dbeafe;
            --primary-50: #eff6ff;
            --secondary: #0f172a;
            --accent: #06b6d4;
            --accent-light: #cffafe;
            --success: #10b981;
            --success-light: #d1fae5;
            --warning: #f59e0b;
            --danger: #ef4444;
            --danger-light: #fee2e2;
            --gray-50: #f8fafc;
            --gray-100: #f1f5f9;
            --gray-200: #e2e8f0;
            --gray-300: #cbd5e1;
            --gray-400: #94a3b8;
            --gray-500: #64748b;
            --gray-600: #475569;
            --gray-700: #334155;
            --gray-800: #1e293b;
            --gray-900: #0f172a;
            --white: #ffffff;
            --shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
            --shadow: 0 1px 3px rgba(0,0,0,0.1), 0 1px 2px rgba(0,0,0,0.06);
            --shadow-md: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06);
            --shadow-lg: 0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -2px rgba(0,0,0,0.05);
            --shadow-xl: 0 20px 25px -5px rgba(0,0,0,0.1), 0 10px 10px -5px rgba(0,0,0,0.04);
            --radius-sm: 6px;
            --radius: 10px;
            --radius-lg: 14px;
            --radius-xl: 20px;
            --sidebar-width: 300px;
            --header-height: 64px;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        html {
            font-size: 16px;
            -webkit-text-size-adjust: 100%;
        }

        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: var(--gray-50);
            color: var(--gray-800);
            line-height: 1.6;
            overflow: hidden;
            height: 100vh;
            -webkit-font-smoothing: antialiased;
        }

        a {
            color: inherit;
            text-decoration: none;
        }

        button {
            cursor: pointer;
            border: none;
            outline: none;
            font-family: inherit;
        }

        input, textarea {
            font-family: inherit;
            outline: none;
        }

        /* ==========================================
           SCROLLBAR STYLES
           ========================================== */
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: var(--gray-300); border-radius: 3px; }
        ::-webkit-scrollbar-thumb:hover { background: var(--gray-400); }

        /* ==========================================
           APP LAYOUT
           ========================================== */
        .app-layout {
            display: flex;
            height: 100vh;
            overflow: hidden;
        }

        /* ==========================================
           SIDEBAR
           ========================================== */
        .sidebar {
            width: var(--sidebar-width);
            background: var(--gray-900);
            color: var(--white);
            display: flex;
            flex-direction: column;
            flex-shrink: 0;
            transition: transform 0.3s ease;
            z-index: 100;
        }

        .sidebar-header {
            padding: 16px 20px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            display: flex;
            align-items: center;
            justify-content: space-between;
            min-height: var(--header-height);
        }

        .sidebar-brand {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .sidebar-brand-icon {
            width: 36px;
            height: 36px;
            background: linear-gradient(135deg, var(--primary), var(--accent));
            border-radius: var(--radius);
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .sidebar-brand h1 {
            font-size: 18px;
            font-weight: 700;
            letter-spacing: -0.5px;
        }

        .sidebar-brand span {
            font-size: 11px;
            color: var(--gray-400);
            display: block;
            margin-top: -2px;
        }

        .new-chat-btn {
            width: calc(100% - 32px);
            padding: 12px 16px;
            margin: 16px 16px 8px;
            background: var(--primary);
            color: var(--white);
            border-radius: var(--radius);
            font-size: 14px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
            justify-content: center;
            transition: all 0.2s;
            flex-shrink: 0;
        }

        .new-chat-btn:hover {
            background: var(--primary-hover);
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(37,99,235,0.4);
        }

        .sidebar-nav {
            padding: 8px 12px;
            margin-bottom: 8px;
        }

        .sidebar-nav a {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 10px 12px;
            border-radius: var(--radius-sm);
            font-size: 14px;
            color: var(--gray-400);
            transition: all 0.2s;
        }

        .sidebar-nav a:hover,
        .sidebar-nav a.active {
            background: rgba(255,255,255,0.1);
            color: var(--white);
        }

        .sidebar-conversations {
            flex: 1;
            overflow-y: auto;
            padding: 8px 12px;
        }

        .sidebar-conversations-label {
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--gray-500);
            padding: 8px 12px 4px;
        }

        .conv-item {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 10px 12px;
            border-radius: var(--radius-sm);
            font-size: 13px;
            color: var(--gray-300);
            transition: all 0.2s;
            cursor: pointer;
            position: relative;
            group: true;
        }

        .conv-item:hover {
            background: rgba(255,255,255,0.08);
            color: var(--white);
        }

        .conv-item.active {
            background: rgba(37,99,235,0.3);
            color: var(--white);
        }

        .conv-item-title {
            flex: 1;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .conv-item-delete {
            display: none;
            color: var(--danger);
            padding: 4px;
            border-radius: 4px;
        }

        .conv-item:hover .conv-item-delete {
            display: block;
        }

        .conv-item-delete:hover {
            background: var(--danger-light);
        }

        .sidebar-footer {
            padding: 16px;
            border-top: 1px solid rgba(255,255,255,0.1);
        }

        .sidebar-footer .user-info {
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 13px;
        }

        .sidebar-footer .user-avatar {
            width: 34px;
            height: 34px;
            border-radius: 50%;
            background: linear-gradient(135deg, var(--primary), var(--accent));
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 14px;
        }

        .sidebar-footer .logout-btn {
            margin-left: auto;
            color: var(--gray-400);
            padding: 6px;
            border-radius: var(--radius-sm);
            transition: all 0.2s;
            background: transparent;
        }

        .sidebar-footer .logout-btn:hover {
            color: var(--danger);
            background: var(--danger-light);
        }

        /* ==========================================
           MAIN CONTENT
           ========================================== */
        .main-content {
            flex: 1;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            min-width: 0;
        }

        .main-header {
            height: var(--header-height);
            background: var(--white);
            border-bottom: 1px solid var(--gray-200);
            display: flex;
            align-items: center;
            padding: 0 20px;
            gap: 12px;
            flex-shrink: 0;
        }

        .menu-toggle {
            display: none;
            padding: 8px;
            border-radius: var(--radius-sm);
            color: var(--gray-600);
            background: transparent;
            transition: all 0.2s;
        }

        .menu-toggle:hover {
            background: var(--gray-100);
        }

        .main-header-title {
            font-size: 16px;
            font-weight: 600;
            color: var(--gray-800);
            flex: 1;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .main-header-status {
            font-size: 12px;
            color: var(--success);
            display: flex;
            align-items: center;
            gap: 4px;
        }

        .main-header-status::before {
            content: '';
            width: 6px;
            height: 6px;
            background: var(--success);
            border-radius: 50%;
        }

        /* ==========================================
           CHAT AREA
           ========================================== */
        .chat-area {
            flex: 1;
            overflow-y: auto;
            padding: 24px;
            scroll-behavior: smooth;
        }

        .chat-welcome {
            max-width: 700px;
            margin: 0 auto;
            text-align: center;
            padding: 60px 20px;
        }

        .chat-welcome-icon {
            width: 80px;
            height: 80px;
            background: linear-gradient(135deg, var(--primary), var(--accent));
            border-radius: var(--radius-xl);
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 24px;
            box-shadow: 0 8px 32px rgba(37,99,235,0.3);
        }

        .chat-welcome h2 {
            font-size: 28px;
            font-weight: 800;
            color: var(--gray-900);
            margin-bottom: 8px;
            letter-spacing: -0.5px;
        }

        .chat-welcome p {
            font-size: 16px;
            color: var(--gray-500);
            max-width: 500px;
            margin: 0 auto 32px;
        }

        .suggestion-chips {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            justify-content: center;
        }

        .suggestion-chip {
            padding: 12px 20px;
            background: var(--white);
            border: 1px solid var(--gray-200);
            border-radius: var(--radius-lg);
            font-size: 14px;
            color: var(--gray-700);
            transition: all 0.2s;
            cursor: pointer;
        }

        .suggestion-chip:hover {
            border-color: var(--primary);
            color: var(--primary);
            background: var(--primary-50);
            transform: translateY(-2px);
            box-shadow: var(--shadow-md);
        }

        /* ==========================================
           MESSAGES
           ========================================== */
        .messages-container {
            max-width: 800px;
            margin: 0 auto;
        }

        .message {
            margin-bottom: 24px;
            animation: messageSlide 0.3s ease;
        }

        @keyframes messageSlide {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .message-user {
            display: flex;
            justify-content: flex-end;
        }

        .message-user .message-bubble {
            background: var(--primary);
            color: var(--white);
            border-radius: var(--radius-lg) var(--radius-lg) 4px var(--radius-lg);
            padding: 14px 20px;
            max-width: 85%;
            font-size: 15px;
            line-height: 1.5;
        }

        .message-assistant {
            display: flex;
            gap: 12px;
            align-items: flex-start;
        }

        .message-assistant .bot-avatar {
            width: 36px;
            height: 36px;
            border-radius: var(--radius);
            background: linear-gradient(135deg, var(--primary), var(--accent));
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
            margin-top: 2px;
        }

        .message-assistant .message-content {
            flex: 1;
            min-width: 0;
        }

        .message-assistant .message-bubble {
            background: var(--white);
            border: 1px solid var(--gray-200);
            border-radius: 4px var(--radius-lg) var(--radius-lg) var(--radius-lg);
            padding: 16px 20px;
            font-size: 15px;
            line-height: 1.7;
            color: var(--gray-800);
            box-shadow: var(--shadow-sm);
        }

        .message-bubble strong { font-weight: 600; color: var(--gray-900); }
        .message-bubble p { margin-bottom: 10px; }
        .message-bubble p:last-child { margin-bottom: 0; }
        .message-bubble ul, .message-bubble ol { padding-left: 20px; margin: 8px 0; }
        .message-bubble li { margin-bottom: 4px; }

        /* ==========================================
           SOURCES
           ========================================== */
        .sources-section {
            margin-top: 16px;
            padding-top: 16px;
            border-top: 1px solid var(--gray-100);
        }

        .sources-label {
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--gray-500);
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .source-cards {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .source-card {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 10px 14px;
            background: var(--gray-50);
            border: 1px solid var(--gray-200);
            border-radius: var(--radius);
            font-size: 13px;
            transition: all 0.2s;
        }

        .source-card:hover {
            background: var(--primary-50);
            border-color: var(--primary);
        }

        .source-icon {
            width: 32px;
            height: 32px;
            border-radius: var(--radius-sm);
            background: var(--primary-light);
            display: flex;
            align-items: center;
            justify-content: center;
            color: var(--primary);
            flex-shrink: 0;
        }

        .source-info {
            flex: 1;
            min-width: 0;
        }

        .source-file {
            font-weight: 600;
            color: var(--gray-800);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .source-meta {
            font-size: 12px;
            color: var(--gray-500);
            margin-top: 2px;
        }

        .source-score {
            padding: 2px 8px;
            background: var(--success-light);
            color: var(--success);
            border-radius: 20px;
            font-size: 11px;
            font-weight: 600;
        }

        /* ==========================================
           IMAGES SECTION
           ========================================== */
        .images-section {
            margin-top: 12px;
        }

        .image-card {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 10px 14px;
            background: var(--accent-light);
            border: 1px solid #a5f3fc;
            border-radius: var(--radius);
            font-size: 13px;
        }

        .image-card-icon {
            width: 32px;
            height: 32px;
            border-radius: var(--radius-sm);
            background: var(--white);
            display: flex;
            align-items: center;
            justify-content: center;
            color: var(--accent);
        }

        /* ==========================================
           COMPARISON TABLE
           ========================================== */
        .comparison-section {
            margin-top: 12px;
        }

        .comparison-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
            border-radius: var(--radius);
            overflow: hidden;
            border: 1px solid var(--gray-200);
        }

        .comparison-table th {
            background: var(--gray-100);
            padding: 10px 14px;
            text-align: left;
            font-weight: 600;
            color: var(--gray-700);
            border-bottom: 1px solid var(--gray-200);
        }

        .comparison-table td {
            padding: 10px 14px;
            border-bottom: 1px solid var(--gray-100);
            color: var(--gray-600);
        }

        .comparison-table tr:last-child td {
            border-bottom: none;
        }

        /* ==========================================
           SUGGESTIONS
           ========================================== */
        .suggestions-section {
            margin-top: 16px;
        }

        .suggestions-label {
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--gray-500);
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .suggestion-buttons {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }

        .suggestion-btn {
            padding: 8px 14px;
            background: var(--white);
            border: 1px solid var(--gray-200);
            border-radius: 20px;
            font-size: 13px;
            color: var(--gray-700);
            transition: all 0.2s;
        }

        .suggestion-btn:hover {
            border-color: var(--primary);
            color: var(--primary);
            background: var(--primary-50);
        }

        /* ==========================================
           CHAT INPUT
           ========================================== */
        .chat-input-area {
            padding: 16px 24px 24px;
            background: var(--gray-50);
            flex-shrink: 0;
        }

        .chat-input-wrapper {
            max-width: 800px;
            margin: 0 auto;
            display: flex;
            gap: 12px;
            align-items: flex-end;
        }

        .chat-input-container {
            flex: 1;
            background: var(--white);
            border: 2px solid var(--gray-200);
            border-radius: var(--radius-lg);
            padding: 4px;
            transition: border-color 0.2s;
            display: flex;
            align-items: flex-end;
        }

        .chat-input-container:focus-within {
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(37,99,235,0.1);
        }

        .chat-input {
            flex: 1;
            border: none;
            padding: 12px 16px;
            font-size: 15px;
            resize: none;
            background: transparent;
            max-height: 150px;
            min-height: 48px;
            line-height: 1.5;
        }

        .send-btn {
            width: 48px;
            height: 48px;
            background: var(--primary);
            color: var(--white);
            border-radius: var(--radius);
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s;
            flex-shrink: 0;
        }

        .send-btn:hover {
            background: var(--primary-hover);
            transform: translateY(-1px);
        }

        .send-btn:disabled {
            background: var(--gray-300);
            cursor: not-allowed;
            transform: none;
        }

        /* ==========================================
           TYPING INDICATOR
           ========================================== */
        .typing-indicator {
            display: none;
            padding: 16px 20px;
            background: var(--white);
            border: 1px solid var(--gray-200);
            border-radius: 4px var(--radius-lg) var(--radius-lg) var(--radius-lg);
            box-shadow: var(--shadow-sm);
        }

        .typing-indicator.active {
            display: block;
        }

        .typing-dots {
            display: flex;
            gap: 4px;
        }

        .typing-dots span {
            width: 8px;
            height: 8px;
            background: var(--gray-400);
            border-radius: 50%;
            animation: typingBounce 1.4s infinite ease-in-out;
        }

        .typing-dots span:nth-child(2) { animation-delay: 0.2s; }
        .typing-dots span:nth-child(3) { animation-delay: 0.4s; }

        @keyframes typingBounce {
            0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
            40% { transform: scale(1); opacity: 1; }
        }

        /* ==========================================
           SIDEBAR OVERLAY (MOBILE)
           ========================================== */
        .sidebar-overlay {
            display: none;
            position: fixed;
            inset: 0;
            background: rgba(0,0,0,0.5);
            z-index: 99;
            backdrop-filter: blur(2px);
        }

        /* ==========================================
           RESPONSIVE DESIGN
           ========================================== */
        @media (max-width: 1024px) {
            .sidebar {
                position: fixed;
                left: 0;
                top: 0;
                bottom: 0;
                transform: translateX(-100%);
            }

            .sidebar.open {
                transform: translateX(0);
            }

            .sidebar-overlay.active {
                display: block;
            }

            .menu-toggle {
                display: flex;
            }

            .chat-input-area {
                padding: 12px 16px 16px;
            }

            .chat-area {
                padding: 16px;
            }
        }

        @media (max-width: 640px) {
            :root {
                --header-height: 56px;
            }

            .chat-welcome {
                padding: 40px 16px;
            }

            .chat-welcome h2 {
                font-size: 22px;
            }

            .chat-welcome p {
                font-size: 14px;
            }

            .suggestion-chips {
                flex-direction: column;
            }

            .suggestion-chip {
                text-align: left;
            }

            .message-user .message-bubble {
                max-width: 90%;
                padding: 12px 16px;
                font-size: 14px;
            }

            .message-assistant .bot-avatar {
                width: 30px;
                height: 30px;
            }

            .message-assistant .message-bubble {
                padding: 12px 16px;
                font-size: 14px;
            }

            .source-card {
                flex-wrap: wrap;
            }

            .comparison-table {
                font-size: 12px;
            }

            .comparison-table th,
            .comparison-table td {
                padding: 8px 10px;
            }

            .chat-input-area {
                padding: 10px 12px 14px;
            }

            .chat-input {
                padding: 10px 14px;
                font-size: 14px;
            }

            .send-btn {
                width: 42px;
                height: 42px;
            }
        }

        @media (max-width: 380px) {
            .chat-welcome-icon {
                width: 64px;
                height: 64px;
            }

            .chat-welcome h2 {
                font-size: 20px;
            }
        }

        /* ==========================================
           UTILITIES
           ========================================== */
        .fade-in {
            animation: fadeIn 0.3s ease;
        }

        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }

        /* History page specific */
        .history-page {
            flex: 1;
            overflow-y: auto;
            padding: 24px;
        }

        .history-container {
            max-width: 800px;
            margin: 0 auto;
        }

        .history-title {
            font-size: 24px;
            font-weight: 700;
            margin-bottom: 24px;
            color: var(--gray-900);
        }

        .history-empty {
            text-align: center;
            padding: 60px 20px;
            color: var(--gray-500);
        }

        .history-empty-icon {
            width: 64px;
            height: 64px;
            background: var(--gray-100);
            border-radius: var(--radius-lg);
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 16px;
            color: var(--gray-400);
        }

        .history-list {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .history-item {
            display: flex;
            align-items: center;
            gap: 16px;
            padding: 16px 20px;
            background: var(--white);
            border: 1px solid var(--gray-200);
            border-radius: var(--radius);
            transition: all 0.2s;
            cursor: pointer;
        }

        .history-item:hover {
            border-color: var(--primary);
            box-shadow: var(--shadow-md);
            transform: translateY(-1px);
        }

        .history-item-icon {
            width: 40px;
            height: 40px;
            background: var(--primary-light);
            border-radius: var(--radius);
            display: flex;
            align-items: center;
            justify-content: center;
            color: var(--primary);
            flex-shrink: 0;
        }

        .history-item-info {
            flex: 1;
            min-width: 0;
        }

        .history-item-title {
            font-weight: 600;
            font-size: 15px;
            color: var(--gray-800);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .history-item-meta {
            font-size: 13px;
            color: var(--gray-500);
            margin-top: 2px;
        }

        .history-item-date {
            font-size: 12px;
            color: var(--gray-400);
            flex-shrink: 0;
        }

        .history-item-delete {
            color: var(--gray-400);
            padding: 6px;
            border-radius: var(--radius-sm);
            transition: all 0.2s;
            background: transparent;
            flex-shrink: 0;
        }

        .history-item-delete:hover {
            color: var(--danger);
            background: var(--danger-light);
        }

        @media (max-width: 640px) {
            .history-page {
                padding: 16px;
            }

            .history-item {
                padding: 12px 14px;
            }

            .history-item-date {
                display: none;
            }
        }

        /* Markdown-like rendering in messages */
        .message-bubble code {
            background: var(--gray-100);
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 0.9em;
            color: var(--gray-700);
        }

        .message-bubble pre {
            background: var(--gray-900);
            color: #e2e8f0;
            padding: 16px;
            border-radius: var(--radius);
            overflow-x: auto;
            margin: 12px 0;
        }

        .message-bubble pre code {
            background: none;
            padding: 0;
            color: inherit;
        }
    </style>

    @yield('head')
</head>
<body>
    @yield('body')

    <script>
        // CSRF token setup for AJAX
        const csrfToken = document.querySelector('meta[name="csrf-token"]').content;

        // Auto-resize textarea
        function autoResize(textarea) {
            textarea.style.height = 'auto';
            textarea.style.height = Math.min(textarea.scrollHeight, 150) + 'px';
        }

        // Sidebar toggle for mobile
        function toggleSidebar() {
            const sidebar = document.querySelector('.sidebar');
            const overlay = document.querySelector('.sidebar-overlay');
            sidebar.classList.toggle('open');
            overlay.classList.toggle('active');
        }

        function closeSidebar() {
            const sidebar = document.querySelector('.sidebar');
            const overlay = document.querySelector('.sidebar-overlay');
            sidebar.classList.remove('open');
            overlay.classList.remove('active');
        }

        // Simple markdown to HTML
        function parseMarkdown(text) {
            return text
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                .replace(/\*(.*?)\*/g, '<em>$1</em>')
                .replace(/`(.*?)`/g, '<code>$1</code>')
                .replace(/\n\n/g, '</p><p>')
                .replace(/\n/g, '<br>');
        }

        // Format date
        function formatDate(dateStr) {
            const date = new Date(dateStr);
            const now = new Date();
            const diff = now - date;
            
            if (diff < 60000) return 'Just now';
            if (diff < 3600000) return Math.floor(diff / 60000) + 'm ago';
            if (diff < 86400000) return Math.floor(diff / 3600000) + 'h ago';
            return date.toLocaleDateString();
        }
    </script>

    @yield('scripts')
</body>
</html>
