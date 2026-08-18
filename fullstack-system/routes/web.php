<?php

use Illuminate\Support\Facades\Route;
use App\Http\Controllers\AuthController;
use App\Http\Controllers\ChatController;

// Auth Routes
Route::get('/login', [AuthController::class, 'showLogin'])->name('login');
Route::post('/login', [AuthController::class, 'login']);
Route::post('/logout', [AuthController::class, 'logout'])->name('logout');

// Redirect root to chat or login
Route::get('/', fn () => redirect()->route('chat.home'));

// Protected Routes
Route::middleware('auth')->group(function () {
    // Chat Routes
    Route::get('/chat', [ChatController::class, 'home'])->name('chat.home');
    Route::match(['GET', 'POST'], '/chat/new', [ChatController::class, 'create'])->name('chat.create');
    Route::get('/chat/history', [ChatController::class, 'history'])->name('chat.history');
    Route::get('/chat/{conversation}', [ChatController::class, 'show'])->name('chat.show');
    Route::post('/chat/{conversation}/send', [ChatController::class, 'send'])->name('chat.send');
    Route::delete('/chat/{conversation}', [ChatController::class, 'destroy'])->name('chat.destroy');
});
