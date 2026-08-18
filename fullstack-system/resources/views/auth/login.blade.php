<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>MedAssist - Login</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🏥</text></svg>">
    <style>
        :root {
            --primary: #2563eb;
            --primary-hover: #1d4ed8;
            --primary-light: #dbeafe;
            --accent: #06b6d4;
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
            --danger: #ef4444;
            --danger-light: #fee2e2;
            --radius: 10px;
            --radius-lg: 14px;
            --radius-xl: 20px;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
            padding: 20px;
            position: relative;
            overflow: hidden;
        }

        body::before {
            content: '';
            position: absolute;
            width: 600px;
            height: 600px;
            background: radial-gradient(circle, rgba(37,99,235,0.15) 0%, transparent 70%);
            top: -200px;
            right: -200px;
            border-radius: 50%;
        }

        body::after {
            content: '';
            position: absolute;
            width: 500px;
            height: 500px;
            background: radial-gradient(circle, rgba(6,182,212,0.1) 0%, transparent 70%);
            bottom: -150px;
            left: -150px;
            border-radius: 50%;
        }

        .login-container {
            width: 100%;
            max-width: 420px;
            position: relative;
            z-index: 1;
        }

        .login-brand {
            text-align: center;
            margin-bottom: 36px;
        }

        .login-brand-icon {
            width: 72px;
            height: 72px;
            background: linear-gradient(135deg, var(--primary), var(--accent));
            border-radius: var(--radius-xl);
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 20px;
            box-shadow: 0 8px 32px rgba(37,99,235,0.4);
            font-size: 36px;
        }

        .login-brand h1 {
            font-size: 28px;
            font-weight: 800;
            color: var(--white);
            letter-spacing: -0.5px;
        }

        .login-brand p {
            font-size: 15px;
            color: var(--gray-400);
            margin-top: 6px;
        }

        .login-card {
            background: var(--white);
            border-radius: var(--radius-xl);
            padding: 36px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }

        .login-card h2 {
            font-size: 20px;
            font-weight: 700;
            color: var(--gray-900);
            margin-bottom: 24px;
        }

        .form-group {
            margin-bottom: 18px;
        }

        .form-group label {
            display: block;
            font-size: 14px;
            font-weight: 600;
            color: var(--gray-700);
            margin-bottom: 6px;
        }

        .form-input {
            width: 100%;
            padding: 12px 16px;
            border: 2px solid var(--gray-200);
            border-radius: var(--radius);
            font-size: 15px;
            color: var(--gray-800);
            transition: all 0.2s;
            background: var(--gray-50);
        }

        .form-input:focus {
            border-color: var(--primary);
            background: var(--white);
            box-shadow: 0 0 0 3px rgba(37,99,235,0.1);
        }

        .form-input.error {
            border-color: var(--danger);
        }

        .error-message {
            display: block;
            font-size: 13px;
            color: var(--danger);
            margin-top: 6px;
            padding: 8px 12px;
            background: var(--danger-light);
            border-radius: var(--radius);
        }

        .login-btn {
            width: 100%;
            padding: 14px;
            background: var(--primary);
            color: var(--white);
            border-radius: var(--radius);
            font-size: 16px;
            font-weight: 700;
            transition: all 0.2s;
            margin-top: 8px;
        }

        .login-btn:hover {
            background: var(--primary-hover);
            transform: translateY(-1px);
            box-shadow: 0 4px 16px rgba(37,99,235,0.4);
        }

        .login-btn:active {
            transform: translateY(0);
        }

        .login-footer {
            text-align: center;
            margin-top: 24px;
            font-size: 13px;
            color: var(--gray-500);
        }

        .login-footer a {
            color: var(--primary);
            font-weight: 600;
        }

        @media (max-width: 480px) {
            .login-card {
                padding: 28px 24px;
            }

            .login-brand h1 {
                font-size: 24px;
            }
        }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="login-brand">
            <div class="login-brand-icon">🏥</div>
            <h1>MedAssist</h1>
            <p>AI-Powered Medical Knowledge Assistant</p>
        </div>

        <div class="login-card">
            <h2>Welcome Back</h2>

            @if ($errors->any())
                <div class="error-message">
                    {{ $errors->first() }}
                </div>
            @endif

            <form method="POST" action="{{ route('login') }}">
                @csrf

                <div class="form-group">
                    <label for="email">Email Address</label>
                    <input 
                        type="email" 
                        id="email" 
                        name="email" 
                        class="form-input @error('email') error @enderror" 
                        value="{{ old('email') }}"
                        placeholder="doctor@hospital.com"
                        required 
                        autofocus
                    >
                </div>

                <div class="form-group">
                    <label for="password">Password</label>
                    <input 
                        type="password" 
                        id="password" 
                        name="password" 
                        class="form-input" 
                        placeholder="Enter your password"
                        required
                    >
                </div>

                <button type="submit" class="login-btn">
                    Sign In
                </button>
            </form>
        </div>

        <div class="login-footer">
            Secure medical AI assistant for healthcare professionals
        </div>
    </div>
</body>
</html>
