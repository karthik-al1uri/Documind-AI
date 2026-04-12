'use client';

import { useState } from 'react';
import { ThumbsUp, ThumbsDown, Check } from 'lucide-react';
import { submitFeedback } from '@/lib/api';

interface Props {
  query: string;
  answer: string;
}

export function FeedbackButtons({ query, answer }: Props) {
  const [rating, setRating] = useState<number | null>(null);
  const [correction, setCorrection] = useState('');
  const [showCorrection, setShowCorrection] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const handleRate = async (v: number) => {
    setRating(v);
    if (v === -1) {
      setShowCorrection(true);
      return;
    }
    await submitFeedback(query, answer, v);
    setSubmitted(true);
  };

  const handleSubmitCorrection = async () => {
    await submitFeedback(query, answer, -1, correction);
    setSubmitted(true);
    setShowCorrection(false);
  };

  if (submitted)
    return (
      <div className="flex items-center gap-1.5 mt-2 text-[10px] text-dm-success">
        <Check size={12} /> Thanks for your feedback
      </div>
    );

  return (
    <div className="mt-2">
      <div className="flex items-center gap-1">
        <button
          type="button"
          onClick={() => void handleRate(1)}
          className={`p-1.5 rounded-md transition-colors ${
            rating === 1
              ? 'bg-dm-success/20 text-dm-success'
              : 'text-dm-muted hover:text-dm-text hover:bg-dm-surface'
          }`}
        >
          <ThumbsUp size={12} />
        </button>
        <button
          type="button"
          onClick={() => void handleRate(-1)}
          className={`p-1.5 rounded-md transition-colors ${
            rating === -1
              ? 'bg-dm-danger/20 text-dm-danger'
              : 'text-dm-muted hover:text-dm-text hover:bg-dm-surface'
          }`}
        >
          <ThumbsDown size={12} />
        </button>
      </div>
      {showCorrection && (
        <div className="mt-2 flex gap-2 animate-fade-in-up">
          <input
            value={correction}
            onChange={(e) => setCorrection(e.target.value)}
            placeholder="Correction (optional)"
            className="flex-1 text-xs px-3 py-1.5 rounded-lg border border-dm-border bg-dm-bg text-dm-text focus:outline-none focus:ring-1 focus:ring-dm-accent"
          />
          <button
            type="button"
            onClick={() => void handleSubmitCorrection()}
            className="px-3 py-1.5 text-xs bg-dm-accent text-white rounded-lg hover:bg-dm-accent-hover transition-colors"
          >
            Submit
          </button>
        </div>
      )}
    </div>
  );
}
