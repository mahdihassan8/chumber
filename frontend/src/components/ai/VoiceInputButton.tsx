import { useEffect, useRef } from "react";
import { useSpeechRecognition } from "@/hooks/useSpeechRecognition";
import { useToast } from "@/context/ToastContext";

interface VoiceInputButtonProps {
  onTranscript: (text: string) => void;
  disabled?: boolean;
}

export function VoiceInputButton({ onTranscript, disabled = false }: VoiceInputButtonProps) {
  const { isSupported, isListening, transcript, error, start, stop, reset } = useSpeechRecognition();
  const { showToast } = useToast();
  const wasListening = useRef(false);

  useEffect(() => {
    if (wasListening.current && !isListening && transcript.trim()) {
      onTranscript(transcript.trim());
      reset();
    }
    wasListening.current = isListening;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isListening]);

  useEffect(() => {
    if (error) showToast(error, "error");
  }, [error, showToast]);

  if (!isSupported) return null;

  return (
    <button
      type="button"
      onClick={isListening ? stop : start}
      disabled={disabled}
      aria-label={isListening ? "Stop voice input" : "Start voice input"}
      title={isListening ? "Stop listening" : "Speak your restock request"}
      className={`relative flex h-11 w-11 shrink-0 items-center justify-center rounded-full transition-colors disabled:opacity-50 ${
        isListening ? "bg-red-600 text-white" : "bg-zinc-100 text-zinc-600 hover:bg-zinc-200"
      }`}
    >
      {isListening && <span className="absolute inset-0 animate-ping rounded-full bg-red-400 opacity-75" />}
      <svg className="relative h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 18.75a6 6 0 006-6v-1.5m-6 7.5a6 6 0 01-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 01-3-3V4.5a3 3 0 116 0v8.25a3 3 0 01-3 3z" />
      </svg>
    </button>
  );
}
