<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Str;
use App\Models\Conversation;
use App\Models\Message;
use App\Services\RagApiService;

class ChatController extends Controller
{
    public function __construct(
        protected RagApiService $ragService
    ) {}

    /**
     * Home page - shows existing conversations or starts new one.
     */
    public function home()
    {
        $conversations = auth()->user()
            ->conversations()
            ->with('latestMessage')
            ->orderBy('updated_at', 'desc')
            ->get();

        return view('chat.home', compact('conversations'));
    }

    /**
     * Show a specific conversation.
     */
    public function show(Conversation $conversation)
    {
        // Ensure user owns this conversation
        if ($conversation->user_id !== auth()->id()) {
            abort(403);
        }

        $conversation->load('messages');
        $conversations = auth()->user()
            ->conversations()
            ->with('latestMessage')
            ->orderBy('updated_at', 'desc')
            ->get();

        return view('chat.show', compact('conversation', 'conversations'));
    }

    /**
     * Create a new conversation.
     */
    public function create(Request $request)
    {
        $conversation = auth()->user()->conversations()->create([
            'title' => 'New Conversation',
        ]);

        if ($request->expectsJson()) {
            return response()->json(['id' => $conversation->id]);
        }

        // If there's a query parameter, send the message automatically
        if ($request->has('q')) {
            $question = $request->q;
            $conversation->messages()->create([
                'role' => 'user',
                'content' => $question,
            ]);
            $title = Str::limit(strip_tags($question), 50);
            $conversation->update(['title' => $title]);

            $ragResponse = $this->ragService->query($question, $conversation->id);
            $data = $ragResponse['data'] ?? [];
            $conversation->messages()->create([
                'role' => 'assistant',
                'content' => $data['answer'] ?? ($ragResponse['error'] ?? 'An error occurred.'),
                'sources' => $ragResponse['success'] ? ($data['sources'] ?? null) : null,
                'suggestions' => $ragResponse['success'] ? ($data['suggestions'] ?? null) : null,
            ]);

            return redirect()->route('chat.show', $conversation);
        }

        return redirect()->route('chat.show', $conversation);
    }

    /**
     * Send a message and get RAG response.
     */
    public function send(Request $request, Conversation $conversation)
    {
        if ($conversation->user_id !== auth()->id()) {
            abort(403);
        }

        $request->validate([
            'message' => 'required|string|max:2000',
        ]);

        // Save user message
        $userMessage = $conversation->messages()->create([
            'role' => 'user',
            'content' => $request->message,
        ]);

        // Update conversation title from first message
        if ($conversation->messages()->count() === 1) {
            $title = Str::limit(strip_tags($request->message), 50);
            $conversation->update(['title' => $title]);
        }

        // Get RAG response
        $ragResponse = $this->ragService->query(
            $request->message,
            $conversation->id
        );

        if ($ragResponse['success']) {
            $data = $ragResponse['data'];

            $assistantMessage = $conversation->messages()->create([
                'role' => 'assistant',
                'content' => $data['answer'] ?? 'I could not generate a response.',
                'sources' => $data['sources'] ?? null,
                'suggestions' => $data['suggestions'] ?? null,
            ]);

            // Check if AJAX request
            if ($request->expectsJson()) {
                return response()->json([
                    'success' => true,
                    'message' => [
                        'id' => $assistantMessage->id,
                        'content' => $assistantMessage->content,
                        'sources' => $assistantMessage->sources,
                        'suggestions' => $assistantMessage->suggestions,
                        'created_at' => $assistantMessage->created_at->toISOString(),
                    ],
                ]);
            }
        } else {
            $assistantMessage = $conversation->messages()->create([
                'role' => 'assistant',
                'content' => $ragResponse['error'] ?? 'An error occurred.',
                'sources' => null,
                'suggestions' => null,
            ]);

            if ($request->expectsJson()) {
                return response()->json([
                    'success' => true,
                    'message' => [
                        'id' => $assistantMessage->id,
                        'content' => $assistantMessage->content,
                        'sources' => null,
                        'suggestions' => null,
                        'created_at' => $assistantMessage->created_at->toISOString(),
                    ],
                ]);
            }
        }

        return redirect()->route('chat.show', $conversation);
    }

    /**
     * Delete a conversation.
     */
    public function destroy(Conversation $conversation)
    {
        if ($conversation->user_id !== auth()->id()) {
            abort(403);
        }

        $conversation->delete();

        if (request()->expectsJson()) {
            return response()->json(['success' => true]);
        }

        return redirect()->route('chat.home');
    }

    /**
     * Chat history page.
     */
    public function history()
    {
        $conversations = auth()->user()
            ->conversations()
            ->with('latestMessage')
            ->orderBy('updated_at', 'desc')
            ->get();

        return view('chat.history', compact('conversations'));
    }
}
