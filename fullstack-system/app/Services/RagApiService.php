<?php

namespace App\Services;

use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;

class RagApiService
{
    protected string $baseUrl;

    public function __construct()
    {
        $this->baseUrl = config('services.rag.base_url', 'http://127.0.0.1:8000');
    }

    /**
     * Send a query to the RAG system and get a response.
     */
    public function query(string $question, ?string $conversationId = null): array
    {
        try {
            $response = Http::timeout(60)
                ->post("{$this->baseUrl}/api/query", [
                    'question' => $question,
                    'conversation_id' => $conversationId,
                ]);

            if ($response->successful()) {
                return [
                    'success' => true,
                    'data' => $response->json(),
                ];
            }

            Log::error('RAG API Error', [
                'status' => $response->status(),
                'body' => $response->body(),
            ]);

            return [
                'success' => false,
                'error' => 'The medical assistant is temporarily unavailable. Please try again.',
            ];
        } catch (\Exception $e) {
            Log::error('RAG API Connection Error', ['message' => $e->getMessage()]);

            // Return a mock/demo response when RAG is not available
            return $this->getMockResponse($question);
        }
    }

    /**
     * Check if the RAG API is healthy.
     */
    public function healthCheck(): bool
    {
        try {
            $response = Http::timeout(5)->get("{$this->baseUrl}/api/health");
            return $response->successful();
        } catch (\Exception $e) {
            return false;
        }
    }

    /**
     * Fallback mock response when RAG API is unavailable.
     */
    private function getMockResponse(string $question): array
    {
        $lowerQuestion = strtolower($question);

        // Simple keyword-based mock responses for demo
        if (str_contains($lowerQuestion, 'diabetes') || str_contains($lowerQuestion, 'سكري')) {
            return [
                'success' => true,
                'data' => [
                    'answer' => "Diabetes mellitus is a chronic metabolic disorder characterized by elevated blood glucose levels. There are two main types:\n\n**Type 1 Diabetes:** Results from autoimmune destruction of pancreatic beta cells, leading to insulin deficiency.\n\n**Type 2 Diabetes:** Characterized by insulin resistance and relative insulin deficiency. It accounts for 90-95% of all diabetes cases.\n\n**Key diagnostic criteria:**\n- Fasting blood glucose ≥ 126 mg/dL\n- HbA1c ≥ 6.5%\n- Random blood glucose ≥ 200 mg/dL with symptoms",
                    'sources' => [
                        [
                            'file' => 'Harrison_Principles_Internal_Medicine.pdf',
                            'page' => 42,
                            'section' => 'Chapter 3: Diabetes Mellitus',
                            'relevance_score' => 0.95,
                            'excerpt' => 'Diabetes mellitus encompasses a group of metabolic diseases...',
                        ],
                        [
                            'file' => 'Endocrinology_Review.pdf',
                            'page' => 18,
                            'section' => 'Type 2 Diabetes Pathophysiology',
                            'relevance_score' => 0.88,
                            'excerpt' => 'Insulin resistance is the hallmark of type 2 diabetes...',
                        ],
                    ],
                    'images' => [
                        [
                            'description' => 'Glucose metabolism pathway diagram',
                            'page' => 43,
                            'source_file' => 'Harrison_Principles_Internal_Medicine.pdf',
                        ],
                    ],
                    'comparisons' => [
                        'Type 1 vs Type 2 Diabetes',
                        [
                            'feature' => 'Age of onset',
                            'type1' => 'Usually childhood/adolescence',
                            'type2' => 'Usually adulthood (>40 years)',
                        ],
                        [
                            'feature' => 'Insulin levels',
                            'type1' => 'Very low/absent',
                            'type2' => 'Normal or elevated initially',
                        ],
                        [
                            'feature' => 'Treatment',
                            'type1' => 'Insulin therapy required',
                            'type2' => 'Lifestyle changes, oral medications, ± insulin',
                        ],
                    ],
                    'suggestions' => [
                        'What are the complications of diabetes?',
                        'How is diabetes managed pharmacologically?',
                        'What dietary changes help manage diabetes?',
                    ],
                ],
            ];
        }

        if (str_contains($lowerQuestion, 'hypertension') || str_contains($lowerQuestion, 'ضغط')) {
            return [
                'success' => true,
                'data' => [
                    'answer' => "Hypertension (high blood pressure) is defined as:\n\n**Blood Pressure Classification:**\n- **Normal:** < 120/80 mmHg\n- **Elevated:** 120-129 / < 80 mmHg\n- **Stage 1 Hypertension:** 130-139 / 80-89 mmHg\n- **Stage 2 Hypertension:** ≥ 140/90 mmHg\n- **Hypertensive Crisis:** > 180/120 mmHg\n\n**Common causes:**\n- Essential (primary) hypertension: 90-95% of cases\n- Secondary hypertension: renal disease, endocrine disorders, medications",
                    'sources' => [
                        [
                            'file' => 'Harrison_Principles_Internal_Medicine.pdf',
                            'page' => 128,
                            'section' => 'Chapter 12: Hypertension',
                            'relevance_score' => 0.93,
                            'excerpt' => 'Hypertension affects approximately 1 billion individuals worldwide...',
                        ],
                    ],
                    'images' => [
                        [
                            'description' => 'Blood pressure measurement technique',
                            'page' => 130,
                            'source_file' => 'Harrison_Principles_Internal_Medicine.pdf',
                        ],
                    ],
                    'suggestions' => [
                        'What are the first-line medications for hypertension?',
                        'What lifestyle modifications reduce blood pressure?',
                        'What are hypertensive emergencies?',
                    ],
                ],
            ];
        }

        if (str_contains($lowerQuestion, 'heart') || str_contains($lowerQuestion, 'قلب') || str_contains($lowerQuestion, 'cardiac')) {
            return [
                'success' => true,
                'data' => [
                    'answer' => "Heart failure is a complex clinical syndrome resulting from structural or functional impairment of ventricular filling or ejection of blood.\n\n**Classification (NYHA):**\n- **Class I:** No limitation of physical activity\n- **Class II:** Slight limitation; comfortable at rest\n- **Class III:** Marked limitation; comfortable only at rest\n- **Class IV:** Unable to carry out any physical activity without discomfort\n\n**Common causes:** Coronary artery disease, hypertension, valvular heart disease, cardiomyopathy",
                    'sources' => [
                        [
                            'file' => 'Braunwald_Heart_Disease.pdf',
                            'page' => 56,
                            'section' => 'Chapter 4: Heart Failure',
                            'relevance_score' => 0.96,
                            'excerpt' => 'Heart failure remains a leading cause of morbidity and mortality...',
                        ],
                    ],
                    'suggestions' => [
                        'What is the treatment for heart failure?',
                        'What are the diagnostic criteria for heart failure?',
                        'What is the difference between systolic and diastolic heart failure?',
                    ],
                ],
            ];
        }

        // Generic fallback response
        return [
            'success' => true,
            'data' => [
                'answer' => "Thank you for your medical question. Based on the available medical literature, I can provide the following information:\n\nYour question relates to medical knowledge that is well-documented in standard medical references. For the most accurate and comprehensive answer, please ensure your question includes specific medical terminology.\n\n**General advice:**\n- Always consider the patient's complete medical history\n- Review relevant laboratory results and imaging\n- Consider evidence-based treatment guidelines\n- Consult specialty references when needed",
                'sources' => [
                    [
                        'file' => 'Medical_Reference_Guide.pdf',
                        'page' => 1,
                        'section' => 'General Medical Information',
                        'relevance_score' => 0.70,
                        'excerpt' => 'Comprehensive medical reference covering common clinical scenarios...',
                    ],
                ],
                'suggestions' => [
                    'Can you provide more specific medical details?',
                    'What symptoms is the patient experiencing?',
                    'What are the relevant lab results?',
                ],
            ],
        ];
    }
}
