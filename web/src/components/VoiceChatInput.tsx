'use client';
import { useState, useRef, useEffect } from 'react';
import { ArrowRight, Mic, Square } from 'lucide-react';

interface VoiceChatInputProps {
  onSendQuery: (query: string) => void;
  isLoading: boolean;
}

export default function VoiceChatInput({ onSendQuery, isLoading }: VoiceChatInputProps) {
  const [query, setQuery] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  const toggleRecording = async () => {
    if (isRecording) {
      if (mediaRecorderRef.current) mediaRecorderRef.current.stop();
      setIsRecording(false);
    } else {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const mediaRecorder = new MediaRecorder(stream);
        mediaRecorderRef.current = mediaRecorder;
        audioChunksRef.current = [];

        mediaRecorder.ondataavailable = (e) => {
          if (e.data.size > 0) audioChunksRef.current.push(e.data);
        };

        mediaRecorder.onstop = async () => {
          const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
          stream.getTracks().forEach((track) => track.stop());

          const formData = new FormData();
          formData.append('file', audioBlob, 'recording.wav');
          
          try {
            const response = await fetch('/api/voice/stt', { method: 'POST', body: formData });
            if (response.ok) {
              const data = await response.json();
              if (data.transcript) {
                setQuery(data.transcript);
              }
            } else {
              console.error("STT Error:", await response.text());
            }
          } catch (error) {
            console.error("STT Request failed:", error);
          }
        };

        mediaRecorder.start();
        setIsRecording(true);
      } catch (err) {
        console.error("Error accessing microphone:", err);
      }
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    onSendQuery(query);
  };

  return (
    <form onSubmit={handleSubmit} className="flex relative w-full items-end bg-[#1E1E1E] border border-[#333333] hover:border-[#555555] focus-within:border-[#888888] rounded-3xl shadow-lg px-6 py-4 transition-all duration-300 overflow-hidden group">
      {/* Light sweep on focus */}
      <div className="absolute inset-0 translate-x-[-100%] group-focus-within:animate-[shimmer_2s_ease-in-out] bg-gradient-to-r from-transparent via-[#8AB4F8]/5 to-transparent pointer-events-none" />

      <button 
        type="button" 
        onClick={toggleRecording} 
        className={`mr-4 mb-0.5 transition-colors relative z-10 ${isRecording ? 'text-[#E53935] animate-pulse drop-shadow-[0_0_8px_rgba(229,57,53,0.6)]' : 'text-[#888888] hover:text-[#E2E2E2]'}`}
        disabled={isLoading}
      >
        {isRecording ? <Square size={22} /> : <Mic size={22} strokeWidth={1.5} />}
      </button>

      <textarea
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          e.target.style.height = 'auto';
          e.target.style.height = e.target.scrollHeight + 'px';
        }}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSubmit(e);
          }
        }}
        rows={1}
        placeholder={isRecording ? 'Listening...' : 'Commence inquiry...'}
        className="flex-1 bg-transparent outline-none text-[#F5EBE1] placeholder:text-[#F5EBE1]/30 w-full text-[14px] relative z-10 font-light resize-none overflow-hidden min-h-[22px] max-h-[150px] py-0.5"
        style={{ fontFamily: '"Figtree", sans-serif' }}
        disabled={isLoading}
      />

      <button type="submit" className="text-[#888888] hover:text-[#E2E2E2] ms-6 mb-0.5 disabled:opacity-30 transition-colors relative z-10" disabled={isLoading || isRecording || !query.trim()}>
        <ArrowRight size={26} strokeWidth={1.5} />
      </button>
    </form>
  );
}
