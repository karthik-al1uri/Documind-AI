'use client';

import { useState } from 'react';
import { ThumbsUp, ThumbsDown, Check } from 'lucide-react';
import { submitFeedback } from '@/lib/api';

interface Props { query: string; answer: string; }

export function FeedbackButtons({ query, answer }: Props) {
  const [rating, setRating] = useState<number | null>(null);
  const [correction, setCorrection] = useState('');
  const [showCorrection, setShowCorrection] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const handleRate = async (v: number) => {
    setRating(v);
    if (v === -1) { setShowCorrection(true); return; }
    await submitFeedback(query, answer, v);
    setSubmitted(true);
  };

  const handleSubmitCorrection = async () => {
    await submitFeedback(query, answer, -1, correction);
    setSubmitted(true);
    setShowCorrection(false);
  };

  if (submitted) return (
    <div className="flex items-center gap-1.5 mt-2 text-[10px] text-green-700">
      <Check size={12} /> Thanks for your feedback
    </div>
  );

  return (
    <div className="mt-2">
      <div className="flex items-center gap-1">
        <button onClick={() => handleRate(1)}
          className={`p-1.5 rounded-md transition-colors ${rating === 1 ? 'bg-green-50 text-green-700' : 'text-ink-4 hover:text-ink-2 hover:bg-surface-2'}`}>
          <ThumbsUp size={12} />
        </button>
        <button onClick={() => handleRate(-1)}
          className={`p-1.5 rounded-md transition-colors ${rating === -1 ? 'bg-red-50 text-red-700' : 'text-ink-4 hover:text-ink-2 hover:bg-surface-2'}`}>
          <ThumbsDown size={12} />
        </button>
      </div>
      {showCorrection && (
        <div className="mt-2 flex gap-2 animate-fade-in-up">
          <input value={correction} onChange={e => setCorrection(e.target.value)}
            placeholder="What's the correct answer?"
            className="flex-1 text-xs px-3 py-1.5 rounded-lg border border-surface-3 focus:outline-none focus:border-brand-400" />
          <button onClick={handleSubmitCorrection}
            className="px-3 py-1.5 text-xs bg-brand-600 text-white rounded-lg hover:bg-brand-700 transition-colors">
            Submit
          </button>
        </div>
      )}
    </div>
  );
}
