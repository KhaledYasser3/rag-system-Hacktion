<?php

namespace Database\Seeders;

use App\Models\User;
use Illuminate\Database\Seeder;
use Illuminate\Support\Facades\Hash;

class DatabaseSeeder extends Seeder
{
    public function run(): void
    {
        User::firstOrCreate(
            ['email' => 'doc@gmail.com'],
            [
                'name' => 'Dr. User',
                'password' => Hash::make('123'),
            ]
        );
    }
}
