'use client';

import { useState } from 'react';
import Header from '@/components/Header';
import PromptInput from '@/components/PromptInput';
import ResultPanel from '@/components/ResultPanel';

import type { GenerateApiResult } from '@/components/ResultPanel';
import { requestFloorPlanGeneration } from '@/lib/generateFloorPlan';

import { getApiBase } from '@/lib/apiBase';

const API_BASE = getApiBase();

export default function Home() {
  const [prompt, setPrompt]       = useState('');
  const [result, setResult]       = useState<GenerateApiResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError]         = useState<string | null>(null);

  async function handleGenerate() {
    if (!prompt.trim()) return;
    setError(null);
    setResult(null);
    setIsLoading(true);
    try {
      const data = await requestFloorPlanGeneration(prompt, API_BASE);
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Something went wrong');
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-gray-100">
      <Header />
      <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">

        <section className="mb-8">
          <label
            htmlFor="prompt"
            className="mb-2 block text-sm font-medium text-gray-700"
          >
            Describe your building
          </label>
          <PromptInput
            value={prompt}
            onChange={setPrompt}
            disabled={isLoading}
          />
          <div className="mt-4 flex items-center gap-3">
            <button
              type="button"
              onClick={handleGenerate}
              disabled={isLoading || !prompt.trim()}
              className="rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-medium text-white shadow transition hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isLoading ? 'Generating…' : 'Generate Design'}
            </button>
            {isLoading && (
              <span className="text-xs text-gray-500">
                Architect thinking → layout → SVG (10–20s)
              </span>
            )}
          </div>
        </section>

        <section>
          <ResultPanel result={result} isLoading={isLoading} error={error} apiBase={API_BASE} />
        
        </section>

      </div>
    </main>
  );
}