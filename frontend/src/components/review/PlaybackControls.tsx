/**
 * Playback controls for video-style frame navigation.
 */

import React, { useCallback, useEffect } from 'react';
import { useReviewStore } from '../../stores/reviewStore';
import type { PlaybackSpeed } from '../../types/review';

const SPEED_OPTIONS: PlaybackSpeed[] = [0.25, 0.5, 1, 2, 4];

interface PlaybackControlsProps {
  disabled?: boolean;
}

export const PlaybackControls: React.FC<PlaybackControlsProps> = ({ disabled = false }) => {
  const {
    currentFrameIndex,
    totalFrames,
    isPlaying,
    playbackSpeed,
    setCurrentFrameIndex,
    stepForward,
    stepBackward,
    togglePlayback,
    setPlaying,
    setPlaybackSpeed,
  } = useReviewStore();

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (disabled) return;

      // Ignore if user is typing in an input
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement
      ) {
        return;
      }

      switch (e.key) {
        case ' ':
          e.preventDefault();
          togglePlayback();
          break;
        case 'ArrowLeft':
          e.preventDefault();
          stepBackward();
          break;
        case 'ArrowRight':
          e.preventDefault();
          stepForward();
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [disabled, togglePlayback, stepBackward, stepForward]);

  // Playback timer
  useEffect(() => {
    if (!isPlaying || disabled) return;

    const frameDelay = 1000 / (30 * playbackSpeed); // Assume 30fps base
    const interval = setInterval(() => {
      const state = useReviewStore.getState();
      if (state.currentFrameIndex >= state.totalFrames - 1) {
        setPlaying(false);
      } else {
        stepForward();
      }
    }, frameDelay);

    return () => clearInterval(interval);
  }, [isPlaying, playbackSpeed, disabled, setPlaying, stepForward]);

  const handleSeek = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      setCurrentFrameIndex(parseInt(e.target.value, 10));
    },
    [setCurrentFrameIndex]
  );

  return (
    <div className="bg-gray-800 rounded-lg p-4">
      {/* Progress bar */}
      <div className="mb-4">
        <input
          type="range"
          min={0}
          max={Math.max(0, totalFrames - 1)}
          value={currentFrameIndex}
          onChange={handleSeek}
          disabled={disabled || totalFrames === 0}
          className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer
                     [&::-webkit-slider-thumb]:appearance-none
                     [&::-webkit-slider-thumb]:w-4
                     [&::-webkit-slider-thumb]:h-4
                     [&::-webkit-slider-thumb]:bg-blue-500
                     [&::-webkit-slider-thumb]:rounded-full
                     [&::-webkit-slider-thumb]:cursor-pointer
                     disabled:opacity-50 disabled:cursor-not-allowed"
        />
        <div className="flex justify-between text-xs text-gray-400 mt-1">
          <span>Frame {currentFrameIndex + 1}</span>
          <span>{totalFrames} total</span>
        </div>
      </div>

      {/* Control buttons */}
      <div className="flex items-center justify-center gap-4">
        {/* Step backward */}
        <button
          onClick={stepBackward}
          disabled={disabled || currentFrameIndex === 0}
          className="p-2 text-gray-300 hover:text-white hover:bg-gray-700 rounded
                     disabled:opacity-50 disabled:cursor-not-allowed"
          title="Previous frame (Left Arrow)"
        >
          <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>

        {/* Play/Pause */}
        <button
          onClick={togglePlayback}
          disabled={disabled || totalFrames === 0}
          className="p-3 bg-blue-600 hover:bg-blue-700 text-white rounded-full
                     disabled:opacity-50 disabled:cursor-not-allowed"
          title={isPlaying ? 'Pause (Space)' : 'Play (Space)'}
        >
          {isPlaying ? (
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 9v6m4-6v6" />
            </svg>
          ) : (
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-5.197-3.028A1 1 0 008 9.028v5.944a1 1 0 001.555.832l5.197-3.028a1 1 0 000-1.664z" />
            </svg>
          )}
        </button>

        {/* Step forward */}
        <button
          onClick={stepForward}
          disabled={disabled || currentFrameIndex >= totalFrames - 1}
          className="p-2 text-gray-300 hover:text-white hover:bg-gray-700 rounded
                     disabled:opacity-50 disabled:cursor-not-allowed"
          title="Next frame (Right Arrow)"
        >
          <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </button>

        {/* Speed selector */}
        <div className="ml-4 flex items-center gap-2">
          <span className="text-sm text-gray-400">Speed:</span>
          <select
            value={playbackSpeed}
            onChange={(e) => setPlaybackSpeed(parseFloat(e.target.value) as PlaybackSpeed)}
            disabled={disabled}
            className="bg-gray-700 text-white text-sm rounded px-2 py-1
                       disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {SPEED_OPTIONS.map((speed) => (
              <option key={speed} value={speed}>
                {speed}x
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Keyboard hints */}
      <div className="mt-3 text-center text-xs text-gray-500">
        Space: Play/Pause | Arrow Keys: Step through frames
      </div>
    </div>
  );
};

export default PlaybackControls;
