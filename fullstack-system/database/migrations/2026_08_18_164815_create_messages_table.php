<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('messages', function (Blueprint $table) {
            $table->id();
            $table->foreignId('conversation_id')->constrained()->cascadeOnDelete();
            $table->enum('role', ['user', 'assistant']);
            $table->text('content');
            $table->json('sources')->nullable(); // RAG sources: file, page, section, images
            $table->json('suggestions')->nullable(); // Suggested follow-ups
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('messages');
    }
};
